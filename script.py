from flask import Flask
from flask_cors import CORS
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # 自动加载.env文件
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not installed, .env file will not be loaded automatically")

from AchievementStrategy import daily_achievement_check
from sql_alchemy import db

from apscheduler.schedulers.background import BackgroundScheduler

# 导入蓝图
from views import init_blueprints


def create_app():
    app = Flask(__name__)
    app.secret_key = 'cyxqadmin666'

    # 从环境变量加载配置（需要FLASK_前缀）
    app.config.from_prefixed_env()
    
    # 设置默认配置（如果环境变量未设置）
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///chat_app.sqlite3')
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', True)
    app.config.setdefault('UPLOAD_FOLDER', 'static/upload')
    app.config.setdefault('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'})
    app.config.setdefault('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)  # 限制上传大小为16MB
    app.config.setdefault('SECRET_KEY', 'dev-secret-key-change-in-production')  # 会话密钥

    # 确保上传目录存在
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)

    # 初始化所有蓝图
    init_blueprints(app)

    # 确保在app上下文内初始化调度器
    with app.app_context():
        scheduler = BackgroundScheduler()
        scheduler.add_job(daily_achievement_check, 'cron', hour=0)  # 每天午夜运行
        scheduler.start()

    return app


app = create_app()

# 允许所有域名跨域访问
CORS(app)

@app.route('/')
def index():
    return "Hello World!"

if __name__ == '__main__':
    # 根据环境变量决定是否使用SSL
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'prod':
        # 生产环境使用SSL
        ssl_context = (
            os.environ.get('SSL_CERT_FILE', 'deepspring-tech.com.pem'),
            os.environ.get('SSL_KEY_FILE', 'deepspring-tech.com.key')
        )
        app.run(
            host='0.0.0.0',
            port=5000,
            ssl_context=ssl_context,
            debug=False
        )
    else:
        # 开发环境不使用SSL
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True
        )