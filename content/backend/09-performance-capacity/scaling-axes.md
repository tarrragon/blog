---
title: "9.13 擴展軸與 Stateless 前提"
date: 2026-05-27
description: "整理垂直 / 水平擴展取捨、stateless vs stateful 前提、auto scaling 操作模型與兩種擴展的 hidden cost"
weight: 13
tags: ["backend", "performance", "scaling", "stateless"]
---

「要換更大的機器、還是要加更多臺機器？」這個問題在規模成長過程中會反覆出現。垂直擴展（scale-up）與水平擴展（scale-out）對應不同壓力來源、各自承擔不同代價：垂直擴展用「換更大的機器」換取簡單、水平擴展用「加更多機器」換取彈性。規劃容量時先判讀自己的壓力屬於哪一種、再選對應的擴展軸 — 選錯軸的代價會在事故時放大。

## 兩個軸的責任差異

垂直擴展指把單一機器換成更高規格（更多 CPU / 記憶體 / IOPS），水平擴展指增加機器數量。同樣是「加資源」，兩者面對的工程問題完全不同。

| 維度     | 垂直擴展（scale-up）                  | 水平擴展（scale-out）              |
| -------- | ------------------------------------- | ---------------------------------- |
| 操作單位 | 換一臺機器                            | 加 N 臺機器                        |
| 程式假設 | 不需要改                              | 必須是 stateless 或有狀態同步機制  |
| 容量上限 | 單機物理規格上限                      | 理論上線性擴展，實際受協調成本限制 |
| 成本曲線 | 規格升級非線性（高階機器溢價）        | 線性，但每臺要付 baseline 成本     |
| 故障代價 | 單點失敗影響整個服務                  | 一臺壞了還有其他臺、可分流         |
| 變更節奏 | 變更要停機或 failover、頻率低         | 隨時可加減、頻率高                 |
| 適合場景 | 資料庫主節點、stateful 服務、單點計算 | API、worker、無狀態服務            |

讀者要從「程式假設」這欄反推自己的選項。如果服務本身是 stateful（資料庫、cache、session store），水平擴展需要設計 partitioning 或 replication；如果是 stateless API server，水平擴展幾乎可以無腦複製。把這個前提搞錯，就會用水平擴展的策略去動 stateful 服務、然後撞牆。

## Stateless 是水平擴展的前提

Stateless 的核心定義是「處理一個請求不依賴前一個請求留下的本機狀態」。Session、本機快取、檔案系統暫存都會破壞 stateless 假設。

| 狀態類型           | 是否破壞 stateless | 緩解方向                                                                                      |
| ------------------ | ------------------ | --------------------------------------------------------------------------------------------- |
| Session 存本機     | 破壞               | 把 session 搬到外部 store（Redis、DB），改用 token 認證                                       |
| 上傳檔案存本機     | 破壞               | 改用物件儲存（S3、GCS）                                                                       |
| 本機快取           | 視情境             | 共用快取可接受（每臺 cache 各自 build）；強一致快取要外接                                     |
| WebSocket 長連線   | 破壞               | 用 [sticky session](/backend/knowledge-cards/sticky-session/) 或外部 broker（Pub/Sub、Redis） |
| 本機 cron / 排程   | 破壞               | 改用分散式排程（leader election 或外部排程服務）                                              |
| 跨請求的記憶體狀態 | 破壞               | 移到外部 state store                                                                          |

很多人以為自己的服務是 stateless、但一上水平擴展就出事，原因常常在這張表的某一行。判讀方式：把單一機器停掉、重新分配流量到其他機器，使用者體驗是否完全無感？如果有任何「重新登入」「上傳消失」「資料看不到」的情境，就有 stateful 殘留。

## Auto Scaling 的操作模型

水平擴展通常搭配 [auto scaling](/backend/knowledge-cards/autoscaling/) — 根據訊號自動加減機器數量。常見的擴展訊號跟對應的判讀重點：

| 訊號               | 反應速度 | 判讀重點                                               |
| ------------------ | -------- | ------------------------------------------------------ |
| CPU 使用率         | 中       | 通用、但對 I/O bound 服務失準                          |
| 記憶體使用率       | 慢       | 適合判 leak、不適合判尖峰流量                          |
| Request rate (RPS) | 快       | 適合 API 服務、需要設定 cool-down 避免抖動             |
| Queue depth        | 快       | 適合 worker 服務、queue 是天然 buffer                  |
| Latency P95        | 中       | 用戶體驗訊號、但已經出現延遲才擴展可能來不及           |
| 自訂業務訊號       | 視訊號   | 訂單數、活動人數，貼近業務但要自己維護 metric pipeline |

設定 auto scaling 的判讀順序：先選訊號（CPU vs RPS vs queue depth），再設閾值（避免過早觸發或過晚觸發），最後加 cool-down（避免反覆擴縮造成抖動）。三步驟有一步沒做好就會撞牆。

Auto scaling 不是萬靈丹。三類問題它無法解決：擴展速度跟不上（新機器啟動要 30 秒、流量尖峰只有 10 秒）、預測式流量（黑五、新片上線、活動）、stateful 服務（資料庫不能用 auto scaling 加 primary）。這三類要分別用 [predictive scaling](/backend/knowledge-cards/predictive-scaling/)、[scheduled scaling](/backend/knowledge-cards/scheduled-scaling/) 跟 partitioning 處理。

## 垂直擴展的天花板

垂直擴展看起來簡單但有兩道牆。

第一道是物理上限。雲端機型的最大規格是有限的：AWS 最大 EC2 instance 是 24 TiB 記憶體 / 448 vCPU 級別，再大就沒有了。撞到上限後沒辦法繼續垂直擴展，只能轉成水平擴展。

第二道是成本曲線。雲端機型的價格不是線性的，越高階的機型每單位資源越貴。對比：4 vCPU 機器月費 $X，8 vCPU 機器約 $1.8X 而非 $2X 看似划算，但到 96 vCPU 機器可能就接近 $30X，遠超線性外推。這個曲線意味著：垂直擴展到一定規模，就算物理上撐得住，財務上也不划算。

對 stateful 服務（特別是主資料庫），垂直擴展常常是第一選擇，因為水平擴展需要重新設計 partitioning。但要清楚兩道牆會在什麼時候撞上：基於目前流量增長率，預估垂直擴展能撐多久？多久之後必須改成水平擴展？這個答案要在「還沒撞牆時」就準備好，不是等到下一次撞牆才開始討論。

## 水平擴展的隱性成本

水平擴展看起來彈性、但有它自己的代價。

**協調成本**：多臺機器要處理「誰是 leader、誰來執行排程、誰來處理同一筆訂單」這類問題。leader election（一群節點選一個主來執行某類獨佔工作）、distributed lock、consensus protocol（如 Raft / Paxos、用來在多個節點間達成一致決策）都會引入新的故障模式。

**連線池放大**：100 臺機器、每臺對資料庫開 10 個連線，等於對 DB 開 1000 個連線。DB 連線是有限資源，水平擴展應用層的同時要評估資料層連線壓力。常見緩解：connection pooler（PgBouncer）、serverless DB（DynamoDB）、讀寫分離。

**狀態同步成本**：cache、session、配置這些「跨機器需要一致」的狀態，要靠外部 store 或 broadcast 機制同步。同步延遲跟頻率會反過來影響服務行為。

**Cold start**：新機器啟動到接流量需要時間（image pull、init container、warm-up）。auto scaling 觸發跟流量到達之間的延遲就是這段。冷啟動長的服務（JVM、需要載入大量資料的服務）要預留更多 buffer。

**Debug 變難**：請求散落在多臺機器，排查問題需要 log 聚合、trace context。沒有這些基礎設施，水平擴展只會把「一臺機器壞」的問題變成「不知道哪一臺機器壞」的問題。

## 混合策略

純垂直或純水平在實際系統中都罕見。常見的混合模式：

- **小規模垂直、大規模水平**：早期單機就能撐，先用較大規格降低運維複雜度；流量上來後再轉水平，把每臺機器規格降回中等。
- **stateless 水平、stateful 垂直**：API server 水平擴展、資料庫主節點垂直擴展、加 read replica 做讀路徑水平擴展。
- **熱資料水平 sharding、冷資料保持單庫**：把熱表用 partition key 拆到多個 shard，冷表保留在主庫不動。
- **核心服務垂直保底、邊緣服務水平彈性**：核心交易服務用更大規格降低事故風險，前端、推薦等服務走 auto scaling。

選混合策略時，要明確標記每個服務在哪個軸上、極限在哪、下一步轉換點在什麼條件下觸發。沒有這張對照表，混合策略容易變成「每個服務都是特例」、最後沒人記得當初為什麼這樣設計。

## 判讀訊號

| 訊號                       | 判讀重點                                 | 對應動作                                                                                                                                             |
| -------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 加機器後 QPS 沒提升        | stateful 殘留（本機快取 / session / 鎖） | 找出 stateful 點、移到外部 store，或改回垂直擴展                                                                                                     |
| 加機器後 DB 連線爆掉       | 連線池放大、DB 是瓶頸                    | 加 connection pooler、評估讀寫分離、考慮資料層擴展                                                                                                   |
| Auto scaling 反覆擴縮      | cool-down 太短或訊號抖動                 | 加 cool-down、改用更穩定訊號（移動平均、business metric）                                                                                            |
| 流量尖峰時新機器來不及啟動 | cold start 太長 / 預測訊號不夠早         | 改 [scheduled scaling](/backend/knowledge-cards/scheduled-scaling/) 或 [predictive scaling](/backend/knowledge-cards/predictive-scaling/)、warm pool |
| 垂直擴展後成本曲線陡升     | 撞到高階機型溢價                         | 評估水平擴展轉型 / 重構 stateful 部分                                                                                                                |
| 水平擴展後事故 MTTR 拉長   | 觀測能力跟不上                           | 補 trace context、結構化 log、service topology                                                                                                       |

## 常見誤區

把「加機器」當作所有效能問題的萬靈丹。如果瓶頸在演算法、SQL query、序列化、locks，加機器只會讓問題變得更貴。先用 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 確定瓶頸位置，再決定擴展軸。

把 auto scaling 當成「設定完就不用管」。auto scaling 是 reactive 策略，它無法處理可預期的尖峰（活動、新片上線、節日）。預期型流量要用 scheduled / predictive scaling 提前準備。

把 stateless 當成「沒有狀態就好」。WebSocket、long-polling、上傳、檔案處理這類服務天然 stateful、強行水平擴展會出事。要分辨「業務本質 stateful」跟「實作偷懶 stateful」，前者用 partitioning 處理、後者用重構移除。

## 定位邊界

本章專注「擴展軸的選擇與前提」。當問題進入具體量化（要加多少臺機器？headroom 多少？），交給 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)；進入瓶頸定位（瓶頸在哪一層？），交給 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)；進入服務拆分（要不要先把 stateful 部分拆出來再水平擴展？），交給 [0.18 服務拆分與邊界判讀](/backend/00-service-selection/service-decomposition-boundaries/)。

## 案例回寫

擴展軸選擇可用以下案例回寫。每個案例對應的軸不同，引用時要先辨識案例的主要壓力來源，再對照本章相應段落。

- [9.C18 Zoom：COVID 30 倍突發](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) — 案例主軸是「stateless API 層水平擴展、stateful 資料層改用 DynamoDB 移除單點」，直接對應本章「stateless 是水平擴展的前提」段。是本批最貼近 scaling axis 主題的案例。
- [9.C12 Riot Games：246 個 EKS cluster 的多遊戲多地區治理](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) — 案例展示水平擴展到極端規模後，協調成本（cluster 治理、版本一致性）變成新的瓶頸；對照本章「水平擴展的隱性成本 / 協調成本」段。
- [9.C19 Capcom：DynamoDB + EKS 上的遊戲後端](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) — 案例主軸是 KV 業務語意、不是 scaling axis 取捨；但可反向追問「stateful 玩家狀態為何適合 KV vs RDB」、對照本章「stateless 是水平擴展的前提」段中的「狀態類型 vs 緩解方向」表。
- [9.C23 Netflix：把關聯式 DB 統一到 Aurora](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — 案例主軸是「DB 種類整併」、不直接對應 scale-up vs scale-out；但 Aurora 在 single-primary 規格選擇上隱含了「先垂直、再考慮分散」的策略，可作為「垂直擴展天花板」段的對照組。

Zomato 跟 Netflix 不在這份案例清單裡的原因要先講清楚：擴展軸的真實示範案例在後端教材中相對稀缺、09 模組多數案例的主軸落在 vendor 或容量規劃。Zoom 是這四個案例中最貼近教科書 — stateless API 水平 + stateful 改用 DynamoDB 的組合直接示範本章核心。Riot Games 揭示水平到極端規模後協調成本翻轉成新瓶頸。Capcom 跟 Netflix Aurora 不直接示範擴展軸取捨、但用反向追問「為什麼選 KV / 為什麼 single-primary 仍是 default」能把它們的決策放回擴展軸框架。

## 跨模組路由

1. 與 [9.1 壓測理論與系統行為](/backend/09-performance-capacity/performance-theory/) 的交接：USL 跟 Little's Law 在理論上推導水平擴展的曲線、本章解釋這道牆在運維現場長什麼樣。
2. 與 [9.6 容量規劃](/backend/09-performance-capacity/capacity-planning/) 的交接：擴展軸選定後，容量規劃決定具體數字。
3. 與 [0.18 服務拆分](/backend/00-service-selection/service-decomposition-boundaries/) 的交接：水平擴展常常是服務拆分的觸發點，反之亦然。
4. 與 [01 database high-concurrency-access](/backend/01-database/high-concurrency-access/) 的交接：資料層水平擴展（sharding、replica）的具體機制。

## 下一步路由

**規模成長路線下一站 → [1.13 應用層查詢反模式與 Query 預算](/backend/01-database/query-anti-patterns/)**：選定擴展軸後、在加機器前先用反模式清單收回單機可撐住的容量。

其他延伸方向：

- 容量計算與 headroom 模型 → [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)
- 擴展前的瓶頸定位 → [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 服務拆分如何配合水平擴展 → [0.18 服務拆分與邊界判讀](/backend/00-service-selection/service-decomposition-boundaries/)
