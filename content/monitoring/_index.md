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

跟模組八的關係：模組六比較「自架 vs 商業」的功能和成本；模組八把行為資料視為商業資產，討論精準行銷、推薦系統、A/B test attribution — 這些是商業方案的核心賣點，也是自架方案最難自建的部分。

### 模組七：資安與隱私

回答「蒐集的資料本身就是風險資產，怎麼保護」。同一份監控資料在不同角色眼中有不同身份：

| 角色     | 看到的是   | 關心的問題                     |
| -------- | ---------- | ------------------------------ |
| 開發者   | debug 資訊 | 錯誤在哪、使用者做了什麼       |
| 安全團隊 | 風險資產   | 含 secret 嗎、被入侵會洩漏什麼 |
| 法務團隊 | 合規負債   | 蒐集合法嗎、保留多久、跨境嗎   |
| 行銷團隊 | 商業原料   | 能做 funnel 嗎、能投廣告嗎     |

**三層防護設計**（影響 SDK 和 collector 的實作）：

| 層                          | 在哪裡做                          | 做什麼                                                                                    | 影響 monitor repo 哪裡                         |
| --------------------------- | --------------------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------- |
| SDK 端 redaction            | sdk-js / sdk-flutter / sdk-python | 送出前自動遮蔽已知 secret pattern（API key / password / token / file path 中的 username） | SDK 的 `redact()` helper + 預設 redaction rule |
| Transport 加密              | SDK → collector                   | HTTPS 或至少 basic auth（即使同區網）                                                     | transport 規格 + collector TLS 設定            |
| Collector 端 access control | collector                         | 儲存加密 at rest、查詢需認證、access log 記錄誰查了什麼                                   | collector 的 auth middleware + 加密儲存        |

**去識別化策略**：

| 資料類型        | 去識別方法                                         | 時機                      |
| --------------- | -------------------------------------------------- | ------------------------- |
| IP 地址         | 截斷最後一段（192.168.1.x）                        | SDK 端或 collector 收到時 |
| User agent      | 保留 OS + browser 版本，去除 fingerprint 細節      | collector 收到時          |
| 自由欄位 `data` | regex 掃描已知 secret pattern，替換為 `[REDACTED]` | SDK 端送出前              |
| Stack trace     | 去除絕對路徑中的 username                          | SDK 端送出前              |
| Session ID      | 不跟真實使用者身份綁定（匿名 UUID）                | SDK 初始化時              |

跟 [Backend 07 資安與資料保護](/backend/07-security-data-protection/) 的關係：Backend 07 聚焦 server-side 的權限、秘密管理、稽核追蹤；本模組聚焦「蒐集來的監控資料本身」的保護。交叉點是 [Secret Management](/backend/knowledge-cards/secret-management/) — 監控資料裡意外包含 secret 時，去識別化機制需要知道什麼 pattern 算 secret。

> 後續章節預定：SDK redaction API 設計、collector access control 實作、GDPR 最小化原則的工程落地、「監控資料洩漏」的 threat model

### 模組八：行為資料的商業利用

回答「蒐集到的行為資料除了 debug，還能做什麼」。這是監控體系從「開發工具」翻轉成「商業資產」的轉折點。

**前提：模組七的去識別化是本模組的入場條件。** 沒做好去識別化就做精準行銷 = 法律風險。本模組假設資料已經過去識別化處理。

**行為資料的商業價值鏈**：

```text
蒐集（SDK 埋點）
  → 清洗（去識別 + 去噪）
    → 分析（funnel / cohort / attribution）
      → 決策（投放 / 改版 / 定價）
        → 驗證（A/B test → 回到蒐集）
```

| 分析類型        | 回答什麼問題                     | 需要的事件                                              | 商業方案                         |
| --------------- | -------------------------------- | ------------------------------------------------------- | -------------------------------- |
| Funnel analysis | 使用者在哪一步流失？             | `event`（page.view / button.click / checkout.complete） | Mixpanel / Amplitude / GA4       |
| Cohort analysis | 不同族群的留存率差異？           | `event` + `lifecycle`（session.begin 時間）             | Mixpanel / Amplitude             |
| Attribution     | 使用者從哪來？哪個廣告帶來轉換？ | `event`（install / first_open / conversion）            | Adjust / AppsFlyer / GA4         |
| A/B test        | 哪個版本的按鈕轉換率更高？       | `event`（variant_shown / conversion）                   | Optimizely / LaunchDarkly / 自建 |
| 推薦系統        | 這個使用者可能對什麼感興趣？     | `event`（view / click / purchase 歷史）                 | 自建 / AWS Personalize           |
| RFM 分群        | 誰是高價值客戶？誰快流失？       | `event`（purchase 頻率 / 金額 / 最近一次）              | 自建 / CRM 工具                  |

**跟監控的邊界**：

|              | 監控（模組一~六）                  | 商業利用（本模組）                 |
| ------------ | ---------------------------------- | ---------------------------------- |
| 看的事件     | 全部四類（error 為主）             | 主要 `event` 類                    |
| 分析粒度     | 單筆事件（這個錯誤的 stack trace） | 聚合統計（過去 30 天的轉換率）     |
| 決策輸出     | 修 bug、改架構                     | 投廣告、改定價、改 UI              |
| 資料保留     | 短期（30 天，debug 用完即丟）      | 長期（年級，行為趨勢需要歷史資料） |
| 去識別化要求 | 中（開發者看 raw data 可接受）     | 高（行銷分析必須去識別）           |

**自架方案能做到哪裡**：

- Funnel / cohort 基礎分析：collector 的聚合查詢 + 簡單腳本可做
- Attribution / 推薦系統：需要專門的資料管線，超出 collector 範圍
- A/B test：需要 feature flag 系統 + 統計檢定，屬獨立基礎設施

> 後續章節預定：行為事件設計（事件命名規範 / 屬性設計 / funnel 定義）、從 collector 資料做基礎 funnel 分析、A/B test 的統計基礎、推薦系統概論、RFM 分群實作
>
> 跨系列連結：
> - 精準行銷的資料管線設計 → 待建 `data-engineering/` 或放 [Backend 01 資料庫](/backend/01-database/)
> - A/B test 的統計檢定 → 待建 `statistics/` 或放 [Backend 09 效能容量](/backend/09-performance-capacity/)
> - 推薦系統架構 → 待建 `machine-learning/` 或放 [Backend](/backend/) 延伸模組
> - 隱私法規（GDPR / CCPA / 個資法） → 待建 `compliance/` 或放 [Backend 07](/backend/07-security-data-protection/) 延伸

## 學習路線

| 路線             | 適合讀者                            | 建議順序                   | 讀完能做什麼                      |
| ---------------- | ----------------------------------- | -------------------------- | --------------------------------- |
| 自架監控快速上手 | 想在自己的 app/script 加監控        | 模組一 → 二 → 四 → 三      | 能部署 collector + 埋點 SDK       |
| SDK 開發者       | 想理解監控 SDK 怎麼設計             | 模組三 → 二 → 五           | 能設計跨平台一致的監控 SDK        |
| 商業方案評估     | 想知道什麼時候該用 Sentry / Datadog | 模組一 → 六                | 能評估自架 vs 商業方案的取捨      |
| 資安合規         | 想確保蒐集的資料不會變成負債        | 模組七 → 二（schema 設計） | 能設計去識別化 + access control   |
| 商業利用         | 想把行為資料變成商業決策            | 模組一 → 七 → 八           | 能設計行為事件 + 基礎 funnel 分析 |

## 教學 × 實作互補循環

本系列的教學內容和 [tarrragon/monitor](https://github.com/tarrragon/monitor) monorepo 是互補關係，兩者各自承擔不同的知識生產責任：

|          | 教學（本系列）                         | 實作（monitor repo）                              |
| -------- | -------------------------------------- | ------------------------------------------------- |
| 職責     | 整理理論框架、分類心智模型、設計原則   | 驗證理論可行性、暴露理論盲區                      |
| 產出方向 | 概念 → 範例 → 判斷準則                 | 程式碼 → 困難 → 新的待整理議題                    |
| 例子     | 「四類事件分類」「SDK API 一致性原則」 | 「collector 收到 10 萬筆/天時 JSONL grep 多慢？」 |

**互補循環的運作方式**：教學先建立理論框架（四類事件、log schema、transport 規格），實作按框架建 SDK 和 collector，實作過程撞到理論沒覆蓋的挑戰（高併發寫入、大資料查詢、儲存生命週期），挑戰回過頭成為教學的新章節。

### 教學與 repo 文件分工

教學和 monitor repo 的文件各自有不同的讀者和目的。教學讀者想理解「為什麼這樣設計」，repo 讀者想知道「怎麼跑起來」。

| 內容                              | 位置                       | 理由         |
| --------------------------------- | -------------------------- | ------------ |
| 設計原則和判斷框架                | 教學（本系列）             | 跨專案可重用 |
| Quick Start（5 分鐘跑起來）       | monitor repo README        | 專案綁定     |
| 部署指南（systemd / config 範例） | monitor repo docs/         | 專案綁定     |
| SDK 整合範例（Flutter / Python）  | monitor repo 各 SDK README | 語言綁定     |
| Troubleshooting                   | monitor repo docs/         | 專案綁定     |
| Migration（SQLite → PostgreSQL）  | monitor repo docs/         | 版本綁定     |

教學讀者想要直接跑起來的步驟，見 [monitor repo](https://github.com/tarrragon/monitor) 的 README Quick Start 段。

### 挑戰在 collector 端，不在 SDK 端

SDK 埋點是已解決問題 — `window.onerror` 攔截錯誤、`http.post` 送出事件、攢批 flush，前端技術成熟且各商業方案已驗證過。SDK 的設計決策（自動攔截 vs 手動上報、flush interval、buffer 上限）有最佳實踐可循。

真正的挑戰在 collector 端，而且挑戰的規模隨使用者數量和時間跨度急劇增長：

| 挑戰         | 觸發條件                                                   | 教學需回補的議題                                                  |
| ------------ | ---------------------------------------------------------- | ----------------------------------------------------------------- |
| 高併發寫入   | 多個 SDK 同時 flush → collector 瞬間收到大量 HTTP request  | 寫入 buffer、WAL、背壓、rate limit                                |
| 大資料查詢   | 累積 30 天 × 每天 10 萬筆 = 300 萬筆 → `grep` 吃光記憶體   | 索引策略（時間分區 + 事件名稱索引）、查詢 API 設計                |
| 儲存生命週期 | JSONL 無限增長 → 磁碟滿                                    | 保留策略（TTL）、壓縮（gzip）、歸檔（冷儲存）、清除（定期 purge） |
| 聚合查詢     | 「過去 7 天 hook.failure 的趨勢」→ 掃描 700 萬筆做 count   | 預聚合（每小時統計寫入摘要表）、物化視圖                          |
| 錯誤回報查詢 | 「最近 10 個 uncaught exception 的 stack trace」→ 全文搜尋 | 錯誤去重（fingerprint）、stack trace 索引                         |

這些挑戰的共同特徵是：**在自用場景（1 人、1 台機器、每天幾百筆）完全不存在，在小規模場景（100 人、每天 10 萬筆）開始浮現，在中規模場景（1000+ 人、每天百萬筆）成為核心問題。** 自架方案從「grep 就夠」演進到「需要時間序列資料庫」的過程，正好是理解商業方案為什麼那樣設計的最佳路徑。

### 實作驅動的教學章節回補

當實作撞牆時，回補流程：

1. **記錄撞牆場景**：在 monitor repo 的 `docs/challenges/` 記錄具體問題（輸入規模、觀察到的症狀、嘗試的方案）
2. **分析根因**：問題屬於哪個領域（資料庫設計 / 併發控制 / 儲存策略 / 查詢最佳化）
3. **回補教學章節**：在 monitoring 教學系列或 [Backend](/backend/) 對應模組新增章節
4. **交叉引用**：collector 高併發問題 → [Backend 01 資料庫](/backend/01-database/) 或 [Backend 09 效能容量](/backend/09-performance-capacity/)

實作撞的牆越多，教學系列就越完整。商業方案（Sentry、Datadog）已經解決過這些問題 — 他們的架構選擇（ClickHouse 做事件儲存、Kafka 做寫入 buffer、Snuba 做聚合查詢）就是這些挑戰的解法。自架過一次，看商業方案的架構文件時每個決策都能理解為什麼。

## 教學寫作方向

1. **自架先於商業** — 先教 grep + JSONL 怎麼查問題，再說 Sentry 的 dashboard 多好用。理解底層才能判斷商業方案值不值得
2. **四類事件是統一語言** — 所有討論都回到 event/error/metric/lifecycle 四類。商業方案差異也用這四類拆解
3. **實作驅動教學** — monitor repo 的實作困難是教學章節的來源。撞牆 → 記錄 → 分析 → 回補章節。教學不只是寫在實作前的理論，也是寫在實作撞牆後的提煉
4. **規模演進是理解工具的路徑** — 從 grep 到 SQLite 到時間序列 DB 的演進過程，正好是理解 Sentry / Datadog 架構選擇的最佳路徑

---

_文件版本：v0.2.0_
_最後更新：2026-06-19_
_系列狀態：分類索引建立中_
