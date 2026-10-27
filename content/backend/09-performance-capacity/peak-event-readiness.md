---
title: "9.11 高峰事件準備"
date: 2026-05-12
description: "可預期峰值從 T-90 到 T-0 的準備時程：容量計畫、quota 申請、壓測、game day 與 pre-scaling 各排在事件前幾天、排在那裡的理由與項目之間的依賴，pre-scaling 的做法、watch room、event tier 分級與準備時間不夠時被壓縮的部分，以及事後 retro"
weight: 11
tags: ["backend", "performance", "capacity", "peak-event"]
---

## 概念定位

高峰事件準備的責任是把「事件臨頭才動手」變成「事前數週流程化準備」。沒有 readiness 流程時、年度活動靠 oncall 臨場處理、出事率高；有流程之後、活動成「routine event」、工程資源穩定釋放。

本章 *是* [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/) 跟 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 在「事件型場景」的應用組合、不重新建立方法論。要看具體方法回到那兩章、本章聚焦在 *流程整合*。

讀完後讀者能設計一個 T-90 → T-0 的事件準備時程、回答「Black Friday 該怎麼準備、Super Bowl 該怎麼準備、新片發布該怎麼準備」。

## 事件分類：五種負載形狀

不同事件對應不同準備強度、第一步要分類。

**可預期極端峰值**：年度活動、預售、賽事決賽。提前數月已知時間、業務影響大。例：Prime Day、Black Friday、Super Bowl、IPL 決賽。日期可預期，需求仍可能超出預測：Coinbase 在超級盃廣告前做過壓測，實際流量仍超出預測而暫時節流，超出預測時的承接機制見 [9.15 無預警瞬時大流量：流量來源辨識、擴展緩衝、請求優先等級、准入控制、體積型攻擊與退路](/backend/09-performance-capacity/unplanned-traffic-surge/)。
**事件型不可預期峰值**：賽事高潮、突發新聞、KOL 推廣。時間或大小不完全可預測。例：賽事進球瞬間、KOL 帶貨、突發新聞引發的流量。
**Flash-sale 瞬間爆量**：售票開賣、報名活動、限量搶購。t=0 瞬間爆量、5-30 分鐘結束。例：演唱會售票、限量商品搶購、報名截止前最後一小時。開賣當下的等候室與事前註冊見 [9.15 無預警瞬時大流量：流量來源辨識、擴展緩衝、請求優先等級、准入控制、體積型攻擊與退路](/backend/09-performance-capacity/unplanned-traffic-surge/) 的〈准入控制：虛擬等候室（virtual waiting room）、waitlist 與事前註冊〉。
**產品爆紅 surge**：新 app 紅、病毒擴散。完全不可預期、流量會隨熱度消退。例：Pokemon GO、ChatGPT 爆紅初期、TikTok challenge。這一類與事件型不可預期峰值沒有準備時程可排，承接的機制見 [9.15 無預警瞬時大流量：流量來源辨識、擴展緩衝、請求優先等級、准入控制、體積型攻擊與退路](/backend/09-performance-capacity/unplanned-traffic-surge/)。
**結構性 surge**：COVID 類外部衝擊、永久 baseline 上移。不會回到舊水準。例：COVID 期間遠距工作工具、烏俄戰爭期間能源類 app。

對應案例：[AWS Prime Day 2025、Disney+ Hotstar、ASOS、Disney+、NTT DOCOMO Lemino](/backend/09-performance-capacity/cases/)（predictable）/ [GR8 Tech、DraftKings、Lyft、FanDuel](/backend/09-performance-capacity/cases/)（event）/ [拓元 Tixcraft、SeatGeek、BookMyShow](/backend/09-performance-capacity/cases/)（flash-sale）/ [Niantic Pokémon GO、Zoom](/backend/09-performance-capacity/cases/)（surge）。

## T-90 → T-0 準備時程

可預期極端峰值的完整準備時程。時程上的項目之間有輸入與輸出的依賴：一台主機在目標利用率下的處理量是容量計畫換算台數的輸入；容量計畫算出的台數是 quota 申請與 pre-scaling 規格的輸入，算出的峰值請求量是壓測要送出的請求量；壓測量到的膝點（請求量再往上加、延遲就開始上升的那一點，[Saturation Point](/backend/knowledge-cards/saturation-point/)）是降級觸發門檻的輸入。沒有台數的服務（按請求計費的 serverless），台數的位置換成同時執行數（峰值請求量 × 平均執行時間），quota 申請的是並行上限，膝點與降級門檻落在下游那一層（資料庫、外部 API）。目標利用率是膝點處理量的一個小於一的比例，目標利用率對應的處理量因此低於膝點；兩者之間留出的餘裕吸收秒級的波動與故障，也涵蓋降級開關生效之前負載爬升的量（[預知的大流量要加多大、編多少預算：從業務預估到擴容規格與費用區間的換算鏈、給決策者與會計的數字，以及每次活動之後的校準](/operations/05-capacity-planning/planned-peak-sizing-and-budget/)〈從業務預估到台數：換算鏈、換算係數的來源與三點估計〉）。每個 T 點離事件多遠，取決於那一項的產出要交給哪幾項，以及它發現的狀況（壓測找到的瓶頸、被拒的 quota 申請、演練時沒有生效的降級）要多久修好；T-2 的 pre-scaling 另外是計費時數的取捨。

**T-90 天**：流量 forecast + 容量計畫敲定。確認峰值請求量：從業務預估經換算鏈算出，預估的誤差用保守、預期、樂觀三點估計帶著，各自換算出台數（[預知的大流量要加多大、編多少預算](/operations/05-capacity-planning/planned-peak-sizing-and-budget/)〈從業務預估到台數：換算鏈、換算係數的來源與三點估計〉；沒有歷史峰值時的起步在同一篇〈每次活動之後的校準，以及沒有歷史資料時的起步〉）。確認 headroom 比例（[Headroom Budget](/backend/knowledge-cards/headroom-budget/)）：用三點估計帶預估的誤差時，headroom 只涵蓋秒級的波動與故障，不再把預估的誤差算進去一次。確認跨 region / AZ 分布。產出 *容量計畫文件*。容量計畫換算台數用的單台處理量沿用最近一次壓測量到的值；服務是新的、從來沒量過時，先用同一種機型做一次小規模的階梯加壓量出單台的值，再敲定容量計畫。T-14 的壓測量完之後回頭校正台數。

**T-30 天**：基礎設施 quota 申請。雲端 instance limit、connection pool、API rate limit、DynamoDB throughput、Lambda concurrency 都要 *提前申請*、不能事件當天才發現 quota 不夠。AWS Infrastructure Event Management（IEM）等服務在這階段啟動。查上限與申請調高的位置見 [雲端主控台的管理領域](/infra/cloud-providers/console-areas/)〈配額與限制：帳號最多能開多少〉。排在這裡的原因：業者不一定當場核准，也可能拒絕，而 T-14 的正式規模壓測也要用到這份 quota。申請時的台數還沒經過 T-14 壓測的校正，所以申請量取容量計畫的保守那一點，再加上活動中補容量的餘裕；quota 調高之後最大花費速度跟著變大，停損的門檻與信用卡額度要依新的值重算（[預知的大流量要加多大、編多少預算](/operations/05-capacity-planning/planned-peak-sizing-and-budget/)〈從台數到預算：計費時數、計費模式、跟著用量計費的項目與付款時點〉）。壓測校正之後的保守點台數仍然超出已核准的 quota 時，T-14 之後要再申請一次，這一次能等核准的時間比 T-30 那一次短。申請被拒時，能開的台數停在已核准的 quota，超出的處理量交給降級、等候室或改活動形式（分批或錯開開放，壓低同一時段湧入的比例；同一篇〈給決策者的選項：規格、費用區間、不足時的後果、回退方式與適合的條件〉），不需要即時回應的寫入另外可以先進 queue（[Queue 緩衝](/operations/07-burst-traffic/queue-buffering/)）；這幾項本身也要準備時間，所以申請排在壓測與 game day 之前。

**T-14 天**：第一輪 production-like 壓測。用階梯加壓（ramp-up）把請求量逐步提高到預期峰值以上、量出各層的膝點（[規模拐點判斷](/operations/05-capacity-planning/scaling-inflection-point/)〈用 ramp-up 找膝點，不用單點壓測〉），驗證在預期峰值的請求率下延遲與錯誤率是否仍在 SLO 內、找出第一輪 bottleneck。排在這裡的原因：要留出修正瓶頸、再測一次的時間，量到的單台處理量也要回頭校正容量計畫的台數。資料庫這類瓶頸的修法（加索引、拆分讀寫、換規格）修完之後要重跑一次壓測。測試環境的資料量、快取命中率或依賴跟 production 不同時，量到的膝點會偏高；用 production traffic replay 或 shadow traffic 量到的比較接近 production（[9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)），代價是送出的是平常的流量組成，不是活動當天的組成。台數校正之後，增量費用照預算的算法重算，超出已核准的預算時在活動前送追加。

**T-7 天**：完整 game day 演練。注入故障場景（DB failure、AZ outage、第三方 quota 耗盡）、驗證降級、failover、rollback 流程。修正最後問題、更新 runbook。降級的觸發門檻從 T-14 量到的膝點推出，所以 game day 排在壓測之後。門檻的預設值是：目標利用率對應的單台處理量 × 活動當天實際開得出的台數（quota 沒核准到計畫的台數時，用已核准的台數），讓降級在延遲開始上升之前生效；觸發點與膝點之間的餘裕，至少要涵蓋降級開關生效之前負載會爬升的量，開關要重新部署才生效時，觸發點要再往下移。測試環境的資料量、快取命中率或依賴跟 production 不同（T-14 那一項）時，膝點可能偏高，另外用 p99 延遲接近 SLO 當第二道觸發條件，兩道哪一道先到就先降級。演練時降級沒有觸發、或觸發之後沒有生效，T-7 到 T-2 之間還有時間修正。

**T-2 天**：pre-scaling 開始。CDN cache pre-warm、Lambda provisioned concurrency 啟動、autoscaler scheduled 開始、DB capacity 預先 scale up。避免事件當天還在 boot。排在這裡的原因：加開的實例開得越早，建立時回傳容量不足、或加開之後發現規格不對時，越有時間換機型或換可用區；代價是計費時數從加開那一刻起算。快取與連線的預熱本身通常要 30 分鐘到 2 小時（下面〈Pre-scaling 策略〉的 pre-warm window），起點只依預熱與加開之後驗證規格的時間決定時，是事件前幾小時。也可以先建立容量預留（capacity reservation），確保當天開得出機器，再在事件前幾小時加開與預熱，預留從建立那一刻起計費。各種起點的費用算法在 [預知的大流量要加多大、編多少預算](/operations/05-capacity-planning/planned-peak-sizing-and-budget/)〈從台數到預算：計費時數、計費模式、跟著用量計費的項目與付款時點〉。

**T-0 day**：watch room 待命、runbook 開機可執行。所有相關 oncall 跨團隊聯合 channel、dashboard 集中、escalation path 清楚。值班表在 T-0 之前排好；值班持續到事件結束之後、每秒請求數回到平常的水準並維持一段時間為止（流量有日週期時，觀察到隔天同一時段，才看得到回流的使用者），之後才縮回 pre-scaling 加開的實例。

**T+7 天**：retro。對比預測 vs 實際、紀錄 incident 跟 near-miss、列下個事件要改的事。寫進 [06 cases](/backend/06-reliability/cases/) 或本模組 cases。

## Pre-scaling 策略

T-2 階段的 pre-scaling 是「不依賴 autoscaler 反應」的容量保險。

**Pre-scaling 涵蓋層次**：

- **ELB warm-up**：請 AWS 預先 warm up ELB，避免流量上來時 ELB 自身需要時間擴容
- **Lambda provisioned concurrency**：預先 boot 一定數量 instance、避免 cold start
- **DynamoDB / Cosmos DB capacity**：scheduled 提前 scale up
- **EC2 ASG**：min instances 提前拉高
- **CDN cache pre-warm**：重要 URL 提前 invalidate / pre-populate
- **DB connection pool**：應用層提前 warm up connection
- **Cache warmup**：把 hot key 提前 populate 進 cache

**Pre-warm window 通常 30 分鐘到 2 小時**、取決於：

- Instance boot time（VM-based 慢、container 快）
- Cache warmup 時間（cold cache 命中率低、要時間 populate）
- Connection pool 預熱（DB connection establish 有 latency）

### CDN Pre-warm 操作細節

CDN pre-warm 在 T-2 階段是 high-impact 操作、但跟其他 pre-scaling 的特性不同。具體做法：

- **找出活動會大量被讀取的 URL 清單**：商品頁、活動 landing page、新 release 內容
- **在每個 CDN edge POP 觸發 cache populate**：可以用 vendor warmup API（Cloudflare Argo、Fastly Image Optimizer pre-fetch、Akamai NetStorage push），或從多個 region 發 synthetic request 強制 edge 拉取
- **驗證 hit ratio 已升高**：用 vendor dashboard 觀察 cache_status=HIT 比例、確認 pre-warm 生效
- **預估 origin 流量曲線**：pre-warm 完成後、活動開始時 edge miss 流量應該大幅降低、origin 容量規劃可以對應放鬆

跟其他 pre-scaling 不同的是 **CDN pre-warm 沒有「容量上限」這個概念** — edge cache 是被動填的、warm 完就是 warm、不像 EC2 / Lambda 那樣需要 reserve 容量。風險不在「填不夠」、在「填錯」（key 不對、TTL 設錯讓 pre-warm 立刻過期；CDN 的 TTL 從哪個標頭取見 [12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限](/backend/12-http-caching/freshness-lifetime/)，只給 CDN 一個期限（`CDN-Cache-Control`）見 [12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/) 的〈把指令指定給特定快取：CDN-Cache-Control〉）。詳見 [5.9 邊緣分發](/backend/05-deployment-platform/edge-cdn-static-distribution/) 的 purge 與 cacheable 判讀。

**事件結束後也要 *scheduled scale down***：autoscaler 通常 scale up 快、scale down 慢、長期 over-provision 浪費錢。

對應案例：[Tixcraft 30 分鐘擴 130 倍](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — pre-scaling + Auto Scaling Group + AMI prebuild + ELB warmup 組合；[Prime Day pre-scaling](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) — predictive scaling + scheduled scaling 兩種組合。

詳見 [Predictive Scaling 卡片](/backend/knowledge-cards/predictive-scaling/) 跟 [Scheduled Scaling 卡片](/backend/knowledge-cards/scheduled-scaling/)。

## Watch room 設計

T-0 當天的指揮中心、跨團隊聯合 channel。

**人員配置**：

- 跨團隊聯合 channel：app / infra / network / SRE / business / customer support
- 24/7 輪班（國際事件可能跨 24 小時）
- 明確 incident commander（[08.7 incident command roles](/backend/08-incident-response/incident-command-roles/)）

**Dashboard 集中**：

- 流量 dashboard：總 RPS、按 region 拆分、按 endpoint 拆分
- 延遲 dashboard：p50 / p95 / p99 即時、按 service 拆分
- 錯誤 dashboard：error rate、按 endpoint、按 status code
- 成本 dashboard：當前 hourly cost、預估全天 cost
- 業務 dashboard：訂單數、轉換率、收入

**Runbook 隨手可用**：常見問題 → 對應動作的明確指引。不要事件當下還在 wiki 找資料。

**Escalation path**：什麼狀況找誰、多久升級。寫成決策樹、不要靠人記。對應 [08.7 incident command roles](/backend/08-incident-response/incident-command-roles/)。

對應 [Game Day 卡片](/backend/knowledge-cards/game-day/)。

## Vendor 緊急支援

戰略事件可以申請 vendor 工程師待命、是「人力 backup」。

**AWS Infrastructure Event Management（IEM）**：年度重大事件可以申請、提供 pre-scaling 與專屬監控通道。
**GCP Customer Reliability Engineering（CRE）**：戰略客戶的 24/7 工程支援、能即時為客戶補容量。
**Azure Premier Support + CSAM**：對等服務。

**注意**：這類服務通常綁定 enterprise 等級合約、不是所有客戶都能用。設計事件準備時要假設「沒有 vendor 救援」、vendor 是 bonus 而非 primary plan。

對應案例：[GR8 Tech World Cup IEM](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) — AWS Infrastructure Event Management 在 2022 FIFA World Cup 期間支援；[Pokemon GO CRE](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/) — 流量達到原先預估的 50 倍時，GCP CRE 即時補上容量。

## Game day 演練

T-7 階段的核心活動、把 readiness 從計畫變實戰。

**演練場景**：

- 模擬「事件當天 worst case」
- 注入故障：DB primary failure、AZ outage、第三方 quota 達標、network partition
- 演練降級：哪些功能關閉、用戶看到什麼
- 演練 failover：流量切到備援
- 演練 rollback：發現新版本問題、能不能快速回退

**Game day 學習目標**：

- runbook 不夠詳細 → 補
- 訊號不夠 → 加 metric / alert
- 人員不夠 → 排班補
- 工具不夠 → 工程補

對應 [06 cases Shopify game day](/backend/06-reliability/cases/shopify/) — Shopify game day 是業界範本、值得直接參考。

## Event tier 分級

不同事件規模對應不同準備強度、不能一律照 T-90 流程跑。

**Regular event**（每週 promo、small feature launch）：

- scheduled scaling 即可
- 無 dedicated watch room
- 對應 [06.8 release gate](/backend/06-reliability/release-gate/) 的常規 release

**Major event**（季度行銷、新功能發布）：

- pre-scaling + watch room
- 簡化版流程：容量計畫與 quota 申請照樣要做（單台處理量可以沿用最近一次壓測的值），準備時間至少要排得進 quota 核准的等待；從 T-14 起的壓測與 game day 縮減輪數
- 跨 team coordination

**Critical event**（年度大促、Super Bowl、IPL）：

- 完整 T-90 流程
- vendor IEM + game day
- 24/7 watch room
- C-level visibility

事件的準備時間比它所屬等級需要的時間短時（例如從公布到舉辦只有一週的 Major event），項目之間的依賴不變，準備的團隊能壓縮的是每一項之後的修正時間；quota 核准、業者的事件支援這類由業者決定的等待時間壓縮不了，排不進去時那一項整個拿不到。壓測測出資料庫的瓶頸時，修完之後重跑壓測的時間排不進去，降級門檻沿用最近一次量到的膝點，而那一次之後改過的查詢與依賴會讓這個值偏離現況，所以 p99 延遲接近 SLO 的那一道觸發（T-7 那一項）照樣要設。來不及壓測時，另一條路是用偏高的係數加開，代價是規格與預算變大（[預知的大流量要加多大、編多少預算](/operations/05-capacity-planning/planned-peak-sizing-and-budget/)〈每次活動之後的校準，以及沒有歷史資料時的起步〉）。超出處理量的請求交給降級（關掉推薦這類功能，減少每個請求的查詢）、改活動形式或等候室；降級開關與等候室本身也要準備時間，準備時間短時能用的只有已經建好、演練過的那幾項。等候室的做法見 [9.15 無預警瞬時大流量：流量來源辨識、擴展緩衝、請求優先等級、准入控制、體積型攻擊與退路](/backend/09-performance-capacity/unplanned-traffic-surge/)〈准入控制：虛擬等候室（virtual waiting room）、waitlist 與事前註冊〉。

對應案例：[FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) regular game → playoff → Super Bowl 三 tier — NFL 賽季 baseline → playoffs 升 2-3x → championship 升 4-5x → Super Bowl 升 5-10x、每 tier 對應不同準備強度。

## 事後 retro

T+7 retro 是讓 readiness 持續改進的關鍵。

**Retro 必答的問題**：

- 流量 forecast 跟實際差多少？（forecast 改進方向）
- 容量 utilization 峰值多少？（headroom 是否合適）
- 有沒有 incident 跟 near-miss？（runbook 更新方向）
- 下個事件要改的事是什麼？

**Retro 產出**：

- forecast 改進建議（給 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)）
- 新 runbook 或 runbook 更新
- 新 monitoring / alert
- 新工程任務（補容量、補工具）

對應 [08.13 post-incident review](/backend/08-incident-response/post-incident-review/) — retro 不只用在 incident、event readiness 也需要。

## 案例對照

| 案例                                                                                           | 教學重點                        |
| ---------------------------------------------------------------------------------------------- | ------------------------------- |
| [Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)          | 可預期極端峰值教科書範本        |
| [Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)        | flash-sale T-2 pre-scaling      |
| [Hotstar IPL](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/) | 全球直播 watch room             |
| [GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)         | AWS IEM + 自家 AI 預測組合      |
| [FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)         | event tier 分級（playoff → SB） |
| [Pokemon GO](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)     | surge 場景的 vendor 救援（CRE） |

## 下一步路由

- 上游：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) / [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)
- 上游：[9.13 擴展軸](/backend/09-performance-capacity/scaling-axes/)（pre-scaling 前要分辨可不可水平擴展）
- 跨模組：[5.9 邊緣分發與靜態資源](/backend/05-deployment-platform/edge-cdn-static-distribution/)（CDN pre-warm / origin protection 是 T-2 核心）
- 平行：[9.15 無預警瞬時大流量：流量來源辨識、擴展緩衝、請求優先等級、准入控制、體積型攻擊與退路](/backend/09-performance-capacity/unplanned-traffic-surge/)（沒有準備窗口時的流量來源辨識、擴展緩衝、負載卸除與准入控制）
- 跨模組：[06.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/) / [08 事故處理模組](/backend/08-incident-response/)
- 跨模組：[預知的大流量要加多大、編多少預算：從業務預估到擴容規格與費用區間的換算鏈、給決策者與會計的數字，以及每次活動之後的校準](/operations/05-capacity-planning/planned-peak-sizing-and-budget/)（T-90 容量計畫裡的規格與預算：從業務預估換算峰值請求量、各層台數與費用區間，以及給決策者的選項與給會計的數字）

## 既建知識卡片

- [Predictive Scaling](/backend/knowledge-cards/predictive-scaling/)
- [Scheduled Scaling](/backend/knowledge-cards/scheduled-scaling/)
- [Game Day](/backend/knowledge-cards/game-day/)
- [Peak Forecast](/backend/knowledge-cards/peak-forecast/)
- [Headroom Budget](/backend/knowledge-cards/headroom-budget/)
- [Saturation Point](/backend/knowledge-cards/saturation-point/)
