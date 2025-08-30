import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from json import loads

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
    preferred_classification = db.Column(db.String(100), nullable=False) # 当前学习的词书(cet4,cet6,雅思,托福等)
    preferred_plan_daily = db.Column(db.Integer, default=20)
    wallet_key = db.Column(db.String(100), nullable=False, unique=True) # 钱包唯一标识
    word_power_amount = db.Column(db.Integer, nullable=False, default=0) # 词力值
    is_deleted = db.Column(db.Integer, nullable=False, default=0)

    stories = db.relationship('StoryCollection', backref='user')
    word_friend = db.relationship('WordFriend', backref='user')

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
    name = db.Column(db.String(100), nullable=False, unique=True)
    level = db.Column(db.Integer, nullable=False, default=0)
    exp = db.Column(db.Integer, nullable=False, default=0)
    nickname = db.Column(db.String(100)) # 用户自定义的名字

class Word(db.Model):
    __tablename__ = 'word'

    word_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    word_en = db.Column(db.String(100), nullable=False)
    word_cn = db.Column(db.String(100), nullable=False)
    example_sentense_en = db.Column(db.Text, nullable=False)
    example_sentense_cn = db.Column(db.Text, nullable=False)
    usphone = db.Column(db.String(50), nullable=False)
    picture = db.Column(db.String(255))  # 存储图片路径或URL
    classification = db.Column(db.String(100), nullable=False)

    # 与掌握表的关联
    mastered_by = db.relationship('UserWordMastery', back_populates='word')

    def to_dict(self):
        return {
            'word_id': self.word_id,
            'word_en': self.word_en,
            'word_cn': json.loads(self.word_cn),
            'usphone': self.usphone,
            'example_en': self.example_sentense_en,
            'example_cn': self.example_sentense_cn,
            'picture': self.picture,
            "speech": f"https://dict.youdao.com/dictvoice?audio={self.word_en}&type=2"
        }

class UserWordMastery(db.Model):
    __tablename__ = 'user_word_mastery'

    user_word_mastery_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey('word.word_id'), nullable=False)
    word_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.now())
    is_mastered = db.Column(db.Integer, nullable=False, default=1) # 0未掌握-进入生词本 1已掌握

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

class TradeTransaction(db.Model):
    __tablename__ = 'trade_transaction'

    trade_transaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender = db.Column(db.String(100), db.ForeignKey('user.wallet_key'), nullable=False)
    receiver = db.Column(db.String(100), db.ForeignKey('user.wallet_key'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    previous_hash = db.Column(db.String(100), nullable=False)
    current_hash = db.Column(db.String(100), nullable=False)

class StoryCollection(db.Model):
    __tablename__ = 'story_collection'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    content_zh = db.Column(db.Text, nullable=False)
    cover_img = db.Column(db.String(255))
    selected_words = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now())

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'content_zh': self.content_zh,
            'cover_img': self.cover_img,
            "selected_words": loads(self.selected_words) if self.selected_words else [],
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
