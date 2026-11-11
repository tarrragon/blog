---
title: "PACELC"
date: 2026-05-13
description: "在 CAP 之外補上正常時段的延遲與一致性取捨框架"
weight: 244
---

PACELC 的核心概念是「系統就算沒有分區，也要在延遲與一致性之間做選擇」。它讓分散式資料庫的取捨從事故時段延伸到日常時段，常用於評估 [global-oltp](/backend/knowledge-cards/global-oltp/) 的可行性。

## 跟其他概念的關係

PACELC 可讀成：若發生 partition（P），系統在 [failover](/backend/knowledge-cards/failover/)（A）與 consistency（C）之間取捨；否則（E），在 latency（L）與 consistency（C）之間取捨。它補足 CAP 只描述分區情境的盲點。

## 可觀察訊號與例子

需要 PACELC 判讀的訊號是「系統平時沒有故障，但延遲或一致性目標仍互相衝突」。例如跨區強一致交易會提高延遲；低延遲讀取通常要接受 stale risk。這個框架常用於比較 [distributed-sql](/backend/knowledge-cards/distributed-sql/) 與 key-value 設計。

## 判斷條件與後果

PACELC 能不能支持一次選型，取決於業務需求有沒有量化成三項：可接受的 stale window、p99 延遲上限、故障時可以降級到什麼程度。三項都有數字時，兩組取捨可以逐一對照：平時（E）拿 p99 上限比對跨區強一致帶來的延遲，故障時（P）拿降級策略比對放棄可用性或放棄一致性的後果。沒有數字時，「偏向一致性」「偏向低延遲」只是立場，兩個候選資料庫的比較沒有任何一方會不及格的條件，PACELC 退化成抽象口號。
