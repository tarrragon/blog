---
title: "7.R11.P7 降級後能力回收延遲"
date: 2026-04-24
description: "說明方案降級後能力回收延遲如何造成授權邊界漂移"
weight: 7237
---

這個失效樣式的核心問題是商業狀態與技術授權狀態不同步。當降級後能力回收延遲，邊界會在時序差中擴張。

## 常見形成條件

- 升級即時生效，降級延後回收。
- 計費狀態更新與授權狀態更新分離。
- 降級事件缺少跨系統一致性檢查。

## 判讀訊號

- 降級後仍可呼叫高階功能。
- 方案狀態與授權狀態長時間偏移。
- 降級事件與高耗資源操作重疊。

## 案例觸發參考

- [Kaseya 2021](/backend/07-security-data-protection/red-team/cases/supply-chain/kaseya-vsa-2021-msp-ransomware-chain/)
- [TeamCity 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/teamcity-2024-cve-27198-27199-auth-path-traversal/)

## 來源流程卡

- [方案升降級流程濫用](/backend/07-security-data-protection/red-team/problem-cards/plan-change-flow-abuse/)

## 下一步路由

本失效樣式對應的實作 chain：

**控制面（mitigation 在這裡定義）**：

- [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)

**演練 / 控制落地（轉成欄位）**：

- [Credential hygiene pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/credential-hygiene-pattern/)
