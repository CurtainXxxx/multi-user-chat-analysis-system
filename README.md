# 多人在线聊天与智能分析系统

> Multi-User Online Chat & Intelligent Analysis System

Python 语言程序设计期末综合大作业，融合六大核心技术构建的实时聊天系统。

*A comprehensive Python course project integrating six core technologies: Socket programming, multi-threading, word frequency analysis, web crawling, file I/O, and regular expressions.*

---

## 功能特性 / Features

- 💬 **实时聊天 / Real-time Chat** — WebSocket 长连接，低延迟消息广播
- 🔒 **@私聊 / Private Chat** — 正则匹配目标用户，消息仅对方可见
- 📊 **词频统计 + 词云 / Word Frequency & Cloud** — jieba 分词 + wordcloud 可视化
- 🕷️ **网页爬虫 / Web Crawler** — requests + BeautifulSoup + 正则清洗，支持中英文站点
- 🌓 **暗色主题 / Dark Mode** — CSS 变量换肤，偏好自动保存
- ⌨️ **正在输入 / Typing Indicator** — 实时感知对方打字状态
- 👥 **在线列表 / Online Users** — 加入/离开实时推送更新
- 🛡️ **安全防护 / Security** — XSS 防御（HTML 转义）+ 重名保护

## 技术栈 / Tech Stack

| 技术 / Technology | 说明 / Description |
|------|------|
| **Socket 编程** | TCP Socket + WebSocket 双版本实现 |
| **多线程/异步** | threading（终端版） + asyncio（Web版） |
| **词频统计** | jieba 中文分词 + 停用词过滤 |
| **词云生成** | wordcloud 可视化输出 |
| **网页爬虫** | requests + BeautifulSoup + UA轮换 + SSL降级 |
| **正则表达式** | 命令解析、HTML标签清洗、@私聊匹配 |
| **文件操作** | JSON 格式聊天记录持久化 |
| **Web 框架** | FastAPI（后端） + 原生 HTML/CSS/JS（前端） |

## 项目结构 / Project Structure

```
├── web_server.py      # Web版服务端 (FastAPI + WebSocket) ★ 主演示版本
├── chat_server.py     # 终端版服务端 (TCP + threading)
├── chat_client.py     # 终端版客户端 (双线程收发)
├── static/
│   └── index.html     # Web前端界面 (纯原生，零框架)
└── requirements.txt   # Python 依赖
```

## 快速开始 / Quick Start

### 1. 安装依赖 / Install

```bash
pip install -r requirements.txt
```

### 2. Web 版（推荐）/ Web Version

```bash
python web_server.py
```

浏览器访问 `http://localhost:8888`，打开多个窗口即可多人聊天。

### 3. 终端版 / Terminal Version

```bash
# 启动服务端
python chat_server.py

# 启动客户端（可开多个）
python chat_client.py
```

## 聊天指令 / Commands

| 指令 / Command | 说明 / Description |
|------|------|
| `@username msg` | 私聊指定用户 / Private message |
| `!stat` | 词频统计 TOP5 + 生成词云图 |
| `!crawl <URL>` | 爬取网页并分析 TOP10 关键词 |
| `!quit` | 退出聊天室 / Leave chat room |

## 依赖 / Dependencies

- Python 3.10+
- FastAPI + uvicorn
- jieba（中文分词）
- wordcloud（词云生成）
- requests + beautifulsoup4（网页爬虫）

## License

MIT
