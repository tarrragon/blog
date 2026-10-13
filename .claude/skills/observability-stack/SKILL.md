---
name: observability-stack
description: "自架指標監控（Prometheus、exporter、Grafana、Alertmanager）的設計、實作與驗收：依層盤點訊號、監控所在層的盲區、各層 exporter 的接法、三項驗收與故障注入、告警（可用與延遲分開、依原因抑制、偵測容器停止）。Triggers: 監控, Prometheus, exporter, Grafana, cAdvisor, node_exporter, Alertmanager, 告警, 抑制, 故障注入"
metadata:
  portable: true
  version: 1.8.0
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
| 決定監控的位置 | 對照〈監控所在層的盲區〉寫下監控跑在哪一層；選一個跑在被監控範圍之外的訊號，寫明它跑在哪台機器或哪個外部服務（和被監控的主機相同的不算；叢集時要在叢集之外）；估算監控元件自己的記憶體與 CPU（還沒接上時看各元件文件的建議值，接上之後用 `sum(container_memory_working_set_bytes{...})` 量），加上各服務的尖峰之後主機仍放得下，放不下就把 Prometheus 這類元件移到主機外 | 盤點表下方三項：監控跑在哪一層、主機外的訊號跑在哪裡、監控自己的資源估算 | 本檔〈監控所在層的盲區〉 |
| 實作 | 固定版本；exporter 連資料庫等服務用最小權限的專用帳號；Prometheus 設定（讀取對象、`rule_files`、`alerting.alertmanagers`）與 Grafana 的資料來源、儀表板以檔案進 repo；環境相依的值用環境變數，並寫下換到新環境時這個值要去哪裡查 | compose（或部署設定）、Prometheus 設定、儀表板檔、README | `references/layer-signals.md` |
| 驗收 | 先跑〈量測前的主機檢查〉，再對每個來源跑讀得到、有標籤、會反應三項驗收，會反應以故障注入驗 | 驗收紀錄：每一項的比較基準與出處、實測值，以及「未驗」清單 | `references/verification.md` |
| 告警 | 來源失效、主機外訊號的通知與 Watchdog 一定做；其餘依服務需要。可用性與延遲分開、間歇的條件先聚合、依原因抑制並寫下盲區、偵測容器停止 | 告警規則與抑制規則，以工具檢查語法並以故障注入確認會成立；選擇不做的告警寫進驗收紀錄的「未驗」，附理由與服務掛掉時由誰怎麼發現 | 本檔〈告警〉 |

一個來源要三項驗收都通過才算接上。只完成一部分的監控在平常看起來都是正常的：有的讀得到而標籤是空的，有的有標籤而數字不會動，要到出事時才發現。

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
- **虛擬機裡看到的磁碟要分清是哪一顆**：虛擬機放 Docker 資料的磁碟是主機上的映像檔，回報的可用空間可以比主機實際剩下的多（OrbStack 上實測主機磁碟寫滿時虛擬機被停掉，其他環境沒有實測）。有些環境（OrbStack）另外把主機的目錄掛進虛擬機：在 Prometheus 查 `count by (device, fstype) (node_filesystem_size_bytes)` 列出各顆，對照主機上 `df -h` 的大小，一致或差一個固定倍數的那一顆是主機的磁碟，就讓磁碟告警涵蓋它；差倍數的那一顆位元組不可信、只用剩餘比例（OrbStack 2.2.3 的 virtiofs 區塊大小欄位填 1 MiB 而區塊數以 4 KiB 計，node_exporter 算出的位元組放大 256 倍）（規則見 `references/layer-signals.md` 的磁碟一則）。
- **監控與被監控的服務共用主機時一起退化**：探測與 Prometheus 自己也在等 CPU，探測量到的延遲包含它們自己的等待；Prometheus 讀取 exporter 的耗時逼近 `scrape_timeout` 時讀取失敗、資料出現空洞；資源耗盡時一起停。所以主機外的訊號那一項要填一個不在這台主機上跑的訊號，通常是外部探測：另一台機器或外部的 uptime 服務定時打服務的健康端點。Prometheus 整個停掉時它自己發不出告警，所以加一條永遠成立的告警規則（Watchdog，`expr: vector(1)`），Alertmanager 經由一條專用的 route 把它持續送到外部服務，外部服務在心跳中斷時通知（dead man's switch）。這條 route 的 `repeat_interval`（預設 4 小時）會被往上取到 `group_interval`（預設 5 分鐘）的倍數，所以兩個都設短於外部服務的心跳期限（例如 `group_interval: 30s`、`repeat_interval: 1m`，對 5 分鐘的心跳期限），`group_wait` 設 0，`group_by` 只放 `alertname`。

## 量測前的主機檢查

故障注入、大量資料、壓測或效能比較之前與期間，在主機本身（不是 Docker 的虛擬機裡）看 load、核心數、記憶體與磁碟：macOS 跑 `uptime`、`sysctl -n hw.ncpu`、`sysctl vm.swapusage`、`df -h`，Linux 跑 `uptime`、`nproc`、`free -h`、`df -h`；load 高而 CPU 使用率不高時多半是記憶體不夠在換頁（swap 接近用滿），這時虛擬機裡的元件逾時與重啟都是它的連帶症狀，量到的數字不能拿來比較；Windows 沒有 load，看 CPU 使用率（`(Get-CimInstance Win32_Processor).LoadPercentage`，不受系統語言影響）與磁碟（`Get-PSDrive C`）。量測期間持續記錄（例如每分鐘一次），不只在開始前看一次；壓測工具跑在同一台主機時，它用的 CPU 也從服務那一份扣掉。

紀錄寫在哪台機器上跑了哪個指令、load 除以核心數、磁碟使用率，以及門檻和它的出處（使用者給的值與原話）。使用者沒給門檻時不自訂，照樣量，紀錄標「主機狀態未經門檻判定」，這次的數字不拿去和其他時間的比較。

## 告警

- **可用性與延遲分成兩個判斷**：可用性探測的條件只放回應碼，以及 TCP 連不連得上。延遲有兩個來源：應用程式在 `/metrics` 輸出的延遲分布（histogram，例如 `rate(...[5m])` 上的 p95），量不到請求進到程式之前的排隊；以及時間窗內慢探測佔的比例（`avg_over_time((<探測耗時指標> > bool 0.5)[15m:<探測間隔>]) > 0.2`），從外面量、含排隊。探測 15 分鐘只有幾十個樣本，取分位數近於取最慢的幾次，所以看比例；讀取間隔不長於探測間隔。第三方應用程式沒有 histogram 時，延遲從入口的 access log 取。拿掉探測條件裡的回應時間之前，先有延遲的告警接手。兩者放在同一個探測裡時，主機過載讓服務變慢就被報成「掛了」。
- **條件持續才發，間歇的條件先聚合**：Prometheus 用 `for`，外部探測工具（Gatus、Uptime Kuma 這一類）用連續失敗次數（次數乘上探測間隔就是持續時間）；持續時間要長過短暫尖峰、短過使用者能忍受的時間，採用的值與依據（觀測到的尖峰長度、使用者給的容忍時間）寫進驗收紀錄。`for` 要求每次評估都成立，load、讀取耗時、讀取失敗這類間歇的條件要先在時間窗內取平均、最大值或比例再加 `for`，否則永遠不成立。恢復也要持續才算數時用 `keep_firing_for`。外部探測工具自己的通知不經過 Alertmanager，抑制與分組管不到它；主機外的探測用它自己的通知管道，主機內的告警一律經過 Alertmanager，同一件事不兩邊都設通知。
- **來源失效**：驗收之後才斷線的來源靠這幾條發現：讀取成功的比例 `avg_over_time(up[15m]) < 0.9 and up`（`and up` 讓讀取對象從清單拿掉之後不再成立，縮容時不殘留告警）、整台主機讀不到 `max_over_time(up{job="node"}[5m]) == 0`（嚴重度與服務停止相同：整台停掉時 cAdvisor 的序列過期，容器停止的規則不成立）、exporter 自己的連線狀態 `pg_up == 0 or redis_up == 0 or nginx_up == 0` 這一類、讀取逼近逾時 `max_over_time(scrape_duration_seconds[5m]) > 8`（`8` 是預設逾時 10 秒的八成，逾時改了跟著改）。
- **依原因抑制**：Alertmanager 的 `inhibit_rules` 讓「主機飽和」的告警成立時，壓下各服務的「變慢」告警。
  - **主機飽和的條件**：5 分鐘平均的 load 除以核心數（`avg_over_time(node_load1[5m])`，例如 `> 1.5`）**或** steal 的比例（例如 `> 0.1`），兩者用 `or` 寫進同一條規則；兩個門檻是起始值，拿主機平常的資料校正。只看 load 的規則在雲端虛擬機上看不到其他租戶。CPU throttling 不放進來，它的成因是容器自己的上限。
  - **盲區**：監控在虛擬機裡時，虛擬機外面（實體機或筆電）的競爭不會讓這條規則成立。規則照樣寫進設定；在驗收紀錄的「未驗」寫「主機飽和在本環境不會成立，抑制只以合成告警驗過；部署到實體主機或看得到 steal 的雲端虛擬機時壓滿全部核心驗一次」（例如 `stress-ng --cpu 0 --timeout 15m`，`--cpu 0` 代表每顆核心一個工作者）。
  - **嚴重度**：會通知值班的是可用性與以 SLO 推出的錯誤預算消耗速度；以固定門檻判斷的延遲列為 warning。抑制只用在 warning 症狀（`target_matchers` 加 `severity="warning"`）；會通知值班的症狀不抑制，因為抑制會把同時發生、與主機無關的故障一起藏掉，改用 `group_by` 依主機合併成一則通知（單機時 `[alertname]` 效果相同；代價是同一台主機上無關的告警也併進來）。
  - **觸發與恢復兩端對齊**：原因從條件成立到告警成立的時間（時間窗的延遲加上 `for`）不長於症狀，否則症狀的通知先送出；原因加 `keep_firing_for`，值不短於症狀規則的時間窗，否則主機恢復後原因先解除，症狀的通知在事故結束之後才送出。
  - **多台主機**：要有一個代表主機的標籤 `host`，它指**症狀發生的那台主機**，不是 exporter 所在的主機。`instance` 是讀取對象的位址，同一台主機上各 exporter 的值都不同，不能用。跑在被監控主機上的 exporter，`host` 寫在讀取設定裡每個讀取對象上（`static_configs` 或 `file_sd_configs` 清單的 `labels`），用雲端的服務發現時以 `relabel_configs` 從 `__meta_*` 標籤取；寫成整個 job 共用的常數（`replacement`）只在一個 job 只讀一台主機時成立；探測類（Gatus、Blackbox）的 `host` 填被探測的那個端點所在的主機，用 `metric_relabel_configs` 依端點決定；Pushgateway 由推送端帶 `host` 並設 `honor_labels: true`。寫法與 Kubernetes 上兩側都要接上節點標籤的做法見 `references/layer-signals.md`〈主機標籤〉。抑制規則寫 `equal: [host]`，症狀規則的聚合（例如 `sum by (host, service, le)`）也保留 `host`：

    ```yaml
    inhibit_rules:
      - source_matchers: [alertname="HostCpuSaturated"]
        target_matchers: [alertname=~"ProbeSlow|ServiceSlow|ScrapeNearTimeout", severity="warning"]
        equal: [host]
    ```

  - **只擋通知**：被抑制的告警在 Prometheus 的 `ALERTS` 序列與各服務的延遲資料裡照常留下。
- **偵測容器停止要看會停止前進的指標**：cAdvisor 在容器停掉之後仍輸出最後的值，所以「序列消失」當不了停掉的訊號。`container_last_seen` 是 cAdvisor 最後一次看到這個容器的時間戳，容器停掉之後不再更新。寫規則之前先在 Prometheus 查 `count by (name, container_label_com_docker_compose_service) (container_last_seen)`，看每個容器的序列帶哪些標籤、哪一個區分服務（compose 是 `container_label_com_docker_compose_service`；compose 以外的容器這一欄是空的）。規則先算每個容器的差值、再依服務取最小值：差值最小的是最近還被看到的那個容器，它還在就代表服務還在：

  ```promql
  min by (host, container_label_com_docker_compose_service) (
    time() - container_last_seen{container_label_com_docker_compose_service!=""}
  ) > 60   # 讀取間隔 15 秒的四倍，讀取間隔改了跟著改；host 讓同一個服務在不同主機上各自判斷
  ```

  服務重建之後，舊容器的序列還在而且停止前進：不聚合或取最大值，每次重建都會誤報。先對 `container_last_seen` 取最小值再相減也會誤報，因為最小的時間戳屬於最舊的那個容器。從沒起來或已被移除的服務沒有序列，這條看不到，拿預期的服務清單對照或寫 `absent()`。
- **檢查與確認的順序**：規則與抑制設定改完，先以 `promtool check rules`、`amtool check-config` 檢查語法，再重新載入（`references/layer-signals.md` 的重新載入一則），最後製造規則要偵測的狀況，確認告警實際成立、該被抑制的狀態是 `suppressed`（做法見 `references/verification.md` 的故障注入表）。

## 查詢的時間窗與 `up` 涵蓋的範圍

- **不拿單次取樣下結論**：`docker stats` 這類指令一次只取一個瞬間，同一個容器幾秒內可以從 0.1% 跳到 27%。名稱以 `_total` 結尾的指標是只增不減的累計值，用 `rate()` 在時間窗內算平均，窗取 Prometheus 讀取間隔（`scrape_interval`）的四倍以上，漏掉一次讀取也還算得出來；例如間隔 15 秒時 `rate(container_cpu_usage_seconds_total[1m])`。
- **`up` 只代表 Prometheus 連得到 exporter**：exporter 連不上它監控的服務時 `up` 照樣是 1，看 exporter 自己的連線狀態指標（`pg_up`、`redis_up`、`nginx_up` 這一類，連得上是 1）；部分 collector 失敗時 `up` 也是 1，看 `node_scrape_collector_success`。核心有提供 PSI 時（pressure collector 成功），`node_pressure_cpu_waiting_seconds_total` 與 io 那一組分得開 CPU 與磁碟的排隊。

---

版本紀錄在同目錄的 `CHANGELOG.md`。
