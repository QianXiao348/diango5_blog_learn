def avatar_context(request):
    if request.user.is_authenticated:
        try:
            avatar_url = request.user.profile.avatar.url
        except:
            avatar_url = '/static/21.png'  # 默认头像
        return {'user_avatar': avatar_url}
    return {}
