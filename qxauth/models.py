from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True, verbose_name='用户')
    birth = models.DateField(blank=True, null=True, verbose_name='生日')
    phone = models.CharField(max_length=11, null=True, blank=True, verbose_name='手机号')
    avatar = models.ImageField(upload_to='avatar/%Y%m%d/', blank=True, verbose_name='头像')
    bio = models.TextField(max_length=500, blank=True, verbose_name='简介')

    def __str__(self):
        return 'user {}'.format(self.user.username)

    class Meta:
        verbose_name = '用户信息'
        verbose_name_plural = verbose_name
