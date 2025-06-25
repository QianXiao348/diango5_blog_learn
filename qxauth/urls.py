from django.urls import path
from . import views

app_name ='qxauth'

urlpatterns = [
    path('login', views.qxlogin, name='login'),
    path('register', views.register, name='register'),
    path('captcha', views.send_email_captcha, name='send_email_captcha'),
    path('logout', views.qxlogout, name='logout')
]
