from django.shortcuts import get_object_or_404, render, redirect, reverse
from django.http.response import JsonResponse
from django.urls.base import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from .models import BlogCategory, Blog, BlogComment
from .forms import PubBlogForm
from django.db.models import Q
from django.http import HttpResponseForbidden


def index(request):
    blogs = Blog.objects.all()
    return render(request, 'index.html', context={'blogs': blogs})

def blog_detail(request, blog_id):
    try:
        blog = Blog.objects.get(pk=blog_id)
    except Exception as e:
        return render(request, '404.html')
    return render(request, 'article/blog_detail.html', context={'blog': blog})

# 发布博客
@require_http_methods(['GET', 'POST'])
@login_required(login_url=reverse_lazy('qxauth:login'))
def pub_blog(request):
    if request.method == 'GET':
        categories = BlogCategory.objects.all()
        return render(request, 'article/pub_blog.html', context={'categories': categories})
    else:
        form = PubBlogForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data.get('title')
            content = form.cleaned_data.get('content')
            category_id = form.cleaned_data.get('category')
            blog = Blog.objects.create(title=title, content=content, author=request.user, category_id=category_id)
            return JsonResponse({'code': 200, 'msg': '发布成功！', 'data': {'blog_id': blog.id}})
        else:
            print(form.errors)
            return JsonResponse({'code': 400, 'msg': '参数错误！'})

# 发布评论
@require_POST
@login_required(login_url=reverse_lazy('qxauth:login'))
def pub_comment(request):
    blog_id = request.POST.get('blog_id')
    content = request.POST.get('content')
    BlogComment.objects.create(blog_id=blog_id, author=request.user, content=content)
    # 重新加载博客详情
    return redirect(reverse('blog:blog_detail', kwargs={'blog_id': blog_id}))

# 查找视图函数
@require_GET
def search(request):
    # /search?q=xxx
    q = request.GET.get('q')
    # 从博客标题和内容进行查找
    blogs = Blog.objects.filter(Q(title__icontains=q)|Q(content__icontains=q)).all()
    return render(request, 'index.html', context={'blogs': blogs})

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