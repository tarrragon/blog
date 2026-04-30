---
title: "Low-frequency Exfiltration Tabletop"
tags: ["Blue Team", "Scenario", "Data Exfiltration", "Tabletop"]
date: 2026-04-30
description: "以受管檔案傳輸系統外送風險設計資料範圍與通報 tabletop"
weight: 72534
---

本情境的責任是演練低頻資料外送的範圍判讀與通報。它以 [MOVEit 2023 MFT exfiltration case](/backend/07-security-data-protection/blue-team/materials/field-cases/moveit-2023-mft-exfiltration-pressure/) 為來源，轉成通用 MFT 與資料出口 tabletop。

## Scenario Trigger

外部 advisory 指出受管檔案傳輸系統存在已被利用漏洞。內部稽核發現 MFT 上有異常 web shell indicator 與多筆低頻大量下載。

## Initial Hypothesis

| 假設                 | 驗證資料                                            |
| -------------------- | --------------------------------------------------- |
| MFT 被植入 web shell | file integrity、web access log、IOC                 |
| 特定資料集已被外送   | download log、object access、database audit         |
| 通報義務已被觸發     | data classification、customer mapping、legal review |

## Control Surface

控制面包含 data classification、MFT ownership、audit trail、incident communication、forensic preserve 與 [retention](/backend/knowledge-cards/retention/)。

## Response Route

1. Contain：隔離 MFT、保留 forensic image、暫停高風險傳輸。
2. Scope：建立資料集、客戶、時間窗與存取主體映射。
3. Notify：讓 legal、customer success 與 incident commander 對齊通報節奏。
4. Recover：修補 MFT、輪替 credential、驗證 log coverage。
5. Write-back：更新資料出口控制、retention 與 low-frequency exfiltration detection。

## Evidence Target

| 證據                     | 用途               |
| ------------------------ | ------------------ |
| MFT access log           | 判斷資料外送時間窗 |
| data classification map  | 判斷通報與影響等級 |
| customer mapping         | 判斷受影響對象     |
| forensic preserve record | 支撐調查與法務回查 |

## Write-back Target

- [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)
- [7.24 資安事故如何回寫產品與架構](/backend/07-security-data-protection/security-incident-write-back-to-product-and-architecture/)
- [Evidence chain pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/evidence-chain-pattern/)
- [Exercise write-back pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/exercise-write-back-pattern/)
