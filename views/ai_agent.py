from flask import Blueprint, request, jsonify
from sql_alchemy import db, AIAgent
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
        return jsonify({'error': 'Missing required parameters'}), 400
    
    agent = create_agent(name, description, system_prompt, avatar_url)
    
    return jsonify({
        'agent_id': agent.agent_id,
        'name': agent.name,
        'description': agent.description,
        'avatar_url': agent.avatar_url
    })

@ai_agent_bp.route("/model/list", methods=['GET'])
def get_model_list():
    agents = AIAgent.query.filter_by(is_active=True).all()
    
    return jsonify([{
        'agent_id': agent.agent_id,
        'name': agent.name,
        'description': agent.description,
        'avatar_url': agent.avatar_url,
        'system_prompt': agent.system_prompt
    } for agent in agents])

@ai_agent_bp.route("/model/switch", methods=['POST'])
def switch_model():
    data = request.get_json()
    user_id = data.get('user_id')
    agent_id = data.get('agent_id')
    
    if not user_id or not agent_id:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # 这里应该实现模型切换逻辑
    # 目前只是返回成功
    return jsonify({'message': 'Model switched successfully'})

@ai_agent_bp.route("/model/buy", methods=['POST'])
def buy_model():
    data = request.get_json()
    user_id = data.get('user_id')
    agent_id = data.get('agent_id')
    
    if not user_id or not agent_id:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # 这里应该实现购买逻辑
    # 目前只是返回成功
    return jsonify({'message': 'Model purchased successfully'})

@ai_agent_bp.route("/model/edit", methods=['POST'])
def edit_model():
    data = request.get_json()
    agent_id = data.get('agent_id')
    name = data.get('name')
    description = data.get('description')
    system_prompt = data.get('system_prompt')
    avatar_url = data.get('avatar_url')
    
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    
    agent = AIAgent.query.get(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    if name:
        agent.name = name
    if description:
        agent.description = description
    if system_prompt:
        agent.system_prompt = system_prompt
    if avatar_url:
        agent.avatar_url = avatar_url
    
    db.session.commit()
    
    return jsonify({
        'agent_id': agent.agent_id,
        'name': agent.name,
        'description': agent.description,
        'avatar_url': agent.avatar_url
    })