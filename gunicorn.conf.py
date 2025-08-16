worker = 2
worker_class = "gevent"
worker_connections = 50  # 限制并发连接数
preload_app = True  # 避免重复加载模型
bind = "0.0.0.0:5000"
keyfile = "deepspring-tech.com.key"
certfile = "deepspring-tech.com.pem"
timeout = 120  # 避免长请求被杀死