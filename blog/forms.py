from django import forms
from .models import BlogComment

# 发表博客
class PubBlogForm(forms.Form):
    title = forms.CharField(max_length=200, min_length=2)
    content = forms.CharField(min_length=2)
    category = forms.IntegerField()


class PubCommentForm(forms.ModelForm):
    class Meta:
        model = BlogComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': '请输入评论内容', 'rows': 3}),
            # 确保这里使用了 Textarea，以便 form.as_p 渲染出多行文本框
        }