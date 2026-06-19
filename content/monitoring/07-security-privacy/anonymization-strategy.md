---
title: "去識別化策略"
date: 2026-06-19
description: "IP 截斷 / user agent 簡化 / stack trace 路徑清理 / session UUID — 四種去識別化技術的適用場景和實作方式"
weight: 4
tags: ["monitoring", "security", "privacy", "anonymization", "gdpr"]
---

去識別化是把監控資料中可以關聯到特定個人的欄位，轉換成無法回溯到個人但仍保留分析價值的形式。去識別化和 [redaction](/monitoring/knowledge-cards/redaction/) 的差別在於：redaction 完全移除資訊（`[REDACTED]`），去識別化保留結構化的資訊但移除可識別性。

## IP 截斷

IP 位址是最常見的個人識別欄位。完整的 IPv4 位址（`192.168.1.50`）可以定位到特定的網路和裝置；截斷後的 IP（`192.168.1.0`）保留網段資訊但無法定位到特定裝置。

### 截斷策略

**IPv4 末八位清零**：`192.168.1.50` → `192.168.1.0`。保留 /24 網段資訊，足以判斷「使用者在哪個網段」但無法定位到特定裝置。Google Analytics 採用這個策略。

**IPv4 末十六位清零**：`192.168.1.50` → `192.168.0.0`。更強的去識別化，但地理定位精度降低到城市級。

**IPv6**：截斷更多位元。IPv6 的後 80 位通常包含 MAC 位址衍生的 interface ID — 截斷到 /48 前綴保留 ISP 資訊，移除裝置識別。

### 實作位置

IP 截斷應在 collector 收到事件後、寫入儲存前執行。SDK 端不做 IP 截斷 — SDK 通常不知道自己的外部 IP（知道的是 NAT 後的內部 IP），外部 IP 是 collector 從 HTTP request 的 source IP 取得的。

## User Agent 簡化

User agent 字串包含瀏覽器版本、OS 版本、裝置型號 — 組合起來可能形成唯一的 fingerprint。簡化 user agent 保留有用的分類資訊（「iOS 17 上的 Safari」），移除可用於 fingerprinting 的細節（「iPhone 15 Pro Max, Build/22A3354」）。

### 簡化規則

保留：平台（iOS / Android / Windows / macOS）、主要版本號（iOS 17、Android 14）、瀏覽器類型（Safari / Chrome / Firefox）。

移除：minor version、build number、裝置型號、CPU 架構、語言設定。

```text
原始：Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X)
簡化：iOS/17 Safari
```

## Stack Trace 路徑清理

Error 事件的 stack trace 包含檔案路徑。檔案路徑可能洩漏部署結構（`/home/deploy_user/app/v2.3.1/src/...`）或開發者的個人資訊（`/Users/alice/projects/...`）。

### 清理規則

**移除使用者目錄前綴**：`/Users/alice/projects/app/src/main.dart:42` → `src/main.dart:42`。保留 source file 相對路徑和行號，移除使用者名稱。

**移除部署路徑前綴**：`/opt/deploy/releases/20260619/app/lib/...` → `lib/...`。保留程式碼結構，移除部署細節。

**統一 path separator**：Windows 路徑（`C:\Users\...`）和 Unix 路徑（`/home/...`）統一處理。

清理規則用正則表達式匹配常見的路徑前綴模式，替換為空字串。自訂的部署路徑格式需要在 collector 設定中額外註冊。

## Session UUID

Session ID 用於關聯同一次使用中的多個事件。UUID v4（隨機產生）作為 session ID，沒有可預測性、沒有順序性、無法回推使用者身份。

### Session ID 的生命週期

SDK 在初始化時產生一個 UUID v4 作為 session ID，所有事件附帶這個 ID。App 重新啟動時產生新的 session ID — 前後兩次使用的事件無法關聯。

這個設計讓分析粒度限制在「一次使用」而非「一個使用者」。如果需要跨 session 關聯（例如計算 DAU），需要另一個 persistent ID — 但 persistent ID 本身就是可識別資訊，需要使用者同意。

### 避免使用可識別的 ID

裝置 ID（IDFA / GAID）、安裝 ID、使用者帳號 — 這些可以關聯到特定個人，不適合作為監控系統的 session ID。使用 UUID v4 確保 session ID 的唯一性來自隨機性而非身份。

去識別化是資料保護的一環，另一環是在資料離開 client 之前就處理 — [SDK Redaction API 設計](/monitoring/07-security-privacy/sdk-redaction-api/)從 SDK 端攔截敏感欄位。法規層面的具體要求見 [GDPR 最小化原則的工程落地](/monitoring/07-security-privacy/gdpr-minimization/)。去識別化完成後的資料才能用於[行為分析](/monitoring/08-business-analytics/) — 這是商業利用的入場條件。
