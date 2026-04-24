---
title: "Trust Boundary"
date: 2026-04-24
description: "說明系統哪些位置開始不能沿用原本的信任假設"
weight: 124
---

Trust boundary 的核心概念是「信任假設在哪裡開始不再成立」。紅隊會特別關注這些切換點，因為只要邊界不清楚，權限、稽核、遮罩與防護都可能只在局部成立。

## 概念位置

Trust boundary 會出現在 [authentication](/backend/knowledge-cards/authentication/)、[authorization](/backend/knowledge-cards/authorization/)、[tenant boundary](/backend/knowledge-cards/tenant-boundary/)、[TLS / mTLS](/backend/knowledge-cards/tls-mtls/)、[SSRF](/backend/knowledge-cards/ssrf/) 與 network policy 交界。它不是單一防護，而是描述「哪裡開始需要重新驗證」的分析框架。

## 可觀察訊號與例子

一個系統只要跨越 client、service、queue、storage、tenant 或第三方整合，就會產生 trust boundary。當邊界跨得越多，紅隊越會檢查訊號是否真的有被重新驗證，而不是延用前一段的假設。

## 設計責任

邊界管理要能說清楚誰信任誰、信任到哪裡、何時失效。若某段流程會跨越身份、租戶、網路或資料層邊界，就要在那一點重新定義驗證、授權與完整性檢查。
