---
title: "怎麼量一個偵測器準不準"
slug: "measuring-detectors"
date: 2026-06-18
description: "當你想說「這個偵測器有多好」，光講準確率不夠。誤報與漏接要分開量，於是有了 precision 和 recall 兩把尺。這是它們的入口"
tags: ["til", "術語", "跨領域", "議題hub"]
---

當你想評估「這個偵測器到底好不好」，會發現只說一個「準確率」不夠——因為[誤報與漏接](../detection-errors/)是兩種不同的錯，要用兩把尺分開量。

## 兩把尺

- **[precision](../precision/)（精確率）**：報出來的之中，有多少是真的？被[誤報](../false-positive/)拉低。
- **[recall](../recall/)（召回率）**：真的之中，抓到了多少？被[漏接](../false-negative/)拉低。

## 單看一把會被騙

因為只看一把會被騙。一個偵測器只要「只報最有把握的那一個」，precision 就逼近滿分——但 recall 極低，幾乎全漏了。反過來「全部都報」recall 滿分、precision 慘不忍睹。兩把一起看，才知道它是真準還是在作弊。

兩者通常此消彼長，調和成單一數字是 F1 score。要偏哪一把，回到[誤報與漏接哪個更貴](../detection-errors/)的判斷。

## 從這裡往下讀

- [precision](../precision/)：報出來的有多少是真的。
- [recall](../recall/)：真的之中抓到多少。
