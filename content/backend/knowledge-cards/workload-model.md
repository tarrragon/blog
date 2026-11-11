---
title: "Workload Model"
date: 2026-05-12
description: "描述 production traffic 形狀的可重播模型 — 容量規劃跟壓測的共同輸入"
weight: 226
---

Workload model 的核心概念是「把 production traffic shape 量化成可重播的模型」。沒有模型、壓測結果無意義、容量規劃靠猜；有模型之後、所有效能決策都有共同的輸入。可先對照 [Load Test](/backend/knowledge-cards/load-test/)。

## 跟其他概念的關係

Workload model 至少包含五個維度：平均吞吐、peak/avg ratio、操作 mix（read / write）、cohort 分布（geographic / device / tier）、burst pattern（時間集中度）。模型可以從 production access log + APM trace 抽出來、要定期 review 因為業務變化會讓模型過時。可先對照 [Peak Forecast](/backend/knowledge-cards/peak-forecast/)。

## 可觀察訊號與例子

模型過時的訊號是「壓測通過但 production 還是出事」。可能是 cohort 變了（VIP 用戶比例上升）、操作 mix 變了（新功能改變 read/write 比）、burst pattern 變了（新行銷活動）。對應案例：[ASOS Black Friday 24h 1.67 億](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) 峰均比 1.81x、跟 [Tixcraft 5 分鐘賣完](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的極端形狀差很多。

## 判斷條件與後果

Synthetic load、production traffic replay 與兩者混合，各自換到的貼近程度與付出的代價不同。synthetic load 的形狀完全由模型決定，強度可以調到 production 還沒出現過的程度，代價是模型漏掉的 cohort 或 burst pattern 也不會出現在壓測裡；replay 最貼近真實流量，代價是重播的請求會打到下游、消耗下游資源，而且只重現已經發生過的形狀；混合用 replay 當基底、用 synthetic 補上預期的尖峰。三種做法都要在壓測時同時對照 production metrics：兩邊誤差大時，模型已經過時，壓測通過的結論套不到 production。壓測依到達率還是依同時在線的使用者數送出請求，也是模型的一部分，選法見 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/)。
