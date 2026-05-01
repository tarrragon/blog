---
title: "7.R7.4.7 GoAnywhere MFT 2023：傳輸中樞被利用的外送鏈"
date: 2026-04-24
description: "MFT 中樞服務漏洞會把檔案交換流程直接轉成資料外送風險"
weight: 71747
---

## 事故摘要

GoAnywhere MFT 2023 事件顯示檔案傳輸中樞在漏洞事件中會快速演變為資料外送與供應鏈通知壓力。

**本案例的演示焦點**：MFT 中樞 zero-day → 跨組織交換資料批量外送 → 多客戶通報壓力的 file-transfer hub exfiltration。跟 MOVEit 同類別、共同說明 MFT 平台暴露面的 systemic risk。

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

- 共同基線：以 [runbook](/backend/knowledge-cards/runbook/) 與 [incident timeline](/backend/knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：為 MFT 流程建立資料分級與權限分域（依交易對象 / 資料敏感度切 audience），mechanism 是讓單點漏洞不會通到全部交換資料。
- 日常：維護交易追蹤與外送告警指標（單窗口下載量 / 跨 partner 異常 access pattern）。
- 事故中：盤點受影響交易、封鎖傳輸路徑、分層通知利害關係人（前提是事先有 partner contact map）。

## 從本案例到實作的 chain

本案例是事故敘事 layer，沿三步 chain 進入 implementation：

- **控制面**：[7.3 入口與伺服端保護](/backend/07-security-data-protection/entrypoint-and-server-protection/) + [7.9 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/) + [7.10 資料 residency / 刪除與證據鏈](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/) —— mitigation 的 mechanism / 前提 / context-dependence 在這裡定義。
- **演練 / 控制落地**：[Low-frequency exfiltration tabletop](/backend/07-security-data-protection/blue-team/materials/scenarios/low-frequency-exfiltration-tabletop/) + [Vulnerability response pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/vulnerability-response-pattern/) + [Evidence chain pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/evidence-chain-pattern/) —— 把樣式轉成 tabletop、漏洞處理與證據鏈欄位。
- **跨章交接**：[backend/01-database](/backend/01-database/) 的資料分級與治理、[backend/08-incident-response](/backend/08-incident-response/) 的跨組織通報流程。

本案例屬於邊界 zero-day 引發的外送、不對應紅隊 problem-cards，主要 chain 直接從控制面起步。

## 來源

| 來源                                                                                             | 類型      | 可引用範圍                         |
| ------------------------------------------------------------------------------------------------ | --------- | ---------------------------------- |
| [fortra.com](https://www.fortra.com/blog/summary-investigation-related-cve-2023-0669)            | 官方      | 受影響版本、修補時序、調查結果     |
| [cisa.gov](https://www.cisa.gov/known-exploited-vulnerabilities-catalog?field_cve=CVE-2023-0669) | 政府/監管 | KEV 列入、跨機構處置建議           |
| [nvd.nist.gov/CVE-2023-0669](https://nvd.nist.gov/vuln/detail/CVE-2023-0669)                     | 技術分析  | CVE 細節、deserialization RCE 機制 |
