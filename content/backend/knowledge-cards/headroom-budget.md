---
title: "Headroom Budget"
date: 2026-05-12
description: "說明容量規劃中為應付異常 burst + AZ 故障 + forecast 誤差的安全餘量"
weight: 230
---

Headroom budget 的核心概念是「預期峰值之上、額外預留多少 capacity 應付異常」。常見 30-50%、不同工作負載比例不同。可先對照 [Peak Forecast](/backend/knowledge-cards/peak-forecast/)。

## 概念位置

Headroom 不是 over-provisioning 浪費、是容量規劃的安全邊界。三個動機：forecast 誤差（預測本身有 ±X% 誤差）、burst pattern（瞬間 spike 超過 average peak）、AZ / region failover（一個 AZ 掛、剩下兩個要承擔全部）。第四個動機是擴展的反應時間：自動擴展從決策到新容量開始服務要幾分鐘，這段時間內流量的上升量要靠事先留著的容量承接，算法見 [9.15 無預警瞬時大流量：流量來源辨識、擴展緩衝、請求優先等級、准入控制、體積型攻擊與退路](/backend/09-performance-capacity/unplanned-traffic-surge/) 的〈自動擴展（autoscaling）的反應時間與緩衝〉。Stateless service 通常 30%、DB 50%、broker 60%。可先對照 [Peak Forecast](/backend/knowledge-cards/peak-forecast/)。

## 可觀察訊號與例子

Headroom 不足的訊號是「peak 期間 utilization 接近 80%、autoscaler 還沒反應」或「single AZ 故障演練時、其他 AZ 撐不住」。對應案例：[GR8 Tech AI 預測](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) — 預測準了可以降 headroom 比例、預測不準必須拉高 headroom。

## 設計責任

Headroom 不是越大越好、會推高成本。要算 *under-provisioning 成本*（下事故的機率 × 影響）vs *over-provisioning 成本*（每月多花的錢）、找平衡點。Cost-sensitive 服務可以降 headroom 但加 reactive autoscaling；critical 服務拉高 headroom + pre-provision。每季 review headroom 比例。
