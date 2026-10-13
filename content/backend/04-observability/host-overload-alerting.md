---
title: "4.27 主機過載時的監控告警：可用與變慢分開判斷、依原因抑制、監控自身的等待"
date: 2026-10-12
description: "多個服務共用一台主機而主機過載時，各服務的探測與告警會一起失敗：可用性與延遲分成兩個判斷的寫法、間歇的條件怎麼持續成立、以主機飽和抑制各服務變慢的規則與它的取捨、以合成告警驗證抑制、抑制藏起各服務受影響程度的差別、探測與 Prometheus 自己也在等 CPU 時的訊號，以及讓監控不比服務先失效的資源隔離；以一次開發環境的過載為例"
weight: 27
tags: ["backend", "observability", "alerting", "prometheus", "monitoring"]
---

多個服務共用一台主機（或一台虛擬機）而主機本身過載時，各服務的探測與告警會一起報失敗；這篇整理這個情形下的告警寫法。共用主機在容量估算、故障範圍與隔離層級上各要考慮什麼，另見 [共用主機的資源競爭](/operations/05-capacity-planning/shared-host-contention/)。告警的一般機制（抑制、分組、條件持續才觸發、burn rate）在 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)，各層的指標從哪裡收見 [4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/)。

文中的數字來自一個短網址服務的開發環境：macOS 上的 OrbStack 2.2.3（在 Mac 上以一台 Linux 虛擬機跑 Docker 的工具）跑 Docker Compose，外部探測用 Gatus 5.37.0（定時打各服務端點、判斷成功與否的工具），指標與告警是 Prometheus 3.15.0 與 Alertmanager 0.34.1。下文的告警規則以 `promtool check rules` 檢查回報 SUCCESS，抑制規則補上 route 與 receivers 之後以 `amtool check-config` 檢查通過。

## 一次主機過載在各層留下的訊號

跑這個開發環境的 Mac 有 8 顆核心，佔用 CPU 的是 Mac 上與這個服務無關的其他程式；在 Mac 上隔幾分鐘跑一次 `uptime`，數小時內的 load average 都在 55 到 78 之間。[load average](/backend/knowledge-cards/load-average/) 是一段時間內在跑或在等 CPU 的平均行程數（Linux 另把等磁碟讀寫的行程也算進去），除以核心數大於 1 代表有行程在排隊，55 對 8 顆核心是每顆核心約 6.9 個可執行的行程，其中近 6 個在等。Docker 的虛擬機同樣分到 8 顆核心。同一段 30 分鐘的時間裡，各層的監控回報：

| 層                                                                                           | 回報                                                                                                    |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Gatus 對 Laravel 後端的探測（條件：回應碼 200 且回應時間低於 500 ms）                        | 達標 49%，最慢 6.0 秒，未達標的那幾次回應碼都是 200                                                     |
| Gatus 對 Go 後端的探測（同樣的條件）                                                         | 達標 92.5%，最慢 2.1 秒                                                                                 |
| Laravel 容器自己的 healthcheck（只看回應碼）                                                 | 一直是 healthy                                                                                          |
| 虛擬機裡的 node_exporter                                                                     | load 除以核心數在 0.33 到 1.28 之間（平均 0.69）                                                        |
| Prometheus 讀取（scrape）各 [exporter](/backend/knowledge-cards/prometheus-exporter/) 的耗時 | 依 job（同一種 exporter 的讀取對象）取的最大值 8.6 到 14.9 秒，預設逾時 10 秒；postgres 有 4 次讀取失敗 |

這張表裡每一個監控回報的都是事實：Laravel 對使用者來說確實變慢了，容器確實活著，虛擬機裡的 load 確實低於下文告警規則用的門檻 1.5。收到告警的人看到的是「Laravel 後端失敗」，而成因在 Mac 上，沒有一個訊號直接指向它。這個情境有三個要分開處理的問題：告警把「變慢」報成「失敗」、告警只報出各服務的症狀而沒有附上它們共同的原因、監控自己也在同一台過載的機器上。

## 可用性與延遲分成兩個判斷

Gatus 那條探測把兩個條件放在一起，任一個不成立就判失敗，所以「慢」和「掛了」在結果裡長得一樣。兩者的處置不同，所以要分成兩個判斷：

- **可用性**：連不連得上、回應碼對不對。不成立代表服務停止回應請求了，要有人立刻處理。
- **延遲**：一段時間內的整體表現（真實請求的[百分位數](/backend/knowledge-cards/percentile/)，例如 5 分鐘的 p95；或慢探測佔的比例），不看單次探測。延遲高代表使用者等得久，先查原因再決定動作。

外部探測一次只量一個請求，單次的回應時間雜訊很大：同一個 Go 後端在幾秒內的探測可以從 0.3 秒到 2 秒。延遲的訊號因此有兩個來源，各補對方看不到的地方：

- **後端自己輸出的請求延遲分布**（[histogram](/backend/knowledge-cards/histogram/)）：反映全部真實請求，依路由分得開；量不到請求進到程式之前在入口與 PHP-FPM 這類行程池排隊的時間，所以過載時會低報。應用程式是第三方軟體、加不了 client library 時，改從入口代理的 access log 取每個請求的回應時間（例如 Nginx 的 `$request_time`）。
- **一段時間窗內慢探測佔的比例**：單次探測的雜訊被稀釋成比例，而探測從外面打，排隊的時間也量得到；探測程式跑在被監控的主機之外時，它也是唯一不和服務一起過載的延遲訊號。探測每 30 秒一次，15 分鐘只有 30 個樣本，在這個樣本數下取 p95 近於取第二慢的那一次，所以看比例而不看分位數。

拆開之後，Gatus 的條件只剩回應碼：

```yaml
endpoints:
  # 可用性：只看回應碼，失敗代表服務沒有在回應請求
  - name: Laravel 後端
    group: 後端
    # 網址的三個部分依自己的部署替換：compose 的服務名、容器內的連接埠、健康檢查的路徑
    url: "http://laravel:8080/-/healthz"
    interval: 30s
    conditions:
      - "[STATUS] == 200"
  # 回應時間不放進條件；延遲由 Prometheus 以時間窗內慢探測的比例判斷（見下一節的 ProbeSlow）
```

拆掉回應時間的條件之前，要先有延遲的告警接手，否則延遲沒有任何告警。同一個開發環境改成這個設定之後，Mac 的 load 仍在 60 到 95 之間，Laravel 的探測連續 146 次成功；這代表延遲不再算進可用性的判斷，Laravel 仍然慢，那一面由下一節的 `ProbeSlow` 負責（同一個環境近 12 小時裡，它對 Laravel 的條件連續成立最長 47 分鐘）。

## 告警的持續條件：`for`、連續失敗次數與時間窗聚合

單次的慢或單次的失敗不發告警，條件持續一段時間才發。Prometheus 的告警規則用 `for`，Gatus 的告警用 `failure-threshold`（連續失敗幾次才發）與 `success-threshold`（連續成功幾次才算恢復），次數乘上探測間隔就是持續時間：

```yaml
endpoints:
  - name: Laravel 後端
    # url、interval、conditions 同上
    alerts:
      - type: slack   # 通知管道依自己的設定
        failure-threshold: 3   # 間隔 30 秒時，連續失敗 90 秒才發
        success-threshold: 2   # 連續成功 60 秒才算恢復
```

持續時間要比主機的短暫尖峰長，又要比使用者能忍受的時間短。下一節範例的 `for: 5m`，意思是不到五分鐘的尖峰不發告警，而使用者要連續等滿五分鐘才會有人收到通知。Gatus 自己的告警直接送到它設定的通知管道，不經過 Alertmanager，下一節的抑制與分組管不到它；把探測程式放在主機外、用它自己的通知管道正是為了不依賴這台主機上的 Alertmanager，主機內的告警則一律經過 Alertmanager，同一件事不要兩邊都設通知。

`for` 要求每一次評估都成立，所以它只適合本身連續的條件。過載時的 load、讀取耗時與讀取失敗都是間歇的尖峰，原始值加 `for` 在兩次尖峰之間就被打斷：同一個環境近 6 小時裡，`scrape_duration_seconds > 8` 加 `for: 5m` 一次也沒有成立，改成 5 分鐘內的最大值（`max_over_time(scrape_duration_seconds[5m]) > 8`）之後連續成立最長 32 分鐘；`node_load1` 除以核心數大於 1.5 在近 12 小時裡最長只連續 2 分鐘，改成 5 分鐘平均之後最長 9 分鐘。間歇的條件因此先在時間窗內聚合（最大值、平均、比例），再加 `for`。聚合也改變了觸發與恢復的時間：`max_over_time[5m]` 加 `for: 5m` 在 5 分鐘內有兩次以上的尖峰時成立，最後一次尖峰之後還要 5 分鐘才恢復。恢復也要持續一段時間才算數，Prometheus 用規則的 `keep_firing_for`（條件不成立之後告警再維持多久）；這是遲滯（hysteresis）在時間上的做法，門檻上的做法（恢復的門檻比觸發的嚴）與兩者的定義見 4.4 的〈Alert Noise Control〉。

## 依原因抑制：主機飽和時壓下各服務變慢

主機過載時，同一台機器上每個服務的延遲告警會一起發出，收到告警的人看到的是一串症狀，而沒有一則說出它們共同的原因。Alertmanager 的[抑制規則](/backend/knowledge-cards/alert-inhibition/)（`inhibit_rules`，inhibit）讓「原因」的告警成立時，自動壓下它造成的「症狀」告警。抑制由另一則告警是否成立決定；Alertmanager 另有靜音（silence），那是人手動設定一段時間不通知，例如維護時段，兩者是不同的機制。

告警規則寫在 Prometheus 的規則檔裡，規則檔的路徑列在 Prometheus 設定的 `rule_files`，Prometheus 設定的 `alerting.alertmanagers` 指向 Alertmanager；兩邊的設定改完要重新載入（Prometheus 要帶 `--web.enable-lifecycle` 啟動，才能 `POST /-/reload`）：

```yaml
# Prometheus 的告警規則檔
groups:
  - name: host-and-service
    rules:
      - alert: HostCpuSaturated
        expr: |
          avg_over_time(node_load1[5m]) / count without (cpu, mode) (node_cpu_seconds_total{mode="idle"}) > 1.5
          or avg without (cpu, mode) (rate(node_cpu_seconds_total{mode="steal"}[5m])) > 0.1
        for: 5m
        keep_firing_for: 15m   # 不短於症狀規則的時間窗
        labels: { severity: warning, scope: host }
      - alert: ProbeSlow
        expr: avg_over_time((gatus_results_duration_seconds{group="後端"} > bool 0.5)[15m:30s]) > 0.2
        for: 10m
        labels: { severity: warning, scope: service }
      - alert: ScrapeNearTimeout
        expr: max_over_time(scrape_duration_seconds[5m]) > 8
        for: 5m
        labels: { severity: warning, scope: monitoring }
```

```yaml
# Alertmanager 設定檔（alertmanager.yml）裡加上這一段；設定檔本身還要有 route 與 receivers，amtool 才會通過
# 主機飽和的告警成立時，壓下 warning 級的症狀；服務停止的告警與會通知值班的症狀不壓
inhibit_rules:
  - source_matchers: [alertname="HostCpuSaturated"]
    target_matchers: [alertname=~"ProbeSlow|ServiceSlow|ScrapeNearTimeout", severity="warning"]
```

規則裡的數字與名稱要依自己的環境重定：

- **`HostCpuSaturated`**：`1.5` 是 5 分鐘平均的 load 為核心數的 1.5 倍以上，代表平均每顆核心有半個行程在排隊；`0.1` 是 [steal](/backend/knowledge-cards/cpu-steal-time/)（虛擬化層 hypervisor 把這台虛擬機想用的 CPU 時間分給別的虛擬機）佔了一成以上的 CPU 時間，雲端虛擬機被其他租戶搶走 CPU 時，虛擬機自己的 load 不一定升高，所以兩者都要看。兩個都是起始值，拿主機平常一段時間的資料校正。Linux 的 load 含等磁碟的行程，磁碟爭用也會讓這條成立；要分開 CPU 與磁碟的排隊，核心有提供 PSI 時（`node_scrape_collector_success{collector="pressure"}` 是 1）看 `node_pressure_cpu_waiting_seconds_total` 與 io 那一組。`keep_firing_for: 15m` 讓它在條件解除後再維持 15 分鐘：症狀規則帶 15 分鐘的時間窗，主機恢復後還會成立一陣子，原因先解除的話，抑制跟著解除，症狀的通知會在事故結束之後才送出。
- **`ProbeSlow`**：15 分鐘內回應超過 0.5 秒（對應前面 Gatus 的 500 ms）的探測佔兩成以上；子查詢的步長 `30s` 對齊探測間隔，Prometheus 的讀取間隔要不長於探測間隔，否則有些探測結果讀不到；`group="後端"` 依自己的探測設定替換。後端輸出延遲分布之後，另加一條以 histogram 算的 `ServiceSlow`（`histogram_quantile(0.95, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))`，指標名稱與區分服務的標籤依各專案替換）。
- **`ScrapeNearTimeout` 的 `8`**：Prometheus 預設讀取逾時 10 秒的八成，逾時改了要跟著改。讀取逼近逾時也列為症狀，因為主機飽和時 Prometheus 自己也在等 CPU（見〈探測程式與 Prometheus 在過載主機上的 CPU 等待〉）。

容器用完自己的 CPU 配額而被暫停執行（CPU throttling，`rate(container_cpu_cfs_throttled_seconds_total[5m])`，只有設了 CPU 上限的容器才輸出）不放進主機飽和的規則：它的成因是那個容器的上限，主機不一定滿，接進來會在上限設太低時反而壓下各服務的症狀。被暫停的時間升高，就調高那個容器的上限或改設權重（見 [Resource Limit](/backend/knowledge-cards/resource-limit/)）。steal 的比例持續高於平常時，可突發型的雲端機型在 standard 模式下先查 CPU 額度是否用完，unlimited 模式額度用完不會降速、只會另外計費，原因在其他租戶，換機型或換主機（額度去哪裡查見共用主機的資源競爭〈容量估算〉）。

**抑制與嚴重度的取捨。** 4.4 的分級裡，critical 會通知值班人員，warning 在工作時間處理。[Symptom-based Alert](/backend/knowledge-cards/symptom-based-alert/) 讓使用者感受得到的症狀走 critical；本篇的分工是：會通知值班人員的是可用性（服務停止回應）與以 SLO 推出的錯誤預算消耗速度，以固定門檻判斷的延遲（`ProbeSlow`）刻意列為 warning，因為固定門檻在主機過載這類共同原因下會一起成立、需要先查原因。抑制把通知交給原因的那一則告警，所以只用在 warning 級的症狀：症狀告警被壓下之後，由主機飽和那一則告警的通知說明發生了什麼。會通知值班人員的症狀不抑制，原因是抑制也會把同時發生、與主機無關的故障一起藏掉，而那正是值班人員要收到的；同一台主機一起成立的 critical 症狀，改用 Alertmanager 的分組（`group_by` 依主機）合成一則通知，主機飽和的狀態附在通知或儀表板上。分組的代價是同一台主機上無關的告警也併進同一則通知，而之後才加入群組的告警要等 `group_interval`（預設 5 分鐘）才送出。單機時 `group_by: [alertname]` 與依主機分組效果相同。抑制只在原因成立的期間生效，所以兩端都要對齊：觸發時，原因規則從條件成立到告警成立的時間（時間窗造成的延遲加上 `for`）不長於症狀規則的同一段時間，否則症狀的通知先送出；恢復時，原因規則以 `keep_firing_for` 讓告警維持到症狀規則的時間窗退完之後。

**多台主機時要有一個代表主機的標籤。** 上面的規則沒有 `equal`，任何一則 `HostCpuSaturated` 都會壓下全部的症狀，只適用於一台主機。`instance` 不能當主機標籤：它是讀取對象的位址，同一台主機上 node_exporter、postgres_exporter、cAdvisor 的 `instance` 都不同，寫 `equal: [instance]` 之後，只有恰好讀自 node_exporter 的症狀會被抑制，其餘服務的症狀都不會。做法是替症狀與原因都加一個 `host` 標籤，它指**症狀發生的那台主機**，不是 exporter 所在的主機：跑在被監控主機上的 exporter，`host` 寫在讀取設定裡每個讀取對象上（`static_configs` 或檔案清單的 `labels`），用雲端的服務發現時以 `relabel_configs` 從執行個體的 `__meta_*` 標籤取；寫成整個 job 共用的常數（`relabel_configs` 的 `replacement`）只在一個 job 只讀一台主機時成立，一個 job 列了好幾台時每台都會被標成同一個名字（目標清單與服務發現的寫法見 [多台主機的指標收集](/backend/04-observability/vendors/prometheus/multi-host-scraping/)）；探測類的指標（Gatus、Blackbox exporter）是從探測程式讀出來的，`host` 要填被探測的那個端點所在的主機，用 `metric_relabel_configs` 依端點名稱或網址決定填哪台（Blackbox 從 `__param_target` 取得被探測的網址）；Pushgateway 由推送端在 grouping label 帶 `host`，並設 `honor_labels: true`。抑制規則寫 `equal: [host]`，症狀規則的聚合也保留 `host`。Kubernetes 上，原因（node_exporter 的序列）與症狀（服務的序列）都要有節點的標籤：服務的序列帶的是 Pod 的位址，用 `* on (namespace, pod) group_left(node) kube_pod_info` 把 `kube_pod_info` 的 `node` 標籤加到服務的序列上；node_exporter 的序列用 `label_replace` 產生同名的 `node` 標籤。

**這條抑制規則在虛擬機裡判斷不到虛擬機以外的原因。** Mac 的 load 在 55 到 78 之間的那次過載，load 是核心數的七到十倍，虛擬機裡算出來的值卻始終低於 1.5，OrbStack 的虛擬機裡 steal 的序列存在、值恆為 0，`HostCpuSaturated` 不會成立，抑制也不會發生。虛擬機裡沒有指標直接指出這個原因；間接反映它的是 Prometheus 自己的讀取耗時（`scrape_duration_seconds`）與探測的回應時間，它們在各服務 CPU 用量都低時一起升高。成因告警成立不了時，症狀告警仍會一起發出，`group_by` 把它們合成一則通知（機制見 4.4〈Alert Noise Control〉）。開發用的虛擬機上主機飽和的規則本來就不會成立，所以在實體主機或雲端虛擬機上要另外壓滿全部核心驗一次（例如 `stress-ng --cpu 0 --timeout 15m`，`--cpu 0` 代表每顆核心一個工作者）。正式環境的主機是雲端虛擬機時，steal 時間通常量得到；是自己的實體機時，node_exporter 看到的就是那台機器，load 的判斷是準的。

## 以合成告警驗證抑制規則

主機飽和不容易刻意製造，所以抑制規則改用合成的告警驗證。Alertmanager 判斷抑制時只比對它收到的告警的標籤，不管告警是不是 Prometheus 算出來的；它的 API 接受直接送入的告警，送一組標籤符合規則的「原因」與「症狀」，就能單獨驗證抑制規則：

```sh
# 送入一組合成的告警，15 分鐘後自動結束（macOS 的 date 語法；Linux 用 date -u -d '+15 min'）
# 127.0.0.1:9093 是 Alertmanager 的預設位址，依自己的部署替換；job 是任意的標記，讓合成告警在清單裡認得出來
now=$(date -u +%Y-%m-%dT%H:%M:%SZ); end=$(date -u -v+15M +%Y-%m-%dT%H:%M:%SZ)
curl -XPOST http://127.0.0.1:9093/api/v2/alerts -H 'Content-Type: application/json' -d "[
  {\"labels\":{\"alertname\":\"HostCpuSaturated\",\"severity\":\"warning\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"},
  {\"labels\":{\"alertname\":\"ScrapeNearTimeout\",\"severity\":\"warning\",\"job\":\"injected\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"}]"
# 只列出被抑制的告警：症狀應該在這裡，status.state 是 suppressed，inhibitedBy 列出壓下它的那一則
curl -s 'http://127.0.0.1:9093/api/v2/alerts?active=false&silenced=false&unprocessed=false'
```

每一則合成告警的標籤，各自從它那條規則的運算式取：拿掉比較運算子直接在 Prometheus 查（例如原因查 `avg_over_time(node_load1[5m]) / count without (cpu, mode) (node_cpu_seconds_total{mode="idle"})`，症狀查 `max_over_time(scrape_duration_seconds[5m])`），把查到的標籤原樣帶上，原因與症狀各查各的，不手動把兩邊的值統一；`ALERTS` 只有在規則成立過之後才有序列，從沒成立過的規則查不到。規則有 `equal` 時，兩邊查到的 `host` 值本來就應該相同，不同就是標籤沒接好；另送一則 `host` 值不同的症狀當對照，再用不帶篩選的 `GET /api/v2/alerts` 確認它維持 `active`（只列被抑制告警的那個查詢看不到它）。同一個短網址服務的實測：送入之後 `ScrapeNearTimeout` 的狀態是 `suppressed`，`HostCpuSaturated` 是 `active`。這只驗證 Alertmanager 的抑制規則；Prometheus 的「主機飽和」規則會不會在實際飽和時成立，要另外以[故障注入](/backend/knowledge-cards/chaos-test/)確認，而虛擬機裡這條規則本來就不會成立，驗收紀錄要把它列為未驗。

## 抑制規則與各服務受影響程度的差別

同一次過載的量測裡，Go 與 Laravel 在同一台主機上，探測回應時間在 500 ms 以內的比例分別是 92.5% 與 49%，未達標的全是慢、沒有錯誤。這個差距是線索：主機資源吃緊時哪一個服務先變慢，也就是該先給它較高的權重、或先分到另一台主機的那一個（隔離的層級見共用主機的資源競爭〈隔離的層級與代價〉）。探測的回應時間也包含 Gatus 自己等 CPU 的時間，所以要排出敏感度，用同一段時間各後端的延遲分布確認。抑制規則把兩者的告警一起壓下，這個差別就只剩在儀表板上。

抑制只壓通知、不壓紀錄：告警在 Prometheus 的 `ALERTS` 序列裡照常留下成立與結束的時間，儀表板上各服務的延遲也照常保留；Alertmanager 的頁面只顯示還在作用中的告警，事後要回頭查就看 `ALERTS`。檢討一次過載時，看的是這段時間各服務的延遲與錯誤率，而不只是「那時候主機過載」。

## 探測程式與 Prometheus 在過載主機上的 CPU 等待

探測程式與 Prometheus 跑在同一台過載的主機上，它們自己也在等 CPU：

- **探測的回應時間包含探測程式自己的等待**：從送出請求到讀完回應，中間任何一段沒分到 CPU 都算進回應時間，被探測的服務不一定有那麼慢。
- **Prometheus 的讀取逾時**：`scrape_duration_seconds` 是每次讀取 exporter 的耗時，逼近 `scrape_timeout`（預設 10 秒）時，讀取開始失敗、時間序列出現空洞；那次過載中 postgres 的讀取在 30 分鐘內失敗了 4 次。空洞在儀表板上看起來是一段沒有資料，容易被讀成服務停了。讀取對象本身回應慢、讀取對象太多等其他成因，見 [Prometheus 容量規劃與故障模式](/backend/04-observability/vendors/prometheus/capacity-failure-modes/)。
- **監控整個停掉**：主機的資源完全耗盡時，監控與被監控的服務一起停，沒有人發出告警。

對策是讓至少一個[頻外訊號](/backend/knowledge-cards/out-of-band-signal/)來自過載的主機之外：正式環境的外部探測放在另一台機器或用外部的 uptime 服務，並監控 Prometheus 本身（業界稱 meta-monitoring：讀取耗時、讀取成功的比例 `avg_over_time(up[15m])`）。監控整個停掉的那一種，Prometheus 自己發不出告警，要靠 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/) 的心跳消失偵測：Prometheus 有一條永遠成立的告警規則（Watchdog，運算式寫 `vector(1)`），Alertmanager 經由一條專用的 route 把它持續送到外部的服務，外部服務在心跳中斷時通知（dead man's switch）。這條 route 的 `repeat_interval` 預設是 4 小時，而且 Alertmanager 會把它往上取到 `group_interval`（預設 5 分鐘）的倍數，所以兩個都要設短於外部服務的心跳期限（例如 `group_interval: 30s`、`repeat_interval: 1m`，對 5 分鐘的心跳期限），`group_wait` 設 0，`group_by` 只放 `alertname`；只改 `repeat_interval` 的話實際上每 5 分鐘才送一次，外部服務會反覆誤報。這幾種情形都是 4.25 在單機情境下的形態。

## 資源隔離：讓監控不比服務先失效

正式環境給重要的服務與監控設定資源的保留量或優先權，主機吃緊時這些服務與監控先分到資源，監控也不會比服務先失效；各個隔離層級的做法與代價見 [共用主機的資源競爭](/operations/05-capacity-planning/shared-host-contention/)〈隔離的層級與代價〉。

開發用的 Mac 上，容器的資源保留只在 Docker 的虛擬機之內生效，管不到 Mac 上的其他程式。Mac 被其他程式佔滿的那段時間，各後端的延遲會讓 `ProbeSlow` 成立，而成因不在服務；那段時間量到的數字能不能拿來和其他時間比較，見共用主機的資源競爭〈容量估算〉。

## 延伸閱讀：告警的分組與分級、SLO 告警與監控的分層

- 抑制之外的降噪手段（分組、條件持續與恢復時的遲滯）與告警的嚴重度分級，見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)。
- 探測工具怎麼選、怎麼接進 Compose，以及容器自己的 healthcheck 與外部探測的分工，見 [多容器服務的存活監看](/operations/04-service-health/multi-container-monitoring/)。
- 本篇的延遲告警用固定的門檻 0.5 秒；門檻改由 SLO 推出、以錯誤預算的消耗速度判斷的寫法在 [4.6 SLI 量測與 SLO 訊號設計](/backend/04-observability/sli-slo-signal/) 與 [Burn Rate](/backend/knowledge-cards/burn-rate/)。
- 告警描述症狀而不是內部指標的理由，見 [Symptom-based Alert](/backend/knowledge-cards/symptom-based-alert/)。
- 本篇的主機飽和規則算的是虛擬機的 load 與 steal；監控裝在哪一層就看不到哪些範圍、主機的磁碟怎麼一起涵蓋，見 [4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/)。
