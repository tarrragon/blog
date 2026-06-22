---
title: "Index Lifecycle Management 與 Log Pipeline"
date: 2026-06-22
description: "說明 Elasticsearch ILM policy 設計、data stream / rollover、Beats vs Elastic Agent 採集選擇、ingest pipeline 與 shard sizing、cross-cluster 策略與 cost governance"
weight: 10
tags: ["backend", "observability", "elastic-stack", "ilm", "log-pipeline"]
---

> 本文是 [Elastic Stack](/backend/04-observability/vendors/elastic-stack/) 的 vendor deep article，深化 overview「Index Lifecycle Management」跟「採集 pipeline」段。初次接觸 Elastic 的讀者建議先讀 [Elastic Stack 服務頁](/backend/04-observability/vendors/elastic-stack/)。

## 問題情境

Elastic Stack 部署後，工程師通常能快速搜尋到 log。問題出在規模成長後：index 數量膨脹導致 cluster 效能退化、disk 滿了才發現沒有 lifecycle policy、shard 太小或太大造成查詢效能不均、採集 agent 的選擇在 Beats / Logstash / Elastic Agent / Fluent Bit 之間搖擺不定。ILM 跟 log pipeline 設計是 Elastic Stack 從「能用」到「可治理」的關鍵步驟。

## 核心概念

### Data Stream vs Index Alias

Elasticsearch 7.9+ 引入 data stream，取代傳統 index alias + rollover 模式。兩者的核心差異：

**Data stream** 是 append-only 的 time-series 資料結構。每個 data stream 下有多個 backing index，由 ILM 自動管理 rollover。寫入只能 append（沒有 update / delete single document），適合 log、metrics、traces。

**Index alias** 是傳統模式 — 手動建立 write alias 指向 current index，配合 ILM rollover action 觸發新 index 建立。支援 update / delete，適合需要修改文件的場景（例如 enrichment pipeline 的 lookup index）。

選擇判讀：time-series 資料（log / metrics / APM trace）一律用 data stream。需要文件修改的 reference data、lookup table 用 index alias。新部署預設用 data stream，除非有明確理由。

### ILM Policy 設計

ILM（Index Lifecycle Management）把 index 的生命週期分成五個 phase：

**Hot phase**：active write + 高頻查詢。Index 在 hot data node 上，用 SSD。Rollover 條件觸發後，current index 變 read-only，新 index 繼續寫入。

**Warm phase**：read-only + 中頻查詢。Index 搬到 warm data node（可以是 HDD 或較便宜的 SSD）。通常在 rollover 後 1-7 天觸發。可以執行 force merge（減少 segment 數量、提升查詢效能）跟 shrink（減少 shard 數量）。

**Cold phase**：searchable snapshot + 低頻查詢。Index 轉成 partial searchable snapshot，資料存在 object storage（S3 / GCS / Azure Blob），本地只保留 cache。查詢可用但較慢。適合 30 天到 1 年的保留。

**Frozen phase**：fully mounted searchable snapshot + 極低頻查詢。資料完全在 object storage，本地無 cache。查詢最慢但成本最低。適合 1 年以上的合規保留。

**Delete phase**：刪除 index。保留期到期後自動清理。

```text
PUT _ilm/policy/application-log-policy
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_primary_shard_size": "30gb",
            "max_age": "1d"
          }
        }
      },
      "warm": {
        "min_age": "3d",
        "actions": {
          "forcemerge": {"max_num_segments": 1},
          "shrink": {"number_of_shards": 1}
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "searchable_snapshot": {
            "snapshot_repository": "s3-repo"
          }
        }
      },
      "delete": {
        "min_age": "365d",
        "actions": {"delete": {}}
      }
    }
  }
}
```

Rollover 條件的選擇：`max_primary_shard_size` 比 `max_size` 更精確（直接控制單一 primary shard 大小）。目標是每個 primary shard 在 20-50 GB 之間。太小（< 5 GB）造成 shard 過多、cluster state 膨脹；太大（> 50 GB）造成 recovery 慢、query 效能下降。

### 儲存成長回推 lifecycle 設計

[Discord 儲存成長案例](/backend/04-observability/cases/discord-storage-growth-observability-gap/)揭露一個在快速成長服務反覆出現的模式：資料量倍增後才發現 ILM 的 hot → warm → cold 邊界不對、hot tier 佔比過高是最常見的成本問題。

問題的根源是 ILM policy 在服務初期設計、之後沒有隨資料量調整。一個服務從 10 GB/day 成長到 100 GB/day 時：

- **Hot tier 膨脹**：原本 hot phase 設 7 天、10 GB/day × 7 天 = 70 GB。成長到 100 GB/day 後、hot tier 變成 700 GB、SSD 成本是原來的 10 倍
- **Warm tier 延遲啟動**：如果 warm phase 的 `min_age` 仍然是 7 天、資料在最貴的 tier 停留太久
- **Cold/frozen phase 未啟用**：初期資料量小時 cold phase 看不到成本效益、成長後才發現 30 天以上的資料全在 warm tier SSD 上

修法是把 ILM review 放進服務的 capacity review cadence（季度或半年）。Review 時看三個指標：`hot_data_size / total_data_size`（hot tier 佔比超過 30% 就該重新評估）、`warm_tier_age_distribution`（warm tier 是否堆了太多舊資料）、`monthly_storage_cost_trend`（成本是否跟資料量同比例增長）。

Searchable snapshot（cold/frozen phase）是成本降幅最大的一步 — 資料從 local SSD 搬到 object storage，儲存成本降 70-90%。但搬遷後查詢延遲從 ms 退化到秒級。判讀「什麼資料該移」的訊號是該 index 在過去 30 天的查詢頻率 — 沒被查過的 index 留在 warm tier 是浪費。

### 採集 Pipeline：Beats vs Elastic Agent vs 第三方

| 採集工具            | 定位                | 適用場景                                        | 管理模式                |
| ------------------- | ------------------- | ----------------------------------------------- | ----------------------- |
| Filebeat            | 單用途 log 採集     | 成熟穩定、資源消耗低、K8s 環境輕量              | 手動 config / ConfigMap |
| Metricbeat          | 單用途 metrics 採集 | host / container / service metrics              | 手動 config             |
| Elastic Agent       | 統一採集 agent      | logs + metrics + security + APM、Fleet 集中管理 | Fleet Server 集中       |
| Logstash            | 重型 ETL pipeline   | 複雜 parsing / enrichment / 多 output           | 手動 config             |
| Fluent Bit / Vector | 第三方輕量 agent    | 多 destination、低 resource、OTel 整合          | 手動 config             |

選擇判讀：

- **新部署、想要集中管理**：Elastic Agent + Fleet。Fleet Server 提供 policy 集中推送、版本升級、health monitoring。代價是 Fleet Server 自身需要維運。
- **既有 Beats 部署、穩定運行**：不急著遷移。Elastic Agent 的 Beats integration 內部仍用 Beats 引擎。
- **K8s 環境、resource 敏感**：Filebeat DaemonSet。資源消耗 ~50-100 MB per node，比 Elastic Agent 低。
- **多 destination（ES + S3 + Kafka）**：Logstash 或 Vector。Beats 的 output 只能寫一個 destination（除非用 output plugin hack）。
- **已有 OTel Collector**：OTel Collector 可以直接把 log 送到 Elasticsearch（OTLP exporter 或 Elasticsearch exporter），不需要額外 Beats。

## 配置 step-by-step

### Ingest Pipeline 設計

Ingest pipeline 在 Elasticsearch 層做 log 的 parsing 跟 enrichment，在 index 前處理。

常用 processor：

- **grok**：regex pattern 解析非結構化 log。適合 nginx access log、syslog 等固定格式。
- **dissect**：delimiter-based parsing。比 grok 快 5-10 倍，但只能處理固定 delimiter 格式。
- **date**：把 log 中的 timestamp string 解析成 `@timestamp`。
- **geoip**：IP 地址轉地理位置。
- **script**：Painless script 做自訂轉換。效能代價高，只在其他 processor 做不到時使用。
- **set / rename / remove**：field 操作。

Pipeline 設計原則：先用 dissect（快）、dissect 做不到才用 grok（慢）。Pipeline 中的 processor 數量跟複雜度直接影響 ingest 吞吐。高 volume 場景（> 10K events/sec per node）要做 ingest pipeline benchmark。

### Mapping Template 與 Dynamic Mapping 治理

Mapping template 定義 index 的 field type。Dynamic mapping 對未知 field 自動建立 mapping — 這是 Elastic 的便利功能，也是最常見的治理問題。

**Dynamic mapping 風險**：application log 帶 arbitrary JSON payload，dynamic mapping 對每個 key 建立 field mapping。一個 log 帶 100 個 unique key → 100 個 field mapping。大量 unique key 會導致 mapping explosion（field 數量爆、cluster state 膨脹、query routing 變慢）。

**治理策略**：

- 用 `dynamic: strict` 或 `dynamic: false`（strict = 拒絕未定義 field、false = 接受但不 index）
- 在 mapping template 明確定義已知 field，用 `dynamic_templates` 控制未知 field 的行為
- 對 arbitrary JSON payload 用 `flattened` field type（ES 7.3+）— 整個 JSON 存為 keyword，可查但不逐 key index

```text
PUT _index_template/app-logs
{
  "index_patterns": ["app-logs-*"],
  "template": {
    "mappings": {
      "dynamic": "strict",
      "properties": {
        "@timestamp": {"type": "date"},
        "message": {"type": "text"},
        "log.level": {"type": "keyword"},
        "service.name": {"type": "keyword"},
        "trace.id": {"type": "keyword"},
        "metadata": {"type": "flattened"}
      }
    }
  }
}
```

### Shard Sizing

Shard sizing 是 Elastic Stack 效能的核心變數。

**目標**：每個 primary shard 20-50 GB（Elastic 官方建議）。每個 data node 管理的 shard 數量上限約 20 per GB heap（預設 heap 一般設 30 GB → ~600 shard per node）。

| 場景                  | 日 ingest 量 | primary shard 數 | rollover 頻率           | 建議                      |
| --------------------- | ------------ | ---------------- | ----------------------- | ------------------------- |
| 小型（< 10 GB/day）   | 5 GB         | 1                | 每天或 max_size 30 GB   | 簡單 ILM 即可             |
| 中型（10-100 GB/day） | 50 GB        | 2-3              | 每天                    | warm + cold ILM           |
| 大型（100+ GB/day）   | 500 GB       | 10-15            | 每小時或 max_size 30 GB | hot-warm-cold-frozen 全用 |

Shard 過多的症狀：cluster state 過大（`_cluster/stats` 的 `indices.shards.total` 數千或數萬）、master node CPU 高（維護 cluster state）、recovery 慢。

Shard 過大的症狀：single shard query 慢（> 500ms for simple filter）、segment merge 時間長、recovery 時單一 shard 復原需要數分鐘。

### Shard count 治理

大量 index 場景（微服務架構下每個服務每天產生一個 data stream backing index）容易累積過多 shard。一個 50 服務的組織、每個服務每天 rollover 一次、primary + 1 replica = 100 shard/day。30 天後 hot + warm tier 有 3000 個 shard。

Elasticsearch 的經驗法則是每個 data node 管理的 shard 數量上限約 20 per GB heap。30 GB heap 的 node 約能管 600 個 shard。3000 個 shard 需要至少 5 個 data node 才不觸發效能退化。

降低 shard 數量的手段：

- **ILM shrink action**：warm phase 把 primary shard 數量縮減（例如 3 → 1）。適合查詢頻率下降的舊 index
- **延長 rollover 週期**：如果單個服務的日資料量只有 1-2 GB，每天 rollover 產生的 shard 太小。調整 rollover 條件為 `max_primary_shard_size: 30gb`（讓系統自動決定 rollover 時機）而非固定 `max_age: 1d`
- **合併小服務**：QPS 很低的服務共用同一個 data stream（用 `service.name` field 區分），減少 data stream 數量

監控指標：`_cat/health` 的 `active_shards` 持續觀察趨勢。設 alert 在 shard count 超過 `data_node_count × 500` 時通知（留 buffer 給 recovery 跟 rebalance）。

## 故障演練與邊界

### ILM rollover 沒觸發

**觸發條件**：ILM policy 已設定但 rollover action 沒有執行。常見原因：index 沒有正確關聯到 ILM policy、或 ILM 被暫停（`_ilm/stop`）。

**判讀**：用 `GET <index>/_ilm/explain` 看 ILM 狀態。`managed: false` 代表 index 不受 ILM 管理。`step: ERROR` 代表 ILM 卡在某個 action。

**修復**：確認 index template 的 `index.lifecycle.name` 指向正確的 ILM policy。如果 ILM step error，用 `POST <index>/_ilm/retry` 重試。

### Searchable snapshot 查詢延遲高

**觸發條件**：cold / frozen phase 的 searchable snapshot index 被高頻查詢。

**表現**：query latency 從 ms 級退化到秒級。原因是每次查詢需要從 object storage（S3 / GCS）拉資料。

**修復**：cold phase 有 local cache、查重複 query 較快；frozen phase 無 cache、每次都拉。如果查詢頻率高到需要 sub-second 回應，這些 index 不應該在 cold/frozen phase — 調整 ILM policy 的 `min_age` 讓它們留在 warm phase 更久。

### Cross-cluster search vs replication

**Cross-cluster search（CCS）**：查詢時 fan-out 到遠端 cluster。適合偶爾跨 cluster 查詢、不需要常駐複製。代價是查詢 latency 包含跨 cluster 的網路延遲。

**Cross-cluster replication（CCR）**：把 index 從 leader cluster 持續複製到 follower cluster。適合 DR、地理就近讀取。代價是複製的 storage 跟網路頻寬成本。

選擇判讀：「偶爾查」→ CCS。「需要低延遲讀 + DR」→ CCR。兩者可以並存。

## 容量與成本

Elastic Stack 的成本由三個維度決定：

**License tier**：Basic（免費、含 ILM / data streams）→ Gold（ML / alerting）→ Platinum（SIEM / endpoint）→ Enterprise。Elastic Cloud 的計費另加 infrastructure cost。

**Data tier storage**：hot tier 用 SSD（最貴）、warm tier 用 HDD 或便宜 SSD、cold/frozen tier 用 object storage（最便宜）。ILM 的 phase 設計直接影響 storage cost。

**Node 數量**：每增加 data node 增加 compute 成本。Shard sizing 跟 ILM 設計決定需要多少 node。

成本最佳化優先序：

1. **ILM + searchable snapshot**：30 天後移到 cold/frozen，storage 成本降 70-90%
2. **Shard sizing**：避免 shard 過多造成的 cluster overhead
3. **Ingest pipeline**：在 ingest 層 drop 不需要的 field，減少 index size
4. **Mapping 治理**：避免 mapping explosion 造成的 cluster state overhead
5. **Retention policy**：明確設定 delete phase，不讓過期資料佔空間

## 整合與下一步

- [Elastic Stack 服務頁](/backend/04-observability/vendors/elastic-stack/)：overview 與日常操作
- [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/)：採集 pipeline 在觀測架構中的定位
- [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/)：mapping drift 跟 field missing 的資料品質面
- [4.C3 Healthcare retention](/backend/04-observability/cases/healthcare-access-traceability-and-retention/)：ILM + searchable snapshot 在合規場景的應用
- [Elastic Cloud migration](../migrate-to-elastic-cloud/)：從自管 Elastic 遷移到 Elastic Cloud
