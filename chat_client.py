"""
多人在线聊天与智能分析系统 - 终端版客户端
==========================================
技术点：
- TCP Socket 编程（与服务端建立连接）
- 多线程（主线程发消息，后台线程收消息——双线程收发分离）
- 正则表达式（!quit 指令匹配）

启动方式：
    python chat_client.py
"""
import socket
import threading
import re
from datetime import datetime

# ---------- 配置 ----------
HOST = '127.0.0.1'      # 服务端 IP（本机）
PORT = 8888             # 服务端端口


def receive_messages(sock):
    """
    后台线程：持续阻塞接收服务端推送的消息并实时打印
    使用 daemon 线程，主线程退出时自动结束
    """
    while True:
        try:
            data = sock.recv(8192)
            if not data:  # 服务端关闭连接
                print('\n[系统] 与服务端断开连接')
                break
            msg = data.decode('utf-8')
            # \r 清除当前输入行，打印消息后恢复 > 提示符
            print(f'\r{msg}\n> ', end='', flush=True)
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            break


def main():
    print('=' * 50)
    print('  多人在线聊天与智能分析系统 - 客户端')
    print('=' * 50)
    print('指令说明：')
    print('  !crawl <URL>  - 爬取网页并分析内容')
    print('  !stat         - 统计聊天 TOP5 高频词 + 生成词云')
    print('  !quit         - 退出聊天室')
    print('=' * 50)

    # 1. 建立 TCP 连接（三次握手）
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        print(f'[错误] 无法连接到服务端 {HOST}:{PORT}，请确保服务端已启动')
        return

    # 2. 输入姓名并发送给服务端
    name = input('请输入你的姓名（必须使用真实姓名）：').strip()
    while not name:
        name = input('姓名不能为空，请重新输入：').strip()
    sock.send(name.encode('utf-8'))

    # 3. 启动后台接收线程（多线程核心）
    recv_thread = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    recv_thread.start()

    # 4. 主线程：读取用户输入并发送
    try:
        while True:
            msg = input('> ').strip()
            if not msg:
                continue
            sock.send(msg.encode('utf-8'))
            # 正则匹配 !quit 指令
            if re.match(r'^!quit\s*$', msg, re.IGNORECASE):
                break
    except KeyboardInterrupt:
        # Ctrl+C 优雅退出
        sock.send('!quit'.encode('utf-8'))
    finally:
        sock.close()
        print('已退出聊天室')


if __name__ == '__main__':
    main()
