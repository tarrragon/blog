---
title: "LGTM Stack 組合運維：Loki + Grafana + Tempo + Mimir"
date: 2026-06-22
description: "說明 Grafana Stack 四個元件的責任分工、部署模式、常見故障與 dashboard provisioning"
weight: 10
tags: ["backend", "observability", "grafana", "loki", "tempo", "mimir"]
---

> 本文是 [Grafana Stack](/backend/04-observability/vendors/grafana-stack/) 的 vendor deep article，深化 overview 的元件組合段。初次接觸 Grafana Stack 的讀者建議先讀 [Grafana Stack 服務頁](/backend/04-observability/vendors/grafana-stack/)。

## 定位

Grafana Stack（LGTM = Loki + Grafana + Tempo + Mimir）是自架觀測平台的完整選項，四個元件各自承擔一類訊號的儲存跟查詢。理解每個元件的責任邊界、部署模式跟故障特性，才能避免「裝了四個元件但不知道哪個壞了」的黑盒問題。

## 四元件的責任分工

| 元件    | 訊號類型 | 查詢語言 | 儲存後端                | 角色                          |
| ------- | -------- | -------- | ----------------------- | ----------------------------- |
| Loki    | Log      | LogQL    | Object storage + BoltDB | Log aggregation、grep 替代品  |
| Mimir   | Metric   | PromQL   | Object storage          | Prometheus 的可擴展長期儲存   |
| Tempo   | Trace    | TraceQL  | Object storage          | Trace 儲存、span 搜尋         |
| Grafana | 視覺化   | —        | —                       | Dashboard、alert、data source |

Grafana 是查詢 / 視覺化層，Loki / Mimir / Tempo 是儲存 / 查詢層。Grafana 本身不存觀測資料，它連接 data source（Loki / Mimir / Tempo / Prometheus / Elasticsearch）做查詢跟渲染。

四個元件獨立部署、獨立擴展、各自有健康指標。一個元件故障不影響其他元件 — Loki 掛了時 Grafana 的 metric dashboard 跟 trace 查詢仍然正常，只有 log panel 會報錯。

## 部署模式

### Monolithic mode

四個元件（或其中幾個）跑在同一個 process / container。適合小規模（每天數 GB log、數十萬 metric series、少量 trace）。部署最簡單 — 一個 docker-compose 或 Helm chart 起全套。

限制是沒辦法獨立擴展 — log 量大但 metric 量小時，monolithic mode 不能只加 Loki 的資源。

### Microservices mode

每個元件拆成獨立的 deployment、各自 autoscaling。Loki 拆成 distributor / ingester / querier / compactor；Mimir 拆成類似的元件；Tempo 也有對應的分層。

適合中到大規模。部署跟維運複雜度顯著上升 — 每個元件的每個子服務都需要獨立的 health check、autoscaling 設定、persistent volume。

### 選擇判準

| 條件                                  | 建議模式              |
| ------------------------------------- | --------------------- |
| 團隊 < 5 人、日 log < 10 GB           | Monolithic            |
| 需要獨立擴展某一類訊號                | Microservices         |
| 不想自管、預算足夠                    | Grafana Cloud         |
| 已有 Prometheus、只需要加 log / trace | 漸進式加 Loki + Tempo |

## 常見故障模式

### Loki：ingester OOM

Loki ingester 把 log chunks 保存在記憶體，高流量時容易 OOM。觸發條件是突然的 log 量爆增（部署後 error storm、某服務開了 debug log level）。

判讀指標：`loki_ingester_memory_chunks`、`process_resident_memory_bytes`。修復方向：調整 chunk flush interval（更頻繁寫入 object storage、降低記憶體壓力）、加 ingester replica、或在 pipeline 層（OTel Collector）做 log volume rate limit。

### Mimir：compactor 卡住

Mimir compactor 負責合併 ingester 寫入的 block。Compactor 卡住時，block 數量持續增長、query 需要掃描更多 block、延遲上升。

判讀指標：`cortex_compactor_runs_completed_total` 停滯、`cortex_bucket_blocks_count` 持續增長。修復方向：檢查 object storage 的寫入權限跟延遲、增加 compactor 資源（CPU / memory）、或暫時停止 ingestion 讓 compactor 追上。

### Tempo：trace not found

使用者用 trace ID 查詢時回 "trace not found"，但 trace 確實存在。常見原因是 Tempo 的 bloom filter / compacted block index 還沒包含該 trace（ingestion 到可查詢有延遲），或 trace 被 retention policy 刪除。

判讀方式：查 trace 的 timestamp 是否在 retention 範圍內、查 `tempo_ingester_traces_created_total` 確認 ingestion 正常、查 compactor 是否正常運行。

### Grafana：dashboard provisioning 漂移

用 provisioning（YAML / JSON 檔案）管理 dashboard 時，手動在 UI 修改的 dashboard 會在下次 provisioning 同步時被覆蓋。團隊成員在 UI 調整了 panel、下次重啟 Grafana 後修改消失。

修復方向：dashboard 修改統一透過 git → provisioning pipeline（GitOps），UI 只用於臨時調整跟探索。把 provisioning 的 `allowUiUpdates` 設為 false、強制所有變更走 git。

## Dashboard Provisioning

Dashboard 的管理方式影響長期維護成本。手動在 UI 建立 dashboard 的起步最快，但隨 dashboard 數量增長會出現版本不一致、無法 rollback、owner 不明的問題。

### Infrastructure as Code

Dashboard JSON 存在 git repo、透過 provisioning 同步到 Grafana。變更走 PR review、有版本歷史、可以 rollback。

Grafana 的 provisioning 機制讀 YAML config，指定 dashboard JSON 的來源（local file / HTTP / API）。Helm chart 部署時把 dashboard JSON 放在 ConfigMap 或 persistent volume。

### Grafonnet / Jsonnet

用 Jsonnet（Grafana 的 dashboard-as-code library）產生 dashboard JSON。適合大量相似 dashboard 的場景 — 每個服務一個 dashboard，結構相同但 data source 跟 label 不同。

Grafonnet 的學習曲線比直接寫 JSON 高，但在 dashboard 數量 > 20 個時開始有維護效率的回報。

## 下一步路由

- [Grafana Stack 服務頁](/backend/04-observability/vendors/grafana-stack/)：overview 跟日常操作
- [Prometheus 服務頁](/backend/04-observability/vendors/prometheus/)：Mimir 的上游 metric 來源
- [OTel Collector 部署模式](/backend/04-observability/vendors/opentelemetry/collector-deployment-patterns/)：LGTM 的 ingestion 入口
- [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/)：pipeline 各層的治理
- [4.18 operating model](/backend/04-observability/observability-operating-model/)：dashboard / alert 的 ownership
