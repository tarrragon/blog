---
title: "7.C5 Okta：2023 Support System 事件"
date: 2026-05-07
description: "支援系統憑證風險如何擴散到客戶租戶的案例。"
weight: 5
tags: ["backend", "security", "case-study"]
---

這個案例的核心責任是提醒控制面不只在正式生產系統，也在支援工具鏈。

## 觀察

Okta 2023 事件顯示支援系統若涉及高權限資料與工作流程，會成為跨租戶風險放大點。

## 判讀

身份與授權治理若只覆蓋產品面，忽略支援流程，仍會留下高影響面缺口。

## 策略

1. 把 support tooling 納入同等級身份治理。
2. 補強 session、token 與操作留痕控制。
3. 將異常支援活動接入告警與 incident 路由。

## 下一步路由

回 [7.2 identity/access boundary](/backend/07-security-data-protection/identity-access-boundary/) 與 [7.13 detection coverage](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)。

## 引用源

- [Okta support system case update](https://sec.okta.com/harfiles)
