from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from sqlalchemy import inspect, text
from sql_alchemy import db, User, Word, AIAgent, ChatMessage, WordFriend, UserWordMastery, WordFriendLevelConfig, UserAchievement, TradeTransaction, StoryCollection
from datetime import datetime
import os

admin_bp = Blueprint('admin', __name__, template_folder='templates', static_folder='static')

# Simple authentication - in production, use proper authentication
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admincyxq')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'cyxqadmin')

def login_required(f):
    """Decorator to require login for admin routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_all_models():
    """Get all SQLAlchemy models"""
    return [
        User, Word, AIAgent, ChatMessage, WordFriend, 
        UserWordMastery, WordFriendLevelConfig, UserAchievement, 
        TradeTransaction, StoryCollection
    ]

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin.index'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
@login_required
def index():
    """Admin dashboard"""
    models = get_all_models()
    model_names = [model.__name__ for model in models]
    
    # Get record counts for each model
    model_stats = []
    for model in models:
        try:
            # Use direct SQL query to avoid ORM issues
            table_name = getattr(model, '__tablename__', None)
            if table_name:
                try:
                    count = db.session.scalar(text(f"SELECT COUNT(*) FROM \"{table_name}\""))
                except:
                    count = 0
            else:
                count = 0
            model_stats.append({
                'name': model.__name__,
                'count': count
            })
        except:
            model_stats.append({
                'name': model.__name__,
                'count': 0
            })
    
    return render_template('admin/index.html', model_names=model_names, model_stats=model_stats)

# User CRUD operations
@admin_bp.route('/users')
@login_required
def list_users():
    """List all users with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('admin/users/list.html', users=users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    """Create a new user"""
    if request.method == 'POST':
        try:
            user = User(
                username=request.form['username'],
                email=request.form['email'],
                wechat_openid=request.form.get('wechat_openid', ''),
                wechat_session_key=request.form.get('wechat_session_key', ''),
                preferred_classification=request.form.get('preferred_classification', 'cet4'),
                preferred_plan_daily=int(request.form.get('preferred_plan_daily', 20)),
                wallet_key=request.form.get('wallet_key', ''),
                word_power_amount=int(request.form.get('word_power_amount', 0)),
                word_friend_name=request.form.get('word_friend_name', 'robot')
            )
            db.session.add(user)
            db.session.commit()
            flash('User created successfully', 'success')
            return redirect(url_for('admin.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'error')
    
    return render_template('admin/users/create.html')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit a user"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            user.username = request.form['username']
            user.email = request.form['email']
            user.wechat_openid = request.form.get('wechat_openid', '')
            user.wechat_session_key = request.form.get('wechat_session_key', '')
            user.preferred_classification = request.form.get('preferred_classification', 'cet4')
            user.preferred_plan_daily = int(request.form.get('preferred_plan_daily', 20))
            user.wallet_key = request.form.get('wallet_key', '')
            user.word_power_amount = int(request.form.get('word_power_amount', 0))
            user.word_friend_name = request.form.get('word_friend_name', 'robot')
            
            db.session.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    return render_template('admin/users/edit.html', user=user)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('admin.list_users'))

# Word CRUD operations
@admin_bp.route('/words')
@login_required
def list_words():
    """List all words with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    words = Word.query.order_by(Word.word_id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('admin/words/list.html', words=words)

@admin_bp.route('/words/create', methods=['GET', 'POST'])
@login_required
def create_word():
    """Create a new word"""
    if request.method == 'POST':
        try:
            word = Word(
                word_en=request.form['word_en'],
                word_cn=request.form['word_cn'],
                example_sentense_en=request.form['example_sentense_en'],
                example_sentense_cn=request.form['example_sentense_cn'],
                usphone=request.form['usphone'],
                picture=request.form.get('picture', ''),
                classification=request.form['classification']
            )
            db.session.add(word)
            db.session.commit()
            flash('Word created successfully', 'success')
            return redirect(url_for('admin.list_words'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating word: {str(e)}', 'error')
    
    return render_template('admin/words/create.html')

@admin_bp.route('/words/<int:word_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_word(word_id):
    """Edit a word"""
    word = Word.query.get_or_404(word_id)
    
    if request.method == 'POST':
        try:
            word.word_en = request.form['word_en']
            word.word_cn = request.form['word_cn']
            word.example_sentense_en = request.form['example_sentense_en']
            word.example_sentense_cn = request.form['example_sentense_cn']
            word.usphone = request.form['usphone']
            word.picture = request.form.get('picture', '')
            word.classification = request.form['classification']
            
            db.session.commit()
            flash('Word updated successfully', 'success')
            return redirect(url_for('admin.list_words'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating word: {str(e)}', 'error')
    
    return render_template('admin/words/edit.html', word=word)

@admin_bp.route('/words/<int:word_id>/delete', methods=['POST'])
@login_required
def delete_word(word_id):
    """Delete a word"""
    word = Word.query.get_or_404(word_id)
    
    try:
        db.session.delete(word)
        db.session.commit()
        flash('Word deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting word: {str(e)}', 'error')
    
    return redirect(url_for('admin.list_words'))

# AI Agent CRUD operations
@admin_bp.route('/ai_agents')
@login_required
def list_ai_agents():
    """List all AI agents with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    ai_agents = AIAgent.query.order_by(AIAgent.agent_id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('admin/ai_agents/list.html', ai_agents=ai_agents)

@admin_bp.route('/ai_agents/create', methods=['GET', 'POST'])
@login_required
def create_ai_agent():
    """Create a new AI agent"""
    if request.method == 'POST':
        try:
            ai_agent = AIAgent(
                name=request.form['name'],
                description=request.form['description'],
                system_prompt=request.form['system_prompt'],
                avatar_url=request.form.get('avatar_url', ''),
                is_active=bool(request.form.get('is_active', False)),
                category=request.form['category'],
                temperature=float(request.form.get('temperature', 0.7)),
                max_tokens=int(request.form.get('max_tokens', 1000))
            )
            db.session.add(ai_agent)
            db.session.commit()
            flash('AI Agent created successfully', 'success')
            return redirect(url_for('admin.list_ai_agents'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating AI agent: {str(e)}', 'error')
    
    return render_template('admin/ai_agents/create.html')

@admin_bp.route('/ai_agents/<int:agent_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_ai_agent(agent_id):
    """Edit an AI agent"""
    ai_agent = AIAgent.query.get_or_404(agent_id)
    
    if request.method == 'POST':
        try:
            ai_agent.name = request.form['name']
            ai_agent.description = request.form['description']
            ai_agent.system_prompt = request.form['system_prompt']
            ai_agent.avatar_url = request.form.get('avatar_url', '')
            ai_agent.is_active = bool(request.form.get('is_active', False))
            ai_agent.category = request.form['category']
            ai_agent.temperature = float(request.form.get('temperature', 0.7))
            ai_agent.max_tokens = int(request.form.get('max_tokens', 1000))
            
            db.session.commit()
            flash('AI Agent updated successfully', 'success')
            return redirect(url_for('admin.list_ai_agents'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating AI agent: {str(e)}', 'error')
    
    return render_template('admin/ai_agents/edit.html', ai_agent=ai_agent)

@admin_bp.route('/ai_agents/<int:agent_id>/delete', methods=['POST'])
@login_required
def delete_ai_agent(agent_id):
    """Delete an AI agent"""
    ai_agent = AIAgent.query.get_or_404(agent_id)
    
    try:
        db.session.delete(ai_agent)
        db.session.commit()
        flash('AI Agent deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting AI agent: {str(e)}', 'error')
    
    return redirect(url_for('admin.list_ai_agents'))

# Chat Message CRUD operations
@admin_bp.route('/chat_messages')
@login_required
def list_chat_messages():
    """List all chat messages with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    chat_messages = ChatMessage.query.order_by(ChatMessage.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('admin/chat_messages/list.html', chat_messages=chat_messages)

@admin_bp.route('/chat_messages/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_chat_message(message_id):
    """Delete a chat message"""
    chat_message = ChatMessage.query.get_or_404(message_id)
    
    try:
        db.session.delete(chat_message)
        db.session.commit()
        flash('Chat message deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting chat message: {str(e)}', 'error')
    
    return redirect(url_for('admin.list_chat_messages'))