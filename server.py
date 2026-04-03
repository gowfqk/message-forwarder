#!/usr/bin/env python3
"""
消息推送转发服务 - Python 版本
接收 Webhook 消息并转发到多个渠道
支持企业微信自建应用自动刷新 token
"""

import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time

# 加载配置（支持环境变量 CONFIG_PATH）
import os
config_path = os.environ.get('CONFIG_PATH')
if config_path:
    CONFIG_PATH = Path(config_path)
else:
    # 优先使用 config/config.json，兼容旧的 config.json
    CONFIG_PATH = Path(__file__).parent / 'config' / 'config.json'
    if not CONFIG_PATH.exists():
        CONFIG_PATH = Path(__file__).parent / 'config.json'
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

# 确保目录存在
LOG_FILE = Path(CONFIG['logFile'])
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

TOKEN_CACHE = Path(CONFIG.get('token_cache', {}).get('file', 'cache/tokens.json'))
TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)

# 配置日志（解决中文乱码）
import sys
import io

# 确保控制台输出 UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(stream=sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Token 缓存
token_cache = {
    'wechat_app': {
        'access_token': None,
        'expires_at': None,
        'expires_in': 7200
    }
}

# 加载缓存的 token
def load_token_cache():
    global token_cache
    if TOKEN_CACHE.exists():
        try:
            with open(TOKEN_CACHE, 'r', encoding='utf-8') as f:
                token_cache = json.load(f)
            logger.info('Loaded token cache from file')
        except Exception as e:
            logger.warning(f'Failed to load token cache: {e}')

# 保存 token 缓存
def save_token_cache():
    try:
        with open(TOKEN_CACHE, 'w', encoding='utf-8') as f:
            json.dump(token_cache, f, indent=2)
    except Exception as e:
        logger.error(f'Failed to save token cache: {e}')

# 获取企业微信应用 access_token
def get_wechat_app_token():
    """获取或刷新企业微信应用 access_token"""
    channel = CONFIG['channels'].get('wechat_app', {})
    
    if not channel.get('enabled'):
        return None
    
    corpid = channel.get('corpid', '')
    corpsecret = channel.get('corpsecret', '')
    
    if not corpid or not corpsecret:
        logger.error('WeChat App: corpid or corpsecret not configured')
        return None
    
    # 验证 CorpID 格式
    if not corpid.startswith('ww') and not corpid.startswith('wx'):
        logger.error(f'WeChat App: Invalid CorpID format - should start with "ww" or "wx", got: {corpid[:5]}...')
        return None
    
    # 验证 CorpSecret 格式（应该是 43 位字母数字）
    if len(corpsecret) < 20:
        logger.error(f'WeChat App: Invalid CorpSecret format - too short, got length: {len(corpsecret)}')
        return None
    
    cached = token_cache.get('wechat_app', {})
    expires_at = cached.get('expires_at')
    
    # 检查缓存是否有效（提前 5 分钟刷新）
    refresh_ahead = CONFIG.get('token_cache', {}).get('refresh_ahead', 300)
    
    if expires_at:
        expiry_time = datetime.fromisoformat(expires_at) if isinstance(expires_at, str) else datetime.fromtimestamp(expires_at)
        if datetime.now() < expiry_time - timedelta(seconds=refresh_ahead):
            logger.info('WeChat App: Using cached access_token')
            return cached.get('access_token')
    
    # 获取新 token
    url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={corpsecret}'
    
    logger.info(f'WeChat App: Requesting token with CorpID: {corpid[:6]}...')
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            if data.get('errcode') == 0:
                access_token = data.get('access_token')
                expires_in = data.get('expires_in', 7200)
                
                token_cache['wechat_app'] = {
                    'access_token': access_token,
                    'expires_in': expires_in,
                    'expires_at': (datetime.now() + timedelta(seconds=expires_in)).isoformat()
                }
                save_token_cache()
                
                logger.info(f'WeChat App: Token refreshed successfully, expires in {expires_in}s')
                return access_token
            else:
                errcode = data.get('errcode')
                errmsg = data.get('errmsg', 'Unknown error')
                logger.error(f"WeChat App: Failed to get token - ErrCode: {errcode}, ErrMsg: {errmsg}")
                
                # 提供详细的错误说明
                if errcode == 40013:
                    logger.error('WeChat App: 40013 - CorpID 或 CorpSecret 无效')
                    logger.error('  可能原因:')
                    logger.error('  1. CorpID 填写错误（应包含 ww 或 wx 前缀）')
                    logger.error('  2. CorpSecret 填写错误（应用 Secret，不是企业 Secret）')
                    logger.error('  3. 应用已被删除或禁用')
                    logger.error('  4. 复制时多了空格或隐藏字符')
                elif errcode == 40002:
                    logger.error('WeChat App: 40002 - 参数类型错误（检查 config.json 格式）')
                elif errcode == 60020:
                    logger.error('WeChat App: 60020 - 企业未授权此应用')
                
                return None
    except urllib.error.HTTPError as e:
        logger.error(f'WeChat App: HTTP Error {e.code} - {e.reason}')
        return None
    except Exception as e:
        logger.error(f'WeChat App: Error getting token - {type(e).__name__}: {e}')
        return None

# 定时刷新 token
def token_refresh_loop():
    """后台线程：定时刷新 token"""
    while True:
        time.sleep(60)  # 每分钟检查一次
        
        channel = CONFIG['channels'].get('wechat_app', {})
        if not channel.get('enabled'):
            continue
        
        cached = token_cache.get('wechat_app', {})
        expires_at = cached.get('expires_at')
        
        if expires_at:
            expiry_time = datetime.fromisoformat(expires_at) if isinstance(expires_at, str) else datetime.fromtimestamp(expires_at)
            refresh_ahead = CONFIG.get('token_cache', {}).get('refresh_ahead', 300)
            
            if datetime.now() >= expiry_time - timedelta(seconds=refresh_ahead):
                logger.info('WeChat App: Auto-refreshing token...')
                get_wechat_app_token()


def send_http_request(url, method='POST', headers=None, data=None, ensure_ascii=False):
    """发送 HTTP 请求"""
    if headers is None:
        headers = {'Content-Type': 'application/json; charset=utf-8'}
    
    # 确保中文正确编码
    body = json.dumps(data, ensure_ascii=ensure_ascii).encode('utf-8') if data else None
    
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return {
                'success': True,
                'status': response.status,
                'body': response.read().decode('utf-8')
            }
    except urllib.error.HTTPError as e:
        return {
            'success': False,
            'status': e.code,
            'error': e.reason,
            'body': e.read().decode('utf-8') if e.fp else ''
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def send_to_wechat_webhook(message, original_data):
    """发送到企业微信机器人（Webhook）"""
    channel = CONFIG['channels'].get('wechat_webhook', {})
    if not channel.get('enabled'):
        return {'success': False, 'reason': 'channel disabled'}
    
    payload = {
        'msgtype': 'text',
        'text': {
            'content': format_message(message, original_data)
        }
    }
    
    return send_http_request(channel['url'], data=payload)


def send_to_wechat_app(message, original_data):
    """发送到企业微信自建应用（支持 Markdown）"""
    channel = CONFIG['channels'].get('wechat_app', {})
    if not channel.get('enabled'):
        return {'success': False, 'reason': 'channel disabled'}

    access_token = get_wechat_app_token()
    if not access_token:
        return {'success': False, 'error': 'Failed to get access_token'}

    agentid = channel.get('agentid', 1000001)
    touser = channel.get('touser', '@all')
    toparty = channel.get('toparty', '')
    totag = channel.get('totag', '')

    payload = {
        'touser': touser,
        'toparty': toparty,
        'totag': totag,
        'msgtype': 'markdown',
        'agentid': agentid,
        'markdown': {
            'content': format_message(message, original_data)
        }
    }

    url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'

    # 确保中文正确编码
    result = send_http_request(url, data=payload, ensure_ascii=False)

    # 检查返回结果
    if result.get('success'):
        try:
            resp_data = json.loads(result.get('body', '{}'))
            if resp_data.get('errcode') != 0:
                result['success'] = False
                result['error'] = resp_data.get('errmsg', 'Unknown error')
        except:
            pass

    return result


def send_to_dingtalk(message, original_data):
    """发送到钉钉"""
    channel = CONFIG['channels'].get('dingtalk', {})
    if not channel.get('enabled'):
        return {'success': False, 'reason': 'channel disabled'}
    
    payload = {
        'msgtype': 'text',
        'text': {
            'content': format_message(message, original_data)
        }
    }
    
    return send_http_request(channel['url'], data=payload)


def send_to_telegram(message, original_data):
    """发送到 Telegram（支持 Markdown）"""
    channel = CONFIG['channels'].get('telegram', {})
    if not channel.get('enabled'):
        return {'success': False, 'reason': 'channel disabled'}

    url = f"https://api.telegram.org/bot{channel['botToken']}/sendMessage"
    payload = {
        'chat_id': channel['chatId'],
        'text': format_message(message, original_data),
        'parse_mode': 'MarkdownV2'
    }

    return send_http_request(url, data=payload)


def send_email(message, original_data):
    """发送邮件通知"""
    channel = CONFIG['channels'].get('email', {})
    if not channel.get('enabled'):
        return {'success': False, 'reason': 'channel disabled'}
    
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    smtp_host = channel.get('smtpHost', '')
    smtp_port = channel.get('smtpPort', 587)
    username = channel.get('username', '')
    password = channel.get('password', '')
    to_email = channel.get('to', '')
    cc_email = channel.get('cc', '')
    bcc_email = channel.get('bcc', '')
    
    if not all([smtp_host, username, password, to_email]):
        return {'success': False, 'error': 'SMTP configuration incomplete'}
    
    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = to_email
        msg['Subject'] = f"📬 消息推送 - {original_data.get('source', 'Unknown')}"
        
        # 添加抄送
        if cc_email:
            msg['Cc'] = cc_email
        
        body = format_message(message, original_data, email_format=True)
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 获取所有收件人
        recipients = get_email_recipients(to_email, cc_email, bcc_email)
        
        if not recipients:
            return {'success': False, 'error': 'No recipients configured'}
        
        # 连接 SMTP 服务器并发送
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.starttls()
        
        server.login(username, password)
        server.sendmail(username, recipients, msg.as_string())
        server.quit()
        
        logger.info(f'Email sent to {recipients}')
        return {'success': True, 'message': f'Email sent to {len(recipients)} recipient(s)'}
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f'Email SMTP auth failed: {e}')
        return {'success': False, 'error': 'SMTP authentication failed'}
    except smtplib.SMTPConnectError as e:
        logger.error(f'Email SMTP connect failed: {e}')
        return {'success': False, 'error': f'SMTP connection failed: {smtp_host}:{smtp_port}'}
    except Exception as e:
        logger.error(f'Email send failed: {type(e).__name__}: {e}')
        return {'success': False, 'error': str(e)}


def format_message(message, original_data, email_format=False):
    """格式化消息"""
    if email_format:
        # 邮件格式
        text = f"📬 消息推送通知\n\n"
        text += f"{'='*50}\n\n"
        text += f"{message}\n\n"
        text += f"{'='*50}\n\n"
        
        if original_data:
            text += f"详细信息:\n"
            text += f"  • 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            if original_data.get('source'):
                text += f"  • 来源：{original_data['source']}\n"
            if original_data.get('level'):
                text += f"  • 级别：{original_data['level']}\n"
            
            # 添加原始数据
            for key, value in original_data.items():
                if key not in ['source', 'level', 'message', 'text', 'content']:
                    text += f"  • {key}: {value}\n"
        
        text += f"\n{'='*50}\n"
        text += f"此邮件由消息推送转发服务自动发送\n"
    else:
        # IM 格式
        text = f"📬 消息推送\n\n{message}\n\n"
        
        if original_data:
            text += "---\n"
            text += f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            if original_data.get('source'):
                text += f"来源：{original_data['source']}\n"
            if original_data.get('level'):
                text += f"级别：{original_data['level']}\n"
    
    return text


def get_email_recipients(to_email, cc_email='', bcc_email=''):
    """获取邮件收件人列表"""
    recipients = []
    
    # 主收件人（支持多个，用逗号或分号分隔）
    if to_email:
        for email in to_email.replace(';', ',').split(','):
            email = email.strip()
            if email:
                recipients.append(email)
    
    # 抄送
    if cc_email:
        for email in cc_email.replace(';', ',').split(','):
            email = email.strip()
            if email:
                recipients.append(email)
    
    # 密送
    if bcc_email:
        for email in bcc_email.replace(';', ',').split(','):
            email = email.strip()
            if email:
                recipients.append(email)
    
    return recipients


def should_forward(message):
    """消息过滤"""
    filters = CONFIG.get('filters', {})
    
    # 排除关键词
    exclude_keywords = filters.get('excludeKeywords', [])
    for keyword in exclude_keywords:
        if keyword in message:
            logger.info(f'Message filtered out (exclude keyword): {keyword}')
            return False
    
    # 包含关键词
    keywords = filters.get('keywords', [])
    if keywords:
        for keyword in keywords:
            if keyword in message:
                return True
        logger.info('Message filtered out (no matching keyword)')
        return False
    
    return True


def forward_message(message, original_data):
    """转发消息到所有渠道"""
    results = {}
    
    # 企业微信机器人（Webhook）
    if CONFIG['channels'].get('wechat_webhook', {}).get('enabled'):
        result = send_to_wechat_webhook(message, original_data)
        results['wechat_webhook'] = result
        logger.info(f"WeChat Webhook: {'✓' if result.get('success') else '✗'}")
    
    # 企业微信自建应用
    if CONFIG['channels'].get('wechat_app', {}).get('enabled'):
        result = send_to_wechat_app(message, original_data)
        results['wechat_app'] = result
        logger.info(f"WeChat App: {'✓' if result.get('success') else '✗'}")
    
    # 钉钉
    if CONFIG['channels'].get('dingtalk', {}).get('enabled'):
        result = send_to_dingtalk(message, original_data)
        results['dingtalk'] = result
        logger.info(f"DingTalk: {'✓' if result.get('success') else '✗'}")
    
    # Telegram
    if CONFIG['channels'].get('telegram', {}).get('enabled'):
        result = send_to_telegram(message, original_data)
        results['telegram'] = result
        logger.info(f"Telegram: {'✓' if result.get('success') else '✗'}")
    
    # 邮件
    if CONFIG['channels'].get('email', {}).get('enabled'):
        result = send_email(message, original_data)
        results['email'] = result
        logger.info(f"Email: {'✓' if result.get('success') else '✗'}")
    
    return results


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""
    
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            result = {
                'status': 'ok',
                'timestamp': datetime.now().isoformat(),
                'channels': {
                    'wechat_webhook': CONFIG['channels'].get('wechat_webhook', {}).get('enabled', False),
                    'wechat_app': CONFIG['channels'].get('wechat_app', {}).get('enabled', False),
                    'dingtalk': CONFIG['channels'].get('dingtalk', {}).get('enabled', False),
                    'telegram': CONFIG['channels'].get('telegram', {}).get('enabled', False)
                },
                'token_cached': token_cache.get('wechat_app', {}).get('access_token') is not None
            }
            self.wfile.write(json.dumps(result).encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not Found'}).encode('utf-8'))
    
    def do_POST(self):
        # 提取路径（去掉查询参数）
        request_path = self.path.split('?')[0]
        
        if request_path == CONFIG['server']['path']:
            # 验证 Token
            auth_header = self.headers.get('Authorization', '')
            token_param = self.path.split('?')[-1] if '?' in self.path else ''
            token_match = (
                auth_header == f"Bearer {CONFIG['auth']['token']}" or
                f"token={CONFIG['auth']['token']}" in token_param
            )
            
            if not token_match:
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}, ensure_ascii=False).encode('utf-8'))
                logger.warning('Unauthorized access attempt')
                return
            
            # 读取请求体（UTF-8 编码）
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {'raw': body}
            
            # 提取消息
            message = (
                data.get('message') or
                data.get('text') or
                data.get('content') or
                str(data.get('msg', body))
            )
            
            logger.info(f"Received message: {message[:100]}...")
            
            # 消息过滤
            if not should_forward(message):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'forwarded': False,
                    'reason': 'filtered'
                }, ensure_ascii=False).encode('utf-8'))
                return
            
            # 转发消息
            results = forward_message(message, data)
            
            all_success = all(r.get('success', False) for r in results.values())
            
            self.send_response(200 if all_success else 207)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
            
            response = {
                'success': all_success,
                'forwarded': True,
                'channels': results,
                'timestamp': datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not Found'}, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")


def main():
    # 加载 token 缓存
    load_token_cache()
    
    # 启动 token 刷新线程
    refresh_thread = threading.Thread(target=token_refresh_loop, daemon=True)
    refresh_thread.start()
    logger.info('Token refresh thread started')
    
    port = CONFIG['server']['port']
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    
    logger.info('=' * 50)
    logger.info('Message Forwarder Started')
    logger.info('=' * 50)
    logger.info(f'Port: {port}')
    logger.info(f"Webhook: http://localhost:{port}{CONFIG['server']['path']}")
    logger.info(f'Health: http://localhost:{port}/health')
    logger.info('=' * 50)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('Shutting down...')
        save_token_cache()
        server.shutdown()


if __name__ == '__main__':
    main()
