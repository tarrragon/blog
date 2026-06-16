---
title: "Kafka Consumer Group Rebalance 與 Lag 診斷：從 protocol 到故障演練"
date: 2026-06-16
description: "Kafka consumer group 的 rebalance protocol（eager vs cooperative incremental）、static group membership、session.timeout.ms / max.poll.interval.ms / heartbeat.interval.ms 三個 timeout 的職責、consumer lag 均勻分布 vs 集中單一 partition 的診斷路徑、rebalance storm 成因與對策；含 kafka-consumer-groups.sh 實機驗證輸出與 4 個 production 故障演練"
weight: 11
tags: ["backend", "message-queue", "kafka", "consumer-group", "rebalance", "consumer-lag", "deep-article"]
---

> 本文是 [Kafka](/backend/03-message-queue/vendors/kafka/) overview「進階主題」的 implementation-layer deep article，承接 overview「Consumer lag 暴增」與「Rebalance storm」兩段判讀原則的展開。Overview 給判讀方向，本文給 protocol 機制、診斷指令與故障演練。

## Rebalance 是 consumer group 重新分配 partition 所有權的協調過程

Rebalance 是 consumer group coordinator 把 topic 的 partition 重新分配給 group 內 consumer 的協調動作，承擔「在成員數變動時維持每個 partition 恰好被一個 consumer 消費」這個責任。觸發條件是 group membership 改變：consumer 加入、consumer 離開、consumer 被判定失效，或 topic partition 數增加。Rebalance 完成前，受影響的 partition 暫停消費，這段空窗就是 rebalance 對 lag 的直接代價。

Consumer group 是 Kafka 把「一份 event stream 分給多個 worker 平行處理」與「同一份 stream 給多個獨立應用各自 replay」兩種需求統一的抽象。同一個 group 內的 consumer 瓜分 partition、彼此不重複消費；不同 group 各自維護 offset、互不干擾。Rebalance 只在 group 內部發生，調整的是 group 內 partition 對 consumer 的 mapping。本文聚焦 group 內 rebalance 的機制與診斷，group 概念本身見 [consumer group 知識卡](/backend/knowledge-cards/consumer-group/)。

實機觀察 partition 如何在兩個 consumer 間分配：同一 group 起兩個 consumer，coordinator 把 3 個 partition 拆給它們。

```text
GROUP    CONSUMER-ID    CLIENT-ID    #PARTITIONS  CURRENT-ASSIGNMENT
live-cg  consumer-A-... consumer-A   2            orders:0,1
live-cg  consumer-B-... consumer-B   1            orders:2

GROUP    ASSIGNMENT-STRATEGY  STATE    #MEMBERS
live-cg  range                Stable   2
```

consumer-A 拿到 partition 0、1，consumer-B 拿到 partition 2，STATE 是 Stable 代表 rebalance 已收斂。`ASSIGNMENT-STRATEGY` 顯示 range，是預設的 partition 分配演算法。

## Eager 與 cooperative incremental 是兩種 rebalance protocol

Rebalance protocol 決定「rebalance 期間 consumer 要不要交出手上全部 partition」，這個選擇直接決定 rebalance 的 stop-the-world 範圍。Kafka 提供兩種：eager 與 cooperative incremental。

Eager rebalance 是早期預設行為：rebalance 觸發時，group 內所有 consumer 先放棄手上全部 partition（revoke all），等 coordinator 算完新分配後再各自重新 assign。代價是 rebalance 期間整個 group 完全停止消費，即使某個 consumer 的 partition 在新舊分配中根本沒變，它也得先放掉再拿回。Group 規模越大、partition 越多，這個全停窗口越痛。

Cooperative incremental rebalance 改成「只 revoke 真正要換手的 partition」。Consumer 先回報自己想保留的 partition，coordinator 算出哪些 partition 需要從 A 搬到 B，只有這些 partition 經歷一次 revoke + reassign，其餘 partition 持續消費不中斷。代價是一次完整 rebalance 可能需要兩輪（第一輪 revoke、第二輪 assign），但每輪只影響少數 partition，整體可用性遠高於 eager。Kafka 2.4 起的 `CooperativeStickyAssignor` 實作這套協議。

實機驗證 cooperative-sticky 可由 consumer 端 config 啟用，`ASSIGNMENT-STRATEGY` 欄位反映實際生效的策略：

```bash
kafka-console-consumer.sh --topic orders --bootstrap-server localhost:9092 \
  --group coop-cg \
  --consumer-property partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor
```

```text
GROUP    ASSIGNMENT-STRATEGY  STATE    #MEMBERS
coop-cg  cooperative-sticky   Stable   1
```

選 protocol 的判準是 group 規模與消費中斷的容忍度：

| Protocol                | revoke 範圍      | rebalance 期間消費    | 適用                                     |
| ----------------------- | ---------------- | --------------------- | ---------------------------------------- |
| Eager (range / sticky)  | 全部 partition   | 全停                  | 小 group、partition 少、rebalance 不頻繁 |
| Cooperative incremental | 僅換手 partition | 未換手 partition 持續 | 大 group、partition 多、要求消費連續性   |

對 partition 數上百、consumer 數十的 group，eager 的全停窗口會讓每次 deploy 都產生明顯 lag spike。Walmart 每天 trillions of message、25K+ consumer 跑在 K8s，pod scaling 與 deploy 觸發的 rebalance 是最大痛點（[3.C17](/backend/03-message-queue/cases/kafka-walmart-mps-rebalance/)）；這種規模下 eager 的全停代價無法接受，cooperative 把中斷限縮到換手 partition 是基本要求。但 Walmart 進一步發現，即使換成 cooperative，partition-consumer 1:1 模型本身在 K8s 規模仍撞到擴張極限，最終把 consumer 解耦成 stateless service。Protocol 選擇降低單次 rebalance 代價，架構解耦才解決 rebalance 頻率本身。

切換 protocol 不能直接全量改：eager 與 cooperative 的 consumer 不能在同一 group 共存。滾動升級時，consumer 需先支援兩種 protocol、再分批切換 config，否則混用會導致 rebalance 失敗或 assignment 不一致。

## 三個 timeout 各自負責不同的失效判定

Consumer 存活由三個 timeout 共同把關，每個負責不同層次的失效訊號，混為一談是 rebalance 誤判的主要來源。

`session.timeout.ms` 是 coordinator 等待 consumer heartbeat 的上限。Consumer 背景執行緒週期性送 heartbeat，coordinator 在這個時間內沒收到就判定 consumer 死亡、觸發 rebalance。預設 45 秒（早期版本 10 秒）。值太小，短暫 GC pause 或網路抖動就誤判離線；值太大，真正死掉的 consumer 要拖很久才被踢出，lag 持續累積。

`heartbeat.interval.ms` 是 consumer 送 heartbeat 的頻率，必須明顯小於 `session.timeout.ms`，慣例設成 1/3。它決定 coordinator 多快能感知 consumer 變化，也決定 rebalance 訊號的傳播速度。值太大，session window 內 heartbeat 次數不足，容錯空間消失。

`max.poll.interval.ms` 是兩次 `poll()` 呼叫之間的上限，負責偵測「consumer 活著但卡住」。Consumer 主執行緒在 `poll()` 之間處理拉到的訊息，如果單批處理太久（下游 I/O 慢、batch 太大、業務邏輯重）超過這個時間，coordinator 判定 consumer 失去處理能力、把它踢出 group。預設 5 分鐘。它跟 session.timeout.ms 的分工是：heartbeat 偵測「行程是否還在」，max.poll.interval 偵測「行程是否還在前進」。

| Timeout                 | 偵測對象           | 預設   | 調整方向                                  |
| ----------------------- | ------------------ | ------ | ----------------------------------------- |
| `session.timeout.ms`    | heartbeat 是否中斷 | 45000  | 環境抖動大調高、要求快速偵測死亡調低      |
| `heartbeat.interval.ms` | heartbeat 傳送頻率 | 3000   | 維持在 session.timeout 的 1/3 左右        |
| `max.poll.interval.ms`  | 兩次 poll 的間隔   | 300000 | 單批處理慢就調高，或縮小 max.poll.records |

這三個值的常見錯配，是把處理變慢誤當成 consumer 死亡。下游 DB 變慢導致每批處理超過 `max.poll.interval.ms`，consumer 被踢出觸發 rebalance，partition 搬到別的 consumer，那個 consumer 同樣被同一個慢下游拖垮，再次被踢，形成連環 rebalance。這種情況調 `session.timeout.ms` 沒用，因為 heartbeat 執行緒一直正常送；要調的是 `max.poll.interval.ms` 或縮小 `max.poll.records` 讓單批更快做完。

## Static group membership 讓 consumer 重啟不觸發 rebalance

Static membership 給 consumer 一個固定身分 `group.instance.id`，讓 coordinator 在 consumer 短暫離線後保留它的 partition 分配，承擔「滾動重啟與短暫中斷不觸發 rebalance」的責任。沒有 static membership 時，consumer 每次重啟都產生一個新的 member id，coordinator 視為「舊成員離開、新成員加入」、觸發兩次 rebalance。

設定方式是給每個 consumer 一個跨重啟穩定的 `group.instance.id`。Coordinator 看到帶 instance id 的 consumer 離線時，不立即 revoke 它的 partition，而是等到 `session.timeout.ms` 真正超時才判定永久離線。在這個窗口內 consumer 帶同一個 instance id 回來，直接接回原本的 partition，不觸發 rebalance。

實機驗證 `group.instance.id` 生效後，`--members` 輸出多出 `GROUP-INSTANCE-ID` 欄位：

```bash
kafka-console-consumer.sh --topic orders --bootstrap-server localhost:9092 \
  --group static-cg --consumer-property group.instance.id=static-member-1
```

```text
GROUP      CONSUMER-ID            GROUP-INSTANCE-ID  CLIENT-ID  #PARTITIONS
static-cg  static-member-1-...    static-member-1    static-A   3
```

static membership 的關鍵搭配是把 `session.timeout.ms` 設得比預期的重啟時間長。K8s 滾動更新一個 pod 重啟可能 10-30 秒，session.timeout.ms 要涵蓋這段，否則 pod 還在重啟、coordinator 已判定永久離線、partition 已搬走，static membership 失去意義。代價是真正死掉的 consumer 也要拖到 session.timeout.ms 才被踢出，這段 partition 無人消費。Static membership 用「容忍較長的真實故障偵測延遲」換「消除重啟造成的 rebalance」，適合重啟頻繁但硬故障罕見的環境。

## 用 kafka-consumer-groups.sh 讀 lag 分布

診斷 lag 的起點是 `kafka-consumer-groups.sh --describe`，它逐 partition 列出 current offset、log end offset 與兩者差值 lag，承擔「定位 lag 集中在哪、規模多大」的責任。Lag 是某 partition 已產出的最新 offset 減去 consumer 已 commit 的 offset，代表還沒被消費的訊息量。

實機製造 lag：produce 30 筆訊息、consumer 只消費 12 筆就停掉，`--describe` 顯示逐 partition 的消費進度落後：

```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group analytics-cg
```

```text
GROUP         TOPIC   PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG  CONSUMER-ID
analytics-cg  orders  0          9               9               0    -
analytics-cg  orders  1          3               9               6    -
analytics-cg  orders  2          0               12              12   -
```

這份輸出本身就是診斷的第一個分岔點：lag 是均勻分布還是集中在少數 partition。這裡 partition 0 lag=0、partition 1 lag=6、partition 2 lag=12，明顯集中在後兩個 partition，指向 partition 層的不平衡而非整體 consumer 不足。

`--state` 看 group 的健康狀態與分配策略，`--members --verbose` 看每個 consumer 實際拿到哪些 partition：

```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group live-cg --state
```

```text
GROUP    COORDINATOR (ID)     ASSIGNMENT-STRATEGY  STATE    #MEMBERS
live-cg  localhost:9092 (1)   range                Stable   2
```

STATE 的取值是診斷訊號：`Stable` 代表分配已收斂正常消費；`PreparingRebalance` / `CompletingRebalance` 代表正在 rebalance；`Empty` 代表 group 沒有 active member（offset 還在但沒人消費），對應上面 lag 輸出裡 `CONSUMER-ID` 全是 `-` 的情況。看到 lag 持續累積又長期停在 rebalance 狀態，問題就在 rebalance 本身而非消費速度。

## Lag 均勻分布與集中單一 partition 指向不同根因

Lag 的分布形狀是診斷的主軸：均勻分布指向消費總能力不足，集中在少數 partition 指向 key 分布或單 partition 的局部問題。同樣是 lag 高，這兩種形狀的修法完全相反，先讀分布再決定方向。

Lag 均勻分布在所有 partition，代表 consumer group 整體消費速度跟不上 producer 寫入速度。根因在消費側的總吞吐：consumer 數量不足、單 consumer 處理慢（CPU / GC / 下游 I/O）、或 producer 突發流量超過 group 設計容量。修法是擴消費能力：加 consumer（上限是 partition 數）、優化單筆處理、或對下游加 batch。如果 lag 隨時間線性成長且各 partition 同步成長，是穩態的容量不足，要重新評估 partition 數與 consumer 數。

Lag 集中在少數 partition、其餘 partition lag 接近零，代表負載不均，根因通常在 key 分布。Producer 用 key 決定 partition（`hash(key) % partition_count`），如果某些 key 是熱點（例如某個大客戶的 id、某個 null key 全落同一 partition），對應 partition 的訊息量遠高於其他，負責它的 consumer 再快也追不上，而其他 consumer 閒著。加 consumer 不解決這個問題，因為瓶頸 partition 仍只能被一個 consumer 消費。修法在 key 設計：拆熱點 key、加 salt 打散、或對熱點走獨立 topic。

Airbnb 的 logging pipeline 遇到的正是 partition 層 skew：event size 從幾百 bytes 到幾百 KB、QPS 跨數個量級，Spark 一個 partition 對一個 task，造成 data skew，catch-up 一個 4 小時 lag 要再花 4 小時（[3.C15](/backend/03-message-queue/cases/kafka-airbnb-spark-streaming-rebalance/)）。它的解法揭露一個關鍵判準：partition 數不該等同 consumer parallelism。當 lag 集中在少數重 partition，加 consumer 受限於 partition 數的天花板無效，要把 parallelism 從 partition 數解耦、按 event volume × size 重新分派 work。這把「lag 集中」的診斷從 key 分布延伸到了 work 分派模型本身。

| Lag 分布形狀                | 根因方向                 | 修法                                           | 加 consumer 是否有效          |
| --------------------------- | ------------------------ | ---------------------------------------------- | ----------------------------- |
| 均勻分布、各 partition 相近 | 消費總能力不足           | 加 consumer、優化處理、batch 下游              | 有效（上限 partition 數）     |
| 集中少數 partition          | key 分布熱點 / data skew | 拆 key、salt、熱點獨立 topic、解耦 parallelism | 無效（瓶頸 partition 仍單線） |

判讀順序固定：先 `--describe` 看分布形狀，再決定往「擴容」還是「重分布」走。跳過分布判讀直接加 consumer，遇到熱點 partition 場景會白花資源還解不了 lag。

## Production 故障演練

### Case 1：consumer 處理慢被踢出 group 形成 rebalance 連環

徵兆：consumer log 反覆出現 `Member ... sending LeaveGroup request` 與 `Attempt to heartbeat failed since group is rebalancing`；lag 持續成長；group STATE 在 `Stable` 與 `PreparingRebalance` 之間反覆跳；同一批 partition 在不同 consumer 間反覆搬移。

根因：下游 I/O 變慢（DB 連線池打滿、外部 API 延遲升高），consumer 單批 `poll()` 後處理超過 `max.poll.interval.ms`（預設 5 分鐘），coordinator 判定該 consumer 失去處理能力、踢出 group、觸發 rebalance。partition 搬到另一個 consumer，後者面對同樣慢的下游、同樣超時被踢，rebalance 連環觸發，每次 rebalance 又讓所有 consumer 暫停消費，lag 加速惡化。

修法：

1. 確認瓶頸是處理慢而非 heartbeat 中斷：consumer log 若有正常 heartbeat 但仍被踢，問題在 `max.poll.interval.ms` 不是 `session.timeout.ms`。
2. 縮小 `max.poll.records`：一次拉少一點，讓單批在 `max.poll.interval.ms` 內做完，這是不改下游就能止血的第一步。
3. 拉高 `max.poll.interval.ms`：給單批更長處理時間，但這只是延後而非解決，要搭配下游修復。
4. 修復下游根因：DB 連線池、外部 API 超時、batch 寫入策略，這才是消除連環 rebalance 的根本。

### Case 2：lag 集中單一 partition、加 consumer 無效

徵兆：`--describe` 顯示一兩個 partition lag 數十萬、其餘 partition lag 接近零；加了 consumer 之後 lag 不降，新 consumer 處於閒置（`--members` 顯示它分到的 partition 都沒 lag）。

根因：producer 的 key 分布有熱點，大量訊息落在同一 partition。Partition 是 Kafka 平行消費的最小單位，一個 partition 只能被 group 內一個 consumer 消費，熱點 partition 的消費速度被單 consumer 鎖死，加再多 consumer 都分不到這個 partition 的工作。

修法：

1. `--describe` 確認 lag 集中形狀，排除「整體容量不足」的均勻分布情境。
2. 找出熱點 key：抽樣訊息看 key 分布，常見是 null key（全落同一 partition）或單一大租戶 id。
3. 重設計 key：對熱點加 salt 打散到多 partition，或讓熱點走獨立 topic 用更多 partition。
4. 若 work 本身有 skew（單筆訊息處理成本差異大），把 parallelism 從 partition 數解耦，按工作量重新分派，如 Airbnb 的 balanced reader（[3.C15](/backend/03-message-queue/cases/kafka-airbnb-spark-streaming-rebalance/)）。

> key 重分布需要 producer 端配合改 key 策略，對既有 topic 是破壞性變更（舊訊息 key 不變），通常搭配新 topic 切換。本文未實機驗證 producer key 重設計的線上切換流程，依官方分區語義說明。

### Case 3：deploy 每次都產生 lag spike

徵兆：每次滾動部署 consumer 服務，lag 在部署窗口內明顯上升、部署完成後緩慢回落；group STATE 在部署期間進入 rebalance；部署越頻繁，累積 lag 越明顯。

根因：每個 consumer pod 重啟，coordinator 看到舊 member 離開、新 member 加入，觸發 rebalance；若用 eager protocol，每次 rebalance 全 group 停止消費；滾動部署逐個重啟 N 個 pod 就觸發 N 次 rebalance，每次全停，lag 在這串全停窗口中累積。

修法：

1. 啟用 static membership：給每個 consumer 固定 `group.instance.id`，重啟時帶同一身分回來、不觸發 rebalance。
2. 把 `session.timeout.ms` 設得比 pod 重啟時間長：涵蓋 K8s 重啟一個 pod 的 10-30 秒，否則 static membership 在窗口內失效。
3. 切換到 cooperative incremental protocol：即使仍有 rebalance，只有換手 partition 中斷，未換手 partition 持續消費。
4. 控制部署並行度：一次重啟太多 pod 會放大同時 rebalance 的影響，分批滾動。

Walmart 在 25K+ consumer 規模下，正是 pod scaling / deploy / heartbeat fail 三類事件持續觸發 rebalance lag spike（[3.C17](/backend/03-message-queue/cases/kafka-walmart-mps-rebalance/)）；static membership 與 cooperative 降低單次代價，但它最終把 consumer 解耦成可獨立 auto-scale 的 stateless service，從架構層消除 rebalance 與 partition 數的綁定。

### Case 4：scale-to-zero 後冷啟動 lag

徵兆：低流量時段 consumer 被縮到 0，流量回來時 lag 已累積一批、需要一段 catch-up；autoscaler 若看 CPU / memory 反應遲鈍，因為 sink 多為 I/O bottleneck、CPU 平坦不觸發擴容。

根因：event-driven workload 的工作量是 backlog（lag）而非 resource usage。用 CPU / memory 當 scaling signal，在 I/O-bound 的 sink consumer 上失靈：訊息堆積但 CPU 不高，autoscaler 不動，lag 持續成長。

修法：

1. 用 consumer lag 當 scaling signal：lag 超過閾值就擴 consumer、lag 清空就縮，直接對齊工作量。
2. 接受 scale-to-zero 的冷啟動 lag 為設計取捨：minReplicaCount=0 省下 idle 成本，代價是流量回來時的 catch-up 窗口，對非即時 sink 可接受。
3. 設 lag 閾值與擴容步長：閾值太高 catch-up 久、太低頻繁擴縮，依 SLA 對 backlog 的容忍度設定。

Trivago 跨 3 region 跑 50+ Kafka sink、每個 always-on 用 1 CPU + 1 GB，CPU/mem autoscaling 對 I/O-bound sink 無效；改用 KEDA 以 consumer lag 為 scaling signal、minReplicaCount=0 達到 scale-to-zero，daily replica-hour 從 50 降到 1-2（[3.C22](/backend/03-message-queue/cases/kafka-trivago-keda-scale-to-zero/)）。這個案例的判準是 resource usage 不等於工作量，event-driven 場景該看 backlog signal。

## Capacity 與 cost

Rebalance 與 lag 的容量規劃圍繞三個變數：partition 數、consumer 數、單次 rebalance 的中斷成本。partition 數是消費平行度的天花板，consumer 數超過 partition 數時多出的 consumer 閒置，所以 partition 數要按峰值需要的平行度規劃，但 partition 過多會推高 metadata 壓力與 rebalance 計算成本。

| 維度                    | 估算                                              | 警戒                                        |
| ----------------------- | ------------------------------------------------- | ------------------------------------------- |
| Consumer 數上限         | 等於 partition 數，超出即閒置                     | consumer = partition 仍跟不上要加 partition |
| Eager rebalance 中斷    | 全 group 停止消費直到分配收斂                     | partition 多、group 大時窗口顯著            |
| Cooperative rebalance   | 僅換手 partition 中斷，可能兩輪                   | 換手比例高時優勢縮小                        |
| session.timeout.ms 窗口 | consumer 死亡到被踢出、partition 無人消費         | 設太大則故障偵測慢、lag 累積                |
| 加 partition 的代價     | 提高平行度上限，但增加 rebalance 與 metadata 成本 | 過度分區推高 controller 壓力                |

實務 default：partition 數按峰值平行度設、保留成長餘量但不過度分區；consumer 數對齊 partition 數、用 lag 而非 CPU 當 autoscaling signal；rebalance 頻繁的環境優先 static membership + cooperative，再評估是否需要把 consumer 從 partition 解耦。加 partition 是單向操作（無法縮回），且改變既有 key 的 partition 對應，要在規劃期一次設足而非事後頻繁調整。

## 整合與下一步

Rebalance 與 lag 診斷接在 consumer 設計與交付語義之上：commit 策略決定 lag 的計算基準與 rebalance 後的重複消費風險，交付語義決定 rebalance 中斷期間訊息是否可能丟失或重放。

### 跟 consumer 設計對位

[3.4 consumer 設計](/backend/03-message-queue/consumer-design/) 涵蓋 commit 策略（auto vs manual）、commit 時機與 partition 分配的整體設計。本文的 rebalance 是 consumer 設計在「成員變動」維度的展開，lag 是 commit 進度的可觀測量。commit 策略選錯會在 rebalance 後放大重複消費或丟失。

### 跟交付與復原語義對位

[3.6 processing 與 recovery 語義](/backend/03-message-queue/processing-recovery-semantics/) 涵蓋 rebalance 中斷期間的 at-least-once / at-most-once 行為。rebalance revoke partition 時，未 commit 的進度會在新 consumer 接手後重放（at-least-once）；commit 太早則可能在 rebalance 中丟失（at-most-once）。idempotency 與 replay 的整體設計見 [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)。

### 相關案例

- [3.C15 Airbnb Spark Streaming](/backend/03-message-queue/cases/kafka-airbnb-spark-streaming-rebalance/) — partition-task 1:1 造成 data skew、parallelism 從 partition 數解耦
- [3.C17 Walmart MPS](/backend/03-message-queue/cases/kafka-walmart-mps-rebalance/) — 25K+ consumer 在 K8s 的 rebalance storm、consumer 解耦成 stateless service
- [3.C22 Trivago KEDA](/backend/03-message-queue/cases/kafka-trivago-keda-scale-to-zero/) — consumer lag 驅動 scale-to-zero、backlog signal 取代 resource usage

### 相關連結

- 上游 vendor 頁：[Apache Kafka](/backend/03-message-queue/vendors/kafka/)
- 知識卡：[consumer lag](/backend/knowledge-cards/consumer-lag/)、[consumer group](/backend/knowledge-cards/consumer-group/)、[partition](/backend/knowledge-cards/partition/)
- 下游能力：[3.4 consumer 設計](/backend/03-message-queue/consumer-design/)、[3.6 processing 與 recovery 語義](/backend/03-message-queue/processing-recovery-semantics/)
