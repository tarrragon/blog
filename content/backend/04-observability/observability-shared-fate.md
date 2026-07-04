---
title: "4.25 觀測共命運失效：工具退化時的訊號與人層設計"
date: 2026-07-04
description: "觀測系統跟被觀測系統共享失效域、在最需要時一起退化；out-of-band 訊號、優雅降級、以及工具盲飛時客服與工程師怎麼還能應對"
weight: 25
tags: ["backend", "observability"]
---

## 大綱

- 共命運失效的三種機制：依賴耦合、反噬、供應商單點
- out-of-band 訊號：獨立失效域的存活與狀態通道
- 優雅降級：觀測系統過載時保住高價值樣本
- 人層應對：telemetry 不可信時客服與工程師的設計
- 判讀訊號、反模式、交接路由

## 概念定位

觀測共命運失效指觀測系統跟它監控的系統共享失效域、在事故壓力下一起退化 —— 而它退化的時刻，正好是你最需要它的時刻。本章的責任是把「觀測會在事故中失能」當成設計輸入：不是假設儀表板永遠可用、再談怎麼判讀訊號（那是 [4.3](/backend/04-observability/tracing-context/)、[4.6](/backend/04-observability/sli-slo-signal/) 的前提），而是假設它會失能、為那個時刻預先設計 out-of-band（獨立於生產棧的旁路）訊號、優雅降級、以及人在盲飛下的應對。

這章跟 [08 事故處理](/backend/08-incident-response/) 的分工是一條窄線：08 講事故的完整角色、指揮鏈、通訊節奏、客訴 intake；本章只截「觀測工具本身退化 / telemetry 不可信」這個特定約束下、哪些設計仍能運作。判準是「工具可靠時就不需要它、工具退化時它才變關鍵」。

## 共命運失效的機制

觀測跟系統共命運不是單一現象、有三種不同機制、修法也不同。

**依賴耦合**是最根本的一種。Google SRE Book 的立論是：觀測系統若跟被觀測系統一樣複雜、依賴一樣多，它會在同樣的壓力下一起變 fragile —— 所以「the elements of your monitoring system that direct to a pager need to be very simple and robust」、規則要「as simple, predictable, and reliable as possible」（見 [4.C15](/backend/04-observability/cases/monitoring-simple-robust-sre-book/)）。這裡要標明推導邊界：SRE Book 沒有「觀測必須不共享失效域」的字面原句、「共命運」是從 simple / robust / fragile / loosely-coupled 這幾個原句推導的框架。啟示是把「叫醒人類」那條路徑的依賴壓到最少、讓它能獨立於生產棧存活。這條 simple 的約束只加在 alerting 的關鍵路徑上、不是要求整個 tracing 與分析棧都簡單 —— 大規模分散式追蹤本質複雜、該複雜的地方複雜、但決定「要不要 page 人」的那條路徑要能在生產棧全滅時獨立運作。

**反噬**是被觀測系統的異常行為把觀測後端打爆。正好在你要下 query 排障的時刻、被觀測系統反過來拖垮了觀測：事故時 error、user、request-id 這類維度會從低基數突然 spike 成高基數（[cardinality](/backend/knowledge-cards/metric-cardinality/) spike）、而 Prometheus 這類 TSDB「every unique combination of key-value label pairs represents a new time series」、高基數會「lead to memory errors and system crashes」（見 [4.C16](/backend/04-observability/cases/cardinality-explosion-incident/)）。這不是外部依賴掛掉、是被觀測系統透過 label 反噬觀測後端。反噬還有兩條打在被觀測服務自己身上的路徑：log 暴量塞爆磁碟、把服務本身也拖垮；觀測 agent 或 sidecar 在高負載時跟服務爭 CPU 與記憶體。修法在 label 白名單與高基數維度的隔離（見 [4.7](/backend/04-observability/cardinality-cost-governance/)）、log 的容量上限與 agent 的資源上限。

**供應商單點**是把「我有沒有事」外包給單一觀測供應商、供應商自己掛。Datadog 2023-03-08 事故裡、客戶的「monitors were unavailable and not alerting」、根因是一個跨區同時觸發的自動更新打到多個本應獨立的部署（見 [4.C18](/backend/04-observability/cases/datadog-2023-monitoring-as-dependency/)）—— 觀測層變成客戶事故的放大器：系統可能沒事但看不到、或有事但沒被叫醒。這是 [correlated failure](/backend/knowledge-cards/correlated-failure/) 的典型：以為獨立的部署共享同一個觸發器。

GitLab 2017 事故把前兩種機制合在一起演了一遍：備份失敗的告警走 email、但「DMARC was not enabled... resulting in them being rejected」、於是「we were never aware of the backups failing, until it was too late」（告警管道靜默失效 —— 沒人監控「告警本身有沒有送達」、這種對監控鏈自己的監控就是 meta-monitoring）；事故發生時公開監控頁又被使用者流量壓垮（儀表板容量共命運）（見 [4.C17](/backend/04-observability/cases/gitlab-2017-silent-monitoring-failure/)）。

## Out-of-band 訊號：活在生產棧之外的證人

共命運的解是準備一個獨立失效域的 out-of-band 訊號 —— 把觀測做得更可靠救不了它、它總會有自己的失效域；真正管用的是當內部觀測全黑時、還有一個活在生產棧之外的訊號能回答「系統死沒死」。

存活訊號有兩種互補形態。**心跳消失**：kube-prometheus 的 Watchdog alert「is always firing」、它停止觸發就代表告警管線本身斷了、由一個獨立失效域的外部偵測器（如 Dead Man's Snitch）判斷心跳消失並通知（見 [4.C19](/backend/04-observability/cases/watchdog-dead-mans-switch/)）—— 因為監控系統自己死了時、它發不出「我死了」的告警。**外部探測**：blackbox / synthetic 從外部 vantage point 主動打 endpoint、資料來源與被測系統解耦。兩者的共同設計是把存活判斷交給不依賴被測系統自己上報的證人。

對外的狀態通道同理。[status page](/backend/knowledge-cards/status-page/) 的失效域必須跟主服務切開 ——「when your website is down, so is your status page」、所以要放在獨立 domain、獨立 infra、甚至獨立 DNS（見 [4.C20](/backend/04-observability/cases/independent-status-page-fault-domain/)）。這不只是給用戶看：內部儀表板全黑時、status page 是客服對用戶、用戶對自己唯一可信的狀態源 —— 它同時是 out-of-band 訊號的對外播報端。

## 優雅降級：過載時保住高價值樣本

觀測系統在事故壓力下會逼近自己的容量上限、這時的設計問題是怎麼降級。差的降級是無差別丟資料（採樣率一律砍、把你要的那條 error trace 也丟了）；好的降級是有選擇地保住診斷價值最高的樣本。

tail sampling 是這個原則的具體做法：head [sampling](/backend/knowledge-cards/sampling/) 在 [trace](/backend/knowledge-cards/trace/) 開頭、資訊不全時就隨機決定去留、高錯誤率下要保留的 error / 慢 trace 常被丟掉；tail sampling 把決策延到整條 trace 到齊之後（latency policy 要用最早 start 與最晚 end 才算得出時長、本身就要等 trace 完整）、才依 policy（`status_codes: [ERROR]`、超過延遲門檻）保留（見 [4.C21](/backend/04-observability/cases/tail-sampling-preserve-errors/)）。但降級機制自己也有上限：tail sampling 的 `sampling_trace_dropped_too_early` 就是它記憶體超標時的降級失敗徵兆 —— 優雅降級不等於無限降級、要監控降級機制自己的飽和點。

同一個原則往上推是容量隔離：觀測前端與後端的容量要獨立於事故流量域（GitLab 的公開監控頁被事故流量壓垮就是沒隔離）、cardinality 要有預算擋住事故時的維度爆炸。

## 驗證備援：不測的備援是薛丁格的備援

前面幾種備援有一個共同的失敗模式：它們平時不觸發、所以沒人知道它們到底有沒有效。dead man's switch 可能因為外部偵測端配錯而從來不會在心跳消失時響、獨立 status page 可能其實跟主站共用了同一個 DNS、tail sampling 的降級路徑可能在真正過載時才發現 memory 上限設太低。判讀訊號裡「告警管道從沒被測過『告警本身會不會送達』」描述的是病徵、藥方是主動測。

驗證的做法是把觀測失效本身當成一個要演練的故障：刻意停掉 Alertmanager、確認 Watchdog 的消失真的觸發外部通知；故意灌高基數、確認降級路徑保住 error trace 而不是整個後端 crash；把主站切掉、確認 status page 仍可達（順便驗它沒偷偷共用主站的 DNS）。這條路由到 [6.4 chaos testing](/backend/06-reliability/chaos-testing/) 與 [08 演練與值班能力](/backend/08-incident-response/drills-and-oncall-readiness/) —— 觀測備援要進演練清單、跟服務本身的 chaos 實驗同一套紀律。

## 人層應對：telemetry 不可信時的設計

觀測退化時、盯著儀表板的人也在盲飛 —— 客服面對湧入的客訴、工程師拿不到可信 telemetry。這條線只收「工具退化」這個約束下的人層設計、完整的事故角色與流程在 [08](/backend/08-incident-response/)。下面三條的來源 framing 都是事故通用準備（SRE Workbook、PagerDuty）、把它們接到「觀測退化 / telemetry 不可信」這個約束是本章的論證、不是來源原文專講的。

**把不依賴當下狀態的決策提前固化**。SRE Workbook 的做法：預寫兩三個溝通模板（「No one wants to write these announcements under extreme stress」）、預定通訊通道、預備聯絡清單（見 [4.C22](/backend/04-observability/cases/sre-workbook-prewired-incident-response/)）。儀表板能自己說話時、即席溝通還撐得住；telemetry 不可信、人得靠零碎訊號拼圖時、認知頻寬全被「判斷現況」吃掉、沒餘裕再設計溝通 —— 預固化把「溝通這件事本身」從故障時的判斷負載裡移除。同一份紀律裡的 mitigation-first（「you don't have to fully understand the details—you only need to know the location of the root cause」）承認你不會有完整資訊、允許先止血；living document 則是 telemetry 不可信時的人肉狀態機、working theories 由人維護、工具全黑時它就是唯一的 dashboard。

**客訴是監控失效時的補位訊號**。Google Home 的事故裡、客戶的電話、推文、Reddit 貼文累積數天、內部監控沒把它升級、最後是客訴量把 bug priority 推到最高（見 [4.C23](/backend/04-observability/cases/google-home-customer-report-signal/)）—— 內部監控漏掉時、consumer 回報常是實際生效的那個訊號。但它是補位、不是主訊號：客訴有延遲（累積數天才成量）、有噪音（單一大客戶跟廣泛影響難分）、有誤報（用戶端問題被當成服務故障）—— 聚合（見下）就是給它降噪。out-of-band 的心跳與探測管的是「系統死沒死」、客訴管的是「哪個功能對誰壞了」、兩者互補。這條要設計兩件事：support-to-engineering 的升級路徑要低摩擦（否則客訴訊號延遲數天才轉成事故）、客訴裡的症狀與 [request-id](/backend/knowledge-cards/request-id/) 是可用的 telemetry 替代品（跟 [11.11 錯誤回報的回饋迴路](/backend/11-api-design/error-feedback-loop/) 的 request-id 契約接得上：consumer 手上的 id 讓盲飛下的定位仍有錨）。

**把客訴制度化成雙向管道**。PagerDuty 的 Customer Liaison 一邊把 incoming support requests 聚合成 IC（Incident Commander、指揮角色見 [08](/backend/08-incident-response/)）可用的 scope 訊號（「6 個客戶說沒收到通知」在監控失效時就是 [blast-radius](/backend/knowledge-cards/blast-radius/)（影響範圍）的量測）、一邊把確認過的狀態往外送（見 [4.C24](/backend/04-observability/cases/pagerduty-customer-liaison/)）。它的溝通紀律「Never lie, and never guess」在盲飛時尤其關鍵：內部都不確定發生什麼時、對外只講確認的、不猜 ETA、避免把盲飛狀態變成錯誤承諾。這條把散落的客訴訊號變成有人負責的通道 —— 也讓 out-of-band 的 status page cadence（沒有新資訊時「我們仍在處理」本身就是要發布的狀態）有了訊號來源。

這三條有個共同的難處：它們平時難為自己辯護 —— 沒事故時看不出價值、演練外很少被觸發、review 時最容易被當成過度準備砍掉。它們的 ROI 全押在「觀測退化的那一小時」、而那一小時平時看不到 —— 這正是「為共命運失效設計」最難落地也最需要紀律的地方。

## 判讀訊號

- 告警管道從沒被測過「告警本身會不會送達」（無 dead man's switch）
- 存活判斷全靠服務自己上報、沒有外部探測或心跳
- status page 跑在跟主服務同一個失效域（同 infra / 同 DNS）
- 事故時觀測後端因 cardinality spike 而變慢或 crash
- log 暴量塞爆磁碟、或觀測 agent 跟服務爭 CPU / 記憶體、把被觀測服務也拖垮
- 這些備援（dead man's switch、獨立 status page、降級路徑）從沒被演練驗證過
- 採樣在高錯誤率下把 error trace 一起丟掉（head-only sampling）
- 只有單一觀測供應商、沒有第二條獨立告警通道
- 溝通模板、通道、聯絡清單都要事故當下臨時決定
- 客訴訊號沒有低摩擦的 support-to-engineering 升級路徑

## 反模式

| 反模式                      | 表面現象                                                                  | 修正方向                                         |
| --------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------ |
| 告警管道無 meta-監控        | 告警靜默失效、沒人知道觀測已死                                            | dead man's switch、外部偵測心跳消失              |
| status page 同失效域        | 主站掛時 status page 一起掛                                               | 獨立 domain / infra / DNS 託管                   |
| head-only sampling          | 高錯誤率下 error trace 被採樣丟掉                                         | tail sampling 保留 ERROR 與尾延遲                |
| 觀測後端無 cardinality 預算 | 事故時維度 spike 把後端打爆                                               | label 白名單、高基數維度隔離                     |
| 單一觀測供應商無備援        | 供應商掛、monitors 全部不告警                                             | 第二獨立通道或 meta-monitoring                   |
| 溝通臨時起草                | [on-call](/backend/knowledge-cards/on-call/) 在高壓下即席寫公告、動作變慢 | 預寫模板、預定通道、預備聯絡清單                 |
| 客訴無升級路徑              | 客訴累積數天才被當事故                                                    | 低摩擦 support-to-engineering 升級、客訴聚合角色 |

## 交接路由

- [4.3 tracing 與 context link](/backend/04-observability/tracing-context/)：正常情況下的 trace 傳播（本章是它失能時的設計）
- [4.6 SLI 量測與 SLO 訊號設計](/backend/04-observability/sli-slo-signal/)：SLO 訊號正常可用時的判讀
- [4.7 cardinality 治理](/backend/04-observability/cardinality-cost-governance/)：cardinality 預算與 sampling 策略矩陣
- [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/)：pipeline 自身的失敗定位
- [08 事故處理](/backend/08-incident-response/)：完整的事故角色、指揮鏈、通訊節奏與客訴 intake（本章只截「觀測退化」約束）
- [11.11 錯誤回報的回饋迴路](/backend/11-api-design/error-feedback-loop/)：consumer 的 request-id / trace-id 回報契約，是客訴訊號源的另一端
- 案例原文：[可觀測性案例正文](/backend/04-observability/cases/)
