from django import forms
from .models import Blog, BlogComment, BlogCategory


# 发表博客
class PubBlogForm(forms.ModelForm):
    class Meta:
        model = Blog 
        fields = ['title', 'content', 'category'] 

        # 可选：为字段添加样式和占位符，如果你的模型字段是 RichTextField，内容这里可能需要特定的widget
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入标题'}),
            'category': forms.Select(attrs={'class': 'form-select'}), # 下拉选择框
        }
        labels = {
            'title': '标题',
            'content': '内容',
            'category': '分类',
        }


class PubCommentForm(forms.ModelForm):
    class Meta:
        model = BlogComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': '请输入评论内容', 'rows': 3}),
            # 确保这里使用了 Textarea，以便 form.as_p 渲染出多行文本框
        }