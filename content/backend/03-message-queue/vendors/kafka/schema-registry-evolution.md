---
title: "Kafka Schema Registry 與 schema 演進：wire format、compatibility level 與安全演進規則"
date: 2026-06-16
description: "Kafka 跨系統事件總線的 schema 治理 implementation deep article — Schema Registry（Confluent / Apicurio）角色、Avro / Protobuf / JSON Schema 取捨、subject naming strategy、backward / forward / full / none 及其 transitive 版本、producer 帶 schema ID 的 5-byte wire format、加欄位帶 default 與刪欄位分步的安全演進規則；含 4 個 production 故障演練與實機驗證的 REST API 回應"
weight: 14
tags: ["backend", "message-queue", "kafka", "schema-registry", "avro", "schema-evolution", "deep-article"]
---

> 本文是 [Apache Kafka](/backend/03-message-queue/vendors/kafka/) overview「KRaft 與 Schema Registry」段的 implementation-layer deep article。Overview 已交代 Schema Registry 在事件總線中的定位；本文聚焦 *怎麼設 compatibility、wire format 長什麼樣、schema 怎麼安全演進、演進設錯會打掛什麼*。對應 [Event Schema Compatibility](/backend/knowledge-cards/event-schema-compatibility/) 知識卡的 implementation 展開。

## 為什麼事件總線需要一個獨立的 schema 治理元件

Schema Registry 是把「event 的結構契約」從 producer 與 consumer 的程式碼裡抽出來、集中存放並強制版本相容性的元件。它承擔的責任是讓不同 service、不同部署節奏的 producer 與 consumer 在 schema 改版時仍能互通，而不需要全體同時上線。Kafka broker 本身只存 bytes、不理解 payload 結構；一旦多個團隊往同一個 topic 寫事件、又各自獨立發版，schema 漂移就會在 consumer 端炸開。

這個責任在單一 service 內部不存在。一個 service 自己 produce、自己 consume，schema 改版同一個 deploy 就同步了，序列化用什麼格式都行。Schema Registry 解的是 *跨 service、跨團隊、跨部署時間* 的契約問題：A 團隊升級了訂單事件加一個欄位，B 團隊的對帳服務還跑舊版 consumer，C 團隊的風控服務跑更舊版——三方不同步演進，靠的就是 registry 在 producer 註冊新 schema 時先擋下破壞相容性的改動。

Yelp 的 [Schematizer 案例](/backend/03-message-queue/cases/kafka-yelp-schematizer/) 把這個責任拉到極端：一天數十億訊息、數百個 service、數千個 schema，自建 registry 強制所有 message 走 Avro、訊息只帶 schema ID。它揭露 schema 治理是 data pipeline 的核心責任、不是 add-on——當規模到了數千 schema，沒有集中強制的相容性檢查，跨服務事件契約會在某次發版後悄悄斷掉，而 broker 不會報任何錯。

Confluent Schema Registry 是業界事實標準的實作；Apicurio 是 CNCF 生態的開源替代，額外支援 OpenAPI / AsyncAPI artifact、且提供 Confluent-compatible API endpoint，遷移成本低。兩者都把 schema 存進一個 Kafka topic（Confluent 用 `_schemas`，single-partition、compacted），registry 自己是無狀態的，掛掉重啟後從該 topic rebuild。

## Schema ID 嵌進訊息的 wire format

Confluent wire format 在每筆訊息的 value（或 key）前面加 5 個 byte：1 個 magic byte（固定 `0x00`）加 4 個 big-endian byte 的 schema ID，後面才接序列化後的 payload。Consumer 拿到訊息先讀這 5 個 byte，用 schema ID 去 registry 查對應 schema，再用該 schema 反序列化。這是「訊息只帶 schema ID、不帶 schema 本體」的機制——schema 本體只在 registry 存一份，訊息裡放的是指標。

本文用 OrbStack 起 `confluentinc/cp-kafka` + `confluentinc/cp-schema-registry`，用 Avro console producer 寫一筆 `{"id":1,"name":"alice"}`，再 dump 出 raw bytes 驗證 wire format：

```text
000000 00 00 00 00 01 02 0a 61 6c 69 63 65 0a   >.......alice.<
```

逐 byte 拆解：

- `00`：magic byte，標識這是 Confluent wire format
- `00 00 00 01`：4-byte big-endian schema ID = 1，consumer 拿這個去 registry 查 schema
- `02`：Avro 把 `id`（long）以 zigzag varint 編碼，`1` 編成 `0x02`
- `0a 61 6c 69 63 65`：`name`（string）長度 5（zigzag `0x0a`）加 UTF-8 的 `alice`

這個格式有兩個工程後果。第一，consumer 反序列化任何訊息前都要能連到 registry——registry 掛掉，已 cache schema ID 的 consumer 還能跑，但遇到沒見過的 schema ID 就卡住。第二，schema ID 是全域單調遞增的整數、跨 subject 共用：同一份 schema 被多個 topic 註冊只會有一個 ID。實機驗證可以看到，先註冊到 `user-value` 的 schema 拿到 `id:1`，之後用同樣結構寫 `users-demo` topic 時，registry 認出是同一份 schema、複用 `id:1`：

```json
{"subject":"users-demo-value","version":1,"id":1,"schemaType":"AVRO", ...}
```

`version` 是 subject 內的序號（每個 subject 從 1 開始）、`id` 是全域的。除錯時看到某筆訊息反序列化失敗，第一步就是讀那 4-byte schema ID、去 registry 撈出它指向哪個 schema、跟 consumer 預期的對不對。

## 序列化格式取捨：Avro、Protobuf、JSON Schema

Schema Registry 支援三種格式，差異不只是語法、而是演進規則與生態的取捨。

| 格式        | 演進機制                          | 適合場景                                    |
| ----------- | --------------------------------- | ------------------------------------------- |
| Avro        | reader / writer schema resolution | data pipeline、強 schema 演進需求、JVM 生態 |
| Protobuf    | field number 標記                 | 已用 gRPC、跨語言 RPC + 事件共用 schema     |
| JSON Schema | 結構 + validation keyword         | 已大量 JSON、要人類可讀、容忍較弱的型別保證 |

Avro 的演進靠 *reader schema 與 writer schema 分離*：訊息用 writer schema（寫入時的版本）序列化，consumer 用自己的 reader schema（讀取時的版本）反序列化，registry 提供兩者做 schema resolution。這是 Avro 在 data pipeline 場景的核心優勢——欄位帶 default 時，舊資料用新 schema 讀會自動填 default，新資料用舊 schema 讀會自動忽略多出來的欄位。Yelp、多數 Kafka-native data platform 都選 Avro，正是因為它的演進語意最完整。

Protobuf 用 field number 而非欄位名做 wire 識別：欄位改名不破壞相容性（number 沒變即可），刪欄位要 reserve 掉 number 避免重用。已經用 gRPC 的團隊讓 RPC 與事件共用同一份 `.proto`，省一套 schema 維護。代價是 Protobuf 的 default 語意較弱（proto3 沒有 explicit presence 的 scalar 一律有 zero value），某些演進判斷不如 Avro 直觀。

JSON Schema 適合既有系統已經大量用 JSON、且看重人類可讀與 validation keyword（`required`、`minimum`、`pattern`）的場景。代價是 payload 較大（欄位名重複出現在每筆訊息）、型別保證弱於前兩者。當吞吐量大、payload size 敏感時，JSON Schema 的頻寬成本會顯著高於 Avro 的 binary 編碼。

選型判準：data pipeline 為主、重演進安全 → Avro；已有 gRPC、RPC 與事件共用 → Protobuf；既有 JSON 生態、重可讀性而吞吐量不極端 → JSON Schema。三者可在同一個 registry 並存（每個 subject 各自標 schemaType），但同一個 subject 內不能混用格式。

## Subject naming strategy 決定相容性檢查的邊界

Subject 是 registry 裡做版本管理與相容性檢查的基本單位；naming strategy 決定「哪些 schema 被歸進同一個 subject、因而要互相相容」。選錯 strategy 會讓相容性檢查管太寬或太窄，是後面故障演練的根源之一。

| Strategy                | Subject 名                      | 相容性檢查邊界                          |
| ----------------------- | ------------------------------- | --------------------------------------- |
| TopicNameStrategy       | `<topic>-value` / `<topic>-key` | 整個 topic 只能有一種 value schema 演進 |
| RecordNameStrategy      | `<record 全名>`                 | 同名 record 跨所有 topic 一起演進       |
| TopicRecordNameStrategy | `<topic>-<record 全名>`         | 同 topic 內可放多種 record、各自演進    |

TopicNameStrategy 是預設，subject 名就是 `<topic>-value`。實機驗證可以看到，用 Avro producer 寫 `users-demo` topic 時，registry 自動建立 `users-demo-value` subject：

```json
["user-value","users-demo-value"]
```

預設策略的隱含假設是「一個 topic 只承載一種事件型別」。這對多數 topic 成立，但當業務要把多種相關事件（例如 `OrderCreated` 與 `OrderCancelled`）放進同一個 topic 以保證跨事件 ordering 時，TopicNameStrategy 會把兩種 record 當成同一個 subject 的版本演進、互相做相容性檢查——這幾乎一定失敗，因為兩種事件結構本來就不同。

這時要改 RecordNameStrategy（subject = record 全名，跨 topic 同名 record 共用一份演進歷史）或 TopicRecordNameStrategy（subject = topic + record 名，同 topic 多型別各自獨立演進）。判準：一個 topic 一種事件 → 預設即可；一個 topic 多種事件且要保 ordering → TopicRecordNameStrategy；同一種 record 散在多個 topic 要強制全域一致 → RecordNameStrategy。Producer 與 consumer 必須設成同一個 strategy，否則 consumer 會用錯 subject 去查 schema。

## Compatibility level：四種基礎 × transitive

Compatibility level 是 registry 在 producer 註冊新 schema 時套用的相容性規則，決定哪些 schema 改動會被擋下。它回答的問題是「新 schema 跟既有 schema 比，誰應該能讀誰寫的資料」。設定可以是全域預設、也可以 per-subject 覆寫。

| Level    | 規則                             | 保護對象                         |
| -------- | -------------------------------- | -------------------------------- |
| BACKWARD | 新 schema 能讀舊 schema 寫的資料 | consumer 先升級、producer 後升級 |
| FORWARD  | 舊 schema 能讀新 schema 寫的資料 | producer 先升級、consumer 後升級 |
| FULL     | 同時滿足 BACKWARD 與 FORWARD     | 雙向都能不同步演進               |
| NONE     | 不檢查                           | 不保護（演進風險全交給人）       |

BACKWARD 是 Confluent 預設，實機驗證可以確認：

```json
{"compatibilityLevel":"BACKWARD"}
```

BACKWARD 保護的是「consumer 先升級」的演進順序——新版 consumer 必須能讀舊版 producer 還在寫的舊資料。它允許的安全改動是「加帶 default 的欄位」與「刪欄位」：新 schema 讀舊資料時，舊資料缺的新欄位用 default 補；新 schema 不要的欄位讀舊資料時忽略。它擋下的是「加沒有 default 的必填欄位」——舊資料沒這欄位、新 consumer 又要求它存在，就讀不出來。

FORWARD 反過來保護「producer 先升級」：舊版 consumer 要能讀新版 producer 寫的資料。它允許「刪帶 default 的欄位」與「加欄位」。當演進順序是 producer 先上、consumer 慢慢跟（例如先讓 producer 開始寫新欄位、consumer 之後才用）時選 FORWARD。

FULL 同時滿足兩者，代價是只能做「加帶 default 的欄位」與「刪帶 default 的欄位」這類雙向安全的改動，演進自由度最低但最安全。當 producer 與 consumer 的升級順序無法協調（大型組織、多團隊各自排程）時，FULL 把演進約束到怎麼改都不會斷。

四種各有一個 transitive 變體（`BACKWARD_TRANSITIVE` 等）。非 transitive 只檢查新 schema 對 *最近一版*；transitive 檢查新 schema 對 *該 subject 所有歷史版本*。差別在這個場景：v1 → v2 相容、v2 → v3 相容，但 v3 對 v1 不相容。非 transitive 會放行 v3（因為只比 v2）；transitive 會擋下。當 consumer 可能 replay 很舊的歷史資料（Kafka 的長期保留 + replay 正是常態），transitive 才能保證任何歷史版本都讀得出來。[3.7 event contract / replay boundary](/backend/03-message-queue/event-contract-replay-boundary/) 講的 replay 邊界，在 schema 層的對應就是 transitive compatibility。

## 安全演進規則：實機驗證註冊與拒絕

把上面的規則落到實際操作。在預設 BACKWARD 下，註冊 v1（`id` + `name`）後，加一個帶 default 的 `email` 欄位是安全的，registry 接受並記為 v2：

```json
{"id":2,"version":2,"schemaType":"AVRO", ...}
```

`user-value` 的版本列表確認累積成兩版：

```json
[1,2]
```

接著嘗試加一個 *沒有 default* 的 `age`（int）必填欄位——這破壞 BACKWARD，因為新 consumer 讀舊資料時 `age` 沒值也沒 default。registry 回 HTTP 409 並指出確切原因：

```json
{"error_code":40901,"message":"Schema being registered is incompatible with an earlier schema for subject \"user-value\", details: [{errorType:'READER_FIELD_MISSING_DEFAULT_VALUE', description:'The field 'age' at path '/fields/3' in the new schema has no default value and is missing in the old schema', ...}], compatibility: 'BACKWARD'}
```

`READER_FIELD_MISSING_DEFAULT_VALUE` 精確命中規則：reader（新 schema）多了一個舊資料沒有、又無 default 的欄位。registry 另外提供 compatibility check API，可以在不真正註冊的前提下先問「相不相容」，給 CI pipeline 在 PR 階段擋下破壞性改動：

```json
{"is_compatible":false}
```

由此導出兩條安全演進的操作規則。**加欄位**：一律帶 default（BACKWARD / FULL 都要），舊資料才能用新 schema 讀出。沒有合理 default 的「必填新欄位」不能直接加——要嘛在 producer 端先全部開始寫該欄位、確認資料齊全後再 promote，要嘛走新 topic / 新 record 而非原地演進。**刪欄位**：分步做。先讓所有 consumer 停止依賴該欄位（部署一輪），確認沒人讀之後，下一輪才從 schema 拿掉。一步到位刪掉還在被讀的欄位，會在 FORWARD / FULL 下被擋、在 BACKWARD 下放行但打掛還沒升級的 consumer。

## Production 故障演練

### Case 1：producer 加必填欄位無 default，打掛舊 consumer

**徵兆**：某團隊 producer 發版後，另一團隊的舊 consumer 開始大量反序列化失敗、`SerializationException` 或 `AvroTypeException: Found X, expecting Y`，consumer lag 暴衝、訊息卡在 poll 階段。producer 端與 broker 端完全沒報錯——訊息照寫成功。

**根因**：subject 的 compatibility level 被設成 NONE（或該欄位走了 FORWARD 不檢查 reader 缺欄位的路徑）。producer 加了一個沒有 default 的必填欄位、registry 沒擋，新訊息帶新 schema ID 寫進 topic。舊 consumer 用自己的舊 reader schema 去反序列化新 writer schema 的資料，遇到自己不認識又無從補值的結構就炸。問題不在 producer 也不在 broker，在 *registry 沒在註冊時擋下這次演進*。

**修法**：

1. **把 compatibility level 改回至少 BACKWARD**：實機驗證過 NONE 會直接放行破壞性 schema——把 `compatibility` 設成 NONE 後，前面被 409 拒絕的破壞性 schema 立刻被接受成 v3。NONE 等於把演進安全完全交給人，多團隊場景幾乎一定出事。
2. **回退 producer**：先讓 producer 退回舊 schema 止血，恢復舊 consumer 可讀。
3. **重新演進**：欄位帶 default 重發，或若該欄位語意上必填、走「先讓 producer 寫、consumer 升級、再 promote」的分步路徑。
4. **CI 防線**：把 compatibility check API（`/compatibility/subjects/<s>/versions/latest`）接進 producer repo 的 CI，PR 階段就用 `is_compatible:false` 擋掉，不等到 production 註冊時才發現。

### Case 2：compatibility level 設錯，放行破壞性變更

**徵兆**：team 以為有 registry 把關所以放心演進，某次刪掉一個還在被下游讀的欄位、registry 接受了，下游服務隔天開始拿到 null / 缺欄位、business logic 走錯分支，但沒有任何 exception——資料「看起來正常」只是少了東西。

**根因**：compatibility level 設成了 FORWARD 而需求其實是 BACKWARD，或設成 NONE。實機驗證可以看到 per-subject 覆寫的行為——對 `user-value` 單獨 PUT `FORWARD` 後查 config 回 `{"compatibilityLevel":"FORWARD"}`，這個 subject 的檢查方向就跟全域預設不同了。FORWARD 允許刪帶 default 的欄位（保護 producer 先升級的順序），但團隊實際的演進順序是 consumer 後升級——方向錯配，registry 放行的正是會打掛 consumer 的那類改動。

**修法**：

1. **依演進順序選 level，不是隨手設**：consumer 先升級選 BACKWARD；producer 先升級選 FORWARD；順序無法協調選 FULL。把這個決策寫進 topic ownership 文件、不是留給註冊當下的人臨時判斷。
2. **可能 replay 歷史就用 transitive**：Kafka 長期保留 + replay 是常態，非 transitive 只擋最近一版、replay 舊資料時舊 schema 仍可能讀不出。長期保留的 topic 預設用 `*_TRANSITIVE`。
3. **per-subject 覆寫要留審計**：全域預設外的每一個 per-subject 覆寫都是一個風險點，要能查出「誰、何時、為什麼把這個 subject 改成跟預設不同」。

### Case 3：schema ID 對不上，consumer 反序列化失敗

**徵兆**：consumer 報 `Schema not found; error code: 40403` 或反序列化拿到亂碼、欄位錯位。某些訊息正常、某些失敗，跟特定 producer 或特定時間段相關。

**根因**有幾種，靠讀訊息前 5 byte 的 schema ID 定位：

- **registry 換過、ID 不一致**：跨環境（dev / staging / prod）各自一套 registry，schema ID 全域遞增的順序不同，同一份 schema 在不同環境是不同 ID。如果有人把 prod 的訊息 mirror 到 staging 而沒搬 schema，staging consumer 拿 prod 的 schema ID 去 staging registry 查就 404。
- **訊息根本不是 Confluent wire format**：有 producer 沒走 schema-aware serializer、直接寫 raw bytes，前 5 byte 不是 magic + ID。consumer 把第一個 byte 當 magic、後 4 byte 當 ID 去查，撈到不存在或錯誤的 schema。
- **registry 不可達或 cache 失效**：consumer 端 schema cache 沒命中、又連不上 registry。

**修法**：

1. **讀 wire format 確認**：dump 訊息 raw bytes，確認第一個 byte 是 `00`、接下來 4 byte 解出來的 ID 在目標 registry 查得到。本文驗證過 `00 00 00 00 01` 對應 schema id 1，這是除錯的第一手證據。
2. **跨環境 schema 搬遷**：mirror 訊息時用 registry 的 import / export，或 MirrorMaker 搭配 schema 同步，不要只搬資料不搬 schema。
3. **隔離非 schema-aware producer**：用 ACL 或 topic 命名規範強制所有 producer 走 schema serializer，避免 raw bytes 混進 schema-managed topic。

### Case 4：subject naming strategy 衝突

**徵兆**：把第二種事件型別寫進既有 topic 時，producer 直接註冊失敗報 incompatible，或多 producer 寫同 topic 互相把對方的 schema 判成不相容、彼此發版互相擋。

**根因**：用 TopicNameStrategy（預設）卻往同一個 topic 放多種 record。subject 是 `<topic>-value`、整個 topic 共用一條演進線，registry 拿 `OrderCancelled` 去跟既有的 `OrderCreated` 做相容性檢查——兩種結構不同的事件當然不相容。strategy 的隱含假設（一 topic 一事件型別）跟實際用法（一 topic 多事件保 ordering）衝突。

**修法**：

1. **改 strategy 配合用法**：一 topic 多事件 → TopicRecordNameStrategy，subject 變成 `<topic>-<record 全名>`，每種 record 各自一條演進線、不互相檢查。
2. **producer 與 consumer 設同一個 strategy**：strategy 不一致時 consumer 會用錯 subject 查 schema，拿到 null 或錯 schema。這是部署層的硬約束，要在共用 config 統一。
3. **若只是不小心寫錯 topic**：那不是 strategy 問題、是路由問題，修 producer 的 topic 選擇邏輯，別為了繞過檢查改成 RecordNameStrategy。

## 容量與運維邊界

| 維度                 | 估算 / 邊界                                     | 警戒                                 |
| -------------------- | ----------------------------------------------- | ------------------------------------ |
| Schema 數量          | 數千 schema registry 仍可運作（Yelp 等級）      | `_schemas` topic 是 single-partition |
| Wire format overhead | 每筆訊息固定 +5 byte                            | 高頻小訊息時相對 overhead 不可忽略   |
| Registry 可用性      | consumer cache 命中時可短暫容忍 registry 不可達 | 冷 consumer / 新 schema ID 時硬依賴  |
| Compatibility 檢查   | 註冊時做、非 hot path                           | transitive 對長歷史 subject 檢查較慢 |
| 環境隔離             | 每環境一套 registry、schema ID 不跨環境一致     | 跨環境 mirror 要同步搬 schema        |

實務 default：data pipeline 場景選 Avro + 至少 BACKWARD；長期保留 + replay 的 topic 用 transitive；compatibility check 接進 CI 在 PR 階段擋破壞性改動，不依賴註冊當下把關；一 topic 一事件型別當預設、要多型別才動 naming strategy。Schema Registry 自己也是個要 HA 的元件——production 跑多副本、`_schemas` topic 的 replication factor 拉高，registry 是事件總線的單點時要當關鍵基礎設施對待。

## 整合與下一步

### 跟 CDC pipeline 的銜接

[Shopify Debezium CDC 案例](/backend/03-message-queue/cases/kafka-shopify-debezium-cdc/) 跑在 100+ MySQL shard、150 個 Debezium connector 的規模（該案例記載的重點是 lock-free snapshot 與 oversized record 處理）。CDC pipeline 有一個一般性的 schema 演進壓力，以下依 CDC 機制推導、非該案例的結論：上游 DDL 一改，Debezium 產生的 Kafka record schema 跟著變，下游 consumer 受影響。Schema Registry 的 compatibility 檢查就是把這道衝擊在進 Kafka 時攔下的關卡——選錯 compatibility level，一次 ALTER TABLE 就可能透過 CDC 打穿整條 pipeline。Debezium 與 Kafka Connect 原生整合 Schema Registry，connector 設定裡指定 registry URL 與 naming strategy。

### 跟 replay 邊界與事件契約

[3.7 event contract / replay boundary](/backend/03-message-queue/event-contract-replay-boundary/) 講的是事件契約能 replay 多遠；schema 層的對應就是本文的 transitive compatibility。Replay 跨越多個 schema 版本時，只有 transitive 能保證任何歷史版本都讀得出來。兩者一起界定「這條事件流的契約能安全回放到多久以前」。

### 下游能力

- 概念索引：[Event Schema Compatibility](/backend/knowledge-cards/event-schema-compatibility/) 知識卡（本文的 implementation 來源）
- 上游 vendor 頁：[Apache Kafka](/backend/03-message-queue/vendors/kafka/)（KRaft 與 Schema Registry 段）
- 對應案例：[3.C14 Yelp Schematizer](/backend/03-message-queue/cases/kafka-yelp-schematizer/)（schema 治理拉到平台層）、[3.C13 Shopify Debezium CDC](/backend/03-message-queue/cases/kafka-shopify-debezium-cdc/)（CDC 場景的 schema evolution）
- 方法論：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
