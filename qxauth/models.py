from django.db import models


# 验证码
class CaptchaModel(models.Model):
    email = models.EmailField(unique=True)
    captcha = models.CharField(max_length=6)
    create_time = models.DateTimeField(auto_now_add=True)
    