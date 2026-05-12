---
title: "9.C3 Coinbase International Exchange：超低延遲交易的逆向容量設計"
date: 2026-05-12
description: "為什麼 Coinbase 國際交易所選 Cluster Placement Group + z1d 而不是自動擴容 — 延遲敏感型負載的容量取捨"
weight: 3
tags: ["backend", "performance", "capacity", "case-study"]
---

這個案例的核心責任是揭示「無明顯峰值但延遲就是收入」這類負載的容量設計、跟前兩個案例形成對照。金融交易不靠峰值定義成敗、靠每個交易的延遲穩定性 — 多 1ms 延遲在套利策略下可能直接吃掉整筆交易的利潤。Coinbase International Exchange 為這類負載做了一系列「反主流」的取捨：固定佈署、不啟用自動擴容、強制節點實體靠近。

## 觀察

Coinbase 在 2023-05 推出國際交易所、上線後關鍵數字（引自 [Coinbase Case Study](https://aws.amazon.com/solutions/case-studies/coinbase-cryptocurrency-exchange-case-study/)）：

| 指標       | 數字                           |
| ---------- | ------------------------------ |
| 吞吐量     | 100,000 messages/sec（擴容後） |
| 延遲目標   | sub-millisecond（次毫秒級）    |
| 累計交易額 | 上線以來超過 150 億美元        |
| 可用性     | 24/7、受監管的交易平台         |

服務組合：

- **Amazon EC2 z1d 實例**：高頻 CPU + NVMe 本地儲存、針對單執行緒效能最佳化
- **EC2 Cluster Placement Groups**：強制把節點集中到單一機架附近、最小化 node-to-node 網路延遲
- **Amazon Aurora**：高速 transaction lookup 的關聯式資料庫
- 「Built from the ground up, using Cloud Native principles」（沒有複用既有交易所程式碼）
- 內部使用 **RAFT consensus** 維持交易順序

## 判讀

這個案例最值得讀的地方、是它「沒有做」的事比「做了」的事更有教學價值。

1. **沒有用 Auto Scaling**：交易撮合引擎用 RAFT consensus 維持嚴格順序、節點數量是 consensus 一部分、不能臨時增加。容量規劃完全是 *pre-provision*、不是 reactive。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/) 必須區分「可水平擴容服務」跟「不可水平擴容服務」、後者的容量公式只有 headroom × peak、沒有 elastic 補救。
2. **沒有用通用 EC2 實例**：z1d 是 AWS 針對「高頻 CPU + NVMe」設計的特化實例、犧牲了通用性換取單核效能。這層選擇隱含一個容量規劃決策：*單機效能上限* 直接決定 *系統理論吞吐上限*、橫向擴容不能超過 RAFT 節點數限制、那麼縱向就必須榨乾。對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 必須先判斷瓶頸屬「可分散」還是「不可分散」。
3. **沒有用多區域分散**：Cluster Placement Group 把節點壓到同一可用區內、犧牲了 region failover 速度、換取 node-to-node 網路延遲。這跟「高可用性」的常見直覺相反、是「延遲敏感型負載的容量設計優先於可靠性設計」的一個範例。
4. **延遲是設計輸入、不是設計結果**：sub-millisecond 不是壓測之後發現可以做到、而是先訂目標、再反推所有架構選擇。對應 [9.1 壓測理論與系統行為](/backend/09-performance-capacity/) 中 Little's Law 的反向應用 — 給定延遲目標 + 吞吐目標、反推 concurrency 上限 + 每個 stage 的 latency budget。

需要警惕的判讀盲點：「sub-millisecond latency 達成」這類陳述通常指 *p50 或 p90*、不一定是 p99 或 p999。長尾延遲在 RAFT 系統下可能比平均高一個數量級（leader election、replication lag）。讀案例時要注意延遲分布 vs 平均值的差別。

## 策略

可重用的工程做法：

1. **延遲敏感型服務先做 latency budget 反推**：給每個 stage（網路、CPU、磁碟、序列化、共識）一個 latency 配額、總和等於 SLO 上限。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/)。
2. **單機效能榨乾優先於橫向擴容**：當 consensus / ordered processing 限制了水平擴容時、單機選型（CPU 頻率、NUMA locality、NVMe）變成主要槓桿。對應 [9.4 Saturation Discovery](/backend/09-performance-capacity/) 把 saturation 點推得越遠。
3. **拓樸感知的部署策略**：Cluster Placement Group 是 AWS 名稱、概念是「網路拓樸感知的工作負載放置」。GCP 有 Compact Placement Policy、Azure 有 Proximity Placement Groups、自建 Kubernetes 有 Pod Topology Spread Constraints + Node Affinity。
4. **接受「不可彈性」是有意識決策、不是失敗**：很多服務不該全部都自動擴容。設計時要區分「需要 elastic 的 stateless 邊緣」跟「必須 pre-provision 的有狀態核心」、容量規劃也要兩條腿。

跨平台等效：所有主流雲端都有對應的高頻 CPU 實例（GCP C2 / Azure HBv 系列）、placement policy 與本地 NVMe 儲存。自建環境可以用 SR-IOV + RDMA + NUMA pinning 達成更極致的版本。

## 下一步路由

- 想設計延遲敏感型服務的容量地圖 → [9.1 壓測理論與系統行為](/backend/09-performance-capacity/) + [9.6 容量規劃模型](/backend/09-performance-capacity/)
- 想搞清楚哪些服務該水平擴容、哪些不該 → [9.5 瓶頸定位流程](/backend/09-performance-capacity/) + [9.4 Saturation Discovery](/backend/09-performance-capacity/)
- 想做 latency budget 反推 → [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) + [04.16 SLI / SLO 訊號](/backend/04-observability/sli-slo-signal/)
- 對照不同形狀的負載 → [9.C1 AWS Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)（可預期極端峰值）/ [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)（事件型不可預期峰值）

## 引用源

- [Coinbase Launches an Ultra-Low-Latency Cryptocurrency Exchange on AWS](https://aws.amazon.com/solutions/case-studies/coinbase-cryptocurrency-exchange-case-study/)
- [Coinbase Scales 50% Faster, Cuts Costs 62% with AWS](https://aws.amazon.com/solutions/case-studies/coinbase-migration-case-study/)
- [Ultra-Low-Latency Crypto Exchange on AWS（video）](https://aws.amazon.com/video/watch/a413043e5cb/)
