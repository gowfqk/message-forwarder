#!/bin/bash
# 消息推送转发服务 - 启动脚本
# 同时启动转发服务和 Web 管理界面

echo "=================================================="
echo "  消息推送转发服务"
echo "=================================================="
echo "  转发服务：http://localhost:3000"
echo "  Web 界面：http://localhost:5000"
echo "=================================================="

# 启动转发服务（后台）
python server.py &
FORWARDER_PID=$!

# 等待 2 秒确保转发服务启动
sleep 2

# 启动 Web 管理界面（前台）
echo "Starting Web Management Interface..."
python web/app.py

# 如果 Web 界面退出，清理转发服务
kill $FORWARDER_PID 2>/dev/null
