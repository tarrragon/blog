---
title: "over-match：規則比對過寬而誤命中"
slug: "over-match"
date: 2026-06-18
description: "over-match（又稱 over-broad match、spurious match）指規則或樣式寫得太寬，命中了不該命中的目標。它是許多 false positive 的機制層成因，常見於 regex 與 glob"
tags: ["til", "術語", "跨領域", "over-match"]
---

> 這個詞出現在「[守衛和規則為什麼會誤觸](../guard-misfires/)」這個問題裡——它是機制成因。

over-match（過寬匹配，又稱 over-broad match、spurious match）指**規則或樣式寫得太寬，命中了不該命中的目標**。

如果說 [false positive](../false-positive/) 是「偵測器誤報」這個現象，over-match 就是它在規則比對層常見的**機制成因**：不是偵測器壞了，是規則的涵蓋範圍超出了意圖。

## 常見場景

- regex 少了邊界或錨點：`cat` 命中 `category`、`scatter`。
- glob 太寬：`*.test.*` 連不想要的也掃進來。
- 關鍵字比對沒看上下文：命中了字面、卻不管語境。

## 怎麼收斂

把規則收窄到「恰好涵蓋意圖」：加邊界（`\b`）、加錨點、加上下文條件。收窄要拿捏——太寬會 over-match（false positive），太窄會漏掉真的（false negative）。這個拉扯就是 [precision](../precision/) 與 [recall](../recall/) 的取捨。

## 相關概念

- 它造成的現象：[false positive](../false-positive/)、[spurious warning](../spurious-warning/)。
- 結果視角：當守衛因 over-match 被觸發，就是 [false trigger](../false-trigger/)。
