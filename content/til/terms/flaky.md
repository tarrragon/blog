---
title: "flaky：時綠時紅的測試"
slug: "flaky"
date: 2026-06-18
description: "flaky test 指同一份程式碼、同一個測試，不改任何東西卻時過時不過。它是測試的 false positive（該綠卻紅）裡特指「間歇、非確定性」的那種"
tags: ["til", "術語", "跨領域", "測試", "flaky"]
---

> 這個詞出現在「[測試紅燈不一定是真的壞](../unreliable-tests/)」這個問題裡。

flaky test（不穩定測試）指**同一份程式碼、同一個測試，什麼都沒改，卻有時過有時不過**。

它是測試領域的 [false positive](../false-positive/)——測試報紅、但被測的程式碼其實沒問題——而 flaky 特指其中「**間歇、非確定性**」的那種。

## 常見成因

- 競態（race condition）、依賴執行順序。
- 時間依賴：sleep、timeout、時鐘、時區。
- 共用狀態沒清乾淨：測試之間互相污染。
- 外部依賴：網路、第三方服務的暫態抖動。

## 為何危險

flaky 會侵蝕對測試套件的信任：紅了第一反應是點重跑而不是查 bug，久了連真的失敗也被當 flaky 忽略——這是測試版的 [alert fatigue](../alert-fatigue/)。

## 與 spurious failure 的區別

flaky 強調「**間歇重現**」（重跑可能就過）；[spurious failure](../spurious-failure/) 強調「這次失敗的原因不是被測對象」，不一定間歇。兩者都是測試的 false positive，角度不同。

## 相關概念

- 上位概念：[false positive](../false-positive/)。
- 近鄰：[spurious failure](../spurious-failure/)、後果 [alert fatigue](../alert-fatigue/)。
