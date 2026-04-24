---
title: "模組八：Go 案例與讀碼路線"
date: 2026-04-23
description: "用一家公司一章的方式理解 Go 在真實服務中的使用方式"
weight: 8
---

這個模組把前面學到的 Go 能力放回真實世界：哪些公司把 Go 用在什麼服務裡、他們為什麼選 Go、以及公開原始碼長什麼樣子。語法學習完成後，案例能幫讀者把語言能力、服務場景與選型條件對齊。

## 章節列表

| 章節                               | 主題                                       | 關鍵收穫                                          |
| ---------------------------------- | ------------------------------------------ | ------------------------------------------------- |
| [8.0](/go/08-case-studies/selection-patterns/)         | Go 的選型案例總覽                          | 用服務壓力辨識 Go 常出現的選型條件                |
| [8.1](/go/08-case-studies/google/)                     | Google：大規模微服務與索引服務             | 看懂 Go 如何支撐大規模搜尋與資料處理              |
| [8.2](/go/08-case-studies/paypal/)                     | PayPal：支付平台與 NoSQL / build pipelines | 看懂 Go 如何處理複雜系統與多執行緒邊界            |
| [8.3](/go/08-case-studies/dropbox/)                    | Dropbox：從 Python 遷移到 Go               | 看懂性能關鍵後端如何逐步轉向 Go                   |
| [8.4](/go/08-case-studies/microsoft/)                  | Microsoft：雲端基礎設施的一部分            | 看懂 Go 如何支撐 cloud infrastructure             |
| [8.5](/go/08-case-studies/twitch/)                     | Twitch：直播與聊天室系統                   | 看懂 Go 如何服務低延遲、高併發的即時系統          |
| [8.6](/go/08-case-studies/cloudflare/)                 | Cloudflare：DNS、SSL 與長連線服務          | 看懂 Go 如何處理網路邊界與大量連線                |
| [8.7](/go/08-case-studies/cockroach-labs/)             | Cockroach Labs：分散式 SQL 資料庫          | 看懂 Go 如何支撐高一致性、高複雜度系統            |
| [8.8](/go/08-case-studies/stream/)                     | Stream：Feeds 與 Chat                      | 看懂 Go 如何支撐大規模即時訊息服務                |
| [8.9](/go/08-case-studies/cloudwego/)                  | ByteDance / CloudWeGo：微服務基礎設施      | 看懂 Go 如何沉澱成微服務治理與框架                |
| [8.10](/go/08-case-studies/high-concurrency-services/) | Go 的高併發服務案例                        | 從長連線、代理、背景處理與資料服務辨識並發壓力    |
| [8.11](/go/08-case-studies/open-source-code-reading/)  | Go 公開原始碼讀碼路線                      | 用入口、組裝、邊界、並發 owner 與測試建立讀碼順序 |

## 案例分類的閱讀方式

案例分類的核心原則是先看服務壓力，再看公司名稱。Google、PayPal、Dropbox、Microsoft、Twitch、Cloudflare、Cockroach Labs、Stream 與 CloudWeGo 代表的是不同工程條件：大規模平台、高併發即時服務、效能敏感遷移、分散式資料系統與微服務治理。

大規模平台案例通常要觀察服務形狀是否一致：入口、設定、[log](/backend/knowledge-cards/log)、部署與 [health check](/backend/knowledge-cards/health-check-liveness) 是否能被很多團隊共用。高併發即時案例通常要觀察連線是否長時間存在，以及 server 是否需要管理大量 client 狀態。效能敏感遷移案例通常要觀察瓶頸是否集中在清楚邊界。分散式基礎設施案例則要觀察主要問題是否落在多節點協調與可靠性。

這張表是入口索引。讀每家公司案例時，應回到具體章節對照：選型判斷看 [Go 的選型案例總覽](/go/08-case-studies/selection-patterns/)，並發服務看 [Go 的高併發服務案例](/go/08-case-studies/high-concurrency-services/)，公開原始碼則依照 [Go 公開原始碼讀碼路線](/go/08-case-studies/open-source-code-reading/) 逐層閱讀。

## 這個模組的用途

- 幫讀者把 Go 的抽象能力對回真實服務
- 幫讀者確認 Go 常落在哪些產品與系統邊界
- 幫讀者建立讀公開原始碼的路線圖
- 幫讀者把「案例」與「實作細節」連起來

## 建議閱讀順序

1. 先看 Google 與 PayPal，理解大規模服務與複雜平台怎麼選 Go
2. 再看 Dropbox、Microsoft、Twitch、Cloudflare，理解性能、即時與基礎設施場景
3. 接著看 Cockroach Labs、Stream、CloudWeGo，理解更極端的高併發與分散式系統
4. 最後再回頭看自己的服務場景，判斷哪些模式值得借用
