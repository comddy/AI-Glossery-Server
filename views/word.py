from flask import Blueprint, request, jsonify
from sql_alchemy import db, UserWordMastery, Word
from datetime import datetime

word_bp = Blueprint('word', __name__)

@word_bp.route('/word/mark-mastered', methods=['POST'])
def mark_word_mastered():
    data = request.get_json()
    user_id = data.get('user_id')
    word_id = data.get('word_id')
    
    if not user_id or not word_id:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # 检查是否已经存在记录
    existing = UserWordMastery.query.filter_by(
        user_id=user_id, word_id=word_id
    ).first()
    
    if existing:
        existing.is_mastered = 1
        existing.created_at = datetime.now()
    else:
        mastery = UserWordMastery(
            user_id=user_id,
            word_id=word_id,
            is_mastered=1
        )
        db.session.add(mastery)
    
    db.session.commit()
    return jsonify({'message': 'Word marked as mastered'})

@word_bp.route('/words', methods=['GET'])
def get_words():
    classification = request.args.get('classification', 'cet4')
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    
    words = Word.query.filter_by(classification=classification)\
        .offset(offset).limit(limit).all()
    
    return jsonify([word.to_dict() for word in words])

@word_bp.route('/today_mastered_words', methods=['GET'])
def get_today_mastered_words():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    today = datetime.now().date()
    mastered_words = db.session.query(Word).join(UserWordMastery).filter(
        UserWordMastery.user_id == user_id,
        db.func.date(UserWordMastery.created_at) == today,
        UserWordMastery.is_mastered == 1
    ).all()
    
    return jsonify([word.to_dict() for word in mastered_words])

@word_bp.route('/get_today_learned_words', methods=['GET'])
def get_today_learned_words():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    today = datetime.now().date()
    learned_words = db.session.query(Word).join(UserWordMastery).filter(
        UserWordMastery.user_id == user_id,
        db.func.date(UserWordMastery.created_at) == today
    ).all()
    
    return jsonify([word.to_dict() for word in learned_words])

@word_bp.route('/unknown_words', methods=['GET'])
def get_unknown_words():
    user_id = request.args.get('user_id')
    classification = request.args.get('classification', 'cet4')
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    # 获取用户未掌握的单词
    mastered_word_ids = db.session.query(UserWordMastery.word_id).filter(
        UserWordMastery.user_id == user_id,
        UserWordMastery.is_mastered == 1
    ).subquery()
    
    unknown_words = Word.query.filter(
        Word.classification == classification,
        ~Word.word_id.in_(mastered_word_ids)
    ).all()
    
    return jsonify([word.to_dict() for word in unknown_words])

@word_bp.route('/tourist_words', methods=['GET'])
def get_tourist_words():
    classification = request.args.get('classification', 'cet4')
    limit = int(request.args.get('limit', 20))
    
    words = Word.query.filter_by(classification=classification).limit(limit).all()
    return jsonify([word.to_dict() for word in words])