---
title: "7.R7.3.2 Ivanti 2024：CVE-2023-46805/2024-21887 VPN 邊界漏洞鏈"
date: 2026-04-24
description: "多漏洞串接下，邊界設備事件如何轉為持續控制風險"
weight: 71732
---

## 事故摘要

2024 年初，Ivanti Connect Secure 相關公告顯示攻擊者可串接 CVE-2023-46805 與 CVE-2024-21887 進行認證繞過與遠端執行，並帶來持久化風險。

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

- 共同基線：以 [runbook](../../../../../knowledge-cards/runbook/) 與 [incident timeline](../../../../../knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：高風險邊界設備準備替代路徑。
- 日常：建立邊界設備健康與變更基線。
- 事故中：執行隔離、重建、憑證輪替三段流程。

## 可引用章節

- `backend/06-reliability` 的可用性與替代路徑
- `backend/08-incident-response` 的隔離與回復流程

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[ivanti.com](https://www.ivanti.com/blog/security-update-for-ivanti-connect-secure-and-ivanti-policy-secure-gateways)
- 政府或監管：[cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa24-060b)
- 技術分析：[nvd.nist.gov/CVE-2023-46805](https://nvd.nist.gov/vuln/detail/CVE-2023-46805)
- 技術分析：[nvd.nist.gov/CVE-2024-21887](https://nvd.nist.gov/vuln/detail/CVE-2024-21887)
