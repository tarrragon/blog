---
title: "監控實務指南"
date: 2026-06-19
description: "整理非伺服器端運行時的監控體系 — 行為蒐集、錯誤回報、效能指標、生命週期追蹤，從自架方案到商業方案的完整知識路線"
weight: 37
tags: ["monitoring"]
---

監控教材的核心目標是教讀者理解「使用者的裝置上發生了什麼事」。開發者不在使用者旁邊，需要系統性地收集行為事件、攔截錯誤、量測效能、追蹤生命週期 — 這四類資訊構成客戶端可觀測性的完整圖像。

## 跟 Backend 可觀測性的關係

[Backend 模組四：可觀測性平台](/backend/04-observability/) 聚焦 server-side — Prometheus metrics、OpenTelemetry tracing、log aggregation、alert routing。那是「伺服器怎麼知道自己出問題」。

本系列聚焦非 server 端運行時 — mobile app、web 頁面、本機腳本（CLI / Hook）、本機服務。這是「開發者怎麼知道使用者端出問題」。

兩者的交叉點是 **事件格式** 和 **transport**。Server-side 用 OTLP（OpenTelemetry Protocol）；本系列用 HTTP POST JSON — 更簡單、無依賴、適合小規模自架。大規模時可橋接到 OTLP。

## 跟 Testing 的關係

[開發測試模組二：客戶端可觀測性](/testing/) 聚焦「開發期的 log 設計」— 連線生命週期 log、protocol 訊息 log、功能規格中的 log 點定義。那是「怎麼在開發時就設計好 log」。

本系列聚焦「log 收集到之後的完整鏈路」— SDK 怎麼埋點、事件怎麼送、collector 怎麼收、資料怎麼查、規則怎麼觸發。Testing 模組二是設計端，本系列是基礎設施端。

## 教學範圍

| 放在本系列                                         | 放在其他系列                                                              |
| -------------------------------------------------- | ------------------------------------------------------------------------- |
| 監控心智模型（四類事件分類與收集策略）             | server-side observability（放 [Backend 04](/backend/04-observability/)）  |
| 跨平台 SDK 設計（JS / Flutter / Python）           | 特定語言的 error handling（放語言教材）                                   |
| 自架 collector（Go、JSONL、rule engine）           | 商業 APM 管理後台操作                                                     |
| Log schema 與 transport 規格                       | 分散式 tracing（放 Backend 04）                                           |
| 商業方案對照（Sentry / Crashlytics / Datadog RUM） | 商業方案的付費方案比較                                                    |
| 本機腳本監控（Python Hook / CLI 工具）             | server daemon 監控（放 Backend 05 部署平台）                              |
| Rule engine（條件觸發 → 自動 issue / alert）       | Incident response 流程（放 [Backend 08](/backend/08-incident-response/)） |

## 教學模組

### 模組一：監控心智模型

回答「要收集什麼、為什麼」。四類事件各自解答的問題：

| 事件類型    | 回答什麼問題     | 範例                                             |
| ----------- | ---------------- | ------------------------------------------------ |
| `event`     | 使用者做了什麼？ | button.click、page.view、hook.run、qr.scan       |
| `error`     | 哪裡壞了？       | uncaught exception、network error、hook failure  |
| `metric`    | 有多快 / 多慢？  | response_time、render_duration、hook_duration_ms |
| `lifecycle` | 系統的狀態轉換？ | app.start、session.begin、ws.connect、hook.init  |

四類不是互斥的 — 一個 hook 執行可以同時產生 `lifecycle`（hook.start）、`metric`（duration）、`error`（如果失敗），和 `event`（hook.complete）。分類的價值是讓查詢和 rule engine 能按類型過濾。

**商業方案如何對應**：

| 商業方案             | 對應的事件類型         | 額外能力                               |
| -------------------- | ---------------------- | -------------------------------------- |
| Sentry               | error + metric         | stack trace 去重、release tracking     |
| Firebase Crashlytics | error                  | crash-free rate、ANR 偵測              |
| Firebase Analytics   | event + lifecycle      | funnel、retention、user property       |
| Datadog RUM          | event + error + metric | session replay、waterfall、core vitals |
| Mixpanel / Amplitude | event                  | funnel、cohort、A/B test attribution   |

自架方案覆蓋四類事件的收集和儲存；商業方案在此基礎上加 dashboard、去重、alerting、session replay 等進階功能。理解四類事件的分類後，商業方案的功能差異就是「在哪類事件上做了什麼加值」。

### 模組二：Log Schema 設計

回答「事件長什麼樣」。跨平台統一事件格式、欄位設計、版本演進策略。

核心格式（`schema/event.schema.json`）：

```json
{
  "v": 1,
  "type": "error",
  "timestamp": "2026-06-19T20:00:00Z",
  "source": { "sdk": "python", "platform": "macos", "app": "claude-hooks" },
  "name": "hook.failure",
  "level": "error",
  "data": { "hook": "branch-status-reminder", "duration_ms": 42 },
  "error": { "message": "FileNotFoundError: ...", "type": "FileNotFoundError" }
}
```

設計原則：

1. **`source` 標明來源** — 收到事件就知道是哪個 SDK、哪個平台、哪個 app
2. **`data` 是自由欄位** — 不同場景的附帶資料差異太大，用結構化 JSON 而非固定欄位
3. **`v` 做版本演進** — Schema 改版時 collector 靠版本號決定解析方式
4. **四類 `type`** — 查詢和 rule engine 的第一個過濾維度

> 對應 repo：[tarrragon/monitor](https://github.com/tarrragon/monitor) 的 `schema/event.schema.json` 是 SOT

### 模組三：SDK 設計模式

回答「怎麼在各平台埋點」。三個 SDK 共用同一套事件格式，但攔截機制不同：

| 平台    | 自動攔截                                     | 手動上報                    |
| ------- | -------------------------------------------- | --------------------------- |
| JS/TS   | `window.onerror`、`unhandledrejection`       | `monitor.event('name', {})` |
| Flutter | `FlutterError.onError`、`PlatformDispatcher` | `monitor.event('name', {})` |
| Python  | `sys.excepthook`、`atexit`                   | `monitor.event('name', {})` |

三個 SDK 的公開 API 設計應保持一致（同名方法、同參數順序），讓跨平台開發者不需重新學習。

### 模組四：Collector 設計

回答「收到的事件怎麼處理」。Go 單一 binary，零外部依賴。

職責鏈：收（HTTP endpoint）→ 驗（JSON Schema）→ 存（JSONL 檔案）→ 查（CLI 查詢）→ 觸發（rule engine）。

自用場景的 collector 跟 production 級 observability 平台的差異：沒有 dashboard（用 grep / jq）、沒有 alerting（用 rule engine + 腳本）、沒有 HA（單機就夠）。這些是刻意的設計選擇——零依賴、零運維、grep 友好。

### 模組五：平台適配

回答「各平台有什麼特殊考量」。JS 的 CORS 限制、Flutter 的 isolate 安全、Python 的 GIL 與 atexit、Go 的 graceful shutdown。

### 模組六：商業方案對照

回答「什麼時候該從自架切換到商業方案」。判斷標準：

| 條件                         | 自架       | 商業方案       |
| ---------------------------- | ---------- | -------------- |
| 使用者 = 開發者自己          | 適合       | 過度           |
| 使用者 < 100 人、同區網      | 適合       | 可考慮免費方案 |
| 使用者 > 1000 人、外部網路   | 維護成本高 | 適合           |
| 需要 session replay / funnel | 自建成本高 | 適合           |
| 需要合規稽核（SOC 2 / GDPR） | 自建困難   | 適合（已認證） |

## 學習路線

| 路線             | 適合讀者                            | 建議順序              | 讀完能做什麼                 |
| ---------------- | ----------------------------------- | --------------------- | ---------------------------- |
| 自架監控快速上手 | 想在自己的 app/script 加監控        | 模組一 → 二 → 四 → 三 | 能部署 collector + 埋點 SDK  |
| SDK 開發者       | 想理解監控 SDK 怎麼設計             | 模組三 → 二 → 五      | 能設計跨平台一致的監控 SDK   |
| 商業方案評估     | 想知道什麼時候該用 Sentry / Datadog | 模組一 → 六           | 能評估自架 vs 商業方案的取捨 |

## 教學寫作方向

1. **自架先於商業** — 先教 grep + JSONL 怎麼查問題，再說 Sentry 的 dashboard 多好用。理解底層才能判斷商業方案值不值得
2. **四類事件是統一語言** — 所有討論都回到 event/error/metric/lifecycle 四類。商業方案差異也用這四類拆解
3. **一個 repo 實證所有理論** — [tarrragon/monitor](https://github.com/tarrragon/monitor) monorepo 是本系列的實作伴侶，每個模組的理論都有對應的 code

---

_文件版本：v0.1.0_
_最後更新：2026-06-19_
_系列狀態：分類索引建立中_
