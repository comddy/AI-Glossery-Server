import json

import requests
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import select, func, join, and_

from AchievementStrategy import AchievementService
from sql_alchemy import db, UserWordMastery, Word
from datetime import datetime

from utils import CommonUtil

word_bp = Blueprint('word', __name__)

@word_bp.route('/rootsAndAffixes', methods=['GET'])
def chat():
    try:
        word = request.args.get('word')

        # 构建系统提示
        prompt = """生成英文单词 `%s` 相关的词根词缀，只需要词根词缀的拆解和完整的解释，结构化输出成json，示例如下：
                {
                    "prefix": {
                        "part": "",
                        "explanation": ""
                    },
                    "root": {
                        "part": "",
                        "explanation": ""
                    },
                    "suffix": {
                        "part": "",
                        "explanation": ""
                    }
                }
                prefix是前缀，root是词根，suffix是后缀，如果有的话就填入，输出只需要json,如果存在对应的词根词缀里面的内容保持json格式里面的内容只能用单引号包含，不要markdown格式，用中文回复，其他多的解释不要。
                """ % word

        # 构建完整消息数组
        full_messages = [{"role": "user", "content": prompt}]

        response = CommonUtil.request_glm_model(full_messages)

        if response.status_code != 200:
            raise Exception(f"AI接口请求失败，状态码: {response.status_code}")

        response_data = response.json()
        if not response_data or not response_data.get('choices') or not response_data['choices'][0].get('message'):
            raise Exception('AI接口返回数据格式不正确')

        raw_data = response_data['choices'][0]['message']['content'][7:-3].strip()
        print(raw_data)
        json_data = json.loads(raw_data)
        return jsonify({
            "success": True,
            "data": json_data
        })

    except Exception as e:
        error_detail = str(e)
        return jsonify({
            "success": False,
            "message": error_detail
        }), 500

@word_bp.route('/word/mark-mastered', methods=['POST'])
def mark_word_mastered():
    """
    标记用户已掌握单词
    POST /api/mark-mastered
    请求体: {
        "user_id": 123,
        "word_id": 456,
        "word_type": 'CET4',
        "is_mastered": 1
    }
    """
    data = request.get_json()

    # 验证必需参数
    if not data or 'user_id' not in data or 'word_id' not in data:
        return jsonify({'message': 'user_id and word_id are required'}), 400

    user_id = data['user_id']
    word_id = data['word_id']
    word_type = data['word_type']
    is_mastered = data.get('is_mastered', 1) # 1已掌握 0未掌握-进入生词本

    # 检查是否已存在记录
    word = UserWordMastery.query.filter_by(user_id=user_id, word_id=word_id, word_type=word_type).first()
    if word:
        # 判断是否是生词本
        if is_mastered == word.is_mastered:
            return jsonify({
                'success': False,
                'message': 'Word already marked as mastered'
            }), 200
        else:
            word.is_mastered = is_mastered
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Word already marked as mastered'
            }), 200

    # 创建新记录
    try:
        mastery = UserWordMastery(user_id=user_id, word_id=word_id, word_type=word_type, created_at=datetime.now(), is_mastered=is_mastered)
        db.session.add(mastery)
        db.session.commit()
        AchievementService.check_achievements(user_id)  # 成就埋点
        return jsonify({
            'message': 'Word marked as mastered successfully',
            'mastery_id': mastery.user_word_mastery_id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@word_bp.route('/words', methods=['GET'])
def get_words():
    """
    获取单词列表(基于用户掌握进度返回10个)
    """
    try:
        user_id = request.args.get('user_id', type=int)
        classification = request.args.get('classification', type=str)
        if not user_id or not classification:
            return jsonify({
                'success': False,
                'message': 'user_id参数必须提供',
                'data': None
            }), 400

        # 查询用户已掌握的单词数量
        mastered_count = UserWordMastery.query.filter_by(
            user_id=user_id,
            word_type=classification,
            is_mastered=1
        ).count()

        offset = mastered_count

        # 查询单词(从偏移量位置开始取10个)
        words = Word.query.filter_by(classification=classification).order_by(Word.word_id).offset(offset).limit(10).all()

        # 格式化返回数据
        words_data = [word.to_dict() for word in words]

        return jsonify({
            'success': True,
            'message': '成功获取单词列表',
            'data': {
                'words': words_data,
                'mastered_count': mastered_count,
                'offset': offset,
                'count': len(words_data)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取单词列表失败: {str(e)}',
            'data': None
        }), 500

@word_bp.route('/today_mastered_words', methods=['GET'])
def get_today_mastered_words():
    # 获取user_id参数
    user_id = request.args.get('user_id', type=int)

    # 验证参数
    if not user_id:
        return jsonify({
            'success': False,
            'message': '必须提供user_id参数'
        }), 400

    try:
        today = datetime.today()
        start_date = today.strftime("%Y-%m-%d 00:00:00")
        end_date = today.strftime("%Y-%m-%d 23:59:59")
        query = select(func.count()).where(
            UserWordMastery.user_id == user_id,
            UserWordMastery.created_at.between(start_date, end_date)
        )
        count = db.session.scalar(query)

        return jsonify({
            'success': True,
            'user_id': user_id,
            'date': today.strftime("%Y-%m-%d"),
            'data': count
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': '获取今日掌握单词数失败',
            'error': str(e)
        }), 500

@word_bp.route('/get_today_learned_words', methods=['GET'])
def get_today_learned_words():
    # 获取user_id参数
    user_id = request.args.get('user_id', type=int)

    # 验证参数
    if not user_id:
        return jsonify({
            'success': False,
            'message': '必须提供user_id参数'
        }), 400

    try:
        today = datetime.today()
        start_date = today.strftime("%Y-%m-%d 00:00:00")
        end_date = today.strftime("%Y-%m-%d 23:59:59")

        # 构建联合查询获取word_en
        query = select(Word.word_en, Word.word_cn).select_from(
            join(UserWordMastery, Word, UserWordMastery.word_id == Word.word_id)
        ).where(
            UserWordMastery.user_id == user_id,
            UserWordMastery.created_at.between(start_date, end_date)
        ).order_by(UserWordMastery.created_at.desc())

        # 执行查询获取所有结果
        results = db.session.execute(query).all()

        # 格式化返回数据
        word_list = []
        for row in results:
            try:
                meaning = json.loads(row.word_cn)[0]["tran"]
            except Exception as e:
                meaning = ""
            word_list.append({
                'text': row.word_en,
                'meaning': meaning,
                'selected': False
            })
        return jsonify({
            'success': True,
            'user_id': user_id,
            'date': today.strftime("%Y-%m-%d"),
            'count': len(word_list),
            'words': word_list  # 直接返回英文单词列表
        })

    except Exception as main_error:
        # 添加详细错误日志
        app.logger.error(f"获取今日单词失败 - 用户ID {user_id}: {str(main_error)}")
        return jsonify({
            'success': False,
            'message': '获取今日掌握单词列表失败',
            'error': str(main_error)
        }), 500

@word_bp.route('/unknown_words', methods=['GET'])
def get_unknown_words():
    # 获取请求参数
    user_id = request.args.get('user_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # 使用join查询生词及其详细信息
    query = db.session.query(Word, UserWordMastery).join(
        UserWordMastery,
        UserWordMastery.word_id == Word.word_id
    ).filter(
        and_(
            UserWordMastery.user_id == user_id,
            UserWordMastery.is_mastered == 0
        )
    ).order_by(UserWordMastery.created_at.desc())

    # 分页处理
    # pagination = query.paginate(
    #     page=page,
    #     per_page=per_page,
    #     error_out=False
    # )

    # 构建响应数据
    unknown_words = []
    # for word, mastery_record in pagination.items:
    #     word_dict = word.to_dict()
    #     word_dict['created_at'] = mastery_record.created_at.isoformat() if mastery_record.created_at else None
    #     word_dict['word_type'] = mastery_record.word_type
    #     unknown_words.append(word_dict)

    # 上面是分页的做法
    # 我这里不分页了
    for word, mastery_record in query.all():
        word_dict = word.to_dict()
        word_dict['created_at'] = mastery_record.created_at.isoformat() if mastery_record.created_at else None
        word_dict['word_type'] = mastery_record.word_type
        unknown_words.append(word_dict)

    # 构建响应
    response = {
        'unknown_words': unknown_words
    }

    return jsonify(response), 200

@word_bp.route('/tourist_words', methods=['GET'])
def get_tourist_words():
    random_words = [word.to_dict() for word in Word.query.order_by(func.random()).limit(10).all()]
    return jsonify({
        'success': True,
        'data': {
            'words': random_words
        }
    })