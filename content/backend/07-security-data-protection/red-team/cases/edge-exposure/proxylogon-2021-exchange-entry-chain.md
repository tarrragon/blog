---
title: "7.R7.3.13 ProxyLogon 2021：CVE-2021-26855/27065 入口鏈式失效"
date: 2026-04-24
description: "郵件系統入口漏洞被串接利用時，事件會迅速擴大到內部服務邊界"
weight: 717313
---

## 事故摘要

ProxyLogon 事件顯示 CVE-2021-26855 與 CVE-2021-27065 這類企業郵件系統入口漏洞可被快速批量利用並形成內網風險。

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

- 共同基線：以 [runbook](../../../../knowledge-cards/runbook/) 與 [incident timeline](../../../../knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：把郵件系統納入高風險資產修補路由。
- 日常：追蹤異常 web shell 與命令執行行為。
- 事故中：執行修補、清查、憑證輪替與重建驗證。

## 可引用章節

- `backend/07-security-data-protection` 的郵件與邊界防護
- `backend/08-incident-response` 的調查與回復步驟

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[microsoft.com](https://www.microsoft.com/en-us/msrc/blog/2021/03/multiple-security-updates-released-for-exchange-server)
- 政府或監管：[cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa21-062a)
- 技術分析：[nvd.nist.gov/CVE-2021-26855](https://nvd.nist.gov/vuln/detail/CVE-2021-26855)
- 技術分析：[nvd.nist.gov/CVE-2021-27065](https://nvd.nist.gov/vuln/detail/CVE-2021-27065)
