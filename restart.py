#!/usr/bin/env python3
"""
重启转发服务的独立脚本
可被 Web 界面调用
"""

import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
SERVER_PID = BASE_DIR / '.server.pid'
SERVER_SCRIPT = BASE_DIR / 'server.py'

def stop():
    """停止服务"""
    if SERVER_PID.exists():
        try:
            pid = int(SERVER_PID.read_text().strip())
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True)
            print(f'Stopped process {pid}')
        except Exception as e:
            print(f'Stop failed: {e}')
    
    SERVER_PID.unlink(missing_ok=True)

def start():
    """启动服务"""
    process = subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT)],
        cwd=str(BASE_DIR)
    )
    SERVER_PID.write_text(str(process.pid))
    print(f'Started process {process.pid}')
    return process.pid

if __name__ == '__main__':
    print('Restarting message forwarder...')
    stop()
    time.sleep(1)
    pid = start()
    print(f'Restarted successfully (PID: {pid})')
