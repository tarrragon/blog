---
title: "Zellij Web Client 外網連線教學"
date: 2026-03-09
draft: false
description: "要讓別人透過瀏覽器連進你的 Zellij session、需要設定 SSL 憑證／防火牆／token 時回來讀"
tags: ["zellij", "terminal", "remote", "web"]
---

Zellij Web Client 讓他人透過瀏覽器連線到指定的 Zellij session，承擔的責任是把終端機多工環境分享給沒有 SSH 連線的協作者。本文承接 [終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/) 的多工器分類；zellij 的本機 pane 操作見 [Zellij 多終端機操作指南](/linux/tools/cli/zellij-pane/)、session 生命週期的 CLI 操作見 [Zellij session 生命週期](/linux/tools/cli/zellij-session-lifecycle/)、tmux 的持久化基礎見 [tmux 基礎](/linux/tools/cli/tmux-persistence-and-basics/)。

---

## 安裝 Zellij

```bash
# macOS
brew install zellij

# Linux（使用安裝腳本）
bash <(curl -L zellij.dev/launch)

# Windows（需要支援原生 Windows 的版本，詳見 GitHub Releases）
# 從 https://github.com/zellij-org/zellij/releases 下載 Windows 版 .zip
# 解壓後將 zellij.exe 加入 PATH
```

確認版本（需 v0.43.0 以上）：

```bash
zellij --version
```

---

## 事前準備

- 一個網域名稱（或固定 IP）
- SSL 憑證（對外連線強制要求）
- SSH 連線能力（如需遠端操作主機）→ 參考 [SSH Key 設定筆記]({{< ref "/work-log/ssh_key_setup" >}})

---

## 步驟一：取得 SSL 憑證

外網連線強制使用 HTTPS，必須提供 SSL 憑證。

> 取得 Let's Encrypt 憑證的 `certbot` 指令需真實網域、本機未實機驗證；自簽憑證的 `openssl` 指令、以及 zellij web server 啟停與 token 管理已在 localhost 實機驗證。

### 使用 Let's Encrypt（免費，推薦）

需要先安裝 `certbot`：

```bash
# macOS
brew install certbot

# Ubuntu / Debian
sudo apt install certbot

# Windows（使用 Chocolatey）
choco install certbot
# 或使用 win-acme（Windows 原生替代方案）：https://www.win-acme.com/
```

申請憑證（將 `your-domain.com` 換成實際網域）：

```bash
sudo certbot certonly --standalone -d your-domain.com
```

> Windows 上若未使用 WSL，建議改用 [win-acme](https://www.win-acme.com/)，操作更直覺。

憑證預設存放在：

```text
# macOS / Linux
/etc/letsencrypt/live/your-domain.com/fullchain.pem   # 憑證
/etc/letsencrypt/live/your-domain.com/privkey.pem      # 私鑰

# Windows（certbot）
C:\Certbot\live\your-domain.com\fullchain.pem
C:\Certbot\live\your-domain.com\privkey.pem
```

### 使用自簽憑證（測試用）

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

> 注意：自簽憑證會讓瀏覽器在連線時顯示安全警告，於測試環境手動選擇繼續即可；正式對外服務改用上面的 Let's Encrypt 憑證。

---

## 步驟二：開放防火牆 Port

Zellij web server 預設只綁本機 `127.0.0.1:8082`，要讓外網連入必須顯式綁到對外位址（見步驟四的 `--ip 0.0.0.0`）並開放對應 port。本教學以 port `3000` 為例（port 可自選），需對外開放這個 port：

> 以下防火牆指令（`ufw` / `pf` / Windows Defender）依各平台官方用法、環境特定、本機未實機驗證。

### Linux（ufw）

```bash
sudo ufw allow 3000/tcp

# 或指定來源 IP（更安全）
sudo ufw allow from 1.2.3.4 to any port 3000
```

### macOS

macOS 內建的防火牆是應用程式層級的，無法直接開放特定 port。通常有兩種做法：

1. **系統偏好設定** → 網路 → 防火牆 → 確認沒有擋住 Zellij
2. **使用 `pf`**（進階，通常不需要）：

```bash
# 新增規則到 /etc/pf.conf
echo "pass in proto tcp from any to any port 3000" | sudo tee -a /etc/pf.conf
sudo pfctl -f /etc/pf.conf
```

> macOS 預設防火牆通常不會擋住主動開啟的服務，多數情況下不需要額外設定。如果是在家用網路，記得在路由器設定 port forwarding。

### Windows

```powershell
# 使用 Windows Defender Firewall（以系統管理員執行 PowerShell）
New-NetFirewallRule -DisplayName "Zellij Web" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow

# 或限制來源 IP（更安全）
New-NetFirewallRule -DisplayName "Zellij Web" -Direction Inbound -Protocol TCP -LocalPort 3000 -RemoteAddress 1.2.3.4 -Action Allow
```

> Zellij 已支援原生 Windows，直接在 PowerShell 或 Windows Terminal 中執行即可。

如果是雲端主機（AWS、GCP、Azure 等），記得同步在後台的安全群組開放 port 3000。

---

## 步驟三：啟動 Zellij

先啟動一個 Zellij session：

```bash
zellij
```

---

## 步驟四：啟動 Web Server

在 Zellij 內，按 `Ctrl+o` 然後按 `s` 開啟 share plugin，從 UI 啟動 web server。

或直接用 CLI 啟動並指定憑證：

```bash
zellij web \
  --ip 0.0.0.0 --port 3000 \
  --cert /etc/letsencrypt/live/your-domain.com/fullchain.pem \
  --key /etc/letsencrypt/live/your-domain.com/privkey.pem
```

背景執行（daemon 模式）：

```bash
zellij web -d \
  --ip 0.0.0.0 --port 3000 \
  --cert /path/to/cert.pem \
  --key /path/to/key.pem
```

停止 web server：

```bash
zellij web --stop
```

確認 web server 執行狀態：

```bash
zellij web --status
```

Zellij web 預設綁 `127.0.0.1:8082`、只接受本機連線；對外服務必須用 `--ip 0.0.0.0` 顯式綁到對外位址、並用 `--port` 指定埠（本教學用 `3000`）。改用其他 port 時把 `--port` 一併調整（例如 `--port 8443`），防火牆規則也要同步改成該 port。

---

## 步驟五：產生登入 Token

為了安全，別人連線前需要用 token 登入，**token 只會顯示一次**，請立即複製。

```bash
zellij web --create-token
```

或在 share plugin（`Ctrl+o` + `s`）裡產生。

將 token 分享給要連線的人。

---

## 步驟六：連線

對方在瀏覽器輸入：

```text
https://your-domain.com:3000/實際-session-名稱
```

首次連線會要求輸入 token，驗證後即可進入 session。若連線後畫面沒有回應，多半是 port 未對外開放，確認防火牆與雲端主機安全群組是否放行該 port。

---

## 連線後的行為

| 情況                   | 結果                            |
| ---------------------- | ------------------------------- |
| Session 正在執行       | 直接 attach 進去                |
| Session 曾存在但已結束 | Zellij 自動重建（resurrection） |
| 全新 session 名稱      | 建立新的 session                |

多人連線時，每個人都有自己的游標，可以同時操作。

---

## 安全建議

- Token 用完後記得撤銷：從 share plugin 或 CLI 管理
- 盡量限制開放的來源 IP，避免對全網開放
- 不建議長期開啟 web server，用完就關
- 撤銷 token 時，所有對應的 session token 也會一併失效

---

## 下一步路由

- zellij 的本機 pane 操作（查看佈局、讀取其他 pane、調整大小）：[Zellij 多終端機操作指南](/linux/tools/cli/zellij-pane/)。
- 不需要瀏覽器、純 SSH 的多工器持久化：[tmux 基礎](/linux/tools/cli/tmux-persistence-and-basics/)。
- 多工器在整個遠端工具選型中的定位：[終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/)。
