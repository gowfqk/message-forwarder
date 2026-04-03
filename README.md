# 消息推送转发服务 🚀

一个轻量级的 HTTP Webhook 服务，接收消息并转发到多个渠道（企业微信、钉钉、Telegram、邮件等）。

[![Docker Pulls](https://img.shields.io/docker/pulls/247798124/message-forwarder)](https://hub.docker.com/r/247798124/message-forwarder)
[![Docker Image Size](https://img.shields.io/docker/image-size/247798124/message-forwarder/latest)](https://hub.docker.com/r/247798124/message-forwarder)
[![GitHub](https://img.shields.io/github/license/gowfqk/message-forwarder)](LICENSE)

---

## 🐳 Docker 部署（推荐）

### 方式一：Docker Compose（最简单）

**⚠️ 重要提示：** 首次启动前请确保 `config/config.json` 是文件而不是文件夹！

**解决方法：**
```bash
# 如果 config.json 是文件夹，删除它
rm -rf config.json
# 或
rmdir /s config.json

# 创建 config 目录和配置文件
mkdir -p config
# 然后编辑 config/config.json
```

**1. 创建配置目录和文件**

```bash
mkdir -p config
nano config/config.json
```

**配置文件模板：**
```json
{
  "server": {"port": 3000, "path": "/webhook"},
  "auth": {"token": "your-secret-token"},
  "channels": {
    "wechat_webhook": {"enabled": false, "type": "webhook", "url": ""}
  }
}
```

**3. 创建 docker-compose.yml**

在项目根目录创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  message-forwarder:
    image: 247798124/message-forwarder:latest
    container_name: message-forwarder
    restart: unless-stopped
    ports:
      - "3000:3000"  # Webhook 接收
      - "5000:5000"  # Web 管理界面
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./cache:/app/cache
    environment:
      - TZ=Asia/Shanghai
      - CONFIG_PATH=/app/config/config.json
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:3000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**4. 启动服务**

```bash
docker-compose up -d
```

**5. 查看日志**

```bash
docker-compose logs -f
```

**6. 停止服务**

```bash
docker-compose down
```

---

### 方式二：Docker 命令

**拉取镜像**
```bash
docker pull 247798124/message-forwarder:latest
```

**运行容器**
```bash
docker run -d \
  --name message-forwarder \
  -p 3000:3000 \
  -p 5000:5000 \
  -v $(pwd)/config.json:/app/config.json \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/cache:/app/cache \
  --restart unless-stopped \
  247798124/message-forwarder:latest
```

**查看日志**
```bash
docker logs -f message-forwarder
```

**停止容器**
```bash
docker stop message-forwarder
docker rm message-forwarder
```

---

### 方式三：构建本地镜像

```bash
# 构建镜像
docker build -t message-forwarder .

# 运行容器
docker run -d --name message-forwarder \
  -p 3000:3000 -p 5000:5000 \
  -v $(pwd)/config.json:/app/config.json \
  message-forwarder
```

---

## 📋 快速配置

### 1. 编辑 config.json

```bash
# 创建配置文件
nano config.json
# 或
notepad config.json
```

**基础配置模板：**

```json
{
  "server": {
    "port": 3000,
    "path": "/webhook"
  },
  "auth": {
    "token": "your-secret-token-here"
  },
  "channels": {
    "wechat_webhook": {
      "enabled": true,
      "type": "webhook",
      "url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
    }
  }
}
```

### 2. 重启服务

```bash
docker-compose restart
# 或
docker restart message-forwarder
```

### 3. 发送测试消息

```bash
curl -X POST "http://localhost:3000/webhook?token=your-secret-token-here" \
  -H "Content-Type: application/json" \
  -d '{"message": "测试消息"}'
```

---

## 🔧 常用命令

### Docker Compose

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 重新构建并启动
docker-compose up -d --build

# 查看服务状态
docker-compose ps
```

### Docker

```bash
# 查看容器状态
docker ps -a

# 查看日志
docker logs -f message-forwarder

# 进入容器
docker exec -it message-forwarder bash

# 重启容器
docker restart message-forwarder

# 停止并删除容器
docker stop message-forwarder
docker rm message-forwarder
```

---

## 📁 数据持久化

| 路径 | 说明 | 是否必需 |
|------|------|----------|
| `./config/config.json` | 配置文件 | ✅ 是 |
| `./logs/` | 日志文件 | ❌ 否 |
| `./cache/` | Token 缓存 | ❌ 否 |

---

## ⚠️ 注意事项

**1. 配置文件格式**

确保 `config/config.json` 是文件而不是文件夹！

```bash
# 错误：Docker 会自动创建文件夹
docker-compose up -d

# 正确：先创建文件
mkdir -p config
nano config/config.json
docker-compose up -d
```

**2. 配置文件编码**

使用 **UTF-8 无 BOM** 编码保存 JSON 文件，否则会导致解析失败。

**3. 端口占用**

确保端口 3000 和 5000 未被占用：

```bash
# Windows
netstat -ano | findstr :3000

# Linux/Mac
lsof -i :3000
```

---

## 📋 docker-compose.yml 完整配置

### 基础配置

```yaml
version: '3.8'

services:
  message-forwarder:
    image: 247798124/message-forwarder:latest  # Docker Hub 镜像
    container_name: message-forwarder          # 容器名称
    restart: unless-stopped                    # 自动重启策略
    ports:
      - "3000:3000"  # Webhook 接收端口
      - "5000:5000"  # Web 管理界面端口
    volumes:
      - ./config:/app/config    # 配置文件目录
      - ./logs:/app/logs        # 日志目录
      - ./cache:/app/cache      # Token 缓存目录
    environment:
      - TZ=Asia/Shanghai        # 时区设置
      - CONFIG_PATH=/app/config/config.json  # 配置文件路径
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:3000/health')"]
      interval: 30s   # 健康检查间隔
      timeout: 10s    # 超时时间
      retries: 3      # 重试次数
```

### 配置说明

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `image` | Docker 镜像地址 | `247798124/message-forwarder:latest` |
| `restart` | 容器重启策略 | `unless-stopped`（推荐） |
| `ports` | 端口映射 | `3000:3000`（Webhook）<br>`5000:5000`（Web UI） |
| `volumes` | 数据卷挂载 | `./config:/app/config`（配置）<br>`./logs:/app/logs`（日志）<br>`./cache:/app/cache`（缓存） |
| `environment` | 环境变量 | `TZ=Asia/Shanghai`（时区）<br>`CONFIG_PATH`（配置文件路径） |

---

## 🔧 Docker Compose 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 重新构建并启动
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f message-forwarder

# 进入容器
docker-compose exec message-forwarder bash

# 更新镜像并重启
docker-compose pull
docker-compose up -d
```

---

## 🌟 支持的推送渠道

| 渠道 | 状态 | 说明 |
|------|------|------|
| 企业微信应用 | ✅ | 支持指定用户/部门 |
| 企业微信机器人 | ✅ | Webhook 方式 |
| 钉钉机器人 | ✅ | Webhook 方式 |
| Telegram Bot | ✅ | Bot Token |
| 邮件通知 | ✅ | SMTP（支持 SSL） |

---

## 🌐 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| Webhook 接收 | `http://localhost:3000/webhook` | 接收消息推送 |
| Web 管理界面 | `http://localhost:5000` | 可视化配置管理 |
| 健康检查 | `http://localhost:3000/health` | 服务状态 |

---

## 📝 配置说明

### 企业微信机器人

```json
{
  "channels": {
    "wechat_webhook": {
      "enabled": true,
      "type": "webhook",
      "url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
    }
  }
}
```

### 企业微信应用

```json
{
  "channels": {
    "wechat_app": {
      "enabled": true,
      "type": "app",
      "corpid": "ww1234567890abcdef",
      "corpsecret": "abcdefghijklmnopqrstuvwxyz123456",
      "agentid": 1000001,
      "touser": "@all"
    }
  }
}
```

### Telegram

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "type": "bot",
      "botToken": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
      "chatId": "-1001234567890"
    }
  }
}
```

### 邮件通知（163 邮箱示例）

```json
{
  "channels": {
    "email": {
      "enabled": true,
      "type": "smtp",
      "smtpHost": "smtp.163.com",
      "smtpPort": 465,
      "username": "your@163.com",
      "password": "your-auth-code",
      "to": "recipient@example.com"
    }
  }
}
```

---

## 🔍 故障排查

### 查看日志

```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f message-forwarder
```

### 服务无法启动

```bash
# 检查端口占用
netstat -ano | findstr :3000

# 检查配置文件
docker exec message-forwarder python -c "import json; json.load(open('/app/config.json'))"
```

### 清除缓存

```bash
# 删除 Token 缓存
rm -rf cache/tokens.json
# 或
docker exec message-forwarder rm -rf /app/cache/tokens.json

# 重启服务
docker-compose restart
```

---

## 🔗 相关链接

- **GitHub**: https://github.com/gowfqk/message-forwarder
- **Docker Hub**: https://hub.docker.com/r/247798124/message-forwarder
- **Issues**: https://github.com/gowfqk/message-forwarder/issues

---

## 📄 License

MIT
