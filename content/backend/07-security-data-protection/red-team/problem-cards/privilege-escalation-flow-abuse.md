---
title: "7.R11.6 權限提升流程濫用"
date: 2026-04-24
description: "說明權限提升流程為何容易把局部存取轉成全域控制"
weight: 7216
---

權限提升流程的核心風險是把高影響能力集中在少數切換節點。當提升條件與審核證據不完整，流程會把局部權限擴張成全域權限。

## 為什麼會出問題

權限提升流程通常是處理例外需求。例外節奏若缺乏明確期限與回收條件，提升能力會長期停留並被重複利用。

## 常見失效樣式

- 權限提升缺乏時效與目的綁定。
- 提升後回收流程依賴人工記憶。
- 權限提升事件缺少跨系統同步。

## 判讀訊號

- 提升後高權限存續時間拉長。
- 同一主體反覆觸發提升與批次操作。
- 提升事件與審核事件的時序對齊存在缺口。

## 案例觸發參考

- [Confluence 2023（22515/22518）](/backend/07-security-data-protection/red-team/cases/edge-exposure/confluence-2023-cve-22515-22518-access-control-chain/)
- [Fortinet 2022（40684）](/backend/07-security-data-protection/red-team/cases/edge-exposure/fortinet-cve-2022-40684-auth-bypass/)

## 可連動章節

- [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)
- [7.14 資安治理例外與 Tripwire](/backend/07-security-data-protection/security-governance-exception-and-tripwire/)

## 對應失效樣式卡

- [7.R11.P6 權限提升缺乏時效綁定](/backend/07-security-data-protection/red-team/problem-cards/fp-privilege-elevation-without-time-bound/)

## 演練 / 控制落地

把本失效樣式轉成 release gate / tabletop 欄位的 blue-team control-pattern：

- [Control owner pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/control-owner-pattern/)
