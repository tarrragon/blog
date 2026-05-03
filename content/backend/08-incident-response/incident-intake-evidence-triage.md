---
title: "8.18 Incident Intake & Evidence Triage"
date: 2026-05-02
description: "把告警、客訴、支援回報與第三方狀態轉成同一個 intake / evidence 判讀流程"
weight: 18
---

## 大綱

- intake 的責任：把不同來源的異常輸入轉成可判讀的事故候選
- 來源類型：[alert](/backend/knowledge-cards/alert/)、customer ticket、support escalation、status page、vendor notice、security signal
- evidence 類型：log、metric、trace、audit log、customer report、vendor status、deployment event
- triage 欄位：time, source, impact, scope, confidence, owner, next action
- 分級前判讀：是否真實、是否擴大、是否影響用戶、是否需要 incident commander
- 跟 04 的交接：訊號品質與 evidence availability
- 跟 07 的交接：security evidence 與 audit chain
- 反模式：每個入口各自處理；客訴早於告警但沒有進 incident flow；vendor notice 無 owner

Incident intake & evidence triage 的價值是把「來源混亂」轉成「判讀一致」。事故入口天然分散，共用 intake 欄位能讓團隊把時間集中在判斷影響與處置優先序。

## 概念定位

Incident intake & evidence triage 是事故流程的入口，責任是把異常來源轉成可分級、可指派、可追蹤的事故候選。

這一頁處理的是事故啟動前的資料整理。事故不一定從 alert 開始，也可能從客訴、支援、第三方狀態或資安訊號開始；intake 讓這些來源使用同一組判讀欄位。

這層的關鍵是資料可路由。只要 intake 能快速回答「來源可信度」「初步影響範圍」「下一步 owner」，事故分級就能提早進入可執行節奏。

## 核心判讀

判讀 incident intake 時，先看輸入是否有 evidence，再看 evidence 是否足以支持分級與指派。

重點訊號包括：

- source 是否可追溯且時間戳穩定
- impact scope 是否能初步估計
- evidence 是否能連到 log、metric、trace 或 audit log
- owner 是否能接手下一步查證
- confidence 是否標示為 confirmed、suspected 或 external-only

| Intake 欄位         | 最小可用判準                         | 常見斷點                 |
| ------------------- | ------------------------------------ | ------------------------ |
| Source / Time       | 可追溯來源與一致時間戳               | 多入口時間基準不一致     |
| Impact / Scope      | 至少可估「受影響對象與範圍」         | 只知有問題，不知影響面   |
| Evidence Link       | 可連到 log / metric / trace / status | 證據散落，需要人工補交接 |
| Owner / Next Action | 有接手人與下一步查證動作             | 警報停在通知，無處置     |
| Confidence          | 明確標示確定性等級                   | 分級時反覆確認真偽       |

## 判讀訊號

- 客戶回報已經累積，但 on-call 沒有收到事故候選
- vendor 狀態頁更新後，內部沒有 owner 追蹤影響
- alert 觸發但缺少服務、區域、tenant 或 user impact
- security signal 與 operational signal 各自分流，沒有共同 evidence view
- 分級會議花大量時間確認事故真實性

典型場景是客訴先於平台告警出現，support 知道影響、on-call 只看到局部指標。若 intake 層能把 ticket、RUM、status 與後端訊號合併成同一筆候選事件，IC 可以更早做出正確分級。

## 交接路由

- 04.16 observability readiness：補 intake 所需訊號
- 04.17 telemetry data quality：標示 evidence 資料限制
- 08.1 severity trigger：把 intake 結果轉成分級判斷
- 08.2 incident command roles：指派 IC、scribe 與 owner
- 08.19 incident decision log：保留 intake 假設與證據
- 07.7 audit trail：資安 evidence chain 來源
