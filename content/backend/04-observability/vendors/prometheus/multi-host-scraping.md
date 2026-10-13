---
title: "多台主機的指標收集：讀取架構、主機標籤、目標清單與主機消失的偵測"
date: 2026-10-13
description: "服務分到多台主機之後，Prometheus 怎麼讀到每一台：exporter 跟著主機與服務走、中央直接讀取與各主機先收再推送的兩種架構、代表主機的 host 標籤加在哪裡、目標清單由什麼產生，以及主機停掉與主機從清單上消失各自怎麼偵測；附在單機設定上模擬第二台主機的驗證"
weight: 15
tags: ["backend", "observability", "vendor", "prometheus"]
---

> 本文是 [Prometheus](/backend/04-observability/vendors/prometheus/) 的 vendor deep article，接在 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 之後：那一篇的 exporter、讀取設定與規則都在一台主機上，本篇處理服務分到多台主機時要改的部分。

這篇整理服務分到多台主機之後，一套 Prometheus 怎麼讀到每一台主機的指標，以及告警、面板要怎麼跟著改。範圍從單機的監控堆疊已經能用開始；文中的設定取自一個短網址服務從單機改成可拆到多台主機的版本（Prometheus 3.15.0、Alertmanager 0.34.1、Grafana 13.2.3），多台主機的部分在同一台機器上模擬第二台主機驗證過機制，沒有在實際的多台主機上跑過。

## exporter 跟著主機與服務走

[exporter](/backend/knowledge-cards/prometheus-exporter/) 只看得到它所在的那一層：node_exporter 讀的是它所在主機的 `/proc` 與 `/sys`，cAdvisor 讀的是它所在主機上的 [cgroup](/backend/knowledge-cards/cgroup/)。所以每一台主機都要各跑一個 node_exporter 與 cAdvisor。服務的 exporter（postgres_exporter、redis_exporter、nginx-prometheus-exporter）跟著它監控的服務走：資料庫放在 db-1，postgres_exporter 就放在 db-1，連線走同一台主機的內部網路，資料庫的連接埠不必為了監控對外開放。

單機時 exporter 不必開連接埠，Prometheus 在同一個 compose 網路裡以服務名稱連到它們。分到多台主機之後，Prometheus 在另一台機器上，exporter 的連接埠要開在主機的網路介面上，而 exporter 沒有認證：連得到 9100 的人就讀得到這台主機的全部指標，包括掛載點、行程數與核心版本。所以連接埠只綁在主機的私有網路位址，再用防火牆或雲端的 security group 限制只有監控主機能連。那個短網址服務用一個疊加的 compose 檔做這件事：

```yaml
# compose.exporters-published.yml：被監控的主機加上這個檔
services:
  node-exporter:
    ports:
      # EXPORTER_BIND_ADDR 是這台主機的私有網路位址；沒設時 compose 直接報錯，不會退回綁定全部介面
      - "${EXPORTER_BIND_ADDR:?設成這台主機的私有網路位址}:9100:9100"
  cadvisor:
    ports:
      - "${EXPORTER_BIND_ADDR:?設成這台主機的私有網路位址}:8080:8080"
```

`${變數:?訊息}` 是 compose 的必填語法：變數沒設時 `docker compose config` 與 `up` 都會以那段訊息失敗。寫成 `${EXPORTER_BIND_ADDR}` 的話，沒設時展開成空字串，連接埠就綁在全部的網路介面上，exporter 直接暴露在公開位址。跨不可信的網段時，exporter 共用的函式庫（exporter-toolkit）支援 `--web.config.file`，可以加上 TLS 與 basic auth，Prometheus 的讀取設定加對應的 `tls_config` 與 `basic_auth`。

## 指標回到中央的兩種架構

每台主機的 exporter 都在跑之後，指標要回到一個能一起查詢、一起算告警的地方。常見的做法有兩種，差別在連線由哪一側發起。

**中央直接讀取**：一台監控主機上的 Prometheus 依目標清單，定時連到每台主機的 exporter 讀取。這是 Prometheus 預設的工作方式，告警規則在這台 Prometheus 上算，所以這台看得到全部主機的序列，跨主機的規則（例如「同一個服務在所有主機上都停了」）直接寫得出來。它成立的前提是監控主機連得到每一台主機：主機都在同一個私有網路（同一個 VPC，或互相路由得到的網段）時最單純。

**各主機先收、再推送到中央**：每台主機跑一個只負責讀取與轉送的程式——Prometheus 以 `--agent` 啟動的 agent 模式、Grafana Alloy 或 OpenTelemetry Collector——讀本機的 exporter，再以 remote write 推送到中央的儲存（Mimir、Thanos 或託管服務，見 [Remote Write 與長期儲存整合](/backend/04-observability/vendors/prometheus/remote-write-long-term-storage/)）。連線由主機往外發起，所以主機在 NAT 後面、跨區域或跨雲、中央連不進去時仍然可行。代價有兩項：agent 模式不能查詢、不算告警也不算 recording rule，這些都移到中央的儲存；中央連不上時 agent 把資料暫存在本機磁碟，官方文件寫明暫存目前上限是兩小時，斷線超過兩小時的那段資料會留下缺口。

選擇看的是網路的可達方向與規模。主機在幾台到幾十台、監控主機連得到每一台時，中央直接讀取的元件最少，本篇以下以它為準；中央連不進去，或一台 Prometheus 已經讀不完全部目標（容量的估法見 [Prometheus 容量規劃與故障模式](/backend/04-observability/vendors/prometheus/capacity-failure-modes/)）時，改用推送。

## 代表主機的 host 標籤

每個序列都要帶一個說明「這是哪台主機」的標籤，告警、抑制與面板才分得出主機。Prometheus 自動加上的 `instance` 不能代替它：`instance` 是讀取對象的位址，同一台主機上 node_exporter 是 `10.0.1.11:9100`、cAdvisor 是 `10.0.1.11:8080`，兩者不相等，以 `instance` 對應原因與症狀時，只有恰好讀自同一個 exporter 的序列對得上（抑制規則上的實際後果見 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/) 的主機標籤一段）。所以另外加一個 `host` 標籤，值是這個序列代表的那台主機。

`host` 加進去之後，凡是把序列聚合起來的地方都要保留它，否則聚合會把不同主機合在一起，一台主機的狀況被另一台蓋掉。容器停止的規則是最直接的例子：

```promql
# 一台主機上，某個服務的所有容器都超過 60 秒沒被 cAdvisor 看到
min by (host, container_label_com_docker_compose_service) (
  time() - container_last_seen{container_label_com_docker_compose_service!=""}
) > 60
```

同一個服務跑在 app-1 與 app-2 兩台主機上、app-2 的容器停了時，分組少了 `host` 的版本取的是兩台的最小值，而 app-1 的容器還在、值很小，整條規則不成立。磁碟的規則同理，依 `host, device, fstype` 分組，不同主機上同名的 `/dev/nvme0n1p1` 才不會合成一個。告警送到 Alertmanager 之後，分組寫 `group_by: [alertname, host]`，同一台主機的同一種告警合成一則；抑制規則寫 `equal: [host]`，一台主機 CPU 飽和只壓下同一台主機上的症狀，其他主機的症狀照常通知。面板頂端放一個以 `label_values(up, host)` 產生的下拉選單，每個查詢加上 `host=~"$host"`，圖例前面加主機名稱，就能切換單一主機或並排比較所有主機。

`host` 加在哪裡，取決於目標清單怎麼產生：檔案清單直接寫在每個目標上，雲端的服務發現用 relabel 從執行個體的 tag 取。

## 目標清單由預期的主機產生

Prometheus 讀哪些目標，可以寫死在 `static_configs`，也可以交給服務發現（service discovery）從外部來源產生。寫死的清單在主機增減時要有人記得改，新開的主機漏加時沒有任何錯誤訊息，它只是不在監控裡。

**檔案清單（`file_sd_configs`）**：讀取設定指向一份 YAML 或 JSON 檔，檔案裡列出目標與它們的標籤，`host` 直接寫在每個目標上：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: node
    file_sd_configs:
      - files: [/etc/prometheus/targets/node.yml]
        refresh_interval: 30s
```

```yaml
# targets/node.yml，由部署工具從主機清單產生；位址是私有網段的佔位值
- targets: ["10.0.1.11:9100"]
  labels: {host: app-1}
- targets: ["10.0.1.12:9100"]
  labels: {host: app-2}
- targets: ["10.0.1.21:9100"]
  labels: {host: db-1}
```

Prometheus 會監看這個檔案，內容改了就重新讀取，不必重新載入設定；`refresh_interval` 是監看失效時的定時重讀。在那個短網址服務上實測，清單加上一台主機之後 13 秒，它就出現在 Prometheus 的 Targets 頁面。這份檔案由 Ansible、Terraform 這類部署工具從主機清單產生，主機清單是部署的依據，監控因此跟著部署走，不靠人記得同步。

**雲端的服務發現**：在 AWS 上用 `ec2_sd_configs`，Prometheus 直接向 EC2 的 API 查詢執行中的執行個體，依 tag 篩選要監控的那些。執行個體的 tag 以 `__meta_ec2_tag_<tag 名稱>` 的形式出現，用 relabel 搬到 `host`：

```yaml
- job_name: node
  ec2_sd_configs:
    - region: ap-northeast-1
      port: 9100              # 預設是 80，要指定 exporter 的連接埠
      filters:
        - name: tag:monitoring
          values: [enabled]
  relabel_configs:
    # 目標位址用私有 IP（預設即是），host 取執行個體的 Name tag
    - source_labels: [__meta_ec2_tag_Name]
      target_label: host
```

這段設定以 `promtool check config` 檢查過語法，沒有在 AWS 上實際跑過；`region`、tag 的名稱與值換成自己環境的。GCP 的 `gce_sd_configs`、Kubernetes 的 `kubernetes_sd_configs` 是同一類，各自提供不同的 `__meta_*` 標籤。

兩種來源的差別在主機被移除時：檔案清單只在部署工具重新產生時改變，雲端的服務發現在執行個體終止的那一刻就把它從目標裡拿掉。所以主機被移除之後，檔案清單上的主機仍在、`up` 變成 0；雲端服務發現的主機連序列都不見，兩者要用不同的規則偵測。

## 主機停掉與主機從清單上消失

**主機停掉、仍在清單上**：Prometheus 讀不到它，`up{host="app-2"}` 變成 0，讀取失敗的告警對那台主機成立。那個短網址服務的規則取 15 分鐘內讀取成功的比例（主機過載時讀取是間歇失敗，`up == 0` 加持續時間會被打斷，理由見 4.27）：

```promql
avg_over_time(up[15m]) < 0.9
```

`up` 帶著目標清單上的 `host`，所以告警自己就指出是哪台主機，摘要可以寫成「Prometheus 連不到 {{ $labels.host }} 的 {{ $labels.job }}」。

**主機從清單上消失**：用雲端的服務發現時，執行個體被終止（或被自動擴縮收掉）之後不再是讀取目標，Prometheus 替它的序列寫入過期標記（staleness marker），`up{host="app-2"}` 在即時查詢裡直接消失，不會變成 0。讀取失敗的規則只對存在的序列判斷，所以這種情形要另外比對預期的數量，而預期的數量取自部署設定，不取自查詢結果：

```promql
# 預期 3 台；數字從部署設定（例如 Auto Scaling 群組的最小容量）來，部署改了這裡跟著改
count(up{job="node"}) < 3

# 某一台不可少的主機，序列不存在時成立
absent(up{job="node", host="db-1"})
```

全部主機同時消失時 `count` 沒有結果可以比較，第一條不成立，由下面清單空了的那一條接手。

**清單整個空了**：部署工具產生了空的檔案，或服務發現的篩選條件寫錯，`node` 這個 job 沒有任何目標。這時沒有任何 `up` 序列可以判斷，讀取失敗的規則全部沉默，看起來就像所有主機都正常：

```promql
absent(up{job="node"})
```

用檔案清單時，主機停掉由讀取失敗的規則處理，清單本身就是預期的主機；用雲端的服務發現時，主機停掉、主機從清單上消失、清單整個空了，三種情形各要有一條規則。

## 監控主機放在哪裡

中央的 Prometheus、Alertmanager 與 Grafana 放在一台獨立的監控主機上，不和被監控的服務共用。共用時，那台主機過載或停掉，監控跟著一起退化或停掉，而那正是最需要它的時候（見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)）。監控主機自己停掉時，它發不出任何告警，所以另外需要一個不經過它的訊號：在監控主機以外跑的外部探測，以及一條永遠成立的 Watchdog 告警，經由 Alertmanager 持續送到外部的心跳服務，心跳中斷時由外部服務通知（設定見 4.27）。

那個短網址服務把元件分成兩個 compose 檔，對應這兩種主機：每台主機都要跑的 exporter 留在 `docker-compose.yml`，Prometheus、Alertmanager、Grafana 移到 `compose.monitoring.yml`。單機時以 `.env` 的 `COMPOSE_FILE=docker-compose.yml:compose.monitoring.yml` 合成同一個專案；拆成多台時，被監控的主機讀 `docker-compose.yml:compose.exporters-published.yml`，監控主機只讀 `compose.monitoring.yml`。`COMPOSE_FILE` 寫在 `.env` 裡，同一個 repo 在每台主機上執行同一條 `docker compose up -d`，各自起各自那一組。

## 在單機上模擬第二台主機的驗證

多台主機的機制在只有一台機器時也驗得到，方法是在同一台機器上另外跑一個 node_exporter 當作第二台主機，把它的連接埠開在主機上，讓 Prometheus 經由主機的位址讀它，而不是經由 compose 網路的服務名稱：

```sh
# 模擬的 host-b：一個獨立的 node_exporter，連接埠開在本機
docker run -d --name hostb-node-exporter -p 127.0.0.1:19100:9100 quay.io/prometheus/node-exporter:v1.12.1
```

```yaml
# 在 targets/node.yml 加上這一筆；host.docker.internal 是容器連到主機的名稱，Docker Desktop 與 OrbStack 預設提供，
# Linux 上的 Docker 要在 Prometheus 的服務加 extra_hosts: ["host.docker.internal:host-gateway"]
- targets: ["host.docker.internal:19100"]
  labels: {host: host-b}
```

在那個短網址服務上，依序確認了四件事：

| 確認的事               | 做法                                                                         | 結果                                                 |
| ---------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------- |
| 清單改了不必重新載入   | 加上 host-b 那一筆                                                           | 13 秒後出現在 Targets 頁面，`host="host-b"`          |
| 主機停掉時只對它告警   | `docker stop hostb-node-exporter`                                            | 2 分 21 秒後讀取失敗的告警對 host-b 成立，app-1 沒有 |
| 抑制只作用在同一台主機 | 對 Alertmanager 送入合成的 host-b 主機飽和，與 host-b、host-c 各一則讀取變慢 | host-b 的讀取變慢被抑制，host-c 的仍是 active        |
| 聚合保留了 host        | promtool 的規則單元測試，再把 `ContainerStopped` 分組裡的 `host` 拿掉重跑    | 測試通過；拿掉 `host` 之後失敗                       |

模擬的 host-b 讀的是同一台虛擬機，數字和 app-1 一樣，所以這組驗證確認的是標籤、清單、規則與抑制的機制，不是兩台主機各自的數字。

「抑制只作用在同一台主機」那一項在第一次測試時沒有通過：host-c 的那一則也被抑制了。原因是 Alertmanager 還在用舊的設定——設定檔的內容改了，而它的掛載路徑沒變，`docker compose up -d` 判定容器設定沒有變化而沒有重建，Alertmanager 也就沒有重新讀取。打 `POST /-/reload` 之後結果正確。Prometheus 的規則與讀取設定同樣如此，改完設定之後兩者都要重新載入，再從 `GET /api/v2/status`（Alertmanager）或 Status → Configuration（Prometheus）確認載入的是新的內容。

規則的單元測試以 `promtool test rules` 執行，餵入合成的時間序列、指定在某個時間點預期成立的告警與它的標籤：

```yaml
# tests/alerts.test.yml 的一段：同一個服務在兩台主機上，只有 app-2 的停了
rule_files:
  - ../rules/alerts.yml
tests:
  - interval: 1m
    input_series:
      - series: 'container_last_seen{host="app-1", container_label_com_docker_compose_service="go"}'
        values: '0+60x10'          # 每分鐘前進 60 秒：容器一直在
      - series: 'container_last_seen{host="app-2", container_label_com_docker_compose_service="go"}'
        values: '0+60x2 120x8'     # 兩分鐘後停在 120：容器停了
    alert_rule_test:
      - eval_time: 6m
        alertname: ContainerStopped
        exp_alerts:
          - exp_labels: {severity: critical, scope: service, host: app-2, container_label_com_docker_compose_service: go}
            exp_annotations: {summary: "app-2 上的 go 已有 4m 0s 沒被 cAdvisor 看到"}
```

測試通過只說明規則照測試寫的方式運作，所以另外把規則改壞一次（拿掉分組裡的 `host`）確認測試會失敗；改壞了仍然通過的測試，檢查不到它宣稱檢查的那件事。

## 延伸閱讀：推送架構、容量與告警

- 改用各主機推送到中央時，中央儲存的選擇與 remote write 的故障模式，見 [Remote Write 與長期儲存整合](/backend/04-observability/vendors/prometheus/remote-write-long-term-storage/)。
- 主機變多之後一台 Prometheus 的時間序列數、記憶體與讀取逾時，見 [Prometheus 容量規劃與故障模式](/backend/04-observability/vendors/prometheus/capacity-failure-modes/)。
- `host` 標籤在探測類指標（Gatus、Blackbox exporter）、Pushgateway 與 Kubernetes 上各自怎麼加，以及主機飽和時的抑制規則，見 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)。
- 面板與告警分到多台主機之後由誰看、權限怎麼分，見 [Prometheus 指標的視覺化工具](/backend/04-observability/vendors/prometheus/visualization-tool-selection/)。
