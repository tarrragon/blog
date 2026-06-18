---
title: "recall：真的之中抓到多少"
slug: "recall"
date: 2026-06-18
description: "recall（召回率、又稱敏感度 sensitivity）= TP /(TP + FN)，衡量真實存在的之中偵測器抓到多少。false negative 越多，recall 越低。與 precision 成對"
tags: ["til", "術語", "跨領域", "指標", "recall"]
---

recall（召回率，又稱敏感度 sensitivity）回答另一個問題：**真實存在的那些，偵測器抓到了多少？**

公式是 `recall = TP / (TP + FN)`：分母是「所有真的陽性」，分子是其中被抓到的。所以 [false negative](../false-negative/) 越多，recall 越低——漏接直接拉低「抓全的能力」。

## 與 precision 成對

recall 只看「漏了沒」，不管「報出來的準不準」（那是 [precision](../precision/)）。兩者通常此消彼長：把門檻調鬆、寧可多報 → recall 升、precision 降。調和兩者的單一指標是 F1 score。

## 什麼時候優先看 recall

當 [false negative](../false-negative/) 的代價高、不能漏時：疾病篩檢、詐欺偵測、安全掃描——寧可多一些誤報（犧牲 precision）再人工複查，也別放走真的。

## 連到家族

- 被它懲罰的錯誤：[false negative](../false-negative/)。
- 統計裡的對應：[Type II error](../type-ii-error/)（recall 高 ≈ 檢定力高）。
- 成對指標：[precision](../precision/)。
