---
title: "CQRS"
date: 2026-06-22
description: "說明讀寫不對稱時為何需要分離查詢與寫入責任、分離的判準與代價"
weight: 328
tags: ["backend", "architecture"]
---

CQRS（Command Query Responsibility Segregation）的核心概念是「把寫入路徑跟讀取路徑拆成各自獨立的模型，各自依自身需求最佳化」。分離後讀取面的具體產物是 [read model](/backend/knowledge-cards/read-model/)。它處理的根本問題是讀寫不對稱 — 同一份資料的寫入形狀跟讀取形狀不同、寫入頻率跟讀取頻率不同、寫入 SLA 跟讀取 SLA 不同。

## 概念位置

CQRS 是一種架構分離策略，位於資料存取模式的設計層。它跟 [read model](/backend/knowledge-cards/read-model/) 的關係是：CQRS 是分離的決策框架，read model 是分離之後「讀取面」的具體產物。

CQRS 經常跟 [event sourcing](/backend/knowledge-cards/event-sourcing/) 一起出現，但兩者是獨立概念。CQRS 只要求讀寫模型分離；[event sourcing](/backend/knowledge-cards/event-sourcing/) 是把寫入模型改成 append-only 的事件流。可以有 CQRS 但沒有 event sourcing（寫入仍用傳統 CRUD，讀取用獨立的 [read model](/backend/knowledge-cards/read-model/)），也可以有 event sourcing 但沒有 CQRS（讀寫都直接操作 event store）。

## 讀寫不對稱的三個維度

分離的動機來自三種不對稱，當任一種超過單一模型能承受的範圍時，CQRS 開始有設計價值。

**形狀不對稱**：寫入時資料以正規化、事務安全的結構進入系統；讀取時不同消費者需要不同的反正規化形狀。一個訂單寫入時是 order + line items + payment 三張表的事務；列表頁需要扁平的 order summary，報表需要跨訂單的聚合，搜尋需要全文索引。強迫同一個模型同時服務這些形狀，會讓寫入模型變得過度複雜或讀取效能退化。

**頻率不對稱**：讀取頻率遠高於寫入頻率是常見的服務模型（商品頁的瀏覽量遠大於商品更新頻率）。讀寫共用模型時，高頻讀取的效能需求會推動寫入模型往讀取最佳化靠攏，犧牲寫入的簡潔性跟一致性保證。

**SLA 不對稱**：不同讀取消費者的延遲容忍跟一致性需求不同。即時顯示需要毫秒級回應但容忍短暫不一致；報表需要完整一致但容忍分鐘級延遲；稽核需要長期可查但容忍更高延遲。單一模型難以同時滿足多種 SLA。

## 分離的設計判準

讀寫不對稱存在不代表一定需要 CQRS。分離的判準是不對稱的程度是否已經超過「在同一個模型上做最佳化」能解決的範圍。

**可以不分離的情境**：讀寫形狀接近（CRUD 應用、管理後台）、讀取消費者單一（只有一種 UI）、流量規模讓讀寫共用模型的效能足夠、團隊規模小到維護兩套模型的成本大於效能收益。

**需要考慮分離的訊號**：讀取效能持續退化但寫入側無法再為讀取最佳化（加 index 已到極限、反正規化導致寫入複雜度上升）；多種讀取消費者對同一份資料有互斥的形狀需求；讀寫的擴展需求方向不同（讀取要水平擴展、寫入要強一致性）。

## 分離的代價

CQRS 的代價集中在同步、一致性與維護三個面向。

**最終一致性**：read model 透過事件或同步機制從 write model 更新，中間有延遲。使用者寫入後立即讀取可能看不到自己的變更。這個延遲窗口需要被明確設計（多長、可接受嗎、UI 怎麼處理）而非假裝不存在。

**同步機制的可靠性**：write model 到 read model 的同步本身是一個需要監控跟治理的資料路徑。同步失敗、同步延遲、同步漂移都需要被偵測跟處理。

**多模型維護**：schema 變更需要同時更新 write model 跟所有 read model。read model 的數量增長後，每次 schema migration 的變更面會擴大。

## 跨領域的應用

讀寫分離的設計張力不限於 application data。觀測資料的讀取路徑設計（[4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)）面臨同樣的不對稱：寫入是高吞吐的 append-only，讀取被至少三種不同 SLA 的消費者（即席診斷、聚合趨勢、鑑識回溯）拉扯。觀測領域用 [recording rule](/backend/knowledge-cards/recording-rule/)、[rollup](/backend/knowledge-cards/rollup/)、[storage tiering](/backend/knowledge-cards/storage-tiering/) 來實作讀寫分離，概念上對應 CQRS 的 read model，但術語跟實作層級不同。

Message queue 的消費端也有類似結構：同一份事件被多個 consumer 以不同速度、不同形狀讀取，fan-out 跟 consumer group 是另一種讀寫分離的實作。
