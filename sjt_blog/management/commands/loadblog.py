import os
import json

from django.core.management.base import BaseCommand
from sjt_blog.settings import BASE_DIR
from blog.models import Blog, User, BlogCategory

class Command(BaseCommand):
    """
    初始化数据库
    """
    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            dest='database',
            default='default',
            help='Specifies the database to load into'
        )

    def handle(self, *args, **options):
        database = options.get('database', 'default')
        data = None

        path = os.path.join(BASE_DIR, 'fixtures/blog_blog.json')
        with open(path, 'rb') as f:
            data = json.load(f)
        if not data:
            return

        for item in data:
            if Blog.objects.using(database).filter(id=item['fields']['id']).exists():
                print(f"Blog [{item['fields']['id']}] already exists, skipping...")

            # 处理外键
            if item['fields'].get('author_id'):
                item['fields']['author_id'] = User.objects.using(database).filter(id=item['fields']['author_id']).first().id
            if item['fields'].get('category_id'):
                item['fields']['category_id'] = BlogCategory.objects.using(database).filter(id=item['fields']['category_id']).first().id

            Blog.objects.using(database).create(**item['fields'])
            print(f"Blog [{item['fields']['id']}] created successfully!")