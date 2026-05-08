---
title: "2.2 cache aside 與失效策略"
date: 2026-04-23
description: "整理 read-through 思路、cache miss 與 invalidation"
weight: 2
tags: ["backend", "cache", "redis"]
---

旁路快取（cache aside）的核心責任是把讀取加速與正式狀態分離。資料庫維持 [source of truth](/backend/knowledge-cards/source-of-truth/)，快取維持可重建副本；兩者透過失效策略與新鮮度窗口對齊。

## 基本流程

[cache aside](/backend/knowledge-cards/cache-aside/) 的讀路徑是「先讀 cache，miss 後回源，再回填 cache」；寫路徑是「先寫 source of truth，再做 cache invalidation 或版本更新」。這個流程讓正式狀態維持單一責任，同時讓熱門讀取獲得低延遲。

實務上要先定義 freshness window。每個資料類型可容忍的不新鮮時間不同：商品介紹可接受秒級延遲，價格、庫存、權限與配額則需要更短窗口或即時失效。

## 失效策略

失效策略的責任是控制 cache 和 source of truth 之間的偏差。常見做法有三類：

1. 事件驅動失效：寫入成功後推事件刪 key 或更新版本，適合正確性要求高的資料。
2. TTL 失效：以時間上限控制資料壽命，適合可短暫不新鮮的資料。
3. 混合策略：事件失效為主、TTL 為保底，適合多來源寫入或跨區快取。

[stale data](/backend/knowledge-cards/stale-data/) 不是例外事件，而是快取系統的常態成本。設計時要先定義可接受的 stale 形式，再設計對應補償與回退路徑。

## 判讀訊號與回源保護

cache 命中下降時，來源系統會承受瞬間回源壓力。回源保護需要和失效策略一起設計：

| 風險訊號                             | 判讀重點                        | 對應動作                                                                        |
| ------------------------------------ | ------------------------------- | ------------------------------------------------------------------------------- |
| hit ratio 下降且 origin QPS 快速上升 | 大量 key 同時過期或失效策略失準 | 分散 TTL、分批失效、啟用 [cache warmup](/backend/knowledge-cards/cache-warmup/) |
| 熱門 key miss 後延遲與錯誤率同步上升 | 單 key 造成 stampede            | 啟用 request coalescing、局部預熱、限流回源                                     |
| cache 層延遲穩定但業務錯誤增加       | 值語意過期或序列化版本漂移      | 補 key version 與 schema migration                                              |
| eviction rate 升高且 value size 變大 | 容量策略與資料形狀不匹配        | 重配記憶體策略、調整 value 拆分                                                 |

[cache stampede](/backend/knowledge-cards/cache-stampede/) 與 [thundering herd](/backend/knowledge-cards/thundering-herd/) 都是回源保護議題；重點是把來源系統視為有限資源，讓 miss 風險可控。

## 服務情境

商品詳情頁是典型 cache aside 場景。頁面讀取需要組合商品主檔、價格、庫存與行銷標籤。主檔可用較長 TTL 與背景更新，價格與庫存則用事件失效與較短 TTL，讓讀取延遲與正確性維持平衡。

當促銷開始時，大量熱門商品同時被讀取。這時 cache 策略的重點從命中率轉到來源保護與新鮮度控制：是否能限制回源尖峰、是否能快速修正錯誤資料、是否能在事故時降級。

## 常見誤區

把命中率當作唯一目標，會忽略資料語意與失敗代價。命中率高不代表結果正確，尤其在價格、權限、配額類資料。

把 cache 當成正式資料來源，會讓資料修復與稽核變複雜。快取系統適合承擔讀取加速，不適合承擔正式狀態的最終判定。

## 案例回寫

cache aside 的失效風險可用 [2.C9 反例](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/) 做回寫。先看事件中的失效節奏：是大批 key 同時過期、失效順序錯置，還是熱點 key 回源放大，再對照本章的 freshness window、回源保護與容量策略。
這個案例主要支撐的是「失效節奏與回源壓力」判讀，不直接支撐分散式鎖租約或 queue replay；若是互斥控制或重播問題，應轉到 2.4 或 3.x。

命中率看似正常但業務錯誤上升時，先回到本章檢查值語意與 key 版本化，再把量測缺口接到 [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)。

## 跨模組路由

cache aside 的設計會直接影響觀測、驗證與事故處理。

1. 與 01 的交接：source of truth 與查詢壓力回到 [1.1 高併發讀寫邊界](/backend/01-database/high-concurrency-access/)。
2. 與 04 的交接：hit ratio、origin QPS、stale read 與 eviction 進入 [Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)。
3. 與 06 的交接：回源保護與壓測邊界進入 [Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)。
4. 與 08 的交接：失效策略誤配與 stampede 事故回寫 [Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)。

## 下一步路由

要進一步處理 TTL、容量與淘汰策略，接著讀 [2.3 TTL 與 eviction](/backend/02-cache-redis/ttl-eviction/)。要看快取策略在真實事件中的失敗與修復，接著讀 [2.C9 反例](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)。
