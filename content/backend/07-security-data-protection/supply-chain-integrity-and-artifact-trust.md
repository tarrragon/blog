---
title: "7.12 供應鏈完整性與 Artifact 信任"
date: 2026-04-24
description: "定義 build provenance、artifact 信任與交付鏈風險問題"
weight: 82
---

本章的責任是把交付鏈信任風險拆成可驗證節點，讓來源可信度、產物完整性與事件後收斂能被一致治理。

## 本章寫作邊界

本章聚焦來源可信度、組件邊界與發佈節奏治理，不討論單一 CI/CD 平台操作流程。

## 供應鏈信任模型

供應鏈治理的核心責任是讓每一個進入正式環境的產物都可追溯、可驗證、可回退。

1. 來源層：確認 build provenance 可對應到可驗證來源與責任主體。
2. 產物層：確認 artifact 在簽署、摘要與傳遞過程沒有完整性斷點。
3. 依賴層：確認第三方組件有隔離邊界與影響面地圖。
4. 節奏層：確認事件後可執行凍結、復原與再驗證流程。
5. 收斂層：確認供應鏈事件可路由到事件分級與回復驗證。

## 判讀流程

判讀流程的責任是把「可部署產物」轉成「可信產物」。

1. 先確認來源提交、build 環境與產物 metadata 是否可關聯。
2. 再確認產物簽署與完整性證據是否可驗證。
3. 接著確認依賴事件是否有快速切換與回退路徑。
4. 最後交接到可靠性與 incident 流程，追蹤收斂結果。

## 問題節點（案例觸發式）

| 問題節點           | 判讀訊號                     | 風險後果               | 前置控制面                                                             |
| ------------------ | ---------------------------- | ---------------------- | ---------------------------------------------------------------------- |
| 來源可追溯性不足   | build 與來源提交無法一致回查 | 發佈可信度下降         | [ci-pipeline](/backend/knowledge-cards/ci-pipeline/)                   |
| artifact 信任斷點  | 發佈產物缺乏簽署與完整性證據 | 受污染產物進入正式流程 | [deployment-contract](/backend/knowledge-cards/deployment-contract/)   |
| 第三方依賴風險放大 | 同類組件事件波及多服務       | 修補與回退成本上升     | [dependency-isolation](/backend/knowledge-cards/dependency-isolation/) |
| 事件後發佈節奏混亂 | 凍結與恢復條件不一致         | 二次事故風險上升       | [release-gate](/backend/knowledge-cards/release-gate/)                 |

## 常見風險邊界

風險邊界的責任是界定何時供應鏈風險已進入高壓狀態。

- build 來源與產物長期無法一致回查時，代表 provenance 模型失效。
- 產物沒有簽署或簽署驗證未納入發佈關卡時，代表完整性邊界不足。
- 第三方事件發生後無法快速判斷受影響服務時，代表依賴隔離不足。
- 事故期間凍結與恢復標準反覆變動時，代表交付節奏未收斂。

## 案例觸發參考

案例觸發的責任是驗證交付鏈信任模型是否有現實抗壓能力。

- 開源組件滲透與下游衝擊： [XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)
- 組件級漏洞造成大範圍傳導： [Log4Shell 2021](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)
- 平台級供應鏈事件與回退壓力： [SolarWinds 2020](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)

## 下一步路由

- 交付平台與部署治理：`05-deployment-platform`
- 發佈驗證與回退演練：`06-reliability`
- 分級與跨部門收斂：`08-incident-response`
