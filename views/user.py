from flask import Blueprint, request, jsonify
from sql_alchemy import db, User
from werkzeug.utils import secure_filename
import os
from utils.CommonUtil import allowed_file, generate_random_filename
from crud.user import update_user, get_user_info

user_bp = Blueprint('user', __name__)

@user_bp.route('/upload-avatar', methods=['POST'])
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        random_filename = generate_random_filename(filename)
        file_path = os.path.join('static/upload', random_filename)
        file.save(file_path)
        
        user_id = request.form.get('user_id')
        user = User.query.get(user_id)
        if user:
            user.avatar_url = f'/static/upload/{random_filename}'
            db.session.commit()
            return jsonify({'avatar_url': user.avatar_url})
    
    return jsonify({'error': 'Invalid file'}), 400

@user_bp.route("/update-profile", methods=['POST'])
def update_profile():
    data = request.get_json()
    user_id = data.get('user_id')
    username = data.get('username')
    
    if not user_id or not username:
        return jsonify({'error': 'Missing parameters'}), 400
    
    user = update_user(user_id, username=username)
    if user:
        return jsonify({'message': 'Profile updated successfully'})
    
    return jsonify({'error': 'User not found'}), 404

@user_bp.route("/update_preferred", methods=['POST'])
def update_preferred():
    data = request.get_json()
    user_id = data.get('user_id')
    preferred_classification = data.get('preferred_classification')
    
    if not user_id or not preferred_classification:
        return jsonify({'error': 'Missing parameters'}), 400
    
    user = update_user(user_id, preferred_classification=preferred_classification)
    if user:
        return jsonify({'message': 'Preferred classification updated'})
    
    return jsonify({'error': 'User not found'}), 404

@user_bp.route("/update_plan_amount", methods=['POST'])
def update_plan_amount():
    data = request.get_json()
    user_id = data.get('user_id')
    preferred_plan_daily = data.get('preferred_plan_daily')
    
    if not user_id or not preferred_plan_daily:
        return jsonify({'error': 'Missing parameters'}), 400
    
    user = update_user(user_id, preferred_plan_daily=preferred_plan_daily)
    if user:
        return jsonify({'message': 'Daily plan updated'})
    
    return jsonify({'error': 'User not found'}), 404

@user_bp.route('/user/learning_percent', methods=['GET'])
def get_learning_percent_api():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    from crud.user import get_learning_percent
    percent = get_learning_percent(user_id)
    return jsonify({'learning_percent': percent})

@user_bp.route('/user/first_word_friend', methods=['GET'])
def get_first_word_friend():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    from sql_alchemy import WordFriend
    word_friend = WordFriend.query.filter_by(user_id=user_id).first()
    
    if word_friend:
        return jsonify({
            'word_friend_id': word_friend.word_friend_id,
            'name': word_friend.name,
            'level': word_friend.level,
            'exp': word_friend.exp,
            'nickname': word_friend.nickname
        })
    
    return jsonify({'error': 'Word friend not found'}), 404