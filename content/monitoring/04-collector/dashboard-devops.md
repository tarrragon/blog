---
title: "DevOps Dashboard 設計"
date: 2026-06-20
description: "Collector 和 SDK 是否健康 — 日常監控的服務狀態卡、吞吐量曲線、儲存用量，以及告警觸發後的排障視圖"
weight: 8
tags: ["monitoring", "collector", "dashboard", "devops", "health", "alerting"]
---

DevOps dashboard 的消費者是維護 collector 的人 — 可能是開發者自己、可能是開源使用者的運維人員。這個 dashboard 不看被監控 app 的業務邏輯，只看 collector 這個基礎設施本身是否健康、各 SDK 實例是否正常回報。

使用模式是混合型：平時靠告警被動通知，收到通知後到 dashboard 查看細節。日常監控視圖提供「一眼確認系統正常」的能力，告警觸發視圖提供「出事了去哪裡查」的排障路徑。

## 日常監控視圖

### 服務狀態卡

一個狀態卡顯示 collector 的存活狀態和各 SDK 實例的最後心跳時間。狀態卡的設計是「綠色代表正常、紅色代表異常」的二元判斷 — 不需要使用者解讀數字。

Collector 存活的判斷依據是 health endpoint 回應。各 SDK 實例的狀態依據是最後一次 `sdk.heartbeat` 事件的時間 — 超過設定的逾時閾值（預設 10 分鐘）標為離線。

需要的事件：`collector.health.check`（collector 自身定期產生）、`sdk.heartbeat`（各 SDK 定期送出）、`sdk.init`（SDK 啟動時送出、標記上線）。

### 吞吐量曲線

折線圖顯示過去 24 小時每分鐘收到的事件數量。多個 SDK 實例用不同顏色區分。吞吐量的正常範圍由歷史資料建立基線 — 突然下降代表某個 SDK 停止送資料，突然上升代表 error storm 或重複送出。

需要的事件：`collector.ingestion.count`（collector 每分鐘記錄收到的事件數，按 source.app 分群）。

### 儲存用量

磁碟使用率的趨勢圖 + 保留策略的執行狀態。開發者需要知道「磁碟什麼時候會滿」和「purge 有沒有正常跑」。

需要的事件：`collector.storage.disk_usage`（定期取樣、metric 類型）、`collector.storage.purge.completed`（每次 purge 完成時記錄清了多少空間）。

### SDK 連線列表

表格列出所有已知的 SDK 實例，每行顯示：app 名稱、版本、平台、最後回報時間、最後一次 init 時間。表格按「最後回報時間」排序 — 最久沒回報的在最上面，方便發現異常。

需要的事件：`sdk.init`（帶 source 完整資訊）、`sdk.heartbeat`（定期更新最後回報時間）。

Heartbeat 的觸發機制是 flush timer 的副作用 — SDK 的 flush timer 觸發時，如果 buffer 為空且距上次 heartbeat 超過設定間隔（預設 5 分鐘），自動注入一筆 `sdk.heartbeat` 事件後送出。不需要獨立的 heartbeat timer。App idle 時 heartbeat 仍會送出，dashboard 的 SDK 連線列表因此能偵測 SDK 是否仍存活。

## 告警觸發視圖

告警由 rule engine 觸發，觸發後開發者進入 dashboard 查看細節。每種告警條件對應一個排障路徑。

### Health check 失敗

Collector 的 health endpoint 連續 N 次回應失敗（由外部 uptime check 偵測、如 cron + curl）。

進入 dashboard 後看：最後一次 `collector.health.check` 的時間和結果、collector 的 stderr log（systemd journal）、process 是否存活。如果 collector 已經掛了，dashboard 本身也不可達 — 這時的排障路徑是 SSH 到主機查 systemd 狀態。

### SDK 停止回報

某個 SDK 實例超過逾時閾值沒有送 `sdk.heartbeat`。可能原因：被監控 app 當掉、網路斷開、SDK 初始化失敗。

進入 dashboard 後看：該 SDK 的最後事件（什麼類型、什麼時間）、最後 `sdk.init` 的 source 資訊（版本、平台）、同時段其他 SDK 是否正常（區分「單一 SDK 問題」和「collector 端問題」）。

### 磁碟用量超過閾值

`collector.storage.disk_usage` 超過 80%。

進入 dashboard 後看：各 backend 的空間佔比（SQLite DB 大小 + 匯出檔大小）、最近一次 purge 的執行時間和清理量、保留策略的設定值。如果 purge 正常執行但空間仍不足，代表事件產生速度超過清理速度 — 需要調整保留策略或擴容磁碟。

### 事件吞吐量異常下降

每分鐘事件數從正常基線突然下降超過 50%。

進入 dashboard 後看：吞吐量曲線標注「下降起始時間」、SDK 連線列表確認哪些 SDK 在該時間點後停止回報、collector 的 ingestion error log。

## 需要的事件總表

| 事件名稱                          | 類型      | 產生者     | 用途                    |
| --------------------------------- | --------- | ---------- | ----------------------- |
| collector.health.check            | lifecycle | Collector  | 服務狀態卡              |
| collector.started                 | lifecycle | Collector  | 部署追蹤                |
| collector.shutdown                | lifecycle | Collector  | 異常關閉偵測            |
| collector.ingestion.count         | metric    | Collector  | 吞吐量曲線              |
| collector.storage.disk_usage      | metric    | Collector  | 儲存用量圖              |
| collector.storage.purge.completed | lifecycle | Collector  | purge 執行記錄          |
| sdk.heartbeat                     | lifecycle | SDK        | 連線列表、存活判斷      |
| sdk.init                          | lifecycle | SDK        | 版本/平台資訊、上線記錄 |
| deployment.started                | lifecycle | CI/CD hook | 部署追蹤                |
| deployment.completed              | lifecycle | CI/CD hook | 部署追蹤                |
| rule.matched                      | event     | Collector  | alert 歷史              |

這些事件是 collector 自身的營運事件，和被監控 app 的事件走同一個 Storage interface 儲存。Collector 同時是事件的生產者和消費者 — `collector.ingestion.count` 由 collector 自己產生、自己儲存、自己在 dashboard 顯示。

## 自動恢復設計

自用工具場景下「凌晨三點 collector 掛了」的處理策略是自動恢復，不需要人介入。

| 機制             | 做法                                                | 恢復時間        |
| ---------------- | --------------------------------------------------- | --------------- |
| systemd watchdog | `WatchdogSec=30s`，collector 定期寫 watchdog notify | 30 秒內重啟     |
| Restart policy   | `Restart=on-failure`、`RestartSec=5s`               | 5 秒後自動重啟  |
| Health endpoint  | `/health` 回應 200 + 最後寫入時間                   | 外部 check 偵測 |
| 啟動自檢         | collector 啟動時檢查 storage 完整性、重建索引       | 啟動時自動修復  |

自動恢復後 collector 送出 `collector.started` 事件，dashboard 的服務狀態卡從紅轉綠。如果連續重啟（10 分鐘內重啟 3 次以上），systemd 的 `StartLimitBurst` 阻止無限重啟、改為發送告警通知人工介入。

## 存取控制

Day-one 的 dashboard 預設無認證 — 同區網內的任何裝置都能打開 dashboard URL。這是同區網信任模型的設計選擇，和 collector 的 HTTP endpoint 無認證一致。

### 風險告知

無認證的 dashboard 暴露以下資訊給同區網的所有裝置：

- **DevOps dashboard**：SDK 版本、平台、IP、collector 的磁碟用量
- **Developer dashboard**：error stack trace（可能包含檔案路徑和程式碼片段）、session 回放（使用者操作序列）
- **中台 dashboard**：行為事件明細、funnel 轉換率

家用 LAN 的場景下，家裡的其他裝置（IoT、家人的電腦）也能存取這些資訊。

### 最小防護

Go 的 `net/http` middleware 可以用幾行程式碼加 basic auth：

```go
func basicAuth(next http.Handler, user, pass string) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        u, p, ok := r.BasicAuth()
        if !ok || u != user || p != pass {
            w.Header().Set("WWW-Authenticate", `Basic realm="monitor"`)
            http.Error(w, "Unauthorized", 401)
            return
        }
        next.ServeHTTP(w, r)
    })
}
```

帳密在 collector 的配置檔設定。Day-one 可選（不設就不啟用），但配置檔中應有 commented-out 的範例讓使用者知道這個選項存在。

### Tripwire

Collector 暴露到公網或跨網路存取時，dashboard 的認證從可選變成必要。公網上的無認證 dashboard 等於公開了 error stack trace 和行為資料。

## 下一步路由

- Developer dashboard 設計 → [Developer Dashboard 設計](/monitoring/04-collector/dashboard-developer/)
- 中台 dashboard 設計 → [中台 Dashboard 設計](/monitoring/04-collector/dashboard-business/)
- Rule engine 的告警設計 → [Rule engine 設計](/monitoring/04-collector/rule-engine/)
- Collector 自我監控的 bootstrapping 問題 → [規模演進](/monitoring/04-collector/scaling-evolution/)
