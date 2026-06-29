---
title: "7.C2 Cloudflare：2023 Control-plane Token 事件"
date: 2026-05-07
description: "控制面 token 事件如何回寫 secrets 與機器憑證治理。"
weight: 2
tags: ["backend", "security", "case-study"]
---

這個案例的核心責任是把控制面 token 風險落到 secret lifecycle 與權限邊界治理。

## 觀察

控制面 token 事件顯示機器憑證若治理不足，會形成跨服務高權限風險。

## 判讀

這類問題的根因是 token 生命週期、最小權限與審計證據鏈未對齊，單一憑證洩漏只是觸發點。

## 策略

1. 用工作負載身份替代長期共享 token。
2. 強制 token rotation 與細粒度 scope。
3. 把憑證事件寫入 release gate 與 incident triage。

## 下一步路由

回 [7.6 secrets and machine credential governance](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) 與 [7.12 supply chain integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)。

## 引用源

- [Cloudflare incident on January 24, 2023](https://blog.cloudflare.com/cloudflare-incident-on-january-24th-2023/)
