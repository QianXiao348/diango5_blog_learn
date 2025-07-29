from django.shortcuts import get_object_or_404, render, redirect, reverse
from django.http.response import JsonResponse
from django.urls.base import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from .models import BlogCategory, Blog, BlogComment
from .forms import PubBlogForm, PubCommentForm
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
import datetime

from django.views.decorators.csrf import csrf_exempt  # 测试时 禁用 CSRF 验证

from .moderation import moderate_content
# （首页）博客的分页
def index(request):
    blog_list = Blog.objects.all().order_by('-pub_time')
    
    # 实例化 Paginator，每页显示 6 篇文章
    paginator = Paginator(blog_list,6)
    
    # 获取当前的页码
    page = request.GET.get('page')
    blogs = paginator.get_page(page)
    
    return render(request, 'registration/index.html', context={'blogs': blogs})

def blog_detail(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id)
    
    # 只获取顶级评论 (parent__isnull=True 或者 level=0) 
    # MPTT 模型的 root_nodes() 方法也能获取所有根节点
    # comments = BlogComment.objects.filter(blog=blog).get_root_nodes().order_by('tree_id', 'lft')
    # 或者直接过滤 parent 字段
    comments = BlogComment.objects.filter(blog=blog, parent__isnull=True).order_by('tree_id', 'lft')
    
    comment_form = PubCommentForm()
    context = {
        'blog': blog,
        'comments': comments, # 现在这里只包含顶级评论
        'comment_form': comment_form,
    }
    return render(request, 'article/blog_detail.html', context=context)

# 图片上传
# @csrf_exempt
@require_POST
def get_image_for_blog(request):
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
                        "url": file_url,        # 图片上传成功后的访问地址
                        "alt": image_file.name, # 图片名称
                        "href": file_url        # 图片点击后跳转的地址（通常与 url 相同）
                    }
                })
    # 如果没有收到文件或请求方法不对
    return JsonResponse({"errno": 1, "message": "图片上传失败"})

# 编辑博客
@require_http_methods(['GET', 'POST'])
@login_required(login_url=reverse_lazy('qxauth:login'))
def edit_blog(request, blog_id):
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
        form = PubBlogForm(request.POST, instance=blog) # instance 绑定数据
        if form.is_valid():
            blog = form.save()
            return JsonResponse({'code': 200, 'msg': '博客更新成功！', 'data': {'blog_id': blog.id}})
        else:
            print(form.errors)
            return JsonResponse({'code': 400, 'msg': '参数错误！', 'errors': form.errors})
        
# 发布博客
@require_http_methods(['GET', 'POST'])
@login_required(login_url=reverse_lazy('qxauth:login'))
def pub_blog(request):
    if request.method == 'GET':
        categories = BlogCategory.objects.all()
        form = PubBlogForm() # GET 请求时，初始化一个空的表单
        return render(request, 'article/pub_blog.html', context={'categories': categories, 'form': form})
    else: # POST 请求
        form = PubBlogForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data.get('title')
            content= form.cleaned_data.get('content')
            
            # ai审核
            is_title_safe, title_moderation_msg = moderate_content(title)
            is_content_safe, content_moderation_msg = moderate_content(content)
            
            if not is_title_safe:
                return JsonResponse({'code': 400, 'msg': f'标题审核失败：{title_moderation_msg}'})
            if not is_content_safe:
                return JsonResponse({'code': 400, 'msg': f'内容审核失败：{content_moderation_msg}'})
            
            # 使用 form.save(commit=False) 获取模型实例，但不立即保存到数据库
            blog = form.save(commit=False)
            blog.author = request.user # 设置作者为当前登录用户

            blog.save() # 将完整的博客实例保存到数据库
            
            return JsonResponse({'code': 200, 'msg': '发布成功！', 'data': {'blog_id': blog.id}})
        else:
            print(form.errors)
            return JsonResponse({'code': 400, 'msg': '参数错误！', 'errors': form.errors})

# 发布评论
@require_POST
@login_required(login_url=reverse_lazy('qxauth:login'))
def pub_comment(request, blog_id, parent_comment_id=None):
    blog = get_object_or_404(Blog, id=blog_id)
    form = PubCommentForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'code': 400, 'msg': '评论内容无效', 'errors': form.errors})

    content = form.cleaned_data.get('content')
    # ai审核
    is_safe, moderation_msg = moderate_content(content)
    if not is_safe:
        return JsonResponse({'code': 400, 'msg': f'用语不规范：{moderation_msg}'})

    parent_comment_id = request.POST.get('parent_comment_id')
    reply_to_user_id = request.POST.get('reply_to_user_id')

    new_comment = form.save(commit=False)
    new_comment.blog = blog
    new_comment.author = request.user

    if parent_comment_id:
        try:
            parent_comment = BlogComment.objects.get(id=parent_comment_id)
            new_comment.parent = parent_comment
            if reply_to_user_id:
                new_comment.reply_to_id = reply_to_user_id
        except BlogComment.DoesNotExist:
            pass  # 忽略错误，作为顶级评论处理

    new_comment.save()

    return JsonResponse({'code': 200, 'msg': '评论成功', 'comment_id': new_comment.id})


# 删除评论
@require_POST
@login_required(login_url=reverse_lazy('qxauth:login'))
def delete_comment(request, comment_id):
    # 获取评论
    comment = get_object_or_404(BlogComment, id=comment_id)

    # 权限检查：只有评论作者或超级用户才能删除
    if not request.user.is_superuser and comment.author != request.user:
        return JsonResponse({'code': 403, 'msg': '你没有权限删除此评论！'})

    try:
        comment.delete()
        # 成功删除后返回 JSON 响应
        return JsonResponse({'code': 200, 'msg': '评论删除成功！'})
    except Exception as e:
        # 捕获删除时的异常，例如数据库错误
        return JsonResponse({'code': 500, 'msg': f'删除评论失败：{e}'})

# 查找视图函数
@require_GET
def search(request):
    # /search?q=xxx
    q = request.GET.get('q')
    # 从博客标题和内容进行查找
    blogs = Blog.objects.filter(Q(title__icontains=q)|Q(content__icontains=q)).all()
    return render(request, 'registration/index.html', context={'blogs': blogs})

# 删除博客
@login_required(login_url=reverse_lazy('qxauth:login'))
def delete_blog(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id)
    if not request.user.is_superuser and blog.author != request.user:
        return HttpResponseForbidden('你不是管理员或博主！没有权限删除博客！')
    if request.method == 'POST':
        blog.delete()
        return redirect(reverse('blog:index'))
    return render(request, 'article/delete_confirm.html', context={'blog': blog})
