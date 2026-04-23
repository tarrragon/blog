---
title: "Cold Start"
date: 2026-04-23
description: "說明服務或快取剛啟動時尚未累積狀態造成的延遲與壓力"
weight: 92
---

Cold start 的核心概念是「系統剛啟動或狀態剛清空時，尚未具備穩定運作所需的暖資料」。它可能出現在 application instance、cache、connection pool、JIT runtime、model loading 或 function runtime。

## 概念位置

Cold start 是部署、autoscaling、cache warmup 與 readiness 的共同問題。新 instance 若尚未建立連線、載入設定或暖好 cache，就接正式流量，可能造成延遲尖峰。

## 可觀察訊號與例子

系統需要處理 cold start 的訊號是擴容後新 instance 的 latency 明顯高於舊 instance。活動流量來臨時自動擴容，若新 instance 都在建立連線與載入 cache，可能無法立即承擔流量。

## 設計責任

Cold start 設計要包含 readiness、warmup、連線預建、流量緩啟與觀測。Autoscaling 設定要考慮啟動到可接流量的真實時間。
