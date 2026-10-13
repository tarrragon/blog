---
title: "Prometheus 指標的視覺化工具：視覺化層的責任，與內建介面、Grafana、Perses、Kibana、託管服務的取捨"
date: 2026-10-13
description: "自架 Prometheus 之後把指標畫成常駐畫面的那一層承擔哪些責任（查詢與呈現、儀表板定義的保存、存取控制、告警規則放在哪一層、多種資料來源、授權與資源），Prometheus 內建介面、Grafana、Perses、Kibana 與託管服務各自滿足哪幾項、成立的前提，以及前提改變時改用哪一個"
weight: 14
tags: ["backend", "observability", "vendor", "prometheus", "grafana"]
---

> 本文是 [Prometheus](/backend/04-observability/vendors/prometheus/) 的 vendor deep article。Prometheus、exporter 與 Grafana 在一台主機上怎麼接起來，見 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/)；儀表板該放哪些圖、怎麼分層，見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)。

這篇整理自架 Prometheus 之後，把指標畫成常駐畫面的那一層要用什麼工具。範圍從 Prometheus 已經在讀取指標開始，比較的對象是自架或託管的視覺化工具；儀表板裡該放哪些圖不在本篇。

## 視覺化層承擔的責任

Prometheus 負責讀取指標、存進時間序列資料庫、依規則算出告警。向 Prometheus 查詢、把結果畫成團隊每天打開來看的畫面，是另一層的工作，這一層稱為視覺化層。視覺化層的責任比「畫圖」多，而各個工具的差別就落在這些責任上：

- **查詢與呈現**：用 PromQL 查詢，結果畫成時間序列圖、表格或單一數值，同一張圖可以疊多個查詢，畫面上可以切換時間範圍與篩選條件（例如選一個服務名稱，整頁的圖跟著換）。
- **儀表板定義的保存**：一張儀表板（[dashboard](/backend/knowledge-cards/dashboard/)）是一份定義——放了哪些圖、每張圖的查詢與單位。這份定義存在工具自己的資料庫，或存在 repo 裡的檔案，決定了換一台機器、重建一次容器之後它還在不在，以及修改能不能經過 code review。
- **存取控制**：Prometheus 與 Alertmanager 的網頁設定檔（`--web.config.file`）只提供 TLS 與 basic auth，通過認證的帳號全部擁有完整權限，官方文件也把這個功能標為實驗性。所以要讓團隊、主管或外部合作方看畫面時，「誰只能看、誰能改」只能在視覺化工具的帳號與角色上分級。
- **告警規則放在哪一層**：有些視覺化工具自帶[告警](/backend/knowledge-cards/alert/)引擎。告警規則可以寫在 Prometheus 的規則檔、由 Alertmanager 發通知，也可以寫在視覺化工具裡；放在哪一層，決定了這個工具停掉時告警還發不發得出去。
- **多種資料來源**：除了 Prometheus 的指標，同一個畫面要不要並排 log、trace 或資料庫的查詢結果。
- **授權與資源**：工具的授權條款對「修改後提供給別人使用」有沒有要求，以及它本身佔多少記憶體。記憶體在監控與服務共用一台小主機時是實際的成本：〈單機 Compose 的最小監控堆疊〉那套設定裡，Grafana 以 `container_memory_working_set_bytes` 量到約 240 MB，比 Prometheus 的約 155 MB 還多。

## Prometheus 內建的查詢介面

Prometheus 自己的網頁介面可以輸入任何 PromQL，結果以表格或時間序列圖顯示。官方文件對它的定位是「主要用於臨時查詢與除錯」，常駐的圖表則指向 Grafana 或 console templates。

這個介面滿足的是查詢與呈現裡的「查」：寫告警規則時，把運算式的比較運算子拿掉貼進來，就看得到每個序列目前的值與帶了哪些標籤；告警頁與讀取對象頁（Alerts、Targets）也在這裡。查詢條件會留在網址上，可以存成書籤，而除此之外沒有任何保存的儀表板。存取控制只有上面那一層 basic auth，看得到畫面的人就看得到全部指標。

console templates 是 Prometheus 提供的另一條路：用 Go 的模板語法寫成網頁，由 Prometheus 伺服器直接提供，模板檔放在 repo 裡就能版控。從 Prometheus 3.0 起，安裝包不再附帶 console templates 與它的函式庫，要用的話自己準備並以 `--web.console.templates`、`--web.console.libraries` 指定；官方文件也建議剛接觸這種監控方式的人先試 Grafana。所以 console templates 現在適合的是已經有一套模板、而且不想多跑一個元件的環境。

內建介面成立的前提是：看的人就是維護 Prometheus 的那一兩位工程師，用途是排查與驗證規則。它不需要多跑任何元件，所以就算另外裝了儀表板工具，排查告警規則時仍然常回到這裡。

## Grafana

Grafana 是開源的視覺化平台，本身不收集資料，向外部的資料來源查詢再畫成儀表板（概念見 [Grafana](/infra/knowledge-cards/grafana/)）。它逐項對應上面的責任：

**查詢與呈現**：Prometheus 是它內建的資料來源之一，查詢直接寫 PromQL，儀表板變數可以從 Prometheus 的標籤值產生下拉選單。

**儀表板定義的保存**：儀表板是一份 JSON。Grafana 預設把它存在自己的資料庫（單機部署預設是容器裡的 SQLite 檔），也可以用 provisioning 從檔案載入。〈單機 Compose 的最小監控堆疊〉用的是 provisioning，並設 `allowUiUpdates: false` 讓檔案成為唯一來源。兩種保存方式在重建容器時的差別很明顯：那套設定沒有替 Grafana 的資料目錄掛 volume，所以重建容器之後，從檔案載入的儀表板照樣出現，存在資料庫裡的使用者與在介面上改過的密碼則全部回到初始狀態。檔案之外，Grafana 也提供以程式產生儀表板的 Foundation SDK（Go、TypeScript、Python 等語言），以及 Terraform provider 與 Kubernetes 上的 Grafana Operator。

**存取控制**：Grafana 有使用者、團隊與角色（Viewer、Editor、Admin），只需要看畫面的人給 Viewer 角色，他們能瀏覽儀表板而無法修改。這是把 Grafana 對團隊開放、而 Prometheus 與 Alertmanager 只綁在本機位址上的理由：要給別人看的那一層有權限分級，沒有權限分級的那幾個元件不對外。

**告警規則放在哪一層**：Grafana 內建一個以 Prometheus Alertmanager 為基礎擴充的 Alertmanager，可以在介面上建立告警規則，規則的資料來源不限於 Prometheus（例如一段 SQL 查詢或 Loki 的 log 查詢）。它也能把告警轉送給外部的 Prometheus Alertmanager，並把外部的 Alertmanager 加成資料來源來檢視；對外部的 Prometheus Alertmanager，Grafana 只能管理靜音（silence），聯絡點與通知政策是唯讀的，因為 Alertmanager 的 HTTP API 不提供修改這些設定。

規則放在 Prometheus 與放在 Grafana 的取捨，在 Grafana 停掉的那一刻分出來。規則寫在 Prometheus 的規則檔時，Grafana 重啟、升級或記憶體不足被停掉，告警照常發出；規則檔放在 repo 裡，可以用 `promtool check rules` 檢查語法、用 `promtool test rules` 寫單元測試。規則寫在 Grafana 時，Grafana 就進入了告警的路徑，它停掉的期間沒有告警，這是觀測系統與被觀測系統一起失效的一種形態（見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)）；換到的是不寫 YAML 的人也能在介面上建規則，以及能對 Prometheus 以外的資料來源告警。〈單機 Compose 的最小監控堆疊〉把規則寫在 Prometheus：告警全部在 Prometheus 與 Alertmanager，Grafana 只負責畫面。

**多種資料來源**：Loki（log）、Tempo（trace）、Elasticsearch、PostgreSQL、MySQL 等都能加成資料來源，同一頁可以把一段時間的錯誤率曲線與那段時間的 log 並排。Grafana 自家的 log 與 trace 後端怎麼搭配，見 [LGTM Stack 組合運維](/backend/04-observability/vendors/grafana-stack/lgtm-stack-operations/)。

**現成的儀表板**：Prometheus 生態系裡的現成儀表板多半是 Grafana 的 JSON——許多 exporter 隨附的 monitoring mixin 產生的就是 Grafana 儀表板，Kubernetes 上常見的 kube-prometheus-stack 也附帶 Grafana。接上一個新的 exporter 時，從它的 mixin 或社群儀表板匯入，再依自己的標籤調整，比從零畫起快得多。

**授權**：Grafana 自 2021 年起由 Apache 2.0 改為 AGPLv3，plugin、agent 與部分函式庫維持 Apache 授權。Grafana Labs 的說明是：使用與修改都不受限制，而修改過的版本若散布出去或透過網路提供給別人使用，就要公開修改的原始碼。在自己的主機上照原樣部署給團隊看，不觸發這個義務；把修改過的 Grafana 包進自己的產品提供給客戶，才需要處理。

Grafana 成立的前提是：畫面要給維護 Prometheus 以外的人看、需要權限分級，或要把指標與其他資料來源放在一起看。在自架 Prometheus 的環境裡，它是最常見的組合，而代價是多一個要維運的元件與它的記憶體，以及要決定它的資料目錄存在哪裡。

## Perses

Perses 是 CNCF 的 sandbox 專案，定位是一份開放的儀表板規格，以及實作這份規格的儀表板工具，全部元件以 Apache 2.0 授權。資料來源支援 Prometheus 的指標、Tempo 的 trace、Loki 的 log、Pyroscope 的 profile，以及 ClickHouse 等其他來源。

Perses 和 Grafana 的差別集中在儀表板定義的保存。Perses 從設計上就以「儀表板是程式碼」為出發點：提供 CUE 與 Go 的 SDK 定義儀表板，並有 Kubernetes operator 以 Custom Resource 宣告儀表板，讓儀表板與服務的其他設定一起走 GitOps 的流程。Grafana 也能以 provisioning 檔與 Foundation SDK 做到版控，差別在預設值：Grafana 預設存在自己的資料庫、檔案是另外接上的，Perses 的規格本身就是檔案。

Perses 成立的前提有兩種：團隊已經用 Kubernetes 與 GitOps 管理部署，希望儀表板也是一份經過 review 的宣告；或者要把儀表板工具嵌進自己對外提供的產品，需要 Apache 授權。代價來自它還在 sandbox 階段：現成的儀表板大多是 Grafana 格式，Perses 的命令列工具 `percli migrate` 能把 Grafana 儀表板轉成 Perses 格式，而官方文件也提醒轉換後仍可能遇到問題，轉換結果要拿自己的儀表板逐張確認。

## Kibana 與 OpenSearch Dashboards

Kibana 是 Elastic Stack 的視覺化層，OpenSearch Dashboards 是 OpenSearch 專案的對應元件，兩者查詢的對象是存在 Elasticsearch 或 OpenSearch 裡的資料，主要用途是 log 的搜尋與分析。它們出現在這個比較裡，是因為組織已經有一套 Elastic 或 OpenSearch 時，會問「指標能不能也放在同一個介面」。

這個選擇的前提是資料已經在 Elasticsearch 或 OpenSearch 裡。指標在 Prometheus 時，常見的組合是讓 log 留在原本的平台、指標用 Grafana 看，再把 Elasticsearch 加成 Grafana 的資料來源，需要並排的那幾頁在 Grafana 裡並排。

## 託管服務

Grafana Cloud、Datadog、雲端供應商的監控主控台（CloudWatch、Cloud Monitoring）把視覺化層連同儲存一起交給供應商：不必維運 Grafana 的資料目錄、升級與帳號，換到的是依資料量或主機數計費，以及資料存在供應商那邊。自架的 Prometheus 可以用 remote write 把指標送到這類服務（見 [Remote Write 與長期儲存整合](/backend/04-observability/vendors/prometheus/remote-write-long-term-storage/)）。整個監控能力該自建還是外包，判斷方式見 [0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/)。

## 前提改變時的選擇

上面各節的結論都綁在幾個前提上，這幾個前提各自獨立，任何一個改變，適合的工具就跟著換：

- **看畫面的人**：只有維護 Prometheus 的人、用途是排查時，內建介面就夠，不多跑元件。要給維護者以外的人看、需要「只能看」的權限時，加上 Grafana 或 Perses 這類有帳號與角色的工具，並讓 Prometheus 與 Alertmanager 繼續只綁在本機位址。
- **儀表板定義的保存方式**：可以接受儀表板存在工具的資料庫裡時，Grafana 的預設就能用，前提是它的資料目錄掛在 volume 上並納入備份，否則重建容器就會遺失。要求每一次修改都經過 code review 時，Grafana 改用 provisioning 檔或 Foundation SDK；部署本身已經是 Kubernetes 加 GitOps 時，Perses 的規格與 operator 是更直接的選項。
- **告警規則的位置**：告警在工具停掉時仍要發得出去、規則要能用 `promtool` 測試時，規則留在 Prometheus，視覺化工具只負責畫面。要對 Prometheus 以外的資料來源告警、或要讓不寫 YAML 的人建規則時，用 Grafana 的告警，並接受它進入告警路徑，另外安排一個不經過它的訊號（例如外部探測）。
- **資料所在的平台**：log 已經在 Elasticsearch 或 OpenSearch 時，log 的搜尋留在 Kibana 或 OpenSearch Dashboards，指標仍在 Grafana，需要並排時把 Elasticsearch 加成 Grafana 的資料來源。
- **授權與散布**：只在自己的主機上部署給團隊用時，Grafana 的 AGPLv3 不產生義務。要修改儀表板工具並包進對外提供的產品時，評估 Perses 這類 Apache 授權的工具，或在不修改 Grafana 的前提下整合。
- **維運的人力**：沒有人力維運視覺化層的升級、帳號與資料目錄時，改用託管服務，代價是計費與資料的位置。

以〈單機 Compose 的最小監控堆疊〉的情境逐項對照：看畫面的人會擴大到團隊，儀表板要放進 repo，告警要在 Grafana 停掉時照常發出，資料只有 Prometheus 的指標，只在自己的主機上部署，維運由同一組人負責。對照的結果是 Grafana 以 provisioning 檔載入儀表板、告警留在 Prometheus 與 Alertmanager，Prometheus 的內建介面保留給排查告警規則時使用。
