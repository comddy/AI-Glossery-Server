import hashlib

from flask import Flask, jsonify, request, send_file, Response
from flask_cors import CORS
import os
import json
import re
import requests

from AchievementStrategy import AchievementService, daily_achievement_check
from sql_alchemy import db, User, UserWordMastery, Word, ChatMessage, AIAgent, \
    WordFriendLevelConfig, UserAchievement, WordFriend, TradeTransaction, StoryCollection
from crud.user import get_user_info, init_user, get_learning_percent
from crud.ai_agent import create_agent
from crud.chat_message import insert_message, get_messages
from werkzeug.utils import secure_filename

from datetime import datetime, date
from sqlalchemy import select, func, join, and_
import asyncio, edge_tts

from apscheduler.schedulers.background import BackgroundScheduler

from utils.CommonUtil import allowed_file, generate_random_filename
from utils.UserUtil import generate_hex_id


def create_app():
    app = Flask(__name__)

    # 初始化扩展
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_app.sqlite3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

    # 图片上传配置
    app.config['UPLOAD_FOLDER'] = 'static/upload'
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传大小为16MB
    # 确保上传目录存在
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)

    # 确保在app上下文内初始化调度器
    with app.app_context():
        scheduler = BackgroundScheduler()
        scheduler.add_job(daily_achievement_check, 'cron', hour=0)  # 每天午夜运行
        scheduler.start()

    return app


app = create_app()

# 允许所有域名跨域访问
CORS(app)


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route("/api/wxlogin", methods=['POST'])
def wx_login():
    data = request.get_json()
    code = data.get('code')
    url = 'https://api.weixin.qq.com/sns/jscode2session'
    params = {
        'appid': 'wx3a9840084303b3c2',  # appid
        'secret': '62b0f378c33ed0567d7cb178b19ca746',  # secret
        'js_code': f'{code}',  # replace with actual js_code
        'grant_type': 'authorization_code'  # fixed value
    }

    response = requests.get(url, params=params).json()
    if response.get("openid") and response.get("session_key"):
        openid = response.get("openid")
        session_key = response.get("session_key")
        user = User.query.filter_by(wechat_openid=openid, is_deleted=0).first()
        if user:
            # 用户已经存在，更新session_key，然后直接返回相应数据
            return jsonify({
                "success": True,
                "data": {
                    "wechat_openid": openid,
                    "username": user.username,
                    "email": user.email,
                    "avatar_url": user.avatar_url,
                    "user_id": user.user_id,
                    "wallet_key": user.wallet_key,
                    "word_power_amount": user.word_power_amount,
                    "preferred_plan": {
                        "preferred": user.preferred_classification,
                        "plan_amount": user.preferred_plan_daily
                    }
                },
                "is_first_login": False
            })
        else:
            # 第一次登录，创建新用户
            user = init_user(openid, session_key)
            return jsonify({
                "success": True,
                "data": {
                    "wechat_openid": openid,
                    "username": user.username,
                    "email": user.email,
                    "avatar_url": user.avatar_url,
                    "user_id": user.user_id,
                    "wallet_key": user.wallet_key,
                    "word_power_amount": user.word_power_amount,
                    "preferred_plan": {
                        "preferred": user.preferred_classification,
                        "plan_amount": user.preferred_plan_daily
                    }
                },
                "is_first_login": True
            })
    else:
        # error
        print("Error Response JSON:", response.json())
        return jsonify({
            "success": False,
            "msg": response.json()
        })


@app.route('/api/story_generation', methods=['POST'])
def story_generation():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        theme = data.get('theme')

        if not prompt and not theme:
            return jsonify({
                "success": False,
                "message": "缺少必要参数: prompt 或 theme"
            }), 400

        system_prompt = f'你是一个英语学习智能助手，你需要根据用户提供的单词或主题，生成一个{theme}主题的英文故事。请确保故事生动有趣，并在故事中合理使用目标单词。生成的故事长度应该适中，建议在300字左右。在故事原文中，把用户给出的单词用括号括起来。请按照以下JSON格式返回："story_title": "故事标题","story_content": "英文故事原文","chinese_translation": "中文翻译"'

        # 这里需要替换为实际的API调用
        # 由于Python中没有直接等效的axios，我们使用requests库
        headers = {
            'Authorization': f'Bearer {os.getenv("ZHIPUAI_API_KEY", "6eb6de30d0c6bab295e8730d7a8a71a0.gbET8XqExYOb99Ni")}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": "glm-4-flash-250414",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }

        proxies = {
            'http': 'http://127.0.0.1:33210',
            'https': 'http://127.0.0.1:33210'
        }

        response = requests.post(
            'https://open.bigmodel.cn/api/paas/v4/chat/completions',
            json=payload,
            headers=headers,
            # proxies=proxies,  # 添加代理配置
            timeout=10
        )

        if response.status_code != 200:
            raise Exception(f"API请求失败，状态码: {response.status_code}")

        response_data = response.json()
        if not response_data or not response_data.get('choices') or not response_data['choices'][0].get('message'):
            raise Exception('AI接口返回数据格式不正确')

        try:
            # 尝试解析JSON响应
            content = response_data['choices'][0]['message']['content']
            result = json.loads(content)
        except json.JSONDecodeError:
            # 尝试清理和提取JSON
            cleaned_content = content.replace('\\n', '').replace('\\', '')
            json_match = re.search(r'\{.*\}', cleaned_content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise Exception('无法提取有效的JSON数据')

        # 验证返回的数据结构
        if not all(key in result for key in ['story_title', 'story_content', 'chinese_translation']):
            print(result)
            raise Exception('故事生成结果格式不完整')

        result['story_content'] = result['story_content'].replace('(', '').replace(')', '')
        return jsonify({
            "success": True,
            "data": {
                'content': result['story_content'],
                'content_zh': result['chinese_translation'],
                'title': result['story_title'],
                'selected_words': prompt.split(',')
            }
        })

    except Exception as e:
        print(e)
        return jsonify({
            "success": False,
            "message": "故事生成过程中发生错误",
            "error": str(e)
        }), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        chat_type = data.get('type', 'default')

        # 构建系统提示
        system_prompt = f"""你是一个{chat_type}风格的英语老师Kris，是一款英语学习软件"VocalBuddy:词友星球"的专任AI老师，你需要和学生进行互动，帮助他们学习英语。你在自我介绍时，请扮演好你的角色，不要和学生聊与学习无关的内容。
请用生动有趣的方式教授英语知识，纠正学生的错误，并鼓励他们进步。你只有第一次回复时，需要先自我介绍。其他时候要尽可能简短回答。如果用户和你发中文，请引导他使用英语回答。"""

        # 构建完整消息数组
        full_messages = [{"role": "system", "content": system_prompt}]
        if isinstance(messages, list) and messages:
            full_messages.extend(messages)

        # 调用AI接口
        import requests
        headers = {
            'Authorization': f'Bearer {os.getenv("ZHIPUAI_API_KEY", "6eb6de30d0c6bab295e8730d7a8a71a0.gbET8XqExYOb99Ni")}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": "glm-4-flash-250414",
            "messages": full_messages
        }

        # 添加代理配置（如果需要）
        proxies = {
            'http': 'http://127.0.0.1:33210',
            'https': 'http://127.0.0.1:33210'
        } if os.getenv('USE_PROXY', 'false').lower() == 'true' else None

        response = requests.post(
            'https://open.bigmodel.cn/api/paas/v4/chat/completions',
            json=payload,
            headers=headers,
            proxies=proxies,
            timeout=15
        )

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

@app.route('/api/word_image_generation', methods=['GET'])
def word_image_generation():
    try:
        word = request.args.get('word')

        header = {
            'Authorization': 'Bearer pat_qgBj4YOM9z2Ur5NGBF1cYicN40kH6IeZpnmYv4sZOfQa81R8CFo6aMeGqFxxK0jn',
            'Content-Type': 'application/json'
        }
        body = {
            'workflow_id': '7542144636219932715',
            'parameters': {
                'input': word
            }
        }
        response = requests.post(
            'https://api.coze.cn/v1/workflow/run',
            json=body,
            headers=header,
            timeout=15
        )

        if response.status_code != 200:
            raise Exception(f"AI图像生成接口请求失败，状态码: {response.status_code}")

        response_data = response.json()
        print("response_data", response_data)

        if response_data['code'] != 0:
            raise Exception(f"AI图像生成接口请求失败: {response_data['msg']}")

        _data = json.loads(response_data['data'])
        print(_data)
        return jsonify({
            "success": True,
            "data": _data["data"]
        })
    except Exception as e:
        error_detail = str(e)
        print(error_detail)
        return jsonify({
            "success": False,
            "message": error_detail
        }), 500

@app.route('/api/cover_image_generation', methods=['POST'])
def cover_image_generation():
    try:
        data = request.get_json()
        prompt = data.get('prompt')

        if not prompt:
            return jsonify({
                "success": False,
                "message": "缺少必要参数: prompt"
            }), 400

        # 构建完整的提示词
        prompt_whole = f'你是一个故事封面设计大师，你需要帮我设计短文故事的封面图片。请根据下面的内容，设计一个吸引人的封面图片。要注意画面干净、清爽，画面上部最好简洁、留白。主题是:{prompt}'

        # 调用AI图像生成接口
        import requests
        headers = {
            'Authorization': f'Bearer {os.getenv("ZHIPUAI_API_KEY", "6eb6de30d0c6bab295e8730d7a8a71a0.gbET8XqExYOb99Ni")}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": "cogview-3-flash",
            "prompt": prompt_whole,
            "quality": "standard",
            "size": "1344x768"
        }

        # 添加代理配置（如果需要）
        proxies = {
            'http': 'http://127.0.0.1:33210',
            'https': 'http://127.0.0.1:33210'
        } if os.getenv('USE_PROXY', 'false').lower() == 'true' else None

        response = requests.post(
            'https://open.bigmodel.cn/api/paas/v4/images/generations',
            json=payload,
            headers=headers,
            proxies=proxies,
            timeout=30  # 30秒超时
        )

        if response.status_code != 200:
            raise Exception(f"AI图像生成接口请求失败，状态码: {response.status_code}")

        response_data = response.json()
        if not response_data or not response_data.get('data') or not response_data['data'][0].get('url'):
            raise Exception('AI接口返回的图像数据格式不正确')

        return jsonify({
            "success": True,
            "image_url": response_data['data'][0]['url']
        })

    except Exception as e:
        error_detail = str(e)
        if hasattr(e, 'response') and e.response and hasattr(e.response, 'json'):
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text

        return jsonify({
            "success": False,
            "message": "图像生成过程中发生错误",
            "error": error_detail
        }), 500


@app.route("/api/add/agent", methods=['POST'])
def add_agent():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    system_prompt = data.get('system_prompt')

    if not name and not description and not system_prompt:
        return jsonify({
            "success": False,
            "message": "输入有误"
        }), 400

    result = create_agent(name, system_prompt, description=description)
    if result:
        return jsonify({
            "success": True,
            "message": "添加成功"
        })
    else:
        return jsonify({
            "success": False,
            "message": "添加失败"
        }), 500


@app.route('/api/chat/messages', methods=['POST'])
def add_message():
    data = request.get_json()

    # 验证必要字段
    required_fields = ['user_id', 'agent_id', 'sender_type', 'content']
    if not all(field in data for field in required_fields):
        return jsonify({
            'success': False,
            'message': '缺少必要字段: user_id, agent_id, sender_type 或 content'
        }), 400

    # 验证 sender_type
    if data['sender_type'] not in ['user', 'agent']:
        return jsonify({
            'success': False,
            'message': 'sender_type 必须是 "user" 或 "agent"'
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


@app.route('/api/chat/conversations', methods=['GET'])
def get_conversation_messages():
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

    messages_data = []
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


@app.route('/api/word/mark-mastered', methods=['POST'])
def mark_mastered():
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


@app.route('/api/words', methods=['GET'])
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


@app.route('/api/latest_message_time', methods=['GET'])
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


@app.route('/api/today_mastered_words', methods=['GET'])
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


@app.route("/api/add_exp", methods=['POST'])
def add_word_friend_exp():
    data = request.get_json()
    word_friend_id = int(data.get('word_friend_id'))
    add_exp = int(data.get('add_exp'))
    current_level = int(data.get('level'))

    # 查询用户关联的特定词友精灵
    user_word_friend = WordFriend.query.filter_by(
        word_friend_id=word_friend_id
    ).first()

    level_config = WordFriendLevelConfig.query.filter_by(
        exp_level=current_level + 1
    ).first()

    added_exp = add_exp + user_word_friend.exp

    if added_exp / level_config.exp_require >= 1:
        # 升级，修改等级
        new_exp = added_exp % level_config.exp_require
        user_word_friend.exp = new_exp
        user_word_friend.level = current_level + 1
    else:
        user_word_friend.exp = added_exp

    user = db.session.query(User).filter_by(user_id=user_word_friend.user_id).first()
    user.word_power_amount += add_exp  # todo:这里暂时用加的经验代表词力值
    db.session.commit()  # 修改直接查到之后原地改了，直接commit

    return jsonify({
        'success': True,
        'message': f'添加经验，当前等级: {user_word_friend.level}'
    })


@app.route("/api/achievements", methods=['GET'])
def get_achievements():
    user_id = request.args.get('user_id', type=int)
    achievements = UserAchievement.query.filter_by(user_id=user_id).all()
    format_achievements = [
        {
            'name': achievement.name,
            'desc': achievement.description,
            'icon': achievement.icon,
            'is_active': achievement.is_active == 1
        }
        for achievement in achievements
    ]
    return jsonify({
        'success': True,
        'data': format_achievements
    })


@app.route('/api/user/first_word_friend', methods=['GET'])
def get_first_word_friend():
    # 获取user_id参数
    user_id = request.args.get('user_id', type=int)

    # 验证参数
    if not user_id:
        return jsonify({
            'success': False,
            'message': '必须提供user_id参数'
        }), 400

    user_info = get_user_info(user_id)
    if user_info:
        return jsonify({
            'success': True,
            'data': user_info
        })
    else:
        return jsonify({
            'success': False,
            "msg": "获取用户信息失败，请联系管理员"
        })


@app.route("/api/3dmodel", methods=['GET'])
def robot():
    model_name = request.args.get('model', type=str)
    # 返回文件
    return send_file(
        f"static/3dmodel/{model_name}.glb",
        as_attachment=True,  # 强制下载（False则尝试浏览器预览）
        download_name=f'{model_name}.glb'  # 下载时显示的文件名
    )


@app.route("/api/test", methods=['GET'])
def test():
    user_id = request.args.get('user_id', type=int)
    # 获取今天的日期
    today = date.today()
    word_count = db.session.query(db.func.count(UserWordMastery.user_word_mastery_id)) \
        .filter(UserWordMastery.user_id == user_id) \
        .filter(UserWordMastery.is_mastered == 1) \
        .filter(db.func.date(UserWordMastery.created_at) == today) \
        .scalar()
    print(word_count)
    return jsonify({
        'success': True,
        "data": word_count
    })


# 转账功能
@app.route('/api/transaction/create', methods=['POST'])
def create_transaction():
    data = request.get_json()
    sender = data.get('sender')
    receiver = data.get('receiver')
    amount = data.get('amount')

    if not all([sender, receiver, amount]):
        return jsonify({"error": "Missing parameters"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400

    try:
        # 检查发送者余额
        sender_user = db.session.query(User).filter_by(wallet_key=sender).first()
        if not sender_user:
            return jsonify({"error": "Sender not found"}), 404

        if sender_user.word_power_amount < amount:
            return jsonify({"error": "Insufficient word power"}), 400

        # 检查接收者是否存在
        receiver_user = db.session.query(User).filter_by(wallet_key=receiver).first()
        if not receiver_user:
            return jsonify({"error": "Receiver not found"}), 404

        # 获取上一个交易的hash
        last_tx = db.session.query(TradeTransaction).order_by(TradeTransaction.created_at.desc()).first()
        previous_hash = last_tx.current_hash if last_tx else "0"

        # 创建交易数据
        tx_id = generate_hex_id()
        current_time = datetime.now()
        tx_data = f"{tx_id}{sender}{receiver}{amount}{current_time}{previous_hash}"
        current_hash = hashlib.sha256(tx_data.encode()).hexdigest()

        # 创建交易记录
        new_transaction = TradeTransaction(
            sender=sender,
            receiver=receiver,
            amount=amount,
            created_at=current_time,
            previous_hash=previous_hash,
            current_hash=current_hash
        )
        db.session.add(new_transaction)

        # 更新双方余额
        sender_user.word_power_amount -= amount
        receiver_user.word_power_amount += amount

        db.session.commit()

        return jsonify({
            "message": "Transaction created",
            "transaction_id": tx_id,
            "hash": current_hash
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# 查询用户交易记录
@app.route('/api/transactions/<wallet_key>', methods=['GET'])
def get_transactions(wallet_key):
    # 检查用户是否存在
    user = db.session.query(User).filter_by(wallet_key=wallet_key).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # 查询用户相关的交易
    transactions = db.session.query(TradeTransaction).filter(
        (TradeTransaction.sender == wallet_key) | (TradeTransaction.receiver == wallet_key)
    ).order_by(TradeTransaction.created_at.desc()).all()

    transactions_data = [{
        "id": tx.id,
        "sender": tx.sender,
        "receiver": tx.receiver,
        "amount": tx.amount,
        "created_at": tx.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        "previous_hash": tx.previous_hash,
        "current_hash": tx.current_hash
    } for tx in transactions]

    return jsonify({
        "public_key": wallet_key,
        "transactions": transactions_data,
        "count": len(transactions_data)
    })


@app.route("/api/update_preferred", methods=['POST'])
def update_preferred_classification_book():
    try:
        data = request.get_json()
        print(data)
        user_id = data['user_id']
        preferred = data['preferred']
        preferred_plan_daily = data['preferred_plan_daily']

        user = User.query.filter_by(user_id=user_id).first()
        user.preferred_classification = preferred
        user.preferred_plan_daily = preferred_plan_daily
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Preferred classification book updated"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/api/update_plan_amount", methods=['POST'])
def update_plan_amount():
    data = request.get_json()
    print(data)
    user_id = data['user_id']
    amount = data['amount']

    user = User.query.filter_by(user_id=user_id).first()
    user.preferred_plan_daily = amount
    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Preferred plan amount updated",
        "data": amount
    })


@app.route('/api/generate_audio', methods=['GET'])
def generate_audio():
    """
    Endpoint to generate audio from text using edge_tts

    Expects GET parameters:
    - text: the text to convert to speech (required)
    - voice: voice identifier (optional, default "en-US-EricNeural")
    - rate: speech speed (optional, default "+0%")
    """
    try:
        # Get request data
        text = request.args.get('text')
        voice = request.args.get('voice', 'en-US-JennyNeural')  # edge_tts 的默认推荐音色
        rate = request.args.get('rate', '+0%')  # 速度调整，例如 "+10%", "-20%"

        if not text:
            return {"error": "Text parameter is required"}, 400

        # 异步调用 edge_tts
        async def generate():
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
            audio_data = b''
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        # 在同步环境中运行异步代码
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_data = loop.run_until_complete(generate())
        loop.close()

        # Return as binary response
        return Response(
            audio_data,
            mimetype='audio/mpeg',  # edge_tts 默认输出为 MP3 格式
            headers={
                'Content-Disposition': 'attachment; filename=generated_audio.mp3'
            }
        )

    except Exception as e:
        return {"error": str(e)}, 500



@app.route('/api/get_today_learned_words', methods=['GET'])
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

@app.route('/api/get_story_collections', methods=['GET'])
def get_story_collections():
    user_id = request.args.get('user_id', type=int)
    # 验证参数
    if not user_id:
        return jsonify({
            'success': False,
            'message': '必须提供user_id参数'
        }), 400

    user = User.query.filter_by(user_id=user_id).first()
    stories = [story.to_dict() for story in user.stories]
    return jsonify({
        'success': True,
        'data': stories,
        'message': "查询成功"
    })

@app.route('/api/collect_story', methods=['POST'])
def collect_story():
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    content_zh = data.get('content_zh')
    cover_img = data.get('cover_img', '')
    selected_words = data.get('selected_words', '')
    user_id = data.get('user_id')

    # 参数验证（确保必填字段不为空）
    if not all([title, content, content_zh, user_id]):
        return jsonify({
            'success': False,
            'message': '缺少必要参数: title, content或user_id'
        }), 400

    # 检查是否已收藏
    story_collection = StoryCollection.query.filter_by(title=title, user_id=user_id).first()
    if story_collection:
        try:
            db.session.delete(story_collection)  # 直接删除收藏记录
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "取消收藏成功"
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "success": False,
                "message": f"取消收藏失败: {str(e)}"
            }), 500
    try:
        story = StoryCollection()
        story.title = title
        story.content = content
        story.content_zh = content_zh
        story.cover_img = cover_img
        story.selected_words = selected_words
        story.user_id = user_id
        db.session.add(story)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '收藏成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e),
        })

@app.route('/api/user/learning_percent', methods=['GET'])
def learning_percent():
    # 获取数
    user_id = request.args.get('user_id', type=int)
    word_type = request.args.get('word_type', type=str)

    # 验证参数
    if not user_id and not word_type:
        return jsonify({
            'success': False,
            'message': '参数有误'
        }), 400

    percent = get_learning_percent(user_id, word_type)
    return jsonify({
        'success': True,
        'data': percent
    })

# 一个游客模式的获取单词方法
@app.route('/api/tourist_words', methods=['GET'])
def tourist_words():
    random_words = [word.to_dict() for word in Word.query.order_by(func.random()).limit(10).all()]
    return jsonify({
        'success': True,
        'data': {
            'words': random_words
        }
    })


@app.route('/api/upload-avatar', methods=['POST'])
def upload_avatar():
    """图片上传接口"""
    # 检查是否有文件部分
    if 'file' not in request.files:
        return jsonify({'error': '没有文件部分'}), 400

    file = request.files['file']
    user_id = request.form.get('user_id')

    # 检查是否选择了文件
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    # 检查文件类型是否允许
    if file and allowed_file(app, file.filename):
        # 生成随机文件名
        random_filename = generate_random_filename(file.filename)
        # 安全地处理文件名
        safe_filename = secure_filename(random_filename)
        file_path = app.config['UPLOAD_FOLDER'] + '/' + safe_filename

        user = User.query.filter_by(user_id=user_id).first()
        # 删除之前的头像
        if user.avatar_url and os.path.exists(user.avatar_url):
            os.remove(user.avatar_url)

        # 保存文件
        file.save(file_path)
        # 更新数据库
        user.avatar_url = file_path
        db.session.commit()

        # 返回成功响应
        return jsonify({
            'success': True,
            'message': '头像上传成功',
            'url': file_path
        }), 200
    else:
        return jsonify({'error': '不允许的文件类型'}), 400

@app.route("/api/update-profile", methods=['POST'])
def update_profile():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        username = data.get('username')
        email = data.get('email')

        user = User.query.filter_by(user_id=user_id).first()
        user.username = username
        user.email = email
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '更新成功',
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e),
        }), 500

@app.route("/api/model/list", methods=['GET'])
def model_list():
    user_id = request.args.get('user_id', type=int)
    if user_id is None:
        return jsonify({
            'success': False,
            'message': '参数异常'
        }), 400
    models = os.listdir("static/3dmodel")
    models = [{
        'id': i+1,
        'name': name[:-4],
        'is_owned': 1 if WordFriend.query.filter_by(user_id=user_id, name=name[:-4]).first() else 0,
    } for i, name in enumerate(models)]
    return jsonify({
        'success': True,
        'data': models
    })

@app.route('/api/unknown_words', methods=['GET'])
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

@app.route("/api/model/switch", methods=['POST'])
def switch_model():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        model_name = data.get('name')
        if not user_id or not model_name:
            return jsonify({
                'success': False,
                'message': '参数错误'
            }), 400

        word_friend = WordFriend.query.filter_by(user_id=user_id).first()
        word_friend.name = model_name
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '切换成功',
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route("/api/model/buy", methods=['POST'])
def buy_model():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        model_name = data.get('name')
        if not user_id or not model_name:
            return jsonify({
                'success': False,
                'message': '参数错误'
            }), 400

        db_word_friend = WordFriend.query.filter_by(user_id=user_id, name=model_name).first()
        if db_word_friend:
            return jsonify({
                'success': False,
                'message': '已持有，请勿重复添加'
            })
        word_friend = WordFriend(user_id=user_id, name=model_name, nickname=model_name)
        db.session.add(word_friend)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '购买成功!',
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route("/api/model/edit", methods=['POST'])
def edit_model():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        name = data.get('name')
        nickname = data.get('nickname')
        if not user_id or not nickname:
            return jsonify({
                'success': False,
                'message': '参数错误'
            }), 400
        word_friend = WordFriend.query.filter_by(user_id=user_id, name=name).first()
        word_friend.nickname = nickname
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '修改成功!',
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=('deepspring-tech.com.pem', 'deepspring-tech.com.key'))