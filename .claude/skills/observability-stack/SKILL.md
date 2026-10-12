---
name: observability-stack
description: "自架指標監控（Prometheus、exporter、Grafana、Alertmanager）的設計、實作與驗收：依層盤點訊號、監控所在層的盲區、各層 exporter 的接法、三項驗收與故障注入、告警（可用與延遲分開、依原因抑制、偵測容器停止）。Triggers: 監控, Prometheus, exporter, Grafana, cAdvisor, node_exporter, Alertmanager, 告警, 抑制, 故障注入"
metadata:
  portable: true
  version: 1.4.0
---

# Observability Stack

替一台主機（或一組主機）上的服務建立自架的指標監控：Prometheus 定期讀取（scrape）各層的 exporter，Grafana 畫儀表板，告警規則交給 Alertmanager。這支 skill 管的是**設計、實作與驗收**，從〈流程〉表的第一列開始做。

適用範圍：以 Docker Compose 部署在一台或幾台主機上的服務。部署在 Kubernetes（用 kube-prometheus-stack 這類 operator）時，盤點、盲區、驗收與告警的原則照用，實作的位置不同，見 `references/layer-signals.md`〈部署在 Kubernetes 時〉。

不負責的事：

- 要不要自架、買 SaaS 還是自建、第一天最少要有哪些訊號：走 `saas-tech-selection` skill 的 observability 維度。
- 判讀一次壓測或事故的數字：另一件任務，有真實資料時再做。驗收時數字不符故障注入表「該看到」那一欄，不屬於判讀，屬於本 skill（見 `references/layer-signals.md`〈實測遇到的問題〉）。
- log 與 trace 的管線。

## 流程

| 步驟 | 動作 | 產出 | 讀 |
| --- | --- | --- | --- |
| 盤點元件與訊號 | 逐個元件寫下歸誰管（自己寫的程式、第三方軟體、編排平台、雲端受管服務），再逐層列出看得到與看不到的資訊、對到收集方式 | 訊號盤點表，欄位：層｜元件與歸誰管｜回答的問題｜收集方式｜看不到 | 本檔〈盤點訊號〉 |
| 決定監控的位置 | 對照〈監控所在層的盲區〉寫下監控跑在哪一層；選一個跑在被監控範圍之外的訊號，寫明它跑在哪台機器或哪個外部服務（和被監控的主機相同的不算；叢集時要在叢集之外）；估算監控元件自己的記憶體與 CPU，加上各服務的尖峰之後主機仍放得下，放不下就把 Prometheus 這類元件移到主機外 | 盤點表下方三項：監控跑在哪一層、主機外的訊號跑在哪裡、監控自己的資源估算 | 本檔〈監控所在層的盲區〉 |
| 實作 | 固定版本；exporter 連資料庫等服務用最小權限的專用帳號；Prometheus 設定（讀取對象、`rule_files`、`alerting.alertmanagers`）與 Grafana 的資料來源、儀表板以檔案進 repo；環境相依的值用環境變數，並寫下換到新環境時這個值要去哪裡查 | compose（或部署設定）、Prometheus 設定、儀表板檔、README | `references/layer-signals.md` |
| 驗收 | 先跑〈量測前的主機檢查〉，再對每個來源跑讀得到、有標籤、會反應三項驗收，會反應以故障注入驗 | 驗收紀錄：每一項的比較基準與出處、實測值，以及「未驗」清單 | `references/verification.md` |
| 告警 | 來源失效、主機外訊號的通知與 Watchdog 一定做；其餘依服務需要。可用性與延遲分開、間歇的條件先聚合、依原因抑制並寫下盲區、偵測容器停止 | 告警規則與抑制規則，以工具檢查語法並以故障注入確認會成立；選擇不做的告警寫進驗收紀錄的「未驗」，附理由與服務掛掉時由誰怎麼發現 | 本檔〈告警〉 |

驗收沒跑完，這個來源就還沒接上：讀得到、標籤空的、數字不會動的監控，在平常看起來都是正常的。

## 盤點訊號：每一層各自只看得到一段

流量用 RED（請求數、錯誤率、延遲分布）看，資源用 USE（使用率、排隊程度、錯誤）看。每一層只看得到經過它的那一段：

| 層 | 回答的問題 | 典型的收集方式 | 看不到 |
| --- | --- | --- | --- |
| 入口（反向代理） | 進來多少、多少在後端之前就失敗、各請求花多久 | access log 記下狀態碼、上游與回應時間（Nginx 的 `$request_time`），轉成指標；連線數由狀態頁（Nginx 的 `stub_status`）加一個 exporter 讀 | 後端內部的時間花在哪一段 |
| 應用程式 | 依路由的延遲、業務事件 | 自己寫的程式用 client library 開 `/metrics`；第三方軟體加不了時，延遲改從入口那一層取 | 請求進到程式之前排隊的時間 |
| 容器 | 每個容器用多少、有沒有用完 CPU 配額而被暫停 | cAdvisor | 容器裡是哪個行程在用資源 |
| 主機 | 整台的 CPU、記憶體、load、磁碟 | node_exporter | 它所在那一層以外的機器的 CPU 負載 |
| 服務內部 | 資料庫與快取的連線、命中、鎖 | 各自的 exporter | 應用程式那一端排隊等連線的請求 |
| 受管服務 | 雲端資料庫等的 CPU、IOPS、儲存 | 雲端供應商的監控，經它的 exporter 轉進 Prometheus | 連到它的應用程式那一端排隊的情形 |
| 外部探測 | 從外面打不打得通、花多久 | Blackbox exporter、Gatus 這類探測工具 | 真實使用者的流量 |

盤點表把入口與應用程式的請求數都列進去，兩者的差額才算得出入口擋下或後端之前就失敗的請求；主機、容器、服務內部三層都列，主機滿的時候才分得出是哪個服務、哪類工作。歸誰管決定訊號從哪裡來：第三方軟體沒有 `/metrics` 就從入口取延遲，編排平台的元件標籤由平台決定，受管服務的資源只在供應商那一側看得到。各層 exporter 的接法與實測遇到的問題見 `references/layer-signals.md`。

## 監控所在層的盲區

監控只看得到它所在的那一層。下面三種盲區，各寫一句進盤點表下方的「監控跑在哪一層」與「主機外的訊號跑在哪裡」：

- **跑在虛擬機裡的監控看不到虛擬機以外的 CPU 競爭從哪裡來**：macOS、Windows 上的 Docker 跑在 Linux 虛擬機裡，node_exporter 與 cAdvisor 回報的是虛擬機。主機上其他程式吃滿 CPU 時，虛擬機的 load 很低而容器全面變慢（OrbStack 的 steal 序列存在、值恆為 0）。虛擬機裡沒有指標直接指出這個原因；間接反映它的是 Prometheus 自己的讀取耗時（`scrape_duration_seconds`）與探測的回應時間，它們在各服務 CPU 用量都低時一起升高。雲端虛擬機看 steal 時間（虛擬機想用 CPU 而虛擬化層分給別的虛擬機的時間），它是累計值，查 `avg without (cpu, mode) (rate(node_cpu_seconds_total{mode="steal"}[5m]))`；先確認它不是恆為 0。
- **虛擬機裡看到的磁碟要分清是哪一顆**：虛擬機放 Docker 資料的磁碟是主機上的映像檔，回報的可用空間可以比主機實際剩下的多（OrbStack 上實測主機磁碟寫滿時虛擬機被停掉，其他環境沒有實測）。有些環境（OrbStack）另外把主機的目錄掛進虛擬機：在 Prometheus 查 `count by (device, fstype) (node_filesystem_size_bytes)` 列出各顆，對照主機上 `df -h` 的大小，有一致的那一顆，就讓磁碟告警涵蓋它（規則見 `references/layer-signals.md` 的磁碟一則）。
- **監控與被監控的服務共用主機時一起退化**：探測與 Prometheus 自己也在等 CPU，探測量到的延遲包含它們自己的等待；Prometheus 讀取 exporter 的耗時逼近 `scrape_timeout` 時讀取失敗、資料出現空洞；資源耗盡時一起停。所以主機外的訊號那一項要填一個不在這台主機上跑的訊號，通常是外部探測：另一台機器或外部的 uptime 服務定時打服務的健康端點。Prometheus 整個停掉時它自己發不出告警，所以加一條永遠成立的告警規則（Watchdog，`expr: vector(1)`），Alertmanager 經由一條專用的 route 把它持續送到外部服務，外部服務在心跳中斷時通知（dead man's switch）。這條 route 的 `repeat_interval`（預設 4 小時）設成短於外部服務的心跳期限（例如 1 分鐘對 5 分鐘），`group_wait` 設 0，`group_by` 只放 `alertname`。

## 量測前的主機檢查

故障注入、大量資料、壓測或效能比較之前與期間，在主機本身（不是 Docker 的虛擬機裡）看 load、核心數與磁碟：macOS 跑 `uptime`、`sysctl -n hw.ncpu`、`df -h`，Linux 跑 `uptime`、`nproc`、`df -h`；Windows 沒有 load，看 CPU 使用率（`Get-Counter '\Processor(_Total)\% Processor Time'`）與磁碟（`Get-PSDrive C`）。量測期間持續記錄（例如每分鐘一次），不只在開始前看一次；壓測工具跑在同一台主機時，它用的 CPU 也從服務那一份扣掉。

紀錄寫在哪台機器上跑了哪個指令、load 除以核心數、磁碟使用率，以及門檻和它的出處（使用者給的值與原話）。使用者沒給門檻時不自訂，照樣量，紀錄標「主機狀態未經門檻判定」，這次的數字不拿去和其他時間的比較。

## 告警

- **可用性與延遲分成兩個判斷**：可用性探測的條件只放回應碼，以及 TCP 連不連得上。延遲有兩個來源：應用程式在 `/metrics` 輸出的延遲分布（histogram，例如 `rate(...[5m])` 上的 p95），量不到請求進到程式之前的排隊；以及探測回應時間在時間窗內的分位數（`quantile_over_time(0.95, <探測耗時指標>[15m])`），從外面量、含排隊。第三方應用程式沒有 histogram 時，延遲從入口的 access log 取。拿掉探測條件裡的回應時間之前，先有延遲的告警接手。兩者放在同一個探測裡時，主機過載讓服務變慢就被報成「掛了」。
- **條件持續才發，間歇的條件先聚合**：Prometheus 用 `for`，外部探測工具（Gatus、Uptime Kuma 這一類）用連續失敗次數（次數乘上探測間隔就是持續時間）；持續時間要長過短暫尖峰、短過使用者能忍受的時間，採用的值與依據（觀測到的尖峰長度、使用者給的容忍時間）寫進驗收紀錄。`for` 要求每次評估都成立，讀取耗時、讀取失敗這類間歇的條件要先在時間窗內取最大值、比例或分位數再加 `for`，否則永遠不成立。
- **來源失效**：驗收之後才斷線的來源靠這幾條發現：讀取成功的比例 `avg_over_time(up[15m]) < 0.9`、exporter 自己的連線狀態 `pg_up == 0 or redis_up == 0 or nginx_up == 0` 這一類、讀取逼近逾時 `max_over_time(scrape_duration_seconds[5m]) > 8`（`8` 是預設逾時 10 秒的八成，逾時改了跟著改）。
- **依原因抑制**：Alertmanager 的 `inhibit_rules` 讓「主機飽和」的告警成立時，壓下各服務的「變慢」告警。
  - **主機飽和的條件**：load 除以核心數（例如 `> 1.5`）**或** steal 的比例（例如 `> 0.1`），兩者用 `or` 寫進同一條規則；只看 load 的規則在雲端虛擬機上看不到其他租戶。CPU throttling 不放進來，它的成因是容器自己的上限。
  - **盲區**：監控在虛擬機裡時，虛擬機外面（實體機或筆電）的競爭不會讓這條規則成立。規則照樣寫進設定；在驗收紀錄的「未驗」寫「主機飽和在本環境不會成立，抑制只以合成告警驗過；部署到實體主機或看得到 steal 的雲端虛擬機時壓滿全部核心驗一次」。
  - **嚴重度**：抑制只用在不通知值班的症狀（warning，例如 `target_matchers` 加 `severity="warning"`）；會通知值班的症狀不抑制，改用 `group_by` 依主機合併成一則通知。抑制會把同時發生、與主機無關的故障一起藏掉。原因規則的 `for` 不長於症狀規則的 `for`。
  - **多台主機**：要有一個代表主機的標籤。`instance` 是讀取對象的位址，同一台主機上各 exporter 的值都不同，不能用。在讀取設定以 `relabel_configs` 替同一台主機上的每個讀取對象加 `host` 標籤，抑制規則寫 `equal: [host]`，症狀規則的聚合（例如 `sum by (service, le)`）也保留 `host`；Kubernetes 上服務的序列帶的是 Pod 的位址，先接上節點的標籤（例如以 `kube_pod_info` 的 `node` 做 join）：

    ```yaml
    inhibit_rules:
      - source_matchers: [alertname="HostCpuSaturated"]
        target_matchers: [alertname=~"ServiceSlow|ScrapeNearTimeout", severity="warning"]
        equal: [host]
    ```

  - **只擋通知**：被抑制的告警在 Prometheus 的 `ALERTS` 序列與各服務的延遲資料裡照常留下。
- **偵測容器停止要看會停止前進的指標**：cAdvisor 在容器停掉之後仍輸出最後的值，所以「序列消失」當不了停掉的訊號。`container_last_seen` 是 cAdvisor 最後一次看到這個容器的時間戳，容器停掉之後不再更新。區分服務的標籤先查 `topk(1, container_last_seen)` 看序列帶哪些標籤（compose 是 `container_label_com_docker_compose_service`），規則先算差值、再依服務取最小值：

  ```promql
  min by (container_label_com_docker_compose_service) (
    time() - container_last_seen{container_label_com_docker_compose_service!=""}
  ) > 60   # 讀取間隔 15 秒的四倍，讀取間隔改了跟著改
  ```

  服務重建之後，舊容器的序列還在而且停止前進：不聚合或取最大值，每次重建都會誤報；`min` 套在 `container_last_seen` 上（而不是差值上）等於取最大的差值，同樣誤報。從沒起來或已被移除的服務沒有序列，這條看不到，拿預期的服務清單對照或寫 `absent()`。
- **檢查與確認的順序**：規則與抑制設定改完，先以 `promtool check rules`、`amtool check-config` 檢查語法，再重新載入（`references/layer-signals.md` 的重新載入一則），最後製造規則要偵測的狀況，確認告警實際成立、該被抑制的狀態是 `suppressed`（做法見 `references/verification.md` 的故障注入表）。

## 查詢的時間窗與 `up` 涵蓋的範圍

- **不拿單次取樣下結論**：`docker stats` 這類指令一次只取一個瞬間，同一個容器幾秒內可以從 0.1% 跳到 27%。名稱以 `_total` 結尾的指標是只增不減的累計值，用 `rate()` 在時間窗內算平均，窗取 Prometheus 讀取間隔（`scrape_interval`）的四倍以上，漏掉一次讀取也還算得出來；例如間隔 15 秒時 `rate(container_cpu_usage_seconds_total[1m])`。
- **`up` 只代表 Prometheus 連得到 exporter**：exporter 連不上它監控的服務時 `up` 照樣是 1，看 exporter 自己的連線狀態指標（`pg_up`、`redis_up`、`nginx_up` 這一類，連得上是 1）；部分 collector 失敗時 `up` 也是 1，看 `node_scrape_collector_success`。

---

版本紀錄在同目錄的 `CHANGELOG.md`。
