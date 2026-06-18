---
title: "noise：淹沒真訊號的誤報"
slug: "noise"
date: 2026-06-18
description: "noise（噪音）指大量 false positive 累積、淹沒真正重要的訊號。借自訊號處理的訊噪比概念，常用於形容 linter、掃描、監控誤報過多的狀態"
tags: ["til", "術語", "跨領域", "noise"]
---

noise（噪音）指**大量 [false positive](../false-positive/) 累積，淹沒了真正重要的訊號**。

這個詞借自訊號處理的**訊噪比（signal-to-noise ratio）**：誤報越多，真訊號越難被看見。一個 linter 報出幾百條多半無關緊要的警告、一個監控系統整天閃 [false alarm](../false-alarm/)，都會被說成「noise 太多」。

## 為何是問題

noise 本身的每一條可能無害，但**總量**會壓垮注意力：真正該處理的混在裡面被略過。降噪（提高規則精度、過濾、分級）是讓真訊號重新浮現的前提。

## 後果

noise 持續累積會導致 [alert fatigue](../alert-fatigue/)——人對告警麻木。所以「降噪」不只是美觀問題，是維持偵測系統可用性的關鍵。

## 連到家族

- 組成 noise 的單位：[false positive](../false-positive/)、[false alarm](../false-alarm/)、[spurious warning](../spurious-warning/)。
- 人因後果：[alert fatigue](../alert-fatigue/)。
