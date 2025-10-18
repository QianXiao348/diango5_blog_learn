# 智能审核博客项目

## 🚀 项目简介

这是一个基于 Django 的智能审核博客项目，集成了用户认证、文章发布、评论、AI 内容审核以及通知系统。项目旨在提供一个安全、高效的博客平台，确保内容的合规性。

## 🛠️ 技术栈

- **后端**: Python 3.10+, Django, Django REST Framework (DRF), Celery, Redis
- **数据库**: MySQL
- **前端**: HTML, CSS (Bootstrap 5), JavaScript (jQuery)
- **内容审核**: 自定义AI模型 (可能通过 Celery 异步调用)
- **部署**: Docker, Nginx, Gunicorn, Uvicorn (FastAPI 部分)

## ✨ 主要功能模块

1.  **用户认证系统 (qxauth)**:
    *   用户注册、登录、注销
    *   个人资料编辑 (头像、性别、电话、生日、简介、用户名)
    *   密码修改、重置
    *   用户关注/取关功能

2.  **博客文章管理 (blog)**:
    *   文章发布、编辑、删除
    *   文章分类、标签
    *   文章详情展示、热门文章
    *   评论功能
    *   AI 内容审核：对发布文章内容进行智能审核，确保合规性。

3.  **消息通知系统 (blog)**:
    *   实时通知用户相关事件（如评论、关注、审核结果）

4.  **聊天功能 (chat - 待完善)**:
    *   用户之间实时聊天（预留功能）

## ⚙️ 安装与运行

### 1. 克隆项目

```bash
git clone <your-repository-url>
cd AIBlogDjango
```

### 2. 创建虚拟环境并安装依赖

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate # Linux/macOS

pip install -r requirements.txt
```

### 3. 数据库配置

项目使用 MySQL 数据库。请在 `sjt_blog/settings.py` 中配置数据库连接信息，或者使用环境变量。

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'aiblog',
        'USER': '<YOUR_DB_USER>',
        'PASSWORD': '<YOUR_DB_PASSWORD>',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```

### 4. 运行数据库迁移

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. 创建超级用户

```bash
python manage.py createsuperuser
```

### 6. 运行开发服务器

```bash
python manage.py runserver
```

项目将在 `http://127.0.0.1:8000/` 运行。

### 7. Celery (异步任务)

如果需要运行异步任务（如邮箱注册），请确保 Redis 服务器正在运行，然后启动 Celery Worker:

```bash
celery -A sjt_blog worker -l info
```

## 📝 API 文档

（根据实际项目接口，这里会生成具体的 API 文档，例如用户登录、注册、文章发布等接口。）

## 🐳 Docker 部署 (待生成)

（当需要部署时，这里将包含 `Dockerfile` 和 `docker-compose.yml` 的配置以及部署说明。）

## 🛡️ 性能与安全

- **数据库优化**: 合理的索引设计。
- **缓存策略**: 使用 Redis 缓存热门数据。
- **安全防护**: JWT 鉴权、CORS 配置、SQL 注入防护、XSS 防护等。

## 🤝 贡献

欢迎贡献代码，请提交 Pull Request。
