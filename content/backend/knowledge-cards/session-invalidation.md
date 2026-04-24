---
title: "Session Invalidation"
tags: ["會話失效", "Session Invalidation"]
date: 2026-04-24
description: "說明事件後如何讓既有會話失效，避免被重放或延續利用"
weight: 265
---

Session invalidation 的核心概念是「使既有會話在定義時間內失去可用性」。它是事件收斂的重要步驟，常與憑證輪替同時執行。

## 概念位置

Session invalidation 位在 [authentication](../authentication/)、[credential](../credential/)、[incident-timeline](../incident-timeline/) 與 [runbook](../runbook/) 之間。它承接身分事件後的收斂節奏。

## 可觀察訊號與例子

系統需要會話失效機制的訊號是修補完成後仍觀察到可疑會話、異常登入地理分布或持續重放行為。邊界設備事件與 SSO 事件常需要全域會話失效。

## 設計責任

會話失效要定義觸發條件、覆蓋範圍、失效時序與驗證方式。設計上需要兼顧安全收斂速度與業務可用性。

