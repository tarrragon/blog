---
title: "4.7 Cardinality 治理與成本邊界"
date: 2026-05-01
description: "把 metric / log / trace 的 cardinality 與成本作為平台一級治理議題"
weight: 7
tags: ["backend", "observability"]
---

## 大綱

- cardinality 為何爆：unbounded label（user_id / request_id / url path）
- metrics 的 cardinality 影響：時序資料庫 series 爆炸、查詢退化
- log 的 cardinality 影響：索引膨脹、保留成本
- trace 的 [sampling](/backend/knowledge-cards/sampling/) 策略：head sampling vs tail sampling、tradeoff
- cost-aware observability：成本作為治理輸入而非事後賬單
- governance 控制面：label 白名單、ingestion quota、保留階梯
- 高峰場景：流量尖峰時 cardinality slope 是 leading indicator
- 跟 [4.1 log schema](/backend/04-observability/log-schema/) 的分工：4.1 設計欄位、4.7 設邊界
- 跟 [4.2 metrics](/backend/04-observability/metrics-basics/) 的分工：4.2 是 metric 種類、4.7 是 label 治理
- 反模式：所有事件都打高 cardinality label、預算耗盡才砍訊號、保留策略無階梯

## 概念定位

Cardinality 治理是把觀測維度當成有限資源管理的流程，責任是讓訊號足夠可切分，同時不讓儲存、查詢與告警成本失控。

這一頁處理的是成本邊界。可觀測性需要有選擇地收集訊號；它把高價值維度留在可查詢路徑，把低價值或無界維度放到更合適的資料層。

Cardinality 跟成本的關係是非線性的。Label 數目每增加一倍，metric series 數目可能呈乘法增長；查詢延遲、儲存大小、索引重建時間都會跟著放大。把 cardinality 視為一級治理項目，能避免「收得越多越好」的直覺推著成本上升。

## Cardinality 在不同訊號的失分模式

Cardinality 在 metric、log、trace 三類訊號的影響機制不同，失分模式也不同。把三者用同一套治理規則處理，會在某類訊號上過度限制、在另一類上失控。

| 訊號類型 | 主要失分機制               | 控制手段                                       | 典型 trigger                  |
| -------- | -------------------------- | ---------------------------------------------- | ----------------------------- |
| Metric   | TSDB series 爆炸、查詢退化 | label 白名單、bucketize、aggregation           | user_id / request_id 進 label |
| Log      | 索引膨脹、保留成本暴增     | 索引欄位限制、結構化分層、分流                 | 完整 URL / payload 進索引欄位 |
| Trace    | sampling 後遺失高價值樣本  | tail sampling、minimum sample floor、 exemplar | head sampling 比例固定        |

Metric cardinality 是最敏感的維度。Prometheus 等 pull-based TSDB 在 series 數超過數百萬時查詢退化、aggregation 失準、recording rule 跑不完。Cloud 託管型 TSDB 雖然容量更大，但每個 active series 的單價非常具體，cardinality 直接對應 vendor 月帳單。

Log cardinality 的失分比較緩慢。Log 的 unique 值多本身不會立即崩潰，但全文索引 + 結構化欄位索引會持續膨脹，到某個臨界點查詢從毫秒退化到秒、再到分鐘。一般診斷不易察覺，要靠 query latency 跟 index size 的長期趨勢才能發現。

Trace cardinality 的問題是另一種：sampling 過於粗暴會丟失高價值樣本。低流量服務、錯誤樣本、長尾延遲樣本若被 head sampling 平均稀釋，事故時無 trace 可看。Trace 的治理重點是 sampling 策略而非單純限制 cardinality。

## 高 cardinality 的常見來源

無界維度進入可查詢路徑是 cardinality 失控的最大來源。常見的「無意中變成 label」：

- **User / tenant identifier**：把 user_id 當 label 時，每個用戶都產生一條 series。10 萬用戶 = 10 萬條 series 乘以其他 label 的笛卡爾積。
- **Request / session identifier**：request_id、session_id、trace_id 本質是無界的，進入 metric label 後 series 無限增長。
- **完整 URL / path parameters**：`/users/123/orders/456` 這類 path 進入 label，每個 unique URL 都是新 series。
- **錯誤訊息 / stack trace**：把 raw error message 當 label 時，每次新錯誤 = 新 series。
- **時間戳跟亂數**：偶發出現的 bug，把 timestamp、uuid 寫進 label。

這些都應該進 *log* 或 *trace* 的欄位，不該進 *metric* 的 label。Metric 的 label 應該是有界的維度：service name、environment、region、status code、http method、error class。

## 高峰場景的 cardinality 失控

高峰場景的 cardinality 治理責任是讓「平時可控的 series 上限」在尖峰時仍能維持決策可用。平時 cardinality 看似穩定，高峰時可能突然出現新 tenant、新 endpoint、新 error class 的湧入，把 series 推到平台極限；治理重點是把「成長斜率」「容量緩衝」「dry-run」「freshness gap」變成預先設計的訊號、而非高峰中即興救火。

對應 [4.C2 Gaming 高峰流量下的訊號新鮮度與 Cardinality](/backend/04-observability/cases/gaming-peak-signal-freshness-and-cardinality/)：揭露「ingestion lag、cardinality growth slope、alert freshness gap」是高峰場景的核心治理項目（三個訊號名稱屬 case 直接列出）；以下做法基於通用工程知識展開。

高峰場景的可操作做法：

1. **把 cardinality growth slope 視為 leading indicator**：series 數目的成長斜率比絕對值更早反映異常。突然出現的快速上升通常意味著新 label 值湧入或既有 label 失控。
2. **預設容量 buffer**：日常使用容量設在平台上限的 50-60%，留高峰時 cardinality 突發空間。把容量推到 90% 才追加治理會在高峰時來不及。
3. **高峰前的 dry-run**：把預期高峰流量的 cardinality 估算進 capacity model，找出可能的 unbounded label。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)。
4. **Alert freshness gap 也要監控**：高峰時 ingestion lag 上升、告警延遲、值班決策落在過期資料上的風險。把 alert freshness（資料時間 vs 當前時間）變成 dashboard 訊號。

高峰結束後做 retrospective：哪些 label 在高峰時超出預期、哪些 alert 因延遲沒及時觸發、哪些 series 應該下次提前 bucketize。這個 retrospective 是治理閉環的一部分，由 [4.8 signal-governance-loop](/backend/04-observability/signal-governance-loop/) 處理長期回寫。

## Sampling 策略

本章是 04 模組的 sampling 策略 SSoT — Head / Tail / Adaptive / Exemplar 四類策略集中在此；sampling 對資料品質的失真風險（low-traffic bias、error sample loss、tail latency loss）由 [4.17 Sampling 與代表性](/backend/04-observability/telemetry-data-quality/#sampling-與代表性) 處理；trace context 層的 sampling 配置由 [4.3 tracing context](/backend/04-observability/tracing-context/) 處理。

Sampling 策略的核心責任是控制觀測成本、同時保留足以判讀的高價值樣本。固定比例 head sampling 是最常見、也是最容易丟失高價值樣本的策略。

| 策略類型            | 機制                                        | 適用場景                         | 主要風險                               |
| ------------------- | ------------------------------------------- | -------------------------------- | -------------------------------------- |
| Head sampling       | 在 trace 開始時決定是否採樣                 | 簡單、低延遲、collector 端低資源 | 不知道 trace 結果就決定、可能丟錯誤    |
| Tail sampling       | 等 trace 結束後再決定（看是否錯誤、長延遲） | 保留錯誤、保留 outlier           | collector 要 buffer 整條 trace、資源高 |
| Adaptive sampling   | 按服務、tenant、流量動態調整比例            | 多租戶、流量差異大               | 規則複雜、需要監控 sampling rate       |
| Exemplar attachment | metric 帶代表性 trace id 樣本               | 從 metric 跳到 trace             | 不解決 sampling 本身、是補充           |

實務上常用組合：低流量服務用接近 100% 採樣（minimum sample floor）、高流量服務用 tail sampling 保留錯誤跟長尾、metric 帶 exemplar 讓從 dashboard 跳到 trace。

四類策略各自的適用情境：

- **Head sampling** 適合單體應用、延遲敏感、collector 端資源吃緊的場景。代價是 trace 開始時無法判斷是否錯誤、會等比例丟掉錯誤樣本。
- **Tail sampling** 適合微服務、需保留錯誤跟長尾的場景。代價是 collector 要 buffer 整條 trace、記憶體跟 CPU 用量明顯增加、對 cluster gateway 容量規劃壓力大。
- **Adaptive sampling** 適合多租戶、流量差異大的場景。風險是規則複雜化會造成 sampling rate 漂移、必須持續監控每個 service / tenant 的實際保留比例、否則治理會失控。
- **Exemplar attachment** 補強 metric → trace 跳轉、不解決 sampling 本身。在已有 head/tail sampling 的場景上加 exemplar 是低成本高價值的做法。

關鍵是 sampling policy 本身要可被服務團隊理解跟調整。把 sampling 規則寫在 collector 配置裡、版本化、跟著 release 一起管理；把當前 sampling rate 跟保留分布暴露在 dashboard 上。當服務團隊發現某段時間 trace 殘缺、要能直接查到 sampling policy 的當下值跟變更紀錄。

## 控制面與保留階梯

可操作的 cardinality / 成本治理控制面有四層，從預防到事後審計都要覆蓋。

1. **設計時 label 白名單**：服務團隊新增 metric 時要 review label 是否在白名單內。白名單列出有界維度（service、env、region、status_code、error_class、http_method），明確排除 user_id、request_id、完整 URL。
2. **Ingestion 層 quota 與 cardinality limit**：collector 或 vendor 端設定每服務、每 tenant 的 series 上限。超過上限時觸發告警，並啟動 graceful 降級（保留高優先 series、其他暫停）。
3. **保留階梯**：依資料熱度跟法規責任分層保留。熱資料（最近 7 天）full granularity、溫資料（7-30 天）aggregated、冷資料（30+ 天）長期歸檔。階梯設計要結合 [4.12 audit log governance](/backend/04-observability/audit-log-governance/) 的法規保留期。
4. **成本歸屬到 owner**：把 ingestion、storage、query 成本拆到服務或團隊維度。沒有歸屬的成本會被視為平台問題，治理動力不會傳到產生成本的團隊。詳見 [4.15 cost attribution](/backend/04-observability/cost-attribution/)。

保留階梯的另一個價值是事故時的容量保護。當熱資料儲存接近滿載、可以加速冷化、主動釋放容量給當下事件、避免被動等保留期到再恢復。

## [Storage tiering](/backend/knowledge-cards/storage-tiering/) 對查詢能力的影響

保留階梯不只是成本工具，它直接決定不同時間範圍的查詢能力。每一層的儲存介質、索引密度、[rollup](/backend/knowledge-cards/rollup/) 精度決定了該層能回答什麼問題、不能回答什麼問題。

### 每一層能回答什麼

Hot tier 保留完整精度與完整索引，能支援即席診斷的所有維度切片（by service、by tenant、by error code、by request id）。當資料從 hot 移到 warm，部分索引可能被移除、精度可能被 rollup 降低，能做的查詢從「特定 request id 的完整事件鏈」退化為「某服務過去兩週的 error rate 趨勢」。到 cold tier，通常只剩 timestamp + 少數結構化欄位的最小索引，細節查詢需要先 rehydrate 回 warm 或 hot 層。

這個退化是設計選擇，但需要被使用者感知。事故復盤時，如果團隊想查兩週前的特定 request 但資料已在 warm tier 且 request id 索引被移除，他們需要知道「不是沒有資料，而是需要 rehydrate 才能查」。

### 跨層查詢的延遲跳變

Dashboard 的時間範圍選擇直接觸發跨層查詢。使用者從「最近 1 小時」（全部在 hot tier）拉到「最近 7 天」（hot + warm tier），查詢延遲從毫秒跳到秒級。再拉到「最近 90 天」（hot + warm + cold tier），延遲可能跳到十秒甚至分鐘級。

這種延遲跳變在事故中的影響是：incident commander 想看長期趨勢來判斷異常是突發還是漸進時，dashboard 卡在載入。應對方式是在 dashboard 設計時就把「長時間趨勢」panel 指向 [recording rule](/backend/knowledge-cards/recording-rule/) 或 rollup series，讓它讀取預聚合資料而非跨層掃描 raw data。

### Tier 邊界依訊號類型差異化

不同訊號類型的 tier 邊界應該不同。Error log 跟 trace 的事故診斷價值比 debug log 高，hot tier 保留期應該更長。[Audit log](/backend/04-observability/audit-log-governance/) 因合規要求可能需要長期可查詢而非純歸檔。SLO-critical 的 metric series 可能需要 hot tier 保留 30 天來支援 monthly burn rate 計算，而 debug-level 的 metric 只需要 7 天 hot tier。

把所有訊號用同一個 tier 邊界管理（「全部 7 天 hot、30 天 warm、1 年 cold」）會讓高價值訊號過早退化、低價值訊號佔用過多 hot tier 容量。依訊號優先級設定差異化的 tier 邊界是保留階梯設計的進階步驟。

詳細的跨訊號查詢設計見 [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)。

## 核心判讀

判讀 cardinality 時，先看維度是否有決策價值，再看它是否有上界。

重點訊號包括：

- user id、request id、完整 URL 是否進入不該承受的 metric label
- log index 是否只索引常用查詢欄位
- trace [sampling](/backend/knowledge-cards/sampling/) 是否能優先保留高價值樣本
- [retention](/backend/knowledge-cards/retention/) 是否依資料熱度與法規責任分層
- cardinality growth slope 是否被監控為 leading indicator

## 判讀訊號

- metric series 數量曲線陡升、TSDB 查詢退化
- log ingestion 成本月對月雙位數成長
- label 含 user_id / request_id / 完整 URL 直接送到 metric
- ingestion quota 觸發時靠砍訊號救火、無 graceful 降階
- 保留策略全平、無冷熱分層、舊資料拖累查詢
- 高峰時 alert freshness gap 擴大、值班用過期資料

## 反模式

| 反模式               | 表面現象                         | 修正方向                                  |
| -------------------- | -------------------------------- | ----------------------------------------- |
| 無界 label 進 metric | user_id / request_id 在 label 中 | label 白名單、把細粒度放到 log / trace    |
| 預算耗盡才砍訊號     | quota 觸發後緊急砍 series        | 平時設成長告警、緩衝容量 50-60%           |
| 保留策略全平         | 所有 log / metric 都留 30 天     | 依熱度跟法規分階、結合 audit retention    |
| Sampling 比例固定    | head sampling 10% 套全部服務     | 低流量 100%、錯誤強制保留、tail sampling  |
| 成本無歸屬           | 平台付帳、團隊無動力治理         | 歸屬到 service owner、進 cost attribution |

## 交接路由

- [4.6 SLI/SLO](/backend/04-observability/sli-slo-signal/)：SLI metric 的 cardinality 上限
- [4.8 signal-governance-loop](/backend/04-observability/signal-governance-loop/)：高峰 retrospective 回寫治理
- [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/)：pipeline 層 quota 執行
- [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)：事故時 cardinality spike 反噬觀測後端
- [4.12 audit log governance](/backend/04-observability/audit-log-governance/)：audit 保留期銜接
- [4.15 cost attribution](/backend/04-observability/cost-attribution/)：成本治理的責任分配層
- [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)：storage tiering 對查詢能力的完整設計
- [6.9 容量成本](/backend/06-reliability/capacity-cost/)：observability 成本作為容量規劃輸入
- [vendors](/backend/04-observability/vendors/)：各平台的 ingestion / query quota 模型
