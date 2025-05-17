
# OVH 幻影狙击手 - 后端服务

这是 OVH 幻影狙击手的后端 API 服务，基于 Flask 开发，提供 RESTful API 接口以支持前端应用。

## 功能

- OVH API 集成
- 服务器列表查询与可用性检测
- 抢购队列管理
- 购买历史记录
- 系统日志
- Telegram 通知

## 安装与运行

1. 确保安装了 Python 3.7 或更高版本

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 运行服务

```bash
python app.py
```

服务将在 `http://localhost:5000` 启动，可通过 API 端点访问。

## API 端点

### 设置管理

- `GET /api/settings` - 获取当前 API 设置
- `POST /api/settings` - 更新 API 设置
- `POST /api/verify-auth` - 验证 API 凭据

### 日志管理

- `GET /api/logs` - 获取系统日志
- `DELETE /api/logs` - 清空系统日志

### 抢购队列

- `GET /api/queue` - 获取抢购队列
- `POST /api/queue` - 添加新的抢购任务
- `DELETE /api/queue/<id>` - 移除抢购任务
- `PUT /api/queue/<id>/status` - 更新抢购任务状态

### 购买历史

- `GET /api/purchase-history` - 获取购买历史
- `DELETE /api/purchase-history` - 清空购买历史

### 服务器管理

- `GET /api/servers` - 获取服务器列表
- `GET /api/availability/<plan_code>` - 检查特定服务器计划的可用性

### 统计信息

- `GET /api/stats` - 获取系统统计信息

## 数据存储

数据存储在以下 JSON 文件中：

- `config.json` - API 设置
- `logs.json` - 系统日志
- `queue.json` - 抢购队列
- `history.json` - 购买历史
- `servers.json` - 服务器列表缓存
