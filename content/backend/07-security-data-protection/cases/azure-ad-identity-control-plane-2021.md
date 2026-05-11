---
title: "7.C3 Azure AD：2021 Identity Control-plane 事件"
date: 2026-05-07
description: "身分控制面事件如何影響多服務信任鏈與回復優先序。"
weight: 3
tags: ["backend", "security", "case-study"]
---

這個案例的核心責任是說明身份服務控制面故障會外溢成大範圍服務故障。

## 觀察

Azure AD 控制面事件導致多個依賴身份驗證的服務受影響，事故處理需要同時兼顧身份恢復與服務降級策略。

## 判讀

當身份系統是共同依賴，問題會跨產品線傳播，必須把身份恢復路徑與業務優先序綁定管理。

## 策略

1. 建立身份控制面的降級與隔離策略。
2. 讓關鍵服務支援有限模式運行。
3. 在 incident command 中獨立處理 identity workstream。

## 下一步路由

回 [7.2 identity and access boundary](/backend/07-security-data-protection/identity-access-boundary/) 與 [8.8 security vs operational incident](/backend/08-incident-response/security-vs-operational-incident/)。

## 引用源

- [Azure AD 2021 incident](https://www.microsoft.com/en-us/security/blog/2021/03/17/azure-active-directory-resilience-lessons-from-the-march-15-2021-incident/)
