import datetime
from django.shortcuts import get_object_or_404, render, redirect, reverse
from django.http.response import JsonResponse
from django.urls.base import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.db.models import Q, F, Count
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt  # 测试时 禁用 CSRF 验证

from .moderation import moderate_content
from .models import BlogCategory, Blog, BlogComment, Notification, BlogLike
from qxauth.models import Follow
from .forms import PubBlogForm, PubCommentForm


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
    comment_list = BlogComment.objects.filter(blog=blog, parent__isnull=True).select_related('author',
                                                                                             'reply_to').order_by(
        'tree_id', 'lft')
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
            blog = form.save()
            return JsonResponse({'code': 200, 'msg': '博客更新成功！', 'data': {'blog_id': blog.id}})
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

            # ai审核
            is_title_safe, title_moderation_msg = moderate_content(title)
            is_content_safe, content_moderation_msg = moderate_content(content)

            if not is_title_safe:
                return JsonResponse({'code': 400, 'msg': f'标题审核失败：{title_moderation_msg}'})
            if not is_content_safe:
                return JsonResponse({'code': 400, 'msg': f'内容审核失败：{content_moderation_msg}'})

            # 使用 form.save(commit=False) 获取模型实例，但不立即保存到数据库
            blog = form.save(commit=False)
            blog.author = request.user  # 设置作者为当前登录用户

            blog.save()  # 将完整的博客实例保存到数据库

            return JsonResponse({'code': 200, 'msg': '发布成功！', 'data': {'blog_id': blog.id}})
        else:
            print(form.errors)
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
        return JsonResponse({'code': 400, 'msg': f'用语不规范：{moderation_msg}'})

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


# 查找视图函数
@require_GET
def search(request):
    # /search?q=xxx
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
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
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


@csrf_exempt
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
