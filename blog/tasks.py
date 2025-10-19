from celery import shared_task
from django.utils import timezone
from django.urls import reverse
from django.db import transaction

from .models import ModerationLog, Blog, Notification
from .moderation import moderate_content


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=2, retry_kwargs={'max_retries': 3})
def run_blog_moderation(self, log_id: int):
    """
    根据 ModerationLog 执行异步审核：
    - 新发布：创建 Blog 并通知作者；
    - 编辑更新：更新 Blog 并通知作者；
    - AI 未通过：保持为 pending，填写原因并加入人工审核队列，同时通知作者。
    返回简单结果字典，便于调试。
    """
    try:
        log = ModerationLog.objects.get(id=log_id)
    except ModerationLog.DoesNotExist:
        return {'status': 'error', 'msg': 'ModerationLog not found'}

    # 解析原始内容（格式："标题: xxx\n内容: yyy"）
    title, content = '', ''
    try:
        lines = log.original_content.split('\n', 1)
        title = lines[0].replace('标题: ', '').strip()
        content = lines[1].replace('内容: ', '').strip() if len(lines) > 1 else ''
    except Exception:
        title = log.original_content[:200]
        content = log.original_content

    # 执行审核（规则 + 模型）
    title_safe, title_msg = moderate_content(title)
    content_safe, content_msg = moderate_content(content)

    if title_safe and content_safe:
        # 审核通过：创建或更新博客
        with transaction.atomic():
            if log.content_id:
                # 编辑更新
                blog = Blog.objects.select_for_update().get(id=log.content_id)
                blog.title = title
                blog.content = content
                if log.category:
                    blog.category = log.category
                blog.pub_time = timezone.now()
                blog.save()
                target_url = reverse('blog:blog_detail', args=[blog.id])
            else:
                # 新发布
                blog = Blog.objects.create(
                    author=log.author,
                    category=log.category,
                    title=title,
                    content=content,
                    pub_time=timezone.now()
                )
                target_url = reverse('blog:blog_detail', args=[blog.id])
                log.content_id = blog.id

            log.status = 'approved'
            log.reviewed_at = timezone.now()
            log.save()

        # 通知作者审核通过
        Notification.objects.create(
            recipient=log.author,
            actor=None,
            verb='博客发布审核',
            content='审核通过',
            description='你的文章已通过审核并发布成功。',
            target_url=target_url
        )
        return {'status': 'approved', 'blog_id': log.content_id}

    else:
        # AI 初审未通过：加入人工审核队列（保持 pending），记录原因并通知作者
        reason_parts = []
        if not title_safe:
            reason_parts.append(f'标题：{title_msg}')
        if not content_safe:
            reason_parts.append(f'内容：{content_msg}')

        # 强制保证：AI 未通过绝不直接拒绝，始终进入人工审核队列
        log.status = 'pending'
        log.reviewed_at = None
        log.reason = 'AI 初审未通过：' + '; '.join([p for p in reason_parts if p.strip()])
        log.flagged_by_ai = True
        log.save()

        Notification.objects.create(
            recipient=log.author,
            actor=None,
            verb='博客发布审核',
            content='进入人工审核队列',
            description=f'AI 初审未通过，已提交人工复核。原因：{log.reason}',
            target_url=reverse('blog:index')
        )
        return {'status': 'pending', 'msg': 'AI 初审未通过，已加入人工审核队列'}