import string
import random

from django.http import HttpResponse
from django.core.cache import cache
from django.core.mail import send_mail
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.models import User
from django.urls.base import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect, reverse
from django.http.response import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt  # 测试时 禁用 CSRF 验证

from .models import Profile, Follow
from .forms import RegisterForm, LoginForm, ProfileForm
from blog.models import Blog

User = get_user_model()

# @csrf_exempt
@require_http_methods(['GET', 'POST'])
def qxlogin(request):
    """ 用户登录 """
    if request.method == 'GET':
        return render(request, 'registration/login.html')
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
                # return JsonResponse({'code': 200, "message": "登录成功"})
            else:
                print("邮箱或密码错误！")
                return JsonResponse({'code':401,"message":"注册输入有误。请再次检查输入邮箱或密码是否符合标准，并重新输入~"})
                # return redirect(reverse('qxauth:login'))

# 用户登出
def qxlogout(request):
    logout(request)
    return redirect('/')

# 用户注册
@require_http_methods(['GET', 'POST'])
def register(request):
    if request.method == 'GET':
        return render(request, 'registration/register.html')
    else:
        form = RegisterForm(request.POST)
        input_code = request.POST.get('captcha') # 前端表单中用户输入的验证码
        email = request.POST.get('email')
        
        redis_code = cache.get(email)
        # print(redis_code)
        # print(input_code)
        if not redis_code or input_code != redis_code:
            return HttpResponse("验证码无效或已过期，请重新获取~")
        
        if form.is_valid():
            email = form.cleaned_data.get('email')
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # 用户的注册
            User.objects.create_user(email=email, username=username, password=password)
            return redirect(reverse('qxauth:login'))
        else:
            print(form.errors)
            return HttpResponse(form.errors)
            # 重新跳转到注册页面
            # return redirect(reverse('qxauth:register'))
            # return render(request, 'register.html', context={'form':form})


def send_email_captcha(request):
    """
    发送邮件验证码
    """
    email = request.GET.get('email')
    if not email:
        return JsonResponse({"code":400, "message":'必须传递邮件！'})
    # 生成验证码（取随机前4位阿拉伯数字） [0,3,2,5...]
    captcha = ''.join(random.sample(string.digits, 6))

    # 存入 Redis，设置过期时间为 5 分钟（300 秒）
    cache.set(email, captcha, 300)
    
    send_mail(
        "博客注册验证码",
        message=f'您的验证码是：{captcha}，5分钟内有效~喵', 
        recipient_list=[email],
        from_email=None, # 这个参数不能少
        fail_silently=False)
    
    return JsonResponse({"code":200, "message": "邮箱验证码发送成功！"})


@require_http_methods(['GET', 'POST'])
@login_required(login_url=reverse_lazy('qxauth:login'))
def edit_profile(request, user_id):
    """修改用户信息"""
    user = User.objects.get(id=user_id)
    if Profile.objects.filter(user_id=user_id).exists():
        # user_id 是 OneToOneField 自动生成的字段
        profile = Profile.objects.get(user_id=user_id)
    else:
        profile = Profile.objects.create(user=user)

    if request.method == 'POST':
        # 验证修改数据者，是否为用户本人
        if request.user != user:
            return HttpResponse('您没有权限修改此用户信息~ 喵！')

        # 上传的文件保存在 request.FILES 中，通过参数传递给表单类
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)

        if profile_form.is_valid():
            # 取得清洗后的合法数据
            profile_cd = profile_form.cleaned_data
            profile.phone = profile_cd['phone']
            profile.birth = profile_cd['birth']
            profile.bio = profile_cd['bio']

            # 如果 request.FILES 存在文件，则保存
            if 'avatar' in request.FILES:
                profile.avatar = profile_cd["avatar"]
            profile.save()
            return redirect(reverse('qxauth:edit_profile', kwargs={'user_id': user_id}))
        else:
            return HttpResponse('输入内容有误，请重新填写 ~ 喵')

    elif request.method == 'GET':
        #  通过 profile 的实例获取表单数据
        profile_form = ProfileForm(instance=profile)
        context = {
            'profile_form': profile_form,
            'profile': profile,
            'user': user
        }
        return render(request, 'registration/edit.html',context=context)


def user_frofile(request, user_id):
    """
    显示指定用户的个人主页 并展示其发布的博客
    """
    target_user = get_object_or_404(User, id=user_id)
    try:
        profile = target_user.profile
    except Profile.DoesNotExist:
        profile = None

    user_blogs = Blog.objects.filter(author=target_user).order_by('-pub_time')
    paginator = Paginator(user_blogs, 6)
    page_num = request.GET.get('page')
    blogs_paginated = paginator.get_page(page_num)

    is_following = False
    if request.user.is_authenticated and request.user != target_user:
        is_following = Follow.objects.filter(follower=request.user, followed=target_user).exists()

    followeds_count = target_user.following.count()
    followers_count_for_template = target_user.followers.count()
    blog_count = user_blogs.count()  # 获取博客数量
    garden_age = (timezone.now() - target_user.date_joined).days

    context = {
        'target_user': target_user,
        'profile': profile,
        'user_blogs': blogs_paginated,
        'blog_count': blog_count,
        'garden_age': garden_age,
        'is_following': is_following,
        'followeds_count': followeds_count,
        'followers_count': followers_count_for_template,
    }

    return render(request, 'registration/user_profile.html', context)

