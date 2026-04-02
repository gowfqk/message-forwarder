#!/usr/bin/env python3
"""
消息推送转发服务 - Web 管理界面
Linux/跨平台版本
"""

import json
import os
import subprocess
import threading
import signal
import sys
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory

# 项目根目录
BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / 'config.json'
LOG_FILE = BASE_DIR / 'logs' / 'forward.log'
TOKEN_CACHE = BASE_DIR / 'cache' / 'tokens.json'
PID_FILE = BASE_DIR / 'web' / '.server.pid'
SERVER_PID_FILE = BASE_DIR / '.server.pid'

app = Flask(__name__, 
            template_folder=Path(__file__).parent / 'templates',
            static_folder=Path(__file__).parent / 'static')

# 服务进程
server_process = None


def load_config():
    """加载配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_config(config):
    """保存配置"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_server_status():
    """获取服务运行状态"""
    global server_process
    
    # 检查 PID 文件
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # 检查进程是否存在
            os.kill(pid, 0)
            return {'running': True, 'pid': pid}
        except (ProcessLookupError, ValueError, PermissionError):
            PID_FILE.unlink(missing_ok=True)
    
    return {'running': False, 'pid': None}


def start_server():
    """启动转发服务"""
    global server_process
    
    if get_server_status()['running']:
        return False, '服务已在运行'
    
    try:
        # 启动 server.py
        server_script = BASE_DIR / 'server.py'
        server_process = subprocess.Popen(
            [sys.executable, str(server_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(BASE_DIR),
            start_new_session=True  # Linux: 创建新会话
        )
        
        # 保存 PID
        with open(PID_FILE, 'w') as f:
            f.write(str(server_process.pid))
        
        return True, f'服务已启动 (PID: {server_process.pid})'
    except Exception as e:
        return False, f'启动失败：{str(e)}'


def stop_server():
    """停止转发服务"""
    global server_process
    
    status = get_server_status()
    if not status['running']:
        return False, '服务未运行'
    
    try:
        pid = status['pid']
        
        # Linux: 发送 SIGTERM
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        
        # 等待进程结束
        try:
            os.waitpid(pid, os.WNOHANG)
        except:
            pass
        
        # 强制结束
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except:
            pass
        
        PID_FILE.unlink(missing_ok=True)
        
        return True, '服务已停止'
    except Exception as e:
        return False, f'停止失败：{str(e)}'


def restart_server():
    """重启转发服务"""
    # 先停止
    stop_server()
    
    import time
    time.sleep(1)  # 等待进程完全停止
    
    # 启动新进程
    try:
        server_script = BASE_DIR / 'server.py'
        
        # 使用当前 Python 解释器
        python_exec = sys.executable
        
        # 如果是嵌入式 Python，可能需要特殊处理
        if 'embed' in python_exec:
            # 尝试查找系统 Python
            for path in ['/usr/bin/python3', '/usr/bin/python', 'python', 'python3']:
                try:
                    subprocess.run([path, '--version'], check=True, capture_output=True)
                    python_exec = path
                    break
                except:
                    continue
        
        process = subprocess.Popen(
            [python_exec, str(server_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(BASE_DIR),
            start_new_session=True
        )
        
        # 保存 PID
        with open(SERVER_PID_FILE, 'w') as f:
            f.write(str(process.pid))
        
        return True, f'服务已重启 (PID: {process.pid})'
    except Exception as e:
        return False, f'重启失败：{str(e)}'


def get_logs(lines=100):
    """获取日志"""
    if not LOG_FILE.exists():
        return []
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except:
        return []


def test_channel(channel_type):
    """测试渠道连接"""
    config = load_config()
    channel = config.get('channels', {}).get(channel_type, {})
    
    if not channel.get('enabled'):
        return False, '渠道未启用'
    
    import urllib.request
    
    if channel_type == 'wechat_app':
        # 测试企业微信应用
        corpid = channel.get('corpid', '')
        corpsecret = channel.get('corpsecret', '')
        
        if not corpid or not corpsecret:
            return False, '未配置 Corp ID 或 Secret'
        
        url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={corpsecret}'
        
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get('errcode') == 0:
                    return True, f'Token 获取成功，有效期 {data.get("expires_in")}s'
                else:
                    return False, data.get('errmsg', 'Unknown error')
        except Exception as e:
            return False, str(e)
    
    elif channel_type == 'wechat_webhook':
        # 测试企业微信机器人
        url = channel.get('url', '')
        if not url:
            return False, '未配置 Webhook URL'
        
        payload = json.dumps({'msgtype': 'text', 'text': {'content': '测试消息'}}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get('errcode') == 0:
                    return True, '发送成功'
                else:
                    return False, data.get('errmsg', 'Unknown error')
        except Exception as e:
            return False, str(e)
    
    elif channel_type == 'dingtalk':
        # 测试钉钉机器人
        url = channel.get('url', '')
        if not url:
            return False, '未配置 Webhook URL'
        
        payload = json.dumps({'msgtype': 'text', 'text': {'content': '测试消息'}}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get('errcode') == 0:
                    return True, '发送成功'
                else:
                    return False, data.get('errmsg', 'Unknown error')
        except Exception as e:
            return False, str(e)
    
    elif channel_type == 'telegram':
        # 测试 Telegram Bot
        bot_token = channel.get('botToken', '')
        chat_id = channel.get('chatId', '')
        
        if not bot_token or not chat_id:
            return False, '未配置 Bot Token 或 Chat ID'
        
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        payload = json.dumps({
            'chat_id': chat_id,
            'text': '🧪 测试消息\n\n这是一条测试消息，用于验证 Telegram 推送功能。'
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get('ok'):
                    return True, '发送成功'
                else:
                    return False, data.get('description', 'Unknown error')
        except Exception as e:
            return False, str(e)
    
    elif channel_type == 'email':
        # 测试邮件发送
        smtp_host = channel.get('smtpHost', '')
        smtp_port = channel.get('smtpPort', 587)
        username = channel.get('username', '')
        password = channel.get('password', '')
        to_email = channel.get('to', '')
        
        if not smtp_host or not username or not password or not to_email:
            return False, '未配置完整的 SMTP 信息'
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = to_email
            msg['Subject'] = '🧪 邮件通知测试'
            
            body = '''
这是一封测试邮件，用于验证邮件通知功能是否正常。

如果您收到这封邮件，说明 SMTP 配置正确。

发送时间：{}
            '''.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 连接 SMTP 服务器并发送
            if smtp_port == 465:
                # SSL 连接
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
            else:
                # 普通连接 + STARTTLS
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                server.starttls()
            
            server.login(username, password)
            server.sendmail(username, [to_email], msg.as_string())
            server.quit()
            
            return True, '邮件发送成功，请查收'
        except smtplib.SMTPAuthenticationError:
            return False, 'SMTP 认证失败，请检查用户名和密码'
        except smtplib.SMTPConnectError:
            return False, f'无法连接 SMTP 服务器 {smtp_host}:{smtp_port}'
        except Exception as e:
            return False, f'发送失败：{type(e).__name__}: {e}'
    
    return False, '不支持的渠道类型'


# ==================== Web 路由 ====================

@app.route('/')
def index():
    """管理首页"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """获取服务状态"""
    status = get_server_status()
    config = load_config()
    
    # 获取 token 缓存状态
    token_cached = False
    if TOKEN_CACHE.exists():
        try:
            with open(TOKEN_CACHE, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
                token_cached = bool(token_data.get('wechat_app', {}).get('access_token'))
        except:
            pass
    
    return jsonify({
        'running': status['running'],
        'pid': status['pid'],
        'config_loaded': bool(config),
        'token_cached': token_cached,
        'channels': {
            'wechat_webhook': config.get('channels', {}).get('wechat_webhook', {}).get('enabled', False),
            'wechat_app': config.get('channels', {}).get('wechat_app', {}).get('enabled', False),
            'dingtalk': config.get('channels', {}).get('dingtalk', {}).get('enabled', False),
            'telegram': config.get('channels', {}).get('telegram', {}).get('enabled', False)
        }
    })


@app.route('/api/config', methods=['GET'])
def api_get_config():
    """获取配置"""
    config = load_config()
    # 隐藏敏感信息
    if 'auth' in config and 'token' in config['auth']:
        config['auth']['token'] = config['auth']['token'][:4] + '****' if len(config['auth']['token']) > 4 else '****'
    
    channels = config.get('channels', {})
    if 'wechat_app' in channels:
        channels['wechat_app']['corpsecret'] = '****' if channels['wechat_app'].get('corpsecret') else ''
    
    return jsonify(config)


@app.route('/api/config', methods=['POST'])
def api_save_config():
    """保存配置"""
    try:
        new_config = request.json
        
        # 加载现有配置（保留敏感信息）
        current_config = load_config()
        
        # 如果新配置中的 token 是掩码，使用旧值
        if new_config.get('auth', {}).get('token', '').endswith('****'):
            new_config['auth']['token'] = current_config.get('auth', {}).get('token', '')
        
        # 如果新配置中的 corpsecret 是掩码，使用旧值
        if new_config.get('channels', {}).get('wechat_app', {}).get('corpsecret', '') == '****':
            new_config['channels']['wechat_app']['corpsecret'] = current_config.get('channels', {}).get('wechat_app', {}).get('corpsecret', '')
        
        save_config(new_config)
        return jsonify({'success': True, 'message': '配置已保存'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/server/start', methods=['POST'])
def api_start_server():
    """启动服务"""
    success, message = start_server()
    return jsonify({'success': success, 'message': message})


@app.route('/api/server/stop', methods=['POST'])
def api_stop_server():
    """停止服务"""
    success, message = stop_server()
    return jsonify({'success': success, 'message': message})


@app.route('/api/server/restart', methods=['POST'])
def api_restart_server():
    """重启服务"""
    success, message = restart_server()
    return jsonify({'success': success, 'message': message})


@app.route('/api/logs')
def api_get_logs():
    """获取日志"""
    lines = request.args.get('lines', 100, type=int)
    logs = get_logs(lines)
    return jsonify({'logs': logs})


@app.route('/api/test/<channel_type>', methods=['POST'])
def api_test_channel(channel_type):
    """测试渠道"""
    success, message = test_channel(channel_type)
    return jsonify({'success': success, 'message': message})


@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory(Path(__file__).parent / 'static', filename)


if __name__ == '__main__':
    import os
    print('=' * 50)
    print('  消息推送转发服务 - Web 管理界面')
    print('=' * 50)
    print(f'  访问地址：http://localhost:5000')
    print('=' * 50)
    
    # 生产环境使用 waitress，开发环境使用 Flask
    try:
        from waitress import serve
        print('[Production] Starting with Waitress...')
        serve(app, host='0.0.0.0', port=5000, threads=4)
    except ImportError:
        print('[Development] Starting with Flask...')
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
