---
title: "Cold Start"
date: 2026-04-23
description: "說明服務或快取剛啟動時尚未累積狀態造成的延遲與壓力"
weight: 93
---

Cold start 的核心概念是「系統剛啟動或狀態剛清空時，尚未具備穩定運作所需的暖資料」。它可能出現在 application instance、cache、connection pool、JIT runtime、model loading 或 function runtime。 可先對照 [Competing Consumers](/backend/knowledge-cards/competing-consumers/)。

## 跟其他概念的關係

Cold start 是部署、autoscaling、cache warmup 與 readiness 的共同問題。新 instance 若尚未建立連線、載入設定或暖好 cache，就接正式流量，可能造成延遲尖峰。 可先對照 [Competing Consumers](/backend/knowledge-cards/competing-consumers/)。

## 可觀察訊號與例子

系統需要處理 cold start 的訊號是擴容後新 instance 的 latency 明顯高於舊 instance。活動流量來臨時自動擴容，若新 instance 都在建立連線與載入 cache，可能無法立即承擔流量。

## 判斷條件與後果

新 instance 從啟動到能以正常延遲處理流量之間有一段時間，cold start 的各項設計處理的都是這段時間。readiness 只看程序是否啟動時，instance 在連線還沒建好、cache 還是空的時候就收到正式流量，使用者遇到延遲尖峰；warmup 與連線預建把這些工作移到接流量之前完成，流量緩啟讓新 instance 先接少量請求，受延遲尖峰影響的只有那些少量請求。新舊 instance 的延遲沒有分開觀測時，看不出延遲尖峰來自 cold start。Autoscaling 的觸發時機只算到 instance 啟動、沒算到可接流量的真實時間時，擴容在尖峰到達時還沒生效，這段時間的流量全部由舊 instance 處理。
