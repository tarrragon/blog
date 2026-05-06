---
title: "Chaos Test"
date: 2026-04-23
description: "說明透過受控故障注入驗證系統在異常條件下的恢復能力"
weight: 159
---


Chaos test 的核心概念是「在可控範圍內主動注入故障，驗證系統韌性」。它用於驗證降級、切換與回復流程。 可先對照 [Checkpoint](/backend/knowledge-cards/checkpoint/)。

## 概念位置

常在預備環境或受控生產範圍執行，模擬節點失效、網路延遲、依賴不可用等情境。 可先對照 [Checkpoint](/backend/knowledge-cards/checkpoint/)。

## 設計責任

設計時要定義故障範圍、停止條件、觀測指標與回復流程，避免測試本身造成失控影響。
