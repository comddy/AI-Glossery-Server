from flask import Blueprint, request, jsonify
from sql_alchemy import db, ChatMessage, AIAgent
from crud.chat_message import insert_message, get_messages

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_id = data.get('user_id')
    agent_id = data.get('agent_id')
    content = data.get('content')
    
    if not all([user_id, agent_id, content]):
        return jsonify({'error': 'Missing parameters'}), 400
    
    # 保存用户消息
    user_message = insert_message(user_id, agent_id, 'user', content)
    
    # 获取AI代理的系统提示
    agent = AIAgent.query.get(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    # 这里应该调用AI API生成回复
    # 模拟AI回复
    ai_response = f"这是AI对'{content}'的回复"
    
    # 保存AI回复
    ai_message = insert_message(user_id, agent_id, 'agent', ai_response)
    
    return jsonify({
        'user_message': {
            'message_id': user_message.message_id,
            'content': user_message.content,
            'created_at': user_message.created_at.isoformat()
        },
        'ai_message': {
            'message_id': ai_message.message_id,
            'content': ai_message.content,
            'created_at': ai_message.created_at.isoformat()
        }
    })

@chat_bp.route('/chat/messages', methods=['POST'])
def get_chat_messages():
    data = request.get_json()
    user_id = data.get('user_id')
    agent_id = data.get('agent_id')
    limit = data.get('limit', 50)
    
    if not user_id or not agent_id:
        return jsonify({'error': 'Missing parameters'}), 400
    
    messages = get_messages(user_id, agent_id, limit)
    
    return jsonify([{
        'message_id': msg.message_id,
        'sender_type': msg.sender_type,
        'content': msg.content,
        'created_at': msg.created_at.isoformat()
    } for msg in messages])

@chat_bp.route('/chat/conversations', methods=['GET'])
def get_conversations():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    # 获取用户最近对话的AI代理
    recent_agents = db.session.query(
        ChatMessage.agent_id,
        AIAgent.name,
        AIAgent.avatar_url,
        db.func.max(ChatMessage.created_at).label('last_message_time')
    ).join(AIAgent, ChatMessage.agent_id == AIAgent.agent_id)\
     .filter(ChatMessage.user_id == user_id)\
     .group_by(ChatMessage.agent_id, AIAgent.name, AIAgent.avatar_url)\
     .order_by(db.desc('last_message_time'))\
     .all()
    
    return jsonify([{
        'agent_id': agent_id,
        'name': name,
        'avatar_url': avatar_url,
        'last_message_time': last_message_time.isoformat() if last_message_time else None
    } for agent_id, name, avatar_url, last_message_time in recent_agents])

@chat_bp.route('/latest_message_time', methods=['GET'])
def get_latest_message_time():
    user_id = request.args.get('user_id')
    agent_id = request.args.get('agent_id')
    
    if not user_id or not agent_id:
        return jsonify({'error': 'Missing parameters'}), 400
    
    latest_message = ChatMessage.query.filter_by(
        user_id=user_id, agent_id=agent_id
    ).order_by(ChatMessage.created_at.desc()).first()
    
    if latest_message:
        return jsonify({'latest_time': latest_message.created_at.isoformat()})
    
    return jsonify({'latest_time': None})