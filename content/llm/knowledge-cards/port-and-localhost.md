---
title: "Port 與 Localhost"
date: 2026-05-12
description: "TCP port 與 listen address 如何決定 API server 的對外暴露範圍"
weight: 1
tags: ["llm", "knowledge-cards", "network"]
---

Port 與 Localhost 的核心概念是「網路 server 暴露在哪個地址、聽哪個 port、讓誰能連進來」。本地 LLM 場景中、Ollama 預設聽 `127.0.0.1:11434`、Continue.dev 等介面層透過這個地址呼叫 [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/)；理解 listen address 跟 port 的角色、才能判讀「為什麼 port 撞 / 為什麼 LAN 上另一台連不到 / 暴露到 internet 安全嗎」。

## 概念位置

完整的 server 入口由兩個欄位定義：

| 欄位           | 角色                                   | 範例值                                |
| -------------- | -------------------------------------- | ------------------------------------- |
| Listen address | 接受哪些網路介面送進來的封包           | `127.0.0.1` / `0.0.0.0` / `192.168.x` |
| Port           | OS 用來區分「同一台機器上哪個 server」 | `11434` / `1234` / `8080`             |

Port 是 16 bit 數字（0 ~ 65535）、其中 0 ~ 1023 是 well-known port（HTTP 80、HTTPS 443 等、需 root 權限才能 bind）、1024 ~ 65535 是 user port、本地 LLM 工具都用這個區間（Ollama 11434、LM Studio 1234、llama.cpp 8080）。同一個 port 在同一個 listen address 上同時只能被一個 process 持有、要兩個 Ollama 並存就要其中一個換 port。

三個常見 listen address 的語意：

| 地址        | 等同名稱      | 接受誰的連線                                          |
| ----------- | ------------- | ----------------------------------------------------- |
| `127.0.0.1` | `localhost`   | 只接受本機 process、外部裝置連不到                    |
| `0.0.0.0`   | 所有介面      | 接受任何網路介面送進來的封包、包含 LAN / VPN / public |
| `192.168.x` | 特定 LAN 介面 | 只接受該 LAN 介面送進來的封包                         |

## 可觀察訊號與例子

驗證 server 真的在聽預期地址：

```bash
# macOS 下查誰佔了 11434
lsof -i :11434
# COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME
# ollama  1234 mac  6u IPv4 0xabcd      0t0 TCP localhost:11434 (LISTEN)
```

`TCP localhost:11434 (LISTEN)` 表示這個 process 只接 localhost 進來的封包。改 listen address 把 Ollama 暴露到 LAN：

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
# lsof 之後會看到 TCP *:11434 (LISTEN)、星號表示所有介面
```

curl 用不同 host 名稱呼叫同一個 server：

```bash
curl http://localhost:11434/api/version    # 走 loopback、最快
curl http://127.0.0.1:11434/api/version    # 跟上面等價
curl http://<本機 LAN IP>:11434/api/version # 若 listen 在 0.0.0.0、會通；只 listen localhost 會 connection refused
```

「為什麼桌機跑 Ollama、筆電連不到」的最常見原因就是 Ollama 沒改 listen address、預設只接受 loopback。

## 設計責任

選 listen address 是信任邊界決定：

- **`127.0.0.1`（預設）**：機器本身就是信任邊界、外部進不來、最安全
- **`0.0.0.0` 在家用 / 信任 LAN**：把 server 暴露給同網路裝置、便於多裝置共用、風險可接受
- **`0.0.0.0` 在公共 Wi-Fi / 對 internet**：等於對所有路過裝置開放、Ollama 沒有內建 auth、需要 SSH tunnel 或 reverse proxy + auth 才安全

Port 衝突的處理順序：用 `lsof` 確認佔用方身分 → 若是舊版自己 kill、若是別的服務改自己的 port → 同步更新 IDE plugin 的 `apiBase`。完整資料流判讀見 [0.7 隱私資料流](/llm/00-foundations/privacy-data-flow/)。
