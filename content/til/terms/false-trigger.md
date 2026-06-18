---
title: "false trigger / 誤觸：守衛被不該觸發的東西觸發"
slug: "false-trigger"
date: 2026-06-18
description: "false trigger（誤觸）指守衛或偵測器被「形似但非真意圖」的輸入觸發，是 hook / guard 場景的 false positive。常見機制是 over-match，典型例子是關鍵字守衛對引用該關鍵字的文字誤觸"
tags: ["til", "術語", "跨領域", "false-trigger"]
---

false trigger（誤觸）指**守衛或偵測器被「形似但其實不是真意圖」的輸入觸發**——是 hook / guard 場景的 [false positive](../false-positive/)。

## 與 over-match 的角度差

- **[over-match](../over-match/)** 是機制視角：規則涵蓋太寬。
- **false trigger** 是結果視角：守衛因此被觸發了。

同一件事的因與果——規則 over-match，於是守衛 false trigger。

## 一個典型例子

關鍵字守衛用「跳過審查」這組字偵測使用者的意圖。結果一則只是**引用或討論**「跳過審查」字樣的訊息也觸發了——命中了字面、但沒有真正要跳過的意圖。

這種「命中字面、無真實意圖」的 false positive 有個精準說法：**lexical false positive**（字面層假陽性）。修法是讓守衛在「明確是引用或討論」時抑制，但方向要保守——寧可偶爾誤觸（false positive），也別漏放真正的意圖（那會變成更危險的 [false negative](../false-negative/)）。這個取捨方向，和 [precision](../precision/) / [recall](../recall/) 的選擇是同一回事。

## 連到家族

- 上位概念：[false positive](../false-positive/)。
- 機制成因：[over-match](../over-match/)。
- 取捨的另一端：[false negative](../false-negative/)。
