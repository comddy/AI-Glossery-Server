# 添加消息
from datetime import datetime
from sql_alchemy import ChatMessage, db


def insert_message(user_id, agent_id, sender_type, content, tokens=0):
    message = ChatMessage(
        user_id=user_id,
        agent_id=agent_id,
        sender_type=sender_type,
        content=content,
        tokens=tokens
    )
    db.session.add(message)
    db.session.commit()

    return message



# 获取会话的所有消息
def get_messages(user_id, agent_id, limit=None):
    query = ChatMessage.query.filter_by(user_id=user_id, agent_id=agent_id).order_by(ChatMessage.created_at.asc())
    if limit:
        query = query.limit(limit)
    return query.all()


# 归档消息
def archive_message(message_id):
    message = ChatMessage.query.get(message_id)
    if message:
        message.is_archived = True
        db.session.commit()
        return True
    return False