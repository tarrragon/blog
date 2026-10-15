---
title: "4.0 服務端監控的分層：容器與程序的自檢、服務網路內的探測、元件指標、應用層訊號、告警規則與分送、告警鏈的監看與使用者路徑的合成監控"
date: 2026-10-14
description: "以每一層監控檢查的對象、看不到的範圍與接手的那一層，把服務端監控串成一條監控鏈，以及拿它盤點一個服務時怎麼判讀缺口的性質（檢查範圍、位置、讀取與訊號失真），涵蓋自架主機、Kubernetes 與雲端託管的情形；使用者路徑那一層另寫合成監控與真實使用者監測的差別，以及盤點時各種缺口的補法"
weight: -4
tags: ["backend", "observability", "monitoring", "alerting"]
---

這一篇把一個後端服務的監控，依每一層檢查的對象排成一條鏈，說明每一層看不到的範圍由哪一層接手，以及拿這條鏈盤點一個服務時怎麼判讀缺口。各層都正常時仍會發生的異常另寫在 [4.0.1 監控鏈事前偵測不到的異常](/backend/04-observability/monitoring-outside-the-chain/)，兩個服務的實際盤點寫在 [4.0.2 以監控鏈盤點單機短網址服務](/backend/04-observability/monitoring-inventory-single-host/) 與 [4.0.3 以監控鏈盤點 Kubernetes 上的電商 checkout](/backend/04-observability/monitoring-inventory-k8s-checkout/)。範圍是跑在自己的主機、Kubernetes 或雲端託管平台上的服務；使用者端（行動 App、網頁、本機腳本）的事件蒐集是另一條路線，見 [監控實務指南](/monitoring/)。各層的做法與設定在連過去的專章裡，這一篇處理它們之間的關係。

例子是一台主機上以 Docker Compose 跑的短網址服務（功能與需求見 [Backend 範例系統](/backend/case-systems/) 的〈短網址服務〉）：入口 Nginx、後端程式、PostgreSQL 與 Valkey，各在一個容器裡。下文把主機、容器、資料庫、快取與入口這些組成服務的單位稱為**元件**，監控用的程式（健康檢查、探測工具、Prometheus、雲端業者的監控）稱為**觀察者**，「層」只用來指監控的層。

## 一層監控檢查的對象與它的缺口

每一個觀察者站在某個位置、檢查一件事。容器的健康檢查確認程序自己的端點能回應；Prometheus 讀取主機與各容器的數字，量測這些元件用了多少資源；心跳監看確認評估告警規則並送出通知的那一串程式仍在運作（那一串程式定期送訊號到另一處，那一處沒收到就通知人）。同一個服務上的各種監控，差別在檢查的對象，也在觀察者的位置。

一個觀察者的盲區分成檢查範圍盲區與位置盲區。**檢查範圍盲區**是它沒有檢查的故障：容器的健康檢查從容器裡面打自己的端點，入口 Nginx 的路由寫錯時，使用者的請求進不來，而健康檢查照樣成功。**位置盲區**是被觀察的元件出事時、觀察者跟著一起停掉的故障：觀察者與被觀察的元件共用同一台主機、同一個 Kubernetes 叢集、同一個雲端帳號或區域、同一條網路時，那個共用的依賴停掉，元件與觀察者一起停，不會有人回報。這一組會一起停掉的依賴叫 [Failure Domain（失效域）](/backend/knowledge-cards/failure-domain/)，判斷時要說清楚是對哪一種失效：雲端業者的監控在一台主機停掉時站在失效域以外，在業者帳號被停權時站在失效域以內；區域故障時依業者而定，CloudWatch 是區域服務、跟著受影響，Google Cloud Monitoring 是全域服務、消失的是那個區域送來的數字。觀測系統與服務一起退化的情形，[4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/) 稱為觀測共命運失效。

盲區之外還有讀取缺口與訊號失真兩種缺口。**讀取缺口**是觀察者看到了，而結果沒有變成送到人手上的通知：沒有任何程式讀它的結果（Docker 把容器標成 `unhealthy`、程式的錯誤率升高，都只是一個狀態或一個數字），或者有規則讀、通知卻送不出去（通知管道的網址寫錯、推播服務拒收）。**訊號失真**是觀察者有檢查、位置對、也有規則讀，而送到人手上的結果仍然不可信：觀察者自己壞掉而被觀察的元件不一定有事時，觀察者的數字跟著消失，以那個數字寫的規則不會成立，看起來與一切正常相同（與位置盲區的分界在出事的是誰：位置盲區是元件出事、觀察者陪著停，這裡是觀察者自己出事）；門檻停在舊的基線；規則以平均值寫，尾端的延遲被蓋掉；告警多到被忽略（[Alert Fatigue](/backend/knowledge-cards/alert-fatigue/)）。各種形態見 [4.5 可觀測性威脅建模](/backend/04-observability/attacker-view-observability-risks/) 的〈弱點二：告警失真〉與 [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/) 的〈缺漏與漂移〉。

服務端監控的各層就是為了這幾種缺口疊起來的，而四種缺口的補法不同。補檢查範圍盲區，加的是檢查前一個觀察者碰不到的對象的觀察者（自檢碰不到程序以外的路徑就加探測，探測分不出原因就加元件指標），對同一個對象多加幾個檢查補不上；補位置盲區，加的是一個放在另一個失效域的觀察者，在同一個失效域裡多加幾個觀察者，共用的依賴停掉時它們會一起停。讀取缺口由告警規則與 Alertmanager 這類分送元件補上：規則讀各層觀察者的結果，成立的狀況由分送元件送到人手上。訊號失真沒有專門的一層，由每一層替自己的觀察者另寫一條「讀不到它」的規則（Prometheus 的 `up == 0` 或 `absent()`），以及定期檢查告警規則本身：門檻是否仍對得上基線、延遲是否以百分位數而不是平均值判斷、長期沒有人處理的告警是否該刪，這一類的治理見 [4.8 訊號治理閉環](/backend/04-observability/signal-governance-loop/)。補上一層缺口的不一定是緊接的那一層。這些為了補缺口而疊起來的各層監控，從離程序最近的自檢到站在失效域以外的使用者路徑合成監控，下文稱為**監控鏈**。

## 容器與程序的自檢

自檢確認程序自己仍能回應。Docker 的 `HEALTHCHECK` 每隔一段時間在容器裡執行一條指令（例如請求自己的 `/healthz`，見 [Health Check](/backend/knowledge-cards/health-check/)），連續失敗幾次之後把容器標成 `unhealthy`。Kubernetes 由 kubelet 定期執行 [probe](/backend/knowledge-cards/probe/)：liveness 失敗時重啟容器，readiness 失敗時把它從接流量的名單拿掉，[startup](/backend/knowledge-cards/startup-probe/) 在程序啟動完成之前暫停另外兩種。systemd 的 `WatchdogSec` 要求程序定期回報，沒有回報就把服務標成失敗並終止它，unit 另外設了 `Restart=on-watchdog`（或 `on-failure`、`always`）才會重啟。

自檢的檢查範圍盲區是程序以外的路徑：自檢在程序所在的容器裡執行，請求能否從別的容器到達程序、入口 Nginx 是否把請求轉到正確的服務，自檢都不檢查，由服務網路內的探測接手。自檢的位置盲區是主機：自檢和程序在同一台主機上，主機停掉時一起停，由失效域以外的心跳監看與使用者路徑的合成監控接手。

自檢還有讀取缺口，而重啟不算補上這個缺口：重啟是處置，讀取缺口指的是沒有人收到通知。單機的 Docker（Swarm 模式以外）把容器標成 `unhealthy` 之後不會自己重啟它，也不會通知任何人，Docker 只發出一個 `health_status` 事件；監聽這個事件、重啟容器的 autoheal，Kubernetes 依 liveness 重啟容器，ECS 以新的 task 換掉不健康的 task，都有了處置而仍然沒有人知道，容器一再重啟時也一樣。補上這個缺口要把重啟寫成規則：Kubernetes 上以 kube-state-metrics（讀 Kubernetes API、把物件狀態轉成指標的程式）的 `kube_pod_container_status_restarts_total` 寫告警規則，kube-prometheus-stack 預設就帶容器反覆重啟的規則，而它預設的 Alertmanager 路由不送任何通知，見 [在 Kubernetes 上接上監控](/backend/04-observability/vendors/prometheus/kubernetes-monitoring-entry/) 的〈chart 預設的 Alertmanager 路由：不送任何通知〉；systemd 的 `OnFailure=` 在 unit 放棄重啟、進入失敗狀態時才觸發送出通知的 unit，見 [服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/)，重啟上限以內的每一次重啟，要以 node_exporter 開啟 `--collector.systemd.enable-restarts-metrics` 之後輸出的 `node_systemd_service_restart_total` 寫規則；ECS 的 task 狀態變更以事件送到 EventBridge，要有規則接它；單機的 Docker 只有 dockerd 的全主機健康檢查失敗總數、不分容器，維運者多半不以它寫規則，讓服務網路內的探測另外發現服務壞掉。檢查要探到多深（只回 200，還是連資料庫也查）屬於健康檢查端點的設計，見 [Health check endpoint 設計](/operations/04-service-health/health-check-endpoint/)；Docker 健康狀態的 `starting`、`healthy`、`unhealthy` 與 `unhealthy` 之後由誰處理，見 [容器的健康檢查](/operations/04-service-health/container-healthcheck/)；Kubernetes 的 liveness、readiness 與 startup 探針各自宣告什麼，見 [Liveness 與 Readiness](/operations/04-service-health/liveness-vs-readiness/)。

## 服務網路內的探測

服務網路內的探測從服務的程序以外發請求，確認請求能到達服務並得到成功的回應。Gatus、Uptime Kuma 或 Prometheus 的 blackbox_exporter 跑在另一個容器裡，以服務名稱對各服務發 HTTP 請求或 TCP 連線；打入口 Nginx 的那一條探測，順便確認入口 Nginx 把請求轉到了正確的服務。自檢的檢查範圍盲區（請求能否從別的容器到達程序）由這一層接手。從外面發請求、只看外部行為的監控叫黑箱監控，讀取內部狀態的叫白箱監控，blackbox_exporter 的名字取自黑箱監控；黑箱與白箱分的是觀察方式（看外部行為或讀內部狀態），不分位置，黑箱探測跑在服務主機上時仍與服務共用失效域，見 [White-box and Black-box Monitoring（白箱與黑箱監控）](/backend/knowledge-cards/white-box-black-box-monitoring/)。

服務網路內的探測的檢查範圍盲區有公開入口與故障原因兩種。公開入口指使用者的請求進來的那一段：公開網域解析出的位址、前面有 CDN、雲端負載平衡器或 WAF（擋惡意請求的網頁應用程式防火牆）時的那一段、主機對外的連接埠與防火牆、入口 Nginx 的 HTTPS 監聽與 TLS 憑證。服務網路內的探測以服務名稱在內部網路直接連到 Nginx，不經過這一段，所以網域設錯、憑證過期、雲端業者的網路故障它量不到，由使用者路徑的合成監控接手。故障原因指請求為什麼失敗或變慢：探測只記錄一條路徑成功或失敗、回應花了多久，請求變慢是因為主機的 CPU 不夠、資料庫的連線用完還是程式本身，探測分不出來，由元件指標接手。探測的位置盲區是主機，主機停掉時探測跟著停，同樣由失效域以外的心跳監看與使用者路徑的合成監控接手。

Gatus 與 Uptime Kuma 能以自己的管道發通知，那條通知不經過告警規則、Alertmanager 與通知管道那一串（下文〈告警規則與分送〉稱為告警鏈），所以告警鏈的心跳證明不了 Gatus 還在運作：Gatus 停掉時是這一層的訊號失真，Gatus 的推播送不出去時是讀取缺口。讓 Prometheus 讀 Gatus 的指標（Gatus 設定 `metrics: true` 之後輸出 `gatus_results_total` 這類指標），寫一條在 Prometheus 讀不到 Gatus 的指標時成立的規則，再以 `gatus_results_total{success="false"}` 寫探測失敗的告警規則交給 Alertmanager，兩種缺口都改由告警鏈與它的監看接住。

「外部探測」這個詞在站內有兩種用法。[多容器服務的存活監看](/operations/04-service-health/multi-container-monitoring/) 與 [4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/) 的外部探測就是服務網路內的探測，「外部」相對於服務的程序；[4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/) 與 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/) 談資源隔離的那一處，外部探測指失效域以外、照使用者路徑發出的探測，「外部」相對於服務的失效域，也就是本篇使用者路徑那一層的合成監控。探測的工具選擇與 TCP 檢查的限制在多容器服務那一篇。

## 元件指標：元件用了多少、處理了多少

元件指標量測主機、容器與各服務用了多少資源、處理了多少請求，以及這些數字在一段時間裡怎麼變化。自架時，Prometheus 每隔固定時間讀取各元件的 [exporter](/backend/knowledge-cards/prometheus-exporter/)（把一個元件的狀態轉成 Prometheus 指標的程式）：node_exporter 給主機的 CPU、記憶體、磁碟與網路，cAdvisor 給每個容器的用量，資料庫、快取與 Nginx 各有自己的 exporter 給連線數、查詢量與請求總數。服務網路內的探測分不出的原因由這一層接手：探測變慢的同時主機的 [load](/backend/knowledge-cards/load-average/)（系統負載平均）超過核心數，原因在主機；只有 PostgreSQL 的連線數頂到上限，原因在資料庫。探測與請求指標回報症狀，元件指標用來找原因；告警寫在症狀上、以原因抑制，是同一組分工。逐個元件檢查資源的使用率、飽和度與錯誤，叫 [USE Method](/backend/knowledge-cards/use-method/)。用量現在正常、照目前的速度幾天後寫滿的磁碟，要另外寫一條以 PromQL 的 `predict_linear` 推算的規則，容量的規劃見 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)。

服務跑在雲端時，雲端業者自己的監控（AWS CloudWatch、Google Cloud Monitoring）是另一個觀察者：它從虛擬化層與託管服務讀數字，量測的也是這一層的對象，位置在主機以外、在同一個業者帳號裡，一台主機停掉時它還在運作。託管的元件（託管資料庫、託管快取、Fargate 與 Cloud Run 這類託管容器的主機、函式平台）沒有地方裝 node_exporter、cAdvisor 這類讀主機的 exporter，主機的數字由業者提供，盤點時記成「由業者提供」，Prometheus 要讀它們時經由 cloudwatch_exporter 這類轉接程式。連線型的 exporter（postgres_exporter、redis_exporter）仍可從外面連進託管資料庫與快取讀取；Fargate 的容器健康檢查與 Cloud Run 的 startup、liveness 探針仍屬自檢那一層。告警與資源一起建立的寫法見 [可觀測性與 log 同生命週期管理](/infra/06-observability-logging/log-metric-alarm-lifecycle/)。

元件指標與下一節應用層訊號的分界在量測的對象：元件指標量的是一個元件用了多少、處理了多少，應用層訊號量的是某個端點的請求是否成功、花了多久。應用層訊號多數由服務的程式自己逐端點記錄；入口與平台在程式外逐路徑記錄的請求數、錯誤數與耗時（Kubernetes 入口控制器的請求指標、雲端負載平衡器的存取紀錄、開了逐路由指標的 API Gateway）量測的是同一個對象，盤點時算應用層，它們看不到的是程式內部的分段。入口 Nginx 的 stub_status（Nginx 內建的狀態頁）只給全部請求的總數、不分端點，留在元件指標。[4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/) 把入口與應用程式的請求量合稱流量監控，對應的是這兩層的交界，那一篇的「層」指的是元件。

元件指標的檢查範圍盲區是個別的請求與回應內容的正確性：指標是彙總後的數字，一個使用者的某一次請求為什麼失敗、經過了哪些服務，它沒有記錄，由應用層訊號的 log 與 trace 接手；資源用量全部正常而程式回了錯的轉址目標時，這一層的每個數字都不會變，這一段由使用者路徑的合成監控比對回應內容接手。監控程式裝在哪裡也決定它量得到什麼，這也屬於檢查範圍盲區：裝在虛擬機裡的 node_exporter 量的是虛擬機，實體主機的 CPU 負載不在它的量測範圍裡。一台主機上把整套堆疊接起來的做法，見 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/)。

## 應用層訊號：請求指標、log 與 trace

應用層訊號記錄使用者的請求是否成功、花了多久，以及某一筆請求錯在哪一段：請求指標記錄前兩項，log、trace 與錯誤追蹤用來找出錯在哪一段。**請求指標**是每個端點的請求率、錯誤率與耗時分布，這三個維度合稱 [RED Method](/backend/knowledge-cards/red-method/)；耗時記成 [histogram](/backend/knowledge-cards/histogram/)（依耗時區間計數的指標），才能把多個實例彙總之後再算 p95、p99 這類 [percentile](/backend/knowledge-cards/percentile/)。**log** 記下每一筆請求與錯誤的細節，用來還原一次事件的經過。**trace** 把一筆請求經過的每個服務串成一條路徑，用來找出慢或錯在哪一段。**錯誤追蹤**（Sentry 這類）把程式丟出的例外依堆疊分組計數，新的例外出現時通知，它也以自己的管道通知，不經過告警鏈。服務的可靠性目標（[SLO](/backend/knowledge-cards/sli-slo/)）也從這一層量：「每 30 天內 99.9% 的轉址請求在 200 毫秒內成功」量的就是請求指標。

應用層訊號的檢查範圍盲區是沒有抵達程式的請求。DNS 解析失敗、入口停掉、憑證過期時，失敗的請求根本沒有進到程式，不在錯誤率的分子，也不在分母：只有某些使用者的請求進不來時，錯誤率維持原樣；全部請求都進不來時，錯誤率算不出值，以錯誤率寫的告警規則不會成立。這一層對這種故障只留下請求率的下降，公開入口的故障本身由使用者路徑的合成監控接手。這一層同樣有讀取缺口：錯誤率升高只是一個數字，沒有規則讀它時不會讓任何人知道；log 也一樣，程式寫進 `docker logs` 的錯誤沒有程式讀它，log 彙整系統 Loki 的規則，或雲端業者的 log 指標篩選，可以把某一類錯誤訊息的出現次數變成告警。指標的類型與 SLI 的設計見 [4.2 metrics 與 SLI/SLO](/backend/04-observability/metrics-basics/) 與 [4.6 SLI 量測與 SLO 訊號設計](/backend/04-observability/sli-slo-signal/)，log 的欄位與查詢見 [4.1 log schema 與搜尋規劃](/backend/04-observability/log-schema/)，trace 見 [4.3 tracing 與 context link](/backend/04-observability/tracing-context/)，錯誤追蹤見 [Sentry](/backend/04-observability/vendors/sentry/)。

## 告警規則與分送

告警規則與分送決定哪些狀況要有人立刻處理、通知送給誰。元件指標與應用層訊號的讀取缺口由這一層接手：Prometheus 定期評估規則（例如「5 分鐘內錯誤率超過 1%」「某台主機 5 分鐘沒讀到資料」），成立的告警送到 Alertmanager，由 Alertmanager 分組（同一台主機的同一種告警合成一則）、[抑制](/backend/knowledge-cards/alert-inhibition/)（主機飽和時，壓下主機飽和造成的各服務變慢告警）、依嚴重度送到手機推播、email 或聊天工具。雲端業者的告警（CloudWatch Alarms 這類）是同一層的另一種實作。規則優先寫在使用者感受得到的症狀上（[Symptom-Based Alert](/backend/knowledge-cards/symptom-based-alert/)），每一則告警連到一份處理步驟（[runbook](/backend/knowledge-cards/runbook/)）。

告警規則的評估、Alertmanager（或業者的告警服務）與通知管道這一串，下文稱**告警鏈**。告警鏈的位置盲區是它自己：Prometheus 或 Alertmanager 與服務共用的依賴（主機、叢集、雲端帳號）停掉時，結果是沒有告警，而沒有告警與一切正常，在收件的人看來沒有差別，由失效域以外的心跳監看接手。告警鏈另有一種故障是讀取缺口：通知管道的網址寫錯、收件端拒收時，沒有任何共用的依賴停掉，規則照常成立，只是通知送不出去，由告警鏈的監看那一層的送失敗訊號接手。告警送出之後沒有人回應時要轉給誰屬於值班流程，不在告警鏈裡，見 [Escalation Policy](/backend/knowledge-cards/escalation-policy/)；升級路徑的演練見 [8.6 演練與值班能力建設](/backend/08-incident-response/drills-and-oncall-readiness/)。告警的設計與噪音控制見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)，主機過載時各服務一起告警的處理見 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)，Alertmanager 的路由與通知管道見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/)。

## 告警鏈的監看：心跳與通知失敗

告警鏈的監看確認告警鏈（告警規則的評估、Alertmanager 或業者的告警服務，以及通知管道）仍在運作，而且它的通知送得出去。告警鏈停掉時發不出任何訊息，所以監看要反過來做：告警鏈每隔固定時間對一個心跳監看服務送一次心跳，心跳監看服務在時限內沒收到就自己通知人，這叫 [Dead Man's Switch（心跳監看）](/backend/knowledge-cards/dead-mans-switch/)。Prometheus 上的做法是一條永遠成立的告警規則（`Watchdog`），Alertmanager 定期把它送到 healthchecks 這類心跳監看服務。監看要證明兩件事：心跳證明評估規則的程式還在跑，送失敗的訊號證明通知送得出去。告警鏈是雲端業者的告警或一支寄信的 cron 腳本時，要證明的也是這兩件事，做法依工具而不同，本篇不展開各家工具。從失效域以外送來的這類訊號叫 [Out-of-Band Signal（頻外訊號）](/backend/knowledge-cards/out-of-band-signal/)。

心跳只證明送心跳的那一條路通，人收告警的通知管道壞掉時心跳照常送達，所以通知送失敗另外要有一個訊號：Alertmanager 送失敗時遞增 `alertmanager_notifications_failed_total` 這個計數器，以這個計數器寫的告警規則，把送失敗這件事送到心跳監看服務的另一個檢查項目，由心跳監看服務通知人。做法見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/) 的〈通知送不出去的偵測〉。心跳監看服務通知人的管道要與告警鏈的通知管道分開（不同的推播服務或不同的收件方式）：兩者共用同一個推播服務時，那個服務停掉，心跳監看服務對送失敗發出的那一則通知也從同一條管道送不出去。

這一層接手告警鏈的位置盲區，所以它成立的條件是心跳監看服務在服務的失效域以外：它和告警鏈跑在同一台主機、同一個叢集上時，那個依賴停掉兩者一起停，沒有人通知。它自己的通知管道也要在失效域以外：通知不經過被監看的那台主機，也不寄到被監看服務網域底下的信箱，那個網域過期時通知一起收不到。通知管道的條件適用於每一個自己發通知的觀察者，包括合成監控服務與 Gatus 這類探測工具；位置的條件只適用於負責接手位置盲區的觀察者，服務網路內的探測照定義跑在服務網路裡。觀察者的位置要怎麼選（第三方服務、另一個業者的主機、兩台主機互相監看）見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)，healthchecks 的接法與停機演練見 [第三方心跳監看與外部探測服務](/backend/04-observability/vendors/prometheus/external-heartbeat-and-probe-services/)，觀測系統與服務在事故中一起退化的其他情形見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)。

## 使用者路徑的合成監控

使用者路徑這一層從使用者所在的位置檢查三件事：請求能否從外面到達服務、回應的狀態碼與內容是否符合預期、使用者實際感受到的耗時。[Synthetic Monitoring（合成監控）](/backend/knowledge-cards/synthetic-monitoring/)以排程主動發請求、模擬使用者；探測端放在哪裡決定它量得到什麼，這一層要求探測端在服務的失效域以外、在使用者所在的網路：解析公開網域、經過公開入口，檢查回應的狀態碼與內容。比對內容讓它接得住回應錯誤而狀態碼正常的故障：打一條已知目標的測試短網址，比對回應的 `Location` 標頭。服務網路內的探測與應用層訊號都看不到的公開入口故障，由它接手；主機整台停掉時，合成監控是少數還在運作、會發出通知的觀察者。

真實使用者監測（RUM，real user monitoring）是這一層的另一種資料來源：資料從使用者的瀏覽器或 App 蒐集，記錄實際請求的耗時與錯誤，量到的是各地區、各種裝置的分布。合成監控只量它固定走的那幾條路徑，而合成監控在沒有使用者的時段也有資料；RUM 在沒有使用者的時段沒有資料。

使用者路徑這一層的檢查範圍盲區是服務的內部：合成監控知道使用者連不進來，不知道是 DNS、入口、主機還是程式壞掉，要回頭比對前面各層的訊號。三種觀察者並排時，哪一個失敗、哪一個正常，就指出失效落在哪一段：合成監控、心跳監看，以及一條服務網路內的探測，條件是它打合成監控打的同一個端點與操作（例如同一條測試短網址的轉址），而且直接打應用程式、不經過入口 Nginx。判讀表在 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/) 的〈心跳監看、外部探測與內部探測並排時的判讀〉，那張表的「外部探測」就是本篇的合成監控，「主機內部對同一功能的探測」就是上面那條服務網路內的探測；服務網路內的探測只打健康端點時，要另外加一條這樣的探測才能對表。判讀「從什麼時候開始」時另外要對照變更紀錄：部署、設定變更與功能開關切換的時間點，Grafana 的 annotation、Sentry 的 release 把它畫在同一條時間軸上。合成監控與 RUM 的定位、與後端 SLI 的整合見 [4.10 Client-side / Synthetic / RUM](/backend/04-observability/client-side-monitoring/)，合成監控服務的挑選條件見 [第三方心跳監看與外部探測服務](/backend/04-observability/vendors/prometheus/external-heartbeat-and-probe-services/)。

## 監控鏈共同的檢查範圍盲區

有幾類異常，在監控鏈的每一層都只留下正常範圍內的數字：業務停了、資料寫錯、排程工作與佇列的消費端沒跑、備份還原不回來、以竊取的帳號做的正常操作、非同步呼叫的第三方業者停掉、帳單失控；另有到期事件與同步呼叫的第三方依賴，各層的規則要等服務中斷才成立。這幾類是整條監控鏈共同的檢查範圍盲區，每一類要先定義的預期與檢查它的規則在 [4.0.1 監控鏈事前偵測不到的異常](/backend/04-observability/monitoring-outside-the-chain/)。

## 以監控鏈盤點一個服務的判讀依據

監控鏈的用途是盤點：把一個服務現有的每一種監控放到它所屬的那一層，逐層判讀缺口。判讀的依據是補上它要什麼：

- **檢查範圍盲區**：這一層沒有觀察者檢查那個對象，補的是一個觀察者：程式碼、探測設定，或一條檢查新對象的規則（例如以 `predict_linear` 推算幾天後寫滿、以上週同時段的數字判斷是否變少）。一層沒有觀察者、而它的檢查對象已經由另一層的觀察者涵蓋時，記為由那一層接手；元件由業者管理、沒有地方放自己的觀察者時，記為由業者提供；缺口的症狀已由另一層檢查、補它不划算時，也可以記為接受，並寫明接受的條件（例如「由探測涵蓋，前提是探測本身的缺口已補上」）。
- **位置盲區**：這一層有觀察者在檢查，而它跟服務共用一個依賴（主機、叢集、雲端帳號或區域、網路），那個依賴停掉時元件與觀察者一起停，補的是另一個失效域的位置；判讀時寫出是對哪一種失效。自己發通知的觀察者，它的通知管道經過的主機、帳號與網域也算進它共用的依賴。
- **讀取缺口**：觀察者有結果，而沒有規則讀它，或通知送不出去，補的是一條讀既有結果的規則、一條通知，或送失敗的偵測。只有自動重啟、沒有通知的，仍算讀取缺口。
- **訊號失真**：觀察者、位置與規則都在，而觀察者自己壞掉時沒有人知道，或規則的門檻與寫法讓結果不可信，補的是對觀察者本身的「讀不到它」規則，以及門檻與寫法的檢查。

跟服務共用失效域的觀察者（服務主機上的程式、同一個叢集裡的監控、同一個雲端帳號與區域裡的業者監控）全都有位置盲區，這一項統一由失效域以外的兩層接手，所以盤點時只在告警鏈的監看與使用者路徑這兩層判位置盲區，每一層只記還開著、沒有被別層接手的缺口。觀察者本身跑在另一個失效域時（例如另一台主機上的 Prometheus 經 VPN 讀取），記為這一層沒有主機停機的位置盲區；它沒有走公開入口，所以使用者路徑那一層的檢查範圍盲區仍然開著。

同一個補法有時同時對應監控鏈的一層與 4.0.1 的一類：佇列改以等待時間告警，既是元件指標那一層的告警寫法，也是 4.0.1〈排程工作與背景工作〉要的預期。記法是告警的寫法（門檻以筆數還是等待時間、以平均還是百分位數判斷）記在監控鏈那一層，業務上的預期（消費端多久沒處理算異常、確認信晚多久算太晚）記在 4.0.1 的那一類，兩處互相指向。

盤點的結果寫成一張表，每一列是監控鏈的一層，欄位是這一層現有的監控與判讀。表的實際樣子與補法見兩個案例：[4.0.2 以監控鏈盤點單機短網址服務](/backend/04-observability/monitoring-inventory-single-host/) 的觀察者全在一台主機上，失效域就是那台主機；[4.0.3 以監控鏈盤點 Kubernetes 上的電商 checkout](/backend/04-observability/monitoring-inventory-k8s-checkout/) 的監控跑在服務所在的叢集裡，失效域是叢集、雲端帳號與區域，而託管資料庫與第三方金流各自站在另一個失效域。

以層盤點只找得到監控鏈定義過的缺口；被盤點的服務特有的故障，要先列出它的失效模式或使用者旅程，再對回各層，見 [4.16 Observability Readiness Review](/backend/04-observability/observability-readiness-review/)（上線前由服務、平台與值班一起確認訊號足以支援事故判讀的審查流程）與 [單點故障盤點](/operations/06-high-availability/spof-inventory/)。事故之後發現的偵測缺口怎麼寫回成新的規則，見 [4.8 訊號治理閉環](/backend/04-observability/signal-governance-loop/)。

列失效模式時，負載超過容量要單獨列一條，因為它在各層呈現的結果不同：變慢由耗時分布與探測看到，請求失敗由錯誤率或入口的請求率看到，無回應與程序終止由自檢、探測逾時與重啟計數看到，停在失效（觸發消失、請求率回到平常之後仍不恢復）沒有任何一層直接看得到。各種結果的判斷標準、成因與看得到它的層見 [9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)。

還沒有任何監控的服務，第一步可以是失效域以外的合成監控：它只需要一個外部服務、不必先有其他任何一層，主機整台停掉時它也會通知；心跳監看要等告警鏈建好才有心跳可送。之後由內往外補，讓每一則告警指得出原因：容器健康檢查與服務網路內的探測見 [多容器服務的存活監看](/operations/04-service-health/multi-container-monitoring/)，Prometheus、exporter 與 Alertmanager 見 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/)，心跳監看與合成監控放到失效域以外見 [第三方心跳監看與外部探測服務](/backend/04-observability/vendors/prometheus/external-heartbeat-and-probe-services/)。第二台主機或第三方服務要先給哪一層、備份要放到哪裡，見 [小型服務的兩到三台主機配置](/operations/06-high-availability/small-service-host-layout/)。
