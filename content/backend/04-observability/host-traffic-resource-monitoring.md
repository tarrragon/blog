---
title: "4.26 單機容器服務的流量與資源監控：各層的訊號、Prometheus 與 exporter、監控所在層的盲區"
date: 2026-10-12
description: "健康檢查之外的流量與資源監控：入口、應用程式、容器、主機與資料庫等服務內部各層的訊號從哪裡收、用哪一個 exporter，Prometheus 加 exporter、單一 agent、開箱即用工具與臨時查看指令的取捨，單次取樣與時間窗的差別，監控裝在虛擬機裡時看不到主機的 CPU 負載、看到的磁碟要分清是哪一顆，以及每接上一個來源的驗收與偵測容器停止的寫法；cAdvisor 與 node_exporter 在 OrbStack 上實測過"
weight: 26
tags: ["backend", "observability", "prometheus", "monitoring", "docker"]
---

這篇整理一台主機（或一台虛擬機）上以 Docker Compose 跑的服務，在健康檢查之外怎麼監控流量與資源用量：每一層的訊號從哪裡收、工具怎麼選，以及監控本身裝在哪一層就看不到哪些範圍。範例是一個短網址服務：入口 Nginx、以 Go 與 Laravel 實作同一組 API 的兩個後端、前台與後台兩個前端網頁、PostgreSQL 與 Valkey。各元件在 compose 裡的實際設定（掛載、旗標、讀取設定與 Grafana 佈建）見 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/)；本篇不涵蓋 Kubernetes 上的做法（Prometheus Operator、ServiceMonitor），Kubernetes 上的做法見 [在 Kubernetes 上接上監控](/backend/04-observability/vendors/prometheus/kubernetes-monitoring-entry/)。

文中的實測在 macOS 的 OrbStack 2.2.3（Docker 29.4.0）上進行，cAdvisor 是 v0.55.1、node_exporter 是 1.12.1、Prometheus 是 3.15.0。實測的那幾天 Mac 上另有與這個服務無關的程式長時間佔用 CPU，所以下文的數字多半量在主機過載的時候，判讀各段時會說明這一點。

## 健康檢查之外的兩個問題：流量與資源

健康檢查回答的是「服務活著嗎」：容器的 healthcheck 確認自己的端點回得了話，外部探測（例如 Gatus、Blackbox exporter）確認從外面打得通。服務活著而變慢、或者某一層快滿了，健康檢查都照樣回報正常，因為它問的不是這兩件事。

**流量監控**問的是每一個服務收到多少請求、多少失敗、花了多久，業界的整理方式是 [RED Method](/backend/knowledge-cards/red-method/)：Rate（每秒請求數）、Errors（錯誤率）、Duration（延遲的分布）。**資源監控**問的是每一種資源用了多少、有沒有開始排隊，整理方式是 [USE Method](/backend/knowledge-cards/use-method/)：Utilization（使用率）、Saturation（排隊的程度，例如等 CPU 的行程數、等連線的請求數）、Errors。兩者要一起看：延遲升高（RED）時，第一個開始排隊的資源（USE）就是瓶頸所在；資源用量升高而延遲不變，代表還有餘裕。

## 各層的訊號從哪裡來

一個請求從入口走到資料庫，每一層只看得到請求經過它的那一段。下表列出每一層看得到什麼、Prometheus 生態裡常用的收集方式，以及那一層結構上看不到的資訊。收集方式欄的 **exporter** 是把某個系統的狀態轉成 Prometheus 指標格式、開一個 HTTP 端點讓 Prometheus 定期來讀取（scrape）的程式（見 [Prometheus Exporter](/backend/knowledge-cards/prometheus-exporter/)）。

| 層           | 看得到                                                                                                           | 收集方式                                                                            | 看不到                                                                                                                                             |
| ------------ | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| 入口 Nginx   | 全部進來的請求，含沒進到後端就被擋下或回錯的；依網域、狀態碼、轉給哪個上游（upstream，Nginx 轉送請求的後端）分開 | access log 送進 log 系統再計數；連線數由 `stub_status` 加 nginx-prometheus-exporter | 請求在後端內部的時間花在哪一段                                                                                                                     |
| 應用程式     | 依路由的延遲、快取命中、業務事件                                                                                 | 程式用 client library 自己開 `/metrics`                                             | 程式還沒收到的請求、程式所在的容器用完 CPU 配額而被暫停                                                                                            |
| 容器         | 每個容器的 CPU、記憶體、網路、磁碟讀寫，以及用完 CPU 配額而被暫停的時間                                          | cAdvisor 讀 [cgroup](/backend/knowledge-cards/cgroup/)                              | 容器裡是哪個行程、哪個查詢在用資源                                                                                                                 |
| 主機或虛擬機 | 整台的 CPU、記憶體、load average、磁碟空間與讀寫                                                                 | node_exporter 讀 `/proc`、`/sys` 與掛載點                                           | 它自己所在那一層以外的機器，見〈監控所在層看不到的範圍：虛擬機與主機〉；裝在 compose 的網路裡時，它看到的網路是自己容器的，主機的網路改看 cAdvisor |
| 服務內部     | PostgreSQL 的連線數、鎖、慢查詢；Valkey 的記憶體、命中率、被淘汰的鍵                                             | postgres_exporter、redis_exporter（也支援 Valkey）                                  | 應用程式那一端排隊等連線的請求                                                                                                                     |
| 外部探測     | 從外面打不打得通、花多久                                                                                         | Blackbox exporter 或 Gatus 的指標                                                   | 真實使用者的流量                                                                                                                                   |

node_exporter 以容器跑在 compose 的網路裡時，它讀的 `/proc/net` 是自己這個容器的網路命名空間，所以 netdev、netstat、sockstat 這幾個 collector 回報的是容器自己的網路。要看主機的網路，讓它以 `network_mode: host` 執行，或關掉這幾個 collector、改看 cAdvisor 的各容器網路指標。

表中的外部探測跑在同一台主機上時，主機整台停掉或使用者到主機的路徑中斷，它跟著停或照樣成功；探測端放在主機的失效域以外的做法見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)。

入口與應用程式兩層都在量流量，兩者的差別是有用的訊號：入口的請求數多於後端收到的數量，差額是被入口擋下、被速率限制擋掉或在後端之前就失敗的請求。主機、容器與服務內部三層都在量資源，粒度由粗到細：主機的 CPU 滿了，容器那一層分得出是哪個服務，服務內部那一層分得出是哪一類工作（例如 PostgreSQL 的連線全被某種查詢佔住）。

## 工具的選項：Prometheus 加 exporter、單一 agent、開箱即用、臨時查看

| 做法                                           | 代表工具                               | 留下什麼                                                       |
| ---------------------------------------------- | -------------------------------------- | -------------------------------------------------------------- |
| Prometheus 加各層的 exporter，儀表板用 Grafana | 各層訊號表裡列的 exporter              | 每一層的時間序列，同一個查詢語言（PromQL）、同一份儀表板       |
| 一個 agent 收全部                              | Grafana Alloy、OpenTelemetry Collector | 每一層的時間序列與同一份儀表板，加上 log 與 trace 走同一條管線 |
| 開箱即用的主機監控                             | Netdata、Beszel                        | 自帶儀表板的即時與短期歷史                                     |
| 臨時查看                                       | `docker stats`、ctop、lazydocker       | 當下那一刻的數字                                               |

**Prometheus 加 exporter** 與**單一 agent** 都把數字存成同一種時間序列、用同一個查詢語言，要拿監控數字做判斷（壓測時找瓶頸在哪一層、把應用程式的指標和資源用量放在同一份儀表板對照、保留歷史比較改動前後）兩者都做得到；分開它們的是之後要不要也收 log 與 trace，以及團隊熟悉哪一套。每個 exporter 只做一件事、各自有文件，出問題時容易定位是哪一層沒收到；代價是 compose 多出七、八個容器（各層的 exporter 加上 Prometheus、Grafana 與 Alertmanager，這個短網址服務以 `container_memory_working_set_bytes` 加總，約 600 MB 記憶體；自己的環境接上之後用同一個查詢量），儀表板要自己組或匯入社群的；畫面這一層為什麼通常用 Grafana、告警規則放在 Prometheus 還是 Grafana，見 [Prometheus 指標的視覺化工具](/backend/04-observability/vendors/prometheus/visualization-tool-selection/)。

單一 agent 把多個 exporter 的工作收進一個行程，之後要收 log 與 [trace](/backend/knowledge-cards/trace/) 時不必再加一套管線（見 [4.11 Telemetry Pipeline 架構](/backend/04-observability/telemetry-pipeline/)）。設定比單一用途的 exporter 抽象，只收指標時多付了這份複雜度。

**開箱即用的工具** 裝上就看得到每個容器與主機的即時狀況，適合只想知道「現在誰在吃資源」。它們的資料和應用程式的指標不在同一個系統裡，壓測紀錄要另外抄數字。

**臨時查看的指令** 沒有歷史，而且只取一個瞬間，判讀上的限制見〈單次取樣與時間窗〉。

## 單次取樣與時間窗：`docker stats` 的瞬間值與 `rate()` 的平均速率

`docker stats --no-stream` 回報的 CPU 百分比，是 Docker 對 cgroup 前後兩次取樣之間的短暫區間算出來的。同一個 Valkey 容器在幾秒內連續取樣八次，結果是 1.41%、0.25%、27.40%、8.26%、1.95%、0.77%、10.87%、0.12%。看到一次 27% 或一次 110%（超過 100% 代表那一刻用了不只一顆核心），不能推論那個服務一直很忙。

cAdvisor 輸出的是累計值：`container_cpu_usage_seconds_total` 是這個容器啟動以來用掉的 CPU 秒數，只增不減。Prometheus 每次讀取都記下當時的累計值，查詢時用 `rate()` 在一段時間窗內算平均速率（`rate()` 如何處理計數器歸零，見 [PromQL 與 Recording Rules 實務](/backend/04-observability/vendors/prometheus/promql-recording-rules/)）：

```promql
# 每個 compose 服務在最近 5 分鐘平均用掉幾顆 CPU（1 代表一整顆核心）
sum by (container_label_com_docker_compose_service) (
  rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service!=""}[5m])
)
```

時間窗的長度決定看到什麼：`rate()` 取 5 分鐘的窗時，短暫的尖峰被平均掉，適合看持續的用量；要看尖峰，改用較短的窗，再用子查詢取一段時間內的最大值，例如 `max_over_time(rate(...[1m])[1h:])`。窗至少要涵蓋 Prometheus 的兩次讀取才算得出速率，常見的做法是取讀取間隔（scrape interval）的四倍以上（間隔 15 秒時取 1 分鐘），漏掉一次讀取也還算得出來。所以窗長沒有通用的值，它由要回答的問題決定：問平常用多少取長窗，問最高到多少取短窗加子查詢。

## Docker 跑在虛擬機裡時 cAdvisor 缺容器名稱：containerd socket 的位置

指標裡只有 `id` 而沒有 `name` 與 compose 標籤時，不論 Docker 跑在哪裡，成因都在 cAdvisor 日誌裡 `Registration of the docker container factory` 那一行：註冊失敗時它寫出找不到的 socket 路徑。cAdvisor 從 cgroup（Linux 核心替每個容器記帳與設限的機制）讀資源用量，cgroup 只認得一個 id；要知道 id 對應哪個容器、容器帶哪些標籤，cAdvisor 要連上容器執行環境的 socket 去問。照官方說明的掛載方式在 OrbStack 上執行時，指標裡只有 `id="/docker/<64 碼雜湊>"`，沒有 `name` 與 compose 服務的標籤，日誌寫著：

```text
Registration of the docker container factory failed: unable to create containerd client:
containerd: cannot unix dial containerd api service: dial unix /run/containerd/containerd.sock: connect: no such file or directory
```

cAdvisor 預設到 `/run/containerd/containerd.sock` 找 containerd，而 OrbStack 的 Docker 把它自己的 containerd socket 放在別的位置。socket 的實際位置可以從虛擬機的 `/var/run` 裡找：下面的指令把它唯讀掛進一個暫時的容器，再用 `find` 列出名稱符合的 socket。

```sh
docker run --rm -v /var/run:/host-run:ro alpine find /host-run -name 'containerd*.sock'
```

在這次測試的 OrbStack 上，指令列出 `/host-run/docker/containerd/containerd.sock` 與 `containerd-debug.sock` 兩個檔案：後者是除錯用的，取前者，並把前綴 `/host-run` 換回 `/var/run`，得到 `/var/run/docker/containerd/containerd.sock`（cAdvisor 本身以 `/var/run:/var/run` 掛載時，容器裡的路徑才和這個路徑相同）。以 `--containerd=<換回前綴的路徑>` 啟動 cAdvisor 之後，日誌改成 `Registration of the docker container factory successfully`，每個容器都帶上了 `name` 與 `container_label_com_docker_compose_service`，〈單次取樣與時間窗〉那段依服務分組的查詢才有結果。其他把 Docker 跑在虛擬機裡的環境（Docker Desktop、Colima）socket 的位置各自不同，本篇沒有實測；同一個方法找到的若是空的，先確認 `-v /var/run` 掛到的是虛擬機那一層，而不是主機分享進來的目錄。

cAdvisor 缺標籤是 exporter 常見的一種失效：exporter 起來了、Prometheus 讀得到、指標也有數字，缺的是分辨數字屬於哪個容器的標籤。所以監控接上之後，驗收不只看讀取成功（Prometheus 的 `up` 是 1），還要看每一個預期的服務都出現在指標的標籤裡。同一類「讀得到而數字是錯的」還有幾種：exporter 連不上它監控的服務而 `up` 照樣是 1、部分 collector 失敗，以及容器停掉之後 cAdvisor 的序列維持在停掉前的值，見〈監控來源接上之後仍沒在監控的情形與驗收〉與〈偵測容器停止〉。

## 監控所在層看不到的範圍：虛擬機與主機

macOS 上的 Docker 跑在一台 Linux 虛擬機裡，容器與裝在 compose 裡的 node_exporter 都在這台虛擬機裡。**load average** 是一段時間內處於可執行狀態（在跑或在等 CPU）的平均行程數，Linux 另外把等待磁碟讀寫的行程也算進去；大於核心數代表有行程在排隊。node_exporter 回報的是虛擬機，同一個時間點和 Mac 本機對照：

| 項目                   | node_exporter（虛擬機） | Mac 本機       |
| ---------------------- | ----------------------- | -------------- |
| load average（1 分鐘） | 2.89（8 顆核心）        | 55（8 顆核心） |
| 記憶體                 | 8.4 GB                  | 16 GB          |

這台 Mac 有 8 顆核心，load 55 代表嚴重排隊（[load average](/backend/knowledge-cards/load-average/) 的讀法），而虛擬機裡只看到 2.89：排隊的是 Mac 上的其他程式，虛擬機只是分到的 CPU 時間變少。容器裡的工作因此全面變慢，而虛擬機與容器的監控都顯示用量很低，從它們的數字找不到原因。

這個落差在那段過載期間持續存在：30 分鐘內虛擬機的 load 除以核心數在 0.33 到 1.28 之間，Mac 在 55 到 78 之間（見 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)）。

### 磁碟：Docker 資料的映像檔與主機本機的磁碟

磁碟的可見範圍與 CPU 不同：虛擬機裡看得到兩顆磁碟，要分清楚是哪一顆。

- **虛擬機放 Docker 資料的磁碟**（OrbStack 上是 `device="/dev/vdb1"`，掛在 `/var/lib/docker`）：它是存在 Mac 磁碟上的一個映像檔，用到才佔用 Mac 的空間。實測它回報可用 34.6 GB 時，Mac 實際只剩 15 GB；後來另一個時間點它剩 48.9%，Mac 剩 2.4%。
- **Mac 本機的磁碟**：OrbStack 用 virtiofs 把 Mac 的 `/Users`、`/private` 等目錄掛進虛擬機，node_exporter 以 `device="mac"`、`fstype="virtiofs"` 回報它。這一顆的剩餘比例和 Mac 上的 `df` 一致，位元組數則放大 256 倍（460 GiB 的 Mac 磁碟顯示成 126 TB）：OrbStack 2.2.3 回報的區塊數以 4 KiB 計，區塊大小欄位（`statfs` 的 `f_bsize`）卻填 1 MiB，node_exporter 把兩者相乘算位元組；`df` 用的是另一個欄位 `f_frsize`（4 KiB），所以它算得對。大小與可用量放大同樣的倍數，比例不受影響，所以這一顆在告警與儀表板上都只用剩餘比例。

只看 Docker 那一顆會以為空間充足。Mac 的磁碟寫滿時，虛擬機（連同裡面全部的容器）會被停掉（實測時 Mac 剩不到 1 GB，大量寫入 PostgreSQL 的過程中連續發生三次）。所以磁碟的告警要依裝置分組、兩顆都涵蓋（同一顆磁碟常掛在好幾個掛載點，不分組時一顆磁碟會發好幾則告警）：

```promql
# 每一顆磁碟的剩餘比例，低於範例門檻 10% 時成立
min by (device, fstype) (
  node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs|vfat"}
  / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs|vfat"}
) < 0.10
```

被排除的 fstype 是記憶體檔案系統（tmpfs）、容器的疊加層（overlay）、唯讀映像（squashfs）與 EFI 分割區（vfat），它們的空間不是要告警的對象；`0.10` 是範例門檻，實際的值依磁碟的增長速度與清出空間要花的時間來定。寫成告警規則時加上持續條件（例如 `for: 10m`），暫存檔造成的短暫低點才不會發告警。剩餘比例之外還有兩種寫法：inode 用完時空間還在而檔案寫不進去，看 `node_filesystem_files_free`；依增長速度預告，`predict_linear(node_filesystem_avail_bytes[6h], 24*3600) < 0` 代表照過去 6 小時的速度，一天內會寫滿。換一個環境時，先查 `count by (device, fstype) (node_filesystem_size_bytes)` 列出各顆，再決定排除哪些；其他把 Docker 跑在虛擬機裡的環境不一定把主機的目錄掛進來：拿列表裡各顆的大小和主機上 `df` 的大小比，一致的那一顆是主機的磁碟，差一個固定倍數的（OrbStack 的 virtiofs 差 256 倍）也是，那一顆只用比例。雲端主機上 node_exporter 看到的就是主機本身的磁碟，ext4、xfs 的 `f_bsize` 與 `f_frsize` 相等，位元組與比例都和 `df` 一致。

所以監控的範圍由它裝在哪一層決定：

- **Linux 主機直接跑 Docker**：node_exporter 看到的就是真正的主機，上表的落差不存在。
- **macOS 或 Windows 上的 Docker**：主機的 CPU 負載只量得到主機那一端，node_exporter 有 macOS 的版本可以裝在 Mac 本機（本篇沒有實測）；磁碟看虛擬機有沒有掛進主機的那一顆。在這種環境量到的數字為什麼要附上主機的負載，見 [共用主機的資源競爭](/operations/05-capacity-planning/shared-host-contention/)〈容量估算〉。
- **雲端的虛擬機**：同一個問題換成「同一台實體機上的其他租戶」。Linux 的 [steal 時間](/backend/knowledge-cards/cpu-steal-time/)（`node_cpu_seconds_total{mode="steal"}`）累計虛擬機想用 CPU 而被虛擬化層（hypervisor）分給別人的時間；它只增不減，所以看 `rate(node_cpu_seconds_total{mode="steal"}[5m])` 換算出的比例，這個比例持續高於平常時，慢的原因在虛擬機之外。

## 監控來源接上之後仍沒在監控的情形與驗收

資源層（cAdvisor、node_exporter、資料庫與快取的 exporter）不依賴任何應用程式碼，接上就有數字；應用程式的指標要先在兩個後端之間定好名稱與標籤，同一份儀表板才能並排比較它們，所以兩層準備好的時間點不同，資源層通常先接上。

一個來源接上之後，還可能在下面幾個位置沒有在監控，它們在平常都看起來正常，只有出事時才被讀到。這一類檢查監控系統本身的工作，業界稱 meta-monitoring：

- **該讀的對象根本沒寫進讀取設定**：沒有 `up` 序列，「每個 job 的 `up` 都是 1」照樣成立；要拿預期的對象清單（例如 `docker compose config --services`）對照 `up` 的 job 清單。

- **讀得到 exporter，而 exporter 連不上它監控的服務**：Prometheus 的 `up` 只代表 Prometheus 連得到 exporter，postgres_exporter 連不上 PostgreSQL 時 `up` 照樣是 1；exporter 自己輸出的連線狀態（`pg_up`、`redis_up`、`nginx_up`）才是 0。
- **讀得到而缺分辨對象的標籤**：前面 cAdvisor 的例子。`count by (container_label_com_docker_compose_service) (container_memory_working_set_bytes)` 列出實際有哪些服務，一個服務一列；另有一列不帶服務標籤，是 root cgroup 與 compose 以外的容器。
- **讀得到，而部分 collector 失敗**：node_exporter 有一部分 collector 在某些環境讀不到資料，`up` 照樣是 1；`node_scrape_collector_success == 0` 列出失敗的那幾個。OrbStack 上列出 18 個，多數是這台機器本來就沒有的硬體或檔案系統（zfs、infiniband、nvme），要看的是預期會有資料的那幾個：這裡的 pressure（PSI）也在失敗之列，所以這個環境用不了 PSI。
- **讀得到也有標籤，而數字對狀況沒有反應**：只有刻意製造一次它該看到的狀況（[故障注入](/backend/knowledge-cards/chaos-test/)）才看得出來。告警規則引用了不存在的指標時運算結果是空的、規則永遠不成立，`promtool` 照樣檢查通過，所以告警規則也要用故障注入確認會成立。

同一個短網址服務第一次接上時，刻意製造狀況的實測（`pg_sleep` 的 90 秒要長過查詢的 1 分鐘時間窗加一個讀取間隔）：

| 製造的狀況                            | 看哪個指標                               | 結果                 |
| ------------------------------------- | ---------------------------------------- | -------------------- |
| 在 Valkey 的容器裡跑一個空轉的迴圈    | 該服務的 CPU（1 分鐘平均）               | 0.98 顆核心          |
| 開 5 個連線各自 `select pg_sleep(90)` | `pg_stat_activity_count{state="active"}` | 5                    |
| 停掉前台的容器                        | Gatus 對前台的探測                       | 0（失敗）            |
| 停掉前台的容器                        | cAdvisor 裡那個容器的序列                | **3 分鐘後仍然存在** |

## 偵測容器停止：cAdvisor 保留的序列與 `container_last_seen`

停掉前台容器的那一次實測裡，cAdvisor 的序列是要特別記下的行為：容器停掉之後，cAdvisor 繼續輸出它最後的 CPU 與記憶體數值，依服務分組的圖上那條線維持在停掉前的值，看起來像服務還在。停止前進的是 `container_last_seen`（這個容器最後一次被看到的時間），所以偵測容器停了要看 `time() - container_last_seen` 有沒有持續增加；告警寫成「序列消失」的話永遠不會響。寫成告警時依服務取最小值：

```promql
# 一個 compose 服務的所有容器都超過 60 秒沒被看到，才算這個服務停了
min by (container_label_com_docker_compose_service) (
  time() - container_last_seen{container_label_com_docker_compose_service!=""}
) > 60
```

`60` 秒是讀取間隔 15 秒的四倍，讀取間隔改了跟著改。用最大值會在重建容器時誤報：服務重建之後，cAdvisor 同時留著舊容器與新容器兩條序列，舊的那條停止前進。實測強制重建一個容器 150 秒後，最大值是 161 秒、最小值是 10 秒。

這條規則看不到沒有序列的服務：服務從來沒起來過、或已經被 `docker compose down` 移除時，cAdvisor 沒有它的序列，差值無從算起。要涵蓋這兩種，拿預期的服務清單對照，或對每個服務寫 `absent()`；cAdvisor 會把已停止容器的序列保留多久本篇沒有量（實測三分鐘後仍在），長時間的停機以外部探測為準。

## 延伸閱讀：指標的設計、儀表板與告警、監控自己的失效

- 指標的型別（counter、gauge、histogram）與 [SLI / SLO](/backend/knowledge-cards/sli-slo/) 的量法，見 [4.2 metrics 與 SLI/SLO](/backend/04-observability/metrics-basics/)。
- 儀表板要放哪些圖、告警的門檻怎麼定，見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)。
- 本篇的查詢只依 compose 服務分組，標籤值只有十幾個；改成依請求路徑或使用者分組時，時間序列與 Prometheus 的記憶體一起膨脹，上限怎麼估、怎麼收斂在 [4.7 Cardinality 治理與成本邊界](/backend/04-observability/cardinality-cost-governance/)。
- 監控跟著它監控的系統一起失效（同一台主機、同一個磁碟），見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)，它在單機上的形態見 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)。本篇的虛擬機盲區是另一回事：監控本身沒有失效，只是看不到它所在層以外的範圍。
