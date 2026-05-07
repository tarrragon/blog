---
title: "7.C4 Microsoft：Storm-0558 簽章金鑰事件"
date: 2026-05-07
description: "簽章金鑰事件如何回寫 identity 信任邊界與觀測證據鏈。"
weight: 4
---

這個案例的核心責任是把身份簽章事件轉成長期信任治理問題。

## 觀察

Storm-0558 事件揭露簽章金鑰與驗證流程一旦失守，會跨租戶影響身份驗證信任。

## 判讀

此類事件的重點不只在修補漏洞，而在重建 key lifecycle、issuer 驗證與審計可見性。

## 策略

1. 重新定義 key issuance 與 rotation 流程。
2. 強化 token 驗證路徑與異常檢測。
3. 讓身份證據鏈可被 incident 與稽核共用。

## 下一步路由

回 [7.6 secrets/credentials](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) 與 [7.7 audit/accountability](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)。

## 引用源

- [Microsoft analysis of Storm-0558](https://www.microsoft.com/en-us/security/blog/2023/09/06/analysis-of-storm-0558-technique-and-microsofts-response/)
