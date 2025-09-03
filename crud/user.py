# 创建用户
from faker import Faker

from sql_alchemy import db, WordFriend, WordFriendLevelConfig, UserWordMastery, UserAchievement, Word
from utils.UserUtil import generate_hex_id


def create_user(**kwargs):
    from sql_alchemy import User
    user = User()
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    db.session.add(user)
    db.session.commit()
    return user


# 获取用户
def get_user_by_id(user_id):
    from sql_alchemy import User
    return User.query.get(user_id)


def get_user_by_username(username):
    from sql_alchemy import User
    return User.query.filter_by(username=username).first()


# 更新用户
def update_user(user_id, **kwargs):
    from sql_alchemy import User
    user = User.query.get(user_id)
    if not user:
        return None

    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)

    db.session.commit()
    return user


# 删除用户
def delete_user(user_id):
    from sql_alchemy import User
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return True
    return False

def get_user_info(user_id):
    from sql_alchemy import User
    # 查询用户关联的第一个单词伙伴（按关联ID排序）
    user = User.query.filter_by(user_id=user_id).first()
    word_friend = WordFriend.query.filter_by(user_id=user_id, name=user.word_friend_name).first()
    if not word_friend: # 该用户暂无单词伙伴
        return None

    next_level_config = WordFriendLevelConfig.query.filter_by(exp_level=word_friend.level + 1).first()
    mastery_word_count = db.session.query(UserWordMastery.word_id) \
        .filter(UserWordMastery.user_id == user_id) \
        .distinct() \
        .count()
    # 查询用户有学习记录的不同日期数
    learning_days = db.session.query(
        db.func.DATE(UserWordMastery.created_at)
    ).filter(
        UserWordMastery.user_id == user_id
    ).group_by(
        db.func.DATE(UserWordMastery.created_at)
    ).count()

    return {
        'word_friend': {
            'id': word_friend.word_friend_id,
            'name': word_friend.name,
            'level': word_friend.level,
            'exp': word_friend.exp,
            "next_level_require": next_level_config.exp_require,
            'nickname': word_friend.nickname
        },
        'user_info': {
            "learning_days": learning_days,
            "mastery_word_count": mastery_word_count,
            "word_power_amount": word_friend.user.word_power_amount,
        }
    }

def init_user(openid, session_key):
    # 新增用户信息
    username = Faker().user_name()  # 随机一个用户名
    user = create_user(
        username=username,
        wechat_openid=openid,
        wechat_session_key=session_key,
        wallet_key=generate_hex_id()
    )
    db.session.add(user)
    user_id = user.user_id

    default_achievements = [
        {
            "icon": '🔥',
            "name": '坚持不懈',
            "desc": '连续学习30天'
        },
        {
            "icon": '📚',
            "name": '词汇大师',
            "desc": '掌握500个单词',
        },
        {
            "icon": '⚡',
            "name": '速记能手',
            "desc": '单日记忆50个单词',
        },
        {
            "icon": '🚀',
            "name": '突破极限',
            "desc": '连续学习100天',
        }
    ]
    # 初始化成就
    for achievement in default_achievements:
        user_achievement = UserAchievement(
            user_id=user_id,
            name=achievement["name"],
            description=achievement["desc"],
            icon=achievement["icon"]
        )
        db.session.add(user_achievement)
    # 初始化词友
    new_word_friend = WordFriend(user_id=user_id, name="robot", nickname="robot")
    db.session.add(new_word_friend)
    db.session.commit()
    return user


def get_learning_percent(user_id, word_type):
    result = round(UserWordMastery.query.filter_by(user_id=user_id, word_type=word_type).count() / Word.query.filter_by(classification=word_type).count() * 100)
    return result