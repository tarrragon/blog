---
title: "7.B7 Threat-Informed Validation"
tags: ["Blue Team", "Threat-Informed Defense", "Validation", "ATT&CK"]
date: 2026-04-30
description: "用威脅導向方法驗證控制面與偵測能力，建立可重複的防守驗證路徑"
weight: 727
---

本篇的責任是建立 threat-informed validation 路徑。讀者讀完後，能把攻擊行為模型轉成控制面驗證與偵測測試。

## 核心論點

Threat-informed validation 的核心概念是用威脅行為驗證防守能力。防守驗證從「控制是否存在」升級為「控制是否能在對手行為下持續生效」。

## 讀者入口

本篇適合銜接 [7.1 攻擊者視角（紅隊）與攻擊面驗證](/backend/07-security-data-protection/red-team/)、[7.B3 資安控制驗證](/backend/07-security-data-protection/blue-team/security-control-validation/) 與 [MITRE ATT&CK Evaluations](/backend/07-security-data-protection/blue-team/materials/professional-sources/mitre-attack-evaluations-threat-informed-validation/)。

## 驗證流程

| 步驟             | 責任                        | 產出            |
| ---------------- | --------------------------- | --------------- |
| Threat selection | 選擇要驗證的攻擊行為        | threat scenario |
| Control mapping  | 對應控制面與偵測規則        | control map     |
| Emulation design | 設計可重複測試流程          | exercise script |
| Signal check     | 檢查告警、分級與交接        | signal evidence |
| Decision review  | 審查 containment 與回應判讀 | response review |
| Write-back       | 回寫規則、runbook、章節     | backlog updates |

## Threat 選型

Threat 選型的責任是聚焦高風險路徑。選型可優先對準 identity abuse、edge exposure、supply chain tampering 與 data exfiltration。

## 控制映射

控制映射的責任是把威脅行為接到服務控制面。每個威脅情境都需要標示 identity、entrypoint、data、supply chain、detection 與 governance 的責任邊界。

## 驗證證據

驗證證據的責任是讓測試結果可比較。常見證據包含規則命中率、triage 時間、誤報率、containment 完成時間與回寫完成率。

## 失配修正

失配修正的責任是讓驗證結果轉成改進行動。當控制面與行為模型失配時，修正可以落在規則調校、流程補強或控制新增，並同步更新 release gate 與 runbook。

## 判讀訊號與路由

| 判讀訊號                 | 代表需求             | 下一步路由  |
| ------------------------ | -------------------- | ----------- |
| 控制存在但測試命中率低   | 需要重整映射與規則   | 7.B7 → 7.B5 |
| 測試命中後交接速度慢     | 需要優化 triage loop | 7.B7 → 7.B6 |
| 測試結果只記錄成功與失敗 | 需要補 evidence 指標 | 7.B7 → 7.B3 |
| 高風險行為未納入演練     | 需要擴充 scenario 庫 | 7.B7 → 7.B9 |

## 必連章節

- [7.B3 資安控制驗證](/backend/07-security-data-protection/blue-team/security-control-validation/)
- [7.B5 Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)
- [7.B6 Incident Triage Loop](/backend/07-security-data-protection/blue-team/incident-triage-loop/)
- [7.B9 Blue Team Scenario Library](/backend/07-security-data-protection/blue-team/blue-team-scenario-library/)

## 完稿判準

完稿時要讓讀者能把一個威脅路徑轉成驗證方案。輸出至少包含威脅選型、控制映射、測試設計、證據欄位、修正路由與回寫位置。
