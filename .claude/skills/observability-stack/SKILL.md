---
name: observability-stack
description: "自架指標監控（Prometheus、exporter、Grafana、Alertmanager）的設計、實作與驗收：依層盤點訊號、監控所在層的盲區、各層 exporter 的接法、三項驗收與故障注入、告警（可用與延遲分開、依原因抑制、偵測容器停止）。Triggers: 監控, Prometheus, exporter, Grafana, cAdvisor, node_exporter, Alertmanager, 告警, 抑制, 故障注入"
metadata:
  portable: true
  version: 1.3.0
---

# Observability Stack

替一台主機（或一組主機）上的服務建立自架的指標監控：Prometheus 定期讀取（scrape）各層的 exporter，Grafana 畫儀表板，需要時加告警規則交給 Alertmanager。這支 skill 管的是**設計、實作與驗收**，從〈流程〉表的第一列開始做。不負責的事：

- 要不要自架、買 SaaS 還是自建、第一天最少要有哪些訊號：走 `saas-tech-selection` skill 的 observability 維度。
- 監控資料出來之後怎麼判讀一次壓測或事故：判讀是另一件任務，有真實資料時再做。
- log 與 trace 的管線。

## 流程

| 步驟 | 動作 | 產出 | 讀 |
| --- | --- | --- | --- |
| 盤點訊號 | 逐層列出看得到與看不到的資訊，對到收集方式 | 訊號盤點表，欄位：層｜回答的問題｜收集方式｜看不到 | 本檔〈盤點訊號〉，各層的值在 `references/layer-signals.md` |
| 決定監控的位置 | 對照〈監控所在層的盲區〉，寫下監控跑在哪一層、哪些範圍它看不到，選一個放在被監控的主機之外的訊號 | 盤點表下方兩項：監控跑在哪一層、主機外的訊號是哪一個 | 本檔〈監控所在層的盲區〉 |
| 實作 | 固定版本；exporter 連資料庫等服務用最小權限的專用帳號；Prometheus 設定（讀取對象、`rule_files`、`alerting.alertmanagers`）與 Grafana 的資料來源、儀表板以檔案進 repo；環境相依的值用環境變數，並寫下換到新環境時這個值要去哪裡查 | compose（或部署設定）、Prometheus 設定、儀表板檔、README | `references/layer-signals.md` |
| 驗收 | 每個來源跑讀得到、有標籤、會反應三項驗收，會反應以故障注入驗 | 驗收結果表（實測值） | `references/verification.md` |
| 告警（需要時） | 可用性與延遲分開、條件持續才發、依原因抑制並寫下抑制的盲區、偵測容器停止 | 告警規則與抑制規則，以工具檢查語法，再以 `references/verification.md` 的故障注入確認會成立 | 本檔〈告警〉 |

驗收沒跑完，這個來源就還沒接上：讀得到、標籤空的、數字不會動的監控，在平常看起來都是正常的。

## 盤點訊號：每一層各自只看得到一段

流量用 RED（請求數、錯誤率、延遲分布）看，資源用 USE（使用率、排隊程度、錯誤）看。每一層只看得到經過它的那一段：

| 層 | 回答的問題 | 典型的收集方式 | 看不到 |
| --- | --- | --- | --- |
| 入口（反向代理） | 進來多少、多少在後端之前就失敗 | 依狀態碼與上游的請求數從 access log 計數；連線數由代理開一個狀態頁（例如 Nginx 的 `stub_status`），再由一個 exporter 讀它、轉成指標。兩者收的東西不同：access log 給依狀態碼的請求數，狀態頁給連線數 | 後端內部的時間花在哪一段 |
| 應用程式 | 依路由的延遲、業務事件 | 程式用 client library 自己開 `/metrics` | 在應用程式之前就失敗的請求 |
| 容器 | 每個容器用多少、有沒有用完 CPU 配額而被暫停 | cAdvisor | 容器裡是哪個行程在用資源 |
| 主機 | 整台的 CPU、記憶體、load、磁碟 | node_exporter | 它所在那一層以外的機器的 CPU 負載 |
| 服務內部 | 資料庫與快取的連線、命中、鎖 | 各自的 exporter | 應用程式那一端排隊等連線的請求 |
| 外部探測 | 從外面打不打得通 | Blackbox exporter、Gatus 這類探測工具 | 真實使用者的流量 |

盤點表把入口與應用程式的請求數都列進去，兩者的差額才算得出入口擋下或後端之前就失敗的請求；主機、容器、服務內部三層都列，主機滿的時候才分得出是哪個服務、哪類工作。各層 exporter 的接法與實測遇到的問題見 `references/layer-signals.md`。

## 監控所在層的盲區

監控只看得到它所在的那一層。下面三種盲區，各寫一句進盤點表下方的兩項（監控跑在哪一層、主機外的訊號是哪一個）：

- **跑在虛擬機裡的監控看不到虛擬機以外的 CPU 競爭**：macOS、Windows 上的 Docker 跑在 Linux 虛擬機裡，node_exporter 與 cAdvisor 回報的是虛擬機。主機上其他程式吃滿 CPU 時，虛擬機的 load 很低而容器全面變慢，虛擬機裡沒有任何指標反映這個競爭（OrbStack 的 steal 序列存在、值恆為 0）。雲端虛擬機看 steal 時間（虛擬機想用 CPU 而虛擬化層分給別的虛擬機的時間），它是累計值，查 `avg by (instance) (rate(node_cpu_seconds_total{mode="steal"}[5m]))`。
- **虛擬機裡看到的磁碟要分清是哪一顆**：虛擬機放 Docker 資料的磁碟是主機上的映像檔，回報的可用空間可以比主機實際剩下的多（OrbStack 上實測主機磁碟寫滿時虛擬機被停掉，其他環境沒有實測）。有些環境（OrbStack）另外把主機的目錄掛進虛擬機：在 Prometheus 查 `count by (device, fstype) (node_filesystem_size_bytes)` 列出各顆，對照主機上 `df -h` 的大小，有一致的那一顆，就讓磁碟告警涵蓋它（告警規則見 `references/layer-signals.md` 的磁碟一則）。
- **監控與被監控的服務共用主機時一起退化**：探測與 Prometheus 自己也在等 CPU，探測量到的延遲包含它們自己的等待；Prometheus 讀取 exporter 的耗時逼近 `scrape_timeout` 時讀取失敗、資料出現空洞；資源耗盡時一起停。所以主機外的訊號那一項要填一個不在這台主機上跑的訊號，通常是外部探測：另一台機器或外部的 uptime 服務定時打服務的健康端點。同時監控 Prometheus 本身（`scrape_duration_seconds`、`up` 的空洞）；Prometheus 整個停掉時它自己發不出告警，所以加一條永遠成立的告警規則（Watchdog，`expr: vector(1)`），Alertmanager 經由一條專用的 route 把它持續送到外部服務，外部服務在心跳中斷時通知（dead man's switch）。

## 量測前的主機檢查

動手做大量資料、壓測或效能比較之前，在主機本身（不是 Docker 的虛擬機裡）看 load、核心數與磁碟：macOS 跑 `uptime`、`sysctl -n hw.ncpu`、`df -h`，Linux 跑 `uptime`、`nproc`、`df -h`；Windows 沒有 load，看 CPU 使用率（`Get-Counter '\Processor(_Total)\% Processor Time'`）。load 除以核心數或磁碟使用率超過使用者定的門檻就延後，採用的門檻與當時的值寫進量測紀錄。

## 告警

- **可用性與延遲分成兩個判斷**：可用性探測的條件只放回應碼，以及 TCP 連不連得上；延遲用應用程式自己在 `/metrics` 輸出的延遲分布（histogram）算一段時間的百分位數（例如 `rate(...[5m])` 上的 p95），不用單次探測的回應時間。兩者放在同一個探測裡時，主機過載讓服務變慢就被報成「掛了」。
- **條件持續才發**：Prometheus 用 `for`，外部探測工具（Gatus、Uptime Kuma 這一類）用連續失敗次數（次數乘上探測間隔就是持續時間）；持續時間要長過短暫尖峰、短過使用者能忍受的時間。
- **依原因抑制**：Alertmanager 的 `inhibit_rules` 讓「主機飽和」的告警成立時，壓下各服務的「變慢」告警。
  - **盲區**：「主機飽和」用監控所在那一層的指標算（node_exporter 的 load 除以核心數、steal 時間）。監控在虛擬機裡時算的是虛擬機，虛擬機外面（實體機或筆電）的競爭不會讓它成立，抑制也就不會發生。規則照樣寫進設定，部署到實體主機或看得到 steal 時間的雲端虛擬機時就會生效；在開發用的虛擬機上，主機的負載照〈量測前的主機檢查〉另外看。
  - **多台主機**：不加 `equal` 時，任何一台主機飽和都會壓下所有主機的症狀。抑制規則加 `equal: [instance]`（或自訂的主機標籤），症狀告警的聚合（例如 `sum by (service, le)`）也要保留同一個標籤：

    ```yaml
    inhibit_rules:
      - source_matchers: [alertname="HostCpuSaturated"]
        target_matchers: [alertname="ServiceSlow"]
        equal: [instance]
    ```

  - **嚴重度**：抑制來源的嚴重度不低於被壓下的症狀。症狀告警會通知值班人員時，「主機飽和」自己也要通知，否則使用者正在等的那段時間沒有人收到任何通知。
  - **只擋通知**：被抑制的告警在 Prometheus 的 `ALERTS` 序列與各服務的延遲資料裡照常留下。
- **偵測容器停止要看會停止前進的指標**：cAdvisor 在容器停掉之後仍輸出最後的值，所以「序列消失」當不了停掉的訊號。`container_last_seen` 是 cAdvisor 最後一次看到這個容器的時間戳，容器停掉之後不再更新。規則先算差值、再依服務取最小值：

  ```promql
  # 標籤名依部署方式而定，用 references/verification.md 的 count by 查實際的標籤名
  min by (container_label_com_docker_compose_service) (
    time() - container_last_seen{container_label_com_docker_compose_service!=""}
  ) > 60   # 讀取間隔 15 秒的四倍，讀取間隔改了跟著改
  ```

  服務重建之後，舊容器的序列還在而且停止前進：不聚合或取最大值，每次重建都會誤報；`min` 套在 `container_last_seen` 上（而不是差值上）等於取最大的差值，同樣誤報。
- **檢查與確認的順序**：規則與抑制設定改完，先以 `promtool check rules`、`amtool check-config` 檢查語法，再重新載入（`references/layer-signals.md` 的重新載入一則），最後製造規則要偵測的狀況，確認告警實際成立、該被抑制的狀態是 `suppressed`（做法見 `references/verification.md` 的故障注入表）。

## 查詢的時間窗與 `up` 涵蓋的範圍

- **不拿單次取樣下結論**：`docker stats` 這類指令一次只取一個瞬間，同一個容器幾秒內可以從 0.1% 跳到 27%。名稱以 `_total` 結尾的指標是只增不減的累計值，用 `rate()` 在時間窗內算平均，窗取 Prometheus 讀取間隔（`scrape_interval`）的四倍以上，漏掉一次讀取也還算得出來；例如間隔 15 秒時 `rate(container_cpu_usage_seconds_total[1m])`。
- **`up` 只代表 Prometheus 連得到 exporter**：exporter 連不上它監控的服務時 `up` 照樣是 1，看 exporter 自己的連線狀態指標（`pg_up`、`redis_up`、`nginx_up` 這一類，連得上是 1）。

---

版本紀錄在同目錄的 `CHANGELOG.md`。
