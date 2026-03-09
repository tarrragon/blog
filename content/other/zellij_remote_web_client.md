---
title: "Zellij Web Client 外網連線教學"
date: 2026-03-09
draft: false
description: "讓別人透過瀏覽器連線到你的 Zellij session，包含 SSL 憑證申請、防火牆設定、Token 管理等完整步驟。"
tags: ["zellij", "terminal", "remote", "web"]
---

讓別人透過瀏覽器連線到你的 Zellij session。

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

申請憑證（將 `your-domain.com` 換成你的網域）：

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

> ⚠️ 自簽憑證瀏覽器會顯示安全警告，僅建議測試使用。

---

## 步驟二：開放防火牆 Port

Zellij web server 預設使用 port `3000`，需要對外開放：

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
  --bind 0.0.0.0:3000 \
  --cert /etc/letsencrypt/live/your-domain.com/fullchain.pem \
  --key /etc/letsencrypt/live/your-domain.com/privkey.pem
```

背景執行（daemon 模式）：

```bash
zellij web -d \
  --bind 0.0.0.0:3000 \
  --cert /path/to/cert.pem \
  --key /path/to/key.pem
```

停止 web server：

```bash
zellij web --stop
```

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
https://your-domain.com:3000/你的-session-名稱
```

首次連線會要求輸入 token，驗證後即可進入 session。

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

## 常見問題

**Q：連線後畫面沒有回應？**
檢查 port 3000 是否有被防火牆擋住。

**Q：瀏覽器顯示「不安全的連線」？**
使用了自簽憑證，在瀏覽器手動選擇繼續即可（測試環境）。正式使用請改用 Let's Encrypt。

**Q：如何確認 web server 是否在執行？**

```bash
zellij web --status
```

**Q：想換不同 port？**

```bash
zellij web --bind 0.0.0.0:8443 ...
```

記得同步更新防火牆規則。
