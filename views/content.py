import asyncio
import os
import re

import edge_tts
from flask import Blueprint, request, jsonify, Response
from sql_alchemy import db, StoryCollection, User
import requests
import json

content_bp = Blueprint('content', __name__)

@content_bp.route('/story_generation', methods=['POST'])
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

@content_bp.route('/cover_image_generation', methods=['POST'])
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

@content_bp.route('/word_image_generation', methods=['GET'])
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

@content_bp.route('/generate_audio', methods=['GET'])
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

@content_bp.route('/get_story_collections', methods=['GET'])
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

@content_bp.route('/collect_story', methods=['POST'])
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