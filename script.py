from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os
import json
import re
import requests

from AchievementStrategy import AchievementService, daily_achievement_check
from sql_alchemy import db, User, UserWordMastery, Word, ChatMessage, AIAgent, \
    WordFriendLevelConfig, UserAchievement, WordFriend
from crud.user import create_user, get_user_info, init_user
from crud.ai_agent import create_agent
from crud.chat_message import insert_message, get_messages

from datetime import timedelta, datetime, date
from sqlalchemy import select, func

from apscheduler.schedulers.background import BackgroundScheduler


def create_app():
    app = Flask(__name__)

    # 初始化扩展
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_app.sqlite3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
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
        user = User.query.filter_by(wechat_openid=openid).first()
        if user:
            # 用户已经存在，更新session_key，然后直接返回相应数据
            return jsonify({
                "success": True,
                "data": {
                    "wechat_openid": openid,
                    "username": user.username,
                    "email": user.email,
                    "avatar_url": user.avatar_url,
                    "user_id": user.user_id
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
                    "user_id": user.user_id
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

        system_prompt = f'你是一个英语学习智能助手，你需要根据用户提供的单词或主题，生成一个尽量复合{theme}主题的英文故事。请确保故事生动有趣，并在故事中合理使用目标单词。生成的故事长度应该适中，建议在300字左右。在故事原文中，把用户给出的单词用括号括起来。请按照以下JSON格式返回："story_title": "故事标题","story_content": "英文故事原文","chinese_translation": "中文翻译"'

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

        return jsonify({
            "success": True,
            "data": result
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
        if hasattr(e, 'response') and e.response and hasattr(e.response, 'json'):
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text

        return jsonify({
            "success": False,
            "message": "聊天对话过程中发生错误",
            "error": error_detail
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
        "word_id": 456
    }
    """
    data = request.get_json()

    # 验证必需参数
    if not data or 'user_id' not in data or 'word_id' not in data:
        return jsonify({'message': 'user_id and word_id are required'}), 400

    user_id = data['user_id']
    word_id = data['word_id']

    # 检查是否已存在记录
    if UserWordMastery.query.filter_by(user_id=user_id, word_id=word_id).first():
        return jsonify({'message': 'Word already marked as mastered'}), 200

    # 创建新记录
    try:
        mastery = UserWordMastery(user_id=user_id, word_id=word_id, created_at=datetime.now())
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
    GET /api/words?user_id=123
    """
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'user_id参数必须提供',
                'data': None
            }), 400

        # 查询用户已掌握的单词数量
        mastered_count = UserWordMastery.query.filter_by(
            user_id=user_id
        ).count()

        offset = mastered_count

        # 查询单词(从偏移量位置开始取10个)
        words = Word.query.order_by(Word.word_id).offset(offset).limit(10).all()

        # 格式化返回数据
        words_data = [{
            'word_id': word.word_id,
            'word_en': word.word_en,
            'word_cn': json.loads(word.word_cn),
            'usphone': word.usphone,
            'example_en': word.example_sentense_en,
            'example_cn': word.example_sentense_cn,
            'picture': word.picture,
            "speech": f"https://dict.youdao.com/dictvoice?audio={word.word_en}&type=2"
        } for word in words]

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
                'success': True,
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
    word_friend_id = data.get('word_friend_id')
    add_exp = data.get('add_exp')
    current_level = data.get('level')

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


@app.route("/api/3dmodel/robot", methods=['GET'])
def robot():
    # 返回文件
    return send_file(
        "static/RobotExpressive.glb",
        as_attachment=True,  # 强制下载（False则尝试浏览器预览）
        download_name='RobotExpressive.glb'  # 下载时显示的文件名
    )

@app.route("/api/test", methods=['GET'])
def test():
    user_id = request.args.get('user_id', type=int)
    # 获取今天的日期
    today = date.today()
    word_count = db.session.query(db.func.count(UserWordMastery.user_word_mastery_id)) \
        .filter(UserWordMastery.user_id == user_id) \
        .filter(db.func.date(UserWordMastery.created_at) == today) \
        .scalar()
    print(word_count)
    return jsonify({
        'success': True,
        "data": word_count
    })

@app.route("/api/testwy", methods=['GET'])
def testwy():
    return "testwy"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=('deepspring-tech.com.pem', 'deepspring-tech.com.key'))
