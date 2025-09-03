import os

# 从环境变量获取配置，如果没有则使用默认值
worker = int(os.environ.get('GUNICORN_WORKERS', 2))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gevent')
worker_connections = int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', 50))  # 限制并发连接数
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:5000')
keyfile = os.environ.get('GUNICORN_KEYFILE', 'deepspring-tech.com.key')
certfile = os.environ.get('GUNICORN_CERTFILE', 'deepspring-tech.com.pem')
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))  # 避免长请求被杀死