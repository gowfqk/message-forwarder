# 消息推送转发服务
FROM python:3.11-slim

# 设置 UTF-8 编码（解决中文乱码）
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
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

# 创建目录
RUN mkdir -p /app/logs /app/cache /app/config

# 暴露端口
EXPOSE 3000 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/health')" || exit 1

# 启动命令
CMD ["python", "server.py"]
