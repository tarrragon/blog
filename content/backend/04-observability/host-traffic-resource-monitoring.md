---
title: "4.26 單機容器服務的流量與資源監控：各層的訊號、Prometheus 與 exporter、監控所在層的盲區"
date: 2026-10-12
description: "健康檢查之外的流量與資源監控：入口、應用程式、容器、主機與資料庫等服務內部各層的訊號從哪裡收、用哪一個 exporter，Prometheus 加 exporter、單一 agent、開箱即用工具與臨時查看指令的取捨，單次取樣與時間窗的差別，以及監控裝在虛擬機裡時看不到主機的 CPU 負載、看到的磁碟要分清是哪一顆；附 OrbStack 上 cAdvisor 與 node_exporter 的實測"
weight: 26
tags: ["backend", "observability", "prometheus", "monitoring", "docker"]
---

這篇整理一台主機（或一台虛擬機）上以 Docker Compose 跑的服務，在健康檢查之外怎麼監控流量與資源用量：每一層的訊號從哪裡收、工具怎麼選，以及監控本身裝在哪一層就看不到哪些範圍。範例是一個入口 Nginx、兩個後端、PostgreSQL 與 Valkey 組成的短網址服務。Kubernetes 上的做法（Prometheus Operator、ServiceMonitor）見 [Prometheus](/backend/04-observability/vendors/prometheus/) 的進階主題。

文中的實測在 macOS 的 OrbStack 2.2.3（Docker 29.4.0）上進行，cAdvisor 是 v0.55.1。

## 健康檢查之外的兩個問題：流量與資源

健康檢查回答的是「服務活著嗎」：容器的 healthcheck 確認自己的端點回得了話，外部探測（例如 Gatus、Blackbox exporter）確認從外面打得通。服務活著而變慢、或者某一層快滿了，健康檢查都照樣回報正常，因為它問的不是這兩件事。

**流量監控**問的是每一個服務收到多少請求、多少失敗、花了多久，業界的整理方式是 [RED Method](/backend/knowledge-cards/red-method/)：Rate（每秒請求數）、Errors（錯誤率）、Duration（延遲的分布）。**資源監控**問的是每一種資源用了多少、有沒有開始排隊，整理方式是 [USE Method](/backend/knowledge-cards/use-method/)：Utilization（使用率）、Saturation（排隊的程度，例如等 CPU 的行程數、等連線的請求數）、Errors。兩者要一起看：延遲升高（RED）時，第一個開始排隊的資源（USE）就是瓶頸所在；資源用量升高而延遲不變，代表還有餘裕。

## 各層的訊號從哪裡來

一個請求從入口走到資料庫，每一層只看得到請求經過它的那一段。下表列出每一層看得到什麼、Prometheus 生態裡常用的收集方式，以及那一層結構上看不到的資訊。收集方式欄的 **exporter** 是把某個系統的狀態轉成 Prometheus 指標格式、開一個 HTTP 端點讓 Prometheus 定期來讀的程式（見 [Prometheus Exporter](/backend/knowledge-cards/prometheus-exporter/)）。

| 層           | 看得到                                                                         | 收集方式                                                                            | 看不到                                                                 |
| ------------ | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| 入口 Nginx   | 全部進來的請求，含沒進到後端就被擋下或回錯的；依網域、狀態碼、交給哪個上游分開 | access log 送進 log 系統再計數；連線數由 `stub_status` 加 nginx-prometheus-exporter | 後端內部花在哪裡                                                       |
| 應用程式     | 依路由的延遲、快取命中、業務事件                                               | 程式用 client library 自己開 `/metrics`                                             | 程式還沒收到的請求、程式所在的容器被限流                               |
| 容器         | 每個容器的 CPU、記憶體、網路、磁碟讀寫，以及被 CPU 配額限流的時間              | cAdvisor 讀 cgroup                                                                  | 容器裡是哪個行程、哪個查詢在用資源                                     |
| 主機或虛擬機 | 整台的 CPU、記憶體、load、磁碟空間與讀寫、網路                                 | node_exporter 讀 `/proc`、`/sys` 與掛載點                                           | 它自己所在那一層以外的機器，見〈監控所在層看不到的範圍：虛擬機與主機〉 |
| 服務內部     | PostgreSQL 的連線數、鎖、慢查詢；Valkey 的記憶體、命中率、被淘汰的鍵           | postgres_exporter、redis_exporter（也支援 Valkey）                                  | 應用程式那一端排隊等連線的請求                                         |
| 外部探測     | 從外面打不打得通、花多久                                                       | Blackbox exporter 或 Gatus 的指標                                                   | 真實使用者的流量                                                       |

入口與應用程式兩層都在量流量，兩者的差別是有用的訊號：入口的請求數多於後端收到的數量，差額是被入口擋下、限流或在後端之前就失敗的請求。容器、主機與服務內部三層都在量資源，粒度由粗到細：主機的 CPU 滿了，容器那一層分得出是哪個服務，服務內部那一層分得出是哪一類工作（例如 PostgreSQL 的連線全被某種查詢佔住）。

## 工具的選項：Prometheus 加 exporter、單一 agent、開箱即用、臨時查看

| 做法                                         | 代表工具                               | 留下什麼                                               |
| -------------------------------------------- | -------------------------------------- | ------------------------------------------------------ |
| Prometheus 加各層的 exporter，面板用 Grafana | 上表的 exporter                        | 每一層的時間序列，同一個查詢語言（PromQL）、同一張面板 |
| 一個 agent 收全部                            | Grafana Alloy、OpenTelemetry Collector | 同上，加上 log 與 trace 走同一條管線                   |
| 開箱即用的主機監控                           | Netdata、Beszel                        | 自帶面板的即時與短期歷史                               |
| 臨時查看                                     | `docker stats`、ctop、lazydocker       | 當下那一刻的數字                                       |

**Prometheus 加 exporter** 適合要拿監控數字做判斷的情況：壓測時要知道瓶頸在哪一層、要把應用程式自己的指標和資源用量放在同一張面板對照、要保留歷史比較改動前後。每個 exporter 只做一件事、各自有文件，出問題時容易定位是哪一層沒收到；代價是 compose 多出五、六個容器（約幾百 MB 記憶體），面板要自己組或匯入社群的。

**單一 agent** 把多個 exporter 的工作收進一個行程，之後要收 log 與 [trace](/backend/knowledge-cards/trace/) 時不必再加一套管線（見 [4.11 Telemetry Pipeline 架構](/backend/04-observability/telemetry-pipeline/)）。設定比單一用途的 exporter 抽象，只收指標時多付了這份複雜度。

**開箱即用的工具** 裝上就看得到每個容器與主機的即時狀況，適合只想知道「現在誰在吃資源」。它們的資料和應用程式的指標不在同一個系統裡，壓測紀錄要另外抄數字。

**臨時查看的指令** 沒有歷史，而且只取一個瞬間，判讀上的限制見〈單次取樣與時間窗〉。

## 單次取樣與時間窗：`docker stats` 的數字為什麼會跳

`docker stats --no-stream` 回報的 CPU 百分比，是兩次讀取 cgroup 之間的短暫區間算出來的。同一個 Valkey 容器在幾秒內連續取樣八次，結果是 1.41%、0.25%、27.40%、8.26%、1.95%、0.77%、10.87%、0.12%。看到一次 27% 或一次 110%，不能推論那個服務一直很忙。

cAdvisor 輸出的是累計值：`container_cpu_usage_seconds_total` 是這個容器啟動以來用掉的 CPU 秒數，只增不減。Prometheus 每次讀取都記下當時的累計值，查詢時用 `rate()` 在一段時間窗內算平均速率：

```promql
# 每個 compose 服務在最近 5 分鐘平均用掉幾顆 CPU（1 代表一整顆核心）
sum by (container_label_com_docker_compose_service) (
  rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service!=""}[5m])
)
```

時間窗的長度決定看到什麼：5 分鐘的窗把短暫的尖峰平均掉，適合看持續的用量；要看尖峰，改用較短的窗，再用子查詢取一段時間內的最大值，例如 `max_over_time(rate(...[1m])[1h:])`。窗至少要涵蓋兩次讀取才算得出速率，常見的做法是取讀取間隔的四倍以上（間隔 15 秒時取 1 分鐘），漏掉一次讀取也還算得出來。量測前先決定要回答的是「平常用多少」還是「最高到多少」。

## 在 OrbStack 這類環境上：cAdvisor 讀不到容器名稱

cAdvisor 從 cgroup 讀資源用量，cgroup 只認得一個 id；要知道 id 對應哪個容器、容器帶哪些標籤，cAdvisor 要連上容器執行環境的 socket 去問。照官方說明的掛載方式在 OrbStack 上執行時，指標裡只有 `id="/docker/<64 碼雜湊>"`，沒有 `name` 與 compose 服務的標籤，日誌寫著：

```text
Registration of the docker container factory failed: unable to create containerd client:
containerd: cannot unix dial containerd api service: dial unix /run/containerd/containerd.sock: connect: no such file or directory
```

cAdvisor 預設到 `/run/containerd/containerd.sock` 找 containerd，而 OrbStack 的 Docker 把它自己的 containerd socket 放在別的位置。socket 實際在哪裡，掛載虛擬機的 `/var/run` 進一個容器去找：

```sh
docker run --rm -v /var/run:/host-run:ro alpine find /host-run -name 'containerd*.sock'
```

在這次測試的 OrbStack 上找到的是 `/var/run/docker/containerd/containerd.sock`，以 `--containerd=<找到的路徑>` 啟動 cAdvisor 之後，日誌改成 `Registration of the docker container factory successfully`，每個容器都帶上了 `name` 與 `container_label_com_docker_compose_service`，〈單次取樣與時間窗〉那段依服務分組的查詢才有結果。其他把 Docker 跑在虛擬機裡的環境（Docker Desktop、Colima）socket 的位置各自不同，用同一個方法找；指標裡只看得到雜湊 id 時，先檢查的就是這一條日誌。

這類問題有個共同的形狀：exporter 起來了、Prometheus 讀得到、指標也有數字，缺的是讓人分辨數字屬於誰的那一層標籤。所以監控接上之後，驗收不只看讀取成功（Prometheus 的 `up` 是 1），還要看每一個預期的服務都出現在指標的標籤裡。

## 監控所在層看不到的範圍：虛擬機與主機

macOS 上的 Docker 跑在一台 Linux 虛擬機裡，容器與裝在 compose 裡的 node_exporter 都在這台虛擬機裡。node_exporter 回報的是虛擬機，同一個時間點和 Mac 本機對照：

| 項目                   | node_exporter（虛擬機） | Mac 本機 |
| ---------------------- | ----------------------- | -------- |
| load average（1 分鐘） | 2.89                    | 55       |
| 記憶體                 | 8.4 GB                  | 16 GB    |

**load average** 是一段時間內處於可執行狀態（在跑或在等 CPU）的平均行程數，Linux 另外把等待磁碟讀寫的行程也算進去；大於核心數代表有行程在排隊。這台 Mac 有 8 顆核心，load 55 代表嚴重排隊，而虛擬機裡只看到 2.89：排隊的是 Mac 上的其他程式，虛擬機只是分到的 CPU 時間變少。容器裡的工作因此全面變慢，而虛擬機與容器的監控都顯示用量很低，從它們的數字找不到原因。

磁碟的情況不同：虛擬機裡看得到兩顆磁碟，要分清楚是哪一顆。

- **虛擬機放 Docker 資料的磁碟**（OrbStack 上是 `device="/dev/vdb1"`，掛在 `/var/lib/docker`）：它是存在 Mac 磁碟上的一個映像檔，用到才佔用 Mac 的空間。實測它回報可用 34.6 GB 時，Mac 實際只剩 15 GB；後來另一個時間點它剩 48.9%，Mac 剩 2.4%。
- **Mac 本機的磁碟**：OrbStack 用 virtiofs 把 Mac 的 `/Users`、`/private` 等目錄掛進虛擬機，node_exporter 以 `device="mac"`、`fstype="virtiofs"` 回報它，數字和 Mac 上的 `df` 一致。

只看 Docker 那一顆會以為空間充足。Mac 的磁碟寫滿時，虛擬機（連同裡面全部的容器）會被停掉（實測時 Mac 剩不到 1 GB，大量寫入 PostgreSQL 的過程中連續發生三次）。所以磁碟的告警要依裝置分組、兩顆都涵蓋（同一顆磁碟常掛在好幾個掛載點，不分組時一顆磁碟會發好幾則告警）：

```promql
# 每一顆磁碟的剩餘比例，低於 10% 告警
min by (device, fstype) (
  node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs|vfat"}
  / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs|vfat"}
) < 0.10
```

其他把 Docker 跑在虛擬機裡的環境不一定把主機的目錄掛進來，查 `node_filesystem_size_bytes` 裡有沒有大小和主機磁碟一致的那一顆就知道。

所以監控的範圍由它裝在哪一層決定：

- **Linux 主機直接跑 Docker**：node_exporter 看到的就是真正的主機，上表的落差不存在。
- **macOS 或 Windows 上的 Docker**：主機的 CPU 負載要在主機上另外量；磁碟看虛擬機有沒有掛進主機的那一顆。node_exporter 有 macOS 的版本可以裝在 Mac 本機，本篇沒有實測；最低限度是在開始大量資料的實驗或壓測之前，在主機上看一次 load 與磁碟空間，寫成腳本、超過門檻就不開始。
- **雲端的虛擬機**：同一個問題換成「同一台實體機上的其他租戶」。Linux 的 `node_cpu_seconds_total{mode="steal"}` 記錄虛擬機想用 CPU 而被 hypervisor 分給別人的時間，持續升高時，慢的原因在虛擬機之外。

## 導入的順序與驗收

導入時先接資源層（cAdvisor、node_exporter、資料庫與快取的 exporter），再接應用程式自己的指標：資源層不依賴任何應用程式碼，接上就有數字；應用程式的指標名稱與標籤要先在各個實作之間定好，同一份面板才能並排比較兩個實作。

每接上一個來源，驗收三件事：

1. **讀得到，而且 exporter 連得到它監控的服務**：Prometheus 的 Targets 頁面上它是 `UP`，或查詢 `up{job="<名稱>"}` 是 1。`up` 只代表 Prometheus 連得到 exporter；postgres_exporter 連不上 PostgreSQL 時 `up` 照樣是 1，要另外看 exporter 自己輸出的連線狀態（`pg_up`、`redis_up`、`nginx_up`）。
2. **每一個預期的服務都出現在標籤裡**：例如查 `count by (container_label_com_docker_compose_service) (container_memory_working_set_bytes)`，一個服務一列。
3. **刻意製造一次它該看到的狀況，確認數字有反應**。監控只在出事時被讀，平常沒有人會發現它讀不到或讀錯。

同一個短網址服務第一次接上時，「刻意製造狀況」那一項的實測：

| 製造的狀況                            | 看哪個指標                               | 結果                 |
| ------------------------------------- | ---------------------------------------- | -------------------- |
| 在 Valkey 的容器裡跑一個空轉的迴圈    | 該服務的 CPU（1 分鐘平均）               | 0.98 顆核心          |
| 開 5 個連線各自 `select pg_sleep(90)` | `pg_stat_activity_count{state="active"}` | 5                    |
| 停掉前台的容器                        | Gatus 對前台的探測                       | 0（失敗）            |
| 停掉前台的容器                        | cAdvisor 裡那個容器的序列                | **3 分鐘後仍然存在** |

最後一列是要特別記下的行為：容器停掉之後，cAdvisor 繼續輸出它最後的 CPU 與記憶體數值，依服務分組的圖上那條線維持在停掉前的值，看起來像服務還在。停止前進的是 `container_last_seen`（這個容器最後一次被看到的時間），所以偵測容器停了要看 `time() - container_last_seen` 有沒有持續增加；告警寫成「序列消失」的話永遠不會響。寫成告警時依服務取最小值：

```promql
# 一個 compose 服務的所有容器都超過 60 秒沒被看到，才算這個服務停了
min by (container_label_com_docker_compose_service) (
  time() - container_last_seen{container_label_com_docker_compose_service!=""}
) > 60
```

用最大值會在重建容器時誤報：服務重建之後，cAdvisor 同時留著舊容器與新容器兩條序列，舊的那條停止前進。實測強制重建一個容器 150 秒後，最大值是 161 秒、最小值是 10 秒。

## 延伸閱讀：指標的設計、面板與告警、監控自己的失效

- 指標的型別、命名與 [SLI / SLO](/backend/knowledge-cards/sli-slo/) 的量法，見 [4.2 metrics 與 SLI/SLO](/backend/04-observability/metrics-basics/)。
- 面板要放哪些圖、告警的門檻怎麼定，見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)。
- 標籤組合太多讓 Prometheus 的記憶體爆掉，見 [4.7 Cardinality 治理與成本邊界](/backend/04-observability/cardinality-cost-governance/)。
- 監控跟著它監控的系統一起失效（同一台主機、同一個磁碟），見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)；本篇的虛擬機盲區是它在單機開發環境上的形態。
