import datetime
import json
import re

from django.shortcuts import get_object_or_404, render, redirect, reverse
from django.http.response import JsonResponse
from django.urls.base import reverse_lazy
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.db.models import Q, F, Count
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt  # 测试时 禁用 CSRF 验证
from django.core.cache import cache

from .moderation import moderate_content
from .models import BlogCategory, Blog, BlogComment, Notification, BlogLike, ModerationLog, User
from qxauth.models import Follow
from .forms import PubBlogForm, PubCommentForm
from .tasks import run_blog_moderation


def index(request):
    """
    首页
    """
    # 使用 annotate() 和 Count() 来一次性计算每篇博客的评论数
    blog_list = Blog.objects.annotate(comment_count=Count('comments')).order_by('-pub_time')

    # 实例化 Paginator，每页显示 6 篇文章
    paginator = Paginator(blog_list, 6)
    # 获取当前的页码
    page = request.GET.get('page')
    blogs = paginator.get_page(page)  # 获取指定页面的数据

    return render(request, 'registration/index.html', context={'blogs': blogs})


def hot_blogs(request):
    """
    热门博客，按综合分数排序，取前20篇
    """
    cache_key = 'hot_blogs'
    hot_blogs = cache.get(cache_key)
    if not hot_blogs:
        blogs = Blog.objects.select_related('author', 'category').annotate(
            comment_count=Count('comments'),
            hot_score=F('like_count')*2 + F('view_count')*3 + F('comment_count')*5
        ).order_by('-hot_score')[:20]
        hot_blogs_list = list(blogs.values(
            'id', 'title', 'content', 'view_count', 'like_count', 'comment_count',
            'pub_time', 'author__username', 'category__name'
        ))
        try:
            cache.set(cache_key, hot_blogs_list, timeout=60 * 1)
            print("缓存设置成功")
        except Exception as e:
            print(f"缓存设置失败: {e}")
        hot_blogs=hot_blogs_list

    paginator = Paginator(hot_blogs, 6)
    page = request.GET.get('page')
    blogs = paginator.get_page(page)

    return render(request, 'article/hot_blogs.html', context={'blogs': blogs})


@require_GET
def category_blogs(request, category_id):
    """
    显示某个分类下的所有博客文章
    """
    category = get_object_or_404(BlogCategory, id=category_id)
    # 获取分类下的博客
    blog_list = Blog.objects.filter(category=category).order_by('-like_count')

    paginator = Paginator(blog_list, 6)
    page = request.GET.get('page')
    blogs = paginator.get_page(page)

    return render(request, 'article/category_blogs.html', context={'blogs': blogs, 'category': category})


def blog_detail(request, blog_id):
    """
    博客详情
    """
    blog = get_object_or_404(Blog.objects.annotate(comment_count=Count('comments')), id=blog_id)

    # 获取浏览量
    session_key = f'viewed_blog_{blog_id}'
    if not request.session.get(session_key):
        blog.view_count = F('view_count') + 1
        blog.save(update_fields=['view_count'])
        request.session[session_key] = True
        # 设置会话过期时间，1 天
        request.session.set_expiry(datetime.timedelta(days=1).total_seconds())
        blog.refresh_from_db()

    # 判断当前用户是否已点赞
    is_liked = False
    if request.user.is_authenticated:
        is_liked = BlogLike.objects.filter(blog=blog, user=request.user).exists()

    # 获取顶级评论
    comment_list = BlogComment.objects.filter(blog=blog, parent__isnull=True).select_related(
                        'author', 'reply_to').order_by('tree_id', 'lft')
    processed_comments = []
    for comment in comment_list:
        comment.display_level = min(comment.level, 1)
        processed_comments.append(comment)

    # 分页
    paginator = Paginator(processed_comments, 10)
    page = request.GET.get('comment_page')
    comments = paginator.get_page(page)

    comment_form = PubCommentForm()  # 创建一个空的表单 用来渲染

    # 处理通知标记已读
    notification_id_from_url = request.GET.get('notification_id')
    if notification_id_from_url:
        try:
            # 确保通知是发送给当前登录用户，并且是未读的
            notification = Notification.objects.get(
                id=notification_id_from_url,
                recipient=request.user,
                is_read=False
            )
            notification.is_read = True
            notification.save()
        except Notification.DoesNotExist:
            # 如果通知不存在、不属于当前用户或已读，则忽略
            pass

    context = {
        'blog': blog,
        'comments': comments,  # 现在这里只包含顶级评论
        'comment_form': comment_form,
        'is_liked': is_liked,
    }
    return render(request, 'article/blog_detail.html', context=context)


@require_POST
def get_image_for_blog(request):
    """
    图片上传
    """
    if request.FILES.get('image_file'):
        image_file = request.FILES.get('image_file')
        # 构造保存路径，按日期+文件名保存
        today = datetime.datetime.now().strftime('%Y%m%d')
        file_name = default_storage.save(f'articles/{today}/{image_file.name}', image_file)
        # 获取完整可访问的 URL
        file_url = default_storage.url(file_name)
        return JsonResponse({
            "errno": 0,  # 表示无错误（errno 为 0）
            "data": {
                "url": file_url,  # 图片上传成功后的访问地址
                "alt": image_file.name,  # 图片名称
                "href": file_url  # 图片点击后跳转的地址（通常与 url 相同）
            }
        })
    # 如果没有收到文件或请求方法不对
    return JsonResponse({"errno": 1, "message": "图片上传失败"})


@require_http_methods(['GET', 'POST'])
@login_required(login_url=reverse_lazy('qxauth:login'))
def edit_blog(request, blog_id):
    """
    编辑博客
    """
    blog = get_object_or_404(Blog, id=blog_id)
    if not request.user.is_authenticated and request.user != blog.author:
        return HttpResponseForbidden('你没有权限修改此博客')

    if request.method == 'GET':
        # 显示欲填充博客编辑页面
        categories = BlogCategory.objects.all()
        form = PubBlogForm(instance=blog)
        context = {
            'form': form,
            'categories': categories,
            'blog': blog
        }
        return render(request, 'article/edit_blog.html', context=context)
    else:
        form = PubBlogForm(request.POST, instance=blog)  # instance 绑定数据
        if form.is_valid():
            title = form.cleaned_data.get('title')
            content = form.cleaned_data.get('content')
            category = form.cleaned_data.get('category')

            # 异步审核：创建日志并提交 Celery 任务
            try:
                log = ModerationLog.objects.create(
                    content_type='blog',
                    content_id=blog.id,
                    original_content=f'标题: {title}\n内容: {content}',
                    flagged_by_ai=True,
                    reason='异步审核',
                    status='pending',
                    author=blog.author,
                    category=category,
                )
                run_blog_moderation.delay(log.id)
                return JsonResponse({'code': 202, 'msg': '文章正在审核，审核完成后将通过通知告知结果'})
            except Exception as e:
                print(f"Error creating ModerationLog for edited blog: {e}")
                return JsonResponse({'code': 500, 'msg': f'服务器内部错误：审核日志创建失败'})
        else:
            print(form.errors)
            return JsonResponse({'code': 400, 'msg': '参数错误！', 'errors': form.errors})


@require_http_methods(['GET', 'POST'])
@login_required(login_url=reverse_lazy('qxauth:login'))
def pub_blog(request):
    """
    发表博客
    """
    if request.method == 'GET':
        categories = BlogCategory.objects.all()
        form = PubBlogForm()  # GET 请求时，初始化一个空的表单
        return render(request, 'article/pub_blog.html', context={'categories': categories, 'form': form})
    else:  # POST 请求
        form = PubBlogForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data.get('title')
            content = form.cleaned_data.get('content')
            category = form.cleaned_data.get('category')

            # 异步审核：创建日志并提交 Celery 任务
            try:
                log = ModerationLog.objects.create(
                    content_type='blog',
                    content_id=None,
                    original_content=f'标题: {title}\n内容: {content}',
                    flagged_by_ai=True,
                    reason='异步审核',
                    status='pending',
                    author=request.user,
                    category=category,
                )
                run_blog_moderation.delay(log.id)
                return JsonResponse({'code': 202, 'msg': '文章正在审核，审核完成后将通过通知告知结果'})
            except Exception as e:
                print(f"Error creating ModerationLog for new blog: {e}")
                return JsonResponse({'code': 500, 'msg': '服务器内部错误：审核日志创建失败'})
        else:
            return JsonResponse({'code': 400, 'msg': '参数错误！', 'errors': form.errors})


@require_POST
@login_required(login_url=reverse_lazy('qxauth:login'))
def pub_comment(request, blog_id, parent_comment_id=None):
    """
    发表评论
    """
    blog = get_object_or_404(Blog, id=blog_id)
    form = PubCommentForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'code': 400, 'msg': '评论内容无效', 'errors': form.errors})

    content = form.cleaned_data.get('content')
    parent_comment_id = request.POST.get('parent_comment_id')
    reply_to_user_id = request.POST.get('reply_to_user_id')  # 获取被回复者ID

    if parent_comment_id and reply_to_user_id:
        User = get_user_model()  # 确保导入 User
        try:
            replied_to_user = User.objects.get(id=reply_to_user_id)
            # 构建前端可能添加的前缀，然后从内容中移除它
            prefix_to_remove = f'回复 @{replied_to_user.username} : '
            if content.startswith(prefix_to_remove):
                content = content[len(prefix_to_remove):].strip()  # 移除前缀并去除首尾空格
        except User.DoesNotExist:
            pass  # 如果用户不存在，则不移除前缀

    # ai审核
    is_safe, moderation_msg = moderate_content(content)

    if not is_safe:
        comment_content = {
            'content': content,
            'blog_id': blog_id,
            'parent_comment_id': parent_comment_id,
            'reply_to_user_id': reply_to_user_id
        }
        ModerationLog.objects.create(
            content_type='comment',
            content_id=None,
            original_content=json.dumps(comment_content, ensure_ascii=False),  # 将字典转换为 JSON 字符串
            flagged_by_ai=True,
            reason=moderation_msg,
            status='pending',
            author=request.user
        )
        return JsonResponse({'code': 202, 'msg': '内容包含敏感词，已提交审核，请等待管理员审核。'})

    # 审核通过，保存评论
    new_comment = form.save(commit=False)
    new_comment.blog = blog
    new_comment.author = request.user
    new_comment.content = content

    # 默认通知作者
    target_user = blog.author

    if parent_comment_id:
        try:
            parent_comment = BlogComment.objects.get(id=parent_comment_id)
            new_comment.parent = parent_comment
            # 避免自己通知自己
            if parent_comment.author != request.user:
                target_user = parent_comment.author
            if reply_to_user_id:
                User = get_user_model()
                try:
                    reply_to_user = User.objects.get(id=reply_to_user_id)
                    if reply_to_user != request.user:
                        target_user = reply_to_user
                except User.DoesNotExist:
                    pass  # 用户不存在，继续通知博主或父评论作者
        except BlogComment.DoesNotExist:
            pass  # 忽略错误，作为顶级评论处理

    new_comment.save()

    notification_obj = None

    # 创建通知
    if target_user != request.user:  # 避免通知自己
        notification_obj = Notification.objects.create(
            recipient=target_user,
            actor=request.user,
            verb='评论了你的博客',
            description=f'您的文章 "{blog.title}" 有新评论或回复：{new_comment.content[:30]}...',
            target_url=reverse('blog:blog_detail', args=[blog_id]) + f'#comment-{new_comment.id}'  # 定位到评论
        )

    # 如果创建了通知对象，则更新其 target_url
    if notification_obj:
        notification_obj.target_url = reverse('blog:blog_detail', args=[blog.id]) \
                                      + f'?notification_id={notification_obj.id}' \
                                      + f'#comment-{new_comment.id}'
        notification_obj.save()

    return JsonResponse({'code': 200, 'msg': '评论成功', 'comment_id': new_comment.id})


@require_POST
@login_required(login_url=reverse_lazy('qxauth:login'))
def delete_comment(request, comment_id):
    """
    删除评论
    """
    # 获取评论
    comment = get_object_or_404(BlogComment, id=comment_id)

    # 权限检查：只有评论作者或超级用户才能删除
    if not request.user.is_superuser and comment.author != request.user:
        return JsonResponse({'code': 403, 'msg': '你没有权限删除此评论！'})

    # 在删除前获取必要的信息，以便创建通知
    comment_author = comment.author
    comment_blog = comment.blog
    deleter = request.user
    notification_obj = None

    try:
        comment.delete()
        # 如果不是评论作者自己删除，则通知评论作者
        if comment_author != deleter:
            notification_obj = Notification.objects.create(
                recipient=comment_author,
                actor=deleter,
                verb='删除了你的评论',
                description=f'您在文章 "{comment_blog.title}" 的评论已被 {deleter.username} 删除。',
                target_url=reverse('blog:blog_detail', args=[comment.blog.id])
            )

        if notification_obj:
            notification_obj.target_url = reverse('blog:blog_detail', args=[comment.blog.id]) \
                                          + f'?notification_id={notification_obj.id}'
            notification_obj.save()

        return JsonResponse({'code': 200, 'msg': '评论删除成功！'})
    except Exception as e:
        return JsonResponse({'code': 500, 'msg': f'删除评论失败：{e}'})


@require_GET
def search(request):
    """ 查找视图函数 /search?q=xxx """
    q = request.GET.get('q')
    # 从博客标题和内容进行查找
    blogs = Blog.objects.filter(Q(title__icontains=q) | Q(content__icontains=q)).all()
    return render(request, 'registration/index.html', context={'blogs': blogs})


@login_required(login_url=reverse_lazy('qxauth:login'))
def delete_blog(request, blog_id):
    """
    删除博客
    """
    blog = get_object_or_404(Blog, id=blog_id)
    if not request.user.is_superuser and blog.author != request.user:
        return HttpResponseForbidden('你不是管理员或博主！没有权限删除博客！')

    blog_author = blog.author
    blog_title = blog.title
    deleter = request.user

    if request.method == 'POST':
        blog.delete()

        if blog_author != deleter:
            Notification.objects.create(
                recipient=blog_author,
                actor=deleter,
                verb='删除了你的博客',
                description=f'{deleter} 删除了你的博客 "{blog_title}"。',
                target_url=reverse('blog:index')
            )

        return redirect(reverse('blog:index'))
    return render(request, 'article/delete_confirm.html', context={'blog': blog})


@login_required(login_url=reverse_lazy('qxauth:login'))
def notifications_list(request):
    """
    通知列表
    """
    notifications = Notification.objects.filter(recipient=request.user).order_by('created_at')
    return render(request, 'notifications/list.html', context={'notifications': notifications})


@require_POST
@login_required(login_url=reverse_lazy('qxauth:login'))
def mark_notification_as_read(request, notification_id):
    """
    标记为已读
    """
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'code': 200, 'msg': '已读标记成功！'})


@require_POST
@login_required(login_url=reverse_lazy('qxauth:login'))
def mark_all_notifications_as_read(request):
    """
    标记所有为已读
    """
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'code': 200, 'msg': '所有通知已标记为已读！'})


@login_required(login_url=reverse_lazy('qxauth:login'))
def delete_notification(request, notification_id):
    """
    删除已读通知
    """
    # 获取通知并检查是否为已读
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)

    # 检查通知是否已读
    if not notification.is_read:
        return JsonResponse({'code': 400, 'msg': '只能删除已读通知，请先标记为已读！'})

    notification.delete()
    return JsonResponse({'code': 200, 'msg': '通知删除成功！'})


@login_required(login_url=reverse_lazy('qxauth:login'))
def delete_all_notifications(request):
    """
    删除所有已读通知
    """
    Notification.objects.filter(recipient=request.user, is_read=True).delete()
    return JsonResponse({'code': 200, 'msg': '所有已读通知已删除！'})


@login_required(login_url=reverse_lazy('qxauth:login'))
def toggle_like(request, blog_id):
    """
    点赞/取消点赞
    """
    blog = get_object_or_404(Blog, id=blog_id)
    user = request.user
    # 获取当前用户对当前博客的点赞状态
    is_liked = BlogLike.objects.filter(blog=blog, user=user).first()

    if is_liked:
        # 取消点赞
        is_liked.delete()
        blog.like_count = F('like_count') - 1
        blog.save(update_fields=['like_count'])
        blog.refresh_from_db()
        return JsonResponse({'code': 200, 'msg': '取消点赞成功！', 'like_count': blog.like_count})
    else:
        # 点赞
        BlogLike.objects.create(blog=blog, user=user)
        blog.like_count = F('like_count') + 1
        blog.save(update_fields=['like_count'])
        blog.refresh_from_db()

        if blog.author != user:
            # 创建点赞通知
            Notification.objects.create(
                recipient=blog.author,
                actor=user,
                verb='点赞了你的博客',
                description=f'{user.username} 点赞了你的博客 "{blog.title}"。',
                target_url=reverse('blog:blog_detail', args=[blog.id])
            )

        return JsonResponse({'code': 200, 'msg': '点赞成功！', 'like_count': blog.like_count})


# @csrf_exempt
@require_POST
@login_required(login_url=reverse_lazy('qxauth:login'))
def toggle_follow(request, user_id):
    """
    关注用户/取消关注
    """
    User = get_user_model()
    profile_user = get_object_or_404(User, id=user_id)
    follower = request.user

    if profile_user == follower:
        return JsonResponse({'code': 400, 'msg': '不能关注自己！'})

    try:
        follow_relation = Follow.objects.get(followed=profile_user, follower=follower)
        follow_relation.delete()
        is_following = False
        msg = '取消关注成功'
    except Follow.DoesNotExist:
        try:
            Follow.objects.create(followed=profile_user, follower=follower)
            is_following = True
            msg = '关注成功'
            # 创建关注通知
            Notification.objects.create(
                actor=follower,
                recipient=profile_user,
                verb='关注了你',
                description=f'{follower.username} 关注了你。',
                target_url=reverse('qxauth:user_profile', args=[follower.id])
            )
        except IntegrityError:
            # 以防并发请求导致重复创建
            is_following = True
            msg = '已关注'
    # 关注数
    followers_count = profile_user.followers.count()

    return JsonResponse({
        "code": 200,
        "message": msg,
        "is_following": is_following,
        "followers_count": followers_count
    })


def is_moderator(user):
    """判断用户是否是管理员或具有特定权限"""
    return user.is_superuser


@user_passes_test(is_moderator, login_url=reverse_lazy('qxauth:login'))
def moderation_queue(request):
    """
    审核队列
    """
    pending_logs = ModerationLog.objects.filter(status='pending')
    context = {
        'pending_logs': pending_logs,
    }
    return render(request, 'article/moderation_queue.html', context)


@user_passes_test(is_moderator, login_url=reverse_lazy('qxauth:login'))
def review_action(request, log_id, action):
    """
    审核操作
    """
    global content_obj
    log = get_object_or_404(ModerationLog, id=log_id, status='pending')
    if log.content_type == 'blog':
        content_obj = get_object_or_404(Blog, id=log.content_id) if log.content_id else None
    verb = "博客内容"
    if action == 'approve':
        log.status = 'approved'
        log.reviewed_at = timezone.now()
        log.moderator = request.user
        log.save()
        target_url = ""

        if not log.flagged_by_ai:
            # 举报内容审核通过，通知举报人未发现违规
            Notification.objects.create(
                recipient=log.reporter,
                actor=log.moderator,
                verb='审核结果通知',
                content='举报未违规',
                description='你举报的文章经审核未发现违规行为。',
                target_url=reverse('blog:blog_detail', args=[content_obj.id])
            )
        else:
            if log.content_type == 'blog':
                if log.content_id:
                    # 已有博客的审核
                    existing_blog = get_object_or_404(Blog, id=log.content_id)

                    lines = log.original_content.split('\n', 1)
                    title = lines[0].replace('标题: ', '').strip()
                    content = lines[1].replace('内容: ', '').strip()

                    existing_blog.title = title
                    existing_blog.content = content
                    existing_blog.category = log.category
                    existing_blog.pub_time = timezone.now()
                    existing_blog.save()
                    verb = "博客文章"
                    target_url = reverse('blog:blog_detail', args=[existing_blog.id])
                else:
                    lines = log.original_content.split('\n', 1)
                    title = lines[0].replace('标题: ', '').strip()
                    content = lines[1].replace('内容: ', '').strip()
                    new_blog = Blog.objects.create(
                        author=log.author,
                        category=log.category,
                        title=title,
                        content=content,
                        pub_time=timezone.now()
                    )
                    log.content_id = new_blog.id
                    log.save()
                    target_url = reverse('blog:blog_detail', args=[new_blog.id])
            elif log.content_type == 'comment':
                verb = "评论内容"
                comment_data = json.loads(log.original_content)

                # # 获取父评论和回复用户对象
                parent_comment = None
                if comment_data.get('parent_comment_id'):
                    parent_comment = BlogComment.objects.get(id=comment_data['parent_comment_id'])

                reply_to_user = None
                if comment_data.get('reply_to_user_id'):
                    reply_to_user = User.objects.get(id=comment_data['reply_to_user_id'])

                blog_instance = get_object_or_404(Blog, id=comment_data['blog_id'])

                new_comment = BlogComment.objects.create(
                    content=comment_data['content'],
                    blog= blog_instance,
                    author=log.author,
                    parent=parent_comment,
                    reply_to=reply_to_user
                )
                log.content_id = new_comment.id
                log.save()
                target_url = reverse('blog:blog_detail', args=[comment_data['blog_id']]) + f'#comment-{new_comment.id}'
            else:
                return JsonResponse({'code': 400, 'msg': '未知内容类型！'})

        # 创建审核通过通知
        Notification.objects.create(
            actor=log.moderator,
            recipient=log.author,
            verb=verb,
            content='审核通过',
            description=f'你的内容已通过审核。',
            target_url=target_url
        )
        return JsonResponse({'code': 200, 'msg': '内容已通过审核！'})
    elif action == 'reject':
        # 在 review_action 的拒绝分支中，确保用户通知使用去敏后的原因
        moderator_reason = (request.POST.get('reason', '') or '').strip()
        original_reason = (log.reason or '').strip()
        internal_reason = moderator_reason or original_reason or '未提供原因'
        # 后台审计保留完整原因（含置信度）
        log.reason = f'人工复核拒绝，原因：{internal_reason}'
        log.status = 'rejected'
        log.reviewed_at = timezone.now()
        log.moderator = request.user
        log.save()

        # 用户侧通知原因去敏（不显示置信度）
        sanitized_reason = sanitize_reason_text(internal_reason)
        Notification.objects.create(
            recipient=log.author,
            actor=request.user,
            verb='内容审核结果',
            content='未通过审核',
            description=f'你的内容未通过人工审核。原因：{sanitized_reason}',
            target_url=reverse('blog:index')
        )
        return JsonResponse({'code': 200, 'msg': '已拒绝并通知作者'})

        target_url = ""
        if log.content_type == 'blog':
            target_url = reverse('blog:blog_detail', args=[log.content_id]) if log.content_id else reverse('blog:index')
        elif log.content_type == 'comment':
            verb = "评论内容"
            comment_data = json.loads(log.original_content)
            blog_id = comment_data.get('blog_id')
            if blog_id:
                target_url = reverse('blog:blog_detail', args=[blog_id])
            else:
                target_url = reverse('blog:index')

        # 如果是举报内容，通知举报人举报成功并删除内容，通知作者违规
        if not log.flagged_by_ai:
            if content_obj:
                content_obj.delete()

            # 通知举报人举报成功
            Notification.objects.create(
                recipient=log.reporter,
                actor=log.moderator,
                verb='举报成功通知',
                content='举报成功',
                description=f'你举报的博客文章经审核确认为违规，已进行处理，感谢你的贡献！',
                target_url=reverse('blog:index')
            )

        # 创建审核拒绝通知（描述里只展示去敏后的原因文本；若人工未填则采用 AI/举报原因）
        Notification.objects.create(
            actor=log.moderator,
            recipient=log.author,
            verb=verb,
            content='审核拒绝',
            description=f'你的内容存在违规了，原因是：{sanitized_reason}',
            target_url=target_url
        )
        return JsonResponse({'code': 200, 'msg': '内容未通过审核！'})


@require_GET
@user_passes_test(is_moderator)
def get_moderation_count(request):
    """
    获取待审核内容的数量
    """
    try:
        count = ModerationLog.objects.filter(status='pending').count()
        return JsonResponse({'code': 200, 'msg': '获取成功！', 'data': {'count': count}})
    except Exception as e:
        return JsonResponse({'code': 500, 'msg': '服务器错误！'})


@user_passes_test(is_moderator, login_url=reverse_lazy('qxauth:login'))
@require_GET
def moderation_detail(request, log_id):
    """
    审核详情页
    """
    log = get_object_or_404(ModerationLog, id=log_id, status='pending')

    processed_content = {}
    if log.content_type == 'blog':
        try:
            lines = log.original_content.split('\n', 1)
            title = lines[0].replace('标题: ', '').strip()
            content = lines[1].replace('内容: ', '').strip()
            processed_content = {
                'title': title,
                'content': content,
            }
        except IndexError:
            # 如果解析失败，提供一个默认值
            processed_content = {'title': '无法解析的标题', 'content': log.original_content}
    elif log.content_type == 'comment':
        try:
            comment_data = json.loads(log.original_content)
            processed_content = comment_data
        except json.JSONDecodeError:
            # 如果解析失败，提供一个默认值
            processed_content = {'content': '无法解析的评论内容'}

    context = {
        'log': log,
        'processed_content': processed_content,  # 将预处理好的内容传递给模板
    }
    return render(request, 'article/moderation_detail.html', context)


@csrf_exempt
@require_POST
@login_required(login_url=reverse_lazy('qxauth:login'))
def report_post(request, blog_id):
    """
    处理用户提交的举报请求，并创建审核日志
    """
    try:
        data = json.loads(request.body)
        reason = data.get('reason', '无具体原因')
        if not reason:
            return JsonResponse({'code': 400, 'msg': '请填写举报理由！'})
    except(json.JSONDecodeError, KeyError):
        return JsonResponse({'code': 400, 'msg': '无效的请求数据！'})

    blog = get_object_or_404(Blog, id=blog_id)

    # 创建审核日志
    ModerationLog.objects.create(
        content_type='blog',
        content_id=blog_id,
        flagged_by_ai=False,
        reporter=request.user,
        reason=reason,
        original_content=blog.title + '\n' + blog.content,
        status='pending',
        author=blog.author,
    )
    return JsonResponse({'code': 200, 'msg': '举报成功，我们会尽快处理！'})


# 统一的用户侧原因去敏函数：移除任何“置信度”相关片段
def sanitize_reason_text(reason: str) -> str:
    if not reason:
        return ''
    cleaned = reason
    patterns = [
        r'[（(][^）)]*置信度[^）)]*[）)]',
        r'模型?置信度[:：]\s*[0-9.]+',
    ]
    for p in patterns:
        cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    cleaned = re.sub(r'([，；,;])\s*([，；,;])+', r'\1', cleaned)
    cleaned = cleaned.strip(' ，；,;')
    return cleaned
