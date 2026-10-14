---
title: "4.0 服務端監控的分層：容器與程序的自檢、服務網路內的探測、元件指標、應用層訊號、告警規則與分送、告警鏈的監看與使用者路徑的合成監控，以及服務正常運作時仍會出的問題"
date: 2026-10-14
description: "以每一層監控回答的問題、看不到的範圍與接手的那一層，把服務端監控串成一條監控鏈，以及拿它盤點一個服務時怎麼判讀缺口的性質；另寫各層都正常時仍會出的問題：業務結果、到期事件、排程工作與備份、安全、第三方依賴與成本，各自的監看做法與承接的專章"
weight: -1
tags: ["backend", "observability", "monitoring", "alerting"]
---

這一篇把一個後端服務的監控，依每一層回答的問題排成一條鏈，說明每一層看不到的範圍由哪一層接手，以及有哪些問題在每一層都正常時仍會發生。範圍是跑在自己的主機或雲端上的服務；使用者端（行動 App、網頁、本機腳本）的事件蒐集是另一條路線，見 [監控實務指南](/monitoring/)。各層的做法與設定在連過去的專章裡，這一篇處理它們之間的關係。

例子是一台主機上以 Docker Compose 跑的短網址服務：入口 Nginx、後端程式、PostgreSQL 與 Valkey，各在一個容器裡。下文把主機、容器、資料庫、快取與入口這些組成服務的單位稱為**元件**，「層」只用來指監控的層。

## 一層監控回答的問題與它的盲區

每一種監控都是一個觀察者，站在某個位置、回答一個問題。容器的健康檢查回答「這個程序自己的端點回不回應」；Prometheus 讀取主機與各容器的數字，回答「這些元件用了多少資源」；心跳監看（告警系統定期送訊號到另一處，那一處沒收到就通知人）回答「告警系統還在不在運作」。同一個服務上的各種監控，差別在問題，也在觀察者的位置。

一個觀察者的盲區有兩種，各取一個名字，下文都用這兩個名字。**問題盲區**是它沒有在問的故障：容器的健康檢查從容器裡面打自己的端點，入口 Nginx 的路由寫錯時，使用者的請求進不來，而健康檢查照樣成功。**位置盲區**是連觀察者自己一起停掉的故障：觀察者與被觀察的元件共用同一台主機、同一個業者帳號或同一條網路時，那個共用的依賴停掉，觀察者跟著停，不會有人回報。這一組會一起停掉的依賴叫 [Failure Domain（失效域）](/backend/knowledge-cards/failure-domain/)。

盲區之外還有一種缺口，叫**讀取缺口**：觀察者看到了，而沒有任何程式讀它的結果、把它變成送到人手上的通知。Docker 把容器標成 `unhealthy`、程式的錯誤率升高，都只是一個狀態或一個數字，沒有程式讀它的時候，結果與沒看到相同。

服務端監控的各層就是為了這三種缺口疊起來的：一層的問題盲區，由問另一個問題的層接手；一層的位置盲區，由站在另一個失效域的層接手；各層的讀取缺口，由告警規則與分送接手。接手的不一定是緊接的那一層。下文把這一串稱為**監控鏈**，從離程序最近的自檢寫起，到站在失效域以外的使用者路徑合成監控為止，每一層寫它回答的問題、做法、盲區與接手的層。

## 容器與程序的自檢

自檢回答的問題是：這個程序自己還能不能回應。Docker 的 `HEALTHCHECK` 每隔一段時間在容器裡執行一條指令（例如請求自己的 `/healthz`），連續失敗幾次之後把容器標成 `unhealthy`。Kubernetes 由 kubelet 定期執行 [probe](/backend/knowledge-cards/probe/)：liveness 失敗時重啟容器，readiness 失敗時把它從接流量的名單拿掉，startup 在程序啟動完成之前暫停另外兩種。systemd 的 `WatchdogSec` 要求程序定期回報，沒有回報就把服務標成失敗並終止它，unit 另外設了 `Restart=on-watchdog`（或 `on-failure`、`always`）才會重啟。

自檢的問題盲區是程序以外的路徑：它在程序所在的容器裡測，別的容器連不連得到它、入口的路由對不對都不在它的問題裡。它的位置盲區是主機：它和程序在同一台主機上，主機停掉時一起停。它還有讀取缺口：單機的 Docker（Swarm 模式以外）把容器標成 `unhealthy` 之後不會自己重啟它，也不會通知任何人。檢查要探到多深（只回 200，還是連資料庫也查）是端點的設計問題，見 [Health check endpoint 設計](/operations/04-service-health/health-check-endpoint/)；Docker 健康狀態的 `starting`、`healthy`、`unhealthy` 與 `unhealthy` 之後由誰處理，見 [容器的健康檢查](/operations/04-service-health/container-healthcheck/)；Kubernetes 的 liveness、readiness 與 startup 探針各自宣告什麼，見 [Liveness 與 Readiness](/operations/04-service-health/liveness-vs-readiness/)。

## 服務網路內的探測

服務網路內的探測回答的問題是：從服務的程序以外發請求，打不打得通。Gatus、Uptime Kuma 或 Prometheus 的 blackbox_exporter 跑在另一個容器裡，以服務名稱對各服務發 HTTP 請求或 TCP 連線；打入口 Nginx 的那一條探測，順便確認入口的路由是通的。自檢的問題盲區「別人連不連得到它」由它接手。

它的問題盲區有兩種。一種是公開入口，這裡指使用者的請求進來的那一段：公開網域解析出的位址、主機對外的連接埠與防火牆、入口 Nginx 的 HTTPS 監聽與 TLS 憑證。服務網路內的探測以服務名稱在內部網路直接連到 Nginx，不經過這一段，所以網域設錯、憑證過期、雲端業者的網路故障它量不到，由使用者路徑的合成監控接手。另一種是原因：它只知道一條路徑成功或失敗、回應花了多久，請求變慢是因為主機的 CPU 不夠、資料庫的連線用完還是程式本身，它分不出來，由元件指標接手。它的位置盲區是主機，主機停掉時它跟著停。站內 [多容器服務的存活監看](/operations/04-service-health/multi-container-monitoring/)、[4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/) 與 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/) 都把這一種叫「外部探測」，那裡的「外部」是相對於服務的程序，與使用者路徑的合成監控那種相對於失效域的外部是兩件事；探測的工具選擇與 TCP 檢查的限制在多容器服務那一篇。

## 元件指標：exporter 從程式外讀取的數字

元件指標回答的問題是：主機、容器與各服務用了多少資源、處理了多少請求，以及這些數字在一段時間裡怎麼變化。Prometheus 每隔固定時間讀取各元件的 [exporter](/backend/knowledge-cards/prometheus-exporter/)（把一個元件的狀態轉成 Prometheus 指標的程式）：node_exporter 給主機的 CPU、記憶體、磁碟與網路，cAdvisor 給每個容器的用量，資料庫、快取與 Nginx 各有自己的 exporter 給連線數、查詢量與請求總數。服務網路內的探測分不出的原因由這一層接手：探測變慢的同時主機的 load（系統負載平均）超過核心數，原因在主機；只有 PostgreSQL 的連線數頂到上限，原因在資料庫。逐個元件檢查資源的使用率、飽和度與錯誤，叫 [USE Method](/backend/knowledge-cards/use-method/)。

這一層與下一節應用層訊號的分界是訊號由誰產生：元件指標由 exporter 從程式外讀取，應用層訊號由服務的程式自己逐端點記錄。入口 Nginx 的請求總數落在這一層，每個端點的錯誤率與耗時落在應用層；4.26 把入口與應用程式的請求量合稱流量監控，對應的是這兩層的交界。

元件指標的問題盲區是個別的請求與答案的對錯：指標是彙總後的數字，一個使用者的某一次請求為什麼失敗、經過了哪些服務，它沒有記錄；資源用量全部正常而程式回了錯的轉址目標時，這一層的每個數字都不會變。監控程式裝的位置也會限制它：裝在虛擬機裡的 node_exporter 看不到實體主機的 CPU 負載。各元件的訊號從哪裡收、用哪一個 exporter、監控程式所在位置看不到的範圍，見 [4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/)；一台主機上把整套堆疊接起來的做法，見 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/)。

## 應用層訊號：請求指標、log 與 trace

應用層訊號由服務的程式自己產生，回答的問題是：使用者的請求成功了沒有、花了多久，以及某一筆請求錯在哪一段。請求指標回答成功了沒有與花了多久，log 與 trace 回答錯在哪一段。**請求指標**是每個端點的請求率、錯誤率與耗時分布，這三個維度合稱 [RED Method](/backend/knowledge-cards/red-method/)；耗時記成 histogram（依耗時區間計數的指標），才能把多個實例彙總之後再算 p95、p99。**log** 記下每一筆請求與錯誤的細節，用來還原一次事件的經過。**trace** 把一筆請求經過的每個服務串成一條路徑，用來找出慢或錯在哪一段。服務的可靠性目標（SLO）也從這一層量：「每 30 天內 99.9% 的轉址請求在 200 毫秒內成功」量的就是請求指標。

應用層訊號的問題盲區是沒有抵達程式的請求。DNS 解析失敗、入口停掉、憑證過期時，失敗的請求根本沒有進到程式，不在錯誤率的分子，也不在分母，錯誤率維持原樣；請求全部停掉時錯誤率算不出值，以它寫的告警規則不會成立。反映這種故障的只有請求率的下降，而公開入口的故障本身由使用者路徑的合成監控接手。這一層同樣有讀取缺口：錯誤率升高只是一個數字，沒有規則讀它時不會讓任何人知道。指標的類型與 SLI 的設計見 [4.2 metrics 與 SLI/SLO](/backend/04-observability/metrics-basics/) 與 [4.6 SLI 量測與 SLO 訊號設計](/backend/04-observability/sli-slo-signal/)，log 的欄位與查詢見 [4.1 log schema 與搜尋規劃](/backend/04-observability/log-schema/)，trace 見 [4.3 tracing 與 context link](/backend/04-observability/tracing-context/)。

## 告警規則與分送

告警回答的問題是：哪些狀況要有人立刻處理，要送給誰。自檢的狀態、元件指標與應用層訊號只是狀態、數字與紀錄，各層的讀取缺口由這一層接手：Prometheus 定期評估規則（例如「5 分鐘內錯誤率超過 1%」「某台主機 5 分鐘沒讀到資料」），成立的告警送到 Alertmanager，由它分組（同一台主機的同一種告警合成一則）、抑制（主機飽和時壓下它造成的各服務變慢）、依嚴重度送到手機推播、email 或聊天工具。Gatus 這類探測工具自己也能發通知，而規則、分組與送給誰集中寫在這一層。規則優先寫在使用者感受得到的症狀上（[Symptom-Based Alert](/backend/knowledge-cards/symptom-based-alert/)），每一則告警連到一份處理步驟（[runbook](/backend/knowledge-cards/runbook/)）。

告警規則的評估、Alertmanager 與通知管道這一串，下文稱**告警鏈**。告警鏈的位置盲區是它自己：Prometheus 或 Alertmanager 停了，結果是沒有告警；通知管道的網址寫錯了，結果也是收不到告警。沒有告警與一切正常，在收件的人看來沒有差別。告警送出之後沒有人回應時要轉給誰，是值班流程的問題，不在告警鏈裡，見 [Escalation Policy](/backend/knowledge-cards/escalation-policy/)；升級路徑的演練見 [8.6 演練與值班能力建設](/backend/08-incident-response/drills-and-oncall-readiness/)。告警的設計與噪音控制見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)，主機過載時各服務一起告警的處理見 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)，Alertmanager 的路由與通知管道見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/)。

## 告警鏈的監看：心跳與通知失敗

告警鏈的監看回答的問題是：告警鏈還在運作嗎、它的通知送得出去嗎。告警鏈停掉時發不出任何訊息，所以監看要反過來做：告警鏈每隔固定時間對一個心跳監看服務送一次心跳，心跳監看服務在時限內沒收到就自己通知人，這叫 [Dead Man's Switch（心跳監看）](/backend/knowledge-cards/dead-mans-switch/)。Prometheus 上的做法是一條永遠成立的告警規則（`Watchdog`），Alertmanager 定期把它送到 healthchecks 這類心跳監看服務。心跳只證明送心跳的那一條路通，人收告警的通知管道壞掉時心跳照常送達，所以通知送失敗另外要有一個訊號：Alertmanager 送失敗時遞增 `alertmanager_notifications_failed_total`，以它寫的告警規則把這件事送到心跳監看服務的另一個檢查項目，由心跳監看服務通知人，做法見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/) 的〈通知送不出去的偵測〉。

這一層接手告警鏈的位置盲區，所以它成立的條件是心跳監看服務在服務的失效域以外：它和告警鏈跑在同一台主機上時，主機停掉兩者一起停，沒有人通知。它自己的通知管道也要在失效域以外：通知不經過被監看的那台主機，也不寄到被監看服務網域底下的信箱，那個網域過期時通知一起收不到。觀察者的位置要怎麼選（第三方服務、另一個業者的主機、兩台主機互相監看）見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)，healthchecks 的接法與停機演練見 [第三方心跳監看與外部探測服務](/backend/04-observability/vendors/prometheus/external-heartbeat-and-probe-services/)，觀測系統與服務在事故中一起退化的情形見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)。

## 使用者路徑的合成監控與真實使用者監測

使用者路徑這一層回答的問題是：使用者從外面連得到服務嗎、他們實際感受到多慢。[Synthetic Monitoring（合成監控）](/backend/knowledge-cards/synthetic-monitoring/)以排程主動發請求、模擬使用者；探測端放在哪裡決定它量得到什麼，這一層要求探測端在服務的失效域以外、在使用者所在的網路：解析公開網域、經過公開入口，檢查回應的狀態碼與內容。服務網路內的探測與應用層訊號都看不到的公開入口故障，由它接手；主機整台停掉時，它是少數還在運作、會發出通知的觀察者。真實使用者監測（RUM，real user monitoring）的資料從使用者的瀏覽器或 App 蒐集，記錄實際請求的耗時與錯誤，量到的是各地區、各種裝置的分布；合成監控只量它固定走的那幾條路徑，而沒有使用者的時段也有資料。

使用者路徑這一層的問題盲區是服務的內部：合成監控知道使用者連不進來，不知道是 DNS、入口、主機還是程式壞掉，要回頭比對前面各層的訊號。合成監控、心跳監看與主機內部的探測三者並排時，哪一個失敗、哪一個正常，就指出失效落在哪一段；判讀表在 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)，那張表的內部探測要打合成監控打的同一個功能、不經過入口，所以只探健康端點的 Gatus 不能直接拿來對表，要另外加一條。合成監控與 RUM 的定位、與後端 SLI 的整合見 [4.10 Client-side / Synthetic / RUM](/backend/04-observability/client-side-monitoring/)，合成監控服務的挑選條件見 [第三方心跳監看與外部探測服務](/backend/04-observability/vendors/prometheus/external-heartbeat-and-probe-services/)。

## 服務正常運作時仍會出的問題

監控鏈各層偵測的都是服務偏離正常運作的訊號：程序沒回應、請求失敗、資源耗盡、告警鏈中斷。下面這幾類問題發生時，它們在各層留下的是正常範圍內的數字（某一類請求的請求率下降、某一類對外呼叫失敗），每個容器都健康、每個探測都成功、資源用量正常，沒有一層的規則會把它判成異常。監看它們要另外定義「預期會看到什麼」，再監看它有沒有出現。

**業務結果。** 程式回應正常而業務停了：付款頁的前端腳本壞掉、按鈕按不下去時，後端收不到結帳請求，錯誤率維持正常，而結帳端點的請求率與訂單數歸零；短網址的建立頁被一次改版拿掉了送出按鈕時，轉址照常運作，新建的短網址數歸零。請求率的下降在應用層看得到，而沒有規則把「變少」當成異常。監看的做法是挑幾個代表業務在運作的數字（每 10 分鐘的訂單數、新建的短網址數），和上週同一時段比較，低於預期一定比例時告警；流量本來就有起伏的服務，以統計基準判斷偏離，見 [4.14 Anomaly Detection](/backend/04-observability/anomaly-detection/)。業務儀表板的定位見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)。

**到期事件。** TLS 憑證、網域、API 金鑰與付費方案在到期之前一切正常，到期那一刻服務中斷。監看的做法是記下到期時間、在剩下一段天數時告警。憑證的到期時間由走公開網址的探測取得：blackbox_exporter 對 HTTPS 目標探測時輸出 `probe_ssl_earliest_cert_expiry`（最早到期那一張憑證的到期時間，Unix 時間戳），規則以它減去現在時間判斷剩下幾天；Gatus 的探測可以加 `[CERTIFICATE_EXPIRATION]` 條件。網域的到期日不在 TLS 握手裡，要從註冊商或 RDAP（WHOIS 的後繼協定）查，部分國碼網域（例如 .io、.jp）沒有 RDAP，仍要查 WHOIS；Gatus 的 `[DOMAIN_EXPIRATION]` 條件代為查詢。自動續期也要監看：續期程序失敗時只在它自己的日誌留下錯誤，不會通知任何人，直到憑證過期。續期與輪替的流程見 [Certificate Rotation and Renewal](/backend/knowledge-cards/certificate-rotation-renewal/)。

**排程工作與備份。** 每晚的備份、報表、資料清理不在請求路徑上，它們沒跑的時候沒有任何請求失敗。監看的做法與告警鏈的心跳相同：工作完成時對心跳監看服務送一次心跳，沒按時送到就通知，見 [Dead Man's Switch（心跳監看）](/backend/knowledge-cards/dead-mans-switch/)。備份另有一項要驗：備份工作成功只證明檔案寫出去了，還原得回來要實際還原一次才知道，見 [備份與還原的地基](/going-live/backup-restore-basics/)。

**安全。** 攻擊者以竊取的帳號登入、提升權限、匯出資料時，每一個請求在元件指標與請求指標上都是正常的請求。監看的對象是行為：登入失敗的次數與來源、權限變更、管理操作、異常的大量讀取，資料來源是稽核紀錄（[Audit Log](/backend/knowledge-cards/audit-log/)）。稽核紀錄的邊界見 [4.12 Audit Log 邊界與 PII 治理](/backend/04-observability/audit-log-governance/)，偵測規則的涵蓋範圍與誤報成本見 [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)。

**第三方依賴。** 金流、簡訊、email、第三方登入的業者停掉時，結果依呼叫的方式而不同。同步呼叫的依賴（金流、第三方登入）停掉時，使用者的請求跟著失敗，錯誤率會上升，而從錯誤率看不出是哪一家；非同步呼叫的依賴（寄信、簡訊、送出的 webhook）停掉時，使用者的請求照常成功，每一層都看不到。監看的做法是把對每一個外部依賴的呼叫各自記成請求指標（成功率、耗時），失敗率升高時就知道是哪一家，同時訂閱業者的狀態頁。依賴關係的盤點見 [4.13 Service Topology 與 Dependency Map](/backend/04-observability/service-topology/)，依賴方停掉時的處理見 [8.15 Vendor / 第三方依賴事故處理](/backend/08-incident-response/vendor-dependency-incident/)。

**成本。** 自動擴充失控、一支程式反覆重試、log 量暴增，服務照常運作而帳單成倍增加。雲端業者的預算告警是最基本的監看；要分辨成本上升是因為流量還是因為效率變差，把每個服務的成本和它的流量並排看，見 [9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/) 的〈Cost dashboard〉。監控系統本身的成本見 [4.7 Cardinality 治理與成本邊界](/backend/04-observability/cardinality-cost-governance/)。

## 以分層盤點一個服務的監控

監控鏈的用途是盤點：把一個服務現有的每一種監控放到它回答的那一層，就看得出每一層的三種缺口哪裡還開著：哪一層沒有觀察者在問那個問題（問題盲區）、哪一層的觀察者與服務共用失效域（位置盲區）、哪一層的結果沒有規則讀（讀取缺口）。服務正常運作時仍會出的那幾類問題，則逐類看有沒有定義「預期會看到什麼」。

以入口 Nginx、後端程式、PostgreSQL 與 Valkey 跑在同一台主機上的短網址服務為例，假設它接了容器健康檢查、同一台主機上的 Gatus、Prometheus 與主機、容器、資料庫、快取與入口的 exporter、Alertmanager 推播到手機，以及跑在同一台主機上的心跳監看服務：

| 監控鏈的層           | 這個服務用的元件                                       | 判讀                                                                          |
| -------------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------- |
| 容器與程序的自檢     | 每個容器的 Docker 健康檢查                             | 有讀取缺口：`unhealthy` 沒有規則讀它，服務壞掉由 Gatus 的探測另外發現         |
| 服務網路內的探測     | 同一台主機上的 Gatus                                   | 有；公開入口是它的問題盲區，由使用者路徑那一層接手                            |
| 元件指標             | Prometheus 與主機、容器、資料庫、快取、入口的 exporter | 有                                                                            |
| 應用層訊號           | 無（只有 Gatus 量到的探測耗時）                        | 問題盲區：程式沒有輸出請求指標，每個端點的錯誤率與耗時分布沒有任何觀察者在問  |
| 告警規則與分送       | Prometheus 規則與 Alertmanager，推播到手機             | 有                                                                            |
| 告警鏈的監看         | 心跳監看服務，跑在同一台主機上                         | 位置盲區：機制能運作，而主機停掉時它跟著停                                    |
| 使用者路徑的合成監控 | 無                                                     | 位置盲區：這一層的問題只有站在失效域以外才問得到，同一台主機上的 Gatus 補不上 |

表上的缺口有兩種性質，補法不同。應用層訊號是問題盲區：這個服務的程式沒有輸出請求指標，補的是程式碼。告警鏈監看與使用者路徑是位置盲區：心跳的機制已經能運作，合成監控的探測工具同一台主機上也有，缺的是一個不和服務共用失效域的地方，補的是另一個業者的服務或主機；失效域以外的觀察者補上之前，主機整台停掉這個故障沒有任何一層會通知。

服務正常運作時仍會出的問題同樣逐類查。這個服務沒有監看憑證到期、沒有監看每晚的資料庫備份。憑證到期要一條走公開網址的探測：讓 Gatus 對公開網域加一條探測並設 `[CERTIFICATE_EXPIRATION]` 條件，或加 blackbox_exporter 的一條規則；Gatus 跑在服務主機上，所以主機停掉時這條探測跟著停，而主機停掉本身由失效域以外的觀察者負責。備份是工作完成時對心跳監看服務送一次心跳；心跳監看服務目前跟服務在同一台主機上，搬到失效域以外之後，備份的心跳也一起受保護。

第二台主機或第三方服務要先給哪一層、備份要放到哪裡，見 [小型服務的兩到三台主機配置](/operations/06-high-availability/small-service-host-layout/)；上線前由服務、平台與值班一起確認訊號足以支援事故判讀的審查流程，見 [4.16 Observability Readiness Review](/backend/04-observability/observability-readiness-review/)。
