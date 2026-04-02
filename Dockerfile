# 消息推送转发服务 - 完整版（集成 Web 管理界面）
# 基于 Python 3.11 精简版

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV FLASK_APP=web/app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY server.py .
COPY restart.py .
COPY web/ ./web/

# 创建日志和缓存目录
RUN mkdir -p /app/logs /app/cache

# 暴露端口
# 3000: 转发服务 Webhook 接收端口
# 5000: Web 管理界面端口
EXPOSE 3000 5000

# 健康检查（检查 Web 管理界面）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/status')" || exit 1

# 启动脚本
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 默认启动两个服务
ENTRYPOINT ["/entrypoint.sh"]
CMD ["all"]

# 标签
LABEL maintainer="Message Forwarder"
LABEL description="消息推送转发服务 - 支持企业微信、钉钉、Telegram、邮件"
LABEL version="2.0.0"
