---
title: "7.R11.P15 發佈凍結缺少重評估觸發器"
tags: ["發布凍結", "Release Freeze", "Tripwire", "Red Team"]
date: 2026-04-30
description: "說明供應鏈事件期間發佈凍結若缺少 tripwire 容易造成決策失效"
weight: 7245
---

這個失效樣式的核心問題是凍結決策只有開始條件，沒有重評估與解除條件。當發佈凍結缺少 tripwire，團隊會在過期決策下持續承擔風險，讓 [release gate](/backend/knowledge-cards/release-gate/) 失去保護作用。

## 常見形成條件

- 事件期間只記錄凍結決策，沒有量化解除條件與 [rollback strategy](/backend/knowledge-cards/rollback-strategy/)。
- 例外流程缺少到期時間與重審節點。
- 凍結、恢復與回退條件在跨部門間不一致。

## 判讀訊號

- 凍結決策在事件結束後長期存續且無重審 [runbook](/backend/knowledge-cards/runbook/) 紀錄。
- 發佈恢復與驗證條件反覆變動。
- 重大訊號變化後沒有觸發例外重評估。

## 案例觸發參考

- [PAN-OS 2024](/backend/07-security-data-protection/red-team/cases/edge-exposure/panos-cve-2024-3400-edge-rce/)
- [XZ 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)
- [TeamCity 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/teamcity-2024-cve-27198-27199-auth-path-traversal/)

## 來源流程卡

- [方案升降級流程濫用](/backend/07-security-data-protection/red-team/problem-cards/plan-change-flow-abuse/)
