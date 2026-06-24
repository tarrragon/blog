---
title: "event.schema.json 完整欄位解說"
date: 2026-06-19
description: "監控事件的 JSON Schema 定義 — 每個欄位的語意、必填/選填、資料型別和設計理由"
weight: 1
tags: ["monitoring", "log-schema", "json-schema", "event"]
---

事件 schema 定義了每一筆監控事件的資料結構。統一的 schema 讓 SDK、collector、查詢工具使用同一個資料契約 — SDK 知道該送什麼欄位，collector 知道該驗證什麼，查詢工具知道該讀什麼。

## 核心欄位

### type（必填）

事件類型。對應四類事件分類（[模組一](/monitoring/01-mental-model/four-event-types/)）：`event`、`error`、`metric`、`lifecycle`。

Collector 用 type 決定事件的處理路徑 — error 類型觸發告警規則，metric 類型進入數值聚合，event 類型進入行為分析。

### name（必填）

事件名稱。使用 namespace.action 格式（[事件命名規範](/monitoring/01-mental-model/event-naming-convention/)）。例如 `terminal.connect.done`、`auth.biometric.failed`。

name 是查詢和統計的主要索引。`grep "terminal.connect"` 找到所有連線事件；按 name 分群計數得到功能使用頻率。

### timestamp（必填）

事件發生的時間。ISO 8601 格式，包含時區偏移。`2026-06-19T14:30:00.123+08:00`。

Timestamp 由 SDK 在事件發生時記錄，不是 collector 收到時記錄。兩者可能有延遲（離線 buffer、網路延遲），以 SDK 端的時間為準。

### source（必填）

事件來源的識別資訊。包含產生事件的 SDK、app 名稱、版本、平台、OS 版本。

```json
{
  "source": {
    "sdk": "flutter",
    "app": "app_tunnel",
    "version": "1.2.0",
    "platform": "ios",
    "os": "17.4"
  }
}
```

`sdk` 標明產生事件的 SDK 種類（`js` / `flutter` / `python` / `go`）。同一個平台可能有不同的 SDK——iOS 上可能是 Flutter SDK 或未來的 Swift 原生 SDK——sdk 欄位讓 collector 區分事件來自哪個 SDK 實作，platform 無法替代這個識別。`sdk` 和 `platform` 為必填，`app`、`version`、`os` 為選填。

Source 讓同一個 collector 接收多個 app 的事件時可以區分來源。也用於分析「哪個版本的 error 率最高」、「哪個 OS 版本有特定問題」。

#### platform 合法值與自動偵測

`platform` 由 SDK init 時自動偵測，開發者不需手動設定。各 SDK 的偵測來源和映射規則：

| SDK     | 偵測來源                   | 映射規則                                                              |
| ------- | -------------------------- | --------------------------------------------------------------------- |
| Python  | `sys.platform`             | `darwin`→`macos`、`linux`→`linux`、`win32`→`windows`、其他直接傳原值  |
| Flutter | `Platform.operatingSystem` | 回傳值（`ios`/`android`/`macos`/`linux`/`windows`）即合法值，無需映射 |
| JS      | 瀏覽器環境                 | 固定為 `web`；OS 偵測（如需要）從 `navigator.userAgentData` 解析      |

Python 的 `sys.platform` 回傳 `darwin` 和 `win32` 不是使用者友善的名稱，SDK 負責映射到標準名稱。Flutter 的 `dart:io Platform.operatingSystem` 恰好回傳合法值。JS SDK 在瀏覽器環境中無法可靠偵測 OS，platform 統一為 `web`。

### session（選填）

使用者 session 的識別資訊。Session ID（UUID）和 session 開始時間。

Session 用於關聯同一次使用中的多個事件。「使用者在這次 session 中做了什麼操作、遇到了什麼 error」的分析依賴 session ID。

去識別化要求：session ID 用 UUID 而非使用者帳號，不包含個人識別資訊（[模組七](/monitoring/07-security-privacy/)）。

### data（選填）

事件的附加資料。自由結構的 JSON object，內容依事件類型和名稱而定。

```json
{
  "data": {
    "url": "wss://192.168.1.100:7681/ws",
    "duration_ms": 320,
    "step": "3/5"
  }
}
```

Data 欄位是 schema 中唯一的自由結構區域。核心欄位（type、name、timestamp、source）有固定格式，data 的內容由事件定義者決定。

### v（必填）

Schema 版本號。整數，從 1 開始遞增。

版本號讓 collector 知道用哪個版本的 schema 驗證這筆事件。Schema 演進時，舊版本的事件仍可被正確處理。

## 完整 schema 範例

```json
{
  "v": 1,
  "type": "error",
  "name": "terminal.connect.failed",
  "timestamp": "2026-06-19T14:30:00.123+08:00",
  "source": {
    "sdk": "flutter",
    "app": "app_tunnel",
    "version": "1.2.0",
    "platform": "ios",
    "os": "17.4"
  },
  "session": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "started": "2026-06-19T14:25:00.000+08:00"
  },
  "data": {
    "step": "ws_connect",
    "error": "Connection refused",
    "url": "wss://192.168.1.100:7681/ws"
  }
}
```

## 下一步路由

- 欄位設計的原則 → [欄位設計原則](/monitoring/02-log-schema/field-design-principles/)
- Schema 版本演進 → [Schema 版本演進策略](/monitoring/02-log-schema/schema-versioning/)
- 和 OpenTelemetry 的差異 → [跟 OpenTelemetry 的 schema 差異對照](/monitoring/02-log-schema/otel-comparison/)
- Log 點的設計方法 → [testing 模組二 客戶端可觀測性](/testing/02-client-observability/)
