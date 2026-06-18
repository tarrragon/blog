---
title: "Type I error：統計學給假陽性的編號"
slug: "type-i-error"
date: 2026-06-18
description: "統計假設檢定把 false positive 叫 Type I error、false negative 叫 Type II error。本篇講這兩個編號的意思、與顯著水準 α 的關係，以及一個好記的順序"
tags: ["til", "術語", "跨領域", "統計", "type-i-error"]
---

> 這個詞出現在「[你的自動判斷會犯兩種錯：誤報與漏接](../detection-errors/)」這個問題裡——它是統計學給「誤報」的編號。

統計學的假設檢定，把 [false positive](../false-positive/) 編號叫 **Type I error**、把 false negative 叫 **Type II error**。

## 兩個編號的意思

假設檢定先立一個虛無假設（H₀，預設「沒有效果 / 沒有差異」），再用資料決定要不要拒絕它：

- **Type I error（型一錯誤）**：H₀ 其實為真，卻拒絕了它——宣稱「有效果」，實際沒有。這就是 false positive。
- **Type II error（型二錯誤）**：H₀ 其實為假，卻沒拒絕——漏掉了真實存在的效果。這就是 false negative。

## 與顯著水準 α 的關係

設計檢定時會先訂一個 **顯著水準 α**（常見 0.05），它就是**容許的 Type I error 機率上限**。在樣本數固定的前提下，把 α 設得越小，越不容易誤報（Type I 降低），但相對更容易漏掉真實效果（Type II 升高）——兩者此消彼長，這是檢定設計的核心取捨。（加大樣本數則可同時壓低兩者。）

## 一個好記的順序

哪個是 Type I、哪個是 Type II 容易記混。一個記法：**Type I 是「太急著宣稱有」（過度反應、誤報），Type II 是「太保守而漏掉」**。可把編號順序記成「先有過度反應，才談漏接」——這純為助記，不是 Neyman-Pearson 當初編號的歷史定義。

## 相關概念

- 概念本身與源頭：[false positive](../false-positive/)。
- 對偶錯誤：[Type II error](../type-ii-error/)（= false negative）。
- 量化的尺：[precision](../precision/)（誤報多則 precision 低）。
- 程式領域描述同一件事的本土詞：[over-match](../over-match/)、[false trigger](../false-trigger/)、[spurious warning](../spurious-warning/) 等。
