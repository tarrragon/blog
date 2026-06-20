---
title: "動機驅動的事件設計"
date: 2026-06-20
description: "Debug / 商業 / 資安 / 效能四個動機各自需要什麼事件 — 從「為什麼收」反推「收什麼」和「什麼階段啟用」"
weight: 6
tags: ["monitoring", "mental-model", "event-design", "motivation", "debug", "security", "analytics"]
---

事件設計是三維結構：動機（為什麼收）決定需要什麼事件、感測器（怎麼收）決定在前端哪裡埋點、生命週期（什麼時候收）決定各事件在哪個產品階段啟用。從動機出發反推事件清單，比從技術能力出發（「SDK 能收什麼就收什麼」）更精準 — 每個事件都能回指一個具體的消費場景。

## Debug 動機

Debug 動機驅動的事件收集目標是「問題發生時、開發者能從事件記錄中重建 context 並定位根因」。

### 要偵測的行為

- 多步驟流程的每一步完成或失敗（連線 → 認證 → 資料交換）
- 系統狀態轉換（前景/背景、連線/斷線、登入/登出）
- 非預期例外（uncaught exception、network error、timeout）
- 使用者最近的操作序列（問題發生前做了什麼）

### 事件表

| 事件名稱                        | 類型      | 觸發時機           | data schema 重點                |
| ------------------------------- | --------- | ------------------ | ------------------------------- |
| {feature}.step.done             | lifecycle | 流程步驟完成       | step_name, duration_ms          |
| {feature}.step.failed           | error     | 流程步驟失敗       | step_name, error, context       |
| app.exception                   | error     | uncaught exception | message, stack_trace, component |
| ws.connected / ws.disconnected  | lifecycle | 連線狀態變化       | url, reason, code               |
| app.foreground / app.background | lifecycle | app 前後景切換     | duration_in_background          |
| {action}.completed              | event     | 使用者完成操作     | action_detail                   |

### 查詢場景

**Session 回放**：按 session_id 過濾、按時間排序，還原「使用者做了什麼 → 系統發生了什麼 → 問題在哪裡出現」。

**Error 根因定位**：按 error name GROUP BY，找出最常出現的錯誤。單筆 error 的 stack_trace + 同 session 的 lifecycle 事件組合，判斷失敗發生在流程的哪一步。

**最近 N 個操作**：error 發生前的 10-20 個 event/lifecycle 事件，等同 Sentry 的 breadcrumb trail。

### 生命週期階段

開發期起全開。Debug 事件是最早需要的 — 實機測試階段就依賴這些事件定位問題。error 類和 lifecycle 類不做取樣（量低且每筆都可能是線索）。

## 商業動機

商業動機驅動的事件收集目標是「回答產品決策的問題 — 使用者在哪裡流失、不同群組行為有什麼差異、哪些功能被使用」。

### 要偵測的行為

- 漏斗步驟完成（註冊 → 啟用 → 付費 → 續約的每一步）
- 功能使用頻率（哪些功能被頻繁使用、哪些從未被觸發）
- Session 長度和頻率（使用者多常用、每次用多久）
- 關鍵轉換事件（首次付費、邀請好友、升級方案）

### 事件表

| 事件名稱                    | 類型      | 觸發時機           | data schema 重點       |
| --------------------------- | --------- | ------------------ | ---------------------- |
| funnel.{name}.step_N        | event     | 漏斗步驟完成       | step_name, funnel_name |
| feature.{name}.used         | event     | 使用者使用特定功能 | feature_name, context  |
| session.start / session.end | lifecycle | session 邊界       | session_duration       |
| conversion.{type}           | event     | 關鍵轉換           | conversion_type, value |

### 查詢場景

**Funnel 轉換率**：每步的完成數 / 上一步的完成數。SQLite 層做每步計數，PostgreSQL 層做 session 級 JOIN 的精確轉換率（見 [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)）。

**Cohort 留存**：按「首次使用週」分群，計算每週的回訪率。需要 session.start 事件 + 使用者首次出現的時間戳。

**功能使用率**：feature.*.used 事件按 name GROUP BY COUNT，排序找出最常/最少使用的功能。

### 生命週期階段

上線後啟用。開發期不需要商業事件（沒有真實使用者）。測試期可以用模擬流量驗證 funnel 事件的觸發正確性，但不做分析。

## 資安動機

資安動機驅動的事件收集目標是「偵測非預期的存取模式、追蹤敏感操作、提供事後稽核的 audit trail」。

### 要偵測的行為

- 認證失敗（密碼錯誤、biometric 失敗、token 過期）
- 權限越界嘗試（嘗試存取非自己的資源、呼叫無權限的 API）
- 敏感資料存取（查看個資、匯出資料、修改權限設定）
- 異常存取模式（短時間大量請求、非常規時段存取、來源 IP 變化）

### 事件表

| 事件名稱              | 類型  | 觸發時機       | data schema 重點                            |
| --------------------- | ----- | -------------- | ------------------------------------------- |
| auth.{method}.failed  | error | 認證失敗       | method, failure_reason, attempt_count       |
| auth.{method}.success | event | 認證成功       | method, duration_ms                         |
| authz.denied          | error | 權限檢查拒絕   | resource, action, role                      |
| sensitive.accessed    | event | 敏感資料被存取 | resource_type, accessor_role                |
| sensitive.exported    | event | 資料被匯出     | export_format, record_count                 |
| admin.setting.changed | event | 管理設定變更   | setting_key, old_value_hash, new_value_hash |

### 查詢場景

**認證失敗監控**：auth.*.failed 事件的 count by session_id，短時間內同一 session 多次失敗 → 暴力破解嫌疑。Rule engine 設閾值告警。

**Audit trail**：sensitive.* 和 admin.* 事件按時間排列，回答「誰在什麼時候存取/修改了什麼」。合規審計的必要紀錄。

**異常 pattern 偵測**：auth 成功後的操作事件頻率和模式分析。正常使用者每 session 操作 10-50 次；自動化腳本可能操作數千次。

### 生命週期階段

開發期起全開。安全事件不能延後 — 「先不收安全事件、上線後再加」等於安全審計的空白期。認證相關事件是 auto-intercept 的一部分（見 [自動攔截機制](/monitoring/03-sdk-design/auto-intercept/)），不需要手動埋點。

### 和 redaction 的關係

資安事件本身可能包含敏感資訊（失敗的密碼、被存取的個資欄位名稱）。事件的 data schema 設計時標記需要 [redaction](/monitoring/knowledge-cards/redaction/) 的欄位 — auth.failed 記錄失敗原因但不記錄輸入的密碼、sensitive.accessed 記錄資源類型但不記錄資源內容。

## 效能動機

效能動機驅動的事件收集目標是「發現效能退化趨勢、定位效能瓶頸、為容量規劃提供數據」。

### 要偵測的行為

- 操作回應時間（API 呼叫、頁面載入、動畫轉場）
- 渲染效能（frame rate、長任務、佈局重排）
- 資源使用（記憶體、CPU、網路流量）
- 外部依賴延遲（第三方 API、CDN、資料庫查詢）

### 事件表

| 事件名稱                  | 類型   | 觸發時機        | data schema 重點                    |
| ------------------------- | ------ | --------------- | ----------------------------------- |
| {operation}.duration      | metric | 操作完成        | duration_ms, operation_name         |
| render.frame_drop         | metric | 掉幀偵測        | dropped_frames, total_frames        |
| resource.memory           | metric | 定期取樣（30s） | heap_used, heap_total               |
| dependency.{name}.latency | metric | 外部呼叫完成    | dependency_name, latency_ms, status |
| web.vitals                | metric | Web 頁面載入    | lcp_ms, fid_ms, cls_score           |

### 查詢場景

**P95 趨勢**：{operation}.duration 事件按天聚合、計算 percentile_cont(0.95)，觀察回應時間是否隨版本增加。

**容量規劃**：resource.memory 事件的趨勢圖，判斷記憶體是否隨使用時間穩定增長（memory leak 訊號）。

**依賴健康度**：dependency.*.latency 事件按 dependency_name GROUP BY，比較各依賴的平均延遲和失敗率。

### 生命週期階段

測試期起啟用。開發期不需要效能事件（本地環境的效能數據不代表 production）。測試期啟用用於建立效能 baseline。上線後持續收集用於趨勢監控。

效能事件量通常最大（每 30 秒一筆 resource.memory × 活躍使用者數），取樣率需要控制 — 自用場景全收、商業產品取樣 10-50%（見 [前端感測器設計](/monitoring/03-sdk-design/frontend-sensor-design/) 的取樣策略段）。

## A/B 測試動機

A/B 測試動機驅動的事件是商業動機的延伸 — 實驗期間收集實驗分組和轉換事件，實驗結束後關閉。

### 事件表

| 事件名稱                    | 類型  | 觸發時機             | data schema 重點                          |
| --------------------------- | ----- | -------------------- | ----------------------------------------- |
| experiment.{name}.assigned  | event | 使用者被分配到實驗組 | experiment_name, variant                  |
| experiment.{name}.converted | event | 使用者完成轉換目標   | experiment_name, variant, conversion_type |

### 生命週期階段

實驗期間啟用，實驗結束後關閉（從 SDK config 或 feature flag 移除）。實驗事件的保留期限跟著實驗週期走 — 實驗結束 + 分析完成後可清除。A/B test 的統計分析見 [A/B test 的統計基礎](/monitoring/08-business-analytics/ab-test-statistics/)。

## 完整對照總表

| 動機  | 要偵測的行為      | 事件名稱模式                | 感測器類型     | 生命週期啟用 | 查詢模式         | 保留層級     |
| ----- | ----------------- | --------------------------- | -------------- | ------------ | ---------------- | ------------ |
| Debug | 流程步驟完成/失敗 | {feature}.step.*            | auto-intercept | 開發期起     | session 回放     | 原始 7d      |
| Debug | 例外拋出          | app.exception               | auto-intercept | 開發期起     | error GROUP BY   | 原始 30d     |
| Debug | 連線狀態          | ws.connected/disconnected   | auto-intercept | 開發期起     | session 回放     | 原始 7d      |
| Debug | 最近操作          | {action}.completed          | 手動埋點       | 開發期起     | breadcrumb trail | 原始 7d      |
| 商業  | 漏斗步驟          | funnel.{name}.step_N        | 手動埋點       | 上線後       | funnel JOIN      | 小時聚合 90d |
| 商業  | 功能使用          | feature.{name}.used         | 手動埋點       | 上線後       | COUNT GROUP BY   | 天聚合 365d  |
| 商業  | Session           | session.start/end           | auto-intercept | 上線後       | cohort 留存      | 天聚合 365d  |
| 商業  | 轉換              | conversion.{type}           | 手動埋點       | 上線後       | funnel 最後一步  | 原始 90d     |
| 資安  | 認證失敗          | auth.{method}.failed        | auto-intercept | 開發期起     | 閾值告警         | 原始 30d     |
| 資安  | 權限拒絕          | authz.denied                | auto-intercept | 開發期起     | pattern 偵測     | 原始 30d     |
| 資安  | 敏感存取          | sensitive.*                 | 手動埋點       | 開發期起     | audit trail      | 原始 365d    |
| 資安  | 設定變更          | admin.setting.changed       | 手動埋點       | 開發期起     | audit trail      | 原始 365d    |
| 效能  | 操作延遲          | {operation}.duration        | 手動埋點       | 測試期起     | P95 趨勢         | 小時聚合 90d |
| 效能  | 渲染效能          | render.frame_drop           | auto-intercept | 測試期起     | 趨勢圖           | 小時聚合 90d |
| 效能  | 資源用量          | resource.memory             | 定期取樣       | 測試期起     | 趨勢圖           | 小時聚合 90d |
| 效能  | 外部依賴          | dependency.{name}.latency   | 手動埋點       | 測試期起     | GROUP BY 依賴    | 小時聚合 90d |
| 效能  | Web Vitals        | web.vitals                  | auto-intercept | 測試期起     | 趨勢圖           | 小時聚合 90d |
| A/B   | 實驗分組          | experiment.{name}.assigned  | 手動埋點       | 實驗期間     | variant GROUP BY | 實驗結束後清 |
| A/B   | 實驗轉換          | experiment.{name}.converted | 手動埋點       | 實驗期間     | 轉換率計算       | 實驗結束後清 |

## 下一步路由

- 四類事件的基礎定義 → [四類事件的完整定義](/monitoring/01-mental-model/four-event-types/)
- 事件枚舉的方法論 → [事件枚舉與補齊檢查](/monitoring/01-mental-model/event-enumeration-method/)
- 前端感測器的具體設計 → [前端感測器設計](/monitoring/03-sdk-design/frontend-sensor-design/)
- 感測器的生命週期控制 → [感測器生命週期管理](/monitoring/03-sdk-design/sensor-lifecycle-management/)
- 查詢消費模式的完整展開 → [查詢消費模式](/monitoring/04-collector/query-consumption-patterns/)
