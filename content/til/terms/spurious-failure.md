---
title: "spurious failure：偽失敗"
slug: "spurious-failure"
date: 2026-06-18
description: "spurious failure 指測試或建置失敗了，但失敗的原因不是被測對象本身（環境、網路、暫態），屬測試的 false positive。與 flaky 的差別在強調「這次的因非真因」而非間歇"
tags: ["til", "術語", "跨領域", "測試", "spurious-failure"]
---

> 這個詞出現在「[測試紅燈不一定是真的壞](../unreliable-tests/)」這個問題裡。

spurious failure（偽失敗）指**測試或建置確實失敗了，但失敗的原因不是被測對象本身**——而是環境、網路、暫態干擾、基礎設施問題。

它是測試的 [false positive](../false-positive/)：報了失敗、但程式碼其實沒問題。

## 與 flaky 的區別

兩者都是測試的 false positive，重點不同：

- **spurious failure** 強調「**這次失敗的原因不是真因**」——例如 CI 機器磁碟滿了、套件源連不上。
- **[flaky](../flaky/)** 強調「**間歇、不穩定**」——重跑可能就過，成因常是競態或時序。

一次 spurious failure 不一定 flaky（環境修好就穩定失敗或穩定通過）；flaky 的每次紅則多半是 spurious——除非不穩定源自被測碼自身的非確定性（那時紅燈反映的是真缺陷，不是偽失敗）。

## 處理

確認是偽失敗後，修的是**環境或基礎設施**，不是被測程式碼。把它和真失敗區分開，避免污染對測試的信任（見 [alert fatigue](../alert-fatigue/)）。

## 相關概念

- 上位概念：[false positive](../false-positive/)。
- 近鄰：[flaky](../flaky/)。
