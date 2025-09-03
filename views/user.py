from flask import Blueprint, request, jsonify, current_app

from sql_alchemy import db, User
from werkzeug.utils import secure_filename
import os
from utils.CommonUtil import allowed_file, generate_random_filename
from crud.user import update_user, get_user_info, get_learning_percent

user_bp = Blueprint('user', __name__)

@user_bp.route('/upload-avatar', methods=['POST'])
def upload_avatar():
    """图片上传接口"""
    # 检查是否有文件部分
    if 'file' not in request.files:
        return jsonify({'error': '没有文件部分'}), 400

    file = request.files['file']
    user_id = request.form.get('user_id')

    # 检查是否选择了文件
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    # 检查文件类型是否允许
    if file and allowed_file(file.filename):
        # 生成随机文件名
        random_filename = generate_random_filename(file.filename)
        # 安全地处理文件名
        safe_filename = secure_filename(random_filename)
        file_path = current_app.config['UPLOAD_FOLDER'] + '/' + safe_filename

        user = User.query.filter_by(user_id=user_id).first()
        # 删除之前的头像
        if user.avatar_url and os.path.exists(user.avatar_url):
            os.remove(user.avatar_url)

        # 保存文件
        file.save(file_path)
        # 更新数据库
        user.avatar_url = file_path
        db.session.commit()

        # 返回成功响应
        return jsonify({
            'success': True,
            'message': '头像上传成功',
            'url': file_path
        }), 200
    else:
        return jsonify({'error': '不允许的文件类型'}), 400


@user_bp.route("/update-profile", methods=['POST'])
def update_profile():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        username = data.get('username')
        email = data.get('email')

        user = User.query.filter_by(user_id=user_id).first()
        user.username = username
        user.email = email
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '更新成功',
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e),
        }), 500

@user_bp.route("/update_preferred", methods=['POST'])
def update_preferred():
    try:
        data = request.get_json()
        print(data)
        user_id = data['user_id']
        preferred = data['preferred']
        preferred_plan_daily = data['preferred_plan_daily']

        user = User.query.filter_by(user_id=user_id).first()
        user.preferred_classification = preferred
        user.preferred_plan_daily = preferred_plan_daily
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Preferred classification book updated"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@user_bp.route("/update_plan_amount", methods=['POST'])
def update_plan_amount():
    data = request.get_json()
    print(data)
    user_id = data['user_id']
    amount = data['amount']

    user = User.query.filter_by(user_id=user_id).first()
    user.preferred_plan_daily = amount
    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Preferred plan amount updated",
        "data": amount
    })

@user_bp.route('/user/learning_percent', methods=['GET'])
def get_learning_percent_api():
    # 获取数
    user_id = request.args.get('user_id', type=int)
    word_type = request.args.get('word_type', type=str)

    # 验证参数
    if not user_id and not word_type:
        return jsonify({
            'success': False,
            'message': '参数有误'
        }), 400

    percent = get_learning_percent(user_id, word_type)
    return jsonify({
        'success': True,
        'data': percent
    })

@user_bp.route('/user/first_word_friend', methods=['GET'])
def get_first_word_friend():
    # 获取user_id参数
    user_id = request.args.get('user_id', type=int)

    # 验证参数
    if not user_id:
        return jsonify({
            'success': False,
            'message': '必须提供user_id参数'
        }), 400

    user_info = get_user_info(user_id)
    if user_info:
        return jsonify({
            'success': True,
            'data': user_info
        })
    else:
        return jsonify({
            'success': False,
            "msg": "获取用户信息失败，请联系管理员"
        })