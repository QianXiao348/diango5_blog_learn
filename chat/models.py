from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Conversation(models.Model):
    """
    对话会话
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=255, blank=True, verbose_name='标题')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    def __str__(self):
        return f"{self.user.username}'s conversation"

    class Meta:
        verbose_name = '对话会话'
        verbose_name_plural = '对话会话'
        ordering = ['-created_at']


class Message(models.Model):
    """
    对话消息
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', verbose_name="所属会话")
    content = models.TextField(verbose_name='内容')
    SELECT = [
        ('user', '用户'),
        ('assistant', '助手'),
    ]
    role = models.CharField(max_length=20, choices=SELECT, verbose_name='角色')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    def __str__(self):
        return f"{self.role}: {self.content[:30]}"

    class Meta:
        verbose_name = "对话消息"
        verbose_name_plural = verbose_name
        ordering = ['created_at']