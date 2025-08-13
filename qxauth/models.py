from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """个人信息"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True, verbose_name='用户')
    birth = models.DateField(blank=True, null=True, verbose_name='生日')
    SELECT_GENDER_CHOICES = (
        ('male', '男'),
        ('female', '女'),
    )
    gender = models.CharField(max_length=10, choices=SELECT_GENDER_CHOICES, default='female', verbose_name='性别')
    phone = models.CharField(max_length=11, null=True, blank=True, verbose_name='手机号')
    avatar = models.ImageField(upload_to='avatar/%Y%m%d/', blank=True, verbose_name='头像')
    bio = models.TextField(max_length=500, blank=True, verbose_name='简介')

    def __str__(self):
        return 'user {}'.format(self.user.username)

    class Meta:
        verbose_name = '用户信息'
        verbose_name_plural = verbose_name


class Follow(models.Model):
    """
    关注者和被关注者
    """
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='关注者'
    )
    followed = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='被关注者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='关注时间')

    class Meta:
        verbose_name = '关注'
        verbose_name_plural = verbose_name
        unique_together = ('follower', 'followed')

    def __str__(self):
        return '{} 关注了 {}'.format(self.follower.username, self.followed.username)
