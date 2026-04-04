# 消息推送转发服务 🚀

一个轻量级的 HTTP Webhook 服务，接收消息并转发到多个渠道（企业微信、钉钉、Telegram、邮件等）。

[![Docker Pulls](https://img.shields.io/docker/pulls/247798124/message-forwarder)](https://hub.docker.com/r/247798124/message-forwarder)
[![Docker Image Size](https://img.shields.io/docker/image-size/247798124/message-forwarder/latest)](https://hub.docker.com/r/247798124/message-forwarder)
[![GitHub](https://img.shields.io/github/license/gowfqk/message-forwarder)](LICENSE)

---

## ✨ 特性

- 🎨 **Markdown 支持** - 企业微信自建应用和 Telegram 支持富文本格式
- 🔄 **自动 Token 刷新** - 企业微信自建应用 access_token 自动刷新
- 📨 **多渠道推送** - 企业微信、钉钉、Telegram、邮件等
- 🎯 **消息过滤** - 支持关键词过滤
- 🌐 **Web 管理界面** - 可视化配置管理
- 🐳 **Docker 部署** - 一键部署，开箱即用

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

**2. 创建 docker-compose.yml**

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

**3. 启动服务**

```bash
docker-compose up -d
```

**4. 查看日志**

```bash
docker-compose logs -f
```

**5. 停止服务**

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
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/cache:/app/cache \
  -e CONFIG_PATH=/app/config/config.json \
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
  -v $(pwd)/config:/app/config \
  -e CONFIG_PATH=/app/config/config.json \
  message-forwarder
```

---

## 📋 快速配置

### 1. 编辑 config/config.json

```bash
# 创建配置文件
mkdir -p config
nano config/config.json
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
  },
  "logFile": "logs/forward.log"
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

## 📝 Webhook 使用说明

### Webhook Body 格式

支持以下字段（按优先级提取）：

| 字段 | 优先级 | 说明 |
|------|--------|------|
| `message` | 1 | 消息内容 |
| `text` | 2 | 文本内容 |
| `content` | 3 | 内容 |
| `msg` | 4 | 消息 |
| 其他字段 | - | 保留在原始数据中 |

### 认证方式

| 方式 | 示例 |
|------|------|
| Header（推荐） | `Authorization: Bearer your-token` |
| URL 参数 | `http://localhost:3000/webhook?token=your-token` |

### 示例

```bash
# 格式1：使用 message 字段
curl -X POST http://localhost:3000/webhook \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "服务器告警",
    "source": "监控系统",
    "level": "critical"
  }'

# 格式2：使用 text 字段
curl -X POST http://localhost:3000/webhook \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "CPU使用率过高",
    "cpu": "95%"
  }'

# 格式3：纯文本
curl -X POST http://localhost:3000/webhook \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: text/plain" \
  -d "这是一条纯文本消息"
```

### 响应格式

**成功：**
```json
{
  "success": true,
  "forwarded": true,
  "channels": {
    "wechat_webhook": {"success": true},
    "telegram": {"success": true}
  },
  "timestamp": "2026-04-03T14:30:00.000Z"
}
```

**失败：**
```json
{
  "error": "Unauthorized"
}
```

---

## 🎨 Markdown 支持

### 支持的渠道

| 渠道 | Markdown | 支持的元素 |
|------|----------|-----------|
| **企业微信自建应用** | ✅ | 加粗、列表、链接、换行 |
| **Telegram** | ✅ | 加粗、链接、代码块、换行、图片 |
| **企业微信 Webhook** | ❌ | 纯文本（显示原始 Markdown） |
| **邮件** | ❌ | 纯文本 |

### 语法示例

```json
{
  "message": "**服务器告警**\n\n> **CPU**: 95%\n> **内存**: 88%\n\n[点击查看详情](https://example.com)",
  "source": "监控系统",
  "server": "server-01"
}
```

### 企业微信自建应用支持语法

```markdown
**加粗文本**
- 列表项1
- 列表项2

[链接文字](https://example.com)

换行使用 \n
```

### Telegram 支持语法

```markdown
**加粗文本**
*斜体文本*
`代码`
[链接文字](https://example.com)

![图片](https://example.com/image.png)
```

---

## 🚀 哪吒探针集成

### 官方占位符变量

| 占位符 | 说明 | 示例值 |
|--------|------|--------|
| `#NEZHA#` | 通知内容（完整告警信息） | CPU使用率过高... |
| `#SERVER.NAME#` | 服务器名称 | Web Server 01 |
| `#SERVER.IP#` | 服务器 IP | 192.168.1.100 |
| `#SERVER.IPV4#` | 服务器 IPv4 地址 | 192.168.1.100 |
| `#SERVER.IPV6#` | 服务器 IPv6 地址 | 2001:db8::1 |
| `#SERVER.CPU#` | CPU 使用率 | 95.2% |
| `#SERVER.MEM#` | 内存使用率 | 88.5% |
| `#SERVER.SWAP#` | 交换分区使用率 | 45.2% |
| `#SERVER.DISK#` | 磁盘使用率 | 87.3% |
| `#SERVER.SPEEDIN#` | 实时入站网速 | 125.6 MB/s |
| `#SERVER.SPEEDOUT#` | 实时出站网速 | 89.3 MB/s |
| `#SERVER.TRANSFERIN#` | 总入站流量 | 1.2 TB |
| `#SERVER.TRANSFEROUT#` | 总出站流量 | 2.4 TB |
| `#SERVER.LOAD1#` | 1分钟内负载 | 8.45 |
| `#SERVER.LOAD5#` | 5分钟内负载 | 7.82 |
| `#SERVER.LOAD15#` | 15分钟内负载 | 6.15 |

### 哪吒面板配置

**URL:** `http://你的服务器IP:3000/webhook?token=你的token`  
**方法:** `POST`  
**Content-Type:** `application/json`

### 告警模板（推荐）

```json
{
  "message": "**#NEZHA#\n\n平均负载: \"#SERVER.LOAD1#\",\"#SERVER.LOAD5#\",\"#SERVER.LOAD15#\"\n\n## [点击访问面板](https://你的面板域名)",
  "source": "哪吒探针",
  "server": "#SERVER.NAME#",
  "ip": "#SERVER.IP#",
  "cpu": "#SERVER.CPU#",
  "memory": "#SERVER.MEM#",
  "disk": "#SERVER.DISK#",
  "load1": "#SERVER.LOAD1#",
  "load5": "#SERVER.LOAD5#",
  "load15": "#SERVER.LOAD15#"
}
```

### 离线告警模板

```json
{
  "message": "**⚠️ 服务器离线**\n\n服务器 **#SERVER.NAME#** 已离线\n\n> **名称**: #SERVER.NAME#\n> **IP**: #SERVER.IP#\n> **IPv4**: #SERVER.IPV4#\n\n## [点击访问面板](https://你的面板域名)",
  "source": "哪吒探针",
  "server": "#SERVER.NAME#",
  "ip": "#SERVER.IP#",
  "ipv4": "#SERVER.IPV4#",
  "status": "offline"
}
```

### 测试哪吒配置

```bash
curl -X POST http://localhost:3000/webhook \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "**服务器告警**\n\n平均负载: \"8.45\",\"7.82\",\"6.15\"\n\n## [点击访问面板](https://nezha.example.com)",
    "source": "哪吒探针",
    "server": "Web Server 01",
    "ip": "192.168.1.100",
    "cpu": "95.2%",
    "memory": "88.5%",
    "load1": "8.45",
    "load5": "7.82",
    "load15": "6.15"
  }'
```

---

## 🔧 常用命令

### Docker Compose

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

### Docker

```bash
# 启动容器
docker start message-forwarder

# 停止容器
docker stop message-forwarder

# 重启容器
docker restart message-forwarder

# 删除容器
docker rm message-forwarder

# 查看运行中的容器
docker ps

# 查看所有容器
docker ps -a
```

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

**4. Docker 配置路径**

Docker 部署时，配置文件必须放在 `config/config.json`（不是根目录的 `config.json`），并通过环境变量 `CONFIG_PATH=/app/config/config.json` 指定。

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

## 🌟 支持的推送渠道

| 渠道 | 状态 | Markdown | 说明 |
|------|------|----------|------|
| 企业微信应用 | ✅ | ✅ | 支持指定用户/部门 |
| 企业微信机器人 | ✅ | ❌ | Webhook 方式 |
| 钉钉机器人 | ✅ | ❌ | Webhook 方式 |
| Telegram Bot | ✅ | ✅ | Bot Token |
| 邮件通知 | ✅ | ❌ | SMTP（支持 SSL） |

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
      "touser": "@all",
      "toparty": "",
      "totag": ""
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
      "to": "recipient@example.com",
      "cc": "",
      "bcc": ""
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
docker exec message-forwarder python -c "import json; json.load(open('/app/config/config.json'))"
```

### 配置未加载

确保使用正确的配置文件路径：
```bash
# 正确
./config/config.json

# 错误（Docker 不支持）
./config.json
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

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📮 联系方式

- GitHub: [@gowfqk](https://github.com/gowfqk)
- Email: gowfqk@163.com
