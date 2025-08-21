from sql_alchemy import db, UserWordMastery, UserAchievement, User
from datetime import datetime, timedelta, date


def calculate_streak(user_id):
    # 获取用户所有学习日期（去重并转换为date对象）
    date_records = db.session.query(
        db.func.DATE(UserWordMastery.created_at).label('learning_date')
    ).filter(
        UserWordMastery.user_id == user_id
    ).distinct().all()

    # 提取日期并转换为date对象
    dates = []
    for record in date_records:
        try:
            # 如果数据库返回的是字符串
            if isinstance(record.learning_date, str):
                date_obj = datetime.strptime(record.learning_date, '%Y-%m-%d').date()
            # 如果数据库返回的是date对象
            elif isinstance(record.learning_date, date):
                date_obj = record.learning_date
            # 如果数据库返回的是datetime对象
            else:
                date_obj = record.learning_date.date()
            dates.append(date_obj)
        except Exception as e:
            continue

    # 按日期降序排序
    dates.sort(reverse=True)

    # 计算连续天数
    streak = 0
    today = date.today()
    prev_date = today

    for current_date in dates:
        delta = prev_date - current_date
        if delta.days == 1 or streak == 0:  # 连续或第一天
            streak += 1
            prev_date = current_date
        else:
            break

    return streak

def daily_achievement_check():
    users = User.query.all()
    for user in users:
        AchievementService.check_achievements(user.id)

class AchievementService:
    @staticmethod
    def check_achievements(user_id):
        """检查并更新用户成就状态"""
        achievements = [
            {
                'name': '坚持不懈', # 连续学习30天
                'check_func': AchievementService.check_30day_streak
            },
            {
                'name': '词汇大师', # 掌握500个单词
                'check_func': AchievementService.check_500_words
            },
            {
                'name': '速记能手', # 单日记忆50个单词
                'check_func': AchievementService.check_50_words_daily
            },
            {
                'name': '突破极限', # 连续学习100天
                'check_func': AchievementService.check_100day_streak
            }
        ]

        for achievement in achievements:
            if not UserAchievement.query.filter_by(
                    user_id=user_id,
                    name=achievement['name'],
                    is_active=True
            ).first():
                if achievement['check_func'](user_id):
                    AchievementService.unlock_achievement(
                        user_id,
                        achievement['name']
                    )

    @staticmethod
    def unlock_achievement(user_id, name):
        """解锁成就"""
        achievement = UserAchievement.query.filter_by(user_id=user_id, name=name).first()
        if achievement:
            achievement.is_active = True
            db.session.commit()

    @staticmethod
    def check_30day_streak(user_id):
        """检查连续学习30天"""
        streak = calculate_streak(user_id)  # 您的连续天数计算函数
        return streak >= 30

    @staticmethod
    def check_500_words(user_id):
        """检查掌握500个单词"""
        word_count = UserWordMastery.query.filter_by(user_id=user_id).count()
        return word_count >= 500

    @staticmethod
    def check_50_words_daily(user_id):
        """检查单日记忆50个单词"""
        today = datetime.now().date()
        count = UserWordMastery.query.filter(
            UserWordMastery.user_id == user_id,
            db.func.DATE(UserWordMastery.created_at) == today
        ).count()
        return count >= 50

    @staticmethod
    def check_100day_streak(user_id):
        """检查连续学习100天"""
        streak = calculate_streak(user_id)  # 您的连续天数计算函数
        return streak >= 100