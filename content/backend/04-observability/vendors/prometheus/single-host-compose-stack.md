---
title: "單機 Compose 的最小監控堆疊：各 exporter 的掛載、讀取設定與 Grafana 佈建"
date: 2026-10-13
description: "以 Docker Compose 在一台主機上接起 Prometheus、Alertmanager、Grafana 與主機、容器、資料庫、快取、入口各層的 exporter：每個掛載與旗標為什麼需要、讀取設定與規則的放法、Grafana 以檔案佈建、連接埠與帳號的權限，以及讀取對象全部 UP 時仍可能漏掉的監控"
weight: 13
tags: ["backend", "observability", "prometheus", "docker", "monitoring"]
---

> 本文是 [Prometheus](/backend/04-observability/vendors/prometheus/) 的 vendor deep article。各層要收哪些訊號、監控所在層看不到什麼、接上之後怎麼驗收，見 [4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/)；告警怎麼寫見 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)。

這篇整理以 Docker Compose 在一台主機上接起一套最小監控堆疊時，每一個元件的設定與它為什麼要這樣設。範圍從「服務已經用 Compose 跑起來」開始，涵蓋 Prometheus、Alertmanager、Grafana，以及主機、容器、PostgreSQL、Redis／Valkey、入口 Nginx 各一個 exporter。文中的設定取自一個短網址服務在單機時的版本（它之後為了拆到多台主機，把讀取清單改成檔案清單，見 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/)）：Prometheus 3.15.0、Alertmanager 0.34.1、Grafana 13.2.3、cAdvisor v0.55.1、node_exporter 1.12.1、postgres_exporter 0.20.1、redis_exporter 1.93.0、nginx-prometheus-exporter 1.5.0。版本號寫死在映像標籤上，升級時一次只改一個元件的映像標籤，改完重跑 [單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/) 裡的驗收；寫 `latest` 的話，換一台主機或跑一次 `docker compose pull` 拿到的就可能是另一個版本，而沒有任何紀錄。

## 堆疊的組成：誰讀誰

在指標收集這一段，Prometheus 是主動發起連線的一方：它每隔一段時間（讀取間隔，scrape interval）向每個 [exporter](/backend/knowledge-cards/prometheus-exporter/) 的 HTTP 端點讀取（scrape）一次指標、存進自己的時間序列資料庫、依規則算出告警交給 Alertmanager；Grafana 向 Prometheus 查詢畫成儀表板。每個 exporter 各自負責把一個系統的狀態轉成指標：

| 元件                      | 讀什麼                                                                                         | 為了讀到它要給的權限                                     |
| ------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| node_exporter             | 主機的 `/proc`、`/sys` 與掛載點                                                                | 主機的行程命名空間與唯讀的根目錄                         |
| cAdvisor                  | 每個容器的 [cgroup](/backend/knowledge-cards/cgroup/) 統計，以及容器執行環境給的容器名稱與標籤 | privileged、主機的 `/sys`、`/var/run`、Docker 的資料目錄 |
| postgres_exporter         | PostgreSQL 的統計視圖                                                                          | 一個只有 `pg_monitor` 角色的資料庫帳號                   |
| redis_exporter            | Redis／Valkey 的 `INFO`                                                                        | 連得到快取的位址                                         |
| nginx-prometheus-exporter | Nginx 的 `stub_status` 狀態頁                                                                  | Nginx 開一個只在內部網路聽的狀態頁                       |

exporter 與被監控的服務放在同一個 compose 網路裡，Prometheus 以服務名稱連它們，所以 exporter 的連接埠都不必對外發佈。

## 主機層：node_exporter

node_exporter 跑在容器裡，預設看到的是容器自己的 `/proc` 與檔案系統。要它回報主機，給它主機的行程命名空間，並把主機的根目錄唯讀掛進來、告訴它從那裡讀：

```yaml
node-exporter:
  image: quay.io/prometheus/node-exporter:v1.12.1
  restart: unless-stopped
  pid: host                     # 看到主機的行程，load 與行程數才是主機的
  command:
    - --path.rootfs=/host       # 從掛進來的主機根目錄讀檔案系統
    - --no-collector.netdev     # 這三個讀的是自己容器的網路命名空間，不是主機的
    - --no-collector.netstat
    - --no-collector.sockstat
  volumes:
    - /:/host:ro,rslave         # rslave 讓主機之後才掛上的磁碟也看得到
```

網路相關的三個 collector 關掉，是因為 node_exporter 留在 compose 的網路裡，它讀到的 `/proc/net` 是自己這個容器的網路命名空間；主機的網路流量改看 cAdvisor 的各容器網路指標，它只涵蓋容器的流量，主機上其他行程（sshd、系統更新）的流量不在裡面。要看主機本身的網路介面，另一個做法是讓它以 `network_mode: host` 執行，代價是它的連接埠直接開在主機上，要另外限制誰連得到。

Docker 跑在虛擬機裡的環境（macOS、Windows），這裡的「主機」是那台虛擬機；它看不到虛擬機外面的 CPU 負載，磁碟則可能同時看到虛擬機的與主機掛進來的那一顆，見 [單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/) 的〈監控所在層看不到的範圍：虛擬機與主機〉。

## 容器層：cAdvisor

cAdvisor 從 cgroup 讀每個容器的 CPU、記憶體、網路與磁碟讀寫，再問容器執行環境（containerd）這個 cgroup 是哪個容器、帶哪些標籤；compose 的服務名稱就是從這裡來的標籤 `container_label_com_docker_compose_service`。

```yaml
cadvisor:
  image: gcr.io/cadvisor/cadvisor:v0.55.1
  restart: unless-stopped
  privileged: true              # 讀主機的 cgroup 與裝置資訊
  command:
    - --containerd=${CADVISOR_CONTAINERD_SOCKET:-/run/containerd/containerd.sock}
    - --docker_only=true        # 只回報容器，不回報主機上其他的 cgroup
    - --housekeeping_interval=15s # 更新統計的間隔，對齊讀取間隔（預設 1 秒）
  volumes:
    - /:/rootfs:ro              # 主機的檔案系統，算各容器的磁碟用量
    - /var/run:/var/run:ro      # containerd 的 socket 在這底下
    - /sys:/sys:ro              # cgroup 的統計
    - /var/lib/docker/:/var/lib/docker:ro   # 容器的可寫層，算各容器的磁碟用量
    - /dev/disk/:/dev/disk:ro   # 把裝置編號對應到磁碟名稱
```

`--containerd` 的值放在環境變數，因為 socket 的位置依環境不同：Linux 主機直接跑 Docker 時預設的 `/run/containerd/containerd.sock` 多半就對；macOS 上的 Docker 跑在虛擬機裡，socket 在虛擬機的另一個位置（OrbStack 2.2.3 上量到的是 `/var/run/docker/containerd/containerd.sock`），位置隨工具與版本不同，要在自己的環境裡找一次。找不到 socket 時 cAdvisor 照樣起來、Prometheus 照樣讀得到，指標卻只剩 `id="/docker/<雜湊>"` 而沒有容器名稱與 compose 標籤；找法與日誌長什麼樣，見 [單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/) 的〈Docker 跑在虛擬機裡時 cAdvisor 缺容器名稱〉。`--housekeeping_interval` 是 cAdvisor 更新每個容器統計的間隔，預設 1 秒，而且閒置的容器會逐步拉長到最多 1 分鐘（`--allow_dynamic_housekeeping` 預設開啟）；Prometheus 每 15 秒才來讀一次，更新得比讀取頻繁的部分沒有人讀，所以對齊讀取間隔，省下 cAdvisor 的 CPU。要每次讀取都拿到新的值，另外設 `--allow_dynamic_housekeeping=false`。

## 服務內部：資料庫、快取與入口

postgres_exporter 連進 PostgreSQL 查統計視圖，用一個專用帳號，只給 PostgreSQL 內建的 `pg_monitor` 角色（讀統計視圖與設定），不沿用應用程式的帳號：

```yaml
postgres-exporter:
  image: prometheuscommunity/postgres-exporter:v0.20.1
  restart: unless-stopped
  environment:
    DATA_SOURCE_URI: postgres:5432/${POSTGRES_DB}?sslmode=disable
    DATA_SOURCE_USER: postgres_exporter
    DATA_SOURCE_PASS: ${POSTGRES_EXPORTER_PASSWORD}
  depends_on:
    postgres:
      condition: service_healthy
```

帳號由資料庫的初始化腳本建立，腳本放在官方映像的 `/docker-entrypoint-initdb.d/`，檔名用 `.sh`（例如 `10-monitoring-role.sh`）：寫成 `.sql` 時 shell 不會展開 `$POSTGRES_EXPORTER_PASSWORD`，密碼會是空的。

```sh
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v pw="$POSTGRES_EXPORTER_PASSWORD" <<'SQL'
CREATE ROLE postgres_exporter LOGIN PASSWORD :'pw';
GRANT pg_monitor TO postgres_exporter;
SQL
```

初始化腳本只在資料目錄是空的時候執行，資料庫已經存在時要另外跑一次同樣的 SQL，例如把腳本餵給執行中的資料庫容器（`postgres` 是 compose 裡資料庫的服務名稱）：

```sh
docker compose exec -T postgres sh -c 'cat > /tmp/r.sh' < infra/postgres/initdb/10-monitoring-role.sh
docker compose exec -T postgres sh /tmp/r.sh
```

這個做法要求資料庫容器裡已經有 `POSTGRES_EXPORTER_PASSWORD` 這個環境變數。給資料庫的服務加上它時，Compose 會重新建立資料庫的容器；依賴它的服務不會跟著重啟（`depends_on` 寫了 `restart: true` 的才會），它們的資料庫連線會斷一次，要靠應用程式自己重連，所以正式環境排在維護時間做，並確認應用程式重連得回來。

redis_exporter 只需要快取的位址（它也支援 Valkey）：

```yaml
valkey-exporter:
  image: oliver006/redis_exporter:v1.93.0
  restart: unless-stopped
  environment:
    REDIS_ADDR: redis://cache:6379   # compose 的服務名稱與連接埠
```

入口 Nginx 的連線數由它自己的 `stub_status` 提供，nginx-prometheus-exporter 讀這個狀態頁轉成指標。狀態頁另開一個只在內部聽的連接埠，只接受私有位址，compose 不把這個連接埠對外發佈：

```nginx
server {
    listen 8081;
    access_log off;
    location = /stub_status {
        stub_status;
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        allow 127.0.0.1;
        deny all;
    }
}
```

```yaml
nginx-exporter:
  image: nginx/nginx-prometheus-exporter:1.5.0
  restart: unless-stopped
  command:
    - --nginx.scrape-uri=http://nginx:8081/stub_status
```

`stub_status` 只有連線數與累計請求數；依狀態碼、網域、上游分開的請求數與回應時間，要從 access log 轉成指標，交給把 log 轉成計數的工具（例如 mtail）或 log 系統（例如 Loki 的 log 查詢），不在這套 exporter 的範圍內。

## Prometheus：讀取設定、規則與重新載入

```yaml
prometheus:
  image: prom/prometheus:v3.15.0
  restart: unless-stopped
  command:
    - --config.file=/etc/prometheus/prometheus.yml
    - --storage.tsdb.path=/prometheus
    - --storage.tsdb.retention.time=15d   # 資料保留多久，依磁碟大小定
    - --web.enable-lifecycle              # 允許 POST /-/reload 重新載入設定
  ports:
    - "127.0.0.1:9090:9090"               # 只綁本機
  volumes:
    # repo 裡放 Prometheus 設定的目錄（裡面有 prometheus.yml 與 rules/），依自己的結構換
    - ./infra/observability/prometheus:/etc/prometheus:ro
    - promdata:/prometheus                # 具名 volume，要在檔案最後的 volumes: 底下宣告

volumes:
  promdata:
```

設定掛的是整個目錄而不是 `prometheus.yml` 單一檔案。單一檔案的 bind mount 綁在掛載當下那個檔案（inode）上，編輯器或部署工具以「寫一個新檔再改名蓋過去」的方式存檔時，主機上的路徑換成了新檔，容器裡看到的仍是舊的那一個或讀不到，重新載入也拿不到新內容；掛目錄時容器每次都從目錄裡重新找這個檔名。

讀取設定（`scrape_configs`）列出每個讀取對象（target），每個對象帶一個 `host` 標籤，值是它回報的那台主機；一台主機時全部相同，看起來多餘，而之後分到多台主機時，告警與面板靠它分出主機。`rule_files` 指向告警規則，`alerting` 指向 Alertmanager：

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
rule_files:
  - /etc/prometheus/rules/*.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]
scrape_configs:
  - job_name: prometheus
    static_configs: [{ targets: ["localhost:9090"], labels: { host: app-1 } }]
  - job_name: alertmanager
    static_configs: [{ targets: ["alertmanager:9093"], labels: { host: app-1 } }]
  - job_name: cadvisor
    static_configs: [{ targets: ["cadvisor:8080"], labels: { host: app-1 } }]
  - job_name: node
    static_configs: [{ targets: ["node-exporter:9100"], labels: { host: app-1 } }]
  - job_name: postgres
    static_configs: [{ targets: ["postgres-exporter:9187"], labels: { host: app-1 } }]
  - job_name: valkey
    static_configs: [{ targets: ["valkey-exporter:9121"], labels: { host: app-1 } }]
  - job_name: nginx
    static_configs: [{ targets: ["nginx-exporter:9113"], labels: { host: app-1 } }]
```

`targets` 寫的是 compose 的服務名稱加上各 exporter 的預設連接埠，換成自己的服務名稱；`app-1` 換成這台主機的名稱。讀取間隔 15 秒取自 Prometheus 官方範例設定的值（程式本身的預設是 1 分鐘），它決定了查詢時間窗的下限：`rate()` 的時間窗取讀取間隔的四倍以上，理由見 [單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/) 的〈單次取樣與時間窗〉。

設定檔的內容改了而掛載路徑沒變時，`docker compose up -d` 判定容器設定沒有變化、不會重建容器，所以改完要讓 Prometheus 與 Alertmanager 各自重新載入設定。`promtool` 與 `amtool` 隨映像附帶，在容器裡跑，路徑是容器內的掛載位置：

```sh
# 檢查語法
docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
docker compose exec prometheus sh -c 'promtool check rules /etc/prometheus/rules/*.yml'
docker compose exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml

# 重新載入設定（Prometheus 要有 --web.enable-lifecycle；Alertmanager 不需要旗標）
curl -X POST http://127.0.0.1:9090/-/reload
curl -X POST http://127.0.0.1:9093/-/reload
```

重新載入之後，從 Prometheus 的 Status → Configuration 與 Alertmanager 的 `GET /api/v2/status` 確認載入的是新的內容。

## Alertmanager：告警的分組與抑制

Alertmanager 接收 Prometheus 算出的告警，決定怎麼分組、哪些被抑制、送到哪裡。這套設定還沒有通知管道，告警在它的網頁上看：

```yaml
alertmanager:
  image: prom/alertmanager:v0.34.1
  restart: unless-stopped
  command:
    - --config.file=/etc/alertmanager/alertmanager.yml
    - --storage.path=/alertmanager
  ports:
    - "127.0.0.1:9093:9093"               # 只綁本機
  volumes:
    - ./infra/observability/alertmanager:/etc/alertmanager:ro   # 掛目錄，理由同 Prometheus
```

`alertmanager.yml` 裡的分組、依原因抑制症狀的規則怎麼寫，見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)。

## Grafana：以檔案佈建資料來源與儀表板

Grafana 的資料來源與儀表板以 provisioning 檔佈建，放進 repo，換一台機器重建時不必在介面上重新點一次：

```yaml
# provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

```yaml
# provisioning/dashboards/files.yml
apiVersion: 1
providers:
  - name: default
    type: file
    allowUiUpdates: false        # 介面上的修改不寫回檔案，以檔案為準
    options:
      path: /var/lib/grafana/dashboards
```

Grafana 的服務把兩個目錄掛進來，資料目錄另外用具名 volume：

```yaml
grafana:
  image: grafana/grafana:13.2.3
  restart: unless-stopped
  environment:
    GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}   # 只在資料庫第一次建立時設定 admin 的密碼
    GF_USERS_ALLOW_SIGN_UP: "false"                         # 關掉自行註冊
  ports:
    - "127.0.0.1:3000:3000"                                 # 只綁本機
  volumes:
    - ./infra/observability/grafana/provisioning:/etc/grafana/provisioning:ro
    - ./infra/observability/grafana/dashboards:/var/lib/grafana/dashboards:ro   # 上面 provider 的 path
    - grafanadata:/var/lib/grafana                          # 使用者、密碼與介面上的設定
  depends_on:
    - prometheus
```

`/var/lib/grafana` 存放 Grafana 自己的資料庫（單機預設是 SQLite），使用者、改過的密碼與在介面上建的東西都在裡面；不掛 volume 的話，重建容器時這些全部消失，從檔案載入的資料來源與儀表板則照樣出現。也因為資料庫留了下來，`GF_SECURITY_ADMIN_PASSWORD` 只在資料庫第一次建立時生效，之後改這個變數不會改變登入密碼，要改密碼用介面或 `grafana cli admin reset-admin-password`。`allowUiUpdates: false` 的取捨是：在介面上調好的儀表板要匯出 JSON 放回 repo 才會留下，好處是 repo 永遠是儀表板的唯一來源。視覺化層為什麼選 Grafana、它與 Prometheus 內建介面、Perses 等工具各自成立的前提，以及告警規則為什麼留在 Prometheus 而不放進 Grafana，見 [Prometheus 指標的視覺化工具](/backend/04-observability/vendors/prometheus/visualization-tool-selection/)。

## 連接埠與資源用量

Prometheus、Alertmanager 與 Grafana 的程式預設聽全部的網路介面，compose 的 `ports` 寫成 `"127.0.0.1:9090:9090"` 這種形式，才只綁在主機的本機位址上。要給其他人看時，對外開的是有帳號與角色的 Grafana，經過入口的反向代理與認證；Prometheus 與 Alertmanager 沒有權限分級，繼續只綁本機。exporter 與被監控的服務在同一個 compose 網路裡，Prometheus 以服務名稱連它們，所以 exporter 都不發佈連接埠。

這一整組（各層的 exporter 加上 Prometheus、Grafana 與 Alertmanager）的記憶體用 `sum by (container_label_com_docker_compose_service) (container_memory_working_set_bytes)` 量。在那個短網址服務上（macOS 的 OrbStack、單機、約九千條活躍的時間序列）一天內每小時取樣，總和約 600 MB 上下，其中 Grafana 約 240 到 400 MB、Prometheus 約 140 到 235 MB 最多。Prometheus 的記憶體主要隨活躍的時間序列數成長，保留天數影響的是磁碟；Grafana 隨開著的面板與同時進行的查詢起伏。這些數字只代表那一台，小機型上監控本身和服務搶同一份記憶體，接上之後用同一個查詢量自己的數字。放不下時把 Prometheus 這類元件移到另一台機器，怎麼拆見 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/) 的〈監控主機放在哪裡〉，共用主機的取捨見 [共用主機的資源競爭](/operations/05-capacity-planning/shared-host-contention/)。

## 讀取對象全部 UP 時仍可能漏掉的監控

Prometheus 的 Targets 頁面上的 `UP` 只代表 Prometheus 讀得到 exporter 的端點；每一層有沒有在監控，要看 exporter 自己回報的狀態：exporter 連不上它監控的服務時 `up` 照樣是 1，要看 `pg_up`、`redis_up`、`nginx_up`；cAdvisor 找不到 socket 時 Prometheus 讀得到它的端點，而指標缺容器名稱與 compose 標籤；node_exporter 有部分 collector 失敗時 `up` 也是 1，要看 `node_scrape_collector_success`。每一種的查法與用故障注入確認數字會反應的做法，見 [單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/) 的〈監控來源接上之後仍沒在監控的情形與驗收〉；以這套指標寫告警、以及主機過載時各服務的告警怎麼收斂，見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)。服務分到多台主機時，exporter 的連接埠、主機標籤、目標清單與主機消失的偵測要怎麼改，見 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/)。

## 延伸閱讀：容量、查詢與長期保存

- 這台 Prometheus 的時間序列數量、記憶體與磁碟怎麼估，讀取逾時與其他故障模式，見 [Prometheus 容量規劃與故障模式](/backend/04-observability/vendors/prometheus/capacity-failure-modes/)。
- 儀表板與告警常用的查詢寫法、recording rule 的設計，見 [PromQL 與 Recording Rules 實務](/backend/04-observability/vendors/prometheus/promql-recording-rules/)。
- 15 天的保留不夠、或要從多台主機統一查詢時，見 [Remote Write 與長期儲存整合](/backend/04-observability/vendors/prometheus/remote-write-long-term-storage/)。
