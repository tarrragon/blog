---
title: "Checkpoint"
date: 2026-04-23
description: "說明長時間處理流程如何記錄可恢復進度"
weight: 81
---

Checkpoint 的核心概念是「記錄處理流程已安全完成的位置」。它讓長時間工作、event consumer、migration、backfill 或資料同步在中斷後可以接續。

## 概念位置

Checkpoint 是恢復能力與重放安全的基礎。它可以是 offset、時間戳、primary key、batch id、file position 或業務狀態。

## 可觀察訊號與例子

系統需要 checkpoint 的訊號是工作需要分批完成或可能中途停止。Backfill 會員資料跑到第 300 萬筆時部署中斷，checkpoint 讓下一次從安全位置繼續。

## 設計責任

Checkpoint 要和處理完成條件對齊。提交太早可能遺失工作，提交太晚可能重複處理；因此 handler 需要 idempotency 或可重入設計。
