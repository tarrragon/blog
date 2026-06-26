---
title: "斷網環境的監控與可觀測性"
date: 2026-06-26
description: "Self-hosted 監控（Prometheus + Grafana）、離線 log 收集（Loki / ELK）、不能 phone home 的告警、NTP 時間同步"
weight: 4
tags: ["infra", "air-gapped", "monitoring", "prometheus", "grafana"]
---

斷網環境不能用 Datadog、New Relic、Sentry Cloud、PagerDuty Cloud 這些 SaaS 監控服務——它們全部需要往外發送資料。監控的三個核心能力（metric 收集、log 彙整、告警通知）全部要用 self-hosted 的開源工具在隔離網路內搭建。原則跟連網環境相同（metric 跟資源同生命週期、alarm 要連到動作），差別在工具的部署和儲存規劃要自己管。

## Metric 收集：Prometheus + Grafana

Prometheus 是 pull-based 的 metric 收集系統——它主動去 scrape 各服務的 metric endpoint，不需要服務往外推資料。這個架構天然適合斷網：所有流量都在內網、不需要出站連線。

### 離線安裝

Prometheus 和 Grafana 都是單一二進位或容器映像，離線安裝跟[映像搬運](/infra/air-gapped/air-gapped-container/)相同的流程：

```bash
# 外部：下載 release binary
wget https://github.com/prometheus/prometheus/releases/download/v2.53.0/prometheus-2.53.0.linux-amd64.tar.gz
wget https://dl.grafana.com/oss/release/grafana-11.1.0.linux-amd64.tar.gz

# 搬運後解壓、設定 systemd service
tar xzf prometheus-2.53.0.linux-amd64.tar.gz
sudo mv prometheus-2.53.0.linux-amd64 /opt/prometheus
```

如果用容器部署，先把映像搬進內部 registry 再 pull：

```bash
# 內部：從內部 registry 啟動
docker run -d -p 9090:9090 \
  -v /etc/prometheus:/etc/prometheus \
  -v /data/prometheus:/prometheus \
  registry.internal:5000/prometheus:v2.53.0
```

### Scrape 設定

Prometheus 的 `prometheus.yml` 定義要 scrape 的目標。斷網環境通常用 static config（手動列出目標）而非 service discovery（需要雲端 API）：

```yaml
scrape_configs:
  - job_name: 'node-exporter'
    static_configs:
      - targets:
          - 'server-01:9100'
          - 'server-02:9100'
          - 'db-01:9100'

  - job_name: 'app'
    static_configs:
      - targets:
          - 'app-01:8080'
          - 'app-02:8080'
    metrics_path: '/metrics'
```

新增機器時手動把它加進 targets 清單。如果用 Consul（內網 service discovery），Prometheus 支援 Consul SD、可以自動發現新服務。

### Node Exporter

每台需要監控的 Linux 機器裝一個 node_exporter（單一二進位、無依賴），暴露 CPU、記憶體、磁碟、網路等系統 metric。離線安裝同理——下載 binary、搬運、解壓、設成 service。

```bash
# 搬運後安裝
tar xzf node_exporter-1.8.1.linux-amd64.tar.gz
sudo cp node_exporter-1.8.1.linux-amd64/node_exporter /usr/local/bin/
sudo useradd --no-create-home --shell /bin/false node_exporter
# 建立 systemd service（略）
```

## Log 收集：Loki 或 ELK

### Grafana Loki（輕量）

Loki 是 Grafana 生態的 log 彙整系統，架構類似 Prometheus（pull/push 都支援），但儲存的是 log stream 而非 metric。它不索引 log 內容（只索引 label），所以儲存成本遠低於 Elasticsearch。

```yaml
# loki-config.yaml 基本設定
auth_enabled: false
server:
  http_listen_port: 3100
storage_config:
  filesystem:
    directory: /data/loki/chunks
schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
```

搭配 Promtail（log 收集 agent）在每台機器上收集 log 並推送到 Loki：

```yaml
# promtail-config.yaml
clients:
  - url: http://loki.internal:3100/loki/api/v1/push
scrape_configs:
  - job_name: system
    static_configs:
      - targets: [localhost]
        labels:
          job: syslog
          __path__: /var/log/*.log
```

### ELK Stack（功能豐富）

Elasticsearch + Logstash + Kibana 是功能最完整的 log 平台，但資源消耗大（Elasticsearch 建議至少 4GB RAM 起跳）。適合需要全文搜索 log 內容的場景。

離線安裝：Elastic 提供離線安裝包（`.deb` / `.rpm`），或用 Docker 映像。三個組件都要搬運。

選型判準：5 台以下的小環境用 Loki（輕量、跟 Prometheus + Grafana 同一套 dashboard）。需要全文搜索、已有 ELK 經驗的團隊用 ELK。

## 告警：沒有外部 webhook 怎麼通知

連網環境的告警通常發到 Slack webhook、PagerDuty API、或 email relay service。斷網環境這些路徑都不通。

### 內部 SMTP

如果隔離網路內有 email server（很多企業內網有 Exchange 或 Postfix），Prometheus Alertmanager 可以發 email 告警：

```yaml
# alertmanager.yml
route:
  receiver: 'email-team'
receivers:
  - name: 'email-team'
    email_configs:
      - to: 'oncall@internal.corp'
        from: 'alertmanager@internal.corp'
        smarthost: 'smtp.internal.corp:25'
        require_tls: false
```

### 內部即時通訊

如果內網有 Mattermost（Slack 的 self-hosted 替代）或 Rocket.Chat，Alertmanager 可以用 webhook 發送到這些工具的 incoming webhook endpoint。

### 實體告警

極端情境（沒有 email、沒有 chat）：Alertmanager 把告警寫到檔案或資料庫、搭配值班制度定期查看。或用 Grafana 的 dashboard + 控制室大螢幕，值班人員直接看板。

告警的設計原則跟連網環境相同——symptom-based（錯誤率、延遲）優先於 cause-based（CPU、記憶體），閾值設計避免告警疲勞。差別在通知的到達速度可能慢一些（email 比 Slack push 慢），所以閾值要稍微保守（提早告警）。

## Metric 與 Log 的儲存規劃

SaaS 監控的儲存是雲端自動擴展的。Self-hosted 的儲存要自己規劃——磁碟滿了 Prometheus 就停止收集、Loki 就停止寫入。

### 容量估算

Prometheus 的儲存量取決於 series 數量 × scrape 間隔 × 保留天數。粗估公式：

```text
每日儲存 ≈ active_series × sample_size(2B) × (86400 / scrape_interval) × compression_ratio(~0.1)
```

1 萬個 active series、15 秒 scrape interval、保留 30 天 ≈ 約 5GB。保留 90 天 ≈ 約 15GB。

Loki 的儲存量取決於 log 流量。粗估：每天 10GB 的 raw log 在 Loki 壓縮後約 1-2GB，保留 30 天 ≈ 30-60GB。

### Retention 設定

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
storage:
  tsdb:
    retention.time: 30d
    retention.size: 10GB  # 以先到的為準
```

超過容量時 Prometheus 自動刪除最舊的資料。設定 retention 前先確認磁碟空間足夠——斷網環境擴容磁碟的流程（採購 + 安裝）可能需要週到月級的時間。

## NTP 時間同步

斷網環境容易被忽略的一個問題是時間同步。沒有 NTP server（`pool.ntp.org`）可連的機器，時鐘會漂移——幾天後各台機器的時間差可能達到秒級。當 Prometheus 收到的 metric timestamp 跟 Loki 收到的 log timestamp 有幾秒落差，事故排查時 metric 跟 log 對不上。

解法是在隔離網路內架一台 NTP server，所有機器從它同步：

```bash
# 內部 NTP server（chrony）
# /etc/chrony/chrony.conf
local stratum 10         # 沒有外部來源時、自己當 stratum 10
allow 10.0.0.0/16        # 允許內部網段同步

# 其他機器指向內部 NTP
server ntp.internal iburst
```

如果隔離網路的閘道可以開 NTP（UDP 123），讓閘道從外部 NTP 同步、內部機器從閘道同步，時間精度可以維持在毫秒級。

時程參考：Prometheus + Grafana + Alertmanager 的初次建置約需 1-2 天。Loki + Promtail 約需半天到一天。NTP server 約需 2 小時。後續維護主要是 Prometheus/Loki 版本更新的搬運（每次 1-2 小時）和儲存容量監控。

## 跨分類引用

- → [斷網環境的通用原則](/infra/air-gapped/air-gapped-principles/)：監控工具的離線安裝走 content ferry 模式
- → [斷網環境的容器管理](/infra/air-gapped/air-gapped-container/)：Prometheus/Grafana/Loki 的容器映像搬運
- → [模組六：可觀測性與 log](/infra/06-observability-logging/)：連網環境的可觀測性 IaC
- → [無 SSH 環境的監控與告警](/infra/takeover/legacy-external-monitoring/)：另一個極端——完全外部監控
