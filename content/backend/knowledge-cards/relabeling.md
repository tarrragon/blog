---
title: "Relabeling（標籤改寫）"
date: 2026-10-13
description: "Prometheus 的讀取對象少了、多了、帶錯標籤，或想在寫入前丟掉某些指標時，查 relabel 規則在哪幾個時間點執行、各自讀得到哪些標籤，以及規則沒有生效時怎麼逐條看出是哪一條規則丟掉或改寫了它"
weight: 473
tags: ["backend", "observability", "prometheus", "knowledge-card"]
---

Relabeling 是 Prometheus 在固定的時間點，依一串規則改寫一組標籤的機制：把一個標籤的值複製或改寫成另一個標籤、刪掉標籤，或者整筆丟掉。同一套規則語法用在幾個時間點，差別在改寫的對象：服務發現找到讀取對象（target）之後、讀取（scrape）之前，改寫的是讀取對象的標籤（`relabel_configs`）；讀到指標之後、寫進資料庫之前，改寫的是每一筆指標（`metric_relabel_configs`）；告警送往 Alertmanager 之前，改寫的是每一則告警的標籤（`alert_relabel_configs`）；遠端寫入之前，改寫的是要送出的每一條序列（`write_relabel_configs`）。另外 `alerting` 設定裡找 Alertmanager 的位址時也有一組 `relabel_configs`，改寫的是 Alertmanager 這個目標。`relabel_configs` 與 `metric_relabel_configs` 最常用，下方〈概念位置〉比較兩者讀得到的標籤，以及丟掉讀取對象或指標各省下什麼。讀取對象從哪裡來，見 [Service Discovery](/backend/knowledge-cards/service-discovery/)；為什麼要丟掉某些標籤或指標，見 [Metric Cardinality](/backend/knowledge-cards/metric-cardinality/)。Kubernetes 上的 Prometheus Operator 以 ServiceMonitor 的 `relabelings` 與 `metricRelabelings` 寫同樣的規則，欄位名稱改成 camelCase（`sourceLabels`、`targetLabel`）。下文的例子以 `host` 為主角：它是監控設定自己加在每筆序列上、代表主機的標籤，Prometheus 本身不產生它（Kubernetes 上常改用 `node`），告警與面板依它分組。

## 概念位置

| 規則的位置               | 改寫的對象       | 讀得到的標籤                                                                                                                                             | 丟掉之後省下什麼                                   |
| ------------------------ | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `relabel_configs`        | 每一個讀取對象   | 服務發現給的 `__meta_*`、讀取設定類的 `__address__`、`__scheme__`、`__metrics_path__`、`__param_*`、`__scrape_interval__` 等，以及清單上寫的標籤與 `job` | 整個讀取對象不讀，連線、解析與儲存都省下           |
| `metric_relabel_configs` | 讀到的每一筆指標 | 指標自己的標籤、指標名稱 `__name__`，以及讀取對象改寫完留下的標籤；`__meta_*` 已經不在                                                                   | 只省下儲存；指標照樣被讀取與解析，丟掉的在解析之後 |

讀取對象多半是 [Prometheus Exporter](/backend/knowledge-cards/prometheus-exporter/) 開的端點，所以丟掉一個讀取對象等於不讀那個 exporter；只想少存幾個指標時才用 `metric_relabel_configs`。

兩個位置之間有一道清除：讀取對象的標籤改寫完之後，Prometheus 刪掉所有以 `__` 開頭的標籤，所以 `__meta_*` 只在 `relabel_configs` 裡讀得到，要留下來的值必須在那裡複製到一個不以 `__` 開頭的標籤上。讀取對象的標籤改寫完如果沒有 `instance` 標籤，Prometheus 以 `__address__` 的值補上，`instance` 預設是讀取位址就是這個緣故。規則之間要暫存的中間值，用 `__tmp` 開頭的標籤名稱，它們在同一道清除裡被刪掉，不會被存進資料庫。

一條規則由幾個欄位組成：`source_labels` 列出要讀的標籤，值以 `;` 串起來（`separator` 可改）；`regex` 比對串起來的值，**比對的是整個值**，`prod` 不符合 `production`；`action` 決定符合之後做什麼，預設 `replace`：以 `replacement`（預設 `$1`，即 regex 第一個括號抓到的部分）寫進 `target_label`。其他常用的 `action` 有 `keep`（只留下符合的，不符合的整筆丟掉）、`drop`（符合的整筆丟掉）、`labelmap`（把名稱符合 regex 的標籤整批複製成新名稱，常用來把 `__meta_kubernetes_pod_label_*` 搬成一般標籤）與 `labeldrop`（刪掉名稱符合 regex 的標籤）。

## 可觀察訊號與例子

以下行為在 Prometheus 3.15 上以檔案清單與一台本機 Prometheus 實測過。

- **讀取對象從讀取狀態的頁面上不見了**：`relabel_configs` 裡的 `keep` 或 `drop` 把它丟掉。Prometheus 3 的網頁介面在 Status 選單下有兩個頁面：Target health 只列出要讀的讀取對象，被丟掉的不在那裡；Service discovery 列出服務發現找到的全部讀取對象，被丟掉的標為 dropped，並附上服務發現給它的原始標籤。清單上明明有這台主機而 Target health 上沒有，先看 Service discovery。同一頁每個讀取對象旁有 show relabeling，逐條列出每一條規則套用之後的標籤與這條規則是否把它丟掉（API 是 `/api/v1/targets/relabel_steps`），可以看出是哪一條規則丟掉或改寫了它。
- **該有的標籤沒有出現**：`replace` 讀的來源標籤不存在時，串起來的值是空字串，預設的 regex `(.*)` 符合空字串，寫進 `target_label` 的值也是空字串，而值為空的標籤等於不存在，沒有任何錯誤。例如以 `__meta_ec2_tag_Name` 寫進 `host`，而有幾台執行個體沒設 Name tag：那幾台執行個體的來源標籤不存在，它們的序列整個沒有 `host`，依 `host` 分組的告警把它們合成一組。這個機制以檔案清單上不存在的標籤實測過，EC2 是它套用的情境。
- **regex 看起來對，規則卻沒動作**：regex 要符合整個值。想比對「值裡含有 prod」，寫成 `.*prod.*`。
- **在 `metric_relabel_configs` 讀 `__meta_*` 讀到空的**：那時 `__meta_*` 已經被清除了。要用服務發現給的資訊改寫指標，先在 `relabel_configs` 把它複製成一般標籤；那個標籤會附加在這個讀取對象的每一筆指標上，通常不必再到 `metric_relabel_configs` 處理。
- **丟掉了指標，讀取時間與 exporter 的負擔卻沒有減少**：`metric_relabel_configs` 在解析之後才丟。Prometheus 替每個讀取對象記錄兩個數字：`scrape_samples_scraped` 是讀到的筆數，`scrape_samples_post_metric_relabeling` 是改寫之後留下的筆數，兩者的差就是被丟掉的筆數（實測丟掉 `go_gc_*` 時是 723 筆讀到、655 筆留下）。讀取時間與 exporter 的負擔不受影響，要省下這兩項得讓 exporter 少輸出，或者用 `relabel_configs` 整個讀取對象不讀。
- **指標代表的對象不是讀取對象**：外部探測工具（例如 Gatus）輸出的是它探測的端點的結果，讀取對象的 `host` 是探測工具所在的主機，要用 `metric_relabel_configs` 依指標名稱或端點名稱把 `host` 改成端點所在的主機，作法見 [主機過載時的監控告警](/backend/04-observability/host-overload-alerting/) 的〈依原因抑制：主機飽和時壓下各服務變慢〉。

## 設計責任

relabel 規則寫完的完成條件有兩項：在 Service discovery 頁面上，每一個該讀的讀取對象都沒有被標為 dropped、不該讀的都被標為 dropped；以及查詢結果裡每一筆序列都帶著告警與面板要分組的那幾個標籤（`count by (host) (up)` 的結果裡沒有缺 `host` 的那一組）。`up` 是讀取對象層級的序列，只反映 `relabel_configs` 的結果；用 `metric_relabel_configs` 改寫標籤時，改以被改寫的那個指標查，例如 `count by (host) ({__name__=~"gatus_.*"})`。規則會靜默地刪掉標籤或整個讀取對象，所以來源標籤可能不存在時，先寫一條一定有值的規則當預設，再寫覆寫的那一條並把它的 regex 設成 `(.+)`：例如先以 `__meta_ec2_instance_id` 寫 `host`，在 Name tag 每台都不同的環境再以 `__meta_ec2_tag_Name` 覆寫，Name tag 為空時覆寫的規則不符合、不動作，`host` 留著執行個體 ID；覆寫的規則沿用預設的 `(.*)` 的話，空字串也符合，`host` 反而被刪掉。寫成規則是這樣，順序就是執行的順序：

```yaml
relabel_configs:
  - source_labels: [__meta_ec2_instance_id]   # 預設：每台都有值
    target_label: host
  - source_labels: [__meta_ec2_tag_Name]      # 覆寫：只在 Name tag 有值時動作
    regex: (.+)
    target_label: host
```

為了控制序列數量而丟掉指標時，先問能不能在讀取對象那一層就不讀；`metric_relabel_configs` 適合丟掉少數幾個不需要的指標或標籤，不適合拿來抵銷一個輸出大量指標的 exporter。
