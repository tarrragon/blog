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
    "app": "terminal_app",
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

| SDK     | 偵測來源                   | 映射規則                                                                  |
| ------- | -------------------------- | ------------------------------------------------------------------------- |
| Python  | `sys.platform`             | `darwin`→`macos`、`linux`→`linux`、`win32`→`windows`、其他直接傳原值      |
| Flutter | `Platform.operatingSystem` | 回傳值（`ios`/`android`/`macos`/`linux`/`windows`）即合法值，無需映射     |
| JS      | 瀏覽器環境                 | 固定為 `web`；OS 偵測（如需要）從 `navigator.userAgentData` 解析          |
| Go      | `runtime.GOOS`             | `darwin`→`macos`、`linux`→`linux`、`windows`→`windows`、映射邏輯同 Python |

以上映射是 SDK init 時的預設自動偵測行為。Python 和 Go 的 runtime 回傳系統內部名稱（`darwin`、`win32`），SDK 負責映射到 schema 定義的標準名稱。Flutter 的 `dart:io Platform.operatingSystem` 恰好回傳合法值。JS SDK 在瀏覽器環境中無法可靠偵測 OS，platform 統一為 `web`。

自動偵測之外，SDK 也接受手動覆蓋 platform 值。短生命週期的命令列腳本（如 CI pipeline step、pre-commit hook）可手動將 platform 設為 `script`，表示非互動式 OS session——這類場景中 OS 名稱不是有意義的區分維度，`script` 讓查詢時能篩選出所有腳本來源的事件。

SDK 不做映射的話，collector 會收到不一致的 platform 值——同是 macOS 的事件有些標 `darwin` 有些標 `macos`，查詢篩選會漏事件。各平台 SDK 的執行環境適配細節見[模組五：平台適配](/monitoring/05-platform-adaptation/)。

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

## Collector 附加欄位（底線前綴）

Collector 在事件寫入 storage 時可以附加系統層的 metadata。這些欄位使用底線前綴（`_flags`、`_fingerprint`），和 SDK 端產生的業務欄位區隔。SDK 送出的事件中不包含這些欄位 — 它們由 collector pipeline 在處理過程中計算並附加。

### _flags（選填，collector 附加）

Collector 端的行為分析或規則引擎偵測到異常時，在事件中附加標記。Dashboard 查詢可用 `_flags` 過濾可疑事件。

```json
{
  "_flags": {
    "suspicious": true,
    "reason": "rate_anomaly"
  }
}
```

`suspicious` 標記的事件不被刪除 — 直接丟棄有誤殺正常流量的風險（行銷活動的真實流量暴增可能觸發異常偵測）。Dashboard 預設排除 `_flags.suspicious = true` 的事件，需要調查時可包含。

標記來源和 reason 值的定義見 [Client-side SDK 認證](/monitoring/07-security-privacy/client-sdk-authentication/) 的事後標記策略段。

### _fingerprint（選填，collector 附加）

Error 事件的去重識別碼。Collector 從 error 的 type、normalized message、stack trace 計算 hash，用於把相同根因的 error 歸組。

```json
{
  "_fingerprint": "a3f8c2e1b7d94f06"
}
```

Fingerprint 的計算邏輯和 error grouping 機制見 [Error Fingerprint 與去重分群](/monitoring/04-collector/error-fingerprint/)。

### SDK 自監控指標

監控系統自身的資料完整性需要獨立的指標追蹤 — SDK 用 metric 類事件回報自己的送出量和丟棄量，collector 用 endpoint 暴露處理量和拒絕量。SDK 端的指標每次 flush 成功後作為標準 schema 事件一起送出，name 以 `sdk.` 前綴標識。

| name                  | 含義                                         |
| --------------------- | -------------------------------------------- |
| `sdk.events.produced` | 事件產生總數（取樣前）                       |
| `sdk.events.sampled`  | 取樣後保留的事件數                           |
| `sdk.events.sent`     | 成功送出的事件數（收到 200/207 的 accepted） |
| `sdk.events.dropped`  | 被 FIFO 丟棄或重試耗盡的事件數               |
| `sdk.flush.failures`  | flush 失敗次數（429 / 5xx / timeout）        |
| `sdk.sampling.rate`   | 當前動態取樣率                               |

Collector 端對應暴露 `collector.events.received`、`collector.events.rejected`、`collector.events.stored`、`collector.events.backpressure` 等指標，透過 `/metrics` endpoint 或 health endpoint 的擴展欄位提供。

完整的指標定義、端到端比對方法和損失率閾值見 [端到端資料完整性](/monitoring/04-collector/data-integrity/) 的監控損失段。

## 完整 schema 範例

```json
{
  "v": 1,
  "type": "error",
  "name": "terminal.connect.failed",
  "timestamp": "2026-06-19T14:30:00.123+08:00",
  "source": {
    "sdk": "flutter",
    "app": "terminal_app",
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
