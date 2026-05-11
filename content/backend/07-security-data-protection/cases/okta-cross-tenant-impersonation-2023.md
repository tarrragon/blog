---
title: "7.C6 Okta：Cross-tenant Impersonation 防禦回寫"
date: 2026-05-07
description: "跨租戶 impersonation 風險如何轉成身份治理與偵測策略。"
weight: 6
tags: ["backend", "security", "case-study"]
---

這個案例的核心責任是把跨租戶身份濫用轉成可檢測、可回退的控制流程。

## 觀察

Okta 公開 cross-tenant impersonation 預防與偵測建議，揭示管理員流程與身份策略是關鍵風險點。

## 判讀

若高權限管理流程與租戶隔離規則未收斂，會形成跨租戶攻擊面。

## 策略

1. 收斂高權限管理員權限與適用範圍。
2. 建立 impersonation 相關事件偵測規則。
3. 將可疑活動納入 incident triage 快速路由。

## 下一步路由

回 [7.2](/backend/07-security-data-protection/identity-access-boundary/) 與 [7.13](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)。

## 引用源

- [Cross-Tenant Impersonation: Prevention and Detection](https://sec.okta.com/articles/2023/08/cross-tenant-impersonation-prevention-and-detection/)
