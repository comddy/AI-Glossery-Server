from flask import Blueprint, request, jsonify
from sql_alchemy import db, StoryCollection
import requests
import json

content_bp = Blueprint('content', __name__)

@content_bp.route('/story_generation', methods=['POST'])
def story_generation():
    data = request.get_json()
    selected_words = data.get('selected_words', [])
    
    if not selected_words:
        return jsonify({'error': 'No words selected'}), 400
    
    # 这里应该调用AI API生成故事
    # 模拟故事生成
    story_content = f"这是一个关于{', '.join(selected_words)}的故事。"
    story_content_zh = f"这是一个关于{', '.join(selected_words)}的中文故事。"
    
    return jsonify({
        'title': 'Generated Story',
        'content': story_content,
        'content_zh': story_content_zh,
        'selected_words': selected_words
    })

@content_bp.route('/cover_image_generation', methods=['POST'])
def cover_image_generation():
    data = request.get_json()
    title = data.get('title')
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    # 这里应该调用AI API生成封面图片
    # 模拟返回图片URL
    cover_url = f"/static/cover_images/{title.replace(' ', '_')}.jpg"
    
    return jsonify({'cover_url': cover_url})

@content_bp.route('/word_image_generation', methods=['GET'])
def word_image_generation():
    word = request.args.get('word')
    
    if not word:
        return jsonify({'error': 'Word is required'}), 400
    
    # 这里应该调用AI API生成单词图片
    # 模拟返回图片URL
    image_url = f"/static/word_images/{word}.jpg"
    
    return jsonify({'image_url': image_url})

@content_bp.route('/generate_audio', methods=['GET'])
def generate_audio():
    text = request.args.get('text')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    # 这里应该调用TTS API生成音频
    # 模拟返回音频URL
    audio_url = f"/static/audio/{hash(text)}.mp3"
    
    return jsonify({'audio_url': audio_url})

@content_bp.route('/get_story_collections', methods=['GET'])
def get_story_collections():
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    stories = StoryCollection.query.filter_by(user_id=user_id).order_by(
        StoryCollection.created_at.desc()
    ).all()
    
    return jsonify([story.to_dict() for story in stories])

@content_bp.route('/collect_story', methods=['POST'])
def collect_story():
    data = request.get_json()
    user_id = data.get('user_id')
    title = data.get('title')
    content = data.get('content')
    content_zh = data.get('content_zh')
    selected_words = data.get('selected_words', [])
    
    if not all([user_id, title, content, content_zh]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    story = StoryCollection(
        user_id=user_id,
        title=title,
        content=content,
        content_zh=content_zh,
        selected_words=json.dumps(selected_words) if selected_words else None
    )
    
    db.session.add(story)
    db.session.commit()
    
    return jsonify(story.to_dict())