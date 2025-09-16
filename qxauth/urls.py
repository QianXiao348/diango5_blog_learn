from django.urls import path
from . import views
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.contrib.auth.decorators import login_required
from django.urls.base import reverse_lazy
from django.contrib.auth import views as auth_views

app_name = 'qxauth'

urlpatterns = [
    # 登录
    path('login', views.qxlogin, name='login'),
    # 注册
    path('register', views.register, name='register'),
    # 发送验证码
    path('send_captcha', views.send_email_captcha, name='send_email_captcha'),
    # 登出
    path('logout', views.qxlogout, name='logout'),
    # 编辑用户信息
    path('edit_profile/<int:user_id>/', views.edit_profile, name='edit_profile'),
    # 修改密码
    path('password_change',
         login_required(PasswordChangeView.as_view(
             template_name='registration/password_change.html',
             success_url=reverse_lazy('qxauth:password_change_done'))),
         name='password_change'),
    # 修改密码成功提示页
    path('password_change/done',
        PasswordChangeDoneView.as_view(template_name='registration/spassword_change_done.html'),
        name='password_change_done'
    ),
    # 密码重置：请求
    path('password_reset/',
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.html',
             success_url=reverse_lazy('qxauth:password_reset_done')
         ),
         name='password_reset'),
    # 邮件发送成功页面
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ),
         name='password_reset_done'),
    # 用户点击邮件重置链接
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html',
             success_url=reverse_lazy('qxauth:password_reset_complete')
         ),
         name='password_reset_confirm'),
    # 密码重置成功完成页
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    # 用户信息
    path('user/<int:user_id>/', views.user_frofile, name='user_profile'),
]
