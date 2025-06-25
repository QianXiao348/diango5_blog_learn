from django.contrib import admin
from .models import BlogCategory, Blog, BlogComment


# Register your models here.
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

class BlogAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'author', 'pub_time', 'content']

class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ['blog', 'content', 'pub_time', 'author']

admin.site.register(BlogCategory, BlogCategoryAdmin)
admin.site.register(Blog, BlogAdmin)
admin.site.register(BlogComment, BlogCommentAdmin)