---
title: "7.R7.3.13 ProxyLogon 2021：CVE-2021-26855/27065 入口鏈式失效"
date: 2026-04-24
description: "郵件系統入口漏洞被串接利用時，事件會迅速擴大到內部服務邊界"
weight: 717313
---

## 事故摘要

ProxyLogon 事件顯示 CVE-2021-26855 與 CVE-2021-27065 這類企業郵件系統入口漏洞可被快速批量利用並形成內網風險。

**本案例的演示焦點**：該CVE-2021-26855 → 邊界設備 / 對外應用入口接管 → 內部資源 / 會話 / 資料的橫向擴散。屬於 edge-exposure 類別、跟身分鏈接管 / 供應鏈植入 / 資料外送等其他 case category 形成互補視角。

## 攻擊路徑

1. 掃描 Exchange 對外入口。
2. 串接漏洞取得伺服器執行能力。
3. 植入 web shell 或建立持續控制。

## 失效控制面

- 郵件入口暴露與修補時差偏大。
- 漏洞利用跡象監控覆蓋不足。
- 事件後清除與重建流程準備不足。

## 如果 workflow 少一步會發生什麼

若少了「修補後入侵痕跡清查」步驟，事件會在已更新版本上延續。

## 可落地的 workflow 檢查點

- 共同基線：以 [runbook](/backend/knowledge-cards/runbook/) 與 [incident timeline](/backend/knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：把郵件系統納入高風險資產修補路由。
- 日常：追蹤異常 web shell 與命令執行行為。
- 事故中：執行修補、清查、憑證輪替與重建驗證。
- mechanism 總綱：邊界事件的核心是讓「漏洞修補」「會話 / 憑證失效」「異常痕跡清查」三件事同步發生、不分先後留下時間窗口（前提是事先有 inventory + 自動化失效 / 清查能力）。

## 從本案例到實作的 chain

本案例是事故敘事 layer，沿三步 chain 進入 implementation：

- **控制面**：[7.3 入口與伺服端保護](/backend/07-security-data-protection/entrypoint-and-server-protection/) + [7.12 偵測涵蓋與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) —— mitigation 的 mechanism / 前提 / context-dependence 在這裡定義。
- **演練 / 控制落地**：[Edge session hijack game day](/backend/07-security-data-protection/blue-team/materials/scenarios/edge-session-hijack-game-day/) + [Vulnerability response pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/vulnerability-response-pattern/) + [Evidence chain pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/evidence-chain-pattern/) —— 把樣式轉成邊界演練、漏洞處理與證據鏈欄位。
- **跨章交接**：[backend/05-deployment-platform](/backend/05-deployment-platform/) 的邊界部署治理、[backend/08-incident-response](/backend/08-incident-response/) 的調查與回復步驟。

本案例屬於邊界 / 入口漏洞類別、不對應紅隊 problem-cards（後者集中於 tenant flow / identity flow），主要 chain 直接從控制面起步。


## 來源

| 來源                                                                                                                      | 類型      | 可引用範圍                     |
| ------------------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------ |
| [microsoft.com](https://www.microsoft.com/en-us/msrc/blog/2021/03/multiple-security-updates-released-for-exchange-server) | 官方      | 受影響版本、漏洞細節、修補節奏 |
| [cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa21-062a)                                           | 政府/監管 | 受影響範圍、跨機構處置建議     |
| [nvd.nist.gov/CVE-2021-26855](https://nvd.nist.gov/vuln/detail/CVE-2021-26855)                                            | 技術分析  | CVE 細節、利用機制             |
| [nvd.nist.gov/CVE-2021-27065](https://nvd.nist.gov/vuln/detail/CVE-2021-27065)                                            | 技術分析  | CVE 細節、利用機制             |
