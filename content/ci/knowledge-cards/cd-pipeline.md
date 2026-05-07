---
title: "CD Pipeline"
date: 2026-05-06
description: "說明持續交付如何把已驗證產物推進到目標環境"
tags: ["CD", "pipeline", "knowledge-card"]
weight: 2
---

CD Pipeline 的核心概念是「把已驗證產物安全交付到目標環境」。它把 build、artifact、deploy 與 release gate 串成可重播流程。

## 概念位置

CD Pipeline 位在 CI 驗證之後，負責 artifact promotion、部署執行、環境保護與回復路徑。

## 可觀察訊號

- 同一份 artifact 需要在多個環境推進。
- 發布步驟需要審核、權限或時間窗控制。
- 發布失敗時需要可回退或可修復路徑。

## 接近真實服務的例子

靜態站會在 CI 成功後上傳 artifact 到 hosting。後端服務會推進同一個 image tag 到 staging 與 production，並以 rollout strategy 控制風險。

## 設計責任

CD Pipeline 要明確定義放行條件、部署順序、例外流程與回復策略，確保發布節奏與風險控制一致。
