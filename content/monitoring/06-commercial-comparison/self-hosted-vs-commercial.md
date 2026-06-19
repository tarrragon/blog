---
title: "自架 vs 商業的判斷決策表"
date: 2026-06-19
description: "使用者數、網路範圍、功能需求、合規要求四個維度判斷該自架還是用商業方案"
weight: 1
tags: ["monitoring", "comparison", "self-hosted", "commercial", "decision"]
---

自架監控和商業方案之間的選擇取決於四個維度的組合。每個維度有明確的閾值 — 超過閾值時自架的成本開始高於商業方案的訂閱費。

## 四個判斷維度

### 使用者數

自架方案的成本和使用者數幾乎無關（JSONL + grep 處理 1 個和 100 個使用者的成本差異很小）。商業方案按事件量或使用者數計費，使用者數增長直接推高費用。

**經驗估算**：使用者數在百人以下時，自架的總成本（開發 + 維護 + 硬體）通常低於商業方案的年費（以典型商業方案年費 $300-$600 和自架的開發維護時間估算）。使用者數在千人以上時，自架需要投入的基礎設施維護（高可用、擴容、備份）成本上升，商業方案的規模經濟開始有優勢。具體的交叉點取決於選用的 vendor 定價（Sentry Developer plan 免費額度 5000 events/月、PostHog 免費到 1M events/月）和自架的維護時間成本。

兩者之間是灰色地帶 — 取決於功能需求和團隊能力。

### 網路範圍

使用者和 collector 是否在同一個網路內。

**同一網路**（自用工具、內部工具）：自架方案直接 HTTP POST 到本機或內網 endpoint，不需要 DNS、TLS 憑證、CDN。成本極低。

**外部網路**（公開 app、SaaS）：自架方案需要處理公網暴露、DDoS 防護、TLS 憑證管理、高可用（多區域部署）。商業方案把這些基礎設施問題內化了。

### 功能需求

自架方案的功能上限是開發者願意投入的工程量。grep + jq 能做基礎查詢和 funnel 分析（[模組八 自架 funnel](/monitoring/08-business-analytics/)）。Dashboard、告警、session replay、A/B test 分群每個功能都是數週到數月的開發量。

商業方案的功能開箱即用。如果需求包含 session replay、A/B test dashboard、自動 issue 分群，商業方案的功能完成度遠高於自架。

### 合規要求

資料必須存放在特定地區（GDPR data residency）或不能離開公司網路（金融、醫療）。

**自架**：資料完全在自己的基礎設施上，資料位置由自己控制。適合最嚴格的合規要求。

**商業方案**：資料存放在 vendor 的基礎設施上。部分 vendor 提供 data residency 選項（Sentry 的 EU hosting、Datadog 的 EU region），但仍然是第三方持有資料。

## 決策表

| 維度     | 自架有利             | 商業方案有利              |
| -------- | -------------------- | ------------------------- |
| 使用者數 | < 100                | > 1000                    |
| 網路範圍 | 同一網路             | 外部網路                  |
| 功能需求 | 查詢 + 基礎分析      | Dashboard + 告警 + replay |
| 合規要求 | 資料不能離開自有設施 | 無特殊限制                |

四個維度中三個以上指向同一方向 → 選那個方向。兩兩對半 → 從自架開始（成本低、可逆），需求增長後再評估切換。

決策表指向商業方案後，[Sentry 深入](/monitoring/06-commercial-comparison/sentry-deep-dive/)和 [Firebase 套件](/monitoring/06-commercial-comparison/firebase-suite/)分別展開兩個主流方案的架構和能力邊界。決策表指向自架時，[模組四 Collector 設計](/monitoring/04-collector/)提供從 HTTP endpoint 到 rule engine 的完整實作藍圖。
