"""
多人在线聊天与智能分析系统 - 终端版服务端
==========================================
技术点：
- TCP Socket 编程（socket 模块）
- 多线程并发（threading 模块，每客户端一个线程）
- 正则表达式（re 模块，指令解析 + HTML清洗）
- 网页爬虫（requests + BeautifulSoup）
- 词频统计（jieba 分词） + 词云生成（wordcloud）
- 文件操作（JSON 格式持久化聊天记录）

启动方式：
    python chat_server.py
"""
import socket
import threading
import json
import re
import os
from datetime import datetime

import jieba
import wordcloud
import requests
from bs4 import BeautifulSoup

# ---------- 配置 ----------
HOST = '0.0.0.0'       # 监听所有网络接口
PORT = 8888             # 服务端口
CHAT_LOG_FILE = 'chat_log.json'           # 聊天记录文件
WORDCLOUD_FILE = '词云图.png'             # 词云图输出文件

# 全局连接列表 + 线程锁
clients = []                              # 元素格式: (username, socket)
clients_lock = threading.Lock()           # 保护 clients 的并发访问

# ---------------------------------------------------------------------------
#  文件操作：聊天记录持久化（JSON 格式）
# ---------------------------------------------------------------------------
def load_chat_log():
    """从 JSON 文件加载历史聊天记录"""
    if os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_chat_log(record):
    """将单条消息（包含时间戳、用户名、内容）追加写入 JSON 文件"""
    log = load_chat_log()
    log.append(record)
    with open(CHAT_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
#  正则表达式应用：HTML 标签清洗
#  依次去除 script/style 标签 → HTML标签 → 实体字符 → 合并空白
# ---------------------------------------------------------------------------
def clean_html(html):
    """用正则清洗网页源码，提取纯文本"""
    # 1. 去除 <script>...</script> 和 <style>...</style> 整块
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
    # 2. 去除所有 HTML 标签 <...>
    clean = re.sub(r'<[^>]+>', '', clean)
    # 3. 去除 HTML 实体字符 &xxx; 和 &#xxx;
    clean = re.sub(r'&[a-zA-Z]+;', ' ', clean)
    clean = re.sub(r'&#?\w+;', ' ', clean)
    # 4. 合并多余空白
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


# ---------------------------------------------------------------------------
#  网页爬虫模块：requests 获取页面 → BeautifulSoup 解析 → 正则清洗 → jieba 分词
# ---------------------------------------------------------------------------
def crawl_and_analyze(url):
    """爬取指定网址，分析页面文本，返回 TOP10 高频词"""
    if not url.startswith('http'):
        url = 'https://' + url

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.encoding = resp.apparent_encoding

    # BeautifulSoup 解析 HTML
    soup = BeautifulSoup(resp.text, 'html.parser')
    # 调用正则清洗函数去除所有标签
    text = clean_html(str(soup))
    if not text:
        return None, None, None

    # jieba 分词 + 停用词过滤
    words = jieba.lcut(text)
    stop_set = {'的', '了', '是', '在', '和', '也', '都', '就', '与', '或', '但', '而', '及',
                '把', '被', '让', '从', '到', '对', '着', '之', '一', '这', '那', '有', '个',
                '很', '要', '会', '可以', '能', '吗', '吧', '呢', '啊', '哦', '嗯', '呀', '什么',
                '怎么', '为什么', '没', '还', '说', '来', '去', '上', '下', '中', '等', '为', '此',
                '其', '以', '及', '可', '如', '该', '通过', '进行', '使用', '一个', '没有', '不是',
                '这个', '那个', '我们', '他们', '自己', '已经', '现在', '因为', '所以', '但是',
                '不过', '然后', '虽然', '如果', 'x', 'nbsp', 'amp',
                # 英文停用词
                'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'to', 'of',
                'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'it', 'its', 'and',
                'or', 'but', 'if', 'not', 'no', 'so', 'than', 'that', 'this', 'will'}
    filtered = [w for w in words if len(w) >= 2 and w not in stop_set]

    # 统计词频
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    top10 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]
    return text[:2000], top10, len(words)


# ---------------------------------------------------------------------------
#  词频统计 + 词云生成：jieba 分词 → 统计 TOP5 → wordcloud 输出 PNG
# ---------------------------------------------------------------------------
def generate_wordcloud(filter_words=None):
    """对聊天记录进行分词统计，生成词云图，返回 TOP5 高频词"""
    if filter_words is None:
        filter_words = set()
    stopwords = {'的', '了', '是', '我', '你', '他', '她', '它', '们', '在', '不', '都', '也',
                 '就', '和', '与', '或', '但', '而', '及', '把', '被', '让', '从', '到', '对',
                 '着', '之', '一', '这', '那', '有', '个', '很', '要', '会', '可以', '能', '吗',
                 '吧', '呢', '啊', '哈', '哦', '嗯', '呀', '嘻嘻', '呵呵', '哈哈', '什么', '怎么',
                 '为什么', '没', '还', '说', '都', '上', '下', '来', '去', '么', '好', '一个', '吧',
                 '没有', '不是', '这个', '那个', '就是', '我们', '你们', '他们', '自己', '知道',
                 '觉得', '如果', '因为', '所以', '但是', '不过', '然后', '虽然', '可以', '应该',
                 '已经', '现在', '今天', '时间', '消息', '聊天', '客户端', '服务端', '发送',
                 'x', 'X', '!stat', '!crawl', '!quit', 'null', 'none', 'true', 'false'}
    all_words = filter_words | stopwords

    # 加载全部聊天记录拼接为长文本
    log = load_chat_log()
    all_text = ' '.join(r['content'] for r in log)

    # jieba 分词 + 停用词过滤
    words = jieba.lcut(all_text)
    filtered = [w for w in words if len(w) >= 2 and w not in all_words]

    # 统计词频 TOP5
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    top5 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]

    # wordcloud 生成词云图
    if freq:
        wc = wordcloud.WordCloud(
            font_path='C:/Windows/Fonts/msyh.ttc',  # 微软雅黑字体路径
            width=800, height=600,
            background_color='white',
            stopwords=all_words
        )
        wc.generate_from_frequencies(freq)
        wc.to_file(WORDCLOUD_FILE)

    return top5


# ---------------------------------------------------------------------------
#  消息广播（线程安全）
# ---------------------------------------------------------------------------
def broadcast(message, sender_conn=None):
    """广播消息给所有客户端（除发送者外）"""
    with clients_lock:
        for name, conn in clients:
            if conn != sender_conn:
                try:
                    conn.send(message.encode('utf-8'))
                except Exception:
                    pass


def broadcast_all(message):
    """广播消息给所有客户端（含发送者）"""
    with clients_lock:
        for _, conn in clients:
            try:
                conn.send(message.encode('utf-8'))
            except Exception:
                pass


# ---------------------------------------------------------------------------
#  客户端处理线程（threading —— 多线程核心）
#  每个客户端连接由一个独立线程处理，主线程继续 accept 新连接
# ---------------------------------------------------------------------------
def handle_client(conn, addr):
    """处理单个客户端连接"""
    username = None
    try:
        # 1. 接收用户名
        username = conn.recv(1024).decode('utf-8').strip()
        if not username:
            conn.close()
            return

        # 2. 注册到 clients 列表（加锁保护共享数据）
        with clients_lock:
            clients.append((username, conn))
        join_msg = f'[系统] {username} 加入了聊天室'
        print(join_msg)
        broadcast_all(join_msg)

        # 3. 消息接收循环
        while True:
            data = conn.recv(8192)
            if not data:
                break
            raw_msg = data.decode('utf-8').strip()
            if not raw_msg:
                continue

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # ----- 正则指令解析 -----
            # !quit —— 退出聊天室
            if re.match(r'^!quit\s*$', raw_msg, re.IGNORECASE):
                quit_msg = f'[系统] {username} 离开了聊天室'
                broadcast_all(quit_msg)
                break

            # !crawl <URL> —— 网页爬虫
            elif re.match(r'^!crawl\s+', raw_msg, re.IGNORECASE):
                url = re.sub(r'^!crawl\s+', '', raw_msg, flags=re.IGNORECASE).strip()
                conn.send(f'[系统] 正在爬取并分析: {url} ...'.encode('utf-8'))
                try:
                    summary, top10, word_count = crawl_and_analyze(url)
                    if summary:
                        words_line = '，'.join(f'{w}({c}次)' for w, c in top10)
                        result = (
                            f'[爬虫分析结果] ({username} 请求)\n'
                            f'页面总词数: {word_count}\n'
                            f'TOP10高频词: {words_line}\n'
                            f'页面摘要: {summary[:500]}...'
                        )
                        broadcast_all(result)
                    else:
                        broadcast_all(f'[爬虫结果] ({username} 请求): 页面无可分析文本')
                except Exception as e:
                    broadcast_all(f'[爬虫失败] ({username} 请求): {str(e)}')

            # !stat —— 词频统计 + 词云
            elif re.match(r'^!stat\s*$', raw_msg, re.IGNORECASE):
                try:
                    top5 = generate_wordcloud(filter_words={username})
                    if top5:
                        words_line = '，'.join(f'{w}({c}次)' for w, c in top5)
                        broadcast_all(f'[词频统计] 当前聊天TOP5高频词: {words_line}')
                        broadcast_all('[系统] 词云图已生成，保存在服务端本地')
                    else:
                        broadcast_all('[词频统计] 暂无足够数据生成词频')
                except Exception as e:
                    conn.send(f'[系统] 词频统计失败: {str(e)}'.encode('utf-8'))

            # 普通消息 —— 添加时间戳 → 存文件 → 广播
            else:
                formatted = f'[{timestamp}] {username}: {raw_msg}'
                print(formatted)
                # 文件操作：持久化存储
                record = {'time': timestamp, 'user': username, 'content': raw_msg}
                save_chat_log(record)
                # 广播给其他用户 + 回显给自己
                broadcast(formatted, sender_conn=conn)
                conn.send(formatted.encode('utf-8'))

    except (ConnectionResetError, ConnectionAbortedError):
        pass  # 客户端异常断开
    finally:
        # 清理：从 clients 列表移除，关闭连接
        if username:
            with clients_lock:
                clients[:] = [(n, c) for n, c in clients if n != username]
        conn.close()
        print(f'[系统] {username} 断开连接')


# ---------------------------------------------------------------------------
#  主入口：Socket TCP 服务端启动
#  socket() → setsockopt(REUSEADDR) → bind() → listen() → accept() 循环
# ---------------------------------------------------------------------------
def main():
    print('=' * 50)
    print('  多人在线聊天与智能分析系统 - 服务端')
    print('=' * 50)
    print(f'  监听地址: {HOST}:{PORT}')
    print(f'  聊天记录: {CHAT_LOG_FILE}')
    print(f'  词云图:   {WORDCLOUD_FILE}')
    print('=' * 50)

    # 创建 TCP Socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 端口复用
    server.bind((HOST, PORT))
    server.listen(10)  # 最大等待连接数
    print('服务端已启动，等待客户端连接...')

    try:
        while True:
            # accept() 阻塞等待新连接
            conn, addr = server.accept()
            print(f'新连接: {addr}')
            # 多线程：为每个客户端创建独立线程
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print('\n服务端正在关闭...')
    finally:
        server.close()


if __name__ == '__main__':
    main()
