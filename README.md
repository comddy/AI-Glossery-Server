
# AI Glossery Server

一个基于Flask的AI词汇学习服务器，提供智能词汇学习、AI对话、成就系统和社交功能。

## 功能特性

### 📚 核心学习功能
- **词汇学习管理**: 支持多种词书分类（CET4、CET6、雅思、托福等）
- **智能记忆算法**: 基于用户掌握程度的个性化学习计划
- **TTS语音支持**: 集成edge-tts提供单词发音功能
- **图片记忆辅助**: 自动生成单词相关图片辅助记忆

### 🤖 AI对话功能
- **多AI代理支持**: 可配置多个AI角色进行对话
- **上下文记忆**: 保持对话历史上下文
- **智能回复**: 基于系统提示词的个性化回复

### 🏆 成就系统
- **连续学习奖励**: 每日签到和连续学习天数统计
- **成就解锁**: 多种学习成就和奖励机制
- **经验值系统**: 词友等级和经验值成长

### 👥 社交功能
- **词友系统**: 用户可拥有多个词友并自定义名称
- **交易系统**: 基于区块链概念的词力值交易
- **故事收藏**: 用户生成的故事内容收藏和分享

### 🎨 内容生成
- **故事生成**: AI根据选定单词生成英文故事
- **封面生成**: 自动为故事生成封面图片
- **头像上传**: 支持用户自定义头像

## 技术栈

- **后端框架**: Flask + SQLAlchemy
- **数据库**: SQLite
- **任务调度**: APScheduler
- **语音合成**: edge-tts
- **文件上传**: Werkzeug
- **跨域支持**: Flask-CORS
- **Web服务器**: Gunicorn

## 项目结构

```
AI-Glossery-Server/
├── crud/                 # 数据操作层
│   ├── user.py          # 用户CRUD操作
│   ├── ai_agent.py      # AI代理CRUD操作
│   └── chat_message.py  # 聊天消息CRUD操作
├── utils/               # 工具类
│   ├── CommonUtil.py    # 通用工具函数
│   └── UserUtil.py      # 用户相关工具
├── static/              # 静态文件
│   └── upload/          # 上传文件目录
├── views/               # 蓝图路由模块
├── AchievementStrategy.py  # 成就策略实现
├── sql_alchemy.py       # 数据库模型定义
├── script.py           # 主应用文件（Flask工厂）
├── gunicorn.conf.py    # Gunicorn配置文件
├── .env.example        # 环境变量示例文件
├── requirements.txt    # 依赖包列表
├── Dockerfile         # Docker容器配置
└── docker-compose.yml # Docker编排配置
```

## 数据库模型

### 主要数据表
- **User**: 用户信息（微信登录、学习偏好、钱包等）
- **Word**: 单词数据（中英文、例句、发音、图片）
- **UserWordMastery**: 用户单词掌握情况
- **AIAgent**: AI代理配置
- **ChatMessage**: 聊天消息记录
- **WordFriend**: 用户词友信息
- **TradeTransaction**: 交易记录（区块链式）
- **StoryCollection**: 故事收藏
- **UserAchievement**: 用户成就

## API接口

### 用户认证
- `POST /api/wxlogin` - 微信登录
- `POST /api/upload-avatar` - 上传头像
- `POST /api/update-profile` - 更新用户资料

### 词汇学习
- `GET /api/words` - 获取单词列表
- `POST /api/word/mark-mastered` - 标记单词掌握
- `GET /api/today_mastered_words` - 今日已掌握单词
- `GET /api/unknown_words` - 生词本单词
- `GET /api/tourist_words` - 游客模式单词

### AI对话
- `POST /api/chat` - 发送聊天消息
- `POST /api/chat/messages` - 获取聊天记录
- `GET /api/chat/conversations` - 获取对话列表
- `GET /api/latest_message_time` - 最新消息时间

### 内容生成
- `POST /api/story_generation` - 生成故事
- `POST /api/cover_image_generation` - 生成封面图片
- `GET /api/word_image_generation` - 生成单词图片
- `GET /api/generate_audio` - 生成语音

### 词友系统
- `GET /api/user/first_word_friend` - 获取首个词友
- `POST /api/add_exp` - 添加经验值
- `GET /api/3dmodel` - 获取3D模型

### 交易系统
- `POST /api/transaction/create` - 创建交易
- `GET /api/transactions/<wallet_key>` - 获取交易记录

### 成就系统
- `GET /api/achievements` - 获取成就列表

### 故事收藏
- `GET /api/get_story_collections` - 获取故事收藏
- `POST /api/collect_story` - 收藏故事

## 安装部署

### 本地开发
1. 创建虚拟环境：`python -m venv .venv`
2. 激活虚拟环境：`.venv\Scripts\activate` (Windows)
3. 安装依赖：`pip install -r requirements.txt`
4. 运行应用：`python script.py`

### Docker部署
1. 构建镜像：`docker-compose build`
2. 启动服务：`docker-compose up -d`

### 生产环境
使用Gunicorn部署：
```bash
gunicorn -c gunicorn.conf.py script:app
```

## 配置说明

### 环境变量配置
项目使用环境变量进行配置管理，复制 `.env.example` 为 `.env` 并修改相应配置：

```bash
cp .env .env
```

#### Flask应用配置（需要FLASK_前缀）
- `FLASK_ENV`: 运行环境 (development/production)
- `FLASK_DEBUG`: 调试模式
- `FLASK_SQLALCHEMY_DATABASE_URI`: 数据库连接字符串
- `FLASK_UPLOAD_FOLDER`: 文件上传目录
- `FLASK_ALLOWED_EXTENSIONS`: 允许的文件扩展名
- `FLASK_MAX_CONTENT_LENGTH`: 最大上传文件大小

#### Gunicorn配置
- `GUNICORN_WORKERS`: worker进程数
- `GUNICORN_WORKER_CLASS`: worker类型
- `GUNICORN_WORKER_CONNECTIONS`: 并发连接数
- `GUNICORN_BIND`: 绑定地址和端口
- `GUNICORN_KEYFILE`: SSL私钥文件
- `GUNICORN_CERTFILE`: SSL证书文件
- `GUNICORN_TIMEOUT`: 请求超时时间

### SSL配置
项目支持HTTPS，需要配置SSL证书文件：
- `deepspring-tech.com.key`: 私钥文件
- `deepspring-tech.com.pem`: 证书文件

配置文件优先级：环境变量 > 代码默认值，建议生产环境使用环境变量配置。

## 开发说明

### 数据库初始化
应用启动时会自动创建SQLite数据库文件，首次运行需要确保数据库目录有写入权限。

### 定时任务
使用APScheduler实现每日成就检查，每天午夜自动运行。

### 文件上传
支持图片格式：PNG, JPG, JPEG, GIF, BMP, WEBP，最大16MB。

## 许可证

MIT License