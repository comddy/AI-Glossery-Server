from flask import Blueprint, request, jsonify
from sql_alchemy import db, ChatMessage, AIAgent
from crud.chat_message import insert_message, get_messages
from utils import CommonUtil

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        agent_id = data.get('agent_id')
        print(messages)

        # 构建系统提示
        agent = AIAgent.query.filter_by(agent_id=agent_id).first()
        system_prompt = agent.system_prompt
        # 构建完整消息数组
        full_messages = [{"role": "system", "content": system_prompt}]
        if isinstance(messages, list) and messages:
            for message in messages:
                full_messages.append({
                    "role": message['sender'],
                    "content": message['content']
                })

        response = CommonUtil.request_glm_model(full_messages)
        print(response.content)

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

@chat_bp.route('/chat/message/add', methods=['POST'])
def add_chat_message():
    data = request.get_json()

    # 验证必要字段
    required_fields = ['user_id', 'agent_id', 'sender_type', 'content']
    if not all(field in data for field in required_fields):
        return jsonify({
            'success': False,
            'message': '缺少必要字段: user_id, agent_id, sender_type 或 content'
        }), 400

    # 验证 sender_type
    if data['sender_type'] not in ['user', 'system', 'assistant']:
        return jsonify({
            'success': False,
            'message': 'sender_type 必须是 "user or system or assistant"'
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

    oralWelcome = "Hi there! 👋 Want to polish your English? I'm here to help! \
    					Just send me any sentence you’re unsure about. I'll check it for you, fix any grammar errors, and give you some extra examples so you can learn from it. \
    					Ready when you are! What's on your mind today?"
    commonWelcome = "Hello! I'm your AI word mentor. How can I assist you?"
    messages_data = [{
        'message_id': -1,
        'sender_type': 'assistant',
        'content': oralWelcome if agent_id == 7 else commonWelcome,
        'created_at': ''
    }]
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