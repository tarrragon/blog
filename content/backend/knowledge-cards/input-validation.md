---
title: "Input Validation"
date: 2026-04-23
description: "說明進入系統的資料如何先被檢查格式、範圍與語意"
weight: 121
---


Input validation 的核心概念是「資料進入系統時先檢查格式、範圍與語意」。它保護後續 business logic、database、queue、parser 與外部 API。 可先對照 [Internal Endpoint](/backend/knowledge-cards/internal-endpoint/)。

## 概念位置

Input validation 是 API 邊界與安全邊界的第一層。它不取代 authorization、business rule 或 database constraint，但能提早拒絕無效資料並產生清楚錯誤。 可先對照 [Internal Endpoint](/backend/knowledge-cards/internal-endpoint/)。

## 可觀察訊號與例子

系統需要 input validation 的訊號是 API 接收 JSON、檔案、URL、查詢條件或 webhook payload。日期範圍、email 格式、檔案大小、enum 值與 ID 格式都應在入口被驗證。

## 設計責任

Validation 要分層：格式檢查在入口，業務規則在 usecase，資料完整性由 database constraint 保底。錯誤回應要清楚但避免洩漏內部細節。
