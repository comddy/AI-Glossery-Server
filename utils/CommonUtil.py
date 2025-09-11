import os

from flask import current_app
import uuid
import requests


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def generate_random_filename(original_filename):
    """生成随机文件名并保留原始扩展名"""
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    random_name = str(uuid.uuid4())
    if ext:
        return f"{random_name}.{ext}"
    return random_name

def request_glm_model(messages):
        # full_messages = [{"role": "user", "content": prompt}]

        # 调用AI接口
        headers = {
            'Authorization': f'Bearer {os.getenv("ZHIPUAI_API_KEY", "6eb6de30d0c6bab295e8730d7a8a71a0.gbET8XqExYOb99Ni")}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": "glm-4-flash-250414",
            "messages": messages
        }

        response = requests.post(
            'https://open.bigmodel.cn/api/paas/v4/chat/completions',
            json=payload,
            headers=headers,
            timeout=15
        )
        return response