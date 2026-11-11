---
title: "Security Middleware"
date: 2026-04-23
description: "說明請求進入 handler 前如何完成共通安全控制"
weight: 1
---

Security Middleware 的核心概念是「在 request 進入業務處理前，先套用共通安全控制」。 可先對照 [Security Misconfiguration](/backend/knowledge-cards/security-misconfiguration/)。

## 跟其他概念的關係

Security Middleware 位在 transport layer 與 handler 之間。它處理 rate limit、redaction、來源限制或其他共通防護。 可先對照 [Security Misconfiguration](/backend/knowledge-cards/security-misconfiguration/)。

## 可觀察訊號

系統需要 security middleware 的訊號是安全控制會影響多個 endpoint，且不應散落在每個 handler 中。

## 接近真實網路服務的例子

rate limit、來源 IP 限制、敏感資訊遮罩與 webhook replay 防護，都可能由 security middleware 承擔。

## 判斷條件與後果

共通安全控制放在 middleware 還是散在各個 handler，決定它涵蓋哪些 endpoint。控制散在各 handler 時，新增的 endpoint 沒有寫那段程式就沒有那項防護，同一項控制在不同 endpoint 的行為也各自不同；放在 transport layer 與 handler 之間的 middleware 時，每個 request 進入業務處理前都經過同一套檢查。拒絕語意（回什麼狀態碼與錯誤格式）不穩定時，client 分不出自己是被 rate limit 拒絕還是被來源限制拒絕，無從決定該稍後重試還是停止重試；沒有稽核輸出時，被拒絕的 request 不留紀錄，事後查不到哪個來源在什麼時間被拒絕。
