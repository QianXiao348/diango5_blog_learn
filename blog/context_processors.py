from .models import Notification


def notifications_context(request):
    """
    获取未读通知数量
    """
    unread_notifications_count = 0
    if request.user.is_authenticated:
        unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return {'unread_notifications_count': unread_notifications_count}
