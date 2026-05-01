---
title: "7.12 供應鏈完整性與 Artifact 信任"
date: 2026-04-24
description: "定義 build provenance、artifact 信任與交付鏈風險問題"
weight: 82
---

本章的責任是把交付鏈信任風險拆成可驗證節點，讓來源可信度、產物完整性與事件後收斂能被一致治理。

## 本章寫作邊界

本章聚焦來源可信度、組件邊界與發佈節奏治理，不討論單一 CI/CD 平台操作流程。

## 本章 threat scope

**In-scope**：來源可追溯性不足 / artifact 信任斷點 / 第三方依賴風險放大 / 事件後發佈節奏混亂。

**Out-of-scope**（路由到他章）：

- CI secrets → [7.6](../secrets-and-machine-credential-governance/)
- workload identity → [7.10](../workload-identity-and-federated-trust/)
- 例外治理 → [7.14](../security-governance-exception-and-tripwire/)
- 偵測平台 → `04-observability`、實作交付 → `05` / `06` / `08`

Reader 對 in-scope 列表的 specific threat 應該能反向 trace 到本章問題節點；out-of-scope 議題請直接跳到對應章節、不在本章 audit 範圍。

## 從本章到實作

本章是 routing layer，沿兩條 chain 進入 implementation：

- **Mechanism**：問題節點表的 `[ci-pipeline]` 等 control link 進 knowledge-card、看具體機制 / 邊界 / context-dependence。
- **Delivery**：「交接路由」欄位指向 `05-deployment-platform / 06-reliability / 08-incident-response`、接配置 / 驗證 / 處置交付。

兩條 chain 完成判準與模組級 chain 規格見 [從章節到實作的 chain](../#從章節到實作的-chain)。

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

## 引用標準

供應鏈領域標準演化快、本章參考下列外部標準作為 mechanism 層 anchor。Reader 套用前 verify 版本仍是 current best practice：

| 標準                                                  | 版本 / 年份                      | 適用場景                                           |
| ----------------------------------------------------- | -------------------------------- | -------------------------------------------------- |
| SLSA（Supply-chain Levels for Software Artifacts）    | v1.0 (2023)                      | build provenance 等級判讀（L1-L4）、來源可追溯模型 |
| NIST SSDF（Secure Software Development Framework）    | SP 800-218 (2022)                | 開發流程安全控制 reference                         |
| Sigstore（cosign / Rekor / Fulcio）                   | continuous                       | artifact 簽署 / 透明度日誌 mechanism               |
| CycloneDX / SPDX                                      | CycloneDX v1.6 / SPDX 3.0 (2024) | SBOM 格式                                          |
| OWASP Software Component Verification Standard (SCVS) | v1.0 (2020)                      | 元件驗證控制 reference                             |

引用版本與 cadence 規則見 [security-citation-currency-and-precision](/report/security-citation-currency-and-precision/)（每 12-24 月 re-check 主流標準是否有新版）。Last reviewed: 2026-05-01。

## 下一步路由

- 交付平台與部署治理：`05-deployment-platform`
- 發佈驗證與回退演練：`06-reliability`
- 分級與跨部門收斂：`08-incident-response`
