from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.index, name='index'),
    # 博客详情
    path('blog/detail/<int:blog_id>', views.blog_detail, name='blog_detail'),
    # 发表博客
    path('blog/pub', views.pub_blog, name='pub_blog'),
    # 处理一级回复
    path('blog/comment/<int:blog_id>/', views.pub_comment, name='pub_comment'),
    # 处理二级回复
    path('blog/comment/<int:blog_id>/reply/<int:parent_comment_id>/', views.pub_comment, name='comment_reply'),
    # 删除评论
    path('blog/comment/delete/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    # 删除博客
    path('blog/delete/<int:blog_id>', views.delete_blog, name='delete_blog'),
    # 编辑已发的博客
    path('blog/edit/<int:blog_id>', views.edit_blog, name='edit_blog'),
    # 搜索
    path('blog/search', views.search, name='search'),
]