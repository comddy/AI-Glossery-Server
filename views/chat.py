import os

from flask import Blueprint, request, jsonify
from sql_alchemy import db, ChatMessage, AIAgent
from crud.chat_message import insert_message, get_messages

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        chat_type = data.get('type', 'default')

        # 构建系统提示
        system_prompt = f"""你是一个{chat_type}风格的英语老师Kris，是一款英语学习软件"VocalBuddy:词友星球"的专任AI老师，你需要和学生进行互动，帮助他们学习英语。你在自我介绍时，请扮演好你的角色，不要和学生聊与学习无关的内容。
    请用生动有趣的方式教授英语知识，纠正学生的错误，并鼓励他们进步。你只有第一次回复时，需要先自我介绍。其他时候要尽可能简短回答。如果用户和你发中文，请引导他使用英语回答。"""

        # 构建完整消息数组
        full_messages = [{"role": "system", "content": system_prompt}]
        if isinstance(messages, list) and messages:
            full_messages.extend(messages)

        # 调用AI接口
        import requests
        headers = {
            'Authorization': f'Bearer {os.getenv("ZHIPUAI_API_KEY", "6eb6de30d0c6bab295e8730d7a8a71a0.gbET8XqExYOb99Ni")}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": "glm-4-flash-250414",
            "messages": full_messages
        }

        # 添加代理配置（如果需要）
        proxies = {
            'http': 'http://127.0.0.1:33210',
            'https': 'http://127.0.0.1:33210'
        } if os.getenv('USE_PROXY', 'false').lower() == 'true' else None

        response = requests.post(
            'https://open.bigmodel.cn/api/paas/v4/chat/completions',
            json=payload,
            headers=headers,
            proxies=proxies,
            timeout=15
        )

        if response.status_code != 200:
            raise Exception(f"AI接口请求失败，状态码: {response.status_code}")

        response_data = response.json()
        if not response_data or not response_data.get('choices') or not response_data['choices'][0].get('message'):
            raise Exception('AI接口返回数据格式不正确')

        return jsonify({
            "success": True,
            "reply": response_data['choices'][0]['message']
        })

    except Exception as e:
        error_detail = str(e)
        return jsonify({
            "success": False,
            "message": error_detail
        }), 500

@chat_bp.route('/chat/messages', methods=['POST'])
def get_chat_messages():
    data = request.get_json()

    # 验证必要字段
    required_fields = ['user_id', 'agent_id', 'sender_type', 'content']
    if not all(field in data for field in required_fields):
        return jsonify({
            'success': False,
            'message': '缺少必要字段: user_id, agent_id, sender_type 或 content'
        }), 400

    # 验证 sender_type
    if data['sender_type'] not in ['user', 'agent']:
        return jsonify({
            'success': False,
            'message': 'sender_type 必须是 "user" 或 "agent"'
        }), 400

    try:
        new_message = insert_message(
            user_id=data['user_id'],
            agent_id=data['agent_id'],
            sender_type=data['sender_type'],
            content=data['content'],
            tokens=data.get('tokens', 0)
        )
        return jsonify({
            'success': True,
            'message': '消息添加成功',
            'data': {
                'message_id': new_message.message_id,
                'created_at': new_message.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': '添加消息失败',
            'error': str(e)
        }), 500

@chat_bp.route('/chat/conversations', methods=['GET'])
def get_conversations():
    user_id = request.args.get('user_id', type=int)
    agent_id = request.args.get('agent_id', type=int)

    if not user_id or not agent_id:
        return jsonify({
            'success': False,
            'message': '必须提供 user_id 和 agent_id 参数'
        }), 400

    # 获取对话消息，按时间升序排列（最早的在前）
    messages = get_messages(
        user_id=user_id,
        agent_id=agent_id
    )

    messages_data = []
    for msg in messages:
        messages_data.append({
            'message_id': msg.message_id,
            'sender_type': msg.sender_type,
            'content': msg.content,
            'created_at': msg.created_at.strftime("%m月%d日 %H:%M")
        })

    return jsonify({
        'success': True,
        'data': messages_data,
        'user_id': user_id,
        'agent_id': agent_id
    })

@chat_bp.route('/latest_message_time', methods=['GET'])
def get_latest_message_time():
    # 获取user_id参数
    user_id = request.args.get('user_id', type=int)

    # 验证参数
    if not user_id:
        return jsonify({
            'success': False,
            'message': '必须提供user_id参数'
        }), 400

    try:
        # 查询用户最新的消息（包含关联的agent信息）
        latest_message = ChatMessage.query.filter_by(
            user_id=user_id
        ).join(
            AIAgent, ChatMessage.agent_id == AIAgent.agent_id
        ).add_columns(
            AIAgent.name
        ).order_by(
            ChatMessage.created_at.desc()
        ).first()

        if not latest_message:
            return jsonify({
                'success': False,
                'message': '该用户暂无聊天记录',
                'data': None
            })

        # 解构查询结果
        message, agent_name = latest_message

        # 转换为中国时区并格式化
        formatted_time = message.created_at.strftime("%Y年%m月%d日 %H:%M分")
        return jsonify({
            'success': True,
            'user_id': user_id,
            "data": {
                'time': formatted_time,
                'agent': agent_name
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': '获取最新消息时间失败',
            'error': str(e)
        }), 500