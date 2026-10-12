# 各層的 exporter：接法與實測遇到的問題

> 何時讀：盤點訊號與實作時，要為某一層選收集方式、寫部署設定，或某一層接上之後數字不對時讀。不適用：判讀壓測或事故的數字。接上一個來源之後，走 `verification.md` 的三項驗收。

## 實作的共同規則

- **版本固定**：映像檔寫明版本，不用 `latest`；README 的版本表與部署設定一致。
- **對外的連接埠只綁本機**：Prometheus、Grafana 的程式預設聽全部介面，所以在部署設定裡把連接埠寫成只綁 `127.0.0.1`（例如 compose 寫 `"127.0.0.1:9090:9090"`）；要對外時另外決定經過哪個入口與認證。
- **exporter 用最小權限的帳號**：資料庫的 exporter 用專用帳號（PostgreSQL 給內建的 `pg_monitor`），不沿用應用程式的帳號。帳號由資料庫初始化腳本建立時，初始化腳本只在資料目錄是空的時候執行，既有的資料庫要另外補建，把補建的指令寫進 README。
- **設定與面板以檔案進 repo**：讀取設定、Grafana 的資料來源與面板以 provisioning 檔佈建，介面上的修改不寫回檔案（`allowUiUpdates: false`），以檔案為準。
- **環境相依的值用環境變數，並寫下找法**：例如 cAdvisor 的 containerd socket 路徑。只寫值的話，換一個環境的人會照抄。

## 各層

盤點表的「看不到」欄以 SKILL.md〈盤點訊號〉的表為準；這張表的最後一欄是這個工具收不到、要改由哪裡收的資訊。

| 層 | 工具 | 接法 | 這個工具收不到（改由哪裡收） |
| --- | --- | --- | --- |
| 入口（Nginx） | nginx-prometheus-exporter | 代理開一個只聽內部 port、只允許私有位址的 `stub_status`，exporter 讀它 | 依網域、狀態碼、上游分開的請求數：要從 access log 算 |
| 容器 | cAdvisor | 掛載 `/`、`/var/run`、`/sys`、`/var/lib/docker`，`--docker_only=true`（只在 Docker 引擎上用）；containerd socket 不在預設位置的環境要用 `--containerd` 指定 | 容器裡是哪個行程 |
| 主機 | node_exporter | `pid: host`、掛載 `/` 到 `/host` 並 `--path.rootfs=/host`；留在容器網路裡時關掉 `netdev`、`netstat`、`sockstat`（看到的是自己容器的網路），網路改看 cAdvisor | 它所在那一層以外的機器的 CPU 負載；磁碟看得到哪幾顆依環境而定，見本檔〈實測遇到的問題〉的磁碟告警一則 |
| PostgreSQL | postgres_exporter | 專用帳號加 `pg_monitor` | 個別查詢的耗時：要 `pg_stat_statements` |
| Redis / Valkey | redis_exporter | `REDIS_ADDR` 指向服務 | 應用程式那一端等它的時間 |
| 外部探測 | Gatus（`metrics: true`）、Blackbox exporter | 探測條件只放可用性 | 真實使用者的流量 |
| 應用程式 | client library 的 `/metrics` | 同一組 API 有多個實作時，各實作共用同一份指標名稱與標籤，才能並排比較 | 在應用程式之前就失敗的請求（入口擋下、連不上）：用入口與應用程式的請求數差額算 |

## 實測遇到的問題

**cAdvisor 只有 cgroup 的雜湊 id、沒有容器名稱與 compose 標籤**：cAdvisor 要問 containerd 才知道 cgroup 是哪個容器。cAdvisor 容器的日誌（`docker logs <cAdvisor 容器>`）有 `Registration of the docker container factory failed: ... containerd.sock: connect: no such file or directory` 就是這個成因，而 `up` 照樣是 1。找 socket 的位置：

```sh
docker run --rm -v /var/run:/host-run:ro alpine find /host-run -name 'containerd*.sock'
```

把找到的路徑（去掉 `/host-run`、換回 `/var/run`）傳給 `--containerd`；同時列出的 `containerd-debug.sock` 是除錯用的，不取。Linux 主機直接跑 Docker 時預設的 `/run/containerd/containerd.sock` 就對；OrbStack 在 `/var/run/docker/containerd/containerd.sock`（OrbStack 2.2.3 時）；其他把 Docker 跑在虛擬機裡的環境（Docker Desktop、Colima）沒有實測，用同一個方法找；找到的若是空的，先確認 `-v /var/run` 掛到的是虛擬機那一層。換回 `/var/run` 的前提是 cAdvisor 本身以 `/var/run:/var/run` 掛載。

**容器停掉之後 cAdvisor 仍輸出它最後的值**：序列不消失，依服務分組的圖維持在停掉前的值。停止前進的是 `container_last_seen`。

**設定檔掛載進容器時，改內容不會讓 compose 重建容器**：例如 Gatus 的設定檔改成 `metrics: true` 之後要手動重啟那個容器；Prometheus 的讀取設定同理（或打它的 reload 端點）。

**改了某個服務的環境變數，compose 會重新建立它，依賴它的服務也跟著重新啟動**：例如給資料庫加 exporter 帳號的密碼變數，資料庫被重新建立、依賴它的後端跟著重新啟動。正式環境改這類環境變數之前要排停機或維護時間。

**磁碟告警一顆磁碟發好幾則，或漏掉主機的磁碟**：同一顆磁碟常掛在好幾個掛載點（OrbStack 把主機的 `/Users`、`/private`、`/tmp` 等都掛進虛擬機），依掛載點告警時一顆磁碟發好幾則。依裝置分組：

```promql
min by (device, fstype) (
  node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs|vfat"}
  / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs|vfat"}
) < 0.10
```

分組前先跑 `count by (device, fstype) (node_filesystem_size_bytes)` 列出各顆，對照主機上 `df` 的大小，認出哪一顆是主機的磁碟（OrbStack 2.2.3 上它的 `fstype` 是 `virtiofs`）。只看 Docker 資料那一顆會漏掉主機快滿。

**規則改了要重新載入**：規則或設定改完，先用 `promtool check rules`、`amtool check-config` 檢查語法，再重新載入。Prometheus 啟動時加 `--web.enable-lifecycle`，才能 `POST /-/reload`；Alertmanager 一律可以打它的 `POST /-/reload`（或送 SIGHUP），不需要額外的旗標。

## 主機標籤

多台主機時，抑制規則以 `equal: [host]` 對應原因與症狀，`host` 指症狀發生的那台主機。各種讀取對象的加法不同：

```yaml
scrape_configs:
  # 本機的 exporter：讀取對象跑在哪台主機，host 就是哪台
  - job_name: node
    static_configs:
      - targets: ["host-a:9100"]
        labels: { host: host-a }
  # 探測：讀取對象是探測程式，host 依被探測的端點填（這裡用 Gatus 的 name 標籤對應）
  - job_name: gatus
    static_configs:
      - targets: ["probe-host:8080"]
    metric_relabel_configs:
      - source_labels: [name]
        regex: "Laravel 後端|Go 後端"
        target_label: host
        replacement: host-a
  # Pushgateway：推送端在 grouping label 帶 host，這裡保留推送端給的標籤
  - job_name: pushgateway
    honor_labels: true
    static_configs:
      - targets: ["pushgateway:9091"]
```

Blackbox exporter 從 `__param_target` 推出被探測的主機。Kubernetes 上服務的序列帶 Pod 的位址，以 `* on (namespace, pod) group_left(node) kube_pod_info` 接上 `node`；node_exporter 那一側以 `label_replace` 產生同名的 `node`，兩側都有同名同值的標籤，`equal` 才對得上。

## 部署在 Kubernetes 時

盤點、盲區、驗收與告警的原則照用，實作的位置換成那套平台與 operator 的做法（以 kube-prometheus-stack 為例）：

- **容器層不另外部署 cAdvisor**：kubelet 內建 cAdvisor，operator 已經讀它，再部署一份會重複收集。
- **規則與抑制寫進 operator 的資源**：告警規則寫成 PrometheusRule，Alertmanager 的設定走 Helm values 或 AlertmanagerConfig，不去編 `rule_files` 再打 reload。AlertmanagerConfig 預設只在自己的 namespace 內比對，節點層的原因告警壓不到其他 namespace 的症狀；跨 namespace 的抑制寫進全域的 Alertmanager 設定。新增之前先列出既有的規則與抑制，這類 stack 已內建 Watchdog 與一組預設的抑制規則，照 SKILL.md 再加一條會重複。
- **標籤不同**：區分服務用 `namespace` 加 `pod` 或 `container`；抑制以節點對應時，原因與症狀兩側都要有 `node` 標籤，寫法見〈主機標籤〉。
- **容器停止**：控制器會重啟或重建 Pod，看 kube-state-metrics 的 Pod 與 Deployment 狀態（例如可用副本數低於期望值），不用 `container_last_seen`。
- **主機外的訊號**：單位是叢集，訊號要跑在叢集之外。
