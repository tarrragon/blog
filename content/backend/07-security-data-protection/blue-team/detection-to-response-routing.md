---
title: "7.B2 從偵測到回應的路由"
tags: ["Blue Team", "Detection", "Response Routing", "Triage"]
date: 2026-04-30
description: "建立資安偵測訊號如何轉成 triage、severity、升級與 incident workflow 的大綱"
weight: 722
---

本篇的責任是把資安偵測訊號轉成回應路由。讀者讀完後，能把 alert、tripwire、audit signal 或外部通報，轉成 triage、severity、owner 與升級流程。

## 核心論點

偵測到回應路由的核心概念是「訊號要能推動決策」。偵測本身提供觀察，回應路由則定義誰判讀、如何分級、何時升級、何時關閉。

## 讀者入口

本篇適合銜接 [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)、[7.14 資安治理例外與 Tripwire](/backend/07-security-data-protection/security-governance-exception-and-tripwire/) 與 [Escalation Policy](/backend/knowledge-cards/escalation-policy/)。

## 路由欄位

| 欄位            | 責任                   | 常見來源                               |
| --------------- | ---------------------- | -------------------------------------- |
| Signal          | 描述觸發事件與觀察證據 | alert、audit log、external advisory    |
| Triage question | 定義第一輪判讀問題     | 影響範圍、可信度、緊急度               |
| Severity        | 對應產品影響與回應節奏 | incident severity                      |
| Owner           | 定義接手角色與升級路徑 | on-call、service owner、security owner |
| Exit condition  | 定義本輪回應的關閉條件 | containment、validation、write-back    |

路由欄位的核心是把訊號轉成可執行任務。若欄位完整，團隊在壓力下仍能用一致方式判讀與升級。

## 訊號分類

訊號分類的責任是建立優先順序。建議先區分三種來源：

1. 技術訊號：監控、掃描、驗證結果。
2. 流程訊號：例外到期、審查延遲、關卡失敗。
3. 外部訊號：公開漏洞、供應鏈公告、客戶通報。

## Triage 問題設計

Triage 問題的責任是縮短第一輪決策時間。常用問題包含：

1. 影響範圍是否持續擴大。
2. 訊號可信度是否足夠觸發升級。
3. 目前證據是否支持 containment。
4. 目前事件是否需要跨團隊決策。

## Severity 對齊

Severity 對齊的責任是讓資安訊號與 incident 節奏一致。這一層建議直接掛到 [incident severity](/backend/knowledge-cards/incident-severity/) 與 [escalation policy](/backend/knowledge-cards/escalation-policy/)。

做法上可先定義分級規則，再為每個分級綁定 owner、通訊節奏與關閉條件。

## Response 路由

Response 路由的責任是把分級後動作排成流程。建議最小流程：

1. Containment：先穩定影響面。
2. Evidence collection：同步保留關鍵證據。
3. Communication：同步內外部利害關係人。
4. Write-back plan：預留回寫任務入口。

## Exit 與回寫

Exit 的責任是定義這輪事件何時完成。關閉前應確認：

1. 影響面收斂到目標範圍。
2. 事件證據可回查。
3. 後續任務已進入問題卡與 workflow。

回寫位置建議固定到 detection rule、problem card 與 incident workflow，讓下一輪判讀更快收斂。

## 判讀訊號與路由

| 判讀訊號                       | 代表需求               | 下一步路由  |
| ------------------------------ | ---------------------- | ----------- |
| 告警名稱清楚但處理者判讀不一致 | 需要 triage question   | 7.B2 → 08   |
| tripwire 觸發後缺少升級對象    | 需要 escalation route  | 7.B2 → 7.14 |
| 外部公告進來後影響範圍判斷緩慢 | 需要 service owner map | 7.B2 → 7.B1 |
| 回應結束後偵測規則沒有更新     | 需要 write-back loop   | 7.B2 → 7.16 |

判讀表格可以直接當作值班檢查單。每次事件結束後重新掃一次，能快速找到下輪優先補強項目。

## 必連章節

- [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- [7.14 資安治理例外與 Tripwire](/backend/07-security-data-protection/security-governance-exception-and-tripwire/)
- [7.16 從公開事故到工程 Workflow](/backend/07-security-data-protection/incident-case-to-control-workflow/)
- [7.B1 防守控制面地圖](/backend/07-security-data-protection/blue-team/defense-control-map/)

## 完稿判準

完稿時要讓讀者能把一個偵測訊號寫成回應路由。路由至少包含 signal、triage question、severity、owner、escalation path、exit condition 與 write-back target。
