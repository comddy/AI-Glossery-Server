import requests
from flask import Blueprint, request, jsonify

from crud.user import init_user
from sql_alchemy import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/wxlogin", methods=['POST'])
def wxlogin():
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
