---
title: "Security Middleware"
date: 2026-04-23
description: "說明請求進入 handler 前如何完成共通安全控制"
weight: 0
---

Security Middleware 的核心概念是「在 request 進入業務處理前，先套用共通安全控制」。

## 概念位置

Security Middleware 位在 transport layer 與 handler 之間。它處理 rate limit、redaction、來源限制或其他共通防護。

## 可觀察訊號

系統需要 security middleware 的訊號是安全控制會影響多個 endpoint，且不應散落在每個 handler 中。

## 接近真實網路服務的例子

rate limit、來源 IP 限制、敏感資訊遮罩與 webhook replay 防護，都可能由 security middleware 承擔。

## 設計責任

Security Middleware 要把共通安全策略放在邊界上，並維持穩定的拒絕語意與稽核輸出。
