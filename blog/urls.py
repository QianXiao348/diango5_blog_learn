from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.index, name='index'),
    # 博客详情
    path('blog/detail/<int:blog_id>', views.blog_detail, name='blog_detail'),
    # 发表博客
    path('blog/pub', views.pub_blog, name='pub_blog'),
    # 上传图片
    path('blog/update_image', views.get_image_for_blog, name='get_image_for_blog'),
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
    # 通知列表
    path('notifications/list', views.notifications_list, name='notifications_list'),
    # 标记已读
    path('notifications/mark_as_read/<int:notification_id>', views.mark_notification_as_read, name='mark_notification_as_read'),
    # 批量标记已读
    path('notifications/mark_all_as_read', views.mark_all_notifications_as_read, name='mark_all_notifications_as_read'),
    # 删除已读通知
    path('notifications/delete/<int:notification_id>', views.delete_notification, name='delete_notification'),
    # 删除所有已读通知
    path('notifications/delete_all', views.delete_all_notifications, name='delete_all_notifications'),
    # 点赞
    path('blog/like/<int:blog_id>', views.toggle_like, name='toggle_like'),
]