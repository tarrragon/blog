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

## 入口來源

Incident intake 的入口來源天然分散。共用 intake 模型的責任是讓不同來源先進同一組欄位，再進 severity trigger、IC 指派與 evidence triage。

| 來源               | 典型訊號                             | Intake 重點                        |
| ------------------ | ------------------------------------ | ---------------------------------- |
| Alert              | burn rate、error rate、latency       | 服務、範圍、runbook、owner         |
| Customer ticket    | 客訴、支援回報、客戶成功團隊         | 受影響帳戶、功能、時間、重現步驟   |
| Vendor notice      | status page、support email、RSS      | 依賴服務、區域、ETA、替代路徑      |
| Security signal    | audit log、SIEM、WAF、IAM alert      | evidence chain、資料風險、分流條件 |
| Deployment event   | deploy、config rollout、feature flag | 變更時間、owner、rollback path     |
| Client-side signal | RUM、synthetic probe、mobile crash   | 用戶感知、region、browser / device |

Alert 適合作為高可信自動入口。它應該帶著 service、severity suggestion、dashboard、runbook 與 owner，讓 on-call 能直接判斷是否啟動 incident。

Customer ticket 適合補足平台盲區。客戶常先看到單一流程失敗、特定 tenant 受影響或前端體驗退化；這類 evidence 需要被轉成 impact scope，並送入事故候選流程。

Vendor notice 適合啟動依賴事故候選。當外部供應商狀態頁更新時，內部仍要判斷自己有哪些功能、客戶與 SLA 被影響，並指定 owner 追蹤替代路徑。

Security signal 適合啟動分流 triage。資安訊號可能需要保護 evidence chain、限制討論頻道、控制對外說法與啟動法規通報，因此 intake 欄位要能標示 security-sensitive。

Deployment event 適合連接近期變更。事故候選如果發生在 deploy、config rollout、migration 或 feature flag 之後，intake 應直接帶出 rollback path 與 change owner。

## Evidence 類型

Evidence triage 的責任是把「我們看到了什麼」和「我們相信到什麼程度」分開。證據可以不足，但限制要被明確標示。

| Evidence 類型    | 判讀價值                    | 常見限制                        |
| ---------------- | --------------------------- | ------------------------------- |
| Log              | 事件細節、request / tenant  | schema drift、drop、PII masking |
| Metric           | 趨勢、SLO、容量、error rate | 聚合過粗、延遲、cardinality cut |
| Trace            | 跨服務路徑與等待點          | sampling、async 斷鏈            |
| Audit log        | 權限、資料、責任鏈          | access restriction、retention   |
| Customer report  | 用戶感知與實際影響          | 主觀描述、時間不精準            |
| Vendor status    | 外部依賴狀態                | ETA 不穩、粒度不符內部功能      |
| Deployment event | 變更與時間線                | owner 缺失、rollout 粒度不清    |

Log evidence 適合回答單一事件發生了什麼。它需要 request id、tenant、region、error class 與 timestamp 才能支援 triage。

Metric evidence 適合回答影響是否擴大。error rate、latency、burn rate、queue lag 與 throughput 能幫 IC 判斷是否升級或縮小範圍。

Trace evidence 適合回答失效在哪個邊界。跨服務 request、queue、worker 與 dependency call 若能串起來，triage 就能更快分辨本地問題與下游問題。

Customer report evidence 適合補足使用者感知。即使 backend 指標尚未超標，客戶回報仍能提供高價值影響訊號，尤其是高價值 tenant 或關鍵功能。

## Triage 流程

Incident intake 的 triage 流程是從異常輸入走到分級候選。流程要快，但每一步都要保留 confidence 與下一步 owner。

1. 建立 intake item，記錄 source、time、summary 與初始 owner。
2. 收集至少一個 evidence link，標示 confirmed、suspected 或 external-only。
3. 初估 impact scope，包括 users、tenant、region、feature 與 duration。
4. 判斷是否需要啟動 severity trigger 或 incident commander。
5. 指定下一步查證、通訊或分流路由。

Confidence 欄位讓團隊在資訊不足時仍能前進。Confirmed 代表已有內部證據支持；suspected 代表有強烈訊號但仍需查證；external-only 代表目前只來自 vendor、customer 或第三方來源。

Impact scope 初估可以粗，但要可更新。第一次 triage 只要能回答「可能影響哪些功能、哪些客戶、是否正在擴大」，就足以支援 severity trigger。

Next action 要具體。好的 next action 會指定 owner、查詢入口、預期回報時間與升級條件，避免 intake 停在通知層。

## 判讀訊號

- 客戶回報已經累積，但 on-call 沒有收到事故候選
- vendor 狀態頁更新後，內部沒有 owner 追蹤影響
- alert 觸發但缺少服務、區域、tenant 或 user impact
- security signal 與 operational signal 各自分流，沒有共同 evidence view
- 分級會議花大量時間確認事故真實性

典型場景是客訴先於平台告警出現，support 知道影響、on-call 只看到局部指標。若 intake 層能把 ticket、RUM、status 與後端訊號合併成同一筆候選事件，IC 可以更早做出正確分級。

## 常見反模式

Incident intake 的反模式通常來自入口分散但欄位不一致。入口分散是現實，欄位一致才是治理重點。

| 反模式                 | 表面現象                         | 修正方向                     |
| ---------------------- | -------------------------------- | ---------------------------- |
| 每個入口各自處理       | alert、support、vendor 各走各的  | 統一 intake 欄位             |
| 客訴停在客服系統       | support 知道影響，on-call 不知道 | ticket 轉 incident candidate |
| Vendor notice 無 owner | 外部狀態更新但內部無人追蹤       | 指定 dependency owner        |
| Evidence 無 confidence | 分級時反覆確認真偽               | 標示 confirmed / suspected   |
| Security signal 混流   | 敏感 evidence 進一般事故頻道     | security-sensitive 分流      |

客訴停在客服系統會延後事故啟動。support ticket 應能轉成 incident candidate，並帶上客戶、功能、時間與重現資訊。

Evidence 缺 confidence 會讓分級會議重複查證同一件事。confidence 的責任是標示當下決策建立在哪個可信度上，證據可以在後續流程持續補強。

## 與 04 和 07 的關係

Incident intake 依賴 04 的 evidence availability。若 log、metric、trace、audit log 或 client-side signal 缺失，intake 需要標示資料限制，並把缺口回寫到 observability readiness 與 telemetry data quality。

Incident intake 也需要 07 的 security evidence 邊界。涉及資料外洩、權限濫用、audit chain 或法規通報的候選事件，應在 intake 階段標示 security-sensitive，讓後續溝通、證據保留與權限控管走正確路由。

## 交接路由

- 04.16 observability readiness：補 intake 所需訊號
- 04.17 telemetry data quality：標示 evidence 資料限制
- 08.1 severity trigger：把 intake 結果轉成分級判斷
- 08.2 incident command roles：指派 IC、scribe 與 owner
- 08.19 incident decision log：保留 intake 假設與證據
- 07.7 audit trail：資安 evidence chain 來源
