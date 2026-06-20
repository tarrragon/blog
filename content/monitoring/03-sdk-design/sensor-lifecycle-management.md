---
title: "感測器生命週期管理"
date: 2026-06-20
description: "產品生命週期的五個階段各啟用什麼感測器 — feature flag 整合、取樣率動態調整、感測器開關的可觀察性"
weight: 7
tags: ["monitoring", "sdk-design", "sensor", "lifecycle", "feature-flag", "sampling"]
---

感測器的啟用組合隨產品階段變化。早期開發只需要 error 和 lifecycle 幫助 debug，production 上線後需要商業事件和效能量測，A/B 測試期間需要實驗專用感測器。把所有感測器一次全開會浪費頻寬和儲存、產生大量低價值事件；全程只開 error 則在需要行為分析時發現沒有資料。感測器的啟停是設計決策，由 SDK config、collector 下發和 feature flag 三層機制控制。

## 五個階段

### 早期開發

開發期的首要需求是 debug — 程式碼寫完跑起來、出問題時能定位。

| 感測器類型 | 啟用 | 理由                               |
| ---------- | ---- | ---------------------------------- |
| error      | 全開 | 每個例外都要看到                   |
| lifecycle  | 全開 | app 啟動、連線、狀態轉換的步驟紀錄 |
| event      | 按需 | 正在開發的功能手動加埋點，其他關閉 |
| metric     | 關閉 | 效能量測在功能穩定前沒有意義       |

開發期的取樣率全部設 1.0（全收）— 事件量極低（開發者自己操作），不需要取樣。

### 功能測試

針對被測功能開啟完整感測器，驗證功能的行為事件和效能指標是否正確觸發。

被測功能的 event 和 metric 全開。其他功能維持開發期設定。測試期間的感測器設定通常由測試 config 檔覆寫 SDK 預設值。

### Production 上線

上線後的感測器組合平衡覆蓋率和成本：

| 感測器類型        | 策略 | 理由                                           |
| ----------------- | ---- | ---------------------------------------------- |
| error             | 全收 | 每個 production error 都有 debug 價值          |
| lifecycle         | 全收 | session 分析和環境資訊需要完整紀錄             |
| event（核心操作） | 全收 | 漏斗關鍵步驟、轉換事件不能漏                   |
| event（高頻 UI）  | 取樣 | scroll、mousemove、hover 等高頻操作只取部分    |
| metric            | 取樣 | 效能指標按時間取樣（每 30 秒一次而非每 frame） |
| 安全事件          | 全收 | auth 失敗、權限越界、敏感操作不取樣            |

### A/B 測試

實驗感測器只對 treatment group 啟用。Control group 不觸發實驗事件，避免污染對照組資料。

實驗專用事件（`experiment.pricing_test.assigned`、`experiment.pricing_test.converted`）由 feature flag 控制 — flag 開啟時 SDK 才送這些事件。實驗結束後 flag 關閉，感測器自動停止。

實驗事件的保留期和實驗週期綁定，實驗結束 + 分析完成後可以 purge。

### 功能下線

功能移除時，對應的感測器 config 一起移除。Collector 端 purge 該功能的歷史事件（或降級到聚合摘要）。

移除 checklist：SDK config 移除事件名稱 → SDK 版本部署 → 確認 collector 不再收到該事件 → purge 歷史資料（可選）。

## 控制機制

三層控制機制各自適合不同的變更頻率：

### SDK init config（靜態）

隨 app 版本部署的本地設定檔。變更需要發新版本。適合穩定的感測器組合。

```yaml
sensors:
  error: { enabled: true, sampling: 1.0 }
  lifecycle: { enabled: true, sampling: 1.0 }
  event:
    funnel.*: { enabled: true, sampling: 1.0 }
    click.*: { enabled: true, sampling: 0.1 }
  metric:
    duration: { enabled: true, sampling: 0.5 }
  experiment:
    pricing_test: { enabled: false }
```

### Collector 端下發（動態）

SDK 啟動時從 collector 的 `/config` endpoint 拉取當前的感測器設定。Collector 端修改設定後，下一次 SDK 重啟或定期 refresh（每 5 分鐘）時生效。適合需要動態調整但不值得接 feature flag 服務的場景。

### Feature flag 服務整合

SDK 在送出事件前查詢 feature flag 判斷感測器是否啟用。適合 A/B 測試 — flag 可以按使用者 / 百分比 / 條件分群啟用。

### 優先順序

三層控制的覆蓋優先順序：

```text
Feature flag > Collector 下發 > SDK 本地 config
```

SDK 本地 config 是 baseline。Collector 下發覆蓋 baseline 的特定欄位。Feature flag 覆蓋一切 — 即使本地 config 和 collector 都說啟用，flag 說關閉就關閉。

## 取樣率設計

取樣率決定「多少比例的事件會被實際送出」。取樣在 SDK 端執行 — 不送的事件不佔頻寬和儲存。

### 全收（sampling: 1.0）

每筆事件都送。適用於：

- **error**：每個 production error 都有 debug 價值，漏掉的 error 可能是最嚴重的那個
- **安全事件**：auth 失敗、權限越界的取樣可能讓攻擊嘗試隱形
- **漏斗關鍵步驟**：funnel 分析的轉換率計算需要精確的步驟計數

### 百分比取樣（0.01-0.5）

只送一定比例的事件。適用於高頻且個別事件價值低的場景：

- scroll / mousemove / hover：每秒觸發數十次，全收會產生大量事件。取樣 1-10% 足以分析使用者行為模式
- frame rate 量測：每幀一筆 metric 太多，每秒或每 30 秒取一筆足夠

取樣的實作用 SDK 端的隨機數 — `if random() < sampling_rate then send(event)` — 不需要 server 端參與。

### 條件取樣（retrospective full capture）

正常情況取樣，但發生 error 時回溯收集該 session 的全部事件。實作方式是 SDK 在記憶體中保留最近 N 筆事件的環形 buffer，觸發 error 時把 buffer 中的事件一併送出。

條件取樣讓「error session 的上下文完整」和「正常 session 不過度收集」兩個目標共存。

## 感測器開關的可觀察性

感測器本身的狀態變化需要被觀察 — 如果感測器靜默失效（config 錯誤導致某類事件停送），開發者可能很久後才發現「怎麼最近沒有 funnel 資料」。

### 啟動時 log 感測器清單

SDK 初始化完成時 log 當前啟用的感測器清單和取樣率。開發者在 debug console 就能看到「哪些感測器在跑」。

### Config 變更事件

感測器 config 變更時（collector 下發新 config、或 feature flag 變化），SDK 送一個 lifecycle 事件：

```json
{
  "type": "lifecycle",
  "name": "sensor.config.changed",
  "data": {
    "source": "collector_push",
    "changed": {"click.*": {"sampling": "0.1 → 0.05"}},
    "active_sensors": 12
  }
}
```

這筆事件讓開發者在查詢時能看到「某個時間點感測器 config 改變了」，和事件量的變化做交叉比對。

## 下一步路由

- 感測器偵測哪些行為 → [前端感測器設計](/monitoring/03-sdk-design/frontend-sensor-design/)
- SDK 的公開 API → [SDK 公開 API 設計](/monitoring/03-sdk-design/public-api/)
- 四類事件的定義 → [四類事件的完整定義](/monitoring/01-mental-model/four-event-types/)
- 事件枚舉方法 → [事件枚舉與補齊檢查](/monitoring/01-mental-model/event-enumeration-method/)
