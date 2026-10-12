---
title: "4.27 主機過載時的監控告警：可用與變慢分開判斷、依原因抑制、監控自身的等待"
date: 2026-10-12
description: "多個服務共用一台主機而主機過載時，各服務的探測與告警會一起失敗：可用性與延遲分成兩個判斷的寫法、條件持續才告警、以主機飽和抑制各服務變慢的規則與它在虛擬機裡失效的條件、抑制藏起各服務受影響程度的差別、探測與 Prometheus 自己也在等 CPU 時的訊號，以及資源隔離與練習環境的前置檢查；附一次實際過載的量測"
weight: 27
tags: ["backend", "observability", "alerting", "prometheus", "monitoring"]
---

這篇整理多個服務共用一台主機（或一台虛擬機）時，主機本身過載讓各服務的監控一起報失敗的處理方式。共用主機是部署時的一個設計條件，它在容量估算、故障範圍與隔離層級上各要考慮什麼，見 [共用主機的資源競爭](/operations/05-capacity-planning/shared-host-contention/)；這篇只談它在監控與告警上的那一面。告警的一般機制（抑制、條件持續才觸發、burn rate）在 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)，各層的指標從哪裡收見 [4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/)。

文中的數字來自一個短網址服務的開發環境：macOS 上的 OrbStack 跑 Docker Compose，監控是 Prometheus 3.15.0、Gatus 5.37.0，告警規則的範例以 `promtool` 與 Alertmanager 0.34.1 的 `amtool` 檢查過語法。

## 一次主機過載在各層留下的訊號

跑這個開發環境的 Mac 有 8 顆核心，load average 在 55 到 78 之間持續了數小時，佔用 CPU 的是 Mac 上與這個服務無關的其他程式。Docker 的虛擬機同樣分到 8 顆核心。同一段 30 分鐘裡各層的監控回報：

| 層                                                                    | 回報                                                                                |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Gatus 對 Laravel 後端的探測（條件：回應碼 200 且回應時間低於 500 ms） | 成功率 49%，最慢 6.0 秒，失敗的那幾次回應碼都是 200                                 |
| Gatus 對 Go 後端的探測（同樣的條件）                                  | 成功率 92.5%，最慢 2.1 秒                                                           |
| Laravel 容器自己的 healthcheck（只看回應碼）                          | 一直是 healthy                                                                      |
| 虛擬機裡的 node_exporter                                              | load 除以核心數在 0.33 到 1.28 之間（平均 0.69）                                    |
| Prometheus 讀取（scrape）各 exporter 的耗時                           | 各 job 的最大值 8.6 到 14.9 秒，預設逾時 10 秒；postgres 那一個 job 有 4 次讀取失敗 |

這張表裡每一個監控回報的都是事實：Laravel 對使用者來說確實變慢了，容器確實活著，虛擬機的負載確實低於一般的告警門檻。收到告警的人看到的是「Laravel 後端失敗」，而成因在 Mac 上，沒有任何一個訊號指向它。這個情境有三個要分開處理的問題：告警把「變慢」報成「失敗」、告警只報出各服務的症狀而沒有附上它們共同的原因、監控自己也在同一台過載的機器上。

## 可用性與延遲分成兩個判斷

Gatus 那條探測把兩個條件放在一起，任一個不成立就判失敗，所以「慢」和「掛了」在結果裡長得一樣。分成兩個判斷，兩者的處置不同：

- **可用性**：連不連得上、回應碼對不對。不成立代表服務停止回應請求了，要有人立刻處理。
- **延遲**：一段時間內的百分位數（例如 5 分鐘的 p95），不看單次探測。延遲高代表使用者等得久，先查原因再決定動作。

外部探測一次只量一個請求，用來判斷可用性很適合，用來判斷延遲則雜訊很大：同一個 Go 後端在幾秒內的探測可以從 0.3 秒到 2 秒。延遲的判斷用後端自己輸出的請求延遲分布（histogram）算百分位數，它反映的是全部真實請求，而不是探測那一個。拆開之後的 Gatus 設定：

```yaml
endpoints:
  # 可用性：只看回應碼，失敗代表服務沒有在回應請求
  - name: Laravel 後端
    group: 後端
    url: "http://laravel:8080/-/healthz"
    interval: 30s
    conditions:
      - "[STATUS] == 200"
  # 延遲由後端的 histogram 在 Prometheus 判斷，探測的回應時間只留在儀表板上參考
```

同一個開發環境改成這個設定之後，Mac 的 load 仍在 60 到 95 之間，Laravel 的探測連續 146 次成功。

## 告警的持續條件：Prometheus 的 `for` 與 Gatus 的連續失敗次數

單次的慢或單次的失敗不發告警，條件持續一段時間才發。Prometheus 的告警規則用 `for`，Gatus 的告警用 `failure-threshold`（連續失敗幾次才發）與 `success-threshold`（連續成功幾次才算恢復）。持續時間要比主機的短暫尖峰長，又要比使用者能忍受的時間短；機制與恢復時的遲滯（hysteresis，恢復的條件比觸發的條件嚴，避免告警在門檻附近反覆開關）見 4.4 的〈Alert Noise Control〉。

## 依原因抑制：主機飽和時壓下各服務變慢

主機過載時，同一台機器上每個服務的延遲告警會一起發出，收到告警的人看到的是一串症狀，而沒有一則說出它們共同的原因。Alertmanager 的抑制規則（`inhibit_rules`，inhibit）讓「原因」的告警成立時，自動壓下它造成的「症狀」告警，通知改由原因那一則說明：

```yaml
# Prometheus 的告警規則
groups:
  - name: host-and-service
    rules:
      - alert: HostCpuSaturated
        expr: node_load1 / count without (cpu, mode) (node_cpu_seconds_total{mode="idle"}) > 1.5
        for: 5m
        labels: { severity: warning, scope: host }
      - alert: ServiceSlow
        expr: histogram_quantile(0.95, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m]))) > 0.5
        for: 5m
        labels: { severity: warning, scope: service }
      - alert: ScrapeNearTimeout
        expr: scrape_duration_seconds > 8
        for: 5m
        labels: { severity: warning, scope: monitoring }
```

```yaml
# Alertmanager：主機飽和的告警成立時，壓下各服務變慢與讀取逼近逾時的告警；服務停止的告警不壓
inhibit_rules:
  - source_matchers: [alertname="HostCpuSaturated"]
    target_matchers: [alertname=~"ServiceSlow|ScrapeNearTimeout"]
```

規則裡的數字要依自己的環境重定：`1.5` 是 load 超過核心數的一倍半，代表平均每顆核心有半個行程在排隊；`0.5` 是 p95 延遲 0.5 秒，對應前面 Gatus 的 500 ms；`8` 秒是 Prometheus 預設讀取逾時 10 秒的八成。`ServiceSlow` 的 `http_request_duration_seconds_bucket` 是後端用 client library 輸出的請求延遲分布，名稱依各專案自己定的指標名稱替換。讀取逼近逾時也列為症狀，因為主機飽和時 Prometheus 自己也在等 CPU（見〈探測程式與 Prometheus 在過載主機上的 CPU 等待〉）。

抑制的方向要和告警的分級一致。4.4 的分級是高嚴重度壓低嚴重度，而 [Symptom-based Alert](/backend/knowledge-cards/symptom-based-alert/) 讓使用者感受得到的症狀走最高的那一級；所以要壓下會通知值班人員的延遲告警時，`HostCpuSaturated` 自己的嚴重度不能比它低，否則使用者正在等的那段時間沒有人收到任何通知。上面的範例兩者都是 `warning`。

這條規則沒有 `equal`，任何一則 `HostCpuSaturated` 都會壓下全部的 `ServiceSlow`，只適用於一台主機的情境。多台主機時加 `equal: [instance]`（或自訂的主機標籤），症狀告警的聚合也要保留同一個標籤，否則一台主機飽和會把其他主機的症狀一起藏掉。

主機飽和的判斷除了 load 除以核心數，還有兩個訊號：Linux 虛擬機的 `node_cpu_seconds_total{mode="steal"}`（虛擬機想用 CPU 而虛擬化層 hypervisor 分給了別人的時間），以及 cAdvisor 的 `container_cpu_cfs_throttled_seconds_total`（容器用完自己的 CPU 配額而被暫停執行的時間，CPU throttling；只有設了 CPU 上限的容器才輸出這個指標）。steal 時間升高指向機器之外的競爭，被暫停的時間升高指向容器自己的配額設得太低，兩者的處置不同。

**這條抑制規則在虛擬機裡判斷不到虛擬機以外的原因。** Mac 的 load 在 55 到 78 之間的那次過載，load 是核心數的七到十倍，虛擬機裡算出來的值卻始終低於 1.5，`HostCpuSaturated` 不會成立，抑制也不會發生。OrbStack 的虛擬機裡 steal 的序列存在、值恆為 0，看不出 Mac 上的競爭，虛擬機裡沒有任何指標反映它。這種情況下能用的訊號是間接的：同一台主機上全部服務的延遲同時上升，而它們的 CPU 用量都不高。正式環境的主機是雲端虛擬機時，steal 時間通常量得到；是自己的實體機時，node_exporter 看到的就是那台機器，load 的判斷是準的。

抑制規則寫完要確認它會壓下目標，而主機飽和不容易刻意製造。Alertmanager 的 API 接受直接送入的告警，用它送一組合成的「原因」與「症狀」，再查症狀的狀態：

```sh
# 送入一組合成的告警，15 分鐘後自動結束（macOS 的 date 語法；Linux 用 date -u -d '+15 min'）
# 127.0.0.1:9093 是 Alertmanager 的預設位址，依自己的部署替換
now=$(date -u +%Y-%m-%dT%H:%M:%SZ); end=$(date -u -v+15M +%Y-%m-%dT%H:%M:%SZ)
curl -XPOST http://127.0.0.1:9093/api/v2/alerts -H 'Content-Type: application/json' -d "[
  {\"labels\":{\"alertname\":\"HostCpuSaturated\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"},
  {\"labels\":{\"alertname\":\"ScrapeNearTimeout\",\"job\":\"injected\"},\"startsAt\":\"$now\",\"endsAt\":\"$end\"}]"
# 只列出被抑制的告警：症狀應該在這裡，status.state 是 suppressed，inhibitedBy 列出壓下它的那一則
curl -s 'http://127.0.0.1:9093/api/v2/alerts?active=false&silenced=false&unprocessed=false'
```

送入的兩則告警，標籤要分別符合 `source_matchers` 與 `target_matchers`；規則有 `equal` 時，兩則都要帶上那幾個標籤而且值相同。同一個短網址服務的實測：送入之後 `ScrapeNearTimeout` 的狀態是 `suppressed`，`HostCpuSaturated` 是 `active`。這只驗證 Alertmanager 的抑制規則；Prometheus 的「主機飽和」規則會不會在實際飽和時成立，要另外以故障注入確認。

## 抑制規則與各服務受影響程度的差別

同一次過載的量測裡，Go 與 Laravel 在同一台主機上，探測成功率分別是 92.5% 與 49%。兩者對 CPU 被搶的敏感程度不同，而這正是容量規劃要知道的事：主機資源吃緊時，哪一個服務先出現延遲與錯誤。抑制規則把兩者的告警一起壓下，這個差別就只剩在儀表板上。

所以抑制只壓通知，不壓紀錄：被抑制的告警在 Alertmanager 裡仍查得到，儀表板上各服務的延遲照常保留。事後檢討一次過載時，看的是這段時間各服務的延遲與錯誤率，而不只是「那時候主機過載」。

## 探測程式與 Prometheus 在過載主機上的 CPU 等待

探測程式與 Prometheus 跑在同一台過載的主機上，它們自己也在等 CPU：

- **探測的回應時間包含探測程式自己的等待**：從送出請求到讀完回應，中間任何一段沒分到 CPU 都算進回應時間，被探測的服務不一定有那麼慢。
- **Prometheus 的讀取逾時**：`scrape_duration_seconds` 是每次讀取 exporter 的耗時，逼近 `scrape_timeout`（預設 10 秒）時，讀取開始失敗、時間序列出現空洞；那次過載中 postgres 的讀取在 30 分鐘內失敗了 4 次。空洞在儀表板上看起來是一段沒有資料，容易被讀成服務停了。
- **監控整個停掉**：主機的資源完全耗盡時，監控與被監控的服務一起停，沒有人發出告警。

對策是讓至少一個訊號來自過載的主機之外：正式環境的外部探測放在另一台機器或用外部的 uptime 服務，並監控 Prometheus 本身（`scrape_duration_seconds` 與 `up` 的空洞）。監控整個停掉的那一種，Prometheus 自己發不出告警，要靠 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/) 的心跳消失偵測：一則永遠成立的告警（Watchdog）持續送到外部的服務，外部服務在心跳中斷時通知（dead man's switch）。這幾種情形都是 4.25 在單機情境下的形態。

## 資源隔離與練習環境的前置檢查

正式環境給重要的服務與監控設定資源的保留量或優先權，主機吃緊時它們先分到資源，監控也不會比服務先失效；各個隔離層級的做法與代價見 [共用主機的資源競爭](/operations/05-capacity-planning/shared-host-contention/)〈隔離的層級與代價〉。

開發用的 Mac 上，Docker 的虛擬機與 Mac 的其他程式共用 CPU 與磁碟。容器的資源保留只在虛擬機之內生效，管不到 Mac 上的其他程式，所以其他程式搶走 CPU 造成的量測雜訊只能接受。要拿數字做判斷的工作（壓測、大量資料的實驗、效能的前後比較）開始之前，先在主機上確認 load 與磁碟空間，超過門檻就不跑：那段時間量到的數字和其他時間的不能比。

## 延伸閱讀：告警的一般機制、SLO 告警與監控的分層

- 抑制、分組、條件持續與恢復時的遲滯，見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)。
- 以錯誤預算的消耗速度告警，取代固定的延遲門檻，見 [4.6 SLI 量測與 SLO 訊號設計](/backend/04-observability/sli-slo-signal/) 與 [Burn Rate](/backend/knowledge-cards/burn-rate/)。
- 告警描述症狀而不是內部指標的理由，見 [Symptom-based Alert](/backend/knowledge-cards/symptom-based-alert/)。
- 監控裝在哪一層就看不到哪些範圍，見 [4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/)。
