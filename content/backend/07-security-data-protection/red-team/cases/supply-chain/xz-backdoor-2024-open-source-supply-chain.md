---
title: "7.R7.2.4 XZ Backdoor 2024：開源供應鏈長期滲透"
date: 2026-04-24
description: "開源維護鏈遭滲透後，為何會直接影響廣泛 Linux 發行流程"
weight: 71724
---

## 事故摘要

2024 年 3 月，XZ Utils 事件揭露開源供應鏈可被長期滲透並在釋出流程埋入後門，對基礎設施信任鏈造成直接衝擊。

**本案例的演示焦點**：開源 maintainer 角色被長期社交滲透 → 釋出流程嵌入後門 → 跨 Linux 發行版下游擴散的 human-supply-chain 攻擊。重點在 maintainer trust governance、跟 build pipeline / artifact provenance 攻擊形成互補。

## 攻擊路徑

1. 長期滲透維護流程。
2. 在釋出包鏈條加入惡意邏輯。
3. 透過下游發行與部署流程擴散風險。

## 失效控制面

- 開源維護與釋出治理缺少獨立覆核。
- 下游對上游釋出信任過高。
- 供應鏈檢測流程常延後辨識異常組件行為。

## 如果 workflow 少一步會發生什麼

若缺少「上游重大事件觸發的版本凍結與風險重評」，下游仍可能將高風險版本推進正式環境。

## 可落地的 workflow 檢查點

- 共同基線：以 [runbook](/backend/knowledge-cards/runbook/) 與 [incident timeline](/backend/knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：關鍵依賴建立雙人覆核與來源驗證（不只 hash 比對、檢查 release-tarball 跟 git tag 的差異），mechanism 是讓 maintainer 單點失守不會直接通到下游。
- 日常：維護套件清單與影響面地圖（含 transitive 依賴、build-time vs runtime 區分）。
- 事故中：啟動版本凍結、替代版本切換與復測流程（前提是事先有「該套件 unavailable 也能 build」的 fallback 評估）。

## 從本案例到實作的 chain

本案例是事故敘事 layer，沿三步 chain 進入 implementation：

- **控制面**：[7.6 供應鏈完整性與 artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) —— mitigation 的 mechanism / 前提 / context-dependence 在這裡定義。
- **演練 / 控制落地**：[Supply chain artifact drill](/backend/07-security-data-protection/blue-team/materials/scenarios/supply-chain-artifact-drill/) + [Vulnerability response pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/vulnerability-response-pattern/) + [Recovery readiness pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/recovery-readiness-pattern/) —— 把樣式轉成 SBOM 演練、版本凍結欄位。
- **跨章交接**：[backend/05-deployment-platform](/backend/05-deployment-platform/) 的依賴治理、[backend/06-reliability](/backend/06-reliability/) 的變更風險控制。

供應鏈類事故不對應紅隊 problem-cards，主要 chain 直接從控制面起步。

## 來源

| 來源                                                                                                                                                      | 類型      | 可引用範圍                          |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ----------------------------------- |
| [openwall.com](http://www.openwall.com/lists/oss-security/2024/03/29/4)                                                                                   | 官方      | 第一手揭露、後門技術細節、發現時序  |
| [cisa.gov](https://www.cisa.gov/news-events/alerts/2024/03/29/reported-supply-chain-compromise-affecting-xz-utils-data-compression-library-cve-2024-3094) | 政府/監管 | 受影響範圍、跨機構處置建議          |
| [nvd.nist.gov/CVE-2024-3094](https://nvd.nist.gov/vuln/detail/CVE-2024-3094)                                                                              | 技術分析  | CVE 細節、build-time injection 機制 |
