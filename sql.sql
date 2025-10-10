-- 用户表
CREATE TABLE IF NOT EXISTS user (
	"user_id"	INTEGER,
	"username"	TEXT NOT NULL UNIQUE,
	"email"	TEXT,
	"avatar_url"	TEXT,
	"created_at"	TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"updated_at"	TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"wechat_openid"	BLOB UNIQUE,
	"wechat_session_key"	TEXT,
	"preferred_classification"	TEXT,
	"wallet_key"	TEXT,
	"word_power_amount"	INTEGER NOT NULL DEFAULT 0,
	"preferred_plan_daily"	INTEGER DEFAULT 20,
	"is_deleted"	INTEGER DEFAULT 0,
	"word_friend_name"	TEXT NOT NULL DEFAULT 'robot',
	PRIMARY KEY("user_id" AUTOINCREMENT)
);

-- AI Agent表
CREATE TABLE IF NOT EXISTS ai_agent (
    agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    system_prompt TEXT NOT NULL,
    avatar_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 聊天消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
	agent_id INTEGER NOT NULL,
    sender_type TEXT NOT NULL CHECK(sender_type IN ('user', 'assistant')),
    content TEXT NOT NULL,
    tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 单词伙伴表
CREATE TABLE IF NOT EXISTS word_friend (
    word_friend_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    level INTEGER NOT NULL DEFAULT 0, -- 等级
    exp INTEGER NOT NULL DEFAULT 0, -- 经验值
    user_id INTEGER NOT NULL,
    nickname TEXT,
    FOREIGN KEY (user_id) REFERENCES user(user_id)
)

-- 单词表
CREATE TABLE IF NOT EXISTS word (
    word_id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_en TEXT NOT NULL,
    word_cn TEXT NOT NULL,
    example_sentense_en TEXT NOT NULL,
    example_sentense_cn TEXT NOT NULL,
    usphone TEXT NOT NULL,
    picture TEXT,
    word_type TEXT NOT NULL
)

-- 用户单词掌握表, 如果有记录说明掌握了
CREATE TABLE IF NOT EXISTS user_word_mastery (
	"user_word_mastery_id"	INTEGER,
	"user_id"	INTEGER NOT NULL,
	"word_id"	INTEGER NOT NULL,
	"created_at"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	"word_type"	TEXT,
	"is_mastered"	INTEGER DEFAULT 1,
	PRIMARY KEY("user_word_mastery_id" AUTOINCREMENT)
)

CREATE TABLE IF NOT EXISTS word_friend_level_config(
	word_friend_level_config_id INTEGER PRIMARY KEY AUTOINCREMENT,
	exp_level INTEGER NOT NULL UNIQUE, -- 等级
	exp_require INTEGER NOT NULL -- 升级到该等级所需经验
)

-- 用户成就表, 创建用户即把所有成就copy一份进来
/**
  {
			icon: '🔥',
			name: '坚持不懈',
			desc: '连续学习30天',
			unlocked: true
		},
		{
			icon: '📚',
			name: '词汇大师',
			desc: '掌握500个单词',
		},
		{
			icon: '⚡',
			name: '速记能手',
			desc: '单日记忆50个单词',
		},
		{
			icon: '🚀',
			name: '突破极限',
			desc: '连续学习100天',
		}
 */
CREATE TABLE IF NOT EXISTS user_achievement(
    user_achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    is_active INTEGER DEFAULT 0, -- 0无1有
)

CREATE TABLE IF NOT EXISTS trade_transaction(
    trade_transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    receiver TEXT NOT NULL,
	amount INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    previous_hash TEXT,
	current_hash TEXT
)

CREATE TABLE IF NOT EXISTS story_collection(
	"id"	INTEGER,
	"title"	TEXT,
	"content"	TEXT,
	"content_zh"	TEXT,
	"cover_img"	TEXT,
	"created_at"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	"user_id"	INTEGER,
	"selected_words"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
)
