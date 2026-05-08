---
title: "1.2 schema design 與資料建模"
date: 2026-04-23
description: "整理 table、index、key 與命名規則"
weight: 2
tags: ["backend", "database", "schema"]
---

資料綱要設計（schema design）的核心責任是把業務狀態轉成可維護、可查詢、可演進的資料結構。資料建模做得好，交易邊界、查詢效率、migration 成本與事故修復路徑都會更穩定。

## 先定義狀態責任

資料模型第一步是定義狀態責任：哪些欄位代表正式狀態、哪些欄位是派生值、哪些欄位只為追蹤與審計。這個分層會直接決定 table 邊界與 relation 方向。

在訂單服務中，訂單主檔、付款狀態、庫存扣減屬於正式狀態；展示排序欄位、快取摘要屬於派生值；版本號、更新時間與來源欄位屬於可追蹤證據。把三類混在同一模型裡，後續查詢與演進成本會持續上升。

## table 與 relation

table 切分要對齊業務聚合邊界。聚合內需要交易一致性的欄位，放在同一交易可控範圍；跨聚合流程透過事件或引用關係接續。relation 的責任是表達資料約束，不是替代流程編排。

主鍵策略要先回答「如何穩定識別」與「如何支援查詢」。自然鍵可讀性高但變動風險高；代理鍵穩定且易擴展，常搭配業務唯一鍵一起使用。外鍵策略則要平衡完整性與演進自由度：正式核心域可強約束，跨域整合可由應用層保護並保留遷移彈性。

## index 與查詢模型

index 設計要從查詢路徑反推，而不是從欄位列表前推。每個高頻查詢至少要回答三件事：過濾條件是什麼、排序規則是什麼、回傳範圍有多大。這三件事能否由索引覆蓋，決定了 latency 與成本。

常見設計原則：

1. 先保護交易關鍵查詢，再處理報表與後台查詢。
2. 複合索引依查詢過濾與排序順序排列，避免僅憑欄位熱門度排列。
3. 大表變更前先評估索引建立成本與回退方案，避免在高峰時段同步放大風險。

## naming 與演進一致性

命名規則的責任是維持跨版本可讀性。table、column、index 的命名若沒有一致語意，migration 與故障排查會持續變慢。穩定做法是把命名和業務語意對齊，並保留可辨識版本與作用域。

schema 演進時，命名與結構要一起考慮。欄位重命名、拆欄位、合併欄位都應配合 [Expand / Contract](/backend/knowledge-cards/expand-contract/) 與 [schema migration](/backend/knowledge-cards/schema-migration/) 策略，讓新舊版本在過渡期可共存。

## 判讀訊號

| 訊號                               | 判讀重點                       | 對應動作                           |
| ---------------------------------- | ------------------------------ | ---------------------------------- |
| 同一查詢在資料量成長後延遲快速上升 | 索引與查詢模型不對齊           | 補複合索引、重寫查詢條件           |
| migration 後查詢計畫顯著變化       | 統計資訊或索引選擇偏移         | 重建統計、校正索引與查詢           |
| 交易流程需跨多表同步更新           | table 邊界與業務聚合邊界不一致 | 重切聚合邊界、減少跨聚合同步更新   |
| 同義欄位在多表重複存在且語意漂移   | 命名與責任邊界失控             | 收斂欄位責任、補資料字典與遷移計畫 |
| 修復事故時需要多次手動比對資料     | 可追蹤欄位與關聯鍵不足         | 補追蹤欄位、設計對帳查詢與修復流程 |

## 常見誤區

把 schema 設計等同於「先能寫入就好」，會把結構債延後到流量成長與事故時一次爆發。資料模型的工程價值在於可演進性，不在於初版欄位數量最少。

把索引當成效能補丁，忽略查詢模型與資料責任，也會讓後續維護成本持續疊加。索引與查詢要一起設計，才能在演進中保持穩定。

## 案例回寫

資料建模議題可以用 [GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/) 做回寫練習。讀這個事件時，先看跨區拓樸切換如何影響資料一致性，再回到本章檢查三件事：聚合邊界是否清晰、交易查詢與對帳查詢是否分層、修復時是否有可追蹤欄位與對帳鍵。
這個案例主要支撐的是「查詢與資料模型邊界」判讀，不直接支撐 transaction retry 或 queue replay 調校；若問題是重試放大，應轉到 1.3 或 3.x 章節處理。

當事件呈現長時間人工比對或查詢語意漂移時，先修正本章的 query boundary 與 naming 一致性，再補 [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/) 的驗證與回退路徑。

## 跨模組路由

schema 設計會直接影響後續可靠性與事故處理。

1. 與 1.3 的交接：交易一致性邊界落在 [transaction boundary](/backend/01-database/transaction-boundary/)。
2. 與 1.6 的交接：演進策略落在 [資料庫轉換實作](/backend/01-database/database-migration-playbook/)。
3. 與 4.20 的交接：查詢與資料驗證證據進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
4. 與 6.11 的交接：高風險 schema 變更進入 [Migration Safety](/backend/06-reliability/migration-safety/)。
5. 與 8.19 的交接：資料修復與回退決策記錄進入 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

要把建模與交易一起看，接著讀 [1.3 transaction 與一致性邊界](/backend/01-database/transaction-boundary/)。要把建模放進變更流程，接著讀 [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/)。
