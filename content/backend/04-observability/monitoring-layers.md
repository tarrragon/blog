---
title: "4.0 服務端監控的分層：容器自檢、服務網路內的探測、資源與流量指標、應用層訊號、告警分送、告警鏈的監看與使用者路徑的合成監控，以及監控鏈以外的問題"
date: 2026-10-14
description: "以每一層監控回答的問題與它看不到的範圍，把服務端監控串成一條監控鏈：容器與程序的自檢、服務網路內的探測、資源與流量指標、應用層的請求指標與 log、trace，告警規則與分送，失效域以外的告警鏈監看與使用者路徑的合成監控；以及服務正常運作時仍會出的問題：業務結果、到期事件、排程工作與備份、安全、第三方依賴與成本。各層連到承接它的專章"
weight: -1
tags: ["backend", "observability", "monitoring", "alerting"]
---

這一篇把一個後端服務的監控，依每一層回答的問題排成一條鏈，說明每一層看不到的範圍由哪一層接手，以及有哪些問題落在這條鏈以外。範圍是跑在自己的主機或雲端上的服務；使用者端（行動 App、網頁、本機腳本）的事件蒐集是另一條路線，見 [監控實務指南](/monitoring/)。各層的做法與設定在連過去的專章裡，這一篇處理它們之間的關係。

## 一層監控回答的問題與它看不到的範圍

每一種監控都是一個觀察者，站在某個位置、回答一個問題。容器的健康檢查回答「這個程序自己的端點回不回應」，Prometheus 讀取 exporter 回答「這一層用了多少資源」，心跳監看回答「告警系統還在不在」。同一個服務上的監控，差別在問題，也在觀察者的位置。

一個觀察者看不到的範圍有兩種來源。**問題以外的故障**：它沒有在問那件事。容器的健康檢查從容器裡面打自己的端點，入口 Nginx 的路由寫錯時，使用者的請求進不來，而健康檢查照樣成功。**連它自己一起停掉的故障**：觀察者與被觀察的對象共用同一台主機、同一個業者帳號或同一條網路時，那個共用的依賴停掉，觀察者跟著停，不會有人回報。這一組會一起停掉的依賴叫 [Failure Domain（失效域）](/backend/knowledge-cards/failure-domain/)。

服務端監控的各層就是照這兩種盲區排出來的：前一層看不到的範圍，由下一層接手。下文把這一串稱為**監控鏈**，從離程序最近的一層往外走，每一層寫它回答的問題、它的做法、它看不到的範圍，以及接手的那一層。

例子是一台主機上以 Docker Compose 跑的短網址服務：入口 Nginx、後端程式、PostgreSQL 與 Valkey，各在一個容器裡。

## 容器與程序的自檢

自檢回答的問題是：這個程序自己還能不能回應。Docker 的 `HEALTHCHECK` 每隔一段時間在容器裡執行一條指令（例如請求自己的 `/healthz`），連續失敗幾次之後把容器標成 `unhealthy`；Kubernetes 的 liveness 與 readiness [probe](/backend/knowledge-cards/probe/) 由 kubelet 定期請求，liveness 失敗時重啟容器，readiness 失敗時把它從接流量的名單拿掉；systemd 的 `WatchdogSec` 要求程序定期回報，沒有回報就重啟它。

自檢看不到三件事。它在程序所在的容器裡測，別的容器連不連得到它、入口的路由對不對都不在問題裡。它的結果多半只改變一個狀態：單機的 Docker（Swarm 模式以外）把容器標成 `unhealthy` 之後不會自己重啟它，也不會通知任何人，服務壞掉這件事要由別的監控另外發現。它和程序在同一台主機上，主機停掉時一起停。檢查要探到多深（只回 200，還是連資料庫也查）是端點的設計問題，見 [Health check endpoint 設計](/operations/04-service-health/health-check-endpoint/)；Docker 健康狀態的三個值、`unhealthy` 之後由誰處理，見 [容器的健康檢查](/operations/04-service-health/container-healthcheck/)；Kubernetes 三種探針各自宣告什麼，見 [Liveness 與 Readiness](/operations/04-service-health/liveness-vs-readiness/)。

## 服務網路內的探測

服務網路內的探測回答的問題是：從服務的程序以外發請求，打不打得通。Gatus、Uptime Kuma 或 Prometheus 的 blackbox_exporter 跑在另一個容器裡，以服務名稱對各服務發 HTTP 請求或 TCP 連線，經過入口的那一條順便確認入口與路由是通的。它接住了自檢看不到的「別人連不連得到它」。

它看不到的範圍有三種。它從服務所在的網路裡面發請求，不經過公開的 DNS、公開入口與 TLS 憑證，所以網域設錯、憑證過期、雲端業者的網路故障它量不到，這一段由使用者路徑的合成監控接手。它只量它探測的那幾條路徑、只知道成功或失敗與回應時間，請求變慢是因為主機的 CPU 不夠、資料庫的連線用完還是程式本身，它分不出來，這一段由資源與流量指標接手。它跟服務在同一台主機上，主機停掉時跟著停。站內 [多容器服務的存活監看](/operations/04-service-health/multi-container-monitoring/) 把這一種叫「外部探測」，那裡的「外部」是相對於服務的程序，與本篇最後一層、相對於失效域的外部是兩件事；探測的工具選擇與 TCP 檢查的限制都在那一篇。

## 資源與流量指標

資源與流量指標回答的問題是：每一層用了多少資源、收到多少流量，以及這些數字在一段時間裡怎麼變化。Prometheus 每隔固定時間讀取各層的 [exporter](/backend/knowledge-cards/prometheus-exporter/)：node_exporter 給主機的 CPU、記憶體、磁碟與網路，cAdvisor 給每個容器的用量，資料庫、快取與 Nginx 各有自己的 exporter 給連線數、查詢量與請求量。這一層把探測分不出的原因接住了：探測變慢的同時主機的 load 超過核心數，原因在主機；只有 PostgreSQL 的連線數頂到上限，原因在資料庫。逐層檢查資源的使用率、飽和度與錯誤，叫 [USE Method](/backend/knowledge-cards/use-method/)。

它看不到個別的請求。指標是彙總後的數字，一個使用者的某一次請求為什麼失敗、經過了哪些服務，它沒有記錄；它也看不到使用者拿到的答案對不對，資源用量全部正常而程式回了錯的轉址目標，這一層的每個數字都不會變。監控裝在哪一層也會限制它：裝在虛擬機裡的 node_exporter 看不到實體主機的 CPU 負載。各層的訊號從哪裡收、用哪一個 exporter、監控所在層看不到的範圍，見 [4.26 單機容器服務的流量與資源監控](/backend/04-observability/host-traffic-resource-monitoring/)；一台主機上把整套堆疊接起來的做法，見 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/)。

## 應用層訊號：請求指標、log 與 trace

應用層訊號由服務的程式自己產生，回答的問題是：使用者的請求成功了沒有、花了多久，以及某一筆請求錯在哪一段。請求指標回答成功了沒有與花了多久，log 與 trace 回答錯在哪一段。**請求指標**是每個端點的請求率、錯誤率與耗時分布，這三個維度合稱 [RED Method](/backend/knowledge-cards/red-method/)，耗時要記成 histogram 才算得出 p95、p99；它與資源指標的差別在量的對象，資源指標量機器，請求指標量使用者的請求。**log** 記下每一筆請求與錯誤的細節，用來還原一次事件的經過。**trace** 把一筆請求經過的每個服務串成一條路徑，用來找出慢或錯在哪一段。服務的可靠性目標（SLO）也從這一層量：「99.9% 的轉址請求在 200 毫秒內成功」量的就是請求指標。

這一層看不到沒有抵達程式的請求：DNS 解析失敗、入口停掉、憑證過期時，請求根本沒有進到程式，程式沒有任何 log 與指標可以記，錯誤率反而因為請求變少而看起來正常。它也只負責記錄，沒有人看的時候，錯誤率升高不會讓任何人知道。指標的類型與 SLI 的設計見 [4.2 metrics 與 SLI/SLO](/backend/04-observability/metrics-basics/) 與 [4.6 SLI 量測與 SLO 訊號設計](/backend/04-observability/sli-slo-signal/)，log 的欄位與查詢見 [4.1 log schema 與搜尋規劃](/backend/04-observability/log-schema/)，trace 見 [4.3 tracing 與 context link](/backend/04-observability/tracing-context/)。

## 告警規則與分送

告警回答的問題是：哪些狀況要有人立刻處理，要送給誰。前面各層的訊號只是數字與紀錄，告警規則把它們變成需要動作的事件：Prometheus 定期評估規則（例如「5 分鐘內錯誤率超過 1%」「某台主機 5 分鐘沒讀到資料」），成立的告警送到 Alertmanager，由它分組（同一台主機的同一種告警合成一則）、抑制（主機飽和時壓下它造成的各服務變慢）、依嚴重度送到手機推播、email 或聊天工具。規則優先寫在使用者感受得到的症狀上（[Symptom-Based Alert](/backend/knowledge-cards/symptom-based-alert/)），每一則告警連到一份處理步驟（[runbook](/backend/knowledge-cards/runbook/)）。

告警系統看不到自己停掉。Prometheus 或 Alertmanager 停了、通知管道的網址寫錯了，結果都是沒有告警，而沒有告警與一切正常在收件的人看來完全一樣。告警送出之後沒有人回應時要升級給誰，是值班流程的問題，不在告警系統裡，見 [8.6 演練與值班能力建設](/backend/08-incident-response/drills-and-oncall-readiness/)。告警的設計與噪音控制見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)，主機過載時各服務一起告警的處理見 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)，Alertmanager 的路由與通知管道見 [Alertmanager 的通知管道](/backend/04-observability/vendors/prometheus/alertmanager-notification-channels/)。

## 告警鏈的監看：心跳與通知失敗

告警鏈的監看回答的問題是：告警系統還在運作嗎、它的通知送得出去嗎。告警系統停掉時發不出任何訊息，所以監看要反過來做：告警系統每隔固定時間對一個監看服務送一次心跳，監看服務在時限內沒收到就自己通知人，這叫 [Dead Man's Switch（心跳監看）](/backend/knowledge-cards/dead-mans-switch/)。Prometheus 上的做法是一條永遠成立的告警規則（`Watchdog`），Alertmanager 定期把它送到 healthchecks 這類監看服務。心跳只證明送心跳的那一條路通，人收告警的通知管道壞掉時心跳照常送達，所以通知送失敗另外要有一個訊號：Alertmanager 送失敗時，把這件事送到監看服務的另一個檢查項目，由監看服務通知。

這一層成立的條件是監看服務在服務的失效域以外：它和告警系統跑在同一台主機上時，主機停掉兩者一起停，沒有人通知；它自己的通知管道（email、推播）也不能經過被監看的那台主機。觀察者的位置要怎麼選（第三方服務、另一個業者的主機、兩台主機互相監看）見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)，healthchecks 的接法與停機演練見 [第三方心跳監看與外部探測服務](/backend/04-observability/vendors/prometheus/external-heartbeat-and-probe-services/)，觀測系統與服務在事故中一起退化的情形見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)。

## 使用者路徑的合成監控與真實使用者監測

使用者路徑的監控回答的問題是：使用者從外面連得到服務嗎、他們實際感受到多慢。[Synthetic Monitoring（合成監控）](/backend/knowledge-cards/synthetic-monitoring/)從服務的失效域以外、在使用者所在的網路發請求：解析公開網域、經過 HTTPS 與公開入口，檢查回應的狀態碼與內容。服務網路內的探測看不到的 DNS、憑證與入口故障，由它接住；主機整台停掉時，它是少數還在運作、會發出通知的觀察者。真實使用者監測（RUM）在使用者的瀏覽器或 App 裡記錄實際請求的耗時與錯誤，量到的是各地區、各種裝置的分布，合成監控只量它固定走的那幾條路徑。

這一層看不到服務的內部：合成監控知道使用者連不進來，不知道是 DNS、入口、主機還是程式壞掉，要回頭比對前面各層的訊號。合成監控、心跳監看與服務網路內的探測三者並排時，哪一個失敗、哪一個正常，就指出失效落在哪一段，判讀表見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)。合成監控與 RUM 的定位與後端 SLI 的整合見 [4.10 Client-side / Synthetic / RUM](/backend/04-observability/client-side-monitoring/)，外部探測服務的挑選條件見 [第三方心跳監看與外部探測服務](/backend/04-observability/vendors/prometheus/external-heartbeat-and-probe-services/)。

## 監控鏈以外：服務正常運作時仍會出的問題

監控鏈的每一層最終問的都是同一件事：服務在不在正常運作。下面這幾類問題發生時，這個問題的答案仍然是「是」：每個容器都健康、每個探測都成功、資源用量正常、告警系統安靜。它們不會在任何一層產生異常訊號，要另外定義「預期會看到什麼」，再監看它有沒有出現。

**業務結果。** 程式回應正常而業務停了：付款頁的前端腳本壞掉、按鈕按不下去時，後端收不到結帳請求，錯誤率維持正常，而訂單數歸零；短網址的建立頁被一次改版拿掉了送出按鈕時，轉址照常運作，新建的短網址數歸零。監看的做法是挑幾個代表業務在運作的數字（每 10 分鐘的訂單數、新建的短網址數），和上週同一時段比較，低於預期一定比例時告警；流量本來就有起伏的服務，以統計基準判斷偏離，見 [4.14 Anomaly Detection](/backend/04-observability/anomaly-detection/)。業務儀表板的定位見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)。

**到期事件。** TLS 憑證、網域、API 金鑰與付費方案在到期之前一切正常，到期那一刻服務中斷。監看的做法是記下到期時間、在剩下一段天數時告警：blackbox_exporter 對 HTTPS 目標探測時輸出 `probe_ssl_earliest_cert_expiry`（最早到期那一張憑證的到期時間，Unix 時間戳），規則以它減去現在時間判斷剩下幾天；網域的到期日不在 TLS 握手裡，要從註冊商或 RDAP（WHOIS 的後繼協定）查。自動續期也要監看，因為續期程序失敗時同樣不產生任何錯誤，直到憑證過期。續期與輪替的流程見 [Certificate Rotation and Renewal](/backend/knowledge-cards/certificate-rotation-renewal/)。

**排程工作與備份。** 每晚的備份、報表、資料清理不在請求路徑上，它們沒跑的時候沒有任何請求失敗。監看的做法與告警鏈的心跳相同：工作完成時對監看服務送一次心跳，沒按時送到就通知，見 [Dead Man's Switch（心跳監看）](/backend/knowledge-cards/dead-mans-switch/)。備份另有一層：備份工作成功只證明檔案寫出去了，還原得回來要實際還原一次才知道，見 [備份與還原的地基](/going-live/backup-restore-basics/)。

**安全。** 攻擊者以竊取的帳號登入、提升權限、匯出資料時，每一個請求在資源與請求指標上都是正常的請求。監看的對象是行為：登入失敗的次數與來源、權限變更、管理操作、異常的大量讀取，資料來源是 [Audit Log](/backend/knowledge-cards/audit-log/)。稽核紀錄的邊界見 [4.12 Audit Log 邊界與 PII 治理](/backend/04-observability/audit-log-governance/)，偵測規則的涵蓋範圍與誤報成本見 [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)。

**第三方依賴。** 金流、簡訊、email、第三方登入的業者停掉時，自己的服務每一層都正常，只有呼叫它們的那一段失敗。監看的做法是把對每一個外部依賴的呼叫各自記成請求指標（成功率、耗時），失敗率升高時就知道是哪一家，同時訂閱業者的狀態頁。依賴關係的盤點見 [4.13 Service Topology 與 Dependency Map](/backend/04-observability/service-topology/)，依賴方停掉時的處理見 [8.15 Vendor / 第三方依賴事故處理](/backend/08-incident-response/vendor-dependency-incident/)。

**成本。** 自動擴充失控、一支程式反覆重試、log 量暴增，服務照常運作而帳單成倍增加。雲端業者的預算告警是最小的一層；要分辨成本上升是因為流量還是因為效率變差，把每個服務的成本和它的流量並排看，見 [9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/) 的〈Cost dashboard〉。監控系統本身的成本見 [4.7 Cardinality 治理與成本邊界](/backend/04-observability/cardinality-cost-governance/)。

## 以分層盤點一個服務的監控

拿到一個服務時，把它現有的每一種監控放到監控鏈上，看哪一層沒有觀察者、哪一層的觀察者與服務共用失效域；再對監控鏈以外的每一類問題，查有沒有定義「預期會看到什麼」。以前面那台主機上的短網址服務為例，假設它接了容器健康檢查、同一台主機上的 Gatus、Prometheus 與各層 exporter、Alertmanager 推播到手機，以及跑在同一台主機上的心跳監看服務：

| 監控鏈的層           | 這個服務用的元件                                       | 判讀                                                          |
| -------------------- | ------------------------------------------------------ | ------------------------------------------------------------- |
| 容器與程序的自檢     | 每個容器的 Docker 健康檢查                             | 有；`unhealthy` 沒有程式讀它，服務壞掉由 Gatus 的探測另外發現 |
| 服務網路內的探測     | 同一台主機上的 Gatus                                   | 有；量不到公開的 DNS 與憑證                                   |
| 資源與流量指標       | Prometheus 與主機、容器、資料庫、快取、入口的 exporter | 有                                                            |
| 應用層訊號           | 只有 Gatus 量到的探測耗時                              | 缺：程式沒有輸出請求指標，每個端點的錯誤率與耗時分布看不到    |
| 告警規則與分送       | Prometheus 規則與 Alertmanager，推播到手機             | 有                                                            |
| 告警鏈的監看         | 心跳監看服務，跑在同一台主機上                         | 機制有，位置不成立：主機停掉時它跟著停                        |
| 使用者路徑的合成監控 | 無                                                     | 缺：主機整台停掉、網域或憑證出錯時，沒有任何觀察者會通知      |

這張表讀出兩個缺口的性質不同。應用層訊號的缺口在問題：這個服務的程式沒有輸出請求指標，補的是程式碼。告警鏈監看與使用者路徑的缺口在位置：心跳的機制已經能運作，缺的是一個不和服務共用失效域的地方，補的是另一個業者的服務或主機，而這一項補上之前，主機整台停掉這個故障沒有任何一層會通知。監控鏈以外的問題同樣逐類查：這個服務沒有監看憑證到期、沒有監看每晚的資料庫備份，兩者都可以用已經有的元件補上：憑證到期是 blackbox_exporter 的一條規則，備份是工作完成時對心跳監看服務送一次心跳。

第二台主機或第三方服務要先給哪一層、備份要放到哪裡，見 [小型服務的兩到三台主機配置](/operations/06-high-availability/small-service-host-layout/)；上線前以清單逐項檢查訊號是否足以支援事故判讀，見 [4.16 Observability Readiness Review](/backend/04-observability/observability-readiness-review/)。
