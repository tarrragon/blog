---
title: "precision：報出來的有多少是真的"
slug: "precision"
date: 2026-06-18
description: "precision（精確率）= TP /(TP + FP)，衡量偵測器說「有」的之中有多少是真的。false positive 越多，precision 越低。與 recall 成對、構成評估分類器的兩端"
tags: ["til", "術語", "跨領域", "指標", "precision"]
---

precision（精確率）回答一個問題：**偵測器說「有」的那些，有多少是真的？**

公式是 `precision = TP / (TP + FP)`：分母是「所有被判為陽性的」，分子是其中真的陽性。所以 [false positive](../false-positive/) 越多，precision 越低——誤報直接稀釋了「報出來的可信度」。

## 與 recall 成對

precision 只看「報出來的準不準」，不管「漏了多少」。漏接由 [recall](../recall/) 衡量。兩者構成評估分類器的兩端，且通常此消彼長：把門檻調嚴、只報最有把握的 → precision 升、recall 降。

調和兩者的單一指標是 **F1 score**（precision 與 recall 的調和平均）。

## 什麼時候優先看 precision

當 false positive 的代價高、要求「報出來就盡量別錯」時：自動封鎖、自動下架、垃圾郵件丟棄——寧可漏一些（犧牲 recall），也別誤殺。

## 連到家族

- 被它懲罰的錯誤：[false positive](../false-positive/)。
- 統計裡的對應：[Type I error](../type-i-error/)（誤報多則 precision 低）。
- 成對指標：[recall](../recall/)。
