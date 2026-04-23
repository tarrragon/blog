---
title: "0.2 狀態與資料儲存選型"
date: 2026-04-23
description: "區分 source of truth、快取、搜尋索引、event log 與 object storage 的選型邊界"
weight: 2
---

狀態與資料儲存選型的核心原則是先判斷資料責任。正式狀態、暫存資料、搜尋索引、事件歷史與大型檔案都屬於資料，但它們需要不同服務能力。

## 本章目標

學完本章後，你將能夠：

1. 區分 source of truth、cache、search index、event log 與 object storage
2. 用資料生命週期判斷儲存服務類型
3. 看懂資料庫與 Redis、搜尋引擎、event store、object storage 的差異
4. 把資料選型轉成可檢查的工程判斷

---

## 【觀察】資料類型不同，儲存責任也不同

資料儲存服務的第一個問題是「這份資料扮演什麼責任」。同一份商品資料可以同時出現在 PostgreSQL、Redis、Elasticsearch、[event log](../knowledge-cards/event-log/) 與 [object storage](../knowledge-cards/object-storage/) 裡，但每個位置的責任不同。

| 資料責任 | 可觀察特徵 | 常見服務方向 |
| -------- | ---------- | ------------ |
| 正式狀態 | 需要交易、一致性、查詢與長期保存 | SQL / document database |
| 暫存讀取 | 來源資料已存在，目標是降低讀取成本 | Redis / cache |
| 搜尋查詢 | 需要[全文搜尋](../knowledge-cards/full-text-search/)、排序、[facet](../knowledge-cards/facet-query/)、相關性 | search engine |
| 事件歷史 | 需要追蹤發生過的事、audit、replay | [event log](../knowledge-cards/event-log/) / stream |
| 大型檔案 | 需要保存圖片、影片、報表、備份 | [object storage](../knowledge-cards/object-storage/) |

這張表是索引。選型時要看資料是否能重建、是否需要一致性、是否要被使用者查詢、是否承擔稽核責任。

## 【判讀】source of truth 承擔正式狀態

[Source of truth](../knowledge-cards/source-of-truth/) 的核心責任是保存系統承認的正式狀態。當資料需要被交易保護、被多個流程共同讀寫、支援一致查詢與長期保存時，應先評估資料庫。

接近真實網路服務的例子包括：

- 訂單狀態：created、paid、shipped、refunded
- 會員帳號：email、password hash、角色、訂閱方案
- 付款紀錄：交易 ID、金額、貨幣、狀態、時間

這類資料的主要風險是寫入一致性。服務要知道誰能改狀態、哪些欄位要一起成功、失敗後如何重試或補償。這些問題通常屬於資料庫與 transaction 邊界。

## 【判讀】cache 承擔可重建的讀取加速

cache 的核心責任是降低讀取成本。快取資料應該能從 [source of truth](../knowledge-cards/source-of-truth/) 或下游服務重建；它的價值在於吸收熱門讀取、降低延遲、保護正式資料來源。

接近真實網路服務的例子包括：

- 商品詳情頁快取商品名稱、價格與庫存摘要
- 使用者 session 或權限摘要
- [WebSocket](../knowledge-cards/websocket/) presence 狀態與 topic 訂閱集合

這類資料的主要風險是過期與不一致。服務要知道 cache miss 怎麼處理、TTL 如何設定、資料更新時如何失效、熱門 key 如何保護。

## 【判讀】search index 承擔查詢體驗

[Search index](../knowledge-cards/search-index/) 的核心責任是支援搜尋體驗。當使用者需要[全文搜尋](../knowledge-cards/full-text-search/)、排序、filter、[facet](../knowledge-cards/facet-query/)、autocomplete 或相關性排序，搜尋索引通常比一般資料庫查詢更合適。

接近真實網路服務的例子包括：

- 電商商品搜尋與分類篩選
- 文件站全文搜尋
- 企業知識庫搜尋與權限過濾

這類資料的主要風險是索引延遲與查詢語意。正式狀態通常仍在資料庫，[search index](../knowledge-cards/search-index/) 是為搜尋體驗建立的讀取模型。服務要知道資料更新後多久進索引、搜尋結果是否允許短暫延遲。

## 【判讀】event log 承擔歷史與重播

[Event log](../knowledge-cards/event-log/) 的核心責任是保存已發生的事。當系統需要 audit、replay、補送、狀態重建或跨服務事件傳遞，事件歷史就需要獨立設計。

接近真實網路服務的例子包括：

- 訂單狀態每次改變都要留下 [audit log](../knowledge-cards/audit-log/)
- 付款成功事件需要被通知、出貨、分析系統各自消費
- 使用者行為事件需要進入分析 pipeline

這類資料的主要風險是順序、重複與 schema 演進。[Event log](../knowledge-cards/event-log/) 要說明事件代表哪個 domain fact、如何去重、如何處理舊版本 payload。

## 【判讀】object storage 承擔大型非結構化資料

[Object storage](../knowledge-cards/object-storage/) 的核心責任是保存大型 blob。當資料是圖片、影片、PDF、匯出報表、備份檔或模型檔案，儲存服務通常需要 object storage，而正式 metadata 放在資料庫。

接近真實網路服務的例子包括：

- 使用者上傳的大頭貼、附件與影片
- 每日報表匯出的 CSV 或 PDF
- 系統備份、稽核封存與資料匯出檔

這類資料的主要風險是存取權限、生命週期、版本與連結有效性。資料庫保存 object key、owner、狀態與 metadata；[object storage](../knowledge-cards/object-storage/) 保存實際檔案內容。

## 【檢查】進入實作前的概念邊界清單

當以下問題都能回答時，代表本章的概念層已完成，可以進入資料儲存實作章節：

1. 每一類資料的責任是否明確（正式狀態、快取、搜尋、事件、檔案）
2. 每一類資料的真實來源是否明確（source of truth 在哪裡）
3. 每一類資料是否定義一致性與延遲容忍度
4. 每一類資料是否定義保留期限與回復方式

下一步建議路由：

- [01-database](../01-database/)
- [02-cache-redis](../02-cache-redis/)

## 小結

資料儲存選型要先問資料責任。正式狀態進資料庫，可重建讀取資料進快取，搜尋體驗用 [search index](../knowledge-cards/search-index/)，歷史與重播用 [event log](../knowledge-cards/event-log/)，大型檔案用 [object storage](../knowledge-cards/object-storage/)。責任分清楚後，同一份業務資料可以出現在多個服務中，但每個服務的位置都能被解釋。
