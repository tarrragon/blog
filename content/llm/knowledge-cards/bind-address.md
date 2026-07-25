---
title: "Bind Address"
date: 2026-05-12
description: "伺服器決定接受哪些網路介面的請求、127.0.0.1 / 0.0.0.0 / 具體 LAN IP 對應三層不同的暴露範圍"
weight: 1
tags: ["llm", "knowledge-cards", "security", "networking"]
---

Bind address 的核心概念是「伺服器啟動時決定『監聽哪個網路介面上的請求』」。同一個 port 在不同 bind address 下、能接受的請求來源完全不同；對本地 LLM [推論伺服器](/llm/knowledge-cards/inference-server/)（Ollama / llama-server / LM Studio）來說、bind address 是決定誰能連到模型的最直接設定。

## 概念位置

三層典型 bind address 的暴露範圍（延伸見 [port and localhost](/llm/knowledge-cards/port-and-localhost/)）：

| bind address                    | 接受來源       | 個人 dev 場景的常見用途             |
| ------------------------------- | -------------- | ----------------------------------- |
| `127.0.0.1` / `localhost`       | 只本機 process | VS Code 連本機 server、最安全預設   |
| 具體 LAN IP（如 `192.168.x.x`） | 同網段設備     | 想分享給家裡桌機 / 筆電             |
| `0.0.0.0`                       | 所有網路介面   | 容器化 / 想接受 LAN + WAN（風險高） |

關鍵差異：

1. `127.0.0.1` 只接 loopback、無論其他網路介面狀態都不接外部請求。
2. `0.0.0.0` 在所有介面上監聽、若機器有 public IP 或在公開 Wi-Fi、就會被網路上其他人連到。
3. 具體 LAN IP 是中間地帶、限定來源到該介面的網段。

檢查當前 bind 狀態的指令：

```bash
# macOS / Linux
lsof -i -P -n | grep LISTEN | grep <port>

# Linux
ss -lntp | grep <port>

# 或
netstat -an | grep LISTEN | grep <port>
```

看到 `127.0.0.1:<port>` 是 loopback、`*:<port>` 或 `0.0.0.0:<port>` 是所有介面。

## 設計責任

理解 bind address 後可以解釋兩個現象：為什麼預設安全的伺服器都 bind 到 `127.0.0.1`（避免不小心暴露）、為什麼 Docker `-p 8080:8080` 預設 bind 到 `0.0.0.0`（容器化的便利性、但對個人 dev 是潛在暴露點）。

設計本地推論伺服器時、預設 loopback、想分享 LAN 時 bind 到具體 LAN IP（不要直接 `0.0.0.0`）、要對外時加 [reverse proxy](/backend/knowledge-cards/api-gateway/) + auth + TLS。詳見 [6.1 推論伺服器的綁定與暴露範圍](/llm/06-security/inference-server-binding/) 跟 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)。
