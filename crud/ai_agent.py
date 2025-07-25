# 创建Agent
from sql_alchemy import AIAgent, db


def create_agent(name, system_prompt, **kwargs):
    agent = AIAgent(name=name, system_prompt=system_prompt, **kwargs)
    db.session.add(agent)
    db.session.commit()
    return agent


# 获取Agent
def get_all_agents():
    return AIAgent.query.all()


def get_agent_by_id(agent_id):
    return AIAgent.query.get(agent_id)


# 更新Agent
def update_agent(agent_id, **kwargs):
    agent = AIAgent.query.get(agent_id)
    if not agent:
        return None

    for key, value in kwargs.items():
        if hasattr(agent, key):
            setattr(agent, key, value)

    db.session.commit()
    return agent


# 删除Agent
def delete_agent(agent_id):
    agent = AIAgent.query.get(agent_id)
    if agent:
        db.session.delete(agent)
        db.session.commit()
        return True
    return False