from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app, make_response
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
    """Admin dashboard with statistics"""
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
    
    # Get additional statistics
    stats = get_dashboard_statistics()
    
    return render_template('admin/index.html', model_names=model_names, model_stats=model_stats, stats=stats)

def get_dashboard_statistics():
    """Get detailed dashboard statistics"""
    stats = {}
    
    # User statistics
    stats['total_users'] = User.query.count()
    stats['active_users_today'] = db.session.scalar(text("""
        SELECT COUNT(DISTINCT user_id) FROM chat_messages 
        WHERE DATE(created_at) = DATE('now')
    """)) or 0
    
    # Chat statistics
    stats['total_messages'] = ChatMessage.query.count()
    stats['today_messages'] = db.session.scalar(text("""
        SELECT COUNT(*) FROM chat_messages 
        WHERE DATE(created_at) = DATE('now')
    """)) or 0
    
    # Word statistics
    stats['total_words'] = Word.query.count()
    
    # AI Agent statistics
    stats['total_agents'] = AIAgent.query.count()
    stats['active_agents'] = AIAgent.query.filter_by(is_active=True).count()
    
    # Recent activity (last 7 days)
    recent_stats = db.session.execute(text("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as message_count,
            COUNT(DISTINCT user_id) as user_count
        FROM chat_messages 
        WHERE created_at >= DATE('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """)).fetchall()
    
    stats['recent_activity'] = [
        {'date': row[0], 'messages': row[1], 'users': row[2]}
        for row in recent_stats
    ]
    
    return stats

# User CRUD operations
@admin_bp.route('/users')
@login_required
def list_users():
    """List users with search and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    query = User.query
    
    # 搜索功能
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.wechat_openid.ilike(f'%{search}%'))
        )
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/users/list.html', users=users, search=search)

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
    """List words with search and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    classification = request.args.get('classification', '')
    
    query = Word.query
    
    # 搜索功能
    if search:
        query = query.filter(
            (Word.word_en.ilike(f'%{search}%')) |
            (Word.word_cn.ilike(f'%{search}%'))
        )
    
    # 分类筛选
    if classification:
        query = query.filter(Word.classification == classification)
    
    words = query.order_by(Word.word_id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # 获取所有分类用于筛选
    classifications = db.session.query(Word.classification).distinct().all()
    classifications = [c[0] for c in classifications if c[0]]
    
    return render_template('admin/words/list.html', 
                         words=words, 
                         search=search, 
                         classification=classification,
                         classifications=classifications)

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
    """List AI agents with search and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    
    query = AIAgent.query
    
    # 搜索功能
    if search:
        query = query.filter(
            (AIAgent.name.ilike(f'%{search}%')) |
            (AIAgent.description.ilike(f'%{search}%'))
        )
    
    # 状态筛选
    if status_filter:
        if status_filter == 'active':
            query = query.filter(AIAgent.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(AIAgent.is_active == False)
    
    ai_agents = query.order_by(AIAgent.agent_id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/ai_agents/list.html', 
                         ai_agents=ai_agents, 
                         search=search, 
                         status_filter=status_filter)

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
                welcome=request.form.get('welcome', '')
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
            ai_agent.welcome = request.form.get('welcome', '')
            
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

@admin_bp.route('/export_database')
@login_required
def export_database():
    """Export database as SQLite file"""
    try:
        # 获取数据库文件路径
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            # 处理相对路径情况
            if not os.path.isabs(db_path):
                db_path = os.path.join(current_app.instance_path, db_path)
            
            # 确保文件存在
            if os.path.exists(db_path):
                # 生成时间戳文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'chat_app_backup_{timestamp}.sqlite3'
                
                # 读取数据库文件内容
                with open(db_path, 'rb') as f:
                    db_data = f.read()
                
                # 创建响应
                response = make_response(db_data)
                response.headers['Content-Type'] = 'application/octet-stream'
                response.headers['Content-Disposition'] = f'attachment; filename={filename}'
                
                flash('数据库导出成功', 'success')
                return response
            else:
                flash('数据库文件不存在', 'error')
                return redirect(url_for('admin.index'))
        else:
            flash('仅支持SQLite数据库导出', 'error')
            return redirect(url_for('admin.index'))
            
    except Exception as e:
        flash(f'数据库导出失败: {str(e)}', 'error')
        return redirect(url_for('admin.index'))

# Chat Message CRUD operations
@admin_bp.route('/chat_messages')
@login_required
def list_chat_messages():
    """List chat messages with search and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    user_id = request.args.get('user_id', type=int)
    agent_id = request.args.get('agent_id', type=int)
    
    query = ChatMessage.query
    
    # 搜索功能
    if search:
        query = query.filter(ChatMessage.content.ilike(f'%{search}%'))
    
    # 用户筛选
    if user_id:
        query = query.filter(ChatMessage.user_id == user_id)
    
    # AI助手筛选
    if agent_id:
        query = query.filter(ChatMessage.agent_id == agent_id)
    
    chat_messages = query.order_by(ChatMessage.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # 获取用户和AI助手列表用于筛选
    users = User.query.with_entities(User.user_id, User.username).all()
    agents = AIAgent.query.with_entities(AIAgent.agent_id, AIAgent.name).all()
    
    return render_template('admin/chat_messages/list.html', 
                         chat_messages=chat_messages, 
                         search=search,
                         user_id=user_id,
                         agent_id=agent_id,
                         users=users,
                         agents=agents)

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