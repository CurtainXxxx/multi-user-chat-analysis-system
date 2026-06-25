# 多人在线聊天与智能分析系统

Python 语言程序设计期末综合大作业，融合六大核心技术构建的实时聊天系统。

## 功能特性

- 💬 **多人在线实时聊天** — WebSocket 长连接，低延迟广播
- 🔒 **@私聊** — 正则匹配目标用户，消息仅对方可见
- 📊 **词频统计 + 词云** — jieba 分词 + wordcloud 可视化
- 🕷️ **网页爬虫** — requests + BeautifulSoup + 正则清洗，支持中英文
- 🌓 **暗色/亮色主题** — CSS变量换肤，偏好自动保存
- ⌨️ **正在输入提示** — 实时感知对方打字状态
- 👥 **在线用户列表** — 加入/离开实时推送
- 🛡️ **安全防护** — XSS防御（HTML转义）+ 重名保护

## 技术栈

| 技术 | 说明 |
|------|------|
| **Socket 编程** | TCP Socket（终端版）+ WebSocket（Web版）|
| **多线程/异步** | threading（终端版）+ asyncio（Web版）|
| **词频统计** | jieba 中文分词 + 停用词过滤 |
| **词云生成** | wordcloud 可视化输出 |
| **网页爬虫** | requests + BeautifulSoup + UA轮换 + SSL降级 |
| **正则表达式** | 命令解析、HTML标签清洗、@私聊匹配 |
| **文件操作** | JSON 格式聊天记录持久化 |
| **Web 框架** | FastAPI（Python）+ 原生 HTML/CSS/JS（前端）|

## 项目结构

```
├── web_server.py      # Web版服务端（FastAPI + WebSocket）★ 主演示版本
├── chat_server.py     # 终端版服务端（TCP + threading）
├── chat_client.py     # 终端版客户端（双线程收发）
├── static/
│   └── index.html     # Web前端界面（纯原生，零框架）
└── requirements.txt   # Python 依赖
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Web 版（推荐）

```bash
python web_server.py
```

浏览器访问 `http://localhost:8888`，打开多个窗口即可多人聊天。

### 3. 启动终端版

```bash
# 先启动服务端
python chat_server.py

# 再启动客户端（可开多个）
python chat_client.py
```

## 聊天指令

| 指令 | 说明 |
|------|------|
| `@用户名 消息` | 私聊指定用户 |
| `!stat` | 统计当前聊天 TOP5 高频词 + 生成词云图 |
| `!crawl <URL>` | 爬取网页并分析 TOP10 关键词 |
| `!quit` | 退出聊天室 |

## 依赖

- Python 3.10+
- FastAPI + uvicorn
- jieba（中文分词）
- wordcloud（词云生成）
- requests + beautifulsoup4（爬虫）
- python-docx（文档生成）

## License

MIT
