---
title: "多台主機的指標收集：讀取架構、主機標籤、目標清單、監控主機的位置與主機消失的偵測"
date: 2026-10-13
description: "服務分到多台主機之後，Prometheus 怎麼讀到每一台：exporter 的部署位置與連接埠、中央直接讀取與各主機先收再推送的架構、代表主機的 host 標籤加在哪裡、目標清單由什麼產生，主機停掉與主機從清單上消失各自怎麼偵測，以及監控元件放在哪一台、compose 檔怎麼依主機角色拆開；附在單機上模擬第二台主機的驗證"
weight: 15
tags: ["backend", "observability", "vendor", "prometheus"]
---

> 這一篇屬於 [Prometheus](/backend/04-observability/vendors/prometheus/) 的實作系列，接在 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 之後：那一篇的 exporter、讀取設定與規則都在一台主機上。

單機的監控堆疊分到多台主機時，要改的是 exporter 的連接埠、代表主機的標籤、讀取對象的清單、主機消失的偵測，以及監控元件放在哪一台；告警與面板跟著依主機分開。文中的設定取自一個短網址服務把監控改成可拆到多台主機的版本（Prometheus 3.15.0、Alertmanager 0.34.1、Grafana 13.2.3），多台主機的部分在同一台機器上模擬第二台主機驗證過機制，沒有在實際的多台主機上跑過。

## exporter 的部署位置與連接埠

[exporter](/backend/knowledge-cards/prometheus-exporter/) 只看得到它所在的那一層：node_exporter 讀的是它所在主機的 `/proc` 與 `/sys`，cAdvisor 讀的是它所在主機上的 [cgroup](/backend/knowledge-cards/cgroup/)。所以每一台主機都要各跑一個 node_exporter 與 cAdvisor。服務的 exporter（postgres_exporter、redis_exporter、nginx-prometheus-exporter）跟著它監控的服務走：資料庫放在 db-1，postgres_exporter 就放在 db-1，連線走同一台主機的內部網路，資料庫的連接埠不必為了監控對外開放。

單機時 exporter 不必開連接埠，Prometheus 在同一個 compose 網路裡以服務名稱連到它們。分到多台主機之後，Prometheus 在另一台機器上，exporter 的連接埠要開在主機的網路介面上，而 exporter 預設沒有認證：連得到 9100 的人就讀得到這台主機的全部指標，包括掛載點、行程數與核心版本。所以連接埠只綁在主機的私有網路位址，再限制只有監控主機能連。限制放在雲端的 security group 最直接；放在主機的防火牆時要注意，Linux 上 Docker 發佈的連接埠由 Docker 自己寫進 iptables，不經過 ufw 這類工具管理的規則，在 ufw 加的限制對它沒有作用，要寫在 Docker 為此保留的 [`DOCKER-USER`](/infra/knowledge-cards/docker-user/) 鏈裡；`DOCKER-USER` 裡用 iptables 指令加的規則在重開機之後就不在；firewalld 主機用 iptables 後端、或用 nftables 後端而有 direct 設定時，`firewall-cmd --reload` 也會清掉它，ufw 主機上可以寫進 `/etc/ufw/after.rules` 讓它在開機時載入。消失的條件與各種寫法在重新載入、重開機之後的結果見 [CDN 後面的源站主機防火牆：只放行 CDN 來源的位置與套用時機、Docker 發佈連接埠的封包路徑、出站 DNS 的限制與地理封鎖](/infra/03-network-foundation/origin-host-firewall/) 的〈Docker 發佈的連接埠：封包路徑與限制的寫法〉。做法是在被監控的主機上多疊一個 compose 檔，每個 exporter 一行 `ports`：

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
  # postgres-exporter（9187）、valkey-exporter（9121）、nginx-exporter（9113）同樣各一行，
  # 只寫在實際跑那個服務的主機上
```

`${變數:?訊息}` 是 compose 的必填語法：變數沒設或是空字串時，`docker compose config` 與 `up` 都會以那段訊息失敗。寫成 `${EXPORTER_BIND_ADDR}` 的話，沒設時展開成空字串，連接埠就綁在全部的網路介面上，exporter 直接暴露在公開位址。

跨不可信的網段時，連接埠只綁私有位址還不夠，要加上 TLS 與認證，而各 exporter 的做法不一樣：node_exporter、postgres_exporter、nginx-prometheus-exporter 用同一個函式庫（exporter-toolkit），以 `--web.config.file` 指定一份設定 TLS 與 basic auth 的檔案；cAdvisor 與 redis_exporter 不支援這個旗標，各自有自己的 TLS 與認證旗標（各映像的 `--help` 列得出來）。不想逐一處理時，在 exporter 前面放一個做 TLS 與認證的反向代理。Prometheus 的讀取設定（`scrape_configs`）再加對應的 `tls_config` 與 `basic_auth`。

## 指標回到中央的架構：中央直接讀取與各主機推送

每台主機的 exporter 都在跑之後，指標要回到一個能一起查詢、一起算告警的地方。常見的做法有兩種，差別在連線由中央的 Prometheus 發起，還是由被監控的主機發起。

**中央直接讀取**：一台監控主機上的 Prometheus 依目標清單，定時連到每台主機的 exporter 讀取（scrape）。這是 Prometheus 預設的工作方式，告警規則在這台 Prometheus 上算，所以這台看得到全部主機的序列，跨主機的規則（例如「同一個服務在所有主機上都停了」）直接寫得出來。它成立的前提是監控主機連得到每一台主機：主機都在同一個私有網路（同一個 VPC，或互相路由得到的網段）時最單純。

**各主機先收、再推送到中央**：每台主機跑一個只負責讀取與轉送的程式——Prometheus 以 `--agent` 啟動的 agent 模式、Grafana Alloy 或 OpenTelemetry Collector——讀本機的 exporter，再以 remote write 推送到中央的儲存（Mimir、Thanos 或託管服務，見 [Remote Write 與長期儲存整合](/backend/04-observability/vendors/prometheus/remote-write-long-term-storage/)）。連線由主機往外發起，所以主機在 NAT 後面、跨區域或跨雲、中央連不進去時仍然可行。代價有兩項：agent 模式不能查詢、不算告警，也不算 recording rule（預先計算並存成新序列的查詢），這些都移到中央的儲存；中央連不上時 agent 把資料暫存在本機磁碟，官方文件寫明暫存目前上限是兩小時，斷線超過兩小時的那段資料會留下缺口。

選擇看的是網路的可達方向與單台 Prometheus 的容量。監控主機連得到每一台、而全部讀取對象在一台 Prometheus 的容量之內時，中央直接讀取的元件最少，本篇以下以它為準；主機在 NAT 後面時，也可以先用 WireGuard 這類 overlay 網路讓監控主機連得進去，維持中央讀取。中央連不進去，或一台 Prometheus 已經讀不完全部讀取對象（容量的估法見 [Prometheus 容量規劃與故障模式](/backend/04-observability/vendors/prometheus/capacity-failure-modes/)）時，改用推送；推送時被監控的主機不必對內開放 exporter 的連接埠，換來的是中央要接受各主機發起的連線，哪一個方向較安全取決於哪一端較不可信（見 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/#地端監控情境需要的連線發起方向與流入的資料)）；`host` 寫在每台 agent 的 `external_labels` 裡，中央的讀取設定不必帶它。

## 代表主機的 host 標籤

每個序列都要帶一個說明「這是哪台主機」的標籤，告警、抑制與面板才分得出主機。Prometheus 自動加上的 `instance` 不能代替它：`instance` 是讀取對象（target）的位址，同一台主機上 node_exporter 是 `10.0.1.11:9100`、cAdvisor 是 `10.0.1.11:8080`，兩者不相等。[抑制規則](/backend/knowledge-cards/alert-inhibition/)以 `instance` 比對原因告警（例如主機 CPU 飽和）與症狀告警（例如讀取變慢）時，只有恰好讀自同一個 exporter 的兩則對得上（實際後果見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/) 的〈依原因抑制〉一節）。所以另外加一個 `host` 標籤，值是這個序列代表的那台主機。另一種做法是用 relabel 把 `instance` 直接改成主機名稱；本篇另外加 `host`，是讓 `instance` 保留讀取位址方便排查，而且探測類指標（Gatus、Blackbox exporter）的 `instance` 是被探測的網址，沒辦法同時當主機名稱。relabel 指 Prometheus 在讀取之前依規則改寫讀取對象的標籤（`relabel_configs`），服務發現帶來的 `__meta_*` 標籤只在這個階段可以取用，之後就丟掉。

`host` 加進去之後，凡是把序列聚合起來的地方都要保留它，否則聚合會把不同主機合在一起，一台主機的狀況被另一台蓋掉。容器停止的規則是最直接的例子（規則本身為什麼看 `container_last_seen`、為什麼取最小值，見 [單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/) 的〈偵測容器停止〉；告警規則在規則檔裡放在 `groups:` 底下的 `rules:` 清單）：

```yaml
- alert: ContainerStopped
  # 一台主機上，某個服務的所有容器都超過 60 秒沒被 cAdvisor 看到
  expr: |
    min by (host, container_label_com_docker_compose_service) (
      time() - container_last_seen{container_label_com_docker_compose_service!=""}
    ) > 60
  for: 1m
  labels: {severity: critical, scope: service}
  annotations:
    summary: "{{ $labels.host }} 上的 {{ $labels.container_label_com_docker_compose_service }} 已有 {{ $value | humanizeDuration }} 沒被 cAdvisor 看到"
```

同一個服務跑在 app-1 與 app-2 兩台主機上、app-2 的容器停了時，分組少了 `host` 的版本取的是兩台的最小值，而 app-1 的容器還在、值很小，整條規則不成立。磁碟的規則同理，依 `host, device, fstype` 分組，不同主機上同名的 `/dev/nvme0n1p1` 才不會合成一個。同一台主機上跑了不只一個 compose 專案、兩邊有同名的服務時，分組再加 `container_label_com_docker_compose_project`，否則一邊停掉會被另一邊的值蓋掉。多台主機時這條規則還依賴時鐘：`container_last_seen` 的值來自被監控主機的時鐘，`time()` 來自 Prometheus 所在的主機，各台要以 NTP（chrony、systemd-timesyncd）同步，偏差接近 60 秒時，容器還在而規則就成立。

告警送到 Alertmanager 之後，分組與抑制也要依主機分開。下面的片段只列 `route` 與 `inhibit_rules`，`receivers` 的寫法見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/)；三個告警名稱取自 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/) 的〈依原因抑制〉，`HostCpuSaturated` 是原因（主機 CPU 飽和），`ScrapeNearTimeout`、`ProbeSlow`、`ServiceSlow` 是症狀（讀取逼近逾時、外部探測變慢、服務自己的延遲變長），換成自己規則檔裡的名稱。名稱對不上時抑制不會報錯，只是不作用：

```yaml
# alertmanager.yml 的 route 與 inhibit_rules
route:
  receiver: none
  group_by: [alertname, host]          # 同一台主機的同一種告警合成一則
inhibit_rules:
  - source_matchers: [alertname="HostCpuSaturated"]
    target_matchers: [alertname=~"ScrapeNearTimeout|ProbeSlow|ServiceSlow", severity="warning"]
    equal: [host]                      # 只壓下同一台主機上的症狀
  - source_matchers: [alertname="HostDown"]   # 整台主機讀不到，見〈主機停掉與主機從清單上消失的偵測〉
    target_matchers: [alertname=~"ScrapeTargetDown|ScrapeNearTimeout"]
    equal: [host]
```

`equal: [host]` 讓一台主機 CPU 飽和只壓下同一台主機上的症狀，其他主機的症狀照常通知；整台主機讀不到時，同一台上各個 exporter 的讀取失敗由 `HostDown` 那一則代表。

面板頂端放一個以 `label_values(up, host)` 產生的下拉選單（Grafana 的儀表板變數，名稱設成 `host`），每個查詢加上篩選、依 `host` 分開，圖例前面加主機名稱：

```promql
# 每台主機各一條：load 除以核心數
node_load1{host=~"$host"}
  / on (host) count by (host) (node_cpu_seconds_total{mode="idle", host=~"$host"})
```

`host` 加在哪裡，取決於目標清單怎麼產生：檔案清單直接寫在每個讀取對象上；用雲端的服務發現時，以 [relabel](/backend/knowledge-cards/relabeling/) 把執行個體的資訊（例如執行個體 ID）複製成 `host` 標籤。單機時在 `static_configs` 的每個讀取對象上寫 `labels: {host: app-1}` 也可以；寫成整個 job 共用的常數（`relabel_configs` 的 `replacement`）只在一個 job 只讀一台主機時成立，一個 job 列了好幾台時，每台都會被標成同一個名字。

## 目標清單的來源：檔案清單與雲端服務發現

Prometheus 讀哪些讀取對象（以下把這份名單稱為目標清單），可以寫死在 `static_configs`，也可以交給服務發現（service discovery）從外部來源產生。寫死的清單在主機增減時要有人記得改，新開的主機漏加時沒有任何錯誤訊息，它只是不在監控裡。

**檔案清單（`file_sd_configs`）**：讀取設定指向一份 YAML 或 JSON 檔，檔案裡列出讀取對象與它們的標籤，`host` 直接寫在每個讀取對象上：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: node
    file_sd_configs:
      - files: [/etc/prometheus/targets/node.yml]   # 容器內的路徑
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

`/etc/prometheus/targets/` 是容器裡的路徑，Prometheus 的服務要把 repo 裡放清單的目錄掛進去。〈單機 Compose 的最小監控堆疊〉把整個 Prometheus 設定目錄掛到 `/etc/prometheus`，清單放在那個目錄的 `targets/` 底下就讀得到；掛的是目錄而不是單一檔案，部署工具以換檔方式改寫清單時，容器才看得到新的內容。檔案不存在或讀不到時 Prometheus 照樣啟動，只寫一行日誌，這個 job 沒有任何讀取對象。從〈單機 Compose 的最小監控堆疊〉改過來時，每一個 job 都要這樣改：那一篇以 compose 的服務名稱寫的讀取對象，在另一台監控主機上解析不到，留著 `static_configs` 的 job 會全部讀取失敗；只有讀 Prometheus 自己與 Alertmanager 的兩個 job 和它們在同一台，可以留著，`host` 改成監控主機的名稱。

Prometheus 會監看這個檔案，內容改了就重新讀取，不必重新載入設定；`refresh_interval` 是監看失效時的定時重讀。在那個短網址服務上（macOS 的 OrbStack），清單加上一台主機之後 13 秒，它就出現在 Prometheus 的 Targets 頁面；另一次把 `refresh_interval` 設成 10 分鐘來測，改檔後 4 秒生效，所以生效靠的是監看而不是定時重讀。這份檔案由 Ansible、Terraform 這類部署工具從主機清單產生，主機清單是部署的依據，監控因此跟著部署走，不靠人記得同步。這個前提是主機只由部署工具建立與移除；有部署工具以外的機制會開關主機時（Auto Scaling、搶占式執行個體被回收），檔案清單會落後實際的主機，被汰換的一直是 `up` 為 0、新開的不在監控裡，這時改用雲端的服務發現（見本節〈雲端的服務發現〉那一段）。

**雲端的服務發現**：在 AWS 上用 `ec2_sd_configs`，Prometheus 定時向 EC2 的 API 查詢執行個體，依 tag 篩選要監控的那些。執行個體的 tag 以 `__meta_ec2_tag_<tag 名稱>` 的形式出現，用 relabel 搬到 `host`：

```yaml
- job_name: node
  ec2_sd_configs:
    - region: ap-northeast-1   # 換成自己的區域
      port: 9100               # 預設是 80，要指定 exporter 的連接埠
      filters:
        - name: tag:monitoring # 只讀帶這個 tag 的執行個體；tag 名稱與值換成自己環境的
          values: [enabled]
  relabel_configs:
    # 讀取對象的位址預設就是私有 IP；host 取執行個體 ID，每台一定不同
    - source_labels: [__meta_ec2_instance_id]
      target_label: host
```

`host` 取執行個體 ID 而不是 Name tag：同一個 Auto Scaling 群組開出來的執行個體多半共用同一個 Name，取 Name 的話各台的 `host` 相同，聚合與抑制又把它們合在一起；Name 每台都不同時才能用它（`__meta_ec2_tag_Name`）。這段設定以 `promtool check config` 檢查過語法，沒有在 AWS 上實際跑過。Prometheus 呼叫 EC2 API 要有權限，跑在 EC2 上時給它所在執行個體的 IAM 角色至少 `ec2:DescribeInstances`。GCP 的 `gce_sd_configs`、Kubernetes 的 `kubernetes_sd_configs` 是同一類，各自提供不同的 `__meta_*` 標籤。

兩種來源的差別在主機被移除時。檔案清單只在部署工具重新產生時改變。`ec2_sd_configs` 在每次重新查詢時（`refresh_interval`，預設 60 秒）更新讀取對象：已終止的執行個體沒有私有 IP，被略過而從清單上消失；停止而沒終止的執行個體仍有私有 IP，留在清單上、`up` 變成 0。篩選條件加上 `instance-state-name` 只取 `running` 的話，停止的執行個體也會從清單上消失。所以停止的執行個體仍在清單上、`up` 變成 0，已終止的（以及加了 `running` 篩選之後停止的）連序列都不見，兩者要用不同的規則偵測。

## 主機停掉與主機從清單上消失的偵測

這一節以中央直接讀取為準。改用各主機推送時，主機停掉時它的 agent 跟著停，Prometheus 不會讀到 `up` 為 0，序列直接中斷，表現和本節的「主機從清單上消失」相同，要用那一段的 `count` 與 `absent` 規則偵測。

**主機停掉、仍在清單上**：Prometheus 讀不到它，`up{host="app-2"}` 變成 0，讀取失敗的告警（`ScrapeTargetDown`）對那台主機成立。這條規則取 15 分鐘內讀取成功的比例，因為主機過載時讀取是間歇失敗，`up == 0` 加持續時間會在兩次失敗之間被打斷（實測見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/) 的〈告警的持續條件〉一節）：

```yaml
- alert: ScrapeTargetDown
  # 15 分鐘內讀取成功的比例低於九成；and up：讀取對象從清單拿掉之後就不再成立
  expr: avg_over_time(up[15m]) < 0.9 and up
  for: 2m
  labels: {severity: warning, scope: monitoring}
  annotations:
    summary: "Prometheus 連不到 {{ $labels.host }} 的 {{ $labels.job }}（{{ $labels.instance }}）"
```

`up` 帶著目標清單上的 `host`，所以告警自己就指出是哪台主機。這條規則的延遲由兩段組成：失敗的比例要累積到低於九成（讀取對象已經跑滿 15 分鐘時，約 1.5 分鐘的失敗），再加上 `for` 的 2 分鐘，合計約 3.5 分鐘。

`and up` 處理的是有意移除的主機。縮容或汰換時，主機常常先停掉、隔一陣子才從清單上拿掉。拿掉之後，15 分鐘的時間窗裡仍留著停機到移除之間的失敗樣本。只寫 `avg_over_time(up[15m]) < 0.9` 的話，規則會對已經不存在的主機再成立十幾分鐘（以 promtool 餵入「上線 15 分鐘、失敗 2 分鐘、接著移除」的序列，移除後 15 分鐘才結束）。`and up` 要求這個讀取對象現在還在，序列過期之後規則就不成立。

整台主機停掉時，這條規則只是 warning，而 critical 的容器停止規則不會成立：cAdvisor 跟著讀不到，它的序列被標成過期，`container_last_seen` 沒有值可算。所以主機層另外一條：

```yaml
- alert: HostDown
  # node_exporter 5 分鐘內沒有一次讀取成功；過載時的間歇失敗中間總有成功的讀取，不會讓它成立
  expr: max_over_time(up{job="node"}[5m]) == 0
  for: 1m
  labels: {severity: critical, scope: host}
  annotations:
    summary: "{{ $labels.host }} 的 node_exporter 5 分鐘內沒有一次讀取成功"
```

**主機從清單上消失**：讀取對象從清單上被拿掉之後，Prometheus 替它的序列寫入過期標記（staleness marker），`up{host="app-2"}` 在即時查詢（instant query）裡直接消失，不會變成 0。讀取失敗的規則只對存在的序列判斷，所以這種情形要另外比對預期的數量，而預期的數量要取自和目標清單不同的來源（部署設定、Auto Scaling 群組的容量、Kubernetes 上 kube-state-metrics 的 `kube_node_info`），不取自同一份清單讀出來的結果：

```promql
# 預期 3 台；數字從部署設定（例如 Auto Scaling 群組的最小容量）來，部署改了這裡跟著改
count(up{job="node"}) < 3

# 某一台不可少的主機，序列不存在時成立
absent(up{job="node", host="db-1"})
```

全部主機同時消失時，`count(up{job="node"})` 沒有結果可以比較而不成立，這時改由〈清單整個空了〉那一條 `absent(up{job="node"})` 偵測。

**清單整個空了**：部署工具產生了空的檔案，或服務發現的篩選條件寫錯，`node` 這個 job 沒有任何讀取對象。這時沒有任何 `up` 序列可以判斷，讀取失敗的規則全部沉默，看起來就像所有主機都正常：

```promql
absent(up{job="node"})
```

用檔案清單時，主機停掉由讀取失敗的規則與 `HostDown` 處理，清單本身就是預期的主機，另外只需要清單整個空了的那一條；清單與預期出自同一份主機清單，產生清單的模板漏掉一台時，監控這一端看不出來，要在部署時比對產出的筆數。用雲端的服務發現時，主機停掉、主機從清單上消失、清單整個空了，三種情形各要有一條規則。

## 監控主機放在哪裡

中央的 Prometheus、Alertmanager 與 Grafana 預設放在一台獨立的監控主機上，不和被監控的服務共用。共用時，那台主機過載或停掉，監控跟著一起退化或停掉，而那正是最需要它的時候（見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)）。監控主機自己停掉時，它發不出任何告警，所以另外需要一個不經過它的訊號：在監控主機以外跑的外部探測，以及一條永遠成立的 Watchdog 告警，經由 Alertmanager 持續送到外部的心跳監看服務，心跳中斷時由外部服務通知（設定見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/) 的〈Watchdog：告警鏈本身的心跳〉；這個訊號為什麼要從主機外面發出，見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/) 的〈探測程式與 Prometheus 在過載主機上的 CPU 等待〉一節）。這一節處理的是同一個私有網路（同一個 VPC）裡分出一台監控主機；同一個業者、同一個區域的主機仍共用業者與帳號這一層的[失效域](/backend/knowledge-cards/failure-domain/)，監控主機放在另一個業者或地端、經 VPN 讀取的配置見 [小型服務的兩到三台主機配置](/operations/06-high-availability/small-service-host-layout/)。服務已經分到兩三台、預算不允許再多一台時，把 Prometheus、Alertmanager 與 Grafana 放在負載最低的那一台，Watchdog 與外部探測照樣保留，代價是那一台過載時監控跟著退化、那一台停掉時它上面的服務與監控一起停；這時 Watchdog 的心跳監看與外部探測要放在這幾台以外（見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)）。

元件因此分成三個 compose 檔：每一台主機（含監控主機）都要跑的 node_exporter 與 cAdvisor 在 `compose.host-exporters.yml`，跟著服務走的 exporter 和服務一起留在 `docker-compose.yml`，Prometheus、Alertmanager、Grafana 在 `compose.monitoring.yml`。監控主機也跑主機層的 exporter，它自己的 CPU、記憶體與磁碟才有人看；它停掉時由 Watchdog 發現，而過載或磁碟快滿要靠它自己的 node_exporter。每台主機在自己的 `.env`（不進版控，每台內容不同）以 `COMPOSE_FILE` 決定讀哪幾個檔，同一個 repo 在每台主機上執行同一條 `docker compose up -d`。`COMPOSE_FILE` 裡檔名的分隔符在 Linux、macOS 是 `:`，Windows 是 `;`：

| 主機                       | `.env` 的 `COMPOSE_FILE`                                                                                      |
| -------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 單機（服務與監控在同一台） | `docker-compose.yml:compose.host-exporters.yml:compose.monitoring.yml`                                        |
| 被監控的主機               | `docker-compose.yml:compose.host-exporters.yml:compose.exporters-published.yml`，另設 `EXPORTER_BIND_ADDR`    |
| 監控主機                   | `compose.host-exporters.yml:compose.monitoring.yml`，目標清單裡以服務名稱列上自己的 node_exporter 與 cAdvisor |

本篇取材的短網址服務只把監控元件拆了出來：它的 `docker-compose.yml` 仍把全部的應用服務、資料庫與快取放在一起，照上表在每台被監控的主機上跑，每一台都會起整套服務。服務要真的分到多台主機，還要依主機的角色再拆 compose 檔（例如資料庫主機只有 PostgreSQL、Valkey 與跟著它們的 exporter，`COMPOSE_FILE` 換成那一組），疊加檔裡也只留那台主機上實際有的 exporter。

## 在單機上模擬第二台主機的驗證

標籤、清單、規則與抑制這幾個機制不依賴主機的數量，所以在同一台機器上多跑一個 node_exporter 當作第二台主機，就能各自確認；兩台主機各自的數字不在確認的範圍內。這個第二台主機的連接埠開在主機的位址上，讓 Prometheus 經由主機的位址讀它，而不是經由 compose 網路的服務名稱：

```sh
# 模擬的 host-b：一個獨立的 node_exporter。用 19100 避開正式那個 node_exporter 的 9100
# Docker Desktop、OrbStack：綁 127.0.0.1 即可
docker run -d --name hostb-node-exporter -p 127.0.0.1:19100:9100 quay.io/prometheus/node-exporter:v1.12.1
# Linux 上的 Docker：綁在 docker0 的位址（ip -4 addr show docker0 查得到，常見是 172.17.0.1）
docker run -d --name hostb-node-exporter -p 172.17.0.1:19100:9100 quay.io/prometheus/node-exporter:v1.12.1
```

```yaml
# 在 targets/node.yml 加上這一筆
- targets: ["host.docker.internal:19100"]
  labels: {host: host-b}
```

`host.docker.internal` 是容器連到主機的名稱，Docker Desktop 與 OrbStack 預設提供；Linux 上要在 Prometheus 的服務加 `extra_hosts: ["host.docker.internal:host-gateway"]`，它解析到 docker0 的位址，所以模擬的 exporter 要綁在那個位址上，綁 127.0.0.1 的話只有主機自己連得到。Linux 這兩行依 Docker 的文件寫成，沒有在 Linux 上實測；下表的結果來自 macOS 的 OrbStack：

| 確認的事               | 做法                                                                      | 結果                                          |
| ---------------------- | ------------------------------------------------------------------------- | --------------------------------------------- |
| 清單改了不必重新載入   | 在 `targets/node.yml` 加上 host-b 那一筆                                  | 13 秒後出現在 Targets 頁面，`host="host-b"`   |
| 主機停掉時只對它告警   | `docker stop hostb-node-exporter`                                         | 讀取失敗的告警對 host-b 成立，app-1 沒有      |
| 抑制只作用在同一台主機 | 以 Alertmanager 的 API 送入合成的告警，見下方                             | host-b 的讀取變慢被抑制，host-c 的仍是 active |
| 聚合保留了 host        | promtool 的規則單元測試，再把 `ContainerStopped` 分組裡的 `host` 拿掉重跑 | 測試通過；拿掉 `host` 之後失敗                |

主機停掉那一項成立得比〈主機停掉與主機從清單上消失的偵測〉估的 3.5 分鐘快（2 分 21 秒），因為 host-b 加進清單不到一分鐘就被停掉，15 分鐘的時間窗裡只有幾次成功的讀取，第一次失敗就讓比例低於九成，只剩 `for` 的 2 分鐘。模擬的 host-b 讀的是同一台虛擬機，數字和 app-1 一樣，所以這組驗證確認的是標籤、清單、規則與抑制的機制，不是兩台主機各自的數字。

抑制那一項以 Alertmanager 的 API 送入三則合成的告警：host-b 的主機飽和（原因），以及 host-b 與 host-c 各一則讀取變慢（症狀）；host-c 只存在於這則合成告警，用來確認不同主機的症狀不受影響。`endsAt` 讓它們 10 分鐘後自己結束：

```sh
# macOS 的 date 語法；Linux 用 date -u -d '+10 min' +%Y-%m-%dT%H:%M:%SZ
now=$(date -u +%Y-%m-%dT%H:%M:%SZ); end=$(date -u -v+10M +%Y-%m-%dT%H:%M:%SZ)
curl -XPOST http://127.0.0.1:9093/api/v2/alerts -H 'Content-Type: application/json' -d "[
  {\"labels\":{\"alertname\":\"HostCpuSaturated\",\"severity\":\"warning\",\"host\":\"host-b\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"},
  {\"labels\":{\"alertname\":\"ScrapeNearTimeout\",\"severity\":\"warning\",\"host\":\"host-b\",\"job\":\"injected\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"},
  {\"labels\":{\"alertname\":\"ScrapeNearTimeout\",\"severity\":\"warning\",\"host\":\"host-c\",\"job\":\"injected\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"}]"
# 每則告警的 status.state 是 suppressed 或 active，inhibitedBy 列出壓下它的原因告警
curl -s http://127.0.0.1:9093/api/v2/alerts
```

第一次跑這一項時 host-c 的那一則也被抑制了：Alertmanager 設定檔的內容改了而掛載路徑沒變，`docker compose up -d` 沒有重建容器，Alertmanager 繼續用沒有 `equal: [host]` 的舊設定。打 `POST /-/reload` 之後結果正確；設定由誰、在什麼時候讀進去，見〈單機 Compose 的最小監控堆疊〉的 Prometheus 一節。

規則的單元測試以 `promtool test rules` 執行，餵入合成的時間序列、指定在某個時間點預期成立的告警與它的標籤：

```yaml
# tests/alerts.test.yml 的一段：同一個服務在兩台主機上，只有 app-2 的停了
rule_files:
  - ../rules/alerts.yml            # 相對於這個測試檔的位置
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

```sh
# 在 repo 的根目錄跑；infra/observability/prometheus 是放 rules/ 與 tests/ 的設定目錄，依自己的結構換
# promtool 隨 Prometheus 的映像附帶，不必另外安裝
docker run --rm -v "$PWD/infra/observability/prometheus:/p" -w /p/tests \
  --entrypoint promtool prom/prometheus:v3.15.0 test rules alerts.test.yml
```

測試通過只說明規則照測試寫的方式運作，所以另外把規則改壞一次（拿掉分組裡的 `host`）確認測試會失敗；改壞了仍然通過的測試，檢查不到它宣稱檢查的那件事。

## 延伸閱讀：推送架構、容量與告警

- 改用各主機推送到中央時，中央儲存的選擇與 remote write 的故障模式，見 [Remote Write 與長期儲存整合](/backend/04-observability/vendors/prometheus/remote-write-long-term-storage/)。
- 主機變多之後一台 Prometheus 的時間序列數、記憶體與讀取逾時，見 [Prometheus 容量規劃與故障模式](/backend/04-observability/vendors/prometheus/capacity-failure-modes/)。
- `host` 標籤在探測類指標（Gatus、Blackbox exporter）、Pushgateway 與 Kubernetes 上各自怎麼加，以及主機飽和時的抑制規則，見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/) 的〈依原因抑制：主機飽和時壓下各服務變慢〉一節；Kubernetes 上在讀取時以 `relabelings` 加節點標籤的做法，見 [在 Kubernetes 上接上監控](/backend/04-observability/vendors/prometheus/kubernetes-monitoring-entry/) 的〈主機標籤改成節點標籤〉。
- 誰能看面板、Viewer 與 Editor 的權限分級，以及告警規則留在 Prometheus 還是放進 Grafana，見 [Prometheus 指標的視覺化工具](/backend/04-observability/vendors/prometheus/visualization-tool-selection/)。
- 監控主機上的 Grafana 只綁本機，讓其他電腦上的人看到它的做法（SSH 通道或 VPN，或監控主機上專用的反向代理），見 [Grafana 的對外存取](/backend/04-observability/vendors/prometheus/grafana-external-access/)。
