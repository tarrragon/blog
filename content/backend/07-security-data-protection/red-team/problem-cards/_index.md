---
title: "7.R11 流程濫用問題卡片"
date: 2026-04-24
description: "以原子化卡片拆解高風險流程的濫用樣式，聚焦為什麼出問題與常見失效路徑"
weight: 721
---

本章的責任是把常見業務流程拆成單一問題卡。每張卡片只處理一個流程節點，主體是失效樣式與判讀訊號，案例作為觸發式證據參考。

## 使用方式

1. 先選一個流程問題卡。
2. 再比對判讀訊號與失效樣式。
3. 觸發條件成立時再引用案例做證據比對。
4. 最後交接到 7.2 / 7.3 / 7.4 / 7.6 / 7.7 或 8.x workflow。

## 卡片列表

### 流程問題卡

- [邀請流程濫用](invite-flow-abuse/)
- [審核流程濫用](approval-flow-abuse/)
- [代理操作濫用](delegated-operation-abuse/)
- [帳號切換濫用](account-switching-abuse/)
- [密碼重設流程濫用](password-reset-flow-abuse/)
- [權限提升流程濫用](privilege-escalation-flow-abuse/)
- [方案升降級流程濫用](plan-change-flow-abuse/)
- [匯出流程濫用](export-flow-abuse/)
- [分享流程濫用](sharing-flow-abuse/)
- [批次操作濫用](bulk-operation-abuse/)
- [跨租戶協作濫用](cross-tenant-collaboration-abuse/)
- [第三方授權濫用](third-party-authorization-abuse/)

### 單一失效樣式卡

- [可重放邀請連結](fp-replayable-invitation-link/)
- [提交與審核責任重疊](fp-submitter-approver-overlap/)
- [代理會話上下文混層](fp-delegated-session-context-bleed/)
- [帳號切換後沿用高權限 token](fp-stale-privileged-token-after-account-switch/)
- [重設憑證可重放且有效期過長](fp-replayable-reset-token-with-long-ttl/)
- [權限提升缺乏時效綁定](fp-privilege-elevation-without-time-bound/)
- [降級後能力回收延遲](fp-entitlement-revocation-lag-after-plan-downgrade/)
- [匯出檔案長時間可重複下載](fp-long-lived-repeatable-export-artifact/)
- [分享連結缺少到期語意](fp-share-link-without-expiry-semantics/)
- [批次流程缺少中止檢查點](fp-batch-flow-without-stop-checkpoint/)
- [跨租戶上下文快取殘留](fp-cross-tenant-context-cache-residue/)
- [第三方 token 授權範圍過寬](fp-overscoped-third-party-token-grant/)
