---
title: "7.R7.3.2 Ivanti 2024：CVE-2023-46805/2024-21887 VPN 邊界漏洞鏈"
date: 2026-04-24
description: "多漏洞串接下，邊界設備事件如何轉為持續控制風險"
weight: 71732
---

## 事故摘要

2024 年初，Ivanti Connect Secure 相關公告顯示攻擊者可串接 CVE-2023-46805 與 CVE-2024-21887 進行認證繞過與遠端執行，並帶來持久化風險。

**本案例的演示焦點**：該CVE-2023-46805 → 邊界設備 / 對外應用入口接管 → 內部資源 / 會話 / 資料的橫向擴散。屬於 edge-exposure 類別、跟身分鏈接管 / 供應鏈植入 / 資料外送等其他 case category 形成互補視角。

## 攻擊路徑

1. 掃描可達 VPN 邊界。
2. 利用漏洞鏈取得初始控制。
3. 建立持續存取與後續移動路徑。

## 失效控制面

- 邊界設備長期暴露且承載關鍵流量。
- 修補後狀態驗證流程不足。
- 清除與重建步驟缺少標準化程序。

## 如果 workflow 少一步會發生什麼

若缺少「修補後完整驗證」步驟，系統可能在已修補狀態下仍保留可利用持久化痕跡。

## 可落地的 workflow 檢查點

- 共同基線：以 [runbook](/backend/knowledge-cards/runbook/) 與 [incident timeline](/backend/knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：高風險邊界設備準備替代路徑。
- 日常：建立邊界設備健康與變更基線。
- 事故中：執行隔離、重建、憑證輪替三段流程。
- mechanism 總綱：邊界事件的核心是讓「漏洞修補」「會話 / 憑證失效」「異常痕跡清查」三件事同步發生、不分先後留下時間窗口（前提是事先有 inventory + 自動化失效 / 清查能力）。

## 從本案例到實作的 chain

本案例是事故敘事 layer，沿三步 chain 進入 implementation：

- **控制面**：[7.3 入口與伺服端保護](/backend/07-security-data-protection/entrypoint-and-server-protection/) + [7.12 偵測涵蓋與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) —— mitigation 的 mechanism / 前提 / context-dependence 在這裡定義。
- **演練 / 控制落地**：[Edge session hijack game day](/backend/07-security-data-protection/blue-team/materials/scenarios/edge-session-hijack-game-day/) + [Vulnerability response pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/vulnerability-response-pattern/) + [Evidence chain pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/evidence-chain-pattern/) —— 把樣式轉成邊界演練、漏洞處理與證據鏈欄位。
- **跨章交接**：[backend/05-deployment-platform](/backend/05-deployment-platform/) 的邊界部署治理、[backend/08-incident-response](/backend/08-incident-response/) 的調查與回復步驟。

本案例屬於邊界 / 入口漏洞類別、不對應紅隊 problem-cards（後者集中於 tenant flow / identity flow），主要 chain 直接從控制面起步。


## 來源

| 來源                                                                                                                  | 類型      | 可引用範圍                     |
| --------------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------ |
| [ivanti.com](https://www.ivanti.com/blog/security-update-for-ivanti-connect-secure-and-ivanti-policy-secure-gateways) | 官方      | 受影響版本、漏洞細節、修補節奏 |
| [cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa24-060b)                                       | 政府/監管 | 受影響範圍、跨機構處置建議     |
| [nvd.nist.gov/CVE-2023-46805](https://nvd.nist.gov/vuln/detail/CVE-2023-46805)                                        | 技術分析  | CVE 細節、利用機制             |
| [nvd.nist.gov/CVE-2024-21887](https://nvd.nist.gov/vuln/detail/CVE-2024-21887)                                        | 技術分析  | CVE 細節、利用機制             |
