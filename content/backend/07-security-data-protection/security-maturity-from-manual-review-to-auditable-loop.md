---
title: "7.20 資安成熟度模型：從人工判斷到可稽核閉環"
tags: ["資安治理", "Maturity Model", "Auditable Loop"]
date: 2026-04-30
description: "建立資安治理成熟度模型的大綱，描述人工判斷、穩定流程、可稽核與自動化閉環"
weight: 90
---

本篇的責任是把模組七整理成可判讀的成熟度模型。讀者讀完後，能判斷團隊目前在人工判斷、穩定流程、可稽核閉環或自動化治理的哪個階段。

## 核心論點

資安成熟度的核心概念是「讓風險決策逐步變得可重複、可驗證、可稽核」。成熟度提升的方向，是把個人經驗轉成團隊流程，再把流程轉成可觀測與可回寫的系統。

## 讀者入口

本篇適合放在模組七收束位置閱讀。它串接 [7.15 資安作為風險路由系統](/backend/07-security-data-protection/security-as-risk-routing-system/)、[7.18 資安控制面如何交接到部署與事故流程](/backend/07-security-data-protection/security-control-handoff-to-delivery-and-incident/) 與 [7.19 資安演練](/backend/07-security-data-protection/security-exercise-from-abuse-case-to-game-day/)。

## 成熟度階梯

成熟度階梯的責任是提供可判讀狀態，協助團隊找到下一個提升路由：

| 階段       | 核心能力             | 可觀察產物                      |
| ---------- | -------------------- | ------------------------------- |
| 人工判斷   | 依靠資深者辨識風險   | review 記錄、口頭決策、零散任務 |
| 穩定流程   | 風險有固定承接路徑   | checklist、owner、runbook       |
| 可稽核閉環 | 決策有證據與回寫位置 | audit log、tripwire、case 回寫  |
| 自動化治理 | 重複判讀可由系統觸發 | release gate、policy、dashboard |

成熟度階梯的價值在於判讀下一步，協助團隊在目前約束下選擇最有回報的提升路徑。每一層都代表一組可持續運作能力。

## 成熟度評估維度

成熟度評估的責任是提供一致觀察面。建議用四個維度判讀：

1. Flow stability：流程是否能在多輪事件中穩定重現。
2. Evidence quality：證據是否支持追溯與驗收。
3. Write-back cadence：案例、流程與控制面更新節奏。
4. Automation coverage：高頻決策是否已由系統觸發。

## 人工判斷階段

人工判斷階段的責任是累積可轉移語言。這一層以資深者判斷為主，重點任務是把零散決策整理成共享術語、路由表與基礎模板。

這一層的核心輸出是「可交接文件」，讓團隊能從口頭經驗走向可重複流程。

## 穩定流程階段

穩定流程階段的責任是建立固定承接路徑。此時可對齊 owner、runbook、release gate 與 incident workflow，讓事件在不同時段都能被一致處理。

這一層的核心輸出是「可執行流程」，讓任務不依賴單一角色記憶。

## 可稽核閉環階段

可稽核閉環階段的責任是建立決策證據鏈。這一層重點是 [audit log](/backend/knowledge-cards/audit-log/)、[tripwire](/backend/knowledge-cards/tripwire/) 與 case-to-workflow 回寫。

這一層的核心輸出是「可驗收改進」，讓每次事件後都能觀察治理能力變化。

## 自動化治理階段

自動化治理階段的責任是把高頻判讀轉成系統能力。此時 release gate、policy、dashboard、alert 可以共同推動重評估與收斂。

這一層的核心輸出是「可持續節奏」，讓治理能力在規模擴張時維持穩定。

## 提升路線圖

成熟度提升建議用小步推進：

1. 先建立路由語言與問題卡片。
2. 再建立 owner、runbook、交接契約。
3. 接著補上 evidence chain 與回寫節奏。
4. 最後把高頻動作轉成系統觸發。

## 判讀訊號與提升路由

| 判讀訊號                       | 目前階段     | 提升路由                      |
| ------------------------------ | ------------ | ----------------------------- |
| 風險判斷依賴少數人經驗         | 人工判斷     | 建立 7.x 路由與 problem cards |
| 控制面已定義但缺少承接流程     | 穩定流程前期 | 建立 7.18 交接契約            |
| 決策有 owner 但缺少證據回寫    | 穩定流程     | 建立 audit trail 與 tripwire  |
| 演練結果能自動推動任務與重評估 | 可稽核閉環   | 建立 dashboard 與 policy gate |

判讀表格的作用是讓團隊在每輪復盤都能快速定位階段，並決定一個最具回報的提升任務。

## 從成熟度判讀到實際 mitigation 強度

成熟度量的是 process metric（流程穩定性 / 證據品質 / 回寫節奏 / 自動化覆蓋）；mitigation 強度要從具體 control 驗證取得。Reader 沿兩條 chain 把 stage 轉成 mitigation 判讀：

- **覆蓋 chain**：列當前 stage 應對的 7.x 章節問題節點（例：可稽核閉環 stage 對應 [7.2 身分擴散](/backend/07-security-data-protection/identity-access-boundary/) / [7.7 證據鏈](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/) / [7.13 訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 主問題節點）；尚未涵蓋的問題節點是當前 stage 仍在的 silent gap。
- **驗證 chain**：用具體事件 / 演練檢查 control 真擋 threat。「有 audit log」是 process metric、「audit log 在事件中能還原責任鏈」是 mitigation 驗證；兩者差距由 [7.19 資安演練](/backend/07-security-data-protection/security-exercise-from-abuse-case-to-game-day/) 量測。

兩條 chain 走完，stage 才轉成可信 mitigation 判讀。Stage 提升跟 mitigation 強度提升是兩件獨立工作——前者擴張組織能力、後者靠下游模組（[05](/backend/05-deployment-platform/) / [06](/backend/06-reliability/) / [08](/backend/08-incident-response/)）真實實作。

## 必連章節

- [7.7 稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)
- [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- [7.15 資安作為風險路由系統](/backend/07-security-data-protection/security-as-risk-routing-system/)
- [7.18 資安控制面如何交接到部署與事故流程](/backend/07-security-data-protection/security-control-handoff-to-delivery-and-incident/)
- [7.19 資安演練：從 Abuse Case 到 Game Day](/backend/07-security-data-protection/security-exercise-from-abuse-case-to-game-day/)

## 完稿判準

完稿時要讓讀者能評估自己團隊的資安治理成熟度。評估結果至少能導出一個下一步：補共享語言、補流程承接、補證據鏈、補自動化觸發或補回寫閉環。
