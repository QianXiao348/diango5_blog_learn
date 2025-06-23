from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.index, name='index'),
    path('blog/detail/<blog_id>', views.blog_detail, name='blog_detail'),
    path('blog/pub', views.pub_blog, name='pub_blog')
]