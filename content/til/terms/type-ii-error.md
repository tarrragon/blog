---
title: "Type II error：統計學給假陰性的編號"
slug: "type-ii-error"
date: 2026-06-18
description: "Type II error 是 false negative 在假設檢定裡的稱呼：沒拒絕為假的虛無假設、漏掉真實效果。與 Type I error 成對，機率記為 β，檢定力 power = 1 − β"
tags: ["til", "術語", "跨領域", "統計", "type-ii-error"]
---

> 這個詞出現在「[你的自動判斷會犯兩種錯：誤報與漏接](../detection-errors/)」這個問題裡——它是統計學給「漏接」的編號。

Type II error（型二錯誤）是 [false negative](../false-negative/) 在統計假設檢定裡的編號：**虛無假設（H₀，預設「沒有效果 / 沒有差異」）其實為假，卻沒拒絕它**——漏掉了真實存在的效果。

它和 [Type I error](../type-i-error/)（誤報、宣稱有實無）成對：

- **Type I**：H₀ 為真卻拒絕 → false positive（誤報）。
- **Type II**：H₀ 為假卻沒拒絕 → false negative（漏接）。

## β 與檢定力

Type II error 的機率記為 **β**。與它互補的是**檢定力（statistical power）= 1 − β**，也就是「H₀ 確實為假時，正確抓到的機率」。提高檢定力（少漏接）通常靠加大樣本數或放大效果量。

把 β 對應到偵測語境，「少漏接」就是提高 [recall](../recall/)——兩者衡量的是同一件事的不同領域 framing。

## 相關概念

- 對偶錯誤：[false positive](../false-positive/) / [Type I error](../type-i-error/)。
- 同概念的偵測語境：[false negative](../false-negative/)。
- 量化的尺：[recall](../recall/)（被 false negative 拉低）。
