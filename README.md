
# OVH 幻影狙击手 - 服务器抢购平台

一个功能全面的 OVH 服务器抢购平台，具有实时服务器列表、可用性检测、自动抢购队列和购买历史跟踪功能。

## 项目信息

**URL**: https://lovable.dev/projects/addef3bc-9ddd-4039-9be8-862af40527b7

## 功能特点

- **仪表盘**: 显示系统状态、统计数据和活跃队列
- **服务器列表**: 浏览所有可用服务器，支持实时可用性检测
- **抢购队列**: 创建和管理自动抢购任务
- **抢购历史**: 查看所有购买记录
- **详细日志**: 实时系统日志
- **API 设置**: 配置 OVH API 凭据和通知选项

## 技术栈

### 前端

- React
- TypeScript
- Tailwind CSS
- Framer Motion (动画)
- React Query (数据获取)
- Axios (API 请求)

### 后端

- Python
- Flask
- OVH API

## 项目结构

```
/
├── src/                     # 前端源代码
│   ├── components/          # React 组件
│   ├── context/             # React Context
│   ├── pages/               # 页面组件
│   └── hooks/               # 自定义 Hooks
│
├── backend/                 # 后端源代码
│   ├── app.py               # 主要的 Flask 应用
│   └── requirements.txt     # Python 依赖
│
└── README.md                # 项目文档
```

## 安装与运行

### 前端

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 后端

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动 Flask 服务器
python app.py
```

## 配置

1. 在 OVH API 网站创建一个 API 应用程序: https://api.ovh.com/createToken/
2. 获取 Application Key, Application Secret 和 Consumer Key
3. 在平台的设置页面输入这些凭据
4. 可选：配置 Telegram 通知

## 使用指南

1. 在设置页面配置 OVH API 凭据
2. 浏览服务器列表，检查可用性
3. 添加目标服务器到抢购队列
4. 监控抢购历史和系统日志

## 贡献

欢迎提交 Issues 和 Pull Requests 来改进本项目。

## 许可证

MIT
