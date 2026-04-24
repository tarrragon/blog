---
title: "7.R5 設定錯誤與隱藏入口"
date: 2026-04-24
description: "說明 debug、預設值與環境差異如何意外暴露能力"
weight: 715
---

紅隊很常從設定錯誤開始找突破點，因為功能本身可能沒問題，但環境、預設值或部署流程會把不該公開的能力打開。這類問題的重點不是程式碼邏輯，而是誰以為某個入口只存在於某個環境。

## 概念位置

這類風險已和 [Security Misconfiguration](../../knowledge-cards/security-misconfiguration/) 直接相連，也會碰到 [Diagnostic Endpoint](../../knowledge-cards/diagnostic-endpoint/)、[Admin Endpoint](../../knowledge-cards/admin-endpoint/)、[feature flag](../../knowledge-cards/feature-flag/)、[Release Gate](../../knowledge-cards/release-gate/) 與 cloud policy。紅隊會找的是隱藏能力、測試殘留、錯誤的 CORS、過寬的來源限制與不一致的環境設定。

## 可觀察訊號與例子

如果 staging 的 debug endpoint 在 production 仍可用、default credential 沒被換掉、或某些環境能看到比預期更多的錯誤訊息，這些都是典型的 misconfiguration surface。紅隊會把這些面視為低成本高回報的突破點。

## 設計責任

設定錯誤不能只靠人工記憶。防護要有 baseline config、環境差異審查、secret scan、IaC review 與 drift detection，並且把高風險設定納入 release gate，而不是只在事故後才回頭處理。
