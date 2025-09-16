import os
from celery import Celery

# 设置 Django 的 settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sjt_blog.settings') # 替换 'sjt_blog' 为你的项目名

app = Celery('diango5_blog')

# 使用 Django settings 配置 Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动从所有已安装的 Django app 中发现任务
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')