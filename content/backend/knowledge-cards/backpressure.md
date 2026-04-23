---
title: "Backpressure"
date: 2026-04-23
description: "說明下游處理速度不足時系統如何讓上游依下游能力送出工作"
weight: 27
---

Backpressure 的核心概念是「下游處理能力不足時，讓上游感知並放慢」。它把上游從「盲目送出」轉為「依下游能力送出」，讓系統在壓力下排隊、拒絕、降級或削峰，以保護下游資源並維持整體可預測性。Backpressure 的本質是「壓力從下游往上游傳遞」的訊號通道，覆蓋範圍比單純的拒絕策略更廣。

## 概念位置

Backpressure 出現在 [in-process channel](../in-process-channel/)、[queue](../queue/)、[worker pool](../worker-pool/)、[HTTP client](../http-client/)、[connection pool](../connection-pool/)、[broker](../broker/) 的 [consumer](../consumer/) 與 [stream pipeline](../stream-pipeline/)。它處理的是速度不匹配：進入速度高於處理速度。

Backpressure 與 [rate limit](../rate-limit/) 的差別在於資訊流向：rate limit 由上游主動設閘門（「每秒最多 N 個」），屬於容量規劃；backpressure 由下游回饋壓力（「我現在只能吃 M 個」），屬於動態調速。兩者常搭配使用：rate limit 處理已知的規劃容量，backpressure 處理無法預先預測的即時變化。

## 可觀察訊號

需要 backpressure 的訊號包含 [queue depth](../queue-depth/) 上升、記憶體持續增加、[timeout](../timeout/) 比例擴大、[consumer lag](../consumer-lag/) 加深、下游 error rate 上升。當這些指標同時出現而上游流量維持穩定時，代表處理鏈某一段已成為瓶頸，壓力需要向上傳遞，而不是繼續往 buffer 堆積。

## 接近真實網路服務的例子

通知服務在行銷活動期間收到大量派送任務。若任務直接交給 worker 處理，worker 很快會塞滿下游第三方 API 的連線配額，latency 暴增、重試加倍，最終把佇列塞爆。導入 backpressure 後，服務依下游 API 實際吞吐動態調整 worker 取件速度：API 回應變慢時 worker 取件速度自動下降，上游請求端收到「任務已接收但延後送達」的回覆。整條 pipeline 的處理速度由最慢的一段決定，系統保留在可預測、可恢復的狀態。

## 設計責任

Backpressure 導入後，團隊需要定義以下邊界：[buffer](../buffer/) 大小、排隊上限、等待期限、拒絕策略、[retry policy](../retry-policy/)、[load shedding](../load-shedding/) 與對使用者的回饋（429 / 503 / 延後通知）。觀測上應能看到 [queue depth](../queue-depth/)、in-flight 數量、處理耗時、drop count、[timeout](../timeout/)、下游 error rate，並把關鍵指標放進 [dashboard](../dashboard/)。

設計取捨的核心是 buffer 尺度：buffer 太小會讓瞬間尖峰被過度拒絕，流失可接受的請求；buffer 太大則延遲失控並可能拖累記憶體。穩定做法是「有限 buffer + 明確拒絕策略」，讓系統在超載時 fail fast，避免把壓力延後累積成更大的雪崩。

<!--
codex-check:
  C1-intent: pass
  C2-atomic: pass (聚焦 backpressure 本身，相鄰概念皆以連結引用)
  C3-business-first: pass (定義段落說明要解決的問題)
  C4-reasoning-path: pass (概念位置 → 訊號 → 例子 → 設計責任)
  C5-searchable: pass (關鍵詞 backpressure / buffer / queue depth 皆 grep 友善)
  C6-positive-framing: pass (「避免」僅用於安全警示語境，屬 §4.3 例外)
  C7-source-verified: pass
  reviewed-at: 2026-04-23
  role: reference-sample (brief §3.1 指定正面範例卡片)
-->
