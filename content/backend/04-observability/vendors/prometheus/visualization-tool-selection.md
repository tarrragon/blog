---
title: "Prometheus 指標的視覺化工具：視覺化層的責任，與內建介面、Grafana、Perses、Kibana／OpenSearch Dashboards、託管服務的取捨"
date: 2026-10-13
description: "自架 Prometheus 之後把指標畫成常駐畫面的那一層承擔哪些責任（查詢與呈現、儀表板定義的保存、存取控制、告警規則放在哪一層、多種資料來源、授權與資源），Grafana 逐項對照這些責任，內建介面、Perses、Kibana／OpenSearch Dashboards 與託管服務各自的定位與成立的前提，以及前提改變時改用哪一個"
weight: 14
tags: ["backend", "observability", "vendor", "prometheus", "grafana"]
---

> 這一篇屬於 [Prometheus](/backend/04-observability/vendors/prometheus/) 的實作系列，回答畫面那一層為什麼通常交給 Grafana、什麼前提下改用別的工具。Prometheus、exporter 與 Grafana 在一台主機上怎麼接起來，見 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/)；儀表板該放哪些圖、怎麼分層，見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)。

比較的對象是 Prometheus 已經在讀取指標之後、把指標畫成常駐畫面的那一層：Prometheus 內建介面、Grafana、Perses、Kibana／OpenSearch Dashboards 與託管服務。儀表板裡該放哪些圖不在本篇。

## 視覺化層承擔的責任

Prometheus 負責讀取（scrape）各 exporter 的指標、存進時間序列資料庫、依規則算出告警。向 Prometheus 查詢、把結果畫成團隊每天打開來看的畫面，是另一層的工作，這一層稱為視覺化層。視覺化層的責任比「畫圖」多，而各個工具的差別就落在這些責任上：

- **查詢與呈現**：用 PromQL 查詢，結果畫成時間序列圖、表格或單一數值，同一張圖可以疊多個查詢，畫面上可以切換時間範圍與篩選條件（例如選一個服務名稱，整頁的圖跟著換）。
- **儀表板定義的保存**：一張儀表板（[dashboard](/backend/knowledge-cards/dashboard/)）是一份定義——放了哪些圖、每張圖的查詢與單位。這份定義存在工具自己的資料庫，或存在 repo 裡的檔案，決定了換一台機器、重建一次容器之後它還在不在，以及修改能不能經過 code review。
- **存取控制**：Prometheus 與 Alertmanager 的網頁設定檔（`--web.config.file`）只提供 TLS 與 basic auth，通過認證的帳號全部擁有完整權限，官方文件也把這個功能標為實驗性。所以要讓團隊、主管或外部合作方看畫面時，「誰只能看、誰能改」要放在視覺化工具的帳號與角色上分級，或放在前面一層帶認證的反向代理（例如 oauth2-proxy）上；Prometheus 本身分不出來。
- **告警規則放在哪一層**：有些視覺化工具自帶[告警](/backend/knowledge-cards/alert/)引擎。告警規則可以寫在 Prometheus 的規則檔、由 Alertmanager 發通知，也可以寫在視覺化工具裡；放在哪一層，決定了這個工具停掉時告警還發不發得出去。
- **多種資料來源**：除了 Prometheus 的指標，同一個畫面要不要並排 log、trace 或資料庫的查詢結果。
- **授權與資源**：工具的授權條款對「修改後提供給別人使用」有沒有要求，以及它本身佔多少記憶體。記憶體在監控與服務共用一台小主機時是實際的成本。Prometheus 的記憶體主要隨活躍的時間序列數成長，Grafana 的隨開著的面板與同時進行的查詢起伏，所以序列很少的單機上 Grafana 可能比 Prometheus 還多；單機、約九千條序列時兩者的實測量見 [單機 Compose 的最小監控堆疊](/backend/04-observability/vendors/prometheus/single-host-compose-stack/) 的〈連接埠與資源用量〉，自己的環境用 `container_memory_working_set_bytes` 量。

## Prometheus 內建的查詢介面

Prometheus 自己的網頁介面可以輸入任何 PromQL，結果以表格或時間序列圖顯示。官方文件對它的定位是「主要用於臨時查詢與除錯」，常駐的圖表則指向 Grafana 或 console templates。

這個介面滿足的是查詢與呈現裡的「查」：寫告警規則時，把運算式的比較運算子拿掉貼進來（`avg_over_time(up[15m]) < 0.9` 貼成 `avg_over_time(up[15m])`），就看得到每個序列目前的值與帶了哪些標籤；告警頁與讀取對象頁（Alerts、Targets）也在這裡。查詢條件會留在網址上，可以存成書籤，而除此之外沒有任何保存的儀表板。存取控制只有 `--web.config.file` 提供的 basic auth，看得到畫面的人就看得到全部指標。

console templates 是 Prometheus 提供的另一條路：用 Go 的模板語法寫成網頁，由 Prometheus 伺服器直接提供，模板檔放在 repo 裡就能版控。從 Prometheus 3.0 起，安裝包不再附帶 console templates 與它的函式庫，要用的話自己準備並以 `--web.console.templates`、`--web.console.libraries` 指定；官方文件也建議剛接觸這種監控方式的人先試 Grafana。所以 console templates 現在適合的是已經有一套模板、而且不想多跑一個元件的環境。

內建介面成立的前提是：看的人就是維護 Prometheus 的那一兩位工程師，用途是排查與驗證規則。它不需要多跑任何元件，所以就算另外裝了儀表板工具，排查告警規則時仍然常回到這裡。

## Grafana

Grafana 是開源的視覺化平台，本身不收集資料，向外部的資料來源查詢再畫成儀表板（概念見 [Grafana](/devops/infra/knowledge-cards/grafana/)）。依視覺化層的責任逐項看，另外加上現成的儀表板一項：

**查詢與呈現**：Prometheus 是它內建的資料來源之一，查詢直接寫 PromQL，儀表板變數可以從 Prometheus 的標籤值產生下拉選單。

**儀表板定義的保存**：儀表板是一份 JSON。Grafana 預設把它存在自己的資料庫（單機部署預設是容器裡的 SQLite 檔），也可以用 provisioning 從檔案載入。〈單機 Compose 的最小監控堆疊〉用的是 provisioning，並設 `allowUiUpdates: false` 讓檔案成為唯一來源。〈單機 Compose 的最小監控堆疊〉替 Grafana 的資料目錄（`/var/lib/grafana`）掛了具名 volume，重建容器不會清掉資料庫裡的東西。假設沒掛，兩種保存方式的差別就會在重建容器時出現：從檔案載入的儀表板照樣出現，存在資料庫裡的使用者、改過的密碼與在介面上建的儀表板全部消失。檔案之外，Grafana 也提供以程式產生儀表板的 Foundation SDK（Go、TypeScript、Python 等語言），以及 Terraform provider 與 Kubernetes 上的 Grafana Operator。

**存取控制**：Grafana 有使用者、團隊與角色（Viewer、Editor、Admin），只需要看畫面的人給 Viewer 角色，他們能瀏覽儀表板而無法修改。這套權限分級是 Prometheus 與 Alertmanager 沒有的那一層（它們只有 basic auth），所以要給團隊看畫面時對外開的是 Grafana。人數多時，登入改接組織既有的帳號系統（Grafana 支援 OAuth、LDAP 等登入方式），權限依團隊與資料夾分。

**告警規則放在哪一層**：Grafana 內建一個以 Prometheus Alertmanager 為基礎擴充的 Alertmanager，可以在介面上建立告警規則，規則的資料來源不限於 Prometheus（例如一段 SQL 查詢或 Loki 的 log 查詢）。它也能把告警轉送給外部的 Prometheus Alertmanager，並把外部的 Alertmanager 加成資料來源來檢視；對外部的 Prometheus Alertmanager，Grafana 只能管理靜音（silence），聯絡點與通知政策是唯讀的，因為 Alertmanager 的 HTTP API 不提供修改這些設定。

規則放在 Prometheus 與放在 Grafana，平常看不出差別，差別出現在 Grafana 停掉的期間。規則寫在 Prometheus 的規則檔時，Grafana 重啟、升級或記憶體不足被停掉，告警照常發出；規則檔放在 repo 裡，可以用 `promtool check rules` 檢查語法、用 `promtool test rules` 寫單元測試。規則寫在 Grafana 時，Grafana 就進入了告警的路徑：它自己停掉的期間沒有告警，告警路徑多了一個會單獨失效的元件（Grafana 的告警可以跑多個實例做高可用，代價是共用的資料庫、實例之間的同步連線（gossip 或 Redis），以及每個實例都評估全部規則而倍增的查詢量；多個實例和服務在同一台主機上時，主機層的失效照樣一起發生）；Grafana 與服務共用主機時，主機過載會讓服務與告警一起停擺，這是觀測系統與被觀測系統一起失效的一種形態（見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)）。規則放在 Grafana 換到的是不寫 YAML 的人也能在介面上建規則，以及能對 Prometheus 以外的資料來源告警。〈單機 Compose 的最小監控堆疊〉把規則寫在 Prometheus：告警全部在 Prometheus 與 Alertmanager，Grafana 只負責畫面。

**多種資料來源**：Loki（log）、Tempo（trace）、Elasticsearch、PostgreSQL、MySQL 等都能加成資料來源，同一頁可以把一段時間的錯誤率曲線與那段時間的 log 並排。Grafana 自家的 log 與 trace 後端怎麼搭配，見 [LGTM Stack 組合運維](/backend/04-observability/vendors/grafana-stack/lgtm-stack-operations/)。

**現成的儀表板**：Prometheus 生態系裡的現成儀表板多半是 Grafana 的 JSON——許多 exporter 隨附 monitoring mixin（一組以程式產生的儀表板與告警規則樣板），它產生的就是 Grafana 儀表板，Kubernetes 上常見的 kube-prometheus-stack 也附帶 Grafana。接上一個新的 exporter 時，從它的 mixin 或社群儀表板匯入，再依自己的標籤調整，比從零畫起快得多。

**授權**：Grafana 自 2021 年起由 Apache 2.0 改為 AGPLv3，plugin、agent 與部分函式庫維持 Apache 授權。Grafana Labs 的說明是：使用與修改都不受限制，而修改過的版本若散布出去或透過網路提供給別人使用，就要公開修改的原始碼。在自己的主機上照原樣部署給團隊看，不觸發這個義務；把修改過的 Grafana 包進自己的產品提供給客戶，才需要處理。

**資源**：多一個常駐的元件，記憶體量級見本篇〈視覺化層承擔的責任〉的授權與資源一項；它的資料目錄要掛 volume 並納入備份。

Grafana 成立的前提是：畫面要給維護 Prometheus 以外的人看、需要權限分級，或要把指標與其他資料來源放在一起看。Prometheus 官方文件把常駐的圖表指向它，現成的儀表板也以它的格式為主，代價是多一個要維運的元件與它的記憶體，以及要決定它的資料目錄存在哪裡。

## Perses

Perses 是 CNCF 的 sandbox 專案（CNCF 三個成熟度等級裡最早期的一級，2026 年 10 月查證時的狀態），定位是一份開放的儀表板規格，以及實作這份規格的儀表板工具，全部元件以 Apache 2.0 授權。資料來源支援 Prometheus 的指標、Tempo 的 trace、Loki 的 log、Pyroscope 的 profile，以及 ClickHouse 等其他來源。

Perses 和 Grafana 的差別集中在儀表板定義的保存。Perses 從設計上就以「儀表板是程式碼」為出發點：提供 CUE 與 Go 的 SDK 定義儀表板，並有 Kubernetes operator（在叢集裡依宣告的資源自動建立與維護對應物件的控制程式）以 Custom Resource 宣告儀表板，讓儀表板與服務的其他設定一起走 GitOps 的流程（以 Git repo 為部署設定的來源，變更合併之後自動套用到環境）。Grafana 也能以 provisioning 檔與 Foundation SDK 做到版控，差別在預設值：Grafana 預設存在自己的資料庫、檔案是另外接上的，Perses 的規格本身就是檔案。

Perses 成立的前提有兩種：團隊已經用 Kubernetes 與 GitOps 管理部署，希望儀表板也是一份經過 review 的宣告；或者要修改儀表板工具、嵌進自己對外提供的產品，而不想承擔 AGPL 公開修改內容的義務（Perses 是 Apache 2.0）。代價是它的生態還小：現成的儀表板大多是 Grafana 格式，Perses 的命令列工具 `percli migrate` 能把 Grafana 儀表板轉成 Perses 格式，而官方文件列的支援範圍是 Grafana 9 到 11 版的儀表板、以盡力而為的方式轉換，告警等儀表板以外的設定不轉，轉換結果要拿自己的儀表板逐張確認。

## Kibana 與 OpenSearch Dashboards

Kibana 是 Elastic Stack 的視覺化層，OpenSearch Dashboards 是 OpenSearch 專案的對應元件，兩者查詢的對象是存在 Elasticsearch 或 OpenSearch 裡的資料，主要用途是 log 的搜尋與分析。它們出現在這個比較裡，是因為組織已經有一套 Elastic 或 OpenSearch 時，會問「指標能不能也放在同一個介面」。

這個選擇的前提是資料已經在 Elasticsearch 或 OpenSearch 裡。指標在 Prometheus 時，常見的組合是讓 log 留在原本的平台、指標用 Grafana 看，再把 Elasticsearch 加成 Grafana 的資料來源，需要並排的那幾頁在 Grafana 裡並排。反方向也可行：Elastic 的 Metricbeat 有讀取 Prometheus 指標的模組，指標也收進 Elasticsearch，代價是同一份指標存兩份、兩邊各自維護保留期限。

## 託管服務

Grafana Cloud、Datadog、雲端供應商的監控主控台（CloudWatch、Cloud Monitoring）把視覺化層連同儲存一起交給供應商：不必維運 Grafana 的資料目錄、升級與帳號，代價是依資料量或主機數計費，以及資料存在供應商那邊。自架的 Prometheus 可以用 remote write 把指標送到這類服務（見 [Remote Write 與長期儲存整合](/backend/04-observability/vendors/prometheus/remote-write-long-term-storage/)）。整個監控能力該自建還是外包，判斷方式見 [0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/)。

## 前提改變時的選擇

各工具成立的前提拆成以下幾項，它們各自獨立變動，任何一項改變，適合的工具就跟著換。這些前提由視覺化層的責任換算而來：看畫面的人對應存取控制；儀表板定義的保存方式、告警規則的位置、資料所在的平台、授權各自對應同名的那一項責任；查詢與呈現每個工具都做得到，不構成差別；主機的資源與維運的人力是責任清單之外的條件。

- **看畫面的人**：只有維護 Prometheus 的人、用途是排查時，內建介面就夠，不多跑元件。要給維護者以外的人看、需要「只能看」的權限時，加上 Grafana 或 Perses 這類有帳號與角色的工具，對外開的是這個工具（經過反向代理與認證，Grafana 的做法見 [Grafana 的對外存取](/backend/04-observability/vendors/prometheus/grafana-external-access/)），Prometheus 與 Alertmanager 繼續只綁在本機位址。
- **看畫面的人是不是不同的客戶**：把儀表板嵌進產品給不同客戶看時，Viewer 角色只管能不能改，不管能看到哪些資料，而儀表板變數（例如 `host`）看的人自己就能改掉。所以要在資料層分開租戶：每個客戶一個 Grafana 組織（organization），各自有只查得到自己資料的資料來源，或讓查詢經過依租戶過濾的儲存（例如 Mimir 的多租戶：Mimir 以請求標頭 `X-Scope-OrgID` 區分租戶，本身不驗證這個標頭，前面要有一層先認證、再替請求填入租戶 ID 的反向代理，否則沒有隔離）。這一項決定的是資料怎麼分，選哪個儀表板工具都要處理。
- **儀表板定義的保存方式**：可以接受儀表板存在工具的資料庫裡時，Grafana 的預設就能用。這時 Grafana 的資料目錄要掛在 volume 上並納入備份，沒有掛的話，重建容器時儀表板就遺失。要求每一次修改都經過 code review 時，Grafana 改用 provisioning 檔或 Foundation SDK；部署本身已經是 Kubernetes 加 GitOps 時，Grafana 可以用 kube-prometheus-stack 的儀表板 sidecar（讀帶特定標籤的 ConfigMap，做法見 [在 Kubernetes 上接上監控](/backend/04-observability/vendors/prometheus/kubernetes-monitoring-entry/) 的〈儀表板經由 ConfigMap 與 sidecar 載入〉）或 Grafana Operator 把儀表板放進同一個流程，並沿用現成的 mixin 儀表板；要儀表板從規格層就是宣告式、或需要 Apache 授權時，Perses 的規格與 operator 是更直接的選項。
- **告警規則的位置**：要求告警在視覺化工具停掉時仍發得出去，或要求規則能用 `promtool` 測試（兩者任一成立）時，規則留在 Prometheus，視覺化工具只負責畫面。要對 Prometheus 以外的資料來源告警、或要讓不寫 YAML 的人建規則時，用 Grafana 的告警，並接受它進入告警路徑，另外安排一個不經過它的訊號（例如外部探測）。
- **資料所在的平台**：log 已經在 Elasticsearch 或 OpenSearch 時，log 的搜尋留在 Kibana 或 OpenSearch Dashboards，指標仍在 Grafana，需要並排時把 Elasticsearch 加成 Grafana 的資料來源。
- **授權與散布**：只在自己的主機上照原樣（不修改原始碼）部署給團隊用時，Grafana 的 AGPLv3 不產生義務；修改過再透過網路提供給團隊使用，就要對使用者提供修改的原始碼。要修改儀表板工具的原始碼並包進對外提供的產品時，評估 Perses 這類 Apache 授權的工具，或在不修改 Grafana 的前提下整合。
- **主機的資源**：只有一台小主機、記憶體與服務共用時，只有維護的人看圖的話，內建介面加上 Prometheus 的告警就能運作。要給其他人看而這台放不下 Grafana 時，資源這一項決定的是 Grafana 放在哪裡，不是用不用：放到另一台機器，或改用託管服務。
- **稽核要求**：要求記錄誰在什麼時候看了哪一張儀表板、或要自訂細粒度的角色時，Grafana 的開源版本不提供：瀏覽紀錄是 Grafana Enterprise 的 usage insights（Grafana Cloud 只有部分方案提供），自訂角色是 Enterprise 的 RBAC，開源版只有 Viewer、Editor、Admin 這類內建角色。
- **維運的人力**：沒有人力維運視覺化層的升級、帳號與資料目錄時，改用託管服務，代價是計費與資料的位置。

以〈單機 Compose 的最小監控堆疊〉的情境逐項對照：看畫面的人會擴大到團隊，儀表板要放進 repo，告警規則要在 Grafana 停掉時照常被算出來（〈單機 Compose 的最小監控堆疊〉還沒有通知管道，接上之後才發得出去），資料只有 Prometheus 的指標，只在自己的主機上部署，維運由同一組人負責。對照的結果是 Grafana 以 provisioning 檔載入儀表板、告警留在 Prometheus 與 Alertmanager，Prometheus 的內建介面保留給排查告警規則時使用。
