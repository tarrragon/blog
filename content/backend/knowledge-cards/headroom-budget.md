---
title: "Headroom Budget"
date: 2026-05-12
description: "說明容量規劃中為應付異常 burst + AZ 故障 + forecast 誤差的安全餘量"
weight: 230
---

Headroom budget 的核心概念是「預期峰值之上、額外預留多少 capacity 應付異常」。常見 30-50%、不同工作負載比例不同。可先對照 [Peak Forecast](/backend/knowledge-cards/peak-forecast/)。

## 跟其他概念的關係

Headroom 是容量規劃的安全邊界，而不是 over-provisioning 浪費。三個動機：forecast 誤差（預測本身有 ±X% 誤差）、burst pattern（瞬間 spike 超過 average peak）、AZ / region failover（一個 AZ 掛、剩下兩個要承擔全部）。第四個動機是擴展的反應時間：自動擴展從決策到新容量開始服務要幾分鐘，這段時間內流量的上升量要靠事先留著的容量承接，算法見 [9.15 無預警瞬時大流量：流量來源辨識、擴展緩衝、請求優先等級、准入控制、體積型攻擊與退路](/backend/09-performance-capacity/unplanned-traffic-surge/) 的〈自動擴展（autoscaling）的反應時間與緩衝〉。Stateless service 通常 30%、DB 50%、broker 60%。可先對照 [Peak Forecast](/backend/knowledge-cards/peak-forecast/)。Headroom 用完之後服務呈現的結果（變慢、請求失敗、無回應或程序終止）與各自的判斷標準，見 [9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)。

## 可觀察訊號與例子

Headroom 不足的訊號是「peak 期間 utilization 接近 80%、autoscaler 還沒反應」或「single AZ 故障演練時、其他 AZ 接手流量後延遲越過 SLO 或開始拒絕請求」。對應案例：[GR8 Tech AI 預測](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) — 預測準了可以降 headroom 比例、預測不準必須拉高 headroom。

## 判斷條件與後果

Headroom 比例是兩種成本的比較：under-provisioning 成本是事故的機率乘上影響，over-provisioning 成本是每月多付的資源費用，比例越高，後者越大。Cost-sensitive 的服務降低 headroom 之後，省下的費用換來較高的事故機率，不足的部分由 reactive autoscaling 補上，前提是 autoscaler 反應時間內的流量上升量仍在剩下的 headroom 之內；critical 服務的事故影響高，拉高 headroom 並 pre-provision，換到的是峰值期間不必等 autoscaler 反應。forecast 的準確度與流量的形狀會隨時間改變，比例訂下之後不再檢視時，它對應的是過去的預測誤差，所以 headroom 比例每季 review 一次。
