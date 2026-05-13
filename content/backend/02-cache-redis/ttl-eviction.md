---
title: "2.3 TTL 與 eviction"
date: 2026-04-23
description: "整理過期策略、容量控制與熱點資料"
weight: 3
tags: ["backend", "cache", "ttl"]
---

存活時間與淘汰策略（TTL and eviction）的核心責任是把快取資源分配成可預期策略。TTL 決定資料可存活多久，eviction 決定容量壓力下誰先被移除；兩者共同定義快取的新鮮度、命中率與回源風險。

## TTL 是新鮮度預算

[TTL](/backend/knowledge-cards/ttl/) 不是單一時間常數，而是資料類型的新鮮度預算。商品描述、推薦列表、活動文案可容忍較長 TTL；價格、庫存、配額、權限則需要更短 TTL 或事件失效。

TTL 設計要連到業務代價。可容忍舊資料的欄位可用長 TTL 降回源壓力；不可容忍錯誤結果的欄位要搭配事件失效與版本控制，讓 TTL 只作為保底機制。

## eviction 是容量分流策略

[eviction](/backend/knowledge-cards/eviction/) 的責任是當記憶體不足時，優先保留最有價值資料。常見策略如 LRU、LFU、TTL-based eviction，各自偏好不同存取型態。

策略選擇重點不在演算法名稱，而在流量形狀：高重複讀取場景偏向保留高頻資料；大量一次性讀取場景需要避免短期噪音擠掉核心 key。快取層若同時承載多種資料，應分 key space 或分叢集管理，避免策略互相干擾。

## hot / cold data 的容量節奏

hot data 與 cold data 的差異不只在存取次數，也在回源成本與業務風險。熱資料 miss 會直接放大來源壓力，冷資料 miss 多半只影響單次延遲。容量規劃要先保護熱資料，再決定冷資料淘汰節奏。

在促銷或重大活動期間，流量分布常快速改變。TTL 與 eviction 需要具備活動模式：預熱核心 key、分散過期時間、限制單批失效，讓來源系統不被同時回源壓垮。

## 分層快取的容量跟成本曲線

當熱資料集合超過 DRAM 經濟範圍、單層快取會同時遇到成本跟命中率瓶頸、要把 cache 結構擴展到分層管理。

對應 [2.C4 Meta CacheLib / Kangaroo](/backend/02-cache-redis/cases/meta-cachelib-kangaroo-tiered-cache/) — Meta 把快取結構從 DRAM-only 擴展到 DRAM + flash 分層、改善容量跟成本平衡。當「全部熱資料塞 DRAM」變太貴、把次熱資料推到 flash、保留 DRAM 給最熱的子集。

**分層快取的相對特性**（具體 size / latency / cost 視硬體配置跟業務 workload）：

- **L1 (DRAM)**：容量最小、延遲最低、單位成本最高、放最熱的子集 — Meta CacheLib 用這層保留熱度最高的 working set
- **L2 (flash / NVMe)**：容量比 L1 大、延遲比 L1 高、單位成本比 L1 低 — Meta Kangaroo 在這層處理次熱資料
- **L3 (持久 KV)**：容量最大、延遲最高、單位成本最低、放冷資料跟 fallback

落層策略要看 *資料熱度分布*。Zipfian 分布（80/20 法則）下、L1 放最熱 20% 就能命中大部分；如果分布更平、要把 L1 擴大或接受更低命中率。具體 L1 / L2 大小比例要實測 workload 才能定。

對應 [2.C7 Cloudflare Cache Reserve](/backend/02-cache-redis/cases/cloudflare-cache-reserve-tiered-storage/) — edge cache 跟 persistent reserve 的分層、長尾資料用 reserve 接住、降低 origin 回源。這是 *同類設計思維* 在 CDN 場景的應用、但分層語意不同（edge cache 是地理分散的、Meta 分層是垂直記憶體 / flash 層）— 兩者都用「冷熱分離降低總成本」、實作機制差異需依場景區分。

**Eviction 跟回補延遲要納入共同指標**：分層 cache 的訊號不只看 L1 命中率、要看 L1 evict 到 L2 的速率、L2 回補到 L1 的延遲、L3 回源到 L2 的尾巴延遲。混合 metric 才能判斷分層策略是否健康。

判讀重點：分層 cache 屬規模觸發的設計、要從 working set 大小判斷。Working set 在 DRAM 經濟範圍內、單層即可；working set 顯著超過 DRAM 容量、需分層讓 DRAM 集中放最熱子集、其餘走 flash 或更下層。

## 判讀訊號

| 訊號                                | 判讀重點                      | 對應動作                            |
| ----------------------------------- | ----------------------------- | ----------------------------------- |
| eviction rate 持續上升              | 容量不足或 key/value 體積失控 | 調整策略、拆分 key space、補容量    |
| hit rate 下降且 origin QPS 同步上升 | TTL 設定過短或過期同步爆發    | 拉長部分 TTL、加入 jitter、分批更新 |
| stale read 事件上升                 | TTL 過長或失效機制不足        | 縮短關鍵欄位 TTL、補事件失效        |
| 熱門 key 在尖峰時段頻繁 miss        | 熱資料未被優先保留            | 預熱 hot set、調整 eviction 權重    |
| 記憶體穩定但業務錯誤增加            | 值語意失真，非容量問題        | 檢查序列化版本、補新鮮度監控與驗證  |

## 常見誤區

把 TTL 統一設定成同一數值，會掩蓋資料語意差異。快取策略應反映資料的重要性與可容忍延遲，而不是單一預設。

把 eviction 視為平台預設值即可，也常導致壓力失真。策略與流量形狀不對齊時，命中率看似可接受，來源系統仍可能在尖峰被回源壓垮。

## 案例回寫

TTL/eviction 的容量節奏可用 [2.C9 反例](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/) 回寫。先看事件中的過期同步與回源尖峰，再回到本章檢查 TTL 分布、淘汰策略與熱資料保護是否同時成立。
這個案例主要支撐的是「容量淘汰與過期波形」判讀，不直接支撐資料庫交易切分或部署切流策略；若事件核心在交易提交或 rollout 批次，應轉到 1.3 或 5.2。

當 eviction 上升但命中率未明顯下降時，先補 value size 與 key 分布監控，再把量測定義回寫到 [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)。

## 跨模組路由

TTL 與 eviction 設計會直接影響觀測、驗證與事故處理。

1. 與 2.2 的交接：讀寫失效流程落在 [cache aside](/backend/02-cache-redis/cache-aside/)。
2. 與 4.17 的交接：新鮮度與容量訊號進入 [Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)。
3. 與 6.20 的交接：尖峰演練與停損邊界進入 [Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)。
4. 與 8.22 的交接：容量失配與快取事故教訓回寫 [Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)。

## 下一步路由

要把 TTL/eviction 放進失效流程，接著讀 [2.2 cache aside 與失效策略](/backend/02-cache-redis/cache-aside/)。要看容量與策略失配案例，接著讀 [2.C9 反例](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)。
