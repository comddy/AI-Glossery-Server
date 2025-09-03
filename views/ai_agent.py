import os

from flask import Blueprint, request, jsonify
from sql_alchemy import db, AIAgent, WordFriend, User, WordFriendLevelConfig
from crud.ai_agent import create_agent

ai_agent_bp = Blueprint('ai_agent', __name__)

@ai_agent_bp.route("/add/agent", methods=['POST'])
def add_agent():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    system_prompt = data.get('system_prompt')
    avatar_url = data.get('avatar_url')
    
    if not all([name, system_prompt]):
        return jsonify({'success': False, 'message': 'Missing required parameters'}), 400
    
    agent = create_agent(name, description, system_prompt, avatar_url)
    
    return jsonify({
        'agent_id': agent.agent_id,
        'name': agent.name,
        'description': agent.description,
        'avatar_url': agent.avatar_url
    })

@ai_agent_bp.route("/model/list", methods=['GET'])
def get_model_list():
    user_id = request.args.get('user_id', type=int)
    if user_id is None:
        return jsonify({
            'success': False,
            'message': '参数异常'
        }), 400
    models = os.listdir("static/3dmodel")
    models = [{
        'id': i+1,
        'name': name[:-4],
        'is_owned': 1 if WordFriend.query.filter_by(user_id=user_id, name=name[:-4]).first() else 0,
        'price': 1000
    } for i, name in enumerate(models)]
    return jsonify({
        'success': True,
        'data': models
    })

@ai_agent_bp.route("/model/switch", methods=['POST'])
def switch_model():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        model_name = data.get('name')
        if not user_id or not model_name:
            return jsonify({
                'success': False,
                'message': '参数错误'
            }), 400

        word_friend = WordFriend.query.filter_by(user_id=user_id, name=model_name).first()
        result = User.query.filter_by(user_id=user_id).update({
            'word_friend_name': word_friend.name
        }) # 同步更新用户当前选择词友
        db.session.commit()
        next_level_config = WordFriendLevelConfig.query.filter_by(exp_level=word_friend.level + 1).first()
        if result > 0:
            return jsonify({
                'success': True,
                'data': {
                    'nickname': word_friend.nickname,
                    'level': word_friend.level,
                    'exp': word_friend.exp,
                    "next_level_require": next_level_config.exp_require,
                },
                'message': '切换成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '没有找到匹配的记录或更新失败'
            })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

@ai_agent_bp.route("/model/buy", methods=['POST'])
def buy_model():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        model_name = data.get('name')
        if not user_id or not model_name:
            return jsonify({
                'success': False,
                'message': '参数错误'
            }), 400

        db_word_friend = WordFriend.query.filter_by(user_id=user_id, name=model_name).first()
        if db_word_friend:
            return jsonify({
                'success': False,
                'message': '已持有，请勿重复添加'
            })
        word_friend = WordFriend(user_id=user_id, name=model_name, nickname=model_name)
        db.session.add(word_friend)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '购买成功!',
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

@ai_agent_bp.route("/model/edit", methods=['POST'])
def edit_model():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        name = data.get('name')
        nickname = data.get('nickname')
        if not user_id or not nickname:
            return jsonify({
                'success': False,
                'message': '参数错误'
            }), 400
        word_friend = WordFriend.query.filter_by(user_id=user_id, name=name).first()
        word_friend.nickname = nickname
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '修改成功!',
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })