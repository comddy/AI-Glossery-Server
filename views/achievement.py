from flask import Blueprint, request, jsonify
from sql_alchemy import db, UserAchievement
from AchievementStrategy import calculate_streak

achievement_bp = Blueprint('achievement', __name__)

@achievement_bp.route("/add_exp", methods=['POST'])
def add_exp():
    data = request.get_json()
    user_id = data.get('user_id')
    exp_amount = data.get('exp_amount', 0)
    
    if not user_id or exp_amount <= 0:
        return jsonify({'error': 'Invalid parameters'}), 400
    
    from sql_alchemy import WordFriend
    word_friend = WordFriend.query.filter_by(user_id=user_id).first()
    
    if not word_friend:
        return jsonify({'error': 'Word friend not found'}), 404
    
    word_friend.exp += exp_amount
    
    # 检查是否升级
    from sql_alchemy import WordFriendLevelConfig
    level_configs = WordFriendLevelConfig.query.order_by(WordFriendLevelConfig.exp_level).all()
    
    new_level = word_friend.level
    for config in level_configs:
        if word_friend.exp >= config.exp_require and config.exp_level > word_friend.level:
            new_level = config.exp_level
    
    if new_level > word_friend.level:
        word_friend.level = new_level
    
    db.session.commit()
    
    return jsonify({
        'word_friend_id': word_friend.word_friend_id,
        'current_exp': word_friend.exp,
        'current_level': word_friend.level
    })

@achievement_bp.route("/achievements", methods=['GET'])
def get_achievements():
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    achievements = UserAchievement.query.filter_by(user_id=user_id).all()
    
    # 计算连续学习天数
    streak = calculate_streak(user_id)
    
    return jsonify({
        'achievements': [{
            'achievement_id': achievement.user_achievement_id,
            'name': achievement.name,
            'description': achievement.description,
            'icon': achievement.icon,
            'is_active': achievement.is_active
        } for achievement in achievements],
        'learning_streak': streak
    })

@achievement_bp.route("/3dmodel", methods=['GET'])
def get_3d_model():
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    from sql_alchemy import WordFriend
    word_friend = WordFriend.query.filter_by(user_id=user_id).first()
    
    if not word_friend:
        return jsonify({'error': 'Word friend not found'}), 404
    
    # 根据词友等级返回不同的3D模型
    model_url = f"/static/3dmodels/level_{word_friend.level}.glb"
    
    return jsonify({
        'model_url': model_url,
        'level': word_friend.level
    })

@achievement_bp.route("/test", methods=['GET'])
def test_endpoint():
    return jsonify({'message': 'Test endpoint works!'})