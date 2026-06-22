---
title: "Remote Write 與長期儲存整合"
date: 2026-06-22
description: "說明 Prometheus remote write 的配置、三家長期儲存後端比較（Mimir / Thanos / Cortex）、故障模式與容量規劃"
weight: 12
tags: ["backend", "observability", "prometheus", "remote-write", "long-term-storage"]
---

> 本文是 [Prometheus](/backend/04-observability/vendors/prometheus/) 的 vendor deep article，深化 overview「Remote write / read」段。初次接觸 Prometheus 的讀者建議先讀 [Prometheus 服務頁](/backend/04-observability/vendors/prometheus/)。

## 問題情境

Remote write 把 Prometheus 的 metrics 即時推送到外部長期儲存，解決單機 retention 上限與跨實例統一查詢的限制。三個觸發點會讓團隊需要 remote write 與長期儲存：

Prometheus 預設 retention 是 15 天。業務需要回顧 90 天的趨勢（容量規劃、季度 SLO 報告、成本歸因），本地 disk 不夠放。加大 disk 可以延長 retention，但 Prometheus 的查詢效能會隨資料量下降 — 本地 TSDB 不做 downsampling，查 90 天 range 的 query 要掃描全量 sample。

多個 Prometheus 實例分散在不同叢集（prod-us、prod-eu、staging），團隊需要一個統一查詢入口看跨叢集 metrics。每個 Prometheus 各自保存自己的資料，沒有跨實例查詢能力。手動切換 Grafana datasource 容易遺漏某個叢集的異常。

單機 Prometheus 是 SPOF — process crash 或 VM 故障時 metrics 完全不可用。跑兩個 Prometheus 各自 scrape 同一組 target 可以達到 HA，但兩份資料有微小差異（scrape 時間偏移），下游查詢需要 dedup。

Remote write 解決這三個問題：Prometheus 保持短期本地儲存（scrape + 即時查詢），同時把 metrics 串流到長期儲存後端。長期後端負責壓縮、downsampling、跨實例查詢與 HA dedup。

## 核心概念

### Remote write protocol

Prometheus 透過 HTTP POST 把 time series 送到 remote write endpoint。每次 POST 包含一批 samples（protobuf 編碼、snappy 壓縮），由 Prometheus 的 WAL（write-ahead log）驅動 — WAL 記錄所有 scrape 到的 samples，remote write 從 WAL 讀取並串流到遠端。

這個設計意味著 remote write 是 best-effort 但有 buffer：如果遠端暫時不可達，samples 會堆在 WAL 裡等重試。WAL 的大小有上限（`--storage.tsdb.wal-segment-size`，預設 128 MB per segment），堆積太多會導致 WAL 佔用大量 disk。

### Exemplar forwarding

Prometheus 2.26 開始支援 exemplar — 在 histogram 或 counter sample 上附加 trace_id / span_id。Remote write 也能把 exemplar 送到支援的後端（Mimir、Grafana Cloud、Tempo）。Exemplar 讓讀者從 metric anomaly 一鍵跳到對應的 trace，是 metrics-to-traces 橋接的關鍵能力。

啟用方式：scrape config 加 `enable_features: [exemplar-storage]`，remote write endpoint 支援 exemplar 即可自動 forward。

### Dedup 策略

跑兩個 Prometheus HA pair 時，兩個實例都 scrape 同一組 target、都 remote write 到同一個後端。後端會收到兩份幾乎相同但不完全一致的 samples（scrape 時間差 ±1-2 秒）。

Thanos 和 Mimir 都有 dedup 機制：Thanos 在 query 層根據 `external_labels`（replica label）做 dedup，每個 time window 只取一個 replica 的值。Mimir 在 ingester 層做 dedup，同一個 series 的重複 sample 在寫入時合併。

Dedup 的前提是兩個 Prometheus 實例設定不同的 `external_labels`（例如 `replica: a` / `replica: b`），讓後端能辨別哪些 series 是同一組的不同副本。

## 配置

### Remote write 基本設定

```yaml
# prometheus.yml
remote_write:
  - url: "http://mimir-distributor:9009/api/v1/push"
    queue_config:
      capacity: 10000
      max_shards: 30
      max_samples_per_send: 5000
      batch_send_deadline: 5s
    write_relabel_configs:
      - source_labels: [__name__]
        regex: "go_.*"
        action: drop
```

`queue_config` 控制 remote write 的並行度與批次大小：

- `capacity`：內存中暫存的 sample 數量。太小會頻繁 flush、太大會佔記憶體
- `max_shards`：並行的 write goroutine 數量。Shard 太少會造成 backlog、太多會壓垮遠端
- `max_samples_per_send`：每次 POST 的 sample 數量。5000 是常用值
- `batch_send_deadline`：即使 batch 沒滿也在這個時間內 flush，避免低流量時 sample 延遲太久

`write_relabel_configs` 在 remote write 前過濾 series — 不需要長期保存的 internal metrics（go runtime、scrape metadata）可以在這裡 drop，減少長期儲存的 cardinality 與成本。

### External labels（HA 與多叢集）

```yaml
global:
  external_labels:
    cluster: prod-us
    replica: a
```

`cluster` label 區分來源叢集，`replica` label 讓長期儲存做 dedup。每個 Prometheus 實例的 external_labels 必須唯一。

### 三家長期儲存比較

| 維度         | Mimir                                                        | Thanos                                      | Cortex                                              |
| ------------ | ------------------------------------------------------------ | ------------------------------------------- | --------------------------------------------------- |
| 架構模式     | Microservice（distributor / ingester / compactor / querier） | Sidecar + Store Gateway + Compactor + Query | Microservice（跟 Mimir 同源、Mimir 是 Cortex fork） |
| 部署複雜度   | 中（Helm chart，最少 4 個元件）                              | 中高（sidecar 綁 Prometheus pod，元件分散） | 高（元件多、已進入維護模式）                        |
| Query layer  | 原生 PromQL + split/merge                                    | Thanos Query 做 fan-out + dedup             | 原生 PromQL（跟 Mimir 共用）                        |
| 多租戶       | 原生（X-Scope-OrgID header）                                 | 有限（靠 label 或獨立部署）                 | 原生（Mimir 繼承）                                  |
| Downsampling | 支援（compactor 做 1h/5m 降取樣）                            | 支援（compactor）                           | 支援                                                |
| 開發狀態     | 活躍（Grafana Labs 主推）                                    | 活躍（CNCF incubating）                     | 維護模式（Grafana Labs 把精力轉到 Mimir）           |
| 對象儲存     | S3 / GCS / Azure Blob                                        | S3 / GCS / Azure Blob / 本地                | S3 / GCS                                            |
| 成本模型     | 自管 compute + storage；Grafana Cloud 按 active series 計費  | 自管 compute + storage                      | 自管（不推薦新部署）                                |

選擇判準依三個維度排序：

**已經在用 Grafana 生態**（Grafana dashboard、Loki、Tempo）：Mimir 是最自然的選擇，跟 Grafana Stack 的整合最深，Grafana Cloud 可以免管 Mimir。

**需要最小化對 Prometheus 的改動**：Thanos sidecar 模式不改 Prometheus 配置（sidecar 讀本地 TSDB block），適合「先加長期儲存、Prometheus 維持現狀」的漸進路徑。但 sidecar 綁 Prometheus pod，K8s 環境外的部署更複雜。

**多租戶需求**：Mimir 原生支援多租戶隔離（每個 tenant 獨立 TSDB、query isolation），Thanos 的多租戶靠 label 或獨立部署。

Cortex 是 Mimir 的前身，新部署不推薦。既有 Cortex 部署可參考 Grafana Labs 的 Mimir migration guide。

### Uber M3 的第四條路

[Uber M3 案例](/backend/04-observability/cases/uber-m3-metrics-platform-scale/)選擇了自建 M3DB 而非 Mimir / Thanos / Cortex — 原因是 M3DB 在 2018 年啟動時、Mimir 尚未存在、Cortex 還在早期階段、Thanos 也剛開源。M3DB 的設計核心是 namespace-level retention（不同 namespace 不同 retention 跟 resolution）、跟 Uber 的 etcd service discovery 深度整合。

M3 的經驗對後來的三家有直接影響：Mimir 的 per-tenant retention、Thanos 的 downsampling compactor、都能追溯到 M3 先踩過的問題。今天做新部署不需要重走 M3 的路 — Mimir 跟 Thanos 已經成熟。但 M3 案例揭露的設計判準仍然有效：

- **跨 cluster 查詢需要 fan-out + dedup**：三家都實作了這個能力，但部署配置跟 dedup 策略各有差異
- **Downsampling 是長期成本控制的必要手段**：不做 downsampling、90 天 range query 的效能跟成本都不可接受
- **多租戶隔離不只是 query 層面**：ingestion rate limit 跟 storage quota per tenant 才能防止「一個團隊的 cardinality 爆炸拖垮整個平台」

## 故障與邊界

### Remote write backlog 佔滿 WAL

**觸發條件**：遠端不可達（network 問題、後端過載）持續超過數分鐘，WAL segment 堆積。

**表現**：`prometheus_remote_storage_bytes_total` 停止增長（寫不出去）、`prometheus_wal_storage_size_bytes` 持續增長、disk 使用率上升。嚴重時 WAL 佔滿 disk，Prometheus 無法寫入新 sample、連 local scrape 也受影響。

**修復**：先恢復遠端連線。WAL backlog 會在連線恢復後自動 catch up — Prometheus 按 WAL 順序重送積壓的 samples。如果 catch up 時間太長（例如堆了數小時），remote write 的 max_shards 可以暫時調高加速回補，但要注意不要壓垮剛恢復的遠端。

**預防**：監控 `prometheus_remote_storage_queue_highest_sent_timestamp_seconds` 跟 current time 的差距 — 差距代表 remote write 延遲。差距超過 5 分鐘時告警。設定 WAL 的 disk 空間上限（`--storage.tsdb.max-block-duration` 搭配 retention 控制 total disk）。

### Target 不可達時的 retry storm

**觸發條件**：remote write endpoint 回傳 5xx 或 429（rate limit），Prometheus 進入指數退避重試。大量 shard 同時 retry，CPU 跟 network 消耗上升。

**表現**：`prometheus_remote_storage_retried_samples_total` 增長、CPU 使用上升、remote write 延遲拉大。如果後端本來就過載，retry storm 會讓情況惡化。

**修復**：remote write 配置中的 `min_backoff` / `max_backoff` 控制 retry 間隔（預設 30ms / 5s）。可以調高 `min_backoff` 減緩 retry 頻率。長期修法是讓後端回傳 429 搭配 `Retry-After` header，Prometheus 會遵守。

### Metrics 語意 drift

**觸發條件**：多個 Prometheus 實例的 `write_relabel_configs` 不一致、或 external_labels 設定有誤。

**表現**：同一個 metric 在長期儲存中出現語意不同的 series — 有些 instance 保留了某個 label、有些 drop 掉了。Dashboard 查詢結果不一致（取決於查到哪個實例的 series）。

**修復**：remote write 的 `write_relabel_configs` 集中管理（配置模板或 Prometheus Operator 的 PrometheusSpec.remoteWrite）。每次修改 relabel 規則後，驗證所有實例的 series label set 一致。Mimir 的 `active_series` API 可以列出目前所有 active series 的 label set。

### Remote write protocol 版本不匹配

**觸發條件**：Prometheus 版本跟長期儲存後端期望的 remote write protocol 版本不一致。Prometheus 2.x 使用 remote write v1（protobuf + snappy），部分較新後端開始支援 v2（native histogram 支援、metadata 改進）。

**表現**：後端回傳 400 Bad Request。Prometheus 對 4xx 的預設行為是不 retry（視為 client error、retry 無意義），samples 被 drop。`prometheus_remote_storage_samples_failed_total` 增長但不像 5xx 那樣有明顯的 retry storm — 靜默丟失更難察覺。

**修復**：確認 Prometheus 版本跟後端的 protocol 相容性。Mimir / Thanos 的文件通常標明支援的 remote write protocol 版本。版本不匹配時升級 Prometheus 或降級後端配置。

### 何時單機 Prometheus 不夠

三個訊號同時出現時，remote write + 長期儲存從「可選」變成「必要」：

**Active series 超過 500 萬**。單機 Prometheus 在 500 萬 series 左右開始出現記憶體壓力（head block ~20 GB）、WAL replay 時間拉長（重啟要數分鐘）、compaction 佔用 CPU。[Uber 在 M3 專案](/backend/04-observability/cases/uber-m3-metrics-platform-scale/)遇到的正是這個天花板 — 數十個叢集各自 scrape 的 metrics 匯總後 series 數遠超單機能力，但「用更大的 VM 跑 Prometheus」不是解法，因為 Prometheus 的 TSDB 是單線程 compaction、垂直擴展的效益有上限。

**Retention 需求超過 30 天**。本地 TSDB 的 retention 拉長時，range query 的效能線性退化 — 查 90 天 range 要掃描的 block 數量是 15 天的 6 倍。Downsampling 是長期儲存後端的標準能力（Mimir / Thanos compactor 把 5 分鐘 resolution 降到 1 小時），但 Prometheus 本地 TSDB 不做 downsampling。Uber 的 M3DB 設計了 namespace-level retention（short-term 48h full resolution、long-term 1y downsampled），讓查詢成本不隨 retention 線性成長。

**跨叢集統一查詢**。多個 Prometheus 各自 scrape 不同 cluster 時，工程師需要一個入口看「所有 cluster 的 checkout error rate」。手動切 Grafana datasource 容易遺漏。Remote write 把所有 Prometheus 的 metrics 匯入同一個長期儲存、用單一查詢入口（Mimir querier / Thanos Query）做 fan-out。

這三個需求在中型公司（50-200 服務、3+ K8s cluster）通常在 1-2 年內同時浮現。規劃 remote write 時不用等三個都出現 — 任一個出現就是啟動的合理時機。

## 容量與 Cost

### Remote write bandwidth

Remote write 的 bandwidth ≈ ingestion rate × 每 sample 壓縮後大小（約 1-2 bytes with snappy）。

| Ingestion rate      | 估算 bandwidth   | 對應規模參考               |
| ------------------- | ---------------- | -------------------------- |
| 10 萬 samples/sec   | ~100-200 KB/s    | 小型：5-10 服務、1 cluster |
| 50 萬 samples/sec   | ~500 KB/s-1 MB/s | 中型：50 服務、2-3 cluster |
| 200 萬 samples/sec  | ~2-4 MB/s        | 大型：200 服務、5+ cluster |
| 1000 萬 samples/sec | ~10-20 MB/s      | 平台級：Uber M3 等級       |

每個 active series 在 15 秒 scrape interval 下每秒產生 ~0.067 個 sample。100 萬 active series 的 ingestion rate ≈ 6.7 萬 samples/sec，對應 ~70-140 KB/s remote write bandwidth。這個數字在內網環境下通常不是瓶頸。

真正的瓶頸在兩個地方：**roundtrip latency** 決定單 shard 吞吐上限（每次 POST 等回應才發下一批）、**後端 ingestion capacity** 決定能消化多少 samples/sec。Mimir 的 distributor 跟 ingester 可以水平擴展，但每加一個 ingester 增加 compute 成本。bandwidth 只是 capacity planning 的第一步，實際規模要用 Mimir 的 `cortex_distributor_received_samples_total` 跟 `cortex_ingester_memory_series` 做持續觀測。

### 長期儲存的 compaction 與 downsampling cost

Mimir 和 Thanos 的 compactor 定期合併 block 並做 downsampling（5m → 1h 粒度）。Compaction 消耗 CPU 和 disk I/O，但跑在長期儲存自己的 compute 上，不影響 Prometheus。

成本結構：

- **Compute**：distributor + ingester + querier + compactor 的 CPU / memory。Mimir 官方建議 ingester 是最吃資源的元件（記憶體中保存 active series）
- **Object storage**：S3 / GCS 的儲存量 ≈ ingestion rate × retention × 壓縮率。Compaction 跟 downsampling 會降低儲存量（通常 2-5x 壓縮）
- **Query cost**：長 range query 需要讀大量 block — 在 cloud object storage 上是 GET request 成本。Mimir 用 index cache（memcached）降低重複查詢的 GET request

跟 Prometheus 本地 TSDB 比，長期儲存把 disk cost 換成 object storage cost（通常更便宜），但增加了 compute cost（長期儲存的 ingester / querier / compactor）。判斷轉折點的方式是比較本地 SSD cost × retention 跟 object storage cost + compute cost。retention 超過 30 天時，object storage 的成本優勢通常明顯。

## 整合與下一步

### 接 Grafana Stack LGTM

Mimir 是 [Grafana Stack](/backend/04-observability/vendors/grafana-stack/) LGTM（Loki + Grafana + Tempo + Mimir）的 metrics 後端。Prometheus remote write 到 Mimir 後，Grafana 用 Mimir 作為 Prometheus-compatible datasource，查詢語言仍是 PromQL。Exemplar forwarding 讓 Mimir metrics 可以連結到 Tempo traces。

### 接 Telemetry Pipeline

Remote write 在 [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/) 中扮演 metrics ingestion 段。如果同時使用 OpenTelemetry Collector，Collector 可以作為 remote write 的中繼（接收 Prometheus scrape → OTLP export → Mimir OTLP endpoint），但多一層中繼增加了 failure point。直接 Prometheus → Mimir remote write 是最簡路徑。

### 接 Cost Attribution

長期儲存的多租戶能力讓 [4.15 cost attribution](/backend/04-observability/cost-attribution/) 可以按 tenant / team / service 拆分 metrics 成本。Mimir 的 per-tenant active series quota 同時控制 cardinality 與成本。

## 交接路由

- [Prometheus 服務頁](/backend/04-observability/vendors/prometheus/)：overview 跟日常操作入口
- [PromQL 與 Recording Rules 實務](../promql-recording-rules/)：remote write 架構下 recording rules 的部署位置選擇
- [容量規劃與故障模式](../capacity-failure-modes/)：remote write 作為容量超限時的卸載路徑
- [Grafana Stack](/backend/04-observability/vendors/grafana-stack/)：Mimir 作為長期儲存的完整操作指南
- [4.11 Telemetry Pipeline](/backend/04-observability/telemetry-pipeline/)：remote write 在 pipeline 架構中的定位
- [4.15 Cost Attribution](/backend/04-observability/cost-attribution/)：多租戶 metrics 的成本拆分
