---
title: "7.C7 Okta：BYO Telephony 的身份安全責任轉換"
date: 2026-05-07
description: "MFA 簡訊/語音路徑從平台托管轉向客戶自管的治理案例。"
weight: 7
---

這個案例的核心責任是說明身份安全控制也會出現供應鏈責任重分配。

## 觀察

Okta 推動 BYO telephony，將 SMS/voice MFA 的供應商控制責任轉給客戶側治理。

## 判讀

這類轉換不是功能變更，而是信任邊界與責任邊界變更，需要同步更新風險模型。

## 策略

1. 明確定義 telephony provider 的安全要求。
2. 把供應商變更納入身份風險評估節奏。
3. 建立跨供應商故障與濫用應變流程。

## 下一步路由

回 [7.10](/backend/07-security-data-protection/workload-identity-and-federated-trust/) 與 [7.14](/backend/07-security-data-protection/security-governance-exception-and-tripwire/)。

## 引用源

- [BYO Telephony and the future of SMS at Okta](https://sec.okta.com/articles/2023/08/byo-telephony-and-future-sms-okta/)
