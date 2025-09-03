from flask import Blueprint, request, jsonify
from sql_alchemy import db, TradeTransaction, User
import hashlib

transaction_bp = Blueprint('transaction', __name__)

@transaction_bp.route('/transaction/create', methods=['POST'])
def create_transaction():
    data = request.get_json()
    sender_key = data.get('sender')
    receiver_key = data.get('receiver')
    amount = data.get('amount')
    
    if not all([sender_key, receiver_key, amount]):
        return jsonify({'error': 'Missing parameters'}), 400
    
    if amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400
    
    # 检查发送者余额
    sender = User.query.filter_by(wallet_key=sender_key).first()
    if not sender or sender.word_power_amount < amount:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    # 检查接收者是否存在
    receiver = User.query.filter_by(wallet_key=receiver_key).first()
    if not receiver:
        return jsonify({'error': 'Receiver not found'}), 404
    
    # 获取上一条交易的哈希
    last_transaction = TradeTransaction.query.order_by(
        TradeTransaction.created_at.desc()
    ).first()
    
    previous_hash = last_transaction.current_hash if last_transaction else 'genesis'
    
    # 创建交易数据并计算哈希
    transaction_data = f"{sender_key}{receiver_key}{amount}{previous_hash}"
    current_hash = hashlib.sha256(transaction_data.encode()).hexdigest()
    
    # 创建交易记录
    transaction = TradeTransaction(
        sender=sender_key,
        receiver=receiver_key,
        amount=amount,
        previous_hash=previous_hash,
        current_hash=current_hash
    )
    
    # 更新用户余额
    sender.word_power_amount -= amount
    receiver.word_power_amount += amount
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'transaction_id': transaction.trade_transaction_id,
        'sender': transaction.sender,
        'receiver': transaction.receiver,
        'amount': transaction.amount,
        'current_hash': transaction.current_hash
    })

@transaction_bp.route('/transactions/<wallet_key>', methods=['GET'])
def get_transactions(wallet_key):
    # 获取用户的所有交易记录
    sent_transactions = TradeTransaction.query.filter_by(sender=wallet_key).order_by(
        TradeTransaction.created_at.desc()
    ).all()
    
    received_transactions = TradeTransaction.query.filter_by(receiver=wallet_key).order_by(
        TradeTransaction.created_at.desc()
    ).all()
    
    transactions = []
    
    for tx in sent_transactions:
        transactions.append({
            'transaction_id': tx.trade_transaction_id,
            'type': 'sent',
            'counterparty': tx.receiver,
            'amount': -tx.amount,
            'timestamp': tx.created_at.isoformat(),
            'hash': tx.current_hash
        })
    
    for tx in received_transactions:
        transactions.append({
            'transaction_id': tx.trade_transaction_id,
            'type': 'received',
            'counterparty': tx.sender,
            'amount': tx.amount,
            'timestamp': tx.created_at.isoformat(),
            'hash': tx.current_hash
        })
    
    # 按时间排序
    transactions.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify(transactions)