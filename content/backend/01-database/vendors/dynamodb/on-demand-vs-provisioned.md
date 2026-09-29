---
title: "DynamoDB On-Demand vs Provisioned：6 軸決策、auto-scaling 邊界與 cost crossover"
date: 2026-05-27
description: "capacity mode 選擇不是單軸 peak/avg ratio；本文展開 6 軸決策（peak/avg / 讀寫比 trend / surge 暫時 vs 永久 baseline / predictable-peak vs flash-sale / DBA 工時釋放 / vendor vs 自管 cost crossover），含 Zomato 50% 成本下降、Zoom 30x permanent surge、Amazon Ads sustained workload 等案例對照"
weight: 33
tags: ["backend", "database", "dynamodb", "capacity-mode", "auto-scaling", "cost-optimization", "deep-article"]
---

這篇整理 [DynamoDB](/backend/01-database/vendors/dynamodb/) 在 provisioned 與 on-demand 兩種 capacity mode 之間的選擇：兩種 mode 的計費與 throttle 行為、auto-scaling 的反應邊界，以及 mode 切換與長期成本的判讀。

capacity mode 的選擇不能只看「peak/avg ratio > 5x」這一個閾值。本篇把判讀擴成六個軸：peak/avg ratio、讀寫比 trend、surge 性質（暫時 vs 永久 baseline 上移）、事件分級（predictable-peak vs flash-sale）、DBA / SRE 工時釋放、DynamoDB 與自管 cluster 的 vendor crossover。

> **DynamoDB 適用度前置判讀**：本篇假設 workload 已通過 DynamoDB 適用度 4 軸（PK 天然均勻 / control plane vs data plane / consistency 可接受 eventual / access pattern 穩定）— 詳見 [single-table-design-pattern 開頭 4 軸前置判讀](../single-table-design-pattern/#dynamodb-適用度前置判讀)、本篇不重複展開。Capacity mode 選擇是 *已選 DynamoDB 後* 的成本決策；若 workload 不適用 DynamoDB、mode 選擇無法救回 vendor 選錯的成本。

## 核心機制：兩種 mode 的工程差異

| 屬性          | Provisioned                                    | On-demand                                                                                                                                                                                     |
| ------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 計費方式      | 預先買 RCU/WCU、按 hour 計                     | 按 request 計、無 capacity 預設                                                                                                                                                               |
| Auto-scaling  | 動態調整、target utilization 70%、min / max    | 自動 scale、仍受單 partition 1000 WCU / 3000 RCU 上限                                                                                                                                         |
| Throttle 表現 | `WriteThrottleEvents` 立即可見、exception 拋出 | 超過單 partition 上限或 on-demand maximum throughput 時被 throttle、記在 `*KeyRangeThroughputThrottleEvents` / `*MaxOnDemandThroughputThrottleEvents`；SDK 自動重試讓它先表現為 latency spike |
| Cost 模型     | 可預測、低基礎 rate                            | 按用量、cost-per-request 約 provisioned base rate 的 6-7 倍                                                                                                                                   |
| Mode 切換限制 | 切到 on-demand：24 小時滾動窗口內最多四次      | 切回 provisioned：隨時可切                                                                                                                                                                    |

**Auto-scaling 內部機制**：

- CloudWatch alarm 觸發 → scaling activity → 1-5 分鐘調整 capacity
- target utilization 70%（建議值、留 buffer 給 scale latency）
- 連續 spike 仍可能 throttle（auto-scaling 反應週期 > spike 速度）

對應 knowledge card：[peak forecast](/backend/knowledge-cards/peak-forecast/)、[cost per request](/backend/knowledge-cards/cost-per-request/)、[scheduled scaling](/backend/knowledge-cards/scheduled-scaling/)。

## Capacity mode 的決策框架

mode 選擇不是單軸 peak/avg ratio。下面 6 軸是 9 個 production case（Zomato / Zoom / Amazon Ads / Disney+ / Tixcraft / Capcom / Lemino / Genesys / PayPay）跨 case 揭露的真實決策維度。

### peak / average 流量 ratio

最直覺的軸、但是單軸誤判的根源。基本判讀：

- 高 ratio（spiky / flash-sale）傾向 on-demand
- 穩定 ratio（sustained / 平緩）傾向 provisioned + auto-scaling

> **Scope warning**：「peak/avg > 5x → on-demand」、「provisioned base rate × 6-7 = on-demand rate」這些具體閾值是經驗值 / 通用工程估算、Amazon Ads 與 Zomato 案例都沒給具體 ratio 數字。實際 crossover 點隨 region pricing + workload shape 變動、不要照搬本文數字。

peak/avg ratio 單獨不夠用、要跟讀寫比 trend、surge 性質、事件分級、DBA / SRE 工時釋放、vendor crossover 合成判讀。

### 讀寫比 trend 變化

`9.C5 Amazon Ads` 揭露的觀測軸：「讀寫比 *變化* 比讀寫比本身更重要」。

- 絕對讀寫比對容量規劃不是最重要（Amazon Ads 是 18:1、Disney+ 推估 5:1、絕對值各家不同）
- 業務邏輯改變（新增即時報表 / 新增推播 / 新增分析 query）會讓讀寫比跳一個量級
- 觀測上加 metric：read / write ratio 7-day rolling average、超過 ±30% 偏移觸發 review

把 trend 變化當 capacity mode 重新評估的訊號 — 不是固定週期 review、是 *trend 偏移* 觸發 review。

### surge 是 *暫時* 還是 *永久 baseline 上移*

`9.C18 Zoom` COVID 30x DAU surge 揭露的軸：surge 後 baseline 永久上移、不會回去。

- 暫時 surge（單日活動 / 季節高峰）：on-demand 划算、活動結束 mode 不用調
- 永久上移後（Zoom COVID、社會行為改變）：原 on-demand 設計會持續燒錢、要重新算 crossover、考慮切回 provisioned

**Tripwire**：surge 結束後 4-8 週仍維持 surge 期間 baseline 的 70%+、判定為「永久 baseline 上移」、重評 mode。

> **Scope warning**：「4-8 週 / 70% 閾值」屬通用工程估算、9.C18 Zoom case 揭露「surge 後 baseline 不會回去」概念、未揭露具體閾值。

### 事件分級：predictable-peak vs flash-sale

`9.C27 Disney+` 跟 `9.C15 Tixcraft` 對比揭露的軸：兩種 event-driven peak 不是同一類。

| 維度         | predictable-peak（Disney+ 新片發布） | flash-sale（拓元售票）                                    |
| ------------ | ------------------------------------ | --------------------------------------------------------- |
| 時間 lead    | 已知日期、提前 1-2 天可預備          | 已知時刻、提前 1-5 分鐘有效                               |
| 峰值倍數     | metadata 3-5x、持續數小時            | 6750x in seconds、t=0 起跳 / t=300 結束                   |
| Scale 方式   | scheduled scaling 預先升 baseline    | scheduled scaling 太慢、必須 pre-provision + composite PK |
| Auto-scaling | 跟得上（事件持續時間長）             | 完全跟不上（事件時間 < scaling 反應週期）                 |
| 後續調回     | 事件結束後 scheduled scaling 降回    | 結束後立即降回、避免燒錢                                  |

`9.C27 Disney+`（Marvel / Star Wars 首日 metadata 流量 3-5 倍、持續時段較長）可以提前 1-2 天 pre-scale、scheduled scaling 合適。`9.C15 Tixcraft` 6750x in seconds，scheduled scaling 太慢、必須事前 pre-provision baseline 拉到極高、或用 on-demand + composite partition key 雙保險。

兩者都不是「peak/avg > 5x → on-demand」單軸決策能解。

> **Scope warning**：上表 predictable-peak 的「提前 1-2 天可預備」這個 lead time 是經驗值、case 未揭露具體時間。pre-scale 的 lead time 依事件性質決定。

### DBA / SRE 工時釋放

`9.C19 Capcom` 跟 `9.C29 Lemino` 揭露的成本軸：DynamoDB 真實成本不只看 monthly bill。

- `9.C19 Capcom`：30% 成本下降的本質是「工程資源從 DB 運維轉到遊戲品質」、Capcom 是遊戲公司不是 IT 公司、把 DBA 時間從 Postgres patching / replication 設定 / backup 排程釋放到遊戲機制設計
- `9.C29 Lemino`：90% 工程工時下降（DBA + connection management + capacity planning 統包）

**評估公式**：

```text
總成本 = direct cost (monthly bill)
       + 工程工時機會成本 (DBA 從 patch/replication/backup 釋放出來做的事)
```

on-demand 的 6-7x base rate 在 DBA 工時釋放下、實質 ROI 可能仍正向（特別在小團隊 / 非 IT 主業公司）。但要算總成本、不是只看 bill。

### Vendor crossover：DynamoDB vs 自管 cluster

`9.C20 Zomato` 警惕段揭露的最上層決策軸：mode 選擇之上還有 vendor 選擇。

- `9.C20 Zomato`：「成本降 50% 是 *當下流量* 的對照」、未來流量繼續成長、DynamoDB cost-per-request 成長率比 TiDB 自管 cluster 高、某流量規模後 crossover、自管 cluster 反而便宜
- 不是只在 on-demand vs provisioned 之間挑、是要算「未來 12-24 個月在預期流量下、DynamoDB（不論 mode）vs 自管 cluster 的成本曲線」

判讀分層：

- **小 / 中流量 startup**：DynamoDB on-demand 簡單划算、不用糾結
- **大流量 + 流量可預測 + DBA 團隊已存在**：自管 cluster crossover 點可能成立、值得算
- **大流量 + 流量不可預測 + 小團隊**：DynamoDB managed 仍划算（DBA / SRE 工時釋放加成）

本軸是 mode 選擇之上的更上層決策、不是每次都展開、但寫進邊界判讀條件。

## 操作流程

從 workload profiling 到 mode 切換的操作流程：profiling workload、判讀 surge 性質、合成各軸決策、provisioned 配 auto-scaling、設 scheduled scaling、切換 mode、驗證切換結果、評估總成本。

#### Profiling workload

用 CloudWatch 過去 30 天 RCU/WCU、算 p50 / p95 / p99 peak、求 peak/avg ratio + read/write ratio rolling avg（讀寫比 trend 的輸入）。

#### 判讀 surge 性質與事件分級

- 是暫時 surge 還是永久 baseline 上移 — 看 surge 結束後 4-8 週的 baseline trend
- 是 predictable-peak 還是 flash-sale — 看事件時間跟 auto-scaling 反應週期的比例

#### 合成各軸決策

```text
peak/avg ratio + 讀寫比 trend + surge 性質
+ 事件分級 + DBA / SRE 工時機會成本 + vendor crossover
→ provisioned + auto-scaling / on-demand / scheduled scaling 三選一
```

不是任一軸獨自決定、是各軸合成；軸間衝突時優先序：vendor crossover > DBA / SRE 工時釋放 > surge 性質（永久 vs 暫時）> 事件分級 > peak/avg ratio > 讀寫比 trend。

#### provisioned 配 auto-scaling

```yaml
BillingMode: PROVISIONED
ProvisionedThroughput:
  ReadCapacityUnits: 100
  WriteCapacityUnits: 50

AutoScalingSettings:
  TargetTrackingScalingPolicy:
    TargetValue: 70.0  # target utilization
    ScaleOutCooldown: 60
    ScaleInCooldown: 60
  MinCapacity: 50      # baseline
  MaxCapacity: 1000    # baseline × 預期 surge multiplier
```

target utilization 70% 留 buffer 給 scale latency；alarm 設 5 分鐘觀察窗。

#### 設 scheduled scaling

已知大事件（黑五、開票、新片發布）前預先提升 min capacity、事件後回原值：

```python
# 黑五前 24 小時把 min capacity 拉到日常 10 倍
client.put_scheduled_action(
    ResourceId="table/orders",
    ScheduledActionName="black-friday-pre-scale",
    Schedule="cron(0 0 * * ? *)",  # 時間 lead 依事件性質決定、非固定 30-60 分鐘
    ScalableTargetAction={"MinCapacity": 5000, "MaxCapacity": 50000}
)
```

#### 切換 mode

```bash
aws dynamodb update-table \
  --table-name orders \
  --billing-mode PAY_PER_REQUEST
```

從 provisioned 切到 on-demand 在 24 小時滾動窗口內最多四次、從 on-demand 切回 provisioned 不限次數；切到 on-demand 的過程要數分鐘，期間 table 維持原本 provisioned 的 throughput。

#### 驗證切換結果

切換後第一週對比 cost + throttle metric、確認方向正確：

- cost 變化方向跟預期一致（on-demand 應該變貴 / provisioned 應該變便宜）
- throttle rate 沒上升
- latency p99 沒退化

#### 評估總成本：工時機會成本與 vendor crossover

直接 cost + 工時機會成本 + 對照自管 cluster 的 cost crossover 曲線。Quarterly review 用這個公式、不是只看 monthly bill。

**Rollback boundary**：on-demand → provisioned 隨時可切、但 baseline 要先 sized 好；切錯方向第一個月可逆、長期累積 cost 不可逆。

## 失敗模式

production 觀察到的 6 個典型 anti-pattern：

#### on-demand 後 cost 翻 3 倍

dev team 切 on-demand「不用管 capacity」、但 workload 是 sustained constant、on-demand 6-7x base rate 全付出來。`9.C5 Amazon Ads` 明示「sustained workload 用 provisioned + auto-scaling」。修法：穩定 workload 用 provisioned + auto-scaling（依 peak/avg ratio 與讀寫比 trend 判讀）。

#### auto-scaling 跟不上 spike

流量 1 分鐘內 10x、auto-scaling alarm 5 分鐘才觸發、前 4 分鐘全 throttle。修法：peak/avg 高且 spike 突然 → on-demand、或 scheduled scaling 預先升配（依 peak/avg ratio 與事件分級判讀）；flash-sale 場景 auto-scaling 不夠快、必須 pre-provision。

#### on-demand hot partition 隱藏

on-demand 的 hot partition 超過單 partition 上限時回 throttling exception、記在 `WriteKeyRangeThroughputThrottleEvents`，SDK 自動重試把它攤成 latency、latency 從 5ms 變 50ms、application timeout retry 加劇問題。修法：on-demand 仍要看 partition-level metric（Contributor Insights）、不能假設 mode 解決設計問題（跟 [partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) cross-link）；mode × partition 交叉判讀。

#### provisioned target utilization 設太高

target = 90% 看似省、實際每次 spike 都先 throttle 再 scale。修法：70% buffer 給 scale latency、不要為了省 cost 把 utilization 推到極限。

#### 用 mode switch 處理日週期流量

team 想「白天 provisioned 晚上 on-demand」省 cost、每天切兩次 mode。從 provisioned 切到 on-demand 在 24 小時滾動窗口內最多四次、切回 provisioned 不限次數，次數上限擋不住這個計畫；代價在切換本身：每次切到 on-demand 要花數分鐘，期間 table 維持原本 provisioned 的 throughput，而用 Console 切到 on-demand 會刪除 auto-scaling 設定。修法：白天 provisioned + 晚上把 capacity 設低、不切 mode；用 scheduled scaling 處理日週期、不用 mode switch。

#### surge 後沒重評 mode、長期燒錢

Zoom 式 30x permanent baseline 上移後、原 on-demand 設計成本爆炸。修法：surge 結束 4-8 週後重評、若 baseline 維持 70%+ 改 provisioned；把「surge 後 mode review」寫進 runbook、不是 ad-hoc 才想到。

**Anti-recommendation**：流量 < 100 RPS、cost < $50/月的小 table 不用糾結 mode、on-demand 簡單；workload 穩定且 cost 高才值得做 provisioned + auto-scaling 的工程投入。

## 容量與觀測

CloudWatch metric：

- `ConsumedReadCapacityUnits` / `ConsumedWriteCapacityUnits`：基本用量
- `ProvisionedReadCapacityUnits` / `ProvisionedWriteCapacityUnits`：provisioned 預設值
- `ThrottledRequests`：兩種 mode 都會記；成因分開看 `WriteKeyRangeThroughputThrottleEvents`（partition 上限）、`WriteProvisionedThroughputThrottleEvents`（provisioned 容量）、`WriteMaxOnDemandThroughputThrottleEvents`（on-demand 上限）
- `SuccessfulRequestLatency` p99：on-demand mode 下 hot partition 訊號

**讀寫比 trend 與 surge 性質需要的觀測**：

- read/write ratio 7-day rolling avg、超過 ±30% 偏移觸發 review
- surge baseline 4-week rolling avg、判斷 surge 是暫時還是永久
- AWS Cost Explorer 按 table + mode 切 cost trend、月對比

Auto-scaling activity log：CloudWatch alarm history + scaling activity，觀察 scaling 是否頻繁但 utilization 仍低（表示 alarm 設太敏感）。

**指標口徑紀律**：引用 case 數字時明示口徑 — Amazon Ads 的 90M reads/sec 是「年度峰值最高一秒、非平均」、Zomato 的 90% latency 降可能只 p50 不是 p99/p999、Zoom 的 30x DAU 是「permanent baseline 上移」非單日 peak。讀 vendor case 數字要分「最大瞬時 / 99 百分位 / 常態 / 滾動」四個口徑、不是混用。

Cost gate：每月 finance review 把 DynamoDB cost 對齊 access pattern volume、不只看絕對數字；DBA / SRE 工時釋放跟 vendor crossover 也納入。

接回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)。

## 邊界與整合

### event-driven scaling 的形狀

Amazon Ads、拓元、Zoom、Genesys、Disney+ 等案例揭露 event-driven scaling 至少有這些形狀：

- **flash-sale spike**：拓元 6750x in seconds（事件分級判為 flash-sale → pre-provision + composite PK）
- **predictable peak**：Disney+ 新片首發（事件分級判為 predictable-peak → scheduled scaling）
- **sustained growth**：Amazon Ads / Capcom（peak/avg ratio 平緩 + DBA / SRE 工時釋放 → provisioned + auto-scaling）
- **surge baseline permanent shift**：Zoom 30x DAU 不會回去（surge 性質判為永久上移 → 重評 mode）
- **B2B sustained + 高可用**：Genesys 99.999%（DBA / SRE 工時釋放 + vendor crossover → managed 工時釋放比 cost 重要）

不是用「peak/avg > 5x」單一閾值決策、是事件型分類 × 軸合成。

### Sibling 與 cross-link

- [partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) — capacity mode 不解 hot partition、mode × partition 交叉判讀
- [single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) — access pattern 影響 peak/avg ratio 跟 read/write ratio
- [gsi-lsi-design](/backend/01-database/vendors/dynamodb/gsi-lsi-design/) — GSI 多時 cost 跟 mode 互動
- [global-tables-conflict](/backend/01-database/vendors/dynamodb/global-tables-conflict/) — 多 region capacity 規劃放大、DBA / SRE 工時釋放在 multi-region 更顯著
- Migration playbook：跨 vendor cost optimization（如 [Zomato TiDB → DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)）對應 type C operational hybrid
- 替代路由：cost 極度敏感 + 流量穩定 + DBA 團隊已存在 → 自管 PostgreSQL / MySQL 可能更便宜（vendor crossover）、回 [PostgreSQL vendor](/backend/01-database/vendors/postgresql/)
- [Zoom：COVID 期間從 1000 萬到 3 億 DAU 的 30 倍突發](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)：30x permanent surge 後的 mode 重評，surge 性質的主案例
- [Capcom：Resident Evil / Monster Hunter 在 DynamoDB + EKS 上的遊戲後端](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) 與 [NTT DOCOMO Lemino：3 個月達 500 萬 MAU 的串流後端](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)：DBA / SRE 工時釋放的主案例
- [Aurora Read Replica Scaling](/backend/01-database/vendors/aurora/read-replica-scaling/)：同一類 event-driven scaling 問題從 SQL 讀副本切入，涵蓋事件分級表（FanDuel 平日 / playoff / championship / Super Bowl）、讀寫雙峰錯位的雙 SLO 並行（DraftKings）與 fleet 治理
