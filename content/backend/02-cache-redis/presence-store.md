---
title: "2.5 presence store 與即時狀態"
date: 2026-04-23
description: "整理線上狀態、跨節點查詢與過期清理"
weight: 5
tags: ["backend", "cache", "presence"]
---

在線狀態儲存（presence store）的核心責任是維持短生命週期狀態的可查詢性，例如線上狀態、連線節點、最後活動時間。它屬於即時協調層，與正式帳務資料分層治理。

## 狀態模型

presence 模型通常包含 `subject`、`node`、`last_seen_at`、`ttl`。主體可能是使用者、裝置、連線或工作者。模型設計重點是查詢責任：需要查單一主體是否在線、查群組在線清單，還是查節點負載分布。

presence 資料具備高變動、短保留特性。設計時應避免把正式業務欄位混入 presence store，讓它保持可快速更新與快速過期。

## heartbeat 與 expiration

heartbeat 的責任是維持活性訊號，expiration 的責任是清理失效狀態。heartbeat 間隔太長會放大誤判離線，太短會增加寫入壓力。expiration 視窗要和網路抖動容忍度一起設計。

穩定做法是定義「可接受延遲在線」窗口，而不是追求絕對即時。presence 判讀通常是近即時近似，不是強一致保證。

## cross-node query

跨節點查詢要先明確一致性需求。聊天室在線名單可容忍短暫不一致；調度系統節點可用性則需要更保守窗口與校驗策略。查詢層應同時提供快取讀取與回源校正路徑，避免單一路徑失真。

在多區部署中，presence 常採區域內優先、跨區聚合延遲同步。這樣能降低廣域寫入成本，同時保留可接受的全域可見性。

## cleanup 策略

cleanup 的責任是避免殭屍狀態堆積。定期掃描、lazy cleanup、事件驅動清理可混合使用。清理策略要與業務容忍度對齊：社交場景可容忍秒級延遲清除，調度場景則需更快收斂。

## 判讀訊號

| 訊號                           | 判讀重點                       | 對應動作                           |
| ------------------------------ | ------------------------------ | ---------------------------------- |
| 在線數異常下降但流量未下降     | heartbeat 發送或寫入路徑中斷   | 檢查 producer 路徑、降級為回源校驗 |
| 離線判斷延遲明顯增加           | expiration 視窗過長或清理積壓  | 調整 TTL、提高 cleanup 頻率        |
| 跨節點查詢結果波動大           | 多節點寫入競態與聚合窗口不一致 | 收斂聚合邏輯、加入版本時間戳       |
| 節點重啟後出現大量殭屍在線     | 清理與重建流程未對齊           | 啟動全量重整、補啟動時同步清理     |
| 高峰時段 presence 查詢延遲拉高 | 熱 key 集中與查詢模式不匹配    | 分散 key、按群組分片、加查詢快取   |

## 常見誤區

把在線狀態儲存當正式狀態來源，會讓一致性與修復成本快速上升。presence 模型適合即時協調，最終業務判定仍由正式資料層承擔。

把 heartbeat 當固定頻率任務，也會造成高峰寫入抖動。頻率應該與線上人數與連線型態一起調整。

## 案例回寫

presence 模型可用 [2.C2 Meta：mcrouter 跨區路由](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/) 回寫。先看跨區路由如何影響在線可見性，再回到本章檢查 heartbeat 視窗、跨節點聚合與清理節奏是否一致。
這個案例主要支撐的是「跨區可見性與狀態新鮮度」判讀，不直接支撐 lock 租約或 queue 語意；若問題是互斥衝突或重播邊界，應轉到 2.4 或 3.x。

若區域內在線正常、跨區可見性延遲偏大，先調整跨區同步策略與 fallback 壽命，再把影響評估接到 [8.20 Customer Impact Assessment](/backend/08-incident-response/customer-impact-assessment/)。

## 跨模組路由

1. 與 2.3 的交接：保留與清理策略回到 [TTL 與 eviction](/backend/02-cache-redis/ttl-eviction/)。
2. 與 4.17 的交接：presence 資料品質與延遲偏差回到 [Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)。
3. 與 6.22 的交接：穩態定義與高峰演練回到 [Steady State Definition](/backend/06-reliability/steady-state-definition/)。
4. 與 8.20 的交接：即時狀態誤判造成客戶影響回到 [Customer Impact Assessment](/backend/08-incident-response/customer-impact-assessment/)。
5. 與 2.10 的交接：presence 狀態變更如何即時廣播給其他節點回到 [Pub/Sub 與即時 fan-out](/backend/02-cache-redis/pub-sub/)。

## 下一步路由

要看快取層一致性與失效策略，接著讀 [2.2 cache aside 與失效策略](/backend/02-cache-redis/cache-aside/)。要看 presence 狀態變更如何即時扇出給其他節點，接著讀 [2.10 Pub/Sub 與即時 fan-out](/backend/02-cache-redis/pub-sub/)。要看跨規模 presence 路由案例，接著讀 [2.C2 Meta：mcrouter 跨區路由](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/)。
