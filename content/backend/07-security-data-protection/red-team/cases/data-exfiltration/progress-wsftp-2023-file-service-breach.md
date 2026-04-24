---
title: "7.R7.4.6 Progress WS_FTP 2023：檔案服務入口與資料外送"
date: 2026-04-24
description: "對外檔案服務漏洞在企業環境常直接轉為資料外送風險"
weight: 71746
---

## 事故摘要

WS_FTP 2023 事件顯示對外檔案服務漏洞能快速變成資料外送事件，並帶來長尾調查壓力。

## 攻擊路徑

1. 掃描可達的 WS_FTP 服務。
2. 利用漏洞取得檔案存取能力。
3. 批量下載或外送高價值資料。

## 失效控制面

- 對外檔案服務缺少最小暴露策略。
- 檔案下載異常偵測覆蓋不足。
- 事件時封鎖與保全流程節奏不足。

## 如果 workflow 少一步會發生什麼

若少了「異常外送即時封鎖」步驟，攻擊者可在同一窗口擴大資料外送規模。

## 可落地的 workflow 檢查點

- 發布前：將檔案服務納入獨立網段與存取白名單。
- 日常：對大批量下載建立 [alert runbook](../../../../../knowledge-cards/alert-runbook/)。
- 事故中：先封鎖外送路徑，再啟動調查與通知流程。

## 可引用章節

- `backend/07-security-data-protection` 的資料外送控制
- `backend/08-incident-response` 的通報與追蹤

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[progress.com](https://www.progress.com/trust-center/security-advisory/ws_ftp-server)
- 政府或監管：[cisa.gov](https://www.cisa.gov/known-exploited-vulnerabilities-catalog?field_cve=CVE-2023-40044)
- 技術分析：[nvd.nist.gov/CVE-2023-40044](https://nvd.nist.gov/vuln/detail/CVE-2023-40044)
