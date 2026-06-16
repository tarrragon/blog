---
title: "Kafka Multi-tenant 治理：quota 限流、ACL 授權與 topic 生命週期"
date: 2026-06-16
description: "單一 Kafka 叢集承載多團隊時、quota 把頻寬與 request 容量切給每個租戶、ACL 把寫入與讀取權限綁到 principal、topic 命名規範劃出 ownership 邊界、生命週期治理回收死 topic 釋放 metadata 壓力。本文涵蓋 producer_byte_rate / consumer_byte_rate / request_percentage 三類 quota 與 user / client-id / 組合三種套用層級、StandardAuthorizer 的 principal × resource × operation × host 授權模型、prefixed ACL 的 tenant 隔離、TopicGC 式的死 topic 回收、以及四個 production 故障演練（單租戶暴衝吃滿頻寬、ACL 過鬆過緊、topic 數量爆炸壓垮 controller、unused topic 未回收）"
weight: 15
tags: ["backend", "message-queue", "kafka", "multi-tenant", "quota", "acl", "governance", "deep-article"]
---

> 本文是 [Apache Kafka](/backend/03-message-queue/vendors/kafka/) overview「Multi-tenant 與配額治理」「Topic 生命週期治理」兩段的 implementation-layer deep article。Overview 說明這些議題對應哪些案例跟子議題、本文展開具體的 quota / ACL 配置、授權模型推導、故障徵兆與修法。

## 共享叢集的治理問題：一個叢集、多個互不信任的租戶

Multi-tenant Kafka 的核心問題是把一個物理叢集切成多個彼此隔離的邏輯空間、讓每個團隊用同一組 broker 卻不互相干擾。當 Kafka 從單一團隊的工具長成全公司的事件總線、叢集承載的不再是一條 pipeline、而是數十到數百個團隊的 producer 跟 consumer。這時叢集的瓶頸從「broker 夠不夠快」轉成「怎麼防止某個團隊的流量、權限、或 topic 失控波及其他所有人」。

[Uber 的 Kafka 平台演進](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/)把這個轉換描述為「從單隊列問題提升到平台治理問題」。當事件平台服務眾多團隊、重點是配額、隔離、觀測與運維標準化、而非只擴 broker。擴 broker 解決的是總容量、解決不了「單一租戶吃光共享資源」這類隔離問題。

共享叢集的治理分三個獨立的軸、各自處理不同的失控來源：

| 治理軸            | 防的是什麼                                      | 工具                                | 失控後果                             |
| ----------------- | ----------------------------------------------- | ----------------------------------- | ------------------------------------ |
| Quota（資源配額） | 單租戶吃滿頻寬 / request 容量、餓死其他租戶     | `kafka-configs.sh` 設 byte rate     | 鄰居 producer 寫入卡死、consumer lag |
| ACL（存取授權）   | 租戶讀寫不屬於自己的 topic、或被未授權方寫入    | `kafka-acls.sh` + broker authorizer | 資料外洩、跨租戶污染、誤刪 topic     |
| 生命週期（治理）  | 死 topic 累積、partition 數爆炸壓垮 metadata 面 | 命名規範 + 活躍判準 + 自動回收      | controller 變慢、rebalance 風暴      |

三軸正交：quota 設好不代表權限對、ACL 鎖好不代表 topic 不會爆炸。下面逐軸展開、每軸都對應 production 踩過的失控場景。本文 quota 與 ACL 操作以 Kafka 4.2.0（KRaft 模式、`apache/kafka:latest`）實機驗證。

## Quota：把頻寬與 request 容量切給租戶

Quota 是 broker 端對 client 的流量上限、由 broker 在超限時主動 throttle（延遲回應）而非拒絕、讓單一租戶無法把共享頻寬吃光。Kafka 的 quota 是 broker-side 強制、不依賴 client 自律 —— 即使 client 不配合、broker 也會在回應裡插入 throttle 延遲、把該 client 的有效吞吐壓回配額內。

### 三類 quota 度量

Kafka quota 度量三種資源、對應三類飽和：

| Quota 鍵             | 單位      | 限制對象                                            | 飽和訊號                          |
| -------------------- | --------- | --------------------------------------------------- | --------------------------------- |
| `producer_byte_rate` | bytes/sec | 單一 client 每秒寫入 broker 的 bytes                | 寫入端 network / disk I/O 飽和    |
| `consumer_byte_rate` | bytes/sec | 單一 client 每秒從 broker 讀取的 bytes              | 讀取端 network 飽和、fan-out 過大 |
| `request_percentage` | 百分比    | 單一 client 佔用 broker request handler 的 CPU 時間 | broker CPU 飽和、小訊息高頻請求   |

前兩個 byte rate 防的是頻寬類飽和、適合「大訊息、穩定流量」的租戶。`request_percentage` 防的是另一種失控 —— 某租戶送大量極小的 request（例如每筆一個 byte、每秒幾萬筆）、byte rate 看起來很低、卻把 broker 的 request handler thread 佔滿。這種「請求數爆炸但流量不大」的攻擊型 pattern 只有 `request_percentage` 抓得到。一個 broker 預設有 N 個 request handler thread、`request_percentage=200` 代表允許該 client 用掉 2 條 thread 的時間（100% = 1 條）。

### 三種套用層級

Quota 可以套在三種 entity 上、精度遞增：

| 套用層級         | entity 指定                                | 適用情境                             |
| ---------------- | ------------------------------------------ | ------------------------------------ |
| client-id        | `--entity-type clients --entity-name <id>` | 沒有認證、用 client.id 區分服務      |
| user             | `--entity-type users --entity-name <user>` | 有 SASL 認證、整個租戶共用一個 quota |
| user + client-id | 兩個 entity 同時指定                       | 同租戶內不同服務分別配額（最細）     |

層級的選擇取決於認證模型。沒開認證的叢集只能用 client-id —— 但 client.id 由 client 自行宣告、可偽造、只適合內部信任環境的粗略區分。開了 SASL 認證後、user 才是可信的租戶邊界、quota 綁 user 才有隔離意義。最細的 user + client-id 組合用在「同一個租戶內、batch 匯入服務跟即時 API 服務要分開限流」這種情境：整個 billing 租戶有一個總配額、但裡面的 `batch-importer` 再單獨壓低、避免夜間批次把租戶配額吃光、害同租戶的即時服務沒頻寬。

### 設定與查詢（實機驗證）

設 client-id 層級、同時給 producer 跟 consumer byte rate：

```bash
kafka-configs.sh --bootstrap-server localhost:9092 --alter \
  --add-config 'producer_byte_rate=1048576,consumer_byte_rate=2097152' \
  --entity-type clients --entity-name svc-orders
# Completed updating config for client svc-orders.
```

設 user 層級、含 `request_percentage`：

```bash
kafka-configs.sh --bootstrap-server localhost:9092 --alter \
  --add-config 'producer_byte_rate=5242880,consumer_byte_rate=10485760,request_percentage=200' \
  --entity-type users --entity-name tenant-billing
# Completed updating config for user tenant-billing.
```

設 user + client-id 組合層級（同租戶內單獨壓低 batch 服務）：

```bash
kafka-configs.sh --bootstrap-server localhost:9092 --alter \
  --add-config 'producer_byte_rate=524288' \
  --entity-type users --entity-name tenant-billing \
  --entity-type clients --entity-name batch-importer
# Completed updating config for user tenant-billing.
```

查詢時 entity 指定要對齊設定時的層級。查 user 層級：

```bash
kafka-configs.sh --bootstrap-server localhost:9092 --describe \
  --entity-type users --entity-name tenant-billing
# Quota configs for user-principal 'tenant-billing' are
#   consumer_byte_rate=1.048576E7, request_percentage=200.0, producer_byte_rate=5242880.0
```

組合層級要兩個 entity 都帶、否則查不到：

```bash
kafka-configs.sh --bootstrap-server localhost:9092 --describe \
  --entity-type users --entity-name tenant-billing \
  --entity-type clients --entity-name batch-importer
# Quota configs for user-principal 'tenant-billing', client-id 'batch-importer' are
#   producer_byte_rate=524288.0
```

不帶 `--entity-name` 而只給 `--entity-type clients` 會列出所有 client-id 層級的 quota、適合稽核整個叢集的 quota 分布。

## ACL：把存取權限綁到 principal

ACL 是 broker 對每個操作的授權檢查、把「誰（principal）能對什麼資源（resource）做什麼操作（operation）從哪裡來（host）」綁成一條規則、broker 在每次 produce / fetch / admin 操作前比對。Quota 管的是「用多少」、ACL 管的是「能不能用」—— 兩者正交、quota 不限制權限、ACL 不限制流量。

### 授權模型四要素

一條 ACL 由四個維度構成、四個維度交集才決定一次操作是否放行：

| 維度      | 含義                                  | 範例值                                             |
| --------- | ------------------------------------- | -------------------------------------------------- |
| principal | 操作的發起身分                        | `User:svc-orders`                                  |
| resource  | 被操作的對象（type + name + pattern） | topic `orders.events`、group `fulfillment-workers` |
| operation | 動作                                  | `Write` / `Read` / `Describe` / `All`              |
| host      | 來源 IP（`*` 為不限）                 | `10.0.3.21`                                        |

resource 的 pattern type 是隔離設計的關鍵：`LITERAL` 精確匹配單一資源名、`PREFIXED` 匹配整個前綴。多租戶的 topic 隔離靠 prefixed ACL 加命名規範 —— 給 `tenant-billing` 一條 `billing.` 前綴的 `All` 權限、它就能自由管理所有 `billing.` 開頭的 topic、卻碰不到 `orders.` 或別租戶的命名空間。命名規範在這裡不只是整潔、是授權邊界本身。

operation 的選擇要對齊角色。一個 producer 需要 topic 的 `Write` 跟 `Describe`（描述 partition metadata）；一個 consumer 需要 topic 的 `Read` `Describe` 加上 consumer group 的 `Read` `Describe`（commit offset 要對 group 有權）。漏掉 group 的 ACL 是常見錯誤：consumer 能讀到訊息、卻 commit 不了 offset、表現成不斷重複消費。

### KRaft 的 StandardAuthorizer

ACL 的儲存與判定由 broker 的 authorizer 負責。KRaft 模式用 `org.apache.kafka.metadata.authorizer.StandardAuthorizer`、ACL 存在 metadata log（取代 ZooKeeper 時代的 `AclAuthorizer` 把 ACL 存在 ZK）。預設的 `apache/kafka` 容器不開 authorizer —— 不開時所有操作放行、ACL 指令也無從生效。啟用需要在 broker 設三項：

```properties
authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer
super.users=User:admin
allow.everyone.if.no.acl.found=false
```

`super.users` 列出繞過所有 ACL 檢查的管理身分、用來開機跟救援；少了它、開 authorizer 後第一個操作就會把自己鎖在外面。`allow.everyone.if.no.acl.found=false` 是隔離的前提 —— 設 `true` 時「沒有任何 ACL 的資源對所有人開放」、等於 deny-list 模式、漏設一個 topic 就全公司可讀。多租戶必須走 `false` 的 allow-list 模式：預設拒絕、明確授權才放行。

> 本文 ACL 操作以實機驗證：用上述三項 env（`KAFKA_AUTHORIZER_CLASS_NAME` / `KAFKA_SUPER_USERS='User:ANONYMOUS'` / `KAFKA_ALLOW_EVERYONE_IF_NO_ACL_FOUND=false`）配完整 KRaft single-node 設定起容器、PLAINTEXT 連線的 principal 為 `User:ANONYMOUS`、設為 super user 後即可用 `kafka-acls.sh` 操作。

### ACL 配置（實機驗證）

給 producer 對單一 topic 的 write + describe：

```bash
kafka-acls.sh --bootstrap-server localhost:9092 --add \
  --allow-principal User:svc-orders \
  --operation Write --operation Describe \
  --topic orders.events
```

給 consumer topic 的 read + describe、外加 consumer group 的權限（一條指令同時建兩個 resource 的 ACL）：

```bash
kafka-acls.sh --bootstrap-server localhost:9092 --add \
  --allow-principal User:svc-fulfillment \
  --operation Read --operation Describe \
  --topic orders.events \
  --group fulfillment-workers
```

prefixed ACL 把整個命名空間授權給一個租戶：

```bash
kafka-acls.sh --bootstrap-server localhost:9092 --add \
  --allow-principal User:tenant-billing \
  --operation All \
  --resource-pattern-type prefixed \
  --topic billing.
# Adding ACLs for resource
#   `ResourcePattern(resourceType=TOPIC, name=billing., patternType=PREFIXED)`
```

host 限制把同一 principal 的權限綁到特定來源 IP：

```bash
kafka-acls.sh --bootstrap-server localhost:9092 --add \
  --allow-principal User:svc-orders \
  --allow-host 10.0.3.21 \
  --operation Write \
  --topic orders.events
```

deny 規則的優先序高於 allow —— 同一 principal 即使有 allow、命中 deny 就拒絕。用來在大範圍 allow（如 prefixed `All`）之上挖一個例外：

```bash
kafka-acls.sh --bootstrap-server localhost:9092 --add \
  --deny-principal User:svc-orders \
  --deny-host 10.0.9.99 \
  --operation Write \
  --topic orders.events
```

列出特定 topic 的全部 ACL、用於稽核：

```bash
kafka-acls.sh --bootstrap-server localhost:9092 --list --topic orders.events
```

## Topic 生命週期治理：命名、ownership 與回收

Topic 生命週期治理把「topic 的建立、歸屬、淘汰」變成有規則的流程、避免死 topic 累積與 partition 數爆炸壓垮叢集的 metadata 面。Kafka 的每個 partition 都是 controller 要追蹤的 metadata 單位；topic 只增不減時、partition 總數隨團隊數線性成長、最終 controller 的 metadata 處理、broker 的 leader election、client 的 metadata fetch 都跟著變慢。

### 命名規範劃出 ownership

Topic 命名規範把 ownership 跟隔離邊界編碼進名字本身。一個可治理的命名規範通常含三段：租戶 / 領域前綴、語意名、版本。例如 `billing.invoices.v1` —— `billing.` 前綴對齊 prefixed ACL 的隔離邊界跟 quota 的租戶歸屬、`invoices` 是語意、`v1` 給 schema 演進留出平行存在的空間。命名規範在多租戶不是風格問題、是三個治理軸的共同錨點：ACL 靠前綴授權、quota 靠前綴歸屬、回收靠前綴找 owner。

實機建 topic 時 Kafka 4.2.0 對 `.` 跟 `_` 混用會出 metric 名稱碰撞警告：

```text
WARNING: Due to limitations in metric names, topics with a period ('.')
or underscore ('_') could collide. To avoid issues it is best to use
either, but not both.
```

成因是 metric 名把 topic 名裡的 `.` 跟 `_` 都正規化掉、`billing.invoices` 跟 `billing_invoices` 可能對映到同一條 metric。命名規範應在 `.` 跟 `_` 之間選一個當分隔符、全叢集一致、避免監控數據互相污染。

### 活躍判準與自動回收

死 topic 的回收靠可量化的活躍判準。[LinkedIn 的 TopicGC](/backend/03-message-queue/cases/linkedin-topicgc-kafka-governance/)以自動治理取代手動清理未使用 topic、降低 metadata 壓力並改善 produce / consume 效能。它的判讀是：當 queue 規模擴大、僅靠容量擴充不夠、topic 生命週期與治理自動化會成為可靠性關鍵。

TopicGC 是 LinkedIn 的內部系統、不是 Kafka 內建指令；它揭示的是一套可借鏡的回收流程結構：

1. 定義活躍判準：以 last produce / last consume timestamp 判斷 topic 是否仍在使用、設一段觀察窗（例如 N 天無寫入且無讀取）。
2. 分級回收：先標記（soft）、進入待回收狀態並通知 owner、保留一段 grace period、無人認領才真正刪除（hard）。兩段式避免誤刪仍有低頻流量的 topic。
3. 保留稽核：每次標記與刪除留紀錄、回收前後比對 controller log、partition 數量、produce / consume 效能指標、確認治理有效且無誤傷。

回收條件的設定要對齊業務節奏。純看 produce timestamp 會誤判「低頻但關鍵」的 topic（如月結批次）；活躍判準要同時看 produce 跟 consume、且觀察窗要長於最長的合法閒置週期。

## Production 故障演練

### Case 1：單一租戶暴衝吃滿頻寬（quota 缺位）

**徵兆**：某團隊上線一支新 backfill job、開始全速寫入；同叢集其他租戶的 producer 端 `request-latency` p99 從個位數 ms 跳到數百 ms、consumer lag 全面上升；broker network out 打到網卡上限、但 CPU 不高。受害的不是暴衝者自己、是所有共用 broker 的鄰居。

**根因**：叢集沒設任何 producer quota、或只對部分租戶設了 quota。沒有 broker-side throttle 時、單一 client 能用滿 broker 的 network / disk I/O、把共享頻寬擠光。byte rate 飽和的特徵是 network 打滿但 CPU 不高 —— 區別於 `request_percentage` 缺位導致的 CPU 飽和。

**修法**：

1. 立即對暴衝 client 設 `producer_byte_rate`、broker 即時 throttle、無需重啟。
2. 建立 quota 預設值：對所有 client-id（或 user）設一個保守的 default byte rate、新租戶上線自動受限、避免「漏設就無限」。
3. 區分 byte rate 與 request_percentage 飽和：network 打滿設 byte rate、CPU 打滿（高頻小訊息）補 `request_percentage`。
4. 容量規劃：把各租戶 quota 總和對齊 broker 的 network / disk 容量、留 headroom、避免「每個 quota 都合理但加總超過物理上限」。

### Case 2：ACL 設太鬆或太緊

**徵兆（太鬆）**：稽核發現某 consumer 服務能讀到不屬於它的租戶 topic；或某 topic 被預期外的 principal 寫入、資料被污染。最壞情況是 `allow.everyone.if.no.acl.found=true` 下漏設 ACL 的 topic 對全叢集可讀寫。

**徵兆（太緊）**：consumer 能讀訊息卻不斷重複消費、log 顯示 commit offset 被拒；或 producer 報 `TOPIC_AUTHORIZATION_FAILED`、明明該有權限。

**根因**：太鬆來自 deny-list 心態 —— `allow.everyone.if.no.acl.found=true` 把「沒設 ACL」當成「開放」、漏設就外洩。太緊通常是漏掉 operation 或 resource：consumer 只給了 topic 的 `Read`、漏給 consumer group 的 `Read` `Describe`、於是讀得到但 commit 不了、表現成重複消費；producer 漏給 `Describe`、拿不到 partition metadata。

**修法**：

1. 走 allow-list：`allow.everyone.if.no.acl.found=false`、預設拒絕、明確授權才放行。
2. ACL 對齊角色模板：producer = topic Write + Describe；consumer = topic Read + Describe 加 group Read + Describe；漏 group ACL 是重複消費的常見根因。
3. 用 prefixed ACL 而非逐 topic 設、把授權邊界對齊命名規範前綴、減少漏設。
4. 稽核流程：定期 `kafka-acls.sh --list` 比對預期授權矩陣、把 ACL 納入版本控制與 review、而非手動逐條加。

### Case 3：Topic 數量爆炸壓垮 metadata 面

**徵兆**：叢集 topic / partition 總數隨團隊增長爬到數萬以上；controller failover 時間從秒級拉長到分鐘級；broker 啟動載入 metadata 變慢；client 的 metadata fetch 變大變慢、rebalance 期間出現連鎖延遲。容量沒滿、但整個叢集的 control plane 變鈍。

**根因**：partition 是 controller 要追蹤的 metadata 單位、數量只增不減。每個團隊隨手建 topic、每個 topic 又開高 partition 數、總 partition 數線性甚至超線性成長、壓垮 metadata 處理。KRaft 相比 ZooKeeper 提高了 metadata 上限、但上限仍存在、不是無限。

**修法**：

1. Partition 數規劃納入 topic 建立流程：partition 數對應並行度上限、不是越多越好；多餘 partition 是純 metadata 成本。詳見 [Partition](/backend/knowledge-cards/partition/) 卡。
2. 回收死 topic 釋放 partition slot：見 Case 4 與生命週期治理段。
3. 監控 metadata 壓力訊號：controller log、partition 總數、controller failover 時間設告警、在壓垮前介入。
4. 規模化路徑：單叢集 metadata 逼近上限時、評估分群（critical / standard / experimental 多叢集）、見 overview 的 [Cross-region 與分層叢集](/backend/03-message-queue/vendors/kafka/)段與 [LinkedIn Tiered Clusters](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/)案例。

### Case 4：Unused topic 未回收

**徵兆**：叢集裡大量 topic 數月無 produce 也無 consume、卻持續佔 partition slot 跟 metadata；沒人記得某些 topic 屬於哪個團隊、不敢刪；新 topic 想建時撞到 partition 上限、被迫先擴叢集而非先回收。

**根因**：沒有活躍判準與回收流程、topic 只建不刪。歸屬資訊沒編碼進命名、回收時找不到 owner、於是「不敢刪」成為預設、死 topic 無限累積。這是 Case 3（metadata 爆炸）的慢性來源。

**修法**：

1. 建立活躍判準：以 last produce / last consume timestamp 加觀察窗判定死 topic、觀察窗長於最長合法閒置週期（避免誤刪月結類低頻 topic）。
2. 兩段式回收：先 soft 標記並通知 owner、grace period 內無人認領才 hard 刪除、避免誤刪。
3. 命名規範補 ownership：前綴對齊團隊、回收時能直接找到 owner、消除「不敢刪」。
4. 自動化加稽核：參考 [TopicGC](/backend/03-message-queue/cases/linkedin-topicgc-kafka-governance/)的流程結構、回收前後比對 metadata 與效能指標、留稽核紀錄。

## 容量與規模邊界

| 維度                   | 估算 / 訊號                                        | 警戒與下一步                                     |
| ---------------------- | -------------------------------------------------- | ------------------------------------------------ |
| Quota 總和 vs 物理容量 | 各租戶 byte rate 加總對 broker network / disk 容量 | 加總逼近物理上限要重新切分、留 headroom          |
| ACL 條目數             | 逐 topic 設會隨 topic 數線性成長                   | 改 prefixed ACL 對齊命名規範、降條目數與漏設風險 |
| Partition 總數         | controller failover 時間、metadata fetch 延遲      | 逼近上限先回收死 topic、再評估分群               |
| Topic 活躍率           | 有 produce / consume 的 topic 佔比                 | 死 topic 比例高代表缺回收流程、補活躍判準        |

Quota 與 ACL 是 broker-side 即時生效、不需重啟、可隨租戶調整、運維成本低。生命週期治理是持續流程、不是一次性操作 —— 死 topic 會持續產生、回收要常態化。三軸的共同前提是命名規範：沒有可治理的命名、quota 找不到歸屬、ACL 邊界對不齊、回收找不到 owner。多租戶治理的第一步是先把命名規範立起來、再談 quota 與 ACL。

## 整合與下一步

### 跟 overview 與案例的對位

- 上游 vendor 頁：[Apache Kafka](/backend/03-message-queue/vendors/kafka/) —— 本文展開其「Multi-tenant 與配額治理」「Topic 生命週期治理」兩段
- 平台治理案例：[3.C6 Uber Kafka 事件平台](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/) —— 單隊列問題提升到平台治理
- 生命週期案例：[3.C3 LinkedIn TopicGC](/backend/03-message-queue/cases/linkedin-topicgc-kafka-governance/) —— 自動回收與 metadata 壓力
- 規模化分群：[3.C4 LinkedIn Tiered Clusters](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/) —— metadata 逼近上限時的多叢集路徑
- 自管轉 managed 的 ACL cutover：[3.C2 VMware → MSK](/backend/03-message-queue/cases/vmware-kafka-to-msk/)

### 跟安全模組對位

ACL 是 Kafka 內建的授權層、處理 broker 級的 principal × resource 授權。完整的 secret 管理（SASL 認證憑證怎麼發、輪替、撤銷）屬於 [07 資料保護與安全模組](/backend/07-security-data-protection/)的範疇 —— ACL 綁的 principal 從哪來、由認證層決定、ACL 只負責「這個 principal 能做什麼」。多租戶的完整信任鏈是「認證確認身分（07）→ ACL 授權操作（本文）→ quota 限制用量（本文）」三層。

### 下一步議題

- Schema 治理：跨租戶共用 topic 時、schema compatibility 是另一層契約治理、見 overview 的 [KRaft 與 Schema Registry](/backend/03-message-queue/vendors/kafka/)段
- Consumer group ACL 細節：跟 [Consumer group](/backend/knowledge-cards/consumer-group/) rebalance 的互動
- Quota 與 [delivery semantics](/backend/knowledge-cards/delivery-semantics/)：throttle 延遲對 producer timeout / retry 的影響

## 相關連結

- 上游 vendor 頁：[Apache Kafka](/backend/03-message-queue/vendors/kafka/)
- 對位 deep article（同模組）：本模組其他 Kafka deep article 見 vendor 頁進階主題段
- 跨模組授權鏈：[07 資料保護與安全模組](/backend/07-security-data-protection/)
- 方法論：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
- 知識卡：[Topic](/backend/knowledge-cards/topic/)、[Partition](/backend/knowledge-cards/partition/)、[Consumer group](/backend/knowledge-cards/consumer-group/)
