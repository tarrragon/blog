---
title: "8.10 Stakeholder 通訊與外部狀態頁"
date: 2026-05-01
description: "把 impact scope、status page、補償政策串成節奏"
weight: 10
---

## 大綱

- 通訊對象分層：內部 [incident command system](/backend/knowledge-cards/incident-command-system/) team、跨部門 stakeholder、客戶、媒體 / 監管
- 跟 [8.4 incident communication](/backend/08-incident-response/incident-communication/) 的分工：8.4 是事中通訊節奏、8.10 是對外承諾與補償
- [status page](/backend/knowledge-cards/status-page/) 設計：影響範圍、嚴重度標示、ETA、更新頻率
- 對外溝通的三個窗：發現、定位、回復（什麼時候該說什麼）
- 補償政策：SLA credit、refund、goodwill；何時主動 / 何時被動
- 法規通報：資安事件 vs 可用性事件的法規差異（GDPR / 個資）
- 反模式：[status page](/backend/knowledge-cards/status-page/) 滯後、語焉不詳、過度承諾 ETA、通報義務漏判

## 概念定位

Stakeholder 通訊與外部狀態頁是把 [impact scope](/backend/knowledge-cards/impact-scope/)、[status page](/backend/knowledge-cards/status-page/) 與補償政策串成一個外部承諾流程，責任是讓不同對象在同一時間看到一致的事件敘述。

這一頁處理的是對外責任，不只是發布訊息。當外部承諾過度或不一致，信任成本通常比故障本身更高。

## 核心判讀

判讀 stakeholder communication 時，先看訊息是否分層，再看 [impact scope](/backend/knowledge-cards/impact-scope/) 與 [status page](/backend/knowledge-cards/status-page/) 是否可執行。

重點訊號包括：

- 內部、客戶、媒體 / 監管是否有不同的訊息節奏
- [status page](/backend/knowledge-cards/status-page/) 是否能清楚描述影響範圍與 ETA
- 補償政策是否預先定義，不靠單次協商
- 法規通報是否有 checklist 與 owner

## 案例對照

- [Slack](/backend/08-incident-response/cases/slack/_index.md)：面向大量工作團隊時，外部狀態頁就是產品的一部分。
- [Microsoft 365](/backend/08-incident-response/cases/microsoft-365/_index.md)：廣泛影響的協作服務需要很清楚的外部節奏。
- [GitHub](/backend/08-incident-response/cases/github/_index.md)：平台型服務的 status page 會直接影響信任。

## 下一步路由

- 04.10 client-side / RUM：客戶感知影響的訊號來源
- 07 資安：資料外送事件的通報路徑
- 08.4 內部通訊：跨層通訊節奏對齊
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：對外公開的 [RCA](/backend/knowledge-cards/rca/) 範圍判定

## 判讀訊號

- [status page](/backend/knowledge-cards/status-page/) 比客戶在 Twitter / 社群上的回報慢
- 對外 [RCA](/backend/knowledge-cards/rca/) 跟內部 [RCA](/backend/knowledge-cards/rca/) 落差大、外部過度修飾
- 補償政策 case-by-case、無預設規則、依個別協商
- 法規通報窗口靠 IR commander 個人記憶、無 checklist
- ETA 過度承諾、後續多次延期、消耗信任

## 交接路由

- 04.10 client-side / RUM：客戶感知影響的訊號來源
- 07 資安：資料外送事件的通報路徑
- 08.4 內部通訊：跨層通訊節奏對齊
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：對外公開的 [RCA](/backend/knowledge-cards/rca/) 範圍判定
- 08.14 multi-incident：多事故對外通訊不可矛盾
- 08.15 vendor 事故：對外通訊的承擔邊界
- 08.17 security vs operational：法規通訊的邊界差異
