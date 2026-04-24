---
title: "MTTR"
date: 2026-04-23
description: "說明平均修復時間如何作為事故處理能力指標"
weight: 160
---

MTTR 的核心概念是「從事故開始到恢復的平均時間」。它幫助團隊追蹤處置效率趨勢，但不能單獨代表可靠性品質。

## 概念位置

MTTR 連接 [incident severity](../incident-severity/)、[alert](../alert/)、[runbook](../runbook/) 與 [post-incident-review](../post-incident-review/)。不同等級事故應分開計算，避免指標失真。

## 可觀察訊號與例子

系統需要 MTTR 的訊號是團隊想驗證事故流程是否改進。若新增 runbook 與升級策略後 MTTR 持續下降，表示流程變更有實際效果。

## 設計責任

MTTR 指標要搭配樣本數、嚴重度分層與影響範圍一起解讀。它應導向流程改善與演練設計，而不是單純追求數字下降。

## 英文術語對照
- Mean Time to Recovery (MTTR)
- Mean Time to Restore
