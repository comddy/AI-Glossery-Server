from .auth import auth_bp
from .user import user_bp
from .word import word_bp
from .chat import chat_bp
from .ai_agent import ai_agent_bp
from .content import content_bp
from .transaction import transaction_bp
from .achievement import achievement_bp

def init_blueprints(app):
    """初始化所有蓝图"""
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(word_bp, url_prefix='/api')
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(ai_agent_bp, url_prefix='/api')
    app.register_blueprint(content_bp, url_prefix='/api')
    app.register_blueprint(transaction_bp, url_prefix='/api')
    app.register_blueprint(achievement_bp, url_prefix='/api')