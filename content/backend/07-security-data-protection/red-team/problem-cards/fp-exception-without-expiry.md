---
title: "7.R11.P18 例外缺少期限與關閉條件"
tags: ["治理例外", "Tripwire", "Risk Acceptance", "Red Team"]
date: 2026-04-30
description: "說明風險例外缺少到期與關閉條件如何累積長期暴露"
weight: 7248
---

這個失效樣式的核心問題是風險例外只有批准結果，沒有到期與關閉邊界。當例外缺少期限與關閉條件，暫時接受的風險會長期停留在正式路徑，並削弱 [containment](/backend/knowledge-cards/containment/) 節奏。

## 常見形成條件

- 例外申請缺少量化關閉條件。
- 例外期間缺少補償控制與監測 [runbook](/backend/knowledge-cards/runbook/)。
- 重大事件發生後沒有觸發例外重審。

## 判讀訊號

- 例外決策長期存續且無重評估記錄。
- 例外到期後仍自動延長。
- 關鍵風險指標變化時例外狀態沒有同步調整與 [incident timeline](/backend/knowledge-cards/incident-timeline/) 回寫。

## 案例觸發參考

- [PAN-OS 2024](/backend/07-security-data-protection/red-team/cases/edge-exposure/panos-cve-2024-3400-edge-rce/)
- [XZ 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)
- [Uber 2022](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/)

## 來源流程卡

- [方案升降級流程濫用](/backend/07-security-data-protection/red-team/problem-cards/plan-change-flow-abuse/)
