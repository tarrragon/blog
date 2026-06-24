---
title: "監控資料洩漏的 Threat Model"
date: 2026-06-19
description: "監控系統本身是攻擊面 — 四個威脅場景（傳輸竊聽 / 儲存入侵 / endpoint 濫用 / 內部越權存取）的風險評估和防護措施"
weight: 6
tags: ["monitoring", "security", "threat-model", "attack-surface", "risk"]
---

監控系統收集的資料本身就是有價值的攻擊目標。Error 訊息包含 stack trace 和系統架構資訊，event 資料包含使用者行為模式，lifecycle 資料包含部署時程和系統狀態。攻擊者取得這些資料後可以用於進一步的攻擊 — stack trace 揭露程式碼結構，部署資訊揭露更新節奏，行為資料揭露高價值使用者。

## 威脅場景一：傳輸竊聽

### 攻擊方式

攻擊者在 SDK 和 collector 之間的網路路徑上攔截未加密的 HTTP 流量。同網段的 ARP spoofing、WiFi sniffing、或中間人（MITM）proxy。

### 暴露的資料

事件的完整 JSON payload — 包括 redaction 後殘留的資訊（使用者行為、系統狀態、error message）。API key 或 basic auth credential 如果在 HTTP header 中明文傳送，也會被攔截。

### 防護

使用 HTTPS 加密傳輸（[Transport 安全](/monitoring/07-security-privacy/transport-security/)）。所有 SDK 到 collector 的通訊走 TLS — 自簽憑證在自用場景足夠，公開部署用 Let's Encrypt。

## 威脅場景二：儲存入侵

### 攻擊方式

攻擊者取得 collector server 的存取權限（SSH 入侵、容器逃逸、雲端 IAM 權限提升），直接讀取儲存的事件檔案。

### 暴露的資料

所有歷史事件 — 包含 redaction 處理後的事件。如果 redaction 不完整（遺漏了某些敏感欄位），歷史事件中可能包含 secret。

### 防護

**最小化儲存**：只保留必要期限的資料，過期自動刪除（[GDPR 最小化原則](/monitoring/07-security-privacy/gdpr-minimization/)）。攻擊者能取得的資料量與保留期間成正比。

**檔案系統加密**：LUKS（Linux）或 FileVault（macOS）對整個磁碟加密。Server 關機後磁碟資料無法被讀取。

**access log 監控**：記錄所有對事件儲存的存取操作（[Collector Access Control](/monitoring/07-security-privacy/collector-access-control/)）。異常存取（非工作時間、非預期的 IP）觸發告警。

## 威脅場景三：Endpoint 濫用

### 攻擊方式

攻擊者取得 SDK 的 API key（從 client 端的程式碼或設定檔中提取），大量寫入垃圾事件或惡意 payload。

### 影響

**資料汙染**：合法事件和垃圾事件混在一起，分析結果不可靠。

**資源耗盡**：大量寫入消耗 collector 的儲存和處理能力。

**注入攻擊**：如果 collector 的查詢介面沒有做好輸入驗證，惡意 payload 中的特殊字元可能觸發 injection。

### 防護

**Rate limit**：每個 API key 的寫入速率限制。正常的 SDK 行為有可預測的寫入頻率（每分鐘 N 個事件），超出正常範圍的寫入被拒絕。

**Schema validation**：collector 只接受符合定義 schema 的事件。格式異常的 payload 在寫入前被丟棄。

**API key 輪替**：如果 API key 被洩漏，輪替 key 讓舊 key 失效。SDK 端更新新 key 後恢復正常。

## 威脅場景四：內部越權存取

### 攻擊方式

有 collector 讀取權限的人（開發者、維運人員）存取超出自己職責範圍的事件資料。例如開發者查看行為分析資料（只應該看 debug 資料），或前端開發者查看 server-side 的 error 事件。

### 防護

**角色分離**：不同用途的資料用不同的存取權限（[Collector Access Control](/monitoring/07-security-privacy/collector-access-control/)）。Debug 資料和行為分析資料分開授權。

**去識別化**：即使有存取權限，看到的也是去識別化後的資料（[去識別化策略](/monitoring/07-security-privacy/anonymization-strategy/)）。IP 截斷、user agent 簡化、stack trace 路徑清理 — 降低資料的個人可識別性。

**access log 審計**：所有讀取操作記錄在 access log 中，定期 review。

## 下一步路由

- SDK 端的 redaction → [SDK Redaction API 設計](/monitoring/07-security-privacy/sdk-redaction-api/)
- Transport 層保護 → [Transport 安全](/monitoring/07-security-privacy/transport-security/)
- Collector 端保護 → [Collector Access Control 實作](/monitoring/07-security-privacy/collector-access-control/)
- 去識別化技術 → [去識別化策略](/monitoring/07-security-privacy/anonymization-strategy/)
- Client-side SDK 認證的多層緩解策略 → [Client-side SDK 認證](/monitoring/07-security-privacy/client-sdk-authentication/)
