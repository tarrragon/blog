---
title: "7.R11 流程濫用問題卡片"
tags: ["Red Team", "Problem Cards", "Failure Patterns"]
date: 2026-04-24
description: "以原子化卡片細化整體 red-team 知識網，承接金字塔結構往下生長的問題討論"
weight: 721
---

本章的責任是承接 red-team 主題層，往下細化成可重用的問題卡與失效樣式卡。每張卡片只處理一個問題節點，主體是失效成因、判讀訊號與案例觸發條件。

## 在紅隊金字塔中的位置

本章是紅隊金字塔的細化層，不只處理高風險流程。它承接 7.R1 到 7.R10 的判讀語言，把攻擊面、信任邊界、流程濫用、資料外送、資源濫用、偵測缺口都拆成單點問題，方便跨章節引用與持續擴充。

## 使用方式

1. 先選一個 red-team 問題主題。
2. 再進入對應問題卡或失效樣式卡。
3. 觸發條件成立時引用案例做證據比對。
4. 最後交接到 7.x 主章節或 8.x workflow。

## 卡片列表

### 流程問題卡

- [邀請流程濫用](/backend/07-security-data-protection/red-team/problem-cards/invite-flow-abuse/)
- [審核流程濫用](/backend/07-security-data-protection/red-team/problem-cards/approval-flow-abuse/)
- [代理操作濫用](/backend/07-security-data-protection/red-team/problem-cards/delegated-operation-abuse/)
- [帳號切換濫用](/backend/07-security-data-protection/red-team/problem-cards/account-switching-abuse/)
- [密碼重設流程濫用](/backend/07-security-data-protection/red-team/problem-cards/password-reset-flow-abuse/)
- [權限提升流程濫用](/backend/07-security-data-protection/red-team/problem-cards/privilege-escalation-flow-abuse/)
- [方案升降級流程濫用](/backend/07-security-data-protection/red-team/problem-cards/plan-change-flow-abuse/)
- [匯出流程濫用](/backend/07-security-data-protection/red-team/problem-cards/export-flow-abuse/)
- [分享流程濫用](/backend/07-security-data-protection/red-team/problem-cards/sharing-flow-abuse/)
- [批次操作濫用](/backend/07-security-data-protection/red-team/problem-cards/bulk-operation-abuse/)
- [跨租戶協作濫用](/backend/07-security-data-protection/red-team/problem-cards/cross-tenant-collaboration-abuse/)
- [第三方授權濫用](/backend/07-security-data-protection/red-team/problem-cards/third-party-authorization-abuse/)

### 單一失效樣式卡

- [可重放邀請連結](/backend/07-security-data-protection/red-team/problem-cards/fp-replayable-invitation-link/)
- [提交與審核責任重疊](/backend/07-security-data-protection/red-team/problem-cards/fp-submitter-approver-overlap/)
- [代理會話上下文混層](/backend/07-security-data-protection/red-team/problem-cards/fp-delegated-session-context-bleed/)
- [帳號切換後沿用高權限 token](/backend/07-security-data-protection/red-team/problem-cards/fp-stale-privileged-token-after-account-switch/)
- [重設憑證可重放且有效期過長](/backend/07-security-data-protection/red-team/problem-cards/fp-replayable-reset-token-with-long-ttl/)
- [權限提升缺乏時效綁定](/backend/07-security-data-protection/red-team/problem-cards/fp-privilege-elevation-without-time-bound/)
- [降級後能力回收延遲](/backend/07-security-data-protection/red-team/problem-cards/fp-entitlement-revocation-lag-after-plan-downgrade/)
- [匯出檔案長時間可重複下載](/backend/07-security-data-protection/red-team/problem-cards/fp-long-lived-repeatable-export-artifact/)
- [分享連結缺少到期語意](/backend/07-security-data-protection/red-team/problem-cards/fp-share-link-without-expiry-semantics/)
- [批次流程缺少中止檢查點](/backend/07-security-data-protection/red-team/problem-cards/fp-batch-flow-without-stop-checkpoint/)
- [跨租戶上下文快取殘留](/backend/07-security-data-protection/red-team/problem-cards/fp-cross-tenant-context-cache-residue/)
- [第三方 token 授權範圍過寬](/backend/07-security-data-protection/red-team/problem-cards/fp-overscoped-third-party-token-grant/)
- [聯邦 token 信任漂移](/backend/07-security-data-protection/red-team/problem-cards/fp-federated-token-trust-drift/)
- [備份刪除證據缺口](/backend/07-security-data-protection/red-team/problem-cards/fp-backup-deletion-evidence-gap/)
- [發佈凍結缺少重評估觸發器](/backend/07-security-data-protection/red-team/problem-cards/fp-release-freeze-without-tripwire/)
- [產物缺少來源證據](/backend/07-security-data-protection/red-team/problem-cards/fp-artifact-without-provenance/)
- [偵測訊號關聯斷點](/backend/07-security-data-protection/red-team/problem-cards/fp-detection-signal-correlation-gap/)
- [例外缺少期限與關閉條件](/backend/07-security-data-protection/red-team/problem-cards/fp-exception-without-expiry/)

### 延伸候選卡

延伸候選卡的責任是保留下一輪拆卡入口。當主章出現新失效樣式或案例映射缺口時，再回填這個區塊。
