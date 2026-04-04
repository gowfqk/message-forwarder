# 消息推送转发服务 🚀

一个轻量级的 HTTP Webhook 服务，接收消息并转发到多个渠道（企业微信、钉钉、Telegram、邮件等）。

[![Docker Pulls](https://img.shields.io/docker/pulls/247798124/message-forwarder)](https://hub.docker.com/r/247798124/message-forwarder)
[![Docker Image Size](https://img.shields.io/docker/image-size/247798124/message-forwarder/latest)](https://hub.docker.com/r/247798124/message-forwarder)
[![GitHub](https://img.shields.io/github/license/gowfqk/message-forwarder)](LICENSE)

---

## ✨ 特性

- 🎨 **Markdown 支持** - 企业微信自建应用和 Telegram
- 🔄 **自动 Token 刷新** - 企业微信自建应用
- 📨 **多渠道推送** - 企业微信、钉钉、Telegram、邮件
- 🎯 **消息过滤** - 支持关键词过滤
- 🌐 **Web 管理界面** - 可视化配置管理
- 🐳 **Docker 部署** - 一键部署

---

## 🐳 Docker 部署

### 1. 创建配置文件

```bash
mkdir -p config
nano config/config.json
```

**config/config.json:**
```json
{
  "server": {"port": 3000, "path": "/webhook"},
  "auth": {"token": "your-secret-token"},
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

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  message-forwarder:
    image: 247798124/message-forwarder:latest
    container_name: message-forwarder
    restart: unless-stopped
    ports:
      - "3000:3000"  # Webhook
      - "5000:5000"  # Web UI
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./cache:/app/cache
    environment:
      - TZ=Asia/Shanghai
      - CONFIG_PATH=/app/config/config.json
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 测试

```bash
curl -X POST "http://localhost:3000/webhook?token=your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"message": "测试消息"}'
```

---

## 📝 Webhook 使用

### Body 格式

```json
{
  "message": "消息内容",
  "source": "来源",
  "server": "服务器名"
}
```

支持字段：`message`, `text`, `content`, `msg`（按优先级提取）

### 认证方式

- **Header（推荐）**: `Authorization: Bearer your-token`
- **URL 参数**: `http://localhost:3000/webhook?token=your-token`

---

## 🎨 Markdown 支持

| 渠道 | Markdown |
|------|----------|
| 企业微信自建应用 | ✅ |
| Telegram | ✅ |
| 企业微信 Webhook | ❌ |
| 邮件 | ❌ |

### 示例

```json
{
  "message": "**服务器告警**\n\n> **CPU**: 95%\n> **内存**: 88%\n\n[查看详情](https://example.com)"
}
```

---

## 🚀 哪吒探针集成

### 配置

```
URL: http://你的IP:3000/webhook?token=your-token
方法: POST
Content-Type: application/json
```

### 告警模板

```json
{
  "message": "**#NEZHA#\n\n平均负载: \"#SERVER.LOAD1#\",\"#SERVER.LOAD5#\",\"#SERVER.LOAD15#\"\n\n## [点击访问面板](https://nz.o0oo.cc)",
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
  "message": "**⚠️ 服务器离线**\n\n服务器 **#SERVER.NAME#** 已离线\n\n## [点击访问面板](https://nz.o0oo.cc)",
  "source": "哪吒探针",
  "server": "#SERVER.NAME#",
  "ip": "#SERVER.IP#",
  "status": "offline"
}
```

### 官方占位符

`#NEZHA#`, `#SERVER.NAME#`, `#SERVER.IP#`, `#SERVER.CPU#`, `#SERVER.MEM#`, `#SERVER.DISK#`, `#SERVER.LOAD1#`, `#SERVER.LOAD5#`, `#SERVER.LOAD15#`, `#SERVER.SPEEDIN#`, `#SERVER.SPEEDOUT#`, `#SERVER.TRANSFERIN#`, `#SERVER.TRANSFEROUT#`

---

## 🌐 访问地址

| 服务 | 地址 |
|------|------|
| Webhook | `http://localhost:3000/webhook` |
| Web UI | `http://localhost:5000` |
| 健康检查 | `http://localhost:3000/health` |

---

## 📋 完整配置示例

```json
{
  "server": {
    "port": 3000,
    "path": "/webhook"
  },
  "auth": {
    "token": "your-secret-token"
  },
  "channels": {
    "wechat_webhook": {
      "enabled": true,
      "type": "webhook",
      "url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
    },
    "wechat_app": {
      "enabled": true,
      "type": "app",
      "corpid": "ww1234567890abcdef",
      "corpsecret": "your-secret",
      "agentid": 1000001,
      "touser": "@all"
    },
    "telegram": {
      "enabled": true,
      "type": "bot",
      "botToken": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
      "chatId": "-1001234567890"
    },
    "email": {
      "enabled": true,
      "type": "smtp",
      "smtpHost": "smtp.163.com",
      "smtpPort": 465,
      "username": "your@163.com",
      "password": "your-auth-code",
      "to": "recipient@example.com"
    }
  },
  "token_cache": {
    "enabled": true,
    "file": "cache/tokens.json",
    "refresh_ahead": 300
  },
  "filters": {
    "keywords": [],
    "excludeKeywords": []
  },
  "logFile": "logs/forward.log"
}
```

---

## 🔧 常用命令

```bash
# 启动/停止
docker-compose up -d
docker-compose down

# 查看日志
docker-compose logs -f

# 重启
docker-compose restart

# 更新镜像
docker-compose pull && docker-compose up -d
```

---

## ⚠️ 注意事项

1. **配置文件位置**: Docker 部署时必须使用 `./config/config.json`（不是根目录的 `config.json`）
2. **编码**: 使用 UTF-8 无 BOM 保存 JSON 文件
3. **端口**: 确保端口 3000 和 5000 未被占用

---

## 🔗 相关链接

- **GitHub**: https://github.com/gowfqk/message-forwarder
- **Docker Hub**: https://hub.docker.com/r/247798124/message-forwarder
- **Issues**: https://github.com/gowfqk/message-forwarder/issues

---

## 📄 License

MIT License
