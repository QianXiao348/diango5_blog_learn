from django import forms
from django.contrib.auth import get_user_model
from .models import Profile
from django.core.cache import cache

User = get_user_model()  #  使用Django自带的用户类

# 注册表单
class RegisterForm(forms.Form):
    username = forms.CharField(max_length=20, min_length=2, error_messages={
        'required':'请输入用户名',
        'max_length':'用户名长度不能超过20',
        'min_length':'用户名长度不能少于2'
    })
    email = forms.EmailField(error_messages={
        'required':'请输入邮箱',
        'invalid':'请输入一个正确的邮箱'
        })
    captcha = forms.CharField(max_length=6, min_length=6, error_messages={
        'required':'请输入验证码',
        'max_length':'验证码长度只能是6',
        'min_length':'验证码长度只能是6'
    })
    password = forms.CharField(max_length=20, min_length=6, error_messages={
        'required':'请输入密码',
        'max_length':'密码长度不能超过20',
        'min_length':'密码长度不能少于6'
    })
    password2 = forms.CharField(max_length=20, min_length=6, error_messages={
        'required': '请重复输入密码',
        'max_length': '密码长度不能超过20',
        'min_length': '密码长度不能少于6'
    })

    def clean(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password != password2:
            raise forms.ValidationError('两次密码不一致！')
        return self.cleaned_data

    # 检验邮箱是否存在数据库
    def clean_email(self):
        email = self.cleaned_data.get('email')  # 通过表单验证后提取 email 字段的值。
        exists = User.objects.filter(email=email).exists()  # 校验用户填写的邮箱是否已存在于数据库
        if exists:
            raise forms.ValidationError('邮箱已被注册！')
        return email

    # 检验验证码
    def clean_captcha(self):
        captcha = self.cleaned_data.get('captcha')
        email = self.cleaned_data.get('email') 
    
        real_captcha = cache.get(email)
        if not real_captcha or real_captcha != captcha:
            raise forms.ValidationError('验证码错误或已过期！')
        cache.delete(f'email_captcha:{email}') 
        return captcha
        

# 登录表单
class LoginForm(forms.Form):
    email = forms.EmailField(error_messages={
        'required':'请输入邮箱',
        'invalid':'请输入一个正确的邮箱'
        })
    password = forms.CharField(max_length=20, min_length=6, error_messages={
        'required':'请输入密码',
        'max_length':'密码长度不能超过20',
        'min_length':'密码长度不能少于6'
    })
    remeber = forms.IntegerField(required=False)


class ProfileForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=11,
        required=False,
        error_messages={
            'max_length': '手机号不能超过11位',
        }
    )
    class Meta:
        model = Profile
        fields = ['phone','birth','avatar','bio']
        widgets = {
            'birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            if len(phone) != 11:  # 同时检查是否为 11 位
                raise forms.ValidationError('手机号必须是11位数字')
        return phone