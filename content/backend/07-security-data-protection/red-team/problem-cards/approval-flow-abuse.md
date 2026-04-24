---
title: "7.R11.2 審核流程濫用"
date: 2026-04-24
description: "說明審核節點為何會變成形式審核，進而放大高風險操作"
weight: 7212
---

審核流程的核心風險是審核責任與操作責任失去獨立性。當審核節奏只剩形式確認，流程會把高風險操作快速放行。

## 為什麼會出問題

審核流程常在效率壓力下追求快速通過。快速通過若缺乏情境證據與責任分離，審核會退化成流程裝飾。

## 常見失效樣式

- 審核人與提交人由同一群組長期重疊。
- 審核依賴固定模板，缺少情境差異判讀。
- 高風險與低風險請求使用同一審核節奏。

## 判讀訊號

- 高風險請求通過時間顯著短於預期。
- 審核意見長期一致且缺少變化。
- 事故後審核判斷依據回查鏈條出現斷點。

## 案例觸發參考

- [Mailchimp 2023](/backend/07-security-data-protection/red-team/cases/data-exfiltration/mailchimp-2023-support-tool-abuse/)
- [Change Healthcare 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/change-healthcare-2024-ops-impact/)

## 可連動章節

- [7.7 稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)
- [8.2 事故指揮與角色分工](/backend/08-incident-response/incident-command-roles/)

## 對應失效樣式卡

- [7.R11.P2 提交與審核責任重疊](/backend/07-security-data-protection/red-team/problem-cards/fp-submitter-approver-overlap/)
