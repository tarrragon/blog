---
title: "4.17 Telemetry Data Quality"
date: 2026-05-02
description: "把 missing signal、schema drift、sampling bias 與 timestamp skew 變成資料品質問題"
weight: 17
---

## 大綱

- telemetry data quality 的責任：確認觀測資料本身可信
- 缺漏類型：missing signal、partial trace、dropped log、stale metric
- 漂移類型：schema drift、label drift、service name drift、semantic convention drift
- 偏誤類型：[sampling](/backend/knowledge-cards/sampling/) bias、low-traffic bias、high-cardinality truncation
- 時間類型：clock skew、ingest delay、out-of-order event、timezone mismatch
- 品質指標：completeness、freshness、consistency、accuracy、coverage
- 跟 04.11 telemetry pipeline 的分工：pipeline 看路徑，data quality 看資料可信度
- 反模式：dashboard 看起來正常但資料少一半；trace sample 漏掉錯誤；timestamp 導致 timeline 錯序

Telemetry data quality 的核心是把「觀測資料失真」當成一級事件。服務事故判讀建立在觀測資料上，資料品質不穩時，團隊會把資料缺口誤讀成系統行為，進而做出錯誤分級、錯誤回復或錯誤 SLO 判斷。

## 概念定位

Telemetry data quality 是把觀測資料當成資料產品治理的能力，責任是讓 log、metric、trace 與 alert 的判讀建立在可信資料上。

這一頁處理的是資料可信度。訊號存在不等於訊號可信；缺漏、漂移、偏誤與時間錯位都會讓事故判讀走向錯誤路徑。

資料品質治理最有效的做法是把品質指標產品化：讓 completeness、freshness、drift、sampling coverage 也進 dashboard 與告警，讓團隊在事故前就能看見資料限制。

## 品質模型

Telemetry data quality 的品質模型由五個面向組成。這五個面向分別回答資料是否存在、是否及時、是否一致、是否代表真實流量，以及是否足以覆蓋關鍵旅程。

| 品質面向     | 核心問題                         | 常見資料                     |
| ------------ | -------------------------------- | ---------------------------- |
| Completeness | 該出現的訊號是否完整出現         | drop rate、coverage、gap     |
| Freshness    | 訊號是否足夠接近事件發生時間     | ingest delay、stale metric   |
| Consistency  | 欄位、命名與語意是否跨服務一致   | schema drift、label drift    |
| Accuracy     | 數值與事件語意是否反映真實狀態   | duplicate event、wrong unit  |
| Coverage     | 高風險旅程與低流量邊界是否被涵蓋 | sampling policy、trace ratio |

Completeness 是事故判讀的基礎。log、metric 或 trace 的缺口如果沒有被標示，dashboard 會呈現一條看似平順的線，實際上可能只是 ingestion pipeline 丟了資料。

Freshness 決定資料能否支援事中決策。告警延遲、metric scrape delay、trace export queue backlog 與 log indexing lag 都會讓 incident commander 用過期資料判斷是否擴大或回復。

Consistency 決定資料能否跨服務拼接。service name、region、tenant、environment、error class 與 semantic convention 若在不同系統漂移，單一服務看起來正常，跨服務事件鏈卻會斷裂。

Accuracy 決定資料能否代表真實狀態。常見問題包含錯誤單位、重複計數、counter reset 誤判、histogram bucket 設錯與 status code mapping 錯誤。

Coverage 決定資料能否覆蓋高風險邊界。低流量服務、VIP tenant、錯誤樣本、長尾 latency 與 rare dependency failure 常被 sampling 或聚合策略稀釋。

## 核心判讀

判讀 telemetry data quality 時，先看資料是否完整與新鮮，再看不同訊號之間是否能互相對齊。

重點訊號包括：

- log / metric / trace 是否有 coverage 與 drop rate
- schema 是否有版本與 drift 偵測
- sampling 是否保留錯誤、高延遲與低流量樣本
- timestamp 是否能支援 [incident timeline](/backend/knowledge-cards/incident-timeline/) 還原
- dashboard 是否標示資料延遲、缺口與查詢範圍

| 品質面向 | 最小可用判準                 | 失真後果                    |
| -------- | ---------------------------- | --------------------------- |
| 完整性   | drop rate、coverage 可被量測 | 事故定位依賴不完整證據      |
| 一致性   | 欄位語意與命名跨服務一致     | 事件鏈需要人工拼接          |
| 代表性   | sampling 覆蓋高風險樣本      | 錯誤被平均化，誤判風險      |
| 時間性   | timestamp 與 delay 可追蹤    | timeline 錯序，決策先後顛倒 |

## 缺漏與漂移

缺漏是 telemetry data quality 最容易造成錯誤安全感的問題。缺漏發生時，圖表通常不會直接報錯，而是呈現較低的流量、較少的錯誤或不完整的 trace。

| 缺漏類型       | 真實服務樣貌                        | 判讀風險                      |
| -------------- | ----------------------------------- | ----------------------------- |
| Missing signal | 新服務路徑沒有 instrument           | 核心旅程失敗但 dashboard 正常 |
| Partial trace  | async job 或 queue consumer 缺 span | 事件鏈停在同步 request        |
| Dropped log    | ingest burst 時 log 被丟棄          | 錯誤率下降被誤判為恢復        |
| Stale metric   | scrape 成功但資料停在舊 timestamp   | incident timeline 被拉歪      |

Missing signal 代表觀測需求沒有覆蓋服務路徑。常見場景是新 feature flag 開啟後走到新 code path，但 SLI、log schema 與 trace 還停在舊路徑。

Partial trace 代表跨邊界 context 缺少完整傳遞。request 進入 queue 後，如果 message 缺少 correlation id 或 consumer 缺少 span，團隊只能知道 request 發出去，背景流程的失敗時間與失敗點會留在盲區。

Dropped log 代表資料流量超過 pipeline 或成本限制。burst error 發生時，如果 log pipeline 開始 sampling 或丟棄，事故團隊看到的錯誤量會比真實狀態少。

Schema drift 是長期維護最常見的品質問題。欄位改名、label 粒度改變、service name 不一致、semantic convention 升級，都會讓查詢與 dashboard 在沒有明顯錯誤的情況下失準。

## Sampling 與代表性

Sampling 的責任是控制觀測成本，同時保留足以判讀的高價值樣本。sampling policy 若只按固定比例抽樣，最容易丟掉低頻但高風險的事件。

| Sampling 風險          | 失真方式                    | 控制面                                   |
| ---------------------- | --------------------------- | ---------------------------------------- |
| Low-traffic bias       | 低流量服務樣本太少          | 對低流量服務設定 minimum sample floor    |
| Error sample loss      | 錯誤 request 被普通比例抽掉 | 對 error、timeout、high latency 強制保留 |
| Tenant skew            | 大 tenant 壓過小 tenant     | 以 tenant 或 plan 做分層 sampling        |
| Cardinality truncation | 高維度 label 被截斷或合併   | 標示 truncation，保留 top-K 與 overflow  |
| Tail latency loss      | 長尾 latency 被平均值掩蓋   | 使用 histogram 與 exemplar               |

Low-traffic bias 會讓小服務或小 tenant 的問題長期不可見。這些路徑平時量小，但可能承擔高價值客戶、管理操作或資安事件；抽樣策略需要保留最低樣本量。

Error sample loss 會直接破壞事故判讀。錯誤、timeout、retry exhausted、DLQ、payment failure 與 authorization failure 應該有更高保留權重，因為它們代表決策價值高於普通成功 request。

Cardinality truncation 需要明確揭露。當平台為了成本截斷 label 或聚合 tenant 維度時，dashboard 應標示資料限制，讓讀者知道當下看的是聚合視角與可用粒度。

## 時間對齊

時間對齊是 incident timeline 的基礎能力。事件發生時間、採集時間、寫入時間、查詢時間與顯示時區若未分清，事故復盤會把原因與結果順序看反。

| 時間問題           | 常見來源                         | 事故後果                     |
| ------------------ | -------------------------------- | ---------------------------- |
| Clock skew         | host、container、client 時鐘不同 | 事件先後被重排               |
| Ingest delay       | exporter queue 或 indexing lag   | 告警與圖表晚於真實事件       |
| Out-of-order event | async pipeline 或 retry 寫入     | 同一 trace 的 span 順序錯亂  |
| Timezone mismatch  | 人工紀錄與平台顯示時區不同       | 對外通訊與內部 timeline 衝突 |

Clock skew 會讓跨服務事件鏈失去可信度。若 API、worker、database proxy 與 observability collector 的時間基準不同，trace 中的等待點可能看起來是負時間或錯誤順序。

Ingest delay 會影響事中決策。incident commander 看到 error rate 下降時，需要知道資料是即時下降，還是 pipeline 還沒收完高峰區段。

Timezone mismatch 常出現在 status page、support ticket、vendor notice 與內部 timeline 對接時。所有事故證據都應保留原始時間與標準化時間，避免復盤時重排錯誤。

## 判讀訊號

- 同一事故在 log、metric、trace 中呈現不同時間線
- service name / region / tenant label 在不同系統拼不起來
- 低流量服務的錯誤被 sampling 稀釋
- pipeline drop 發生但 dashboard 沒提示資料缺口
- post-incident review 發現判讀基於不完整資料

常見場景是「圖看起來穩，但資料在悄悄掉」。例如 ingest 層 partial drop 後 error rate 下降，看似健康，實際是訊號少了高風險區段。這類情況若沒有資料品質指標，會讓事故決策建立在錯誤安全感上。

## 控制面

Telemetry data quality 的控制面是把資料限制顯性化。資料品質不需要追求完美，但需要讓讀者知道目前能相信什麼、限制在哪裡、何時需要改用其他 evidence。

1. 為每種 telemetry 設定品質指標。
2. 在 dashboard 標示 freshness、coverage 與 known gap。
3. 對 schema drift、drop rate 與 sampling policy 建立告警。
4. 在 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 記錄資料限制。
5. 在 post-incident review 中回寫造成判讀錯誤的資料品質缺口。

品質指標本身也需要 owner。平台團隊可以維護 pipeline drop、ingest delay 與 semantic convention；服務團隊需要維護 service-specific schema、business event 與 user journey coverage。

資料限制應直接出現在操作入口。若某 dashboard 的 trace sample 只保留 10%、某 tenant label 被聚合、某時間區段有 log gap，讀者應在同一個畫面看到限制，並把限制納入當下決策。

## 常見反模式

Telemetry data quality 的反模式來自把查詢結果視為事實本身。查詢結果只是資料產品的輸出，仍然受採集、轉換、抽樣、儲存與查詢限制影響。

| 反模式               | 表面現象                            | 修正方向                        |
| -------------------- | ----------------------------------- | ------------------------------- |
| dashboard 即事實     | 圖表下降就判斷服務恢復              | 顯示資料延遲與 coverage         |
| schema 漂移無治理    | 查詢突然少資料但沒人知道            | 欄位版本與 drift 偵測           |
| sampling policy 黑箱 | 錯誤樣本被抽掉仍用比例推估          | 公開 sampling policy 與例外規則 |
| timeline 單時間戳    | 只記顯示時間，不記事件原始時間      | 同時保留 event / ingest / query |
| 成本截斷不標示       | 高 cardinality 被合併但仍當完整資料 | 標示 truncation 與聚合粒度      |

dashboard 即事實會讓事故決策失去資料謙遜。圖表顯示健康時，仍要確認資料有沒有缺口、延遲或抽樣偏誤，尤其在 pipeline 自身承受壓力時。

sampling policy 黑箱會降低服務團隊的風險判讀品質。平台可以為成本抽樣，但抽樣規則要能被服務團隊理解，並且允許錯誤、高延遲與低流量關鍵路徑保留更高權重。

## 與 SLO 和事故的關係

Telemetry data quality 是 SLO 與事故 evidence 的可信度前提。SLI 若建立在失真資料上，error budget、burn rate alert 與 release freeze 都會被錯誤資料牽動。

在 SLO 場景中，資料品質缺口會直接改變可靠性政策。若 availability SLI 漏掉 mobile client、region label 漂移、error sample 被抽掉，團隊會高估可靠性並繼續放行高風險變更。

在事故場景中，資料品質限制需要進入 [incident decision log](/backend/08-incident-response/incident-decision-log/)。當 IC 做出升級、降級、等待或 rollback 決策時，應同時記錄當下 evidence 的 completeness、freshness 與 confidence。

## 交接路由

- 04.1 log schema：治理欄位漂移
- 04.7 cardinality / cost：處理高維度截斷與成本取捨
- 04.11 telemetry pipeline：追查 drop、delay 與 ingest 問題
- 04.14 anomaly detection：避免模型學到偏誤資料
- 08.19 incident decision log：標記事中判讀使用的資料品質限制
