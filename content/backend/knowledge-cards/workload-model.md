---
title: "Workload Model"
date: 2026-05-12
description: "描述 production traffic 形狀的可重播模型 — 容量規劃跟壓測的共同輸入"
weight: 225
---

Workload model 的核心概念是「把 production traffic shape 量化成可重播的模型」。沒有模型、壓測結果無意義、容量規劃靠猜；有模型之後、所有效能決策都有共同的輸入。可先對照 [Load Test](/backend/knowledge-cards/load-test/)。

## 概念位置

Workload model 至少包含五個維度：平均吞吐、peak/avg ratio、操作 mix（read / write）、cohort 分布（geographic / device / tier）、burst pattern（時間集中度）。模型可以從 production access log + APM trace 抽出來、要定期 review 因為業務變化會讓模型過時。可先對照 [Peak Forecast](/backend/knowledge-cards/peak-forecast/)。

## 可觀察訊號與例子

模型過時的訊號是「壓測通過但 production 還是出事」。可能是 cohort 變了（VIP 用戶比例上升）、操作 mix 變了（新功能改變 read/write 比）、burst pattern 變了（新行銷活動）。對應案例：[ASOS Black Friday 24h 1.67 億](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) 峰均比 1.81x、跟 [Tixcraft 5 分鐘賣完](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的極端形狀差很多。

## 設計責任

設計時要決定「synthetic load」vs「production traffic replay」vs「混合」。synthetic 好控制但容易脫離 reality；replay 最貼真實但消耗下游資源；混合是常見折衷。模型必須驗證：壓測 *同時* 對比 production metrics、看誤差有多大。
