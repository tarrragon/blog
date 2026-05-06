---
title: "Flaky Test"
date: 2026-05-06
description: "說明非決定性測試如何降低 CI gate 信任度與治理方式"
tags: ["CI", "test", "flaky", "knowledge-card"]
weight: 15
---

Flaky Test 的核心概念是「同一版本在相同條件下測試結果不穩定」。它會把紅燈從有效訊號降級成噪音，直接影響 CI gate 信任度。

## 概念位置

Flaky Test 位在 test stage 與 release gate 之間，會放大重跑成本與判讀延遲。

## 可觀察訊號

- 同一 commit 重跑結果時好時壞。
- 失敗集中在等待條件、時間假設或外部依賴。
- 團隊習慣以重跑代替根因修復。

## 接近真實服務的例子

UI 測試在動畫未完成時抓取元素，或整合測試依賴不穩定第三方 API，都容易出現 flaky pattern。

## 設計責任

Flaky Test 治理要建立 owner、隔離策略、修復 SLA 與觀測指標，讓測試結果恢復可判讀性。
