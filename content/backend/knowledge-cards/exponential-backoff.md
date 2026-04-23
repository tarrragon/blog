---
title: "Exponential Backoff"
date: 2026-04-23
description: "說明重試間隔如何逐步拉長以降低下游壓力"
weight: 45
---

Exponential backoff 的核心概念是「每次重試後把下一次等待時間按倍數拉長」。它讓系統在暫時性故障期間降低呼叫頻率，給下游恢復時間。

## 概念位置

Backoff 是 retry policy 的節奏控制。固定間隔重試容易在下游尚未恢復時持續施壓；指數退避能讓重試從快速恢復逐漸轉成保守等待。

## 可觀察訊號與例子

系統需要 backoff 的訊號是下游服務短暫 timeout、rate limit 或重啟。通知服務呼叫第三方簡訊 API 失敗時，可以先快速重試一次，再逐步拉長間隔，避免所有 worker 持續打向同一個故障 API。

## 設計責任

Backoff 要搭配最大等待時間、最大重試次數、jitter 與錯誤分類。永久性錯誤應進入分類處理或 dead-letter；暫時性錯誤才適合退避重試。
