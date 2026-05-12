---
title: "6.1 推論伺服器的綁定與暴露範圍"
date: 2026-05-12
description: "個人 dev 場景下 llama-server / Ollama / LM Studio 的 bind address 判讀：127.0.0.1 vs LAN vs 反代、預設安全、誤開放給內網的後果"
tags: ["llm", "security", "inference-server", "bind-address", "network-exposure"]
weight: 2
---

推論伺服器的 [bind address](/llm/knowledge-cards/bind-address/) 決定誰能從網路連到模型。本章把「我這個 server 開到哪裡了」「家裡其他電腦該不該連得到」「反向代理會放大什麼風險」整理成可操作的判讀。實際 bind / `--host` / `OLLAMA_HOST` 等設定指令見 [1.0 Ollama](/llm/01-local-llm-services/ollama/)、[1.1 LM Studio](/llm/01-local-llm-services/lm-studio/)、[1.2 llama.cpp](/llm/01-local-llm-services/llama-cpp/)；PC 場景的 CUDA backend 跟 Windows firewall 差異見 [5.3](/llm/05-discrete-gpu/llama-cpp-on-pc/)、[5.4](/llm/05-discrete-gpu/lm-studio-on-windows/)。傳輸層加密見 backend [tls-mtls](/backend/knowledge-cards/tls-mtls/) 卡、流量限制見 backend [rate-limit](/backend/knowledge-cards/rate-limit/) 卡。本章 framing 是個人 dev 視角；production / 對外公開 API 服務的入口治理見 [Backend 7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)。

讀完本章後、你應該能對自己跑的推論伺服器回答：bind 在哪、誰能連到、預設配置安不安全、要分享給家裡其他電腦時該怎麼設、要透過反代或 tunnel 上 internet 時要做什麼。

## 本章目標

1. 認識 bind address 的三層典型範圍：loopback / LAN / WAN。
2. 區分 llama-server / Ollama / LM Studio 在三層上的預設行為差異。
3. 判讀「我要讓哪些機器連到這個 server」的工作流問題。
4. 認識反向代理 / Cloudflare Tunnel / Tailscale 把本地伺服器搬到網路上的延伸風險。
5. 對應的最低安全配置：auth、TLS、firewall 規則。

## bind address 的三層典型範圍

```text
┌──────────────────────────────────────────────────────────────┐
│ WAN（公開 internet）                                          │
│  ↑                                                            │
│  └─ 反代 / Cloudflare Tunnel / ngrok：本機 → 對外暴露         │
│                                                               │
│ LAN（家裡 / 辦公室內網）                                       │
│  ↑                                                            │
│  └─ 0.0.0.0 / 192.168.x.x：本機 → 內網其他電腦可連            │
│                                                               │
│ Loopback（本機）                                              │
│  └─ 127.0.0.1 / localhost：只能本機連                         │
└──────────────────────────────────────────────────────────────┘
```

三層的風險梯度：

| 層       | 誰能連             | 個人 dev 場景的常見用途                 | 暴露後果                                              |
| -------- | ------------------ | --------------------------------------- | ----------------------------------------------------- |
| Loopback | 只有本機 process   | VS Code Continue.dev、本機 CLI 工具     | 攻擊面最小、本機已被入侵就無防線                      |
| LAN      | 同一網段的所有設備 | 家裡其他電腦 / 平板用、實驗室共用       | 同網段惡意設備、訪客 Wi-Fi、IoT 設備都可能連          |
| WAN      | 整個 internet      | 出門用、分享給朋友、實驗 SaaS-like 部署 | 任何人都能掃到、不認識的人也能發 prompt、API key 被偷 |

## 三個主流伺服器的預設行為

| 伺服器                    | 預設 bind | 改 bind 的方式                           | 預設 auth            |
| ------------------------- | --------- | ---------------------------------------- | -------------------- |
| llama-server（llama.cpp） | 127.0.0.1 | `--host 0.0.0.0` 或 `--host 192.168.x.x` | 無、可用 `--api-key` |
| Ollama                    | 127.0.0.1 | 環境變數 `OLLAMA_HOST=0.0.0.0`           | 無、需自行加反代     |
| LM Studio（GUI 模式）     | 127.0.0.1 | Local Server 設定面板切換                | 無、需自行加反代     |

> **事實查核註**：上表的預設值是 2026 年 5 月主流版本的常見配置、各工具的預設值可能因版本變動、建議引用前以對應工具的官方文件跟 `--help` 為準。Ollama 從某個版本開始支援部分驗證機制、具體版本見 [Ollama GitHub release notes](https://github.com/ollama/ollama/releases)。

預設都是 `127.0.0.1`、是個人 dev 友善的安全起點。改到 `0.0.0.0` 之前、值得停下來想三個問題：

1. 真的需要其他機器連嗎？多數場景只需要本機連、保持 loopback。
2. 同網段有哪些其他設備？家裡的 IoT 設備、訪客手機都算。
3. 開出去後、API key / prompt 內容會被誰看到？

## 「不小心開到 LAN」的常見路徑

個人 dev 場景下、誤開放到 LAN 的常見路徑：

1. **複製貼上社群教學的指令**：教學作者也許在 lab 環境跑、把 `--host 0.0.0.0` 寫進範例；複製貼上時沒注意。
2. **Docker / 容器化跑伺服器**：Docker 預設 bridge 網路、若 `-p 8080:8080` 沒指定 host、port 會 bind 到所有介面、等同 `0.0.0.0`。改用 `-p 127.0.0.1:8080:8080` 限定本機。
3. **環境變數從 dotfile 載入**：把 `OLLAMA_HOST=0.0.0.0` 設在 dotfile、再裝其他工具時忘了這個設定還在生效。
4. **多台機器想互通**：例如 dev 用筆電、模型在桌機；想當作小型 server 時、若同網段有不信任的設備、就要做 auth。

檢查當前 bind 狀態的指令：

```bash
# macOS / Linux
lsof -i -P -n | grep LISTEN | grep -E "(ollama|llama|lmstudio|1234|8080|11434)"

# 或用 ss（Linux）
ss -lntp | grep -E "(1234|8080|11434)"

# 或用 netstat（macOS / Linux）
netstat -an | grep LISTEN | grep -E "(1234|8080|11434)"
```

看到 `127.0.0.1:11434` 是 loopback、`*:11434` 或 `0.0.0.0:11434` 是 bind 到所有介面。

## 暴露後的具體後果

把 bind 開到 LAN（甚至 WAN）、可能的具體後果：

1. **prompt 內容洩漏**：每個 prompt 包含的 code、檔案路徑、API key、商業邏輯都會在請求 body 裡。同網段任何人 dump 流量都能看到（HTTP）或要破 TLS（HTTPS）。
2. **API 被別人用**：對方拿你的 server 跑他自己的 prompt、消耗你的算力跟電費；若你的 server 連到雲端 LLM 當 fallback、會消耗你的 API quota。
3. **被當跳板**：tool use 啟用的話、攻擊者可以透過 prompt 觸發 tool 的副作用、讀寫檔案、執行 shell command（見 [6.2](/llm/06-security/tool-use-permission-model/)）。
4. **被當 DoS 目標**：發送大量 prompt 讓 GPU 滿載、影響本機其他工作。

WAN 暴露的進一步後果：

5. **被自動化 scanner 掃到**：internet 上有持續掃描常見 port 的 bot、`11434` / `8080` 是知名 LLM port、會被加進掃描清單。
6. **被列入公開 LLM 服務清單**：類似 Shodan 的服務會收錄對外可用的 inference endpoint、可能被「LLM as free service」目錄列進去。

> **事實查核註**：「公開 LLM endpoint 被掃描跟列進目錄」是社群觀察到的現象、具體 scanner 工具、目錄服務跟頻率依時段變動、建議引用前以 [Shodan](https://www.shodan.io/) 等公開掃描資料庫的當前狀態為準。

## 想分享 LAN 時的最低安全配置

如果你的工作流真的需要讓家裡另一台機器連（例如桌機跑模型、筆電寫 code）、最低應該做：

1. **限定 LAN 介面、不要 0.0.0.0**：bind 到具體 LAN IP（如 `--host 192.168.1.5`）、不要 bind 到所有介面。
2. **開 firewall 規則**：macOS 用內建 Firewall、Linux 用 ufw / iptables、Windows 用內建 Firewall、限定只接受同網段來源。
3. **加 API key**：llama-server 支援 `--api-key <key>`、其他伺服器透過反代（如 caddy / nginx）加 basic auth 或 API key。
4. **不接訪客 Wi-Fi**：訪客 Wi-Fi 通常跟主網段共用、要分開 VLAN 或直接不開放。
5. **檢查同網段設備清單**：用 `arp -a` 或 router 管理介面看連著哪些 MAC address、有不認識的就先別開。

## 想透過反代 / tunnel 上 WAN 的延伸風險

把本地 LLM 暴露到 WAN 的常見技術：

| 技術                  | 特性                                                    | 個人 dev 視角的風險                                                   |
| --------------------- | ------------------------------------------------------- | --------------------------------------------------------------------- |
| Cloudflare Tunnel     | 不開 router port、tunnel 進 Cloudflare、Cloudflare 對外 | prompt 經過 Cloudflare、依政策可能 log；Cloudflare 帳號是 trust point |
| ngrok                 | 同上、tunnel 進 ngrok                                   | 同上、ngrok 帳號是 trust point                                        |
| Tailscale / WireGuard | mesh VPN、端到端加密                                    | 設備加入 mesh 後互信、設備本身被入侵會直接拿到 LLM                    |
| nginx / caddy + 反代  | 自己跑反代、自己加 TLS / auth                           | 反代設定錯誤、TLS 證書管理失誤都會把 server 直接曝光                  |

進階防護見 [Backend 7.3 入口治理](/backend/07-security-data-protection/entrypoint-and-server-protection/) 跟 [Backend 7.5 傳輸信任與憑證生命週期](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)。個人 dev 場景的判讀：

1. **預設不要上 WAN**：若沒有具體需求（如多裝置工作流、跨地點協作）、保持 LAN 或 loopback。
2. **要上 WAN 時優先用 Tailscale-like mesh**：可以保持「私網」感覺、不暴露在公開 internet 上。
3. **真的要公開（如做給朋友試用的 demo）**：上反代、做 auth、明確跟使用者說會 log 什麼。

## 給讀者的綁定判讀流程

每次啟動 / 配置新伺服器時的判讀流程：

1. **明確列出「誰需要連」**：只有本機 IDE？家裡桌機？外出筆電？朋友的 demo？
2. **選擇對應的 bind 範圍**：本機選 loopback、家裡選 LAN IP、外出選 mesh VPN、公開 demo 才用反代。
3. **跑 `lsof / netstat / ss` 確認實際 bind 狀態**：跟意圖一致才算配好。
4. **若 bind 到 LAN / WAN、加 API key**：別假設「沒人會掃到」、做最低 auth。
5. **記下當前配置**：寫在 `~/llm/server-config.md` 之類、避免日後忘了哪台是哪個 mode。

## 小結

bind address 是本地 LLM 的第一個對外接觸面。個人 dev 場景下、預設 loopback 是合理起點、要開到 LAN 時需要明確意圖 + 最低 auth + firewall、要上 WAN 時優先用 mesh VPN 而不是反代直接公開。Docker / dotfile / 社群教學貼指令是常見的誤暴露路徑、值得每次配置完用 `lsof` 確認實際狀態。tool use 啟用時、bind 暴露的後果會放大、見下一章。

下一章：[6.2 tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/)、處理伺服器跑起來後最大的副作用面。
