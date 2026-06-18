---
title: "守衛和規則為什麼會誤觸"
slug: "guard-misfires"
date: 2026-06-18
description: "一個守衛、linter 或規則明明邏輯沒錯，卻命中了不該命中的東西。多半是規則寫太寬。描述這種誤觸的詞各有切面，這是它們的入口"
tags: ["til", "術語", "跨領域", "議題hub"]
---

你寫了一個守衛或規則（hook、linter、regex），它邏輯看起來沒錯，卻**命中了不該命中的東西**——這是規則層的[誤報](../false-positive/)。多半的根因是同一個：規則寫得比意圖寬。

## 因、果、與一個切面

- **機制（因）**：規則涵蓋範圍超出意圖，叫 **[over-match](../over-match/)**（過寬匹配）。
- **結果（果）**：守衛因此被形似但非真意圖的輸入觸發，叫 **[false trigger](../false-trigger/)**（誤觸）。
- **linter 切面**：靜態分析報的偽警告，叫 **[spurious warning](../spurious-warning/)**。

## 怎麼想這件事

誤觸不是「偵測器壞了」，是規則的範圍沒收好。收窄規則時要拿捏：太寬會誤觸（[誤報](../false-positive/)），太窄會漏掉真的（[漏接](../false-negative/)）。這個拉扯就是[怎麼量偵測器](../measuring-detectors/)裡 precision 與 recall 的取捨。

## 從這裡往下讀

- [over-match](../over-match/)：規則過寬而誤命中。
- [false trigger](../false-trigger/)：守衛被誤觸。
- [spurious warning](../spurious-warning/)：linter 的偽警告。
