---
title: "Kafka Replication、ISR 與 exactly-once：從 acks 到端到端不重不漏"
date: 2026-06-16
description: "Kafka 的可靠性由 replication 與 ISR 決定寫入承諾、由 producer idempotence 與 transaction 決定處理語義。本文涵蓋 acks=0/1/all 取捨、min.insync.replicas 與 ISR shrink/expand 的真實行為、enable.idempotence 去重、Kafka transaction + read_committed 隔離、以及端到端 exactly-once 的邊界與成本；含 3-broker 叢集停 broker 觀察 ISR 收縮到低於 min.insync 後 acks=all 被拒的實機演練。"
weight: 12
tags: ["backend", "message-queue", "kafka", "replication", "isr", "exactly-once", "deep-article"]
---

> 本文是 [Kafka](/backend/03-message-queue/vendors/kafka/) overview「Replication 與 exactly-once 升級」段的 implementation-layer deep article。Overview 已給出 partition / replication 的選型定位、本文展開 *寫入承諾* 跟 *處理語義* 兩條獨立軸線怎麼設、邊界在哪、成本是什麼。對應反例 [3.C9 Queue 語義誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)。

## 寫入承諾與處理語義是兩條獨立軸線

Kafka 的可靠性拆成兩個彼此正交的問題、混在一起談是多數誤配的起點。第一條軸線是 *寫入承諾*：一筆訊息寫進 broker 後、在多少 replica 落地才算「成功」、broker 掛掉時這筆訊息會不會消失。這條軸線由 replication factor、ISR、`acks` 與 `min.insync.replicas` 共同決定、屬於 broker 端的耐久性保證。第二條軸線是 *處理語義*：同一筆訊息在 producer 重送、consumer 重啟、partition rebalance 等情境下、會不會被寫進去兩次或被處理兩次。這條軸線由 producer idempotence、transaction 與 consumer 端的 commit 設計決定、屬於端到端的正確性保證。

兩條軸線可以獨立調整：可以有「寫入承諾很強但處理語義是 at-least-once」的配置（acks=all + 非冪等 consumer）、也可以有「寫入承諾較弱但已開冪等」的配置。把 exactly-once 當成單一開關去找、是因為沒看出這兩條軸線存在。本文先講第一條（replication / ISR / acks）、再講第二條（idempotence / transaction）、最後談兩者疊起來能達成什麼、達不成什麼。

這個拆分對映 [delivery semantics](/backend/knowledge-cards/delivery-semantics/) 與 [idempotency](/backend/knowledge-cards/idempotency/) 兩張知識卡：前者描述 broker 承諾的送達次數、後者描述處理端怎麼讓「送達多次」不等於「生效多次」。

## ISR：誰算「跟得上」的副本

ISR（in-sync replica、同步副本集）是一個 partition 當前「跟得上 leader」的 replica 集合、是 Kafka 把 replication factor 這個 *靜態配置* 轉成 *動態保證* 的關鍵概念。Replication factor = 3 只說明這個 partition 有 3 份 replica；但任一時刻真正跟得上 leader 的可能只有 2 份或 1 份。ISR 就是這個「當前實際同步」的集合、寫入承諾的判斷都基於 ISR、不是基於 replication factor。

一個 follower 留在 ISR 內的條件是：它在 `replica.lag.time.max.ms`（預設 30 秒）內持續向 leader 拉取資料、且追上 leader 的 log end offset。當 follower 因為 broker 慢、網路抖動、GC 停頓或 disk 壓力而落後超過這個時間窗、leader 會把它移出 ISR — 這就是 ISR shrink（收縮）。當它恢復、重新追上、再被加回 ISR — 這是 ISR expand（擴張）。

ISR 收縮本身不是故障、是 Kafka 對「這個 follower 暫時不可信」的誠實表態。真正的風險在於：ISR 收縮到某個程度後、`acks=all` 的寫入承諾會無法滿足 `min.insync.replicas` 而開始拒絕寫入。下一段的 acks 取捨直接建立在 ISR 這個概念上。

實機看 ISR 的方式是 `kafka-topics.sh --describe`、Isr 欄位列出當前同步的 broker id：

```bash
# RF=3、min.insync.replicas=2 的 topic、三 broker 都同步時
kafka-topics.sh --describe --topic repl-demo --bootstrap-server kafka1:9092
# Topic: repl-demo  PartitionCount: 1  ReplicationFactor: 3  Configs: min.insync.replicas=2
#   Topic: repl-demo  Partition: 0  Leader: 2  Replicas: 2,3,1  Isr: 2,3,1
```

Replicas 欄位是 *配置上* 的 3 份副本、Isr 欄位是 *當前實際同步* 的集合。兩者一致代表健康；Isr 比 Replicas 短代表有副本落後。日常巡檢用 `kafka-topics.sh --describe --under-replicated-partitions` 直接列出 Isr 短於 Replicas 的 partition。

## acks 與 min.insync.replicas：寫入承諾的兩個旋鈕

寫入承諾由 producer 端的 `acks` 跟 broker / topic 端的 `min.insync.replicas` 共同決定、兩者必須一起設才有意義。`acks` 決定 producer 在收到「成功」回應前、要等多少 replica 確認；`min.insync.replicas` 決定 broker 在 ISR 不足時是否拒絕寫入。前者是 producer 的等待策略、後者是 broker 的拒絕底線。

`acks` 三個值對應遞增的耐久性與遞增的延遲成本：

| acks 值 | 承諾                              | 資料風險                                             | 延遲 |
| ------- | --------------------------------- | ---------------------------------------------------- | ---- |
| 0       | 不等任何確認、送出即視為成功      | leader 沒收到也不知道、broker 掛掉直接丟             | 最低 |
| 1       | leader 寫入本地 log 即回成功      | leader 確認後、follower 同步前掛掉、這筆訊息遺失     | 中   |
| all     | ISR 內所有 replica 都確認才回成功 | ISR 內任一存活即不丟；ISR 不足 min.insync 時拒絕寫入 | 最高 |

`acks=0` 適用「丟一兩筆無所謂」的場景、例如高頻 metric 上報、log shipping 的非關鍵層。它把網路往返成本壓到最低、代價是 producer 完全不知道 broker 有沒有收到。任何牽涉金流、訂單、狀態變更的訊息都不該用 acks=0。

`acks=1` 是一個容易被誤以為安全的中間值。它只等 leader 寫入本地、不等 follower 同步。多數時候運作正常、但存在一個明確的資料遺失窗口：leader 回了成功、follower 還沒拉到這筆訊息、此時 leader 所在 broker 崩潰、新 leader 從 follower 中選出 — 那筆「已回成功」的訊息在新 leader 上不存在、producer 卻以為寫成功了。這個窗口在正常運行時很窄、但在 broker 滾動重啟、硬體故障、AZ 中斷時會被放大。

`acks=all` 是耐久性配置的正解、但只有搭配 `min.insync.replicas ≥ 2` 才完整。單獨設 acks=all、若 `min.insync.replicas=1`、那麼當 ISR 收縮到只剩 leader 一份時、acks=all 等同 acks=1 — 「所有 ISR 確認」這個條件在 ISR 只剩 1 份時形同虛設。`min.insync.replicas=2` 補上這個漏洞：它要求 ISR 至少有 2 份才接受 acks=all 寫入、否則直接拒絕、把「靜默遺失」轉成「明確拒絕」。

`min.insync.replicas` 是 topic-level 可動態調整的配置、不需重啟 broker：

```bash
# 動態調整單一 topic 的 min.insync.replicas
kafka-configs.sh --alter --topic repl-demo \
  --add-config min.insync.replicas=2 \
  --bootstrap-server kafka1:9092

# 查當前值、synonyms 會顯示 topic override 蓋過 broker default
kafka-configs.sh --describe --topic repl-demo --bootstrap-server kafka1:9092
# min.insync.replicas=2 synonyms={DYNAMIC_TOPIC_CONFIG:min.insync.replicas=2,
#   DYNAMIC_DEFAULT_BROKER_CONFIG:min.insync.replicas=1, DEFAULT_CONFIG:min.insync.replicas=1}
```

RF=3 + acks=all + min.insync.replicas=2 是業界對「不能丟資料」topic 的標準三件組：3 份副本提供冗餘、acks=all 要求同步確認、min.insync=2 在容忍一台 broker 掛掉的同時仍保證每筆寫入落在至少兩份 replica。容忍度的算術是 `RF - min.insync.replicas`：3 - 2 = 1、代表可以掉一台 broker 仍正常寫入、掉兩台則寫入被拒（但已寫入的資料不丟）。

## Producer idempotence：去掉重送造成的重複

Producer idempotence（冪等生產者、`enable.idempotence=true`）解決的是 *producer 重送* 造成的 broker 端重複。它讓「producer 因為沒收到 ack 而重送同一筆訊息」這件事、在 broker 端被去重、不會寫進兩筆。這是處理語義軸線的第一塊、獨立於前面的寫入承諾。

問題的根源是：producer 送出訊息後、若因網路超時沒收到 broker 的 ack、它無法分辨是「訊息沒送到」還是「訊息送到了但 ack 在回程丟了」。預設行為是重送。在沒有冪等保護時、若實際是後者、broker 就收到兩筆相同訊息、partition 裡出現重複。

冪等機制的做法是給每個 producer 分配一個 producer ID（PID）、並為每個 partition 維護一個遞增的 sequence number。Broker 記住每個 (PID, partition) 已接受的最大 sequence；重送的訊息帶相同 sequence、broker 認出是重複、直接丟棄並回成功。這個保證的範圍是 *單一 producer session 內、單一 partition* 的精確一次寫入。

開啟方式是 producer 端設 `enable.idempotence=true`。在較新版 Kafka 這已是預設值、且它會隱含要求 `acks=all`、`retries > 0`、`max.in.flight.requests.per.connection ≤ 5` — 因為冪等去重依賴這些前提。冪等的成本極低（broker 多維護 PID/sequence 的少量 metadata）、幾乎沒有理由關閉。

需要明確的邊界是：冪等只覆蓋 *同一個 producer session*。Producer 重啟後拿到新的 PID、broker 無法把新舊 session 的訊息關聯起來。跨 session 的去重、以及「寫多個 partition 要嘛全成功要嘛全失敗」的需求、要靠下一段的 transaction。

## Kafka transaction 與 read_committed：跨 partition 的原子寫入

Kafka transaction（交易）解決的是 *跨多個 partition 的原子寫入* 與 *consume-process-produce 的原子提交*。它讓一組寫入（可能跨多個 topic / partition）以及對應的 consumer offset commit、要嘛全部對下游可見、要嘛全部不可見。這是處理語義軸線的第二塊、建立在冪等之上。

典型場景是 stream processing 的 consume-process-produce 迴圈：consumer 讀入一批訊息、處理後產出結果寫到另一個 topic、然後 commit 讀取進度。若這三步不是原子的、崩潰時可能出現「結果已產出但 offset 沒 commit」（重啟後重複處理、重複產出）或「offset 已 commit 但結果沒寫成功」（訊息遺失）。Transaction 把「產出結果」跟「commit offset」綁成一個原子操作、消除這個窗口。

啟用 transaction 需要 producer 設一個穩定的 `transactional.id`、並在程式碼中走完整的 transaction 生命週期：

```text
producer.initTransactions()      // 向 transaction coordinator 註冊、fence 掉舊 session
producer.beginTransaction()
  producer.send(record1)          // 跨多個 topic/partition 的寫入
  producer.send(record2)
  producer.sendOffsetsToTransaction(offsets, groupMetadata)  // consumer 進度也納入交易
producer.commitTransaction()      // 全部原子提交；失敗則 abortTransaction()
```

`transactional.id` 提供跨 session 的 fencing（隔離）：同一個 transactional.id 的新 producer 啟動時、coordinator 會 fence 掉舊的、避免「殭屍 producer」在崩潰後復活還繼續寫。這是冪等的 PID 機制做不到的跨 session 保證。

> **實機限制**：`kafka-console-producer.sh` 帶 `--producer-property transactional.id=...` 不會自動呼叫 `initTransactions()`、會直接報 `IllegalStateException: Cannot add partition ... before completing a call to initTransactions`。完整 transaction 生命週期只能在 client code 中驗證、無法用 console 工具演示。本文的 transaction 行為描述依官方 producer API 語義、生命週期程式碼未經本地 client 實機跑通。

Transaction 的另一半在 consumer 端：`isolation.level=read_committed`。預設的 `read_uncommitted` 會讀到尚未 commit、甚至最終被 abort 的 transactional 訊息。設成 `read_committed` 後、consumer 只會看到已 commit 的 transactional 訊息、abort 的訊息對它不可見、未 commit 的訊息會被擋在 last stable offset（LSO）之前等待。

```bash
# consumer 以 read_committed 隔離級別讀取、只看已 commit 的 transactional 訊息
kafka-console-consumer.sh --topic repl-demo --from-beginning \
  --isolation-level read_committed \
  --bootstrap-server kafka1:9092
```

需要注意：對非 transactional 的普通訊息、read_committed 跟 read_uncommitted 行為相同 — 普通訊息一律可見。隔離級別只對 transactional 訊息產生差異。這也是為什麼若上游沒有任何 transactional producer、把 consumer 改成 read_committed 不會有任何可觀察的效果。

## 端到端 exactly-once 的邊界與成本

端到端 exactly-once 的意思是：訊息從 producer 到 consumer 處理結果、整條路徑上「不重不漏」。它由前面所有零件疊出來、但有明確的適用邊界、不是萬用保證。

Kafka 原生能提供 exactly-once 的範圍是 *Kafka-to-Kafka 的封閉迴圈*：consume from Kafka、process、produce to Kafka、commit offset、整個用 transaction 綁定。Kafka Streams 框架把這套封裝成 `processing.guarantee=exactly_once_v2` 一個配置、底層就是 transaction + 冪等 + read_committed 的組合。在這個封閉迴圈內、exactly-once 是真實成立的。

邊界出現在 *離開 Kafka 的那一刻*。當處理結果要寫進外部系統（資料庫、HTTP API、第三方服務、寄信、扣款）、Kafka 的 transaction 管不到外部系統的提交。一筆訊息「已扣款但 offset commit 前崩潰」這種跨系統不一致、Kafka transaction 無法消除 — 它只保證 Kafka 內部的原子性。跨系統的 exactly-once 要靠外部系統自己的冪等鍵（idempotency key）、或 outbox pattern、或兩階段提交、由應用層補上、不是 Kafka 送的。

成本方面、exactly-once 不是免費的耐久性升級：

| 成本維度         | 影響                                                                               |
| ---------------- | ---------------------------------------------------------------------------------- |
| 吞吐             | transaction 的 begin/commit 與 coordinator 往返增加 per-batch overhead、吞吐下降   |
| 延遲             | read_committed 要等 LSO 推進、consumer 端引入額外延遲                              |
| 複雜度           | producer 要管 transaction 生命週期、abort 路徑、fencing；錯誤處理比 fire-forget 重 |
| coordinator 壓力 | transaction coordinator 與 `__transaction_state` topic 成為新的關鍵路徑與容量點    |

務實的判斷是：先確認需求真的是 exactly-once、還是「at-least-once + 下游冪等」就夠。多數業務（包括金流）用 at-least-once 送達 + 下游用業務冪等鍵去重、就達到了「效果上不重複」、且吞吐與複雜度成本遠低於完整 transaction exactly-once。完整的 Kafka transaction exactly-once 留給 Kafka-to-Kafka 的 stream processing pipeline、那是它的甜蜜點。這個取捨對映 [3.6 processing-recovery-semantics](/backend/03-message-queue/processing-recovery-semantics/) 對「在哪一層放冪等」的判讀。

## 故障演練

可靠性配置的價值在故障時才顯現。以下演練在 3-broker KRaft 叢集（RF=3、min.insync.replicas=2）上跑、用停 broker 製造 ISR 收縮、觀察各配置的真實行為。

### ISR 收縮到低於 min.insync.replicas 時 acks=all 被拒

**演練**：起 3-broker 叢集、建 RF=3 / min.insync.replicas=2 的 topic、初始 ISR = 三台全在。依序停掉兩個 follower broker、觀察 ISR 收縮、再用 acks=all produce。

**初始狀態**（ISR 三份全在、acks=all 正常）：

```text
Topic: repl-demo  Partition: 0  Leader: 2  Replicas: 2,3,1  Isr: 2,3,1
# acks=all produce → exit=0
```

**停一個 follower（broker 3）**、ISR 收縮到 2 份、仍滿足 min.insync=2：

```text
Topic: repl-demo  Partition: 0  Leader: 2  Replicas: 2,3,1  Isr: 2,1
# acks=all produce → exit=0（ISR=2 仍 >= min.insync=2、寫入接受）
```

**再停一個 follower（broker 1）**、ISR 收縮到只剩 leader 1 份、低於 min.insync=2：

```text
# acks=all produce → broker 拒絕：
[Producer] Got error produce response ... Error: NOT_ENOUGH_REPLICAS, retrying
org.apache.kafka.common.errors.NotEnoughReplicasException:
  Messages are rejected since there are fewer in-sync replicas than required.
```

**判讀**：這正是 min.insync.replicas 的設計意圖在運作。ISR 不足時、broker 選擇 *明確拒絕寫入*（NOT_ENOUGH_REPLICAS）、而不是降級成 acks=1 默默接受。對 producer 而言、寫入失敗會觸發 retry、retry 耗盡後拋例外、上游應用感知到「現在寫不進去」、可以 fail-fast 或 backpressure — 而不是寫了一筆只在單一 broker 上、隨時可能隨那台 broker 一起消失的「假成功」訊息。把資料遺失轉成可觀測的寫入拒絕、是這個配置的全部目的。

**恢復**：重啟兩個 broker、ISR 自動 expand 回三份、acks=all 恢復接受寫入：

```text
Topic: repl-demo  Partition: 0  Leader: 2  Replicas: 2,3,1  Isr: 1,2,3
```

> 附帶觀察：在 KRaft 模式下、controller 也是 quorum（本演練三台都兼任 controller）。同時停掉兩台、controller quorum 失去多數、`kafka-topics.sh --describe` 對 metadata 的查詢會 timeout（DisconnectException）。production 叢集應把 controller 數量與 broker 故障域分開規劃、避免 broker 故障連帶打垮 metadata 平面。

### Unclean leader election 的取捨

當一個 partition 的所有 ISR replica 都不可用、只剩一個 *曾經落後、已被踢出 ISR* 的 replica 還活著、Kafka 面臨一個無法兩全的選擇。`unclean.leader.election.enable=false`（預設）會選擇 *不選 leader*：這個 partition 進入不可用狀態、拒絕讀寫、直到某個 ISR replica 恢復。`unclean.leader.election.enable=true` 會選擇 *把那個落後的 replica 提為 leader*：partition 立刻恢復可用、代價是那個 replica 上缺失的訊息（leader 掛掉前已 commit 但它還沒同步到的部分）永久遺失。

**判讀**：這是一個 *可用性 vs 耐久性* 的直接取捨、沒有正確答案、只有對映業務的選擇。對金流、訂單、審計這類「丟一筆都不行」的 topic、保持 false、寧可 partition 短暫不可用也不接受靜默資料遺失。對 metric、log、可重算的衍生資料、開 true 換可用性、丟幾筆可接受。預設 false 是合理的安全預設、但要意識到它的代價是「所有 replica 都不在 ISR 時、partition 會卡住不可用」、這在多 broker 同時故障時會發生。

### Idempotent producer 對重送去重

**演練**：producer 開 `enable.idempotence=true`、acks=all、模擬 ack 丟失導致的重送。

**判讀**：冪等開啟後、producer 因網路超時重送的訊息帶相同 (PID, partition, sequence)、broker 認出 sequence 重複、丟棄重送並回成功、partition 內不出現重複。實機上 `enable.idempotence=true` 的 produce 寫入正常（exit=0）、消費端讀回的訊息數等於實際送出的邏輯訊息數、重送不放大。要記住的邊界仍是：這只覆蓋單一 producer session；producer 重啟換 PID 後、跨 session 的重複要靠 transaction 或下游冪等鍵處理。

### Transaction 中途失敗的 read_committed 隔離

**演練**：transactional producer 在 beginTransaction 後寫入若干訊息、然後 abortTransaction（模擬處理中途失敗）；consumer 分別用 read_uncommitted 與 read_committed 讀取。

**判讀**：read_committed 的 consumer 看不到被 abort 的訊息 — 中途失敗的 transaction 對它等於沒發生過、不會讀到「處理一半的髒資料」。read_uncommitted 的 consumer 則會讀到這些最終被 abort 的訊息、若據此處理就產生了不該發生的副作用。這是 transaction 隔離的核心價值：把「transaction 失敗」的可見性控制在 commit 邊界內。

> 本段的 abort 行為依官方 transaction 語義描述。本地以 `kafka-console-consumer.sh --isolation-level read_committed` 驗證了隔離級別參數可用、且對已 commit 的普通訊息 read_committed 與 read_uncommitted 輸出一致（普通訊息一律可見、隔離級別只對 transactional 訊息產生差異）；完整的 begin/abort transaction 生命週期需 client code、未用 console 工具跑通。

## Capacity / cost

各配置的容量與成本影響、決定它適用的規模與 topic 類別：

| 配置                           | 吞吐 / 延遲影響                             | 適用                                      | 警戒                                       |
| ------------------------------ | ------------------------------------------- | ----------------------------------------- | ------------------------------------------ |
| acks=0                         | 最低延遲、最高吞吐                          | 可丟的 metric / log shipping              | 任何狀態變更類訊息不可用                   |
| acks=1                         | 中等、單次往返                              | 容忍極少量遺失的衍生資料                  | 誤當安全選項、broker 故障窗口會遺失        |
| acks=all + min.insync=2 + RF=3 | 延遲 +1 次跨 broker 往返、吞吐略降          | 不能丟的業務訊息                          | min.insync 沒設則 acks=all 在 ISR=1 時失效 |
| enable.idempotence=true        | 幾乎無額外成本                              | 所有 producer 預設開                      | 只覆蓋單一 session                         |
| transaction + read_committed   | begin/commit overhead、read 端 LSO 等待延遲 | Kafka-to-Kafka stream processing 封閉迴圈 | 跨外部系統不成立、coordinator 成新關鍵路徑 |

務實 default：

- 業務 topic 一律 RF=3 + acks=all + min.insync.replicas=2、idempotence 預設開
- 容忍度算術 `RF - min.insync.replicas` 要 ≥ 1、否則單台 broker 維護就會中斷寫入
- 完整 transaction exactly-once 只給 Kafka-to-Kafka pipeline；跨系統用 at-least-once + 下游冪等鍵
- unclean.leader.election 保持 false、除非該 topic 明確可丟資料換可用性

## 整合 / 下一步

### 跟 processing-recovery-semantics 對位

寫入承諾保證訊息留在 broker、但 *處理* 的不重不漏在 consumer 端。[3.6 processing-recovery-semantics](/backend/03-message-queue/processing-recovery-semantics/) 展開 consumer 的 commit 時機、崩潰恢復的 replay 範圍、以及「冪等放在哪一層」的判讀 — 跟本文的 transaction exactly-once 邊界互補：本文界定 Kafka 能送什麼、那篇界定處理端怎麼接才不放大重複。

### 跟 event-contract-replay-boundary 對位

Exactly-once 的封閉迴圈假設訊息格式穩定、replay 可重現。[3.7 event-contract-replay-boundary](/backend/03-message-queue/event-contract-replay-boundary/) 展開 schema 演進與 replay 邊界 — 當 transaction 提供的原子性遇上 schema 變更、replay 舊訊息的可重現性會受 contract 影響、是 exactly-once 在時間維度上的延伸限制。

### 對應反例 3.C9

[3.C9 Queue 語義誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) 是本文兩條軸線混淆的真實後果：broker 遷移後「名稱上相近的 delivery semantics」在失敗重播時產生不同結果、出現重複扣款與狀態漏更新。判讀路徑正是本文的拆分 — 先確認是寫入承諾（acks / ISR）還是處理語義（idempotence / commit 時機）出問題、不要用 queue depth 這種寫入承諾層的指標去判斷處理語義層的故障。

### 對應案例 3.C21 Goldman Sachs MSK 遷移

[3.C21 Goldman Sachs MSK 遷移](/backend/03-message-queue/cases/kafka-goldman-sachs-msk-migration/) 揭露遷移時可靠性配置的細節風險集中在 client 端的 timeout / flush / LB 配置、而非 broker 本身。本文的 acks=all 在 ISR 不足時拒絕寫入、若 client 端的 retry 與 timeout 沒對齊（如 flush timeout 太短）、會把「broker 正常的 backpressure」誤判成「遷移失敗」。可靠性配置與 client 容錯參數要一起驗證。

### 下一步路由

- 上游概念：[delivery semantics](/backend/knowledge-cards/delivery-semantics/)、[idempotency](/backend/knowledge-cards/idempotency/) 知識卡
- 同 vendor：[Kafka overview](/backend/03-message-queue/vendors/kafka/) 的 producer / consumer 設計段
- 下游能力：[3.6 processing-recovery-semantics](/backend/03-message-queue/processing-recovery-semantics/)、[3.7 event-contract-replay-boundary](/backend/03-message-queue/event-contract-replay-boundary/)、[6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)
- 方法論：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
