from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'user'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    avatar_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now())
    updated_at = db.Column(db.DateTime, default=datetime.now(), onupdate=datetime.now())
    wechat_openid = db.Column(db.String(100), unique=True, nullable=False)
    wechat_session_key = db.Column(db.String(100), nullable=False)
    preferred_classification = db.Column(db.String(100), nullable=False)


class AIAgent(db.Model):
    __tablename__ = 'ai_agent'

    agent_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    system_prompt = db.Column(db.Text, nullable=False)
    avatar_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now())
    updated_at = db.Column(db.DateTime, default=datetime.now(), onupdate=datetime.now())


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    message_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('ai_agent.agent_id'), nullable=False)
    sender_type = db.Column(db.String(10), nullable=False)  # 'user' or 'agent'
    content = db.Column(db.Text, nullable=False)
    tokens = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now())


class WordFriend(db.Model):
    __tablename__ = 'word_friend'

    word_friend_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.Integer, nullable=False, default=0)
    exp = db.Column(db.Integer, nullable=False, default=0)

class Word(db.Model):
    __tablename__ = 'word'

    word_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    word_en = db.Column(db.String(100), nullable=False)
    word_cn = db.Column(db.String(100), nullable=False)
    example_sentense_en = db.Column(db.Text, nullable=False)
    example_sentense_cn = db.Column(db.Text, nullable=False)
    usphone = db.Column(db.String(50), nullable=False)
    picture = db.Column(db.String(255))  # 存储图片路径或URL

    # 与掌握表的关联
    mastered_by = db.relationship('UserWordMastery', back_populates='word')


class UserWordMastery(db.Model):
    __tablename__ = 'user_word_mastery'

    user_word_mastery_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey('word.word_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())

    # 定义关系
    user = db.relationship('User', backref='mastered_words')
    word = db.relationship('Word', back_populates='mastered_by')

class WordFriendLevelConfig(db.Model):
    __tablename__ = 'word_friend_level_config'

    word_friend_level_config_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exp_level = db.Column(db.Integer, nullable=False)
    exp_require = db.Column(db.Integer, nullable=False)

class UserAchievement(db.Model):
    __tablename__ = 'user_achievement'
    user_achievement_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
