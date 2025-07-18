from django.shortcuts import get_object_or_404, render, redirect, reverse
from django.http.response import JsonResponse
from django.urls.base import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from .models import BlogCategory, Blog, BlogComment
from .forms import PubBlogForm, PubCommentForm
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

# （首页）博客的分页
def index(request):
    blog_list = Blog.objects.all().order_by('-pub_time')
    
    # 实例化 Paginator，每页显示 6 篇文章
    paginator = Paginator(blog_list,6)
    
    # 获取当前的页码
    page = request.GET.get('page')
    blogs = paginator.get_page(page)
    
    return render(request, 'registration/index.html', context={'blogs': blogs})

# 博客详情
def blog_detail(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id)
    # mptt 会根据 tree_id 和 lft 字段自动排序，以保证正确的树形结构
    comments = BlogComment.objects.filter(blog=blog).order_by('tree_id', 'lft')
    comment_form = PubCommentForm() # 初始化一个空的评论表单
    context = {
        'blog': blog,
        'comments': comments, # 将已排序的评论列表传递给模板
        'comment_form': comment_form, # 将评论表单传递给模板
    }
    return render(request, 'article/blog_detail.html', context=context)

# 编辑博客
@require_http_methods(['GET', 'POST'])
@login_required(login_url=reverse_lazy('qxauth:login'))
def edit_blog(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id)
    if not request.user.is_authenticated or request.user != blog.author:
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
            # 使用 form.save(commit=False) 获取模型实例，但不立即保存到数据库
            blog = form.save(commit=False)
            blog.author = request.user # 设置作者为当前登录用户

            blog.save() # 现在，将完整的博客实例保存到数据库
            
            return JsonResponse({'code': 200, 'msg': '发布成功！', 'data': {'blog_id': blog.id}})
        else:
            print(form.errors)
            return JsonResponse({'code': 400, 'msg': '参数错误！', 'errors': form.errors})

# 发布评论
@require_http_methods(['POST'])
@login_required(login_url=reverse_lazy('qxauth:login'))
def pub_comment(request, blog_id, parent_comment_id=None):
    blog = get_object_or_404(Blog, id=blog_id)
    comment_form = PubCommentForm()
    if request.method == 'POST':
        comment_form = PubCommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.blog = blog
            new_comment.author = request.user
            # 二级回复
            if parent_comment_id:
                try:
                    # 获取父级评论
                    parent_comment = BlogComment.objects.get(id=parent_comment_id)
                    # 将新评论的 parent 字段设置为父评论实例
                    new_comment.parent = parent_comment
                    new_comment.reply_to = parent_comment.author 
                except BlogComment.DoesNotExist:
                    # 如果提供的父评论ID无效，则将其作为顶级评论处理
                    new_comment.parent = None
            new_comment.save()
            return redirect(reverse('blog:blog_detail', args=[blog.id]) + f'#comment-{new_comment.id}')
        else:
            context = {
                'blog': blog,
                'comment_form': comment_form,
                'parent_comment_id': parent_comment_id
            }
            return render(request, 'article/blog_detail.html', context=context)

# 删除评论
@require_POST
@login_required(login_url=reverse_lazy('qxauth:login'))
def delete_comment(request, comment_id):
    # 获取评论
    comment = get_object_or_404(BlogComment, id=comment_id)
    if not request.user.is_superuser and comment.author != request.user:
        return JsonResponse({'code': 403, 'msg': '你没有权限删除此评论！'})
    comment.delete()
    return redirect(reverse('blog:blog_detail', args=[comment.blog.id]))

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
