---
title: "false negative：假陰性是 false positive 的另一半"
slug: "false-negative"
date: 2026-06-18
description: "false negative（假陰性）是偵測器漏掉真實存在的東西——說「沒有」，真實卻是「有」。它和 false positive 同屬混淆矩陣的兩個錯誤格，統計叫 Type II error、訊號偵測叫 miss。本篇講概念、各領域稱呼，與兩者的取捨"
tags: ["til", "術語", "跨領域", "false-negative"]
---

false negative（假陰性）指**偵測器漏掉了真實存在的東西**——說「沒有」，真實卻是「有」。它是 [false positive](../false-positive/) 的另一半：兩者同屬[混淆矩陣](../false-positive/)四格裡的兩個錯誤格。

- **false positive（誤報）**：說有、實無。
- **false negative（漏接）**：說無、實有。

## 各領域怎麼稱呼

和 false positive 一樣，false negative 換領域有不同叫法：

- **統計**：[Type II error](../type-ii-error/)（沒拒絕為假的虛無假設，漏掉真實效果）。
- **訊號偵測理論**：miss（漏失），對應雷達「該偵測到敵機卻沒報」。
- **醫學**：偽陰性（有病卻驗成陰性）。

## 和 false positive 的取捨

FP 與 FN 通常此消彼長：把偵測門檻調鬆、少漏接（FN 降），就容易多誤報（FP 升）；調嚴反之。要犧牲哪一個，取決於**哪種錯誤代價更高**：

- 癌症篩檢怕**漏接**（FN 致命），寧可多一些 FP 再複檢。
- 自動封鎖、垃圾郵件怕**誤殺**（FP 擾民），寧可放過一些再人工補。

這個取捨在統計裡就是 α 與 [Type II error](../type-ii-error/) 的拉扯（見 [Type I error](../type-i-error/)），量化的尺則是 [precision](../precision/) 與 [recall](../recall/)——false negative 拉低的是 recall。
