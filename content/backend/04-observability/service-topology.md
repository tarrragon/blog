---
title: "4.13 Service Topology 與 Dependency Map"
date: 2026-05-01
description: "把跨服務依賴從文件變成自動發現的觀測訊號"
weight: 13
tags: ["backend", "observability"]
---

## 大綱

- 為何依賴拓撲需要獨立節點：人工維護的依賴圖永遠過時
- 拓撲訊號的來源：trace（4.3）、service mesh（mTLS / sidecar）、network flow log
- 服務 graph 的維度：呼叫頻率、latency、錯誤率、版本
- 依賴變化告警：新增依賴、刪除依賴、依賴方向反轉
- [blast radius](/backend/knowledge-cards/blast-radius/) 分析：上游失效時下游影響範圍預測
- 動態叢集下的拓撲追蹤：擴縮事件如何回寫拓撲訊號
- 跟 [4.3 tracing](/backend/04-observability/tracing-context/) 的分工：trace 是單 request、topology 是統計聚合
- 跟 [05 deployment platform](/backend/05-deployment-platform/) 的整合：service mesh 部署
- 反模式：架構圖只在 wiki 上、跟實際流量漂移；新依賴上線缺 review；拓撲圖回答「這服務掛了誰受影響」需要人工追查

## 概念定位

Service topology 是把跨服務依賴從文件轉成可觀測資料的能力，責任是讓團隊能用實際呼叫關係判斷依賴、影響面與變更風險。

這一頁處理的是服務關係圖。Trace 解釋單次 request、topology 解釋一段時間內的依賴結構；兩者合起來才能回答「這個服務壞了會影響誰」。

人工維護的依賴圖在快速變動的微服務環境下會持續漂移。新服務上線、舊服務下架、依賴方向反轉、版本切換都會發生在 wiki 圖更新之前；事故時依賴 wiki 圖判讀 blast radius，會把過期的依賴結構誤當成當前事實。

## 拓撲訊號的來源

Service topology 的可信度取決於資料來源是否反映真實流量。常見的訊號來源各有覆蓋範圍跟限制：

| 來源             | 覆蓋範圍                            | 主要限制                              |
| ---------------- | ----------------------------------- | ------------------------------------- |
| Trace（4.3）     | 應用層呼叫關係、含 latency / 錯誤率 | 需要 instrumentation 覆蓋、有採樣偏誤 |
| Service mesh     | sidecar / mTLS 拦截的所有跨服務流量 | 依賴 mesh 部署、不含外部依賴          |
| Network flow log | L3 / L4 連線記錄、含外部依賴        | 缺少應用語意、難判斷哪個 service      |
| API gateway log  | 外部入口流量、含 client / API 維度  | 只看到 gateway 視角、不知道內部呼叫   |

實務上常用組合：trace 作為主要來源（提供應用語意跟錯誤率），service mesh 作為補充（補上未 instrument 的服務），network flow log 作為兜底（揭露未管理的外部依賴）。

把不同來源的拓撲訊號合併時，要顯式記錄每段依賴的來源。當 trace 看不到某段依賴、service mesh 卻看得到時，可能意味著 instrumentation 缺失或服務 bypass mesh，這本身是治理訊號。

## 服務 Graph 的維度

服務 graph 不是單純的「誰呼叫誰」。每段依賴關係要帶上可判讀的維度，事故時才能用來做決策。

- **呼叫頻率**：高頻依賴跟低頻依賴的失效影響不同。高頻依賴失效會立即放大成 5xx，低頻依賴失效可能要數小時才浮現。
- **Latency 分布**：依賴 p50 / p99 latency 決定下游 timeout 應該設多少。沒有 latency 訊號的依賴圖無法支援 timeout 設計。
- **Error rate**：依賴的錯誤率提供 budget 訊號。當某依賴錯誤率上升，下游應該觸發降級而不是無限重試。
- **版本 / API contract**：依賴的版本變化跟 API contract 變更要進拓撲訊號。版本升級後若某段依賴消失，可能是 contract breaking。
- **方向跟可選性**：是必要依賴（失效 = 服務失敗）還是可選依賴（失效 = 功能降級），影響事故分級。

這些維度進入拓撲訊號後，配合 [6.14 dependency budget](/backend/06-reliability/) 才能把依賴可靠性變成可量化決策。

## 依賴變化的治理

依賴關係的變化本身是訊號。新增依賴、刪除依賴、依賴方向反轉，都是值得告警的事件。沒有依賴變化偵測時，新服務接入往往跳過依賴 review，事故發生才從 trace 反查到「原來這條 path 已經接了三個月」。

可操作的依賴變化告警：

1. **新增依賴 alert**：當 trace 出現新的 service-to-service 呼叫，觸發 review。新依賴是否在預期內、是否經過 contract review、是否有 fallback。
2. **依賴消失 alert**：某段穩定存在的依賴在 N 分鐘內 trace 看不到，可能是 instrumentation 漏、可能是上游被誤改、可能是真實事故的早期訊號。
3. **依賴方向反轉**：A → B 變成 B → A 通常意味著 refactor 或誤改、應該觸發 review。
4. **循環依賴偵測**：環狀依賴會在事故時放大恢復難度、應該在拓撲訊號層級就阻擋。

## 動態叢集下的拓撲訊號

動態叢集擴縮會持續改變服務的拓撲：Pod 數量浮動、node 換代、service IP 變化、跨 cluster 流量重新分配。拓撲訊號要追上這些變化，才能反映當前實際依賴結構。

對應 [4.C8 Airbnb K8s 規模化下的觀測訊號治理](/backend/04-observability/cases/airbnb-observability-k8s-scale-signals/)：揭露「叢集擴縮跟工作負載變動需要回寫觀測模型」「叢集層指標跟服務層指標要分開治理」「擴縮事件跟事故關聯要可回溯」的方向。以下基於通用工程知識展開。

動態叢集對拓撲訊號的挑戰有三個面向：

1. **拓撲節點不穩定**：Pod 短暫存在、IP 不固定，把 Pod 當拓撲節點會讓 graph 持續抖動。可操作做法是用 service 層級節點（service name + version + region），把 Pod / instance 層級放到 dashboard drill-down，不在主拓撲圖呈現。
2. **擴縮事件 vs 真實事故區分**：擴縮過程中 Pod 重啟、health check 短暫失敗、依賴連線中斷，會產生跟事故相似的訊號。把擴縮事件本身打進 timeline，事故判讀時能分辨「這段錯誤是擴縮造成還是上游問題」。
3. **跨 cluster 流量變化**：multi-cluster 部署下，流量可能因 cluster 變更從 cluster A 切到 cluster B，拓撲圖要能呈現跨 cluster 邊界。沒有跨 cluster 視角時，B cluster 突增的流量會被誤判成 traffic spike，而不是 failover 事件。

把叢集層指標（node count、Pod count、HPA event）跟服務層指標（call rate、error rate、latency）分開治理，是動態叢集環境的基本要求。叢集層指標的 owner 通常是 platform team、服務層指標的 owner 通常是 service team，兩者放在同一 dashboard 上要清楚標示來源跟責任。

擴縮事件回溯到事故關聯的另一個價值是 capacity retrospective。當 HPA 在事故前後觸發、scale-up 是否足夠、scale-down 是否過快，都需要把擴縮 timeline 跟事故 timeline 拼起來看，回到 [6.9 容量成本](/backend/06-reliability/capacity-cost/) 跟 [9.6 容量規劃](/backend/09-performance-capacity/) 的回寫。

## Blast Radius 推導

Blast radius 分析的核心責任是回答「如果這個服務或依賴失效、哪些上游 / 下游會受影響、影響多深」。沒有實時拓撲訊號時，這個分析靠經驗、容易低估或高估。

實時 topology 加上依賴可選性標記後，blast radius 可以分層推導：

- **直接下游**：直接呼叫該服務的服務、立即受影響。
- **間接下游**：透過中間服務間接依賴、影響時間延後。
- **可降級下游**：依賴是 optional、失效會觸發降級但不失敗。
- **必要下游**：依賴是 mandatory、失效會傳播成服務失敗。

事故時把 blast radius 從拓撲推導出來、再對照實際看到的 5xx 跟 SLO burn rate、能驗證影響面是否符合預期。當實際影響超出推導 blast radius、通常意味著存在未紀錄依賴。

## 核心判讀

判讀 topology 時，先看資料是否來自真實流量，再看依賴變化是否能被治理。

重點訊號包括：

- service graph 是否包含呼叫方向、頻率、latency 與 error rate
- 新增依賴是否能觸發 review 或 alert
- [blast radius](/backend/knowledge-cards/blast-radius/) 是否能從上游 / 下游關係推導
- topology 是否能餵給 dependency budget 與事故型態判讀
- 動態擴縮事件是否打進 timeline、能跟事故區分

## 判讀訊號

- 事故時回答「誰呼叫這服務」需要人工追查
- 新服務接入無依賴 review、出事後才發現連結
- 架構文件跟實際呼叫關係漂移、半年沒更新
- service mesh 部署但拓撲訊號未被使用
- 循環依賴存在但無人發現
- 擴縮事件造成的短暫錯誤被誤判成事故

## 反模式

| 反模式                    | 表面現象                       | 修正方向                                  |
| ------------------------- | ------------------------------ | ----------------------------------------- |
| Wiki 架構圖               | 圖跟實際流量漂移半年           | 從 trace / mesh 自動生成、持續更新        |
| 新依賴無 review           | trace 出現新依賴沒人知道       | 新依賴 alert、依賴 review 進 release flow |
| 拓撲節點用 Pod / Instance | 動態叢集下圖持續抖動           | service 層級節點、Pod 放 drill-down       |
| 叢集跟服務指標混在一張圖  | platform 跟 service 責任不清   | 分層 dashboard、明確 owner                |
| Blast radius 靠經驗推導   | 影響面評估不準、事後才發現遺漏 | 從拓撲訊號自動推導、跟實際影響對照        |

## 交接路由

- [4.3 tracing](/backend/04-observability/tracing-context/)：拓撲訊號的原始來源
- [4.18 operating model](/backend/04-observability/observability-operating-model/)：叢集層 / 服務層 ownership 分工
- [05 部署](/backend/05-deployment-platform/)：service mesh 配置
- [6.5 pre-mortem](/backend/06-reliability/)：依賴失效路徑分析
- [6.9 capacity cost](/backend/06-reliability/capacity-cost/)：擴縮事件 retrospective
- [6.14 dependency budget](/backend/06-reliability/)：拓撲是依賴可靠性評估的資料來源
- [8.9 事故型態庫](/backend/08-incident-response/)：[cascading failure](/backend/knowledge-cards/cascading-failure/) 型態的拓撲依據
