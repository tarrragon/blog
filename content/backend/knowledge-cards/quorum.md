---
title: "Quorum"
date: 2026-05-13
description: "分散式系統以多數節點同意作為提交或讀取有效性的門檻"
weight: 250
---

Quorum 的核心概念是「操作要被接受，必須取得最小同意門檻」。它的責任是把一致性從單節點保證轉成多節點共識機制，常用於 [linearizability](/backend/knowledge-cards/linearizability/) 與 [global-oltp](/backend/knowledge-cards/global-oltp/)。

## 概念位置

在多區域系統裡，quorum 直接決定兩個結果：提交延遲下限與故障時可用範圍。節點距離越遠、同意門檻越高，延遲通常越高；但容錯能力也會提升。這層取捨通常要和 [latency-budget](/backend/knowledge-cards/latency-budget/) 一起評估。

## 可觀察訊號與例子

需要 quorum 判讀的訊號是「跨區資料正確性要求高，但延遲目標仍按單區設定」。例如要求全球強一致卻同時要求跨洲 p99 低於 50ms，通常與 quorum 物理成本衝突。

## 設計責任

設計 quorum 時要明確寫下節點分布、門檻策略與區域失效劇本。這些條件若只存在於腦中，事件期間很容易出現錯誤切換或過度擴散的回退操作。
