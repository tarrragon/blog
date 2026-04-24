---
title: "7.R7.3.1 MOVEit 2023：外網檔案服務批量外送"
date: 2026-04-24
description: "MFT 對外入口在零時差事件中如何被批量利用"
weight: 71731
---

## 事故摘要

2023 年 5 到 6 月，MOVEit Transfer 事件顯示，對外檔案傳輸服務在漏洞公開後可被快速批量利用並造成資料外送。

## 攻擊路徑

1. 掃描外網可達 MFT 入口。
2. 利用漏洞取得存取能力。
3. 蒐集與外送高價值資料。

## 失效控制面

- 對外入口缺少最小暴露設計。
- 漏洞修補與隔離流程慢於攻擊自動化。
- 外送行為偵測粒度不足。

## 如果 workflow 少一步會發生什麼

若缺少「漏洞公告即觸發入口隔離」流程，等待正式修補期間仍會被持續掃描與利用。

## 可落地的 workflow 檢查點

- 共同基線：以 [runbook](../../../../knowledge-cards/runbook/) 與 [incident timeline](../../../../knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：對外服務建立即時隔離開關。
- 日常：監控大批量匯出與異常下載模式。
- 事故中：先隔離入口，再做修補與回復。

## 可引用章節

- `backend/05-deployment-platform` 的邊界流量控制
- `backend/08-incident-response` 的止血優先序

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：https://www.progress.com/trust-center/moveit-transfer-and-moveit-cloud-vulnerability
- 政府或監管：https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-158a
- 技術分析：https://nvd.nist.gov/vuln/detail/CVE-2023-34362
