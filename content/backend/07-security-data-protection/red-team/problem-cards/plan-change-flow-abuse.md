---
title: "7.R11.7 方案升降級流程濫用"
date: 2026-04-24
description: "說明方案切換流程為何容易成為權限與資源邊界繞過點"
weight: 7217
---

方案升降級流程的核心風險是把商業權限與技術權限綁在同一切換節點。當計費狀態與能力狀態不同步，流程會形成可利用的邊界差。

## 為什麼會出問題

方案切換通常優先滿足商業即時性。即時切換若缺少狀態一致性與回滾語意，攻擊者可利用時序差取得超額能力。

## 常見失效樣式

- 升級立即生效，降級延遲回收能力。
- 計費失敗仍保留高階功能。
- 方案變更缺少稽核與通知鏈。

## 判讀訊號

- 升降級事件與高耗資源操作重疊。
- 方案狀態與授權狀態出現偏移。
- 邊界功能在降級後仍可存取。

## 案例觸發參考

- [Kaseya 2021](/backend/07-security-data-protection/red-team/cases/supply-chain/kaseya-vsa-2021-msp-ransomware-chain/)
- [TeamCity 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/teamcity-2024-cve-27198-27199-auth-path-traversal/)

## 可連動章節

- [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)
- [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)

## 對應失效樣式卡

- [7.R11.P7 降級後能力回收延遲](/backend/07-security-data-protection/red-team/problem-cards/fp-entitlement-revocation-lag-after-plan-downgrade/)

## 演練 / 控制落地

把本失效樣式轉成 release gate / tabletop 欄位的 blue-team control-pattern：

- [Control owner pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/control-owner-pattern/)
