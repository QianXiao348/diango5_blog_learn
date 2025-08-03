from django.db import models
from django.contrib.auth import get_user_model
from mptt.models import MPTTModel, TreeForeignKey

User = get_user_model()


class BlogCategory(models.Model):
    """
    博客分类
    """
    name = models.CharField(max_length=200, verbose_name='分类名称')

    class Meta:
        verbose_name = '博客分类'
        verbose_name_plural = verbose_name
        ordering = ['name']


class Blog(models.Model):
    """
    博客
    """
    title = models.CharField(max_length=200, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    pub_time = models.DateTimeField(auto_now=True, verbose_name='发布时间')
    category = models.ForeignKey(BlogCategory, on_delete=models.CASCADE, verbose_name='分类')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='作者')
    view_count = models.PositiveIntegerField(default=0, verbose_name='浏览量')
    like_count = models.PositiveIntegerField(default=0, verbose_name='点赞数')

    class Meta:
        verbose_name = '博客'
        verbose_name_plural = verbose_name
        ordering = ['-pub_time']


class BlogLike(models.Model):
    """
    点赞
    """
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, verbose_name='点赞的博客')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='点赞的用户')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='点赞时间')

    class Meta:
        verbose_name = '博客点赞'
        verbose_name_plural = verbose_name
        unique_together = ('blog', 'user')


class BlogComment(MPTTModel):
    """
    评论
    """
    content = models.TextField(max_length=200, verbose_name='内容')
    pub_time = models.DateTimeField(auto_now_add=True, verbose_name='评论时间')
    blog = models.ForeignKey(Blog,
                             on_delete=models.CASCADE,
                             related_name='comments',
                             verbose_name='所属博客'
                             )
    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               verbose_name='评论的作者'
                               )
    parent = TreeForeignKey('self',
                            on_delete=models.CASCADE,
                            null=True,
                            blank=True,
                            related_name='children',
                            verbose_name='回复的评论')
    reply_to = models.ForeignKey(User,
                                 on_delete=models.CASCADE,
                                 null=True,
                                 blank=True,
                                 related_name='replyers',
                                 verbose_name='回复的作者'
                                 )

    class MPTTMeta:
        order_insertion_by = ['-pub_time']

    class Meta:
        verbose_name = '博客评论'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.content[:20]


class Notification(models.Model):
    """
    通知
    """
    content = models.TextField(max_length=200, verbose_name='内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='通知时间')
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='接收者'
    )
    # 发送通知的用户 (例如评论通知可以有评论者)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='触发者'
    )
    verb = models.CharField(max_length=200, verbose_name='通知类型')
    description = models.TextField(blank=True, verbose_name='描述')
    is_read = models.BooleanField(default=False, verbose_name='是否已读')
    target_url = models.URLField(max_length=500, blank=True, verbose_name='目标url')

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient.username} - {self.verb} - {self.content[:30]}'
