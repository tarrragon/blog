---
title: "7.C11 選型：單人遠端 Shell — Tailscale vs Cloudflare Tunnel"
date: 2026-06-17
description: "以「手機遠端操作本機 shell」為情境，比較 Tailscale mesh VPN 與 Cloudflare Tunnel + Access 兩種存取模型的選型判讀。"
weight: 11
tags: ["backend", "security", "case-study", "tailscale", "cloudflare", "remote-access"]
---

這篇選型比較的核心情境是**單人自用遠端 shell 存取**：人在外、手機操作家中或辦公室本機的真實終端機（zsh）。兩個候選方案代表兩種根本不同的安全模型——「公開端點 + 多層防護」vs「私有網路 + 端點不存在」。

## 情境約束

- 單人自用（owner = 開發 = 維運 = 唯一用戶）
- 失敗代價高：整台機器的 shell 外洩
- 手機端需自建 Flutter 終端機 UI（兩方案皆需）
- 預算趨近零（免費方案）

## 兩方案架構對比

### 方案 A：Cloudflare Tunnel + Cloudflare Access

```
Flutter app（Face ID）
   │  WSS，帶三組憑證
   ▼
Cloudflare Tunnel（named，固定網域）
   ▼
Cloudflare Access（邊緣：驗 Service Token）── 未授權流量在此被擋
   ▼
Go proxy（本機：驗 X-App-Tunnel-Token）── 第二道
   ▼
ttyd（本機：basic auth）── 第三道
   ▼
zsh
```

### 方案 B：Tailscale mesh VPN

```
Flutter app（Face ID）
   │  WS，帶 ttyd basic auth
   ▼
Tailscale mesh VPN（WireGuard 加密隧道，裝置級認證）
   ▼
Go proxy（本機：稽核 log + 透明轉發，不做認證）
   ▼
ttyd（本機：basic auth）── 應用層最後防線
   ▼
zsh
```

## 核心選型維度

| 維度 | Cloudflare Tunnel + Access | Tailscale |
|------|---------------------------|-----------|
| **網路模型** | 出站連線到 CF 邊緣，產生**公開 URL** | WireGuard mesh VPN，裝置間**私有 IP**，無公開端點 |
| **攻擊面** | 公開 URL 存在，需層層防護 | 服務端點不存在於公開網路，攻擊者連 IP 都到不了 |
| **認證層數** | 三層：CF Access + proxy token + ttyd | 兩層：Tailscale 裝置認證 + ttyd |
| **Go proxy 職責** | 驗 token + 稽核 log + 轉發 | 稽核 log + 轉發（不做認證） |
| **元件數** | 5（app → CF → CF Access → proxy → ttyd） | 3（app → Tailscale → proxy/ttyd） |
| **需要自有網域** | 是 | 否（MagicDNS 自動分配） |
| **啟停行程數** | 3（cloudflared + ttyd + proxy） | 2（ttyd + proxy），Tailscale daemon 常駐 |
| **憑證包欄位** | 8 欄（含 CF Access 憑證 + proxy token） | ~5 欄（endpoint + ttyd 帳密） |
| **密鑰管理複雜度** | 高（proxy token 需可插拔後端 keychain/file/env） | 低（僅 ttyd 帳密） |
| **費用** | 免費（Cloudflare 個人方案） | 免費（Tailscale 個人方案，100 裝置內） |
| **外部依賴** | Cloudflare 邊緣網路 + CF Access 控制面 | Tailscale 協調伺服器 + DERP relay |

## 選型判讀

### Tailscale 勝出的場景（本情境適用）

- **攻擊面最小化是首要目標**：shell 閘道的失敗代價極高，「端點不存在」比「保護公開端點」本質上更安全
- **單人自用**：不需要 CF Access 的多人 policy / IdP 整合 / Device Posture 等企業功能
- **架構簡單性**：從 5 元件 3 層認證縮為 3 元件 2 層認證，Go proxy 職責大幅簡化（砍認證閘道，只留 log + 轉發）
- **密鑰管理簡化**：不再需要為 proxy token 建可插拔多後端（keychain/file/env），只管 ttyd 帳密
- **不需要自有網域**：Tailscale MagicDNS 或直接用 Tailscale IP

### Cloudflare Tunnel 勝出的場景（本情境不適用，但值得記錄）

- **需要對外提供服務**（非自用）：CF 的 WAF / CDN / rate limit / bot protection 生態豐富
- **需要 HTTP 層細粒度存取控制**：CF Access 的 Application + Policy 模型適合管多個 internal web app
- **需要 Device Posture 檢查**：CF 整合 CrowdStrike / SentinelOne 等 EDR 做裝置健康判斷
- **已在用 Cloudflare 生態**：共用控制面的管理紅利（同一 Logpush / API token / Audit Log）
- **多人 / 多團隊 / 合規場景**：CF Access 的 IdP 整合 + Service Auth + Audit Log 比 Tailscale 個人方案完整

### 邊界情境

- **多人但仍小規模**（2-5 人）：Tailscale ACL 足以控制；超過此規模再評估 CF Access 或 Teleport
- **需要 session recording**：兩者都沒有一流方案——Tailscale 需 Enterprise tier，CF Access 只記 metadata 不錄 keystroke。重 audit 走 [Teleport](/backend/07-security-data-protection/vendors/teleport/)
- **需要從固定 IP 出網**：Tailscale Exit Node 可做但不是設計核心；CF 有更成熟的方案

## Tailscale 採用後的安全底線

即使 Tailscale 攻擊面更小，仍需維持以下底線：

| 底線 | 說明 |
|------|------|
| ttyd 綁 Tailscale 介面或 localhost | 不監聽公開網路介面 |
| Tailscale ACL 限制裝置 | 只有 owner 裝置可存取 proxy port |
| ttyd basic auth | Tailscale 萬一被穿越的最後防線 |
| 稽核 log | proxy 記錄每次連線（client_ip，不含 PTY 內容） |
| 不開機自啟（ttyd/proxy） | 手動起停最小化服務暴露窗 |

## 此選型的 tripwire

| 訊號 | 觸發後重評 |
|------|-----------|
| 從單人變多人 | Tailscale ACL 是否足夠，或需升級為 Teleport / CF Access |
| 需要對外暴露服務 | Tailscale Funnel 不適合 production hardened ingress，改走 CF |
| 需要合規 session recording | Tailscale Enterprise 或改走 Teleport |
| 需要 WAF / bot protection | Tailscale 沒有應用層防護，改走 CF |

## 從本情境到 vendor 詳頁

- Tailscale 完整 vendor 判讀 → [Tailscale SSH](/backend/07-security-data-protection/vendors/tailscale-ssh/)
- Cloudflare Access 完整 vendor 判讀 → [Cloudflare Access](/backend/07-security-data-protection/vendors/cloudflare-access/)
- Infrastructure access + 合規場景 → [Teleport](/backend/07-security-data-protection/vendors/teleport/)
- 本選型的章節歸屬 → [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)
