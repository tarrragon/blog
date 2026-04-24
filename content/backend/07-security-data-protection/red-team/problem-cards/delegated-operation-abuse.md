---
title: "7.R11.3 代理操作濫用"
date: 2026-04-24
description: "說明代理操作為何容易形成責任鏈斷點與高權限濫用"
weight: 7213
---

代理操作的核心風險是把操作者與責任主體分離。當代理邊界與審計邊界沒有一致設計，流程會形成可擴散的高權限通道。

## 為什麼會出問題

代理操作常用來提升客服與營運效率。效率導向若缺少情境限制與可回查證據，代理能力會超出原始責任範圍。

## 常見失效樣式

- 代理操作缺少明確目的與時效。
- 代理能力覆蓋一般使用者日常流程之外的功能。
- 代理會話與原始使用者會話可混用。

## 判讀訊號

- 代理操作集中在非客服時段。
- 代理主體在短時間跨多租戶操作。
- 代理流程中高風險動作比例上升。

## 案例觸發參考

- [MGM 2023](../cases/identity-access/mgm-2023-identity-lateral-impact/)
- [Mailchimp 2023](../cases/data-exfiltration/mailchimp-2023-support-tool-abuse/)

## 可連動章節

- [7.2 身分與授權邊界](../../identity-access-boundary/)
- [7.7 稽核追蹤與責任邊界](../../audit-trail-and-accountability-boundary/)

## 對應失效樣式卡

- [7.R11.P3 代理會話上下文混層](fp-delegated-session-context-bleed/)
