from django.shortcuts import render, redirect, reverse
from django.http.response import JsonResponse
import string
import random
from django.core.mail import send_mail
from qxauth.models import CaptchaModel
from django.views.decorators.http import require_http_methods
from .forms import RegisterForm, LoginForm
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.models import User

User = get_user_model()

# 用户登录
@require_http_methods(['GET', 'POST'])
def qxlogin(request):
    if request.method == 'GET':
        return render(request, 'login.html')
    else:
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            remember = form.cleaned_data.get('remember')
            user = User.objects.filter(email=email).first()
            if user and user.check_password(password):
                login(request, user) # 自带的登录函数
                if not remember:
                    # 默认的session会保留2周，反过来处理不需要记住我，设置过期时间位0
                    request.session.set_expiry(0)
                return redirect('/')  # 登录成功后跳转到首页
            else:
                print("邮箱或密码错误！")
                return redirect(reverse('qxauth:login'))

# 用户登出
def qxlogout(request):
    logout(request)
    return redirect('/')

# 用户注册
@require_http_methods(['GET', 'POST'])
def register(request):
    if request.method == 'GET':
        return render(request, 'register.html')
    else:
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # 用户的注册
            User.objects.create_user(email=email, username=username, password=password)
            return redirect(reverse('qxauth:login'))
        else:
            print(form.errors)
            # 重新跳转到注册页面
            return redirect(reverse('qxauth:register'))
            # return render(request, 'register.html', context={'form':form})
              
# 发送邮件验证码
def send_email_captcha(request):
    email = request.GET.get('email')
    if not email:
        return JsonResponse({"code":400, "message":'必须传递邮件！'})
    # 生成验证码（取随机前4位阿拉伯数字） [0,3,2,5...]
    captcha = ''.join(random.sample(string.digits, 6))
    # 存储到数据库中（后续应该存储在缓存中）
    CaptchaModel.objects.update_or_create(email=email, defaults={'captcha': captcha})
    send_mail("博客注册验证码", message=f'您的验证码是：{captcha}', recipient_list=[email], from_email=None)
    return JsonResponse({"code":200, "message": "邮箱验证码发送成功！"})