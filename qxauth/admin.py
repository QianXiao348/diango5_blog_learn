from django.contrib import admin
from .models import CaptchaModel, Profile
# Register your models here.

class CaptchaAdmin(admin.ModelAdmin):
    list_display = ['captcha', 'email', 'create_time']

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'birth', 'bio', 'avatar']

admin.site.register(CaptchaModel, CaptchaAdmin)
admin.site.register(Profile, ProfileAdmin)