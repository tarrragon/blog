---
title: "false alarm：監控的偽警報"
slug: "false-alarm"
date: 2026-06-18
description: "false alarm 指監控、告警或入侵偵測系統觸發了，但實際沒事，是 monitoring / IDS 領域的 false positive。字面就是「假警報」，與訊號偵測的 false positive 同源"
tags: ["til", "術語", "跨領域", "false-alarm"]
---

> 這個詞出現在「[告警太多，反而沒人看](../alert-overload/)」這個問題裡。

false alarm（偽警報）指**監控、告警或入侵偵測（IDS）系統觸發了，但實際上沒事**——是 monitoring / 資安領域的 [false positive](../false-positive/)。

「alarm」這個字面比 false positive 更口語、更早，消防與保全領域早就在用「假警報」。放到偵測語境，它就是 false positive 的一種。

## 為何要在意

單一 false alarm 只是虛驚，但**累積**會出兩個問題：

- 量大形成 [noise](../noise/)，真警報被埋沒。
- 人對告警麻木，演變成 [alert fatigue](../alert-fatigue/)——連真的也不再認真看。

所以告警系統的設計重點之一，就是壓低 false alarm 率（提高 [precision](../precision/)），同時別漏掉真事件。

## 相關概念

- 上位概念：[false positive](../false-positive/)。
- 量多後的狀態與後果：[noise](../noise/)、[alert fatigue](../alert-fatigue/)。
