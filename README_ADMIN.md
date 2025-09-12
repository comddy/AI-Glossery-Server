# 数据库管理网页界面

## 功能概述

已成功创建了一个完整的数据库管理网页界面，方便您对数据库进行简单的增删改查操作。

## 访问方式

1. 启动应用：
   ```bash
   python script.py
   ```

2. 访问管理界面：
   - 打开浏览器访问：`http://localhost:5000/admin/login`

## 可用功能

### 用户管理
- 查看所有用户列表
- 添加新用户
- 编辑用户信息
- 删除用户

### 单词管理
- 查看所有单词列表
- 添加新单词
- 编辑单词信息
- 删除单词

## 技术特性

- **安全性**：简单的登录验证机制
- **响应式设计**：使用Bootstrap框架，支持移动设备
- **表单验证**：服务器端验证和错误处理
- **消息提示**：操作成功/失败的Flash消息提示
- **数据完整性**：支持所有数据库字段的CRUD操作

## 自定义配置

可以通过环境变量修改默认登录凭据：
```bash
export ADMIN_USERNAME=myadmin
export ADMIN_PASSWORD=mypassword
```

## 文件结构

```
views/admin/
├── __init__.py          # 管理蓝图和路由
├── templates/admin/
│   ├── base.html        # 基础模板
│   ├── login.html       # 登录页面
│   ├── index.html       # 管理首页
│   ├── users/
│   │   ├── list.html    # 用户列表
│   │   ├── create.html  # 添加用户
│   │   └── edit.html    # 编辑用户
│   └── words/
│       ├── list.html    # 单词列表
│       ├── create.html  # 添加单词
│       └── edit.html    # 编辑单词
```

## 扩展建议

未来可以添加更多功能：
- 其他数据表的管理界面
- 数据导出功能
- 搜索和筛选功能
- 批量操作功能
- 数据统计和图表展示