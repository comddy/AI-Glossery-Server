from flask import Flask
import uuid


def allowed_file(app: Flask, filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_random_filename(original_filename):
    """生成随机文件名并保留原始扩展名"""
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    random_name = str(uuid.uuid4())
    if ext:
        return f"{random_name}.{ext}"
    return random_name