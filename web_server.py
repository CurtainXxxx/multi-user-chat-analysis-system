"""
多人在线聊天与智能分析系统 - Web版服务端
FastAPI + WebSocket，替代原 chat_server.py 的 Socket 通信
"""
import json
import re
import os
from datetime import datetime

import jieba
import wordcloud
import requests
from bs4 import BeautifulSoup

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# ---------- 配置 ----------
HOST = '0.0.0.0'
PORT = 8888
CHAT_LOG_FILE = 'chat_log.json'
WORDCLOUD_FILE = '词云图-费枭健.png'

# ---------- WebSocket 连接管理 ----------
class ConnectionManager:
    """管理所有 WebSocket 连接"""
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}  # username -> websocket

    def connect(self, username: str, ws: WebSocket):
        self.connections[username] = ws

    def disconnect(self, username: str):
        self.connections.pop(username, None)

    async def broadcast(self, message: str, sender: str = None):
        """广播给所有人（除发送者外）"""
        for name, ws in list(self.connections.items()):
            if name != sender:
                try:
                    await ws.send_text(message)
                except Exception:
                    pass

    async def broadcast_all(self, message: str):
        """广播给所有人（含发送者）"""
        for name, ws in list(self.connections.items()):
            try:
                await ws.send_text(message)
            except Exception:
                pass

    async def send_to(self, username: str, message: str):
        """发送给指定用户"""
        ws = self.connections.get(username)
        if ws:
            try:
                await ws.send_text(message)
            except Exception:
                pass

    def get_users(self) -> list[str]:
        return list(self.connections.keys())

    async def broadcast_users(self):
        """推送在线用户列表给所有人"""
        users = self.get_users()
        data = json.dumps({"type": "userlist", "users": users})
        for name, ws in list(self.connections.items()):
            try:
                await ws.send_text(data)
            except Exception:
                pass

manager = ConnectionManager()

# ---------- 文件操作 ----------
def load_chat_log():
    if os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_chat_log(record):
    log = load_chat_log()
    log.append(record)
    with open(CHAT_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

# ---------- 正则：HTML清洗 ----------
def clean_html(html):
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = re.sub(r'&[a-zA-Z]+;', ' ', clean)
    clean = re.sub(r'&#?\w+;', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

# ---------- 网页爬虫 ----------
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def crawl_and_analyze(url):
    if not url.startswith('http'):
        url = 'https://' + url

    # 多组 User-Agent，模拟不同浏览器
    ua_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    ]

    last_error = ""
    for attempt in range(2):
        headers = {
            'User-Agent': ua_list[attempt % len(ua_list)],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
        }
        try:
            resp = requests.get(url, headers=headers, timeout=15,
                              allow_redirects=True, verify=False)
            if resp.status_code == 403:
                last_error = "网站拒绝访问(403)"
                continue
            if resp.status_code >= 400:
                last_error = f"HTTP {resp.status_code}"
                continue

            resp.encoding = resp.apparent_encoding or 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 去掉不可见标签
            for tag in soup(['script', 'style', 'meta', 'link', 'noscript']):
                tag.decompose()

            text = clean_html(str(soup))
            if not text or len(text) < 20:
                last_error = "页面文本太少，无法分析"
                continue

            # 分词 + 词频 TOP10
            words = jieba.lcut(text)
            stop_set = {'的','了','是','在','和','也','都','就','与','或','但','而','及',
                        '把','被','让','从','到','对','着','之','一','这','那','有','个',
                        '很','要','会','可以','能','吗','吧','呢','啊','哦','嗯','呀','什么',
                        '怎么','为什么','没','还','说','来','去','上','下','中','等','为','此',
                        '其','以','及','可','如','该','通过','进行','使用','一个','没有','不是',
                        '这个','那个','我们','他们','自己','已经','现在','因为','所以','但是',
                        '不过','然后','虽然','如果','x','nbsp','amp','gt','lt','quot','http','https',
                        # 英文停用词
                        'the','a','an','is','are','was','were','be','been','being',
                        'have','has','had','do','does','did','will','would','could','should',
                        'may','might','can','shall','to','of','in','for','on','with','at','by',
                        'from','as','into','through','during','before','after','above','below',
                        'between','under','again','further','then','once','here','there','when',
                        'where','why','how','all','both','each','few','more','most','other',
                        'some','such','no','nor','not','only','own','same','so','than','too',
                        'very','just','because','but','and','or','if','while','about','up',
                        'out','off','over','its','it','he','she','they','them','we','you',
                        'me','my','your','his','her','their','our','us','i','am','re','ve',
                        'this','that','these','those','which','who','whom','what','also',
                        'any','s','t','don','don\'t','doesn\'t','aren\'t','isn\'t','wasn\'t'}
            filtered = [w for w in words if len(w) >= 2 and w not in stop_set]
            freq = {}
            for w in filtered:
                freq[w] = freq.get(w, 0) + 1
            top10 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]
            return text[:2000], top10, len(words)

        except requests.exceptions.SSLError:
            last_error = "SSL证书错误，可尝试 http:// 开头"
            if url.startswith('https://'):
                url = url.replace('https://', 'http://', 1)  # 降级到HTTP重试
        except requests.exceptions.ConnectTimeout:
            last_error = "连接超时，网站可能无法访问"
        except requests.exceptions.ReadTimeout:
            last_error = "读取超时，网站响应太慢"
        except requests.exceptions.ConnectionError:
            last_error = "无法连接，请检查网址是否正确"
        except requests.exceptions.TooManyRedirects:
            last_error = "重定向次数过多"
        except Exception as e:
            last_error = f"爬取异常: {str(e)[:50]}"

    raise Exception(last_error or "爬取失败，请检查网址")

# ---------- 词频统计 + 词云 ----------
def generate_wordcloud(filter_words=None):
    if filter_words is None:
        filter_words = set()
    stopwords = {'的','了','是','我','你','他','她','它','们','在','不','都','也',
                 '就','和','与','或','但','而','及','把','被','让','从','到','对',
                 '着','之','一','这','那','有','个','很','要','会','可以','能','吗',
                 '吧','呢','啊','哈','哦','嗯','呀','嘻嘻','呵呵','哈哈','什么','怎么',
                 '为什么','没','还','说','都','上','下','来','去','么','好','一个','吧',
                 '没有','不是','这个','那个','就是','我们','你们','他们','自己','知道',
                 '觉得','如果','因为','所以','但是','不过','然后','虽然','可以','应该',
                 '已经','现在','今天','时间','消息','聊天','客户端','服务端','发送',
                 'x','X','!stat','!crawl','!quit','null','none','true','false',
                 # 英文停用词
                 'the','a','an','is','are','was','were','be','been','being',
                 'have','has','had','do','does','did','will','would','could','should',
                 'may','might','can','shall','to','of','in','for','on','with','at','by',
                 'from','as','into','through','during','before','after','above','below',
                 'between','under','again','further','then','once','here','there','when',
                 'where','why','how','all','both','each','few','more','most','other',
                 'some','such','no','nor','not','only','own','same','so','than','too',
                 'very','just','because','but','and','or','if','while','about','up',
                 'out','off','over','its','it','he','she','they','them','we','you',
                 'me','my','your','his','her','their','our','us','i','am','re','ve',
                 'this','that','these','those','which','who','whom','what','also',
                 'any','s','t','don','don\'t','doesn\'t','aren\'t','isn\'t','wasn\'t'}
    all_words = filter_words | stopwords

    log = load_chat_log()
    all_text = ' '.join(r['content'] for r in log)
    words = jieba.lcut(all_text)
    filtered = [w for w in words if len(w) >= 2 and w not in all_words]

    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    top5 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]

    if freq:
        wc = wordcloud.WordCloud(
            font_path='C:/Windows/Fonts/msyh.ttc',
            width=800, height=600,
            background_color='white',
            stopwords=all_words
        )
        wc.generate_from_frequencies(freq)
        wc.to_file(WORDCLOUD_FILE)

    return top5

# ---------- FastAPI 应用 ----------
app = FastAPI(title="多人在线聊天与智能分析系统")

@app.get("/")
async def index():
    """返回聊天页面"""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return HTMLResponse("<h1>static/index.html 未找到</h1>", status_code=404)

@app.get("/wordcloud")
async def get_wordcloud():
    """返回词云图"""
    if os.path.exists(WORDCLOUD_FILE):
        return FileResponse(WORDCLOUD_FILE)
    return HTMLResponse("词云图尚未生成", status_code=404)

@app.get("/users")
async def get_users():
    """返回在线用户列表"""
    return {"users": manager.get_users()}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket 聊天端点"""
    username = None
    connected = False
    try:
        # 1. 先完成 WebSocket 握手
        await ws.accept()

        # 2. 等待客户端发送用户名
        data = await ws.receive_text()
        username = data.strip()
        if not username:
            await ws.close()
            return

        # 检查重名
        if username in manager.connections:
            await ws.send_text(json.dumps({
                "type": "system", "content": f'❌ 用户名 "{username}" 已被占用，请换一个名字重新登录'
            }))
            await ws.close()
            return

        manager.connect(username, ws)
        connected = True

        # 给新用户发送历史记录（最近50条）
        history = load_chat_log()
        if history:
            for record in history[-50:]:
                await ws.send_text(json.dumps({
                    "type": "chat",
                    "user": record["user"],
                    "time": record["time"],
                    "content": record["content"],
                    "self": record["user"] == username
                }))

        # 广播加入通知 + 推送在线列表
        join_msg = f'🟢 {username} 加入了聊天室'
        print(join_msg)
        await manager.broadcast_all(json.dumps({
            "type": "system", "content": join_msg
        }))
        await manager.broadcast_users()

        # 消息循环
        while True:
            raw_msg = await ws.receive_text()
            raw_msg = raw_msg.strip()
            if not raw_msg:
                continue

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # ---- !quit ----
            if re.match(r'^!quit\s*$', raw_msg, re.IGNORECASE):
                break  # 退出循环，由 finally 处理清理

            # ---- !crawl <url> ----
            elif re.match(r'^!crawl\s+', raw_msg, re.IGNORECASE):
                url = re.sub(r'^!crawl\s+', '', raw_msg, flags=re.IGNORECASE).strip()
                await manager.send_to(username, json.dumps({
                    "type": "system", "content": f'⏳ 正在爬取并分析: {url} ...'
                }))
                try:
                    summary, top10, word_count = crawl_and_analyze(url)
                    if summary:
                        words_line = '，'.join(f'{w}({c}次)' for w, c in top10)
                        result = (
                            f'📊 爬虫分析结果（{username} 请求）\n'
                            f'页面总词数: {word_count}\n'
                            f'TOP10高频词: {words_line}\n'
                            f'页面摘要: {summary[:500]}...'
                        )
                        await manager.broadcast_all(json.dumps({
                            "type": "system", "content": result
                        }))
                    else:
                        await manager.broadcast_all(json.dumps({
                            "type": "system", "content": f'📊 爬虫结果（{username} 请求）: 页面无可分析文本'
                        }))
                except Exception as e:
                    await manager.broadcast_all(json.dumps({
                        "type": "system", "content": f'❌ 爬虫失败（{username} 请求）: {str(e)}'
                    }))

            # ---- !stat ----
            elif re.match(r'^!stat\s*$', raw_msg, re.IGNORECASE):
                try:
                    top5 = generate_wordcloud(filter_words={username})
                    if top5:
                        words_line = '，'.join(f'{w}({c}次)' for w, c in top5)
                        await manager.broadcast_all(json.dumps({
                            "type": "stat",
                            "content": f'📈 当前聊天TOP5高频词: {words_line}',
                            "words": [{"word": w, "count": c} for w, c in top5],
                            "wordcloud": "/wordcloud"
                        }))
                    else:
                        await manager.broadcast_all(json.dumps({
                            "type": "system", "content": '📈 词频统计: 暂无足够数据'
                        }))
                except Exception as e:
                    await manager.send_to(username, json.dumps({
                        "type": "system", "content": f'❌ 词频统计失败: {str(e)}'
                    }))

            # ---- !typing（正在输入指示）----
            elif re.match(r'^!typing\s*$', raw_msg, re.IGNORECASE):
                await manager.broadcast(json.dumps({
                    "type": "typing", "user": username
                }), sender=username)

            # ---- 普通消息 ----
            else:
                # @用户名 私聊
                at_match = re.match(r'^@(\S+)\s+(.+)', raw_msg)
                if at_match:
                    target, private_msg = at_match.group(1), at_match.group(2)
                    if target in manager.connections:
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        whisper = f'[{timestamp}] 🔒 {username} 对你说: {private_msg}'
                        await manager.send_to(target, json.dumps({
                            "type": "whisper", "user": username,
                            "time": timestamp, "content": whisper
                        }))
                        await manager.send_to(username, json.dumps({
                            "type": "whisper", "user": username,
                            "time": timestamp, "content": f'🔒 你对 {target} 说: {private_msg}',
                            "self": True
                        }))
                    else:
                        await manager.send_to(username, json.dumps({
                            "type": "system", "content": f'❌ 用户 "{target}" 不在线'
                        }))
                else:
                    print(f'[{timestamp}] {username}: {raw_msg}')
                    record = {"time": timestamp, "user": username, "content": raw_msg}
                    save_chat_log(record)

                    await manager.broadcast(json.dumps({
                        "type": "chat",
                        "user": username,
                        "time": timestamp,
                        "content": raw_msg
                    }), sender=username)

                    # 回显给自己
                    await manager.send_to(username, json.dumps({
                        "type": "chat",
                        "user": username,
                        "time": timestamp,
                        "content": raw_msg,
                        "self": True
                    }))

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if connected:
            manager.disconnect(username)
            leave_msg = f'🔴 {username} 离开了聊天室'
            print(leave_msg)
            try:
                await manager.broadcast_all(json.dumps({
                    "type": "system", "content": leave_msg
                }))
                await manager.broadcast_users()
            except Exception:
                pass
            try:
                await ws.close()
            except Exception:
                pass

# ---------- 主入口 ----------
def main():
    print('=' * 50)
    print('  多人在线聊天与智能分析系统 - Web版')
    print('=' * 50)
    print(f'  访问地址: http://localhost:{PORT}')
    print(f'  聊天记录: {CHAT_LOG_FILE}')
    print(f'  词云图:   {WORDCLOUD_FILE}')
    print('=' * 50)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")

if __name__ == '__main__':
    main()
