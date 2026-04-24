---
title: "7.R7.4.7 GoAnywhere MFT 2023：傳輸中樞被利用的外送鏈"
date: 2026-04-24
description: "MFT 中樞服務漏洞會把檔案交換流程直接轉成資料外送風險"
weight: 71747
---

## 事故摘要

GoAnywhere MFT 2023 事件顯示檔案傳輸中樞在漏洞事件中會快速演變為資料外送與供應鏈通知壓力。

## 攻擊路徑

1. 鎖定可達 MFT 入口。
2. 利用漏洞取得傳輸系統存取能力。
3. 搜集並外送跨組織交換資料。

## 失效控制面

- 傳輸中樞缺少入口隔離與最小授權。
- 傳輸行為與資料分級未有效關聯。
- 事件中跨組織通報流程準備不足。

## 如果 workflow 少一步會發生什麼

若少了「受影響交易清單快速盤點」步驟，團隊會延後通知與修復決策，擴大業務衝擊。

## 可落地的 workflow 檢查點

- 共同基線：以 [runbook](../../../../knowledge-cards/runbook/) 與 [incident timeline](../../../../knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：為 MFT 流程建立資料分級與權限分域。
- 日常：維護交易追蹤與外送告警指標。
- 事故中：盤點受影響交易、封鎖傳輸路徑、分層通知利害關係人。

## 可引用章節

- `backend/01-database` 的資料分級與治理
- `backend/08-incident-response` 的跨組織通報流程

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[fortra.com](https://www.fortra.com/blog/summary-investigation-related-cve-2023-0669)
- 政府或監管：[cisa.gov](https://www.cisa.gov/known-exploited-vulnerabilities-catalog?field_cve=CVE-2023-0669)
- 技術分析：[nvd.nist.gov/CVE-2023-0669](https://nvd.nist.gov/vuln/detail/CVE-2023-0669)
