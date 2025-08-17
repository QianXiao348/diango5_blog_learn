from django.contrib import admin
from .models import BlogCategory, Blog, BlogComment, Notification, ModerationLog


# Register your models here.
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']


class BlogAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'author', 'pub_time', 'content']


class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ['blog', 'content', 'pub_time', 'author']


class NotificationAdmin(admin.ModelAdmin):
    list_display = ['verb', 'actor', 'recipient', 'target_url', 'content', 'description', 'is_read', 'created_at']


class ModerationLogAdmin(admin.ModelAdmin):
    list_display = ['author', 'content_type', 'content_id', 'original_content', 'reason', 'status', 'created_at']


admin.site.register(BlogCategory, BlogCategoryAdmin)
admin.site.register(Blog, BlogAdmin)
admin.site.register(BlogComment, BlogCommentAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(ModerationLog, ModerationLogAdmin)
