---
title: "Trust Boundary"
date: 2026-04-24
description: "說明系統哪些位置開始不能沿用原本的信任假設"
weight: 125
---

Trust boundary 的核心概念是「信任假設在哪裡開始不再成立」。紅隊會特別關注這些切換點，因為只要邊界不清楚，權限、稽核、遮罩與防護都可能只在局部成立。 可先對照 [Authentication](/backend/knowledge-cards/authentication/)。

## 跟其他概念的關係

Trust boundary 會出現在 [authentication](/backend/knowledge-cards/authentication/)、[authorization](/backend/knowledge-cards/authorization/)、[tenant boundary](/backend/knowledge-cards/tenant-boundary/)、[TLS / mTLS](/backend/knowledge-cards/tls-mtls/)、[SSRF](/backend/knowledge-cards/ssrf/) 與 network policy 交界。它是描述「哪裡開始需要重新驗證」的分析框架，涵蓋範圍超過任何單一防護措施；邊界清單與資產、攻擊者能力假設並排列舉時走 [threat model](/backend/knowledge-cards/threat-model/)。

## 可觀察訊號與例子

一個系統只要跨越 client、service、queue、storage、tenant 或第三方整合，就會產生 trust boundary。當邊界跨得越多，紅隊越會檢查訊號是否真的有被重新驗證，而不是延用前一段的假設。

## 判斷條件與後果

一段流程跨越身份、租戶、網路或資料層邊界的那一點，是前一段的信任假設失效的位置。下一段沿用前一段的驗證結果時（內部服務直接採信上游傳來的 user id），攻擊者只要進入前一段，權限、稽核與遮罩就只在前一段成立，原因是後一段沒有自己確認請求來自誰、能做什麼、內容是否被改過。說得出誰信任誰、信任到哪裡、何時失效，才列得出每一個跨越點，所以驗證、授權與完整性檢查在每一個跨越點各自重做一次。網路邊界這一處的原則是 [Zero Trust（零信任）](/backend/knowledge-cards/zero-trust/)：連線來自內網或 VPN，不構成跳過驗證的理由。
