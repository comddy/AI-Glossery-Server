from flask import Blueprint, request, jsonify, send_file
from sql_alchemy import db, UserAchievement, User, WordFriendLevelConfig, WordFriend
from AchievementStrategy import calculate_streak

achievement_bp = Blueprint('achievement', __name__)

@achievement_bp.route("/add_exp", methods=['POST'])
def add_exp():
    data = request.get_json()
    word_friend_id = int(data.get('word_friend_id'))
    add_exp = int(data.get('add_exp'))
    current_level = int(data.get('level'))

    # 查询用户关联的特定词友精灵
    user_word_friend = WordFriend.query.filter_by(
        word_friend_id=word_friend_id
    ).first()

    level_config = WordFriendLevelConfig.query.filter_by(
        exp_level=current_level + 1
    ).first()

    added_exp = add_exp + user_word_friend.exp

    if added_exp / level_config.exp_require >= 1:
        # 升级，修改等级
        new_exp = added_exp % level_config.exp_require
        user_word_friend.exp = new_exp
        user_word_friend.level = current_level + 1
    else:
        user_word_friend.exp = added_exp

    user = db.session.query(User).filter_by(user_id=user_word_friend.user_id).first()
    user.word_power_amount += add_exp  # todo:这里暂时用加的经验代表词力值
    db.session.commit()  # 修改直接查到之后原地改了，直接commit

    return jsonify({
        'success': True,
        'message': f'添加经验，当前等级: {user_word_friend.level}',
        'data': {
            'level': user_word_friend.level,
            'exp': user_word_friend.exp
        }
    })

@achievement_bp.route("/achievements", methods=['GET'])
def get_achievements():
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'user_id is required'}), 400
    
    achievements = UserAchievement.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'success': True,
        'data': [{
            'achievement_id': achievement.user_achievement_id,
            'name': achievement.name,
            'desc': achievement.description,
            'icon': achievement.icon,
            'is_active': achievement.is_active
        } for achievement in achievements]
    })

@achievement_bp.route("/3dmodel", methods=['GET'])
def get_3d_model():
    model_name = request.args.get('model', type=str)
    # 返回文件
    return send_file(
        f"static/3dmodel/{model_name}.glb",
        as_attachment=True,  # 强制下载（False则尝试浏览器预览）
        download_name=f'{model_name}.glb'  # 下载时显示的文件名
    )