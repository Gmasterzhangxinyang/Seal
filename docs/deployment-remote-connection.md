# MEC202 远程连接方案说明

> 维护者：Wene  
> 最后更新：2026-05-16  
> 适用分支：`wene`

## 架构概览

```
用户浏览器
    │
    ▼
┌─────────────────────────────────────┐
│  云服务器 (110.42.229.174)           │
│  Ubuntu 24.04                       │
│                                      │
│  Nginx :80                           │
│  ├─ /          → 前端静态文件         │
│  ├─ /api/*     → WireGuard 代理      │
│  ├─ /api/stamp/leave → SSE 流式     │
│  └─ /video_feed → MJPEG 视频流      │
│                                      │
│  前端: /var/www/mec202-web/          │
│  源码: /home/ubuntu/MEC202/          │
└──────────────┬──────────────────────┘
               │ WireGuard VPN
               │ 10.66.66.1 (云服务器)
               │ 10.66.66.2 (机器人机器)
               ▼
┌─────────────────────────────────────┐
│  机器人机器 (Windows)                 │
│                                      │
│  FastAPI :5001                       │
│  ├─ /api/stamp       盖章           │
│  ├─ /api/stamp/leave  SSE 流式盖章  │
│  ├─ /api/voice/*     语音控制       │
│  ├─ /api/calibration  标定          │
│  ├─ /api/logs         日志          │
│  └─ /video_feed      摄像头视频流   │
│                                      │
│  硬件: WeArm 机械臂 + USB摄像头     │
└─────────────────────────────────────┘
```

## 连接链路

### 1. WireGuard VPN 隧道

云服务器和机器人机器之间通过 WireGuard 建立加密隧道。

**云服务器侧 (`/etc/wireguard/wg0.conf`)：**
```ini
[Interface]
PrivateKey = <云服务器私钥>
Address = 10.66.66.1/24
ListenPort = 51820

[Peer]
PublicKey = <机器人机器公钥>
AllowedIPs = 10.66.66.2/32
```

**机器人机器侧（Windows WireGuard 客户端）：**
```ini
[Interface]
PrivateKey = <机器人机器私钥>
Address = 10.66.66.2/24

[Peer]
PublicKey = <云服务器公钥>
Endpoint = 110.42.229.174:51820
AllowedIPs = 10.66.66.0/24
PersistentKeepalive = 25
```

**启动：**
```bash
# 云服务器
sudo wg-quick up wg0

# 验证连通性
ping 10.66.66.2
```

### 2. 安全组（腾讯云控制台）

需要在云服务器安全组中放行：
- **UDP 51820** — WireGuard 端口（入站）
- **TCP 80** — HTTP 前端（入站，通常已开放）

### 3. Nginx 反向代理

配置位于 `/etc/nginx/sites-enabled/mec202`，核心规则：

- `/api/` → `http://10.66.66.2:5001`（一般 API，300s 超时）
- `/api/stamp/leave` → SSE 流式，关闭 buffering
- `/video_feed` → MJPEG 视频流，关闭 buffering，3600s 超时

**验证部署：**
```bash
sudo nginx -t && sudo nginx -s reload
```

## 前端部署流程

本机（云服务器）更新前端步骤：

```bash
cd /home/ubuntu/MEC202
git pull origin lxx          # 拉取最新代码

cd apps/web
pnpm install && pnpm build   # 构建前端

# 部署到 Nginx 目录
sudo cp dist/index.html /var/www/mec202-web/
sudo cp -r dist/assets/* /var/www/mec202-web/assets/

sudo nginx -s reload
```

## 机器人机器侧更新

机器人机器（Windows 10.66.66.2）更新后端：

```bash
cd MEC202
git pull origin lxx          # 同步代码

# 安装新依赖
pip install -r requirements.txt
# 或使用 uv（如果启用了）
# uv sync

# 检查 .env 配置
# 确认 API keys: GLM-4V, 数据库连接等

# 重启后端
# (根据实际启动方式，可能是 python main.py 或 uvicorn)
```

## 端口映射速查

| 服务 | 位置 | 端口 | 说明 |
|------|------|------|------|
| Nginx 前端 | 云服务器 | 80 | 对外访问入口 |
| FastAPI 后端 | 机器人机器 | 5001 | 经 WireGuard 代理 |
| WireGuard | 云服务器 | 51820/UDP | VPN 隧道 |

## 故障排查

### 前端 502
```bash
# 检查 WireGuard 是否连通
ping 10.66.66.2

# 检查机器人机器后端是否运行
curl http://10.66.66.2:5001/api/health
```

### SSE 流式无响应
确认 Nginx 中 `/api/stamp/leave` 的 location 块包含：
```nginx
proxy_buffering off;
proxy_http_version 1.1;
chunked_transfer_encoding on;
```

### 视频流卡顿
确认 `/video_feed` 的 `proxy_buffering off` 和 `proxy_read_timeout` 设置。
