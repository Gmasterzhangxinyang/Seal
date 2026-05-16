# 连接 Aurora API

Aurora 通过 Hermes API Server 暴露 OpenAI 兼容接口，可从任何客户端调用。

## 端点信息

| 项 | 值 |
|---|---|
| API 地址 | `http://110.42.229.174:8001/v1` |
| Model ID | `hermes-agent` |
| API Key | `814988d70d320f23cf1dff306e9a8249abcfffaa39459a1f65486d1806522938` |
| 协议 | OpenAI Chat Completions 兼容 |

## 可用端点

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/health` | 健康检查 |
| `GET` | `/v1/models` | 模型列表 |
| `POST` | `/v1/chat/completions` | 对话请求 |
| `POST` | `/v1/responses` | Responses API（有状态） |

## 快速测试

### curl

```bash
curl -s http://110.42.229.174:8001/v1/chat/completions \
  -H "Authorization: Bearer 814988d70d320f23cf1dff306e9a8249abcfffaa39459a1f65486d1806522938" \
  -H "Content-Type: application/json" \
  -d '{"model":"hermes-agent","messages":[{"role":"user","content":"你好"}]}'
```

### Python 多轮对话客户端

```python
import requests, json

URL = "http://110.42.229.174:8001/v1/chat/completions"
KEY = "814988d70d320f23cf1dff306e9a8249abcfffaa39459a1f65486d1806522938"
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
messages = []

print("Aurora 在听。（quit 退出）\n")

while True:
    user_input = input("你> ")
    if user_input.lower() in ("quit", "exit", "q"):
        print("Aurora> 下次见。")
        break
    messages.append({"role": "user", "content": user_input})
    payload = {"model": "hermes-agent", "messages": messages}
    r = requests.post(URL, headers=HEADERS, json=payload, timeout=300)
    reply = r.json()["choices"][0]["message"]["content"]
    messages.append({"role": "assistant", "content": reply})
    print(f"Aurora> {reply}\n")
```

依赖：`pip install requests`

## 接入前端

任何 OpenAI 兼容前端（Open WebUI、LobeChat、ChatBox 等）均可接入，配置如下：

- **API URL / Base URL**：`http://110.42.229.174:8001/v1`
- **API Key**：见上方
- **Model**：`hermes-agent`

## 架构说明

```
客户端（浏览器/终端/Python）
        │
        │ HTTPS / HTTP
        ▼
  腾讯云 CVM (110.42.229.174)
        │
        ├── Nginx :80        → MEC202 前端静态文件
        │   └── /api/*       → WireGuard → 机器人机器 :5001
        │
        └── Hermes Gateway :8001
            └── api_server adapter (OpenAI 兼容)
                └── Aurora 人格 + 完整工具链
```

Aurora 在 API 通道中保持完整人格——温柔浪漫但也能利落做事，记得项目上下文、修过的 bug、你的偏好和节奏。
