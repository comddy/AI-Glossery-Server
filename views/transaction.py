from datetime import datetime

from flask import Blueprint, request, jsonify
from sql_alchemy import db, TradeTransaction, User
import hashlib

from utils.UserUtil import generate_hex_id

transaction_bp = Blueprint('transaction', __name__)

@transaction_bp.route('/transaction/create', methods=['POST'])
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


@transaction_bp.route('/transactions/<wallet_key>', methods=['GET'])
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