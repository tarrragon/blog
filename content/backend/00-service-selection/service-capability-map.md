---
title: "0.1 後端服務能力地圖"
date: 2026-04-23
description: "用需求類型判斷應先評估資料庫、快取、訊息佇列、觀測平台或部署平台"
weight: 1
---

後端服務能力地圖的核心原則是先辨識需求類型，再選擇服務分類。資料庫、快取、訊息佇列、觀測平台與部署平台都屬於後端能力，但它們分別回答「狀態放哪裡」、「讀取怎麼變快」、「工作怎麼跨 process」、「系統怎麼診斷」、「服務怎麼交付」。

## 本章目標

學完本章後，你將能夠：

1. 用需求類型辨識後端服務分類
2. 區分資料儲存、快取、訊息傳遞、觀測與部署平台
3. 判斷一個問題應先進入哪個 backend 模組
4. 避免把所有外部技術都混成同一種「基礎設施」

---

## 【觀察】需求會先表現成系統症狀

後端服務選型通常從症狀開始。產品需求或事故描述裡會出現一些可觀察訊號：

| 需求訊號                               | 代表的工程問題       | 優先評估方向 |
| -------------------------------------- | -------------------- | ------------ |
| 資料需要長期保存、查詢、交易一致性     | 狀態真相與持久化     | 資料庫       |
| 熱門資料讀取太頻繁、下游被打爆         | 讀取壓力與暫存       | 快取 / Redis |
| request 內完成工作太慢、需要重試或排隊 | 非同步處理與可靠傳遞 | 訊息佇列     |
| 出事時找不到原因、跨服務路徑不清楚     | 診斷與操作訊號       | 可觀測性平台 |
| 部署、擴容、流量入口與健康檢查不穩     | 服務交付與平台合約   | 部署平台     |

這張表是索引。真正的選型要看每個訊號背後的資料生命週期、流量形狀與操作需求。

## 【判讀】資料長期存在通常先看資料庫

資料庫解決的是「系統承認哪份資料是正式狀態」。如果資料需要長期保存、支援查詢、維持交易一致性、被多個 request 共同讀寫，選型應先進入資料庫與持久化模組。

接近真實網路服務的例子包括：

- 電商訂單需要保存付款狀態、出貨狀態與退款紀錄
- 會員系統需要保存帳號、權限、登入方式與審計資料
- [SaaS](../../knowledge-cards/tenant-boundary/) 產品需要保存 workspace、plan、billing 與使用量

這類問題的核心是 [source of truth](../../knowledge-cards/source-of-truth/)。快取可以加速讀取，[queue](../../knowledge-cards/queue/) 可以延後處理，[log](../../knowledge-cards/log/) 可以協助診斷，但正式狀態仍需要清楚的資料模型與一致性邊界。

下一步可讀：[資料庫與持久化](../../01-database/)。

## 【判讀】讀取壓力集中通常先看快取

快取解決的是「同一類資料被重複讀取時，如何降低正式資料來源壓力」。如果資料本身已經有 [source of truth](../../knowledge-cards/source-of-truth/)，但熱門資料導致資料庫或下游 API 壓力過高，選型應先進入快取與 Redis 模組。

接近真實網路服務的例子包括：

- 商品詳情頁被大量瀏覽，但商品資料變更頻率低
- 使用者權限或 [Feature Flag](../../knowledge-cards/feature-flag/) 每個 request 都要查
- 即時服務需要快速查詢 client presence 或 [topic](../../knowledge-cards/topic/) 訂閱狀態

這類問題的核心是讀取路徑與失效策略。快取要回答資料何時過期、何時更新、下游失敗時如何回應、cache [miss](../../knowledge-cards/cache-hit-miss/) 尖峰如何保護系統。

下一步可讀：[快取與 Redis](../../02-cache-redis/)。

## 【判讀】工作跨出 request 通常先看訊息傳遞

訊息佇列解決的是「工作離開目前 process 或 request 後，如何可靠地被處理」。如果一個 request 需要觸發後續工作、等待外部系統、重試、批次處理或跨服務通知，選型應先進入訊息佇列與事件傳遞模組。

接近真實網路服務的例子包括：

- 付款成功後要寄信、更新 CRM、發送推播與建立出貨任務
- 使用者上傳影片後要轉檔、產生縮圖與通知完成
- IoT 裝置上報資料後要清洗、聚合與觸發告警

這類問題的核心是 [delivery semantics](../../knowledge-cards/delivery-semantics/)。系統要決定是否需要持久化、是否允許重複投遞、失敗是否重試、[consumer](../../knowledge-cards/consumer/) 如何水平擴展。

下一步可讀：[訊息佇列與事件傳遞](../../03-message-queue/)。

## 【判讀】看不見系統行為通常先看觀測平台

可觀測性平台解決的是「服務發生什麼、為什麼發生、影響範圍多大」。如果事故發生後只能看單機 log，無法串起 request、事件、下游依賴與容量趨勢，選型應先進入可觀測性模組。

接近真實網路服務的例子包括：

- API 偶爾變慢，但無法判斷是資料庫、外部 API 還是部署節點問題
- queue lag 上升，但不知道 [producer](../../knowledge-cards/producer/) 變快還是 consumer 變慢
- [WebSocket](../../knowledge-cards/websocket/) client 斷線增加，但缺少連線生命週期與地區資訊

這類問題的核心是操作訊號。log、metric、[trace](../../knowledge-cards/trace/)、[dashboard](../../knowledge-cards/dashboard/) 與 [alert](../../knowledge-cards/alert/) 需要共用欄位與關聯方式，才能讓工程師從症狀回到原因。

下一步可讀：[可觀測性平台](../../04-observability/)。

## 【判讀】服務交付不穩通常先看部署平台

部署平台解決的是「服務如何被啟動、更新、擴容、接流量與停止」。如果問題集中在 [rolling update](../../knowledge-cards/rolling-update/)、[liveness](../../knowledge-cards/health-check-liveness/)、[load balancer](../../knowledge-cards/load-balancer/)、[service registry](../../knowledge-cards/service-registry/)、[service discovery](../../knowledge-cards/service-discovery/)、container image 或資源限制，選型應先進入部署平台與網路入口模組。

接近真實網路服務的例子包括：

- 發版時部分 request 失敗，舊 pod 和新 pod 切換不穩
- 服務需要水平擴展，但 client 不知道該連到哪個 instance
- shutdown 時仍有背景工作或長連線尚未清理

這類問題的核心是平台合約。程式要提供 health、[readiness](../../knowledge-cards/readiness/)、shutdown 與資源使用訊號；平台要提供流量入口、排程、發版與回滾能力。

下一步可讀：[部署平台與網路入口](../../05-deployment-platform/)。

## 小結

後端服務選型先從需求類型開始。資料長期存在先看資料庫，讀取壓力集中先看快取，工作跨出 request 先看訊息傳遞，系統行為缺少可見性先看觀測平台，服務交付不穩先看部署平台。分類清楚後，後續產品選型與實作細節才會有正確位置。
