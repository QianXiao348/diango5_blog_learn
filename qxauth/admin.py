from django.contrib import admin
from .models import Profile, Follow
# Register your models here.


class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'birth', 'bio', 'avatar']
    
    
class FollowAdmin(admin.ModelAdmin):
    list_display = ['follower', 'followed', 'created_at']
    
    
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Follow, FollowAdmin)