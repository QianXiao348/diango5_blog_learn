from .models import Notification, BlogCategory


def notifications_context(request):
    """
    提供全局分类列表、未读计数
    """
    categories = BlogCategory.objects.all().order_by('name')
    unread_notifications_count = 0
    if request.user.is_authenticated:
        unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return {
        'categories': categories,
        'unread_notifications_count': unread_notifications_count
    }
