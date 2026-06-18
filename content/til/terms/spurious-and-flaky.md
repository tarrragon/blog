---
title: "spurious、flaky、noise：計算領域怎麼描述假陽性"
slug: "spurious-and-flaky"
date: 2026-06-18
description: "在計算領域 false positive 是本土第一線詞，但描述偵測器誤觸還有更精準的同義詞：spurious / over-match（過寬匹配）、flaky（間歇假失敗）、noise（誤報噪音）。本篇整理它們各自貼合的情境"
tags: ["til", "術語", "跨領域", "計算", "spurious", "flaky"]
---

計算領域不必向別的領域借「假陽性」這個詞——[false positive](../false-positive/) 在這裡就是本土第一線詞，遍布 linter、靜態分析、資安掃描、垃圾郵件過濾、入侵偵測、監控告警。

不過依**情境**，計算領域有更精準的本土同義詞，各自貼合不同的誤報樣態。

## 依情境的精準詞

- **spurious / spurious trigger**：偵測器命中了不該命中的東西。常見於規則或樣式比對過寬，例如 regex **over-match**（過寬匹配），或一個守衛（guard）對「只是引用觸發詞的文字」誤觸。
- **flaky**：測試「該綠卻間歇紅」的假失敗——同一份程式碼、同一個測試，有時過有時不過。flaky 特指這種不穩定、非確定性的 false positive。
- **noise**：誤報多到淹沒真訊號。誤報累積會造成 **alert fatigue（告警疲勞）**，讓人對告警麻木而漏看真正重要的。
- **precision（精確率）**：衡量角度的詞。false positive 越多，precision 越低；它和 recall（召回率，與 false negative 相關）構成評估分類器的兩端。

## 一個剛遇到的實例

一個 PreToolUse 守衛用關鍵字比對偵測「跳過審查」的意圖，結果對一則只是**引用**「跳過審查」字樣的訊息也觸發了——命中了字面、但沒有真正的意圖。

精確描述這個狀況：它是 **lexical false positive**（字面層的假陽性），或說 **spurious trigger / over-match**。修法是讓守衛在「明確是引用或討論」時抑制，但方向要保守——寧可偶爾誤觸，也不能漏放真正的意圖（那會變成更危險的 false negative）。

## 連到其他領域

- 概念本身與源頭：[false positive](../false-positive/)。
- 統計學給同一件事的編號：[Type I error](../type-i-error/)。
