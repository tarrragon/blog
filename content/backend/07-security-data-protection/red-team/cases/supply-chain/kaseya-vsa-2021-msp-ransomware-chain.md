---
title: "7.R7.2.9 Kaseya VSA 2021：MSP 供應鏈擴散路徑"
date: 2026-04-24
description: "管理平台事件透過 MSP 模型向多客戶擴散時，workflow 應如何分層應對"
weight: 71729
---

## 事故摘要

Kaseya VSA 2021 事件指出 MSP 管理平台若失守，攻擊可沿著託管關係快速擴展到多個客戶環境。

**本案例的演示焦點**：MSP / RMM 管理平面被入侵 → 透過自動化能力批次下發 → 多客戶同時感染的 fan-out 供應鏈擴散。重點在「管理平面權限範圍」與「客戶分域隔離」設計。

## 攻擊路徑

1. 攻擊管理平台入口。
2. 透過自動化管理能力下發惡意行為。
3. 連鎖影響多個下游客戶系統。

## 失效控制面

- 管理平面與客戶環境隔離不足。
- 自動化任務缺少高風險動作保護。
- 多租戶事件協調流程準備不足。

## 如果 workflow 少一步會發生什麼

若少了「跨客戶分批隔離」步驟，事件會在同一時間窗內形成大規模連鎖衝擊。

## 可落地的 workflow 檢查點

- 共同基線：以 [runbook](/backend/knowledge-cards/runbook/) 與 [incident timeline](/backend/knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：限制管理平面高風險任務範圍（破壞性動作要求 multi-party approval / 批次上限），mechanism 是讓單點接管不會立刻 fan-out 到所有客戶。
- 日常：建立多租戶事件通知與處置模板（含跨時區、跨法域的客戶通報路由）。
- 事故中：先分域隔離、再啟動客戶側回復計畫（前提是事先有客戶分組與隔離開關）。

## 從本案例到實作的 chain

本案例是事故敘事 layer，沿三步 chain 進入 implementation：

- **控制面**：[7.6 供應鏈完整性與 artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) + [7.5 工作負載身份與 federated trust](/backend/07-security-data-protection/workload-identity-and-federated-trust/) —— mitigation 的 mechanism / 前提 / context-dependence 在這裡定義。
- **演練 / 控制落地**：[Supply chain artifact drill](/backend/07-security-data-protection/blue-team/materials/scenarios/supply-chain-artifact-drill/) + [Recovery readiness pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/recovery-readiness-pattern/) + [Vulnerability response pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/vulnerability-response-pattern/) —— 把樣式轉成多租戶演練、回復欄位與漏洞處理流程。
- **跨章交接**：[backend/08-incident-response](/backend/08-incident-response/) 的跨組織通訊節奏、[backend/05-deployment-platform](/backend/05-deployment-platform/) 的多租戶部署治理。

供應鏈類事故不對應紅隊 problem-cards，主要 chain 直接從控制面起步。

## 來源

| 來源                                                                               | 類型      | 可引用範圍                           |
| ---------------------------------------------------------------------------------- | --------- | ------------------------------------ |
| [helpdesk.kaseya.com](https://helpdesk.kaseya.com/hc/en-gb/articles/4403440684689) | 官方      | 受影響版本、修補時序、客戶通報節奏   |
| [cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa21-209a)    | 政府/監管 | 受影響範圍、檢測指引、跨機構處置建議 |
| [nvd.nist.gov/CVE-2021-30116](https://nvd.nist.gov/vuln/detail/CVE-2021-30116)     | 技術分析  | CVE 細節、authenticated bypass 機制  |
