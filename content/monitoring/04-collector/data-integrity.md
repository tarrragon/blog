---
title: "端到端資料完整性"
date: 2026-06-24
description: "從 SDK 到 storage 的資料損失地圖 — 每個環節的損失類型、控制策略、完整性指標、被自己 SDK DDoS 的防護"
weight: 15
tags: ["monitoring", "collector", "data-integrity", "loss", "reliability", "backpressure"]
---

監控資料從事件產生到寫入 storage，經過 SDK buffer、HTTP transport、collector pipeline、storage backend 四個環節。每個環節都有丟失事件的可能 — 記憶體 buffer 溢出、網路超時、背壓丟棄、磁碟寫入失敗。端到端資料完整性的目標是讓每個損失點都是有意識的設計取捨，而非靜默丟失。

監控資料和交易資料的根本差異在這裡：交易資料的損失會直接造成商業損害（少了一筆訂單），監控資料的損失影響的是可觀測性的覆蓋率（少了幾筆 event 不影響趨勢判斷，但漏了 error 可能讓 bug 晚幾天被發現）。這個差異決定了完整性設計的方向 — 追求的是「損失可控且可觀測」，而非「零損失」。合規稽核 log、billing event 和安全事件不適用這個假設 — 它們的損失有法規或商業後果，需要 at-least-once delivery 和獨立的持久化保證，通常用 transaction log 而非監控管線處理。

## 資料損失地圖

一筆事件從產生到持久化，依序經過四個環節。每個環節的損失類型、發生條件和影響範圍各不同。

```text
事件產生 → [SDK buffer] → HTTP POST → [Collector pipeline] → [Storage]
     ①          ②            ③              ④                   ⑤
```

### 環節一：事件產生階段

事件在 SDK 的 `monitor.event()` / `monitor.error()` 被呼叫時產生，進入記憶體 buffer。這個階段的損失來自取樣和 SDK 初始化時序。

**靜態取樣**：SDK config 中設定的取樣率（例如 metric 類 0.1 = 每 10 筆只收 1 筆）是設計內的損失。取樣後的事件量直接影響後續所有環節的負載。取樣率的設定依據見[感測器生命週期管理](/monitoring/03-sdk-design/sensor-lifecycle-management/)。

**SDK 未初始化**：app 啟動後到 `monitor.init()` 完成之間的事件會被丟棄。如果 init 排在其他初始化邏輯之後，啟動階段的 crash 可能漏捕。商業 SDK（Sentry、Crashlytics）用 native crash handler 在 SDK 層之外攔截這類 crash，自架方案通常接受這個損失。

### 環節二：SDK buffer 階段

事件進入記憶體 buffer 後，等待 flush 觸發。Buffer 溢出和 app 強制終止是這段路徑上的兩個風險。

**FIFO 丟棄**：記憶體 buffer 有容量上限（典型值 200-500 筆）。離線時間過長或事件產生速率過高時，buffer 滿了會丟棄最舊的事件。丟棄策略見[離線 buffer 與重試](/monitoring/03-sdk-design/offline-buffer/)，優先級丟棄見 [Ingestion Scaling 第一層](/monitoring/04-collector/ingestion-scaling/)。

**App 強制終止**：iOS 的 `kill`、Android 的 process death、Python 的 `SIGKILL` — 記憶體 buffer 中未 flush 的事件全部遺失。[攢批送出策略](/monitoring/03-sdk-design/batch-flush/)的 close flush 嘗試在 app 正常退出時送出剩餘事件，但強制終止時連 close callback 都不會執行。

**動態取樣**：收到 collector 的 HTTP 429（Too Many Requests，表示 collector 過載）後，SDK 自動降低取樣率（從 1.0 降到 0.5 → 0.1）。這是對 collector 過載的回饋反應 — 損失的事件量隨背壓程度增加。和靜態取樣的差異是動態取樣在正常情況下不生效，只在過載時啟用。

### 環節三：Transport 階段

SDK flush 時透過 HTTP POST 送出 batch。網路故障和重試耗盡構成 transport 層的主要損失。

**HTTP 超時 / 連線失敗**：collector 不可達時，batch 保留在 SDK buffer 等待下次 flush 重試。重試次數有上限（3 次），超過後丟棄 batch 並記錄 `sdk.flush.dropped` metric。重試策略見[攢批送出策略](/monitoring/03-sdk-design/batch-flush/)。

**離線補發擁塞**：離線恢復後，SDK 一次補發大量累積事件。如果補發速率過高（一批 500 筆 × 多個 SDK 同時恢復），collector 可能觸發背壓回 429，SDK 又進入動態降採樣 — 補發本身造成新的損失。[離線 buffer 與重試](/monitoring/03-sdk-design/offline-buffer/)的分批補發（每批 50-100 筆、間隔 1-2 秒）用來避免這個問題。

### 環節四：Collector pipeline 階段

Collector 收到 HTTP request 後，事件進入處理鏈路。背壓、驗證拒絕和 pipeline 內部的 buffer 溢出都可能在這裡造成損失。

**Channel 背壓**：Collector 內部用一個專屬的寫入 goroutine 搭配 Go channel 做序列化寫入（[Collector 架構](/monitoring/04-collector/architecture/)的並發寫入策略段），channel 有固定容量。Channel 滿時 HTTP handler 回 429，事件被拒絕。SDK 收到 429 後保留事件在 buffer 等待重試，但如果 SDK buffer 也快滿，部分事件會被 FIFO 丟棄。這裡的損失是 SDK 層和 collector 層的連鎖反應 — collector 的背壓壓力最終由 SDK 的 buffer 承擔。

**Schema validation reject**：事件格式不符合 JSON Schema 的事件被拒絕（400 或 207 中的 rejected 部分）。這是品質閘門而非容量限制 — 被拒絕的事件無論重試多少次都不會通過，SDK 應該清除這些事件並記錄 warning。問題在 SDK 端的事件建構邏輯（程式碼 bug），需要修 SDK 而非重試。

**429 後事件已回 202 但未寫入**：collector 回了 202（已接受）但事件還在 channel buffer 中未寫入 storage 時，如果 collector crash 或被 SIGKILL，channel 中的事件遺失。這是「已承諾但未持久化」的窗口。[Container 部署設計](/monitoring/04-collector/container-deployment/)的 graceful shutdown 序列嘗試在 shutdown 時 flush pending writes，但非 graceful shutdown（OOMKill、硬體故障）無法保護。

### 環節五：Storage 階段

事件從 channel 寫入 storage backend。寫入失敗和資料管理操作（downsample / purge）構成最後一段損失。

**SQLite `database is locked`**：busy timeout 到期後寫入失敗。Single-writer pattern 降低發生機率但不能完全消除 — downsample / purge job 執行期間持有 write lock，如果 job 跑太久（數秒以上），ingestion 的寫入可能逾時。

**磁碟空間不足**：SQLite 寫入需要磁碟空間（WAL 檔案 + 主資料庫 + 臨時檔案）。磁碟滿時寫入失敗，事件遺失。保留策略的 purge job 負責控制磁碟使用量，但如果 purge 頻率低於寫入增長速率，磁碟可能在兩次 purge 之間被填滿。

**Downsample / purge 的設計內損失**：保留策略到期的原始事件被刪除（purge），只保留聚合摘要（hourly_summary / daily_summary）。這是設計內的損失 — 原始事件的 stack trace、完整 JSON data 在 purge 後不可回復，只剩下計數。保留策略見[規模演進](/monitoring/04-collector/scaling-evolution/)的分層保留段。

## 設計內損失 vs 異常損失

上述損失點可以分成兩類，處理方式根本不同。

| 類型     | 損失點                               | 特徵                      | 處理方式                      |
| -------- | ------------------------------------ | ------------------------- | ----------------------------- |
| 設計內   | 靜態取樣、動態取樣、FIFO 丟棄、purge | 有意識的取捨、可預測的量  | 在 config 中設定、用指標監控  |
| 異常     | crash 丟 buffer、disk full、WAL 損壞 | 非預期的故障、不可預測    | 用告警偵測、用恢復機制應對    |
| 品質閘門 | schema reject                        | SDK 端 bug 導致、重試無效 | 修 SDK 程式碼、不在 collector |

設計內損失的目標是讓損失量可控 — 取樣率設 0.1 代表預期丟 90%，FIFO buffer 容量 200 代表離線超過 20 分鐘（每分鐘 10 筆）後開始丟棄。這些數字是 config 參數，可以根據業務需求調整。

異常損失的目標是儘早偵測 — collector crash 後 channel 中有多少筆未寫入？磁碟使用率到多少該告警？下方的完整性指標段專門處理偵測異常損失的方法。

品質閘門的處理在 SDK 端而非 collector 端 — schema validation reject 的事件無論重試多少次都不會通過，問題在事件建構邏輯。具體的 reject 行為和回應格式見[環節四的 Schema validation reject 段](#環節四collector-pipeline-階段)。

## 監控損失本身的方法

監控系統的完整性需要「監控自己的監控」— 用獨立的指標追蹤每個環節的進出量，損失量 = 進量 - 出量。

### SDK 端指標

SDK 內部維護計數器，每次 flush 成功後一起送出（作為 metric 類事件）：

| 指標                  | 含義                                         | 計算方式                       |
| --------------------- | -------------------------------------------- | ------------------------------ |
| `sdk.events.produced` | 事件產生總數（取樣前）                       | 每次 `monitor.event()` 調用 +1 |
| `sdk.events.sampled`  | 取樣後保留的事件數                           | 通過取樣邏輯的事件 +1          |
| `sdk.events.sent`     | 成功送出的事件數（收到 200/207 的 accepted） | flush 成功後按 accepted 累加   |
| `sdk.events.dropped`  | 被 FIFO 丟棄或重試耗盡的事件數               | 每次丟棄 +1                    |
| `sdk.flush.failures`  | flush 失敗次數（429 / 5xx / timeout）        | 每次 flush 失敗 +1             |
| `sdk.sampling.rate`   | 當前動態取樣率                               | 收到 429 後更新                |

`produced - sampled` = 取樣損失（設計內）。`sampled - sent - dropped` 如果不為零，代表有事件卡在 buffer 中尚未送出或未被計入任何分類。

### Collector 端指標

Collector 在 `/metrics` endpoint（或 health endpoint 的擴展欄位）暴露處理計數器：

| 指標                            | 含義                                  |
| ------------------------------- | ------------------------------------- |
| `collector.events.received`     | 收到的事件總數（HTTP handler 層計數） |
| `collector.events.rejected`     | schema validation 拒絕的事件數        |
| `collector.events.stored`       | 成功寫入 storage 的事件數             |
| `collector.events.backpressure` | 因 channel 滿回 429 的事件數          |
| `collector.channel.depth`       | 當前 channel 中待寫入的事件數         |
| `collector.storage.errors`      | storage 寫入失敗的次數                |

`received - rejected - stored - backpressure` 如果不為零，代表有事件在 pipeline 中遺失（channel buffer 中的事件在 crash 時丟失就會造成這個差距）。

### 端到端比對

SDK 的 `sent` 和 collector 的 `received` 之間的差距是 transport 層的損失 — 網路丟包、中間件攔截（reverse proxy 的 body size limit）或 collector 重啟期間的連線失敗。

這個比對在自用場景下用手動 spot check 就夠（SDK log 的 sent count vs collector dashboard 的 received count）。小型以上規模需要自動化：一個定期 job 比對兩邊的計數器，差距超過閾值時告警。

### 損失率的可接受範圍

| 規模     | event 類損失率 | error 類損失率 | 監控粒度              |
| -------- | -------------- | -------------- | --------------------- |
| 自用     | < 10%          | < 1%           | 手動 spot check       |
| 小型團隊 | < 5%           | < 0.5%         | 每日自動比對          |
| 中型以上 | < 1%           | < 0.1%         | 即時 dashboard + 告警 |

閾值的推導邏輯：event 類的損失影響統計精度 — 取樣率 0.9 加上 transport 和 collector 層的少量損失，自用場景合計 < 10% 是合理的上限；funnel 分析用取樣校正（除以取樣率）仍然有效。Error 類的損失直接影響 bug 發現速度 — 容忍度比 event 低一個數量級。中型以上規模的 < 1% / < 0.1% 接近商業方案（Sentry / Datadog）的 SLA 水準。

[Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/) 的 error 快通道設計就是基於這個優先級差異。

## 被自己的 SDK DDoS

「SDK 產生的流量壓垮自己的 collector」是自架監控系統最常見的可靠性事故。來源是自家 SDK 的異常行為或正常行為在特定條件下的放大效應 — 內部流量失控，而非外部攻擊。外部偽造流量的防護見 [Client-side SDK 認證](/monitoring/07-security-privacy/client-sdk-authentication/)。

本段按觸發場景分類（SDK bug / 部署推送 / 使用者暴增），和 [Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/) 的四層防線（SDK 端 / collector 單機 / 水平擴展 / queue 解耦）是不同切面。四層防線按防護位置劃分、說明機制怎麼做；本段按場景劃分、說明什麼時候哪些機制會被觸發。

### SDK bug：事件風暴

SDK 程式碼 bug 導致事件無限迴圈 — 常見於事件處理器內再次觸發事件（error handler 中呼叫 `monitor.event()` 又觸發 error），或 UI 事件綁定錯誤導致每個 frame 產生一筆事件（60 fps = 每秒 60 筆）。

**損失路徑**：事件風暴首先填滿 SDK buffer → 觸發高頻 flush → collector 收到大量 request → channel 滿觸發 429 → SDK 動態降採樣。如果 SDK 的動態降採樣邏輯本身也有 bug（降到 0.1 後不再降），collector 仍然會持續承壓。

**防護層級**：

SDK 端 — 事件產生速率上限。SDK 內部維護每秒事件計數器，超過閾值（例如 100 events/sec）後的事件直接丟棄，不進 buffer。這個上限獨立於取樣和背壓機制，是防止 SDK 自身 bug 的最後一道防線。

```text
// SDK 端的 rate limiter（偽碼，各語言實作不同）
count = atomicIncrement(eventCounter)
if count > maxEventsPerSecond:
    atomicIncrement(droppedCounter)
    return  // 不進 buffer
```

Collector 端 — per-key rate limit。每個 API key（或 source.app）的請求速率獨立限制。一個失控的 SDK 被限速時，其他 SDK 的事件不受影響。這和 [Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/) 的 per-SDK rate limiting 是同一個機制。

Collector 端 — circuit breaker。如果某個 API key 的 429 回應次數在短時間內超過閾值，collector 暫時拒絕該 key 的所有請求（回 503），不再逐筆檢查 rate limit。冷卻期過後自動恢復。這降低了 rate limit 本身的 CPU 開銷 — 高頻 429 回應也有成本。閾值需高於正常 burst 的 per-key 429 頻率 — 如果正常 flush 在 burst 時每分鐘最多觸發 N 次 429，circuit breaker 閾值設為 5N-10N 避免誤觸。具體數字（例如 50 次/分鐘、5 分鐘冷卻）依部署規模調整。

### 部署推送：補發風暴

100 台機器同時重啟（rolling deploy），每台機器的 SDK 在啟動時：

1. 讀取本地 persistence 中的離線事件
2. 初始化後立即 flush 離線事件 + 新的 lifecycle 事件

100 個 SDK 在幾秒內同時發起離線補發 + 正常 flush，collector 瞬間承受 100 倍的正常流量。

**防護方式**：init jitter — SDK 初始化後不立即 flush，而是等待一個隨機延遲（0 到 flush_interval 之間的均勻分佈）。100 個 SDK 的首次 flush 分散在 0-30 秒內，流量從一個尖峰變成斜坡。

```python
import random
initial_delay = random.uniform(0, flush_interval_seconds)
# 第一次 flush 延遲 initial_delay 秒，後續按正常 interval
```

離線補發也加 jitter — 每批補發之間的間隔從固定的 1 秒改為 1-3 秒的隨機值。100 個 SDK 的補發批次在時間軸上交錯，避免所有 SDK 以相同節奏同時送出。

### 使用者行為高峰：同時在線暴增

行銷活動、媒體報導、季節性高峰 — 同時在線使用者從 100 人暴增到 10,000 人。每個使用者的 SDK 正常運作，但總量超出 collector 的處理能力。

這個場景和 SDK bug 的差異：每個 SDK 的行為完全正常，問題在總量。Per-key rate limit 不會觸發（每個 SDK 的速率在正常範圍），需要的是全域流量控制。

**防護方式**：Collector 端的全域 channel 背壓（[Ingestion Scaling 第二層](/monitoring/04-collector/ingestion-scaling/)）是第一道防線 — channel 滿時所有 SDK 收到 429，各自動態降採樣。如果動態降採樣後流量仍然過大，水平擴展（多 collector + load balancer）或 queue 解耦是解法。

行銷活動的可預測性是優勢 — 活動日期已知，可以提前擴展 collector 容量（加機器或調高 channel 容量）。突發的媒體報導則依賴動態降採樣和背壓的自動調節。

### 三種場景的防護對照

| 場景       | 流量特徵        | 首要防護                          | 次要防護              |
| ---------- | --------------- | --------------------------------- | --------------------- |
| SDK bug    | 單 SDK 異常高頻 | SDK 端 rate limit + per-key limit | Circuit breaker       |
| 部署推送   | 多 SDK 同時突發 | Init jitter + 補發 jitter         | Channel 背壓          |
| 使用者暴增 | 全域持續高量    | 動態降採樣 + channel 背壓         | 水平擴展 / queue 解耦 |

## 資料恢復 vs 接受損失

每個損失點都可以投入工程努力降低損失量。問題是恢復的工程成本是否值得 — 監控資料不是交易紀錄，恢復的價值取決於損失的事件類型和數量。

### 值得恢復的場景

**Error 事件**：每筆 error 都可能對應一個需要修的 bug。Error 的損失代表 bug 可能更晚被發現、在更多使用者身上發生後才被注意到。值得投入本地 persistence、優先級丟棄（error 最後丟）、error 快通道等機制降低損失。

**Lifecycle 事件**：session 邊界（session.begin / session.end）是 cohort 分析和 session replay 的基礎。丟失 session 邊界會讓整個 session 的事件無法正確歸屬。Lifecycle 事件量低（每 session 幾筆），保留成本小、損失影響大。

### 接受損失的場景

**高頻 metric 事件**：render.frame_time 每秒 60 筆，丟幾筆對趨勢分析的影響在統計誤差範圍內。聚合前移（SDK 端每 5 秒送一筆 summary）比逐筆保留更有效率。

**行為 event 事件**：button.click、page.view 在取樣後丟幾筆，funnel 的轉換率計算用取樣校正（除以取樣率）仍然有效。單筆行為事件的 debug 價值低 — 知道某使用者點了某按鈕通常不影響決策。

**超過保留期的原始事件**：purge 後只剩聚合摘要。如果分析需求發現需要更長的原始事件保留期，調整 retention config，不要嘗試從聚合摘要「恢復」原始事件 — 那是不可能的。

### 恢復成本的判斷

本地 persistence（SDK 端把 buffer 寫到檔案系統）的實作成本和收益：

| 因素     | 記憶體 FIFO（簡單）       | 本地 persistence（完整）              |
| -------- | ------------------------- | ------------------------------------- |
| 實作成本 | array + 容量檢查          | 檔案讀寫 + 並發安全 + 容量管理 + 去重 |
| 保護範圍 | 短暫離線（buffer 容量內） | 長時間離線（本地儲存容量內）          |
| 不保護   | app 強制終止              | app 強制終止（寫入中的事件仍然遺失）  |
| 適用場景 | 自用工具、SDK 初期版本    | 行動 app、離線場景頻繁的使用環境      |

MVP 階段用記憶體 FIFO。本地 persistence 作為第二階段功能，在離線損失率超出可接受範圍時投入。

## 下一步路由

- SDK 端的離線保護 → [離線 buffer 與重試](/monitoring/03-sdk-design/offline-buffer/)
- Collector 端的流量防護 → [Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/)
- Collector 的處理鏈路 → [Collector 架構](/monitoring/04-collector/architecture/)
- Container 環境的 graceful shutdown → [Container 部署設計](/monitoring/04-collector/container-deployment/)
- 保留策略和降採樣 → [規模演進](/monitoring/04-collector/scaling-evolution/)
- SDK 認證和偽造流量防護 → [Client-side SDK 認證](/monitoring/07-security-privacy/client-sdk-authentication/)
