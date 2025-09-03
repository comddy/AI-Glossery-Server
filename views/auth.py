from flask import Blueprint, request, jsonify
from sql_alchemy import db, User
from utils.UserUtil import generate_hex_id

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/wxlogin", methods=['POST'])
def wxlogin():
    data = request.get_json()
    code = data.get('code')
    
    # 这里应该调用微信API获取openid和session_key
    # 模拟返回
    openid = "mock_openid_" + generate_hex_id(16)
    session_key = "mock_session_key_" + generate_hex_id(16)
    
    user = User.query.filter_by(wechat_openid=openid).first()
    
    if not user:
        user = User(
            username=f"user_{generate_hex_id(8)}",
            email=f"user_{generate_hex_id(8)}@example.com",
            wechat_openid=openid,
            wechat_session_key=session_key,
            preferred_classification="cet4",
            wallet_key=generate_hex_id(32),
            word_friend_name=f"word_friend_{generate_hex_id(8)}"
        )
        db.session.add(user)
        db.session.commit()
    
    return jsonify({
        'user_id': user.user_id,
        'username': user.username,
        'email': user.email,
        'avatar_url': user.avatar_url,
        'wallet_key': user.wallet_key
    })