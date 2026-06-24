---
title: "Rate Limiting"
date: 2026-06-24
description: "限制每個 client 在單位時間內可送出的事件數量 — 防止單一 SDK bug 或偽造流量消耗整個 collector 的處理能力"
weight: 8
tags: ["monitoring", "rate-limiting", "security", "knowledge-card"]
---

速率限制（rate limiting）的通用概念見 [Backend 知識卡：Rate Limit](/backend/knowledge-cards/rate-limit/) — 限制某個主體在一段時間內可使用的資源量。本卡聚焦監控系統中的具體實作：限制每個 client（API key / source.app）在單位時間內可送出的事件數量，保護 collector 不被單一 SDK 的 bug（事件風暴）或偽造流量消耗處理能力。可先對照 [backpressure](/monitoring/knowledge-cards/backpressure/)（全域的容量訊號）和 [sampling](/monitoring/knowledge-cards/sampling/)（SDK 端的主動降載）。

## 和 backpressure 的差異

Rate limiting 和 backpressure 都限制流量，但保護的維度不同。Rate limiting 是 per-client 的配額機制 — 每個 API key 有獨立的速率上限，一個 client 超限不影響其他 client。Backpressure 是全域的容量訊號 — collector 的寫入 channel 滿時對所有 client 回 429，不區分來源。一個 client 的失控用 rate limiting 處理（隔離問題源），全域流量過大用 backpressure 處理（全體降速）。

## 可觀察訊號與例子

Rate limiting 觸發的訊號是 collector 端對特定 API key 回 429 的次數上升、而其他 key 正常。典型場景：某個 SDK 版本有 bug 導致每秒產生 1000 筆事件 → per-key rate limiter 超過閾值 → 該 key 的後續 request 被回 429 → 其他 SDK 不受影響。

## 設計責任

Rate limiting 承擔的設計責任是「在公平性和可用性之間取得平衡」。閾值設太低，正常的 burst flush（攢批後一次送出）會被誤觸；閾值設太高，失控的 SDK 要送很多筆才被擋。合理的閾值需高於正常 burst 的事件速率。

## 完整章節

Per-SDK rate limiting 的實作 → [Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/)。Rate limiting 在 collector access control 中的角色 → [Collector Access Control 實作](/monitoring/07-security-privacy/collector-access-control/)。偽造流量場景下 rate limiting 和其他防護層的配合 → [Client-side SDK 認證](/monitoring/07-security-privacy/client-sdk-authentication/)。
