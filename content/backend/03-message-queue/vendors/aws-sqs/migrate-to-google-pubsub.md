---
title: "AWS SQS → Google Pub/Sub：queue 模型搬到 topic + subscription 模型的跨雲遷移"
date: 2026-06-16
description: "SQS 是單一 region-scoped pull queue、Pub/Sub 是 global topic + first-class subscription 的 pub/sub 模型；這篇跨雲 migration playbook 走 6 維 diff dimension audit（components / data topology 軸 High）、對位 visibility timeout → ack deadline、maxReceiveCount → dead-letter topic、long polling → streaming pull、IAM policy → Service Account、SQS-to-many-consumer 要重設計成 topic fan-out；含 5 個 production 故障演練（fan-out 行為差 / ack deadline 太短重投 / ordering key vs FIFO / 跨雲網路成本 / DLT 設定差）跟 dual-publish 漸進 cutover"
weight: 11
tags: ["backend", "message-queue", "aws-sqs", "google-pubsub", "migration", "cross-cloud"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [AWS SQS](/backend/03-message-queue/vendors/aws-sqs/) 跟 [Google Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/)。這是一個 *跨雲 managed-to-managed* 遷移：兩端都是 cloud-managed、運維負擔都低、但 *資料拓樸* 跟 *消費抽象* 不同 — SQS 是 region-scoped 的單一 pull queue、Pub/Sub 是 global topic + 多個 first-class subscription。主結構走 operational redesign hybrid（Type C）、額外為 components / data topology 兩個高維度抽獨立段。

## SQS 跟 Pub/Sub 不是同一種訊息抽象

SQS 跟 Pub/Sub 都是 cloud-managed 非同步訊息服務、都解「解耦 producer / consumer、不自管 broker」這個問題、application 程式碼裡都是「發訊息、收訊息、處理完確認」的形狀。從這層看兩者可互換、遷移像是換 SDK。

差別在 *消費抽象* 跟 *資料拓樸*。SQS 的核心實體是 queue：一條 region-scoped 的訊息隊列、訊息被一個 consumer 領走（in-flight）就對其他 consumer 隱形、處理完 DeleteMessage 就消失。要讓同一筆事件送給多個下游、SQS 端的做法是在 SNS 前面 fan-out、再各接一條 SQS queue。Pub/Sub 的核心實體是 topic + subscription 兩層：topic 收訊息、subscription 是 *first-class* 的消費端點、一個 topic 可掛 N 個 subscription、每個 subscription 各自維護消費進度、fan-out 是模型內建而不是外接。

這個差別決定了遷移的形狀。如果原系統只是「一條 queue、一群 worker 競爭領取」、那 Pub/Sub 端是「一個 topic、一個 pull subscription」、對位乾淨、application 改動小。如果原系統靠 SNS-to-many-SQS 做扇出、那 Pub/Sub 端是「一個 topic、多個 subscription」、整個 fan-out 拓樸要重畫、這不是換 SDK、是重設計訊息流。先判斷自己屬於哪一種、再決定 playbook 的重量。

## 為什麼會跨雲遷這條路徑

跨雲從 SQS 遷到 Pub/Sub 的 driver 跟同雲 vendor 切換不同、通常不是「Pub/Sub 比 SQS 好」、而是 *整體 workload 的重心移到 GCP*：

1. **資料平台落在 GCP**：下游分析走 BigQuery、streaming 走 Dataflow、容器跑 Cloud Run。事件如果留在 AWS、每筆都要跨雲搬到 GCP 才能進 BigQuery、跨雲 egress 費用跟延遲都是常態成本。把訊息層也移到 Pub/Sub、事件可以用 BigQuery subscription 直接落地、省掉中間搬運。
2. **需要 global topic、不想管 region**：SQS queue 綁 region、跨 region 要自己複製或在前面架路由。Pub/Sub topic 沒有 region 概念、publish 進去全球可訂閱、多區域服務的事件分發是 first-class。
3. **fan-out 從外接變內建**：原本靠 SNS + 多條 SQS 維護的扇出拓樸、在 Pub/Sub 是「一個 topic 掛多個 subscription」、少一層 SNS、扇出關係在 subscription 列表一覽。

這三條 driver 都假設 *重心已經或即將在 GCP*。如果系統長期紮根 AWS、只為了「換個 queue」跨雲、會付出跨雲 IAM 重對位、雙雲計費、跨雲網路延遲的代價、ROI 通常不成立。遷移前先確認 driver 是 workload 重心轉移、不是單純偏好。

## 結構為什麼是 operational hybrid 加兩個高維度獨立段

寫這篇前先跑 [diff dimension audit](/posts/migration-playbook-methodology/)、6 維評級如下：

| Diff 維度          | 評級   | SQS → Pub/Sub 的具體差異                                                          |
| ------------------ | ------ | --------------------------------------------------------------------------------- |
| Schema / API       | Medium | 都是「發 / 收 / 確認」、但 API 名詞與參數全換（QueueUrl → topic+subscription）    |
| Operational model  | High   | IAM policy → Service Account、CloudWatch → Cloud Monitoring、redrive → DLT 重訂閱 |
| Abstraction        | Medium | 都是訊息服務、但 pull queue ↔ topic/subscription 的消費抽象不同                   |
| Components（數量） | High   | 單一 queue ↔ topic + N subscription 兩層實體；SNS+SQS 扇出 ↔ topic 內建扇出       |
| Application change | Medium | SDK 換、ack / fan-out 邏輯改、但商業邏輯多數可保留                                |
| Data topology      | High   | region-scoped queue ↔ global topic；single-consumer ↔ multi-subscription fan-out  |

主導維度是 *operational model*（跨雲身份與監控全換）、所以主結構走 Type C operational redesign hybrid。但 components 跟 data topology 也是 High — 不是把它們塞進 operational 段就能講清楚的、消費抽象從「一條 queue」變「topic + 多 subscription」是讀者最容易踩雷的地方。按 [migration 方法論的 multi-axis 規則](/posts/migration-playbook-methodology/)、高維度抽成獨立段補充、不硬塞進單一 type 標籤。所以本篇結構是：operational 對位主軸 + 「消費抽象重設計」獨立段（components / topology 軸）+ 跨雲特有的 IAM 與網路段。

## Operational 對位：機制名詞換、語意要逐一確認

跨雲遷移最容易出錯的環節、是 *找到語意相近的功能、卻假設行為一致*。SQS 跟 Pub/Sub 多數機制都有對位、但每一組都有行為差、找得到對應功能只是第一步。下表先給對照、後面逐項展開語意陷阱。

| SQS 機制                        | Pub/Sub 對位                    | 語意是否等價                                      |
| ------------------------------- | ------------------------------- | ------------------------------------------------- |
| Visibility timeout              | Ack deadline                    | 近似、但上限與延長機制不同                        |
| DeleteMessage                   | Ack（acknowledge）              | 近似、但 Pub/Sub 自動 extension 改變實際行為      |
| maxReceiveCount + DLQ + redrive | Dead-letter topic + 重訂閱      | 概念對應、DLT 是 topic 不是 queue、重處理方式不同 |
| Long polling（WaitTimeSeconds） | Streaming pull                  | 不等價、streaming pull 是長連線串流、不是輪詢     |
| Message attributes              | Message attributes              | 概念對應、型別與大小限制不同                      |
| FIFO queue（MessageGroupId）    | Ordering key                    | 都給順序、但去重與吞吐取捨不同                    |
| IAM policy + Queue policy       | IAM role + Service Account      | 跨雲身份模型完全不同、不是改語法是重對位          |
| CloudWatch metric / alarm       | Cloud Monitoring metric / alert | metric 名詞與語意不同、alarm 邏輯要重寫           |

### Visibility timeout → ack deadline

Visibility timeout 跟 ack deadline 都回答同一個問題：consumer 領走訊息後、多久沒確認就視為失敗、把訊息重新投遞。語意對位成立、但兩端的數字與延長機制不同。

SQS visibility timeout 預設 30 秒、上限 12 小時、consumer 要延長就主動呼叫 ChangeMessageVisibility。Pub/Sub ack deadline 預設 10 秒、上限 600 秒（10 分鐘）、而且 client library 預設會 *自動* 在背景延長 deadline（lease management）。這個自動延長是最容易踩到的差異：在 SQS 端習慣「設一個夠長的 visibility timeout、處理完再 delete」、搬到 Pub/Sub 如果只把 ack deadline 設成 600 秒上限、卻沒意識到 client library 在背景幫忙延長、長任務的行為會跟預期不同；反過來、如果關掉自動延長又設了預設 10 秒、處理稍久就重投。對位的正確做法是先理解 client library 的 lease 行為、再決定 ack deadline 跟 MaxAckPending、而不是把 SQS 的 timeout 數字直接搬過去。

### maxReceiveCount / redrive → dead-letter topic

兩端都用「重試 N 次仍失敗就隔離」防止 poison message 阻塞 pipeline、但隔離後的容器不同。SQS 的 DLQ 是另一條 *queue*、用 maxReceiveCount 控制門檻、修好下游後用 redrive policy 把訊息放回原 queue。Pub/Sub 的 dead-letter topic 是另一個 *topic*、用 subscription 的 max delivery attempt 控制門檻、超過就 publish 到 DLT。

差別在重處理路徑。SQS redrive 是把 DLQ 訊息搬回 main queue、是一個 queue-to-queue 的搬移動作。Pub/Sub 的 DLT 是 topic、要重處理得在 DLT 上再開一個 subscription 來消費、沒有內建的「放回原 topic」按鈕。[Mercari item feed 的案例](/backend/03-message-queue/cases/pubsub-mercari-item-feed-dlt/)就是用 DLT 把重試多次仍失敗的訊息隔離、讓後續訊息優先處理、同時把 topic 當突發流量的 load-leveling buffer。從 SQS 搬過來時、redrive 的心智模型要換成「DLT 是一個獨立 topic、重處理是另開 subscription」、不是「按一個按鈕放回去」。設定 DLT 還需要給 Pub/Sub service account 對 DLT 的 publisher 權限跟對原 subscription 的 subscriber 權限、漏設會讓訊息卡住不進 DLT。

### Long polling → streaming pull

這一組不是等價對位、是機制不同。SQS long polling 是 consumer 發一個 ReceiveMessage 請求、最多等 20 秒、有訊息就回、沒有就空回、本質仍是 *輪詢*、只是把空輪詢的頻率降下來省 cost。Pub/Sub 的 pull 在 client library 預設是 *streaming pull*：consumer 跟 Pub/Sub 建一條長連線、訊息一到就推過來、不是 consumer 反覆問。

對位時不要把 long polling 的「WaitTimeSeconds 20 秒」翻譯成某個 Pub/Sub 參數 — 沒有對應參數、因為機制不同。要關注的是 flow control：streaming pull 因為訊息會主動推來、要用 MaxOutstandingMessages / MaxAckPending 控制同時在處理的訊息量、否則 consumer 會被一次塞太多訊息壓垮。SQS 端「一次拉最多 10 條」的批次節流、在 Pub/Sub 端變成 flow control 設定。[Spotify autoscaling 的案例](/backend/03-message-queue/cases/pubsub-spotify-autoscaling-consumers/)揭露了相關陷阱：下游失敗時 consumer 不 ack 仍持續消耗 CPU、autoscaling 反而把資源越拉越高 — autoscale 訊號要看處理成功率、不是 backlog 加 CPU。

### IAM policy → Service Account

跨雲遷移裡、身份模型是 *重對位* 而不是改語法的部分。SQS 的存取控制是 IAM policy（identity-based、掛在 user / role）加 queue policy（resource-based、掛在 queue）兩層、cross-account 靠這兩層互動。Pub/Sub 是 GCP IAM role（publisher / subscriber / viewer 等）加 Service Account、push subscription 要用 Service Account 認證到目標 endpoint。

兩套身份模型沒有自動轉換工具、要逐條重畫：誰能 publish 對應誰有 topic 的 publisher role、誰能消費對應誰有 subscription 的 subscriber role。跨雲場景還多一層 — 如果遷移期 AWS 端的服務要 publish 到 GCP 的 topic、得用 workload identity federation 或 service account key、讓 AWS 的工作負載拿到 GCP 身份。這部分沒有 case 可引、依 GCP 官方 IAM 文件加最小權限原則設計：每個 service account 只給它實際需要的 role、不要為了遷移方便給 broad role 再說以後收緊、那個「以後」通常不會來。

### CloudWatch → Cloud Monitoring

監控訊號要重建、不是改名。SQS 在 CloudWatch 看 ApproximateNumberOfMessagesVisible（queue 深度）跟 ApproximateAgeOfOldestMessage（lag）。Pub/Sub 在 Cloud Monitoring 看 num_undelivered_messages（backlog）跟 oldest_unacked_message_age（最老未確認訊息年齡）。語意相近、但 alarm 邏輯要重寫、而且 Pub/Sub 的 backlog 數字要配合 subscription 維度看 — 同一個 topic 的不同 subscription 各自有 backlog、一個堵住不代表全部堵住。遷移時要把原本對 queue 深度的告警、改成對每個 subscription 的 backlog 與 age 告警。

## 消費抽象重設計：從一條 queue 到 topic 加多 subscription

這是 components 跟 data topology 兩個高維度的核心、也是從 SQS 搬到 Pub/Sub 最需要重新畫圖的地方。SQS 的世界裡、一條 queue 對應一群競爭領取的 worker；要扇出就在前面架 SNS、SNS 後面接多條 SQS、每條 queue 各一群 worker。Pub/Sub 把這個拓樸壓平：一個 topic 收訊息、掛多少個 subscription 就有多少條獨立的消費流、每個 subscription 各自記進度、彼此不影響。

重設計從盤點現有拓樸開始。先列出：哪些是「單一 queue、一群 worker」的簡單情境、哪些是「SNS fan-out 到多條 SQS」的扇出情境。簡單情境對位乾淨 — 一個 topic、一個 pull subscription、原本競爭領取的 worker 改成同一個 subscription 的多個 consumer、Pub/Sub 自動把訊息分給它們。扇出情境要把 SNS + 多 SQS 換成「一個 topic + 多 subscription」、原本每條 SQS queue 變成一個 subscription、SNS 那一層消失。

扇出情境裡有個方向相反的陷阱要避免：不要把「多個下游」誤設計成「多個 consumer 共用一個 subscription」。同一個 subscription 的多個 consumer 是 *競爭* 關係、訊息只會給其中一個 — 那是負載分攤、不是扇出。要每個下游都收到完整一份、就要每個下游一個 *獨立* subscription。這跟 SQS 端「一條 queue 一個下游、扇出靠 SNS 複製」的直覺方向一致、但實體換了：在 SQS 是多條 queue、在 Pub/Sub 是多個 subscription。畫遷移圖時、SQS 的每條 fan-out queue 一對一映射到 Pub/Sub 的一個 subscription、不要合併。

## Application 重設計範例：SQS receive-delete 換成 Pub/Sub pull-ack

```go
// SQS 端：long polling receive、處理完 DeleteMessage
svc := sqs.NewFromConfig(cfg)
for {
    out, _ := svc.ReceiveMessage(ctx, &sqs.ReceiveMessageInput{
        QueueUrl:            &queueURL,
        MaxNumberOfMessages: 10,
        WaitTimeSeconds:     20, // long polling
    })
    for _, m := range out.Messages {
        process(m.Body)
        svc.DeleteMessage(ctx, &sqs.DeleteMessageInput{
            QueueUrl:      &queueURL,
            ReceiptHandle: m.ReceiptHandle,
        })
    }
}
```

```go
// Pub/Sub 端：streaming pull、處理完 Ack、用 flow control 節流
sub := client.Subscription("orders-sub")
sub.ReceiveSettings.MaxOutstandingMessages = 100 // flow control、取代「一次拉 10 條」
err := sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    process(msg.Data)
    msg.Ack() // 取代 DeleteMessage；client library 在背景自動延長 ack deadline
})
```

差異：

- SQS 主動輪詢（ReceiveMessage 迴圈）→ Pub/Sub 回呼模型（Receive 把訊息推進 callback）
- SQS DeleteMessage → Pub/Sub msg.Ack()、語意都是「確認處理完、別重投」
- SQS WaitTimeSeconds 控制輪詢等待 → Pub/Sub MaxOutstandingMessages 控制 flow control
- SQS 一次最多 10 條的批次上限 → Pub/Sub 沒有這個上限、改用 flow control 設同時在途量
- ack deadline 的延長在 SQS 要主動 ChangeMessageVisibility、在 Pub/Sub 由 client library 自動處理

application 邏輯的商業處理部分（process 函式）多數可保留、改動集中在收訊息的框架跟確認語意、估計 20-40% 程式碼。

## Production 故障演練

### Case 1：fan-out 設計成共用 subscription、下游各收到一部分

**徵兆**：把原本 SNS fan-out 到 3 條 SQS 的拓樸搬到 Pub/Sub、為了省事建一個 topic + 一個 subscription、讓 3 個下游服務都連這個 subscription。上線後發現每個下游只收到大約三分之一的訊息、不是各收完整一份。

**根因**：同一個 subscription 的多個 consumer 是負載分攤關係、Pub/Sub 把訊息分給其中一個 consumer、不是每個都送。這對應到 SQS 端「一條 queue 多個 worker 競爭領取」的行為、但被誤用在需要扇出的場景。SQS 端的扇出靠 SNS 複製訊息到多條 queue、那個複製動作在 Pub/Sub 應該由「多個 subscription」承擔、不是多個 consumer 共用一個 subscription。

**修法**：

1. **每個下游一個獨立 subscription**：3 個下游就建 3 個 subscription 掛同一個 topic、每個各收完整一份
2. **遷移圖一對一映射**：SQS 的每條 fan-out queue 對應一個 Pub/Sub subscription、不合併
3. **負載分攤跟扇出分開設計**：同一下游要多 worker 分攤、是同一 subscription 多 consumer；不同下游各收一份、是多 subscription

### Case 2：ack deadline 沿用 SQS 數字太短、長任務反覆重投

**徵兆**：SQS 端 visibility timeout 設 5 分鐘跑得好好的、搬到 Pub/Sub 隨手把 ack deadline 設成預設或一個小數字、結果處理時間稍長的訊息被反覆重投、同一筆訊息處理多次、下游出現重複副作用。

**根因**：Pub/Sub ack deadline 預設 10 秒、上限 600 秒、跟 SQS visibility timeout 上限 12 小時差很多。如果關掉 client library 的自動 lease extension、又把 ack deadline 設小、處理時間一超過就被判定失敗重投。SQS 的「設一個夠長的 timeout」直覺搬過來不適用、因為 Pub/Sub 的上限低很多、且延長機制是 client library 自動做。

**修法**：

1. **理解 client library 的 lease 行為**：多數 client library 預設會背景自動延長 ack deadline 到處理完、優先依賴這個而不是手動設超長 deadline
2. **長任務拆短或改架構**：單筆處理超過 10 分鐘上限的、考慮拆成多階段或把長任務移出訊息處理路徑
3. **下游做 idempotency**：跟 SQS 一樣、Pub/Sub 是 at-least-once、重投本來就會發生、下游用 message ID 去重才是根本解

### Case 3：FIFO 順序需求對位到 ordering key、吞吐落差超出預期

**徵兆**：原系統用 SQS FIFO queue + MessageGroupId 保證同一群訊息順序處理、搬到 Pub/Sub 啟用 ordering key 對位、上線後吞吐比預期低很多、且某些情境順序仍亂。

**根因**：SQS FIFO 跟 Pub/Sub ordering key 都提供順序、但取捨點不同。SQS FIFO 同時給「順序」跟「5 分鐘去重窗口」、吞吐受限（每 MessageGroupId 串行）。Pub/Sub ordering key 給「同一 key 的訊息按 publish 順序送達」、但要 publish 端跟 subscription 端都正確設定（publish 要設 ordering key、subscription 要 enableMessageOrdering）、漏一邊順序就不保證；而且啟用 ordering 後同一 key 串行、吞吐同樣受限。把 FIFO 的「去重 + 順序」一包功能、誤以為 ordering key 也一包提供、是落差來源。

**修法**：

1. **拆開「順序」跟「去重」兩個需求**：Pub/Sub ordering key 只管順序、去重要 application 端自己用 message ID 做
2. **publish 跟 subscription 兩端都設 ordering**：缺一邊順序不保證、遷移檢查清單要把兩端都列上
3. **重新評估是否真需要全域順序**：FIFO 常被過度使用、很多場景只需要 per-entity 順序、用 ordering key 按 entity 分 key、比強制全域串行吞吐高很多

### Case 4：跨雲遷移期雙雲都在跑、egress 成本與延遲被低估

**徵兆**：漸進 cutover 期間 AWS 跟 GCP 兩邊都在處理訊息、為了[對帳](/backend/knowledge-cards/data-reconciliation/)把訊息在兩雲之間搬、月底帳單跨雲 egress 費用遠超預估、且跨雲呼叫的尾延遲拖慢端到端處理。

**根因**：SQS 在 AWS region 內、Pub/Sub 在 GCP、遷移期的 dual publish 或對帳如果讓資料反覆跨雲、每一筆出 AWS 的訊息都計 egress 費。跨雲不只是錢、跨雲網路的延遲跟抖動比同雲高、放在同步處理路徑上會放大尾延遲。同雲 vendor 切換沒有這個維度、跨雲遷移必須把它列進成本模型。

**修法**：

1. **縮短雙雲並行窗口**：dual publish 的對帳期越短越省、設明確的並行截止日、不要無限期雙跑
2. **對帳用抽樣不用全量搬運**：驗證一致性用抽樣比對 message ID / count、不要把所有訊息都搬到對面雲比對
3. **生產者就近落點**：遷移後讓 producer 直接 publish 到 Pub/Sub、不要繞 AWS 再跨雲、消除穩態的跨雲 egress

### Case 5：dead-letter topic 權限沒配齊、毒訊息卡住不進 DLT

**徵兆**：subscription 設了 dead-letter topic 跟 max delivery attempt、預期重試超限的訊息進 DLT、實際上毒訊息一直在原 subscription 反覆重投、DLT 是空的、後續訊息被堵。

**根因**：Pub/Sub 要把訊息送進 DLT、是由 Pub/Sub 的 service account 代為 publish 到 DLT topic；同時它也要對原 subscription 有 subscriber 權限才能 ack 掉原訊息。這兩個權限漏任一個、forwarding 到 DLT 就失敗、訊息卡在原 subscription。SQS 端 DLQ 是 queue 屬性、不需要額外給 service 權限、所以這個跨雲差異容易被漏掉。

**修法**：

1. **配齊 DLT 雙權限**：給 Pub/Sub service account 對 DLT topic 的 publisher role、跟對原 subscription 的 subscriber role
2. **遷移後做毒訊息演練**：故意 publish 一筆會失敗的訊息、確認它真的在 max attempt 後進 DLT、不是卡在原 subscription
3. **監控 DLT backlog**：DLT 開一個 subscription 監控其 num_undelivered_messages、確認毒訊息有被導流且有人處理、對照 [Mercari DLT 案例](/backend/03-message-queue/cases/pubsub-mercari-item-feed-dlt/)的設計

## 漸進 cutover：dual publish 加雙消費對帳

跨雲遷移風險高、不適合一次切換、走漸進 cutover 把可逆邊界拉長：

1. **Phase 0：拓樸盤點** — 列出所有 SQS queue、標記哪些是單一 queue、哪些是 SNS fan-out、各自映射到 Pub/Sub 的 topic / subscription 結構
2. **Phase 1：Pub/Sub 端建好對位資源** — 建 topic / subscription / DLT、配齊 IAM 與 service account、重建 Cloud Monitoring 告警、application 寫好 Pub/Sub consumer 但先不收流量
3. **Phase 2：dual publish** — producer 同時 publish 到 SQS 跟 Pub/Sub、兩邊 consumer 都跑、Pub/Sub 端的處理結果先寫到隔離區或標記、不影響正式下游
4. **Phase 3：雙消費對帳** — 抽樣比對兩邊處理的訊息 ID 與數量、確認 Pub/Sub 端沒漏、沒重複到無法接受的程度、ack deadline / fan-out / ordering 行為都符合預期
5. **Phase 4：流量切換** — 對帳通過後、把正式下游切到 Pub/Sub 端、SQS 端轉成備援、保留一段觀察期可回切
6. **Phase 5：下線 SQS** — 觀察期穩定後停掉 dual publish、移除 SQS 資源、消除穩態跨雲 egress（這是不可逆階段、不要在對帳沒過時提前做）

對帳期是這套流程的核心保險、也是 Case 4 跨雲成本的來源 — 對帳用抽樣、並行窗口設明確截止日、平衡「驗證信心」跟「雙雲成本」。

## Capacity / cost 對照

| 維度        | AWS SQS                                      | Google Pub/Sub                                           |
| ----------- | -------------------------------------------- | -------------------------------------------------------- |
| 計費模型    | 每百萬 request（含 send / receive / delete） | 按 throughput（publish + subscribe 的資料量計費）        |
| Region 模型 | Region-scoped、跨 region 自己處理            | Global topic、無 region 概念                             |
| 扇出成本    | SNS + 多 SQS、每條 queue 各計費              | 一個 topic 多 subscription、按各 subscription throughput |
| 訊息保留    | 預設 4 天、上限 14 天                        | 預設 7 天、可調                                          |
| 順序成本    | FIFO queue 比 standard 貴                    | ordering key 啟用後吞吐受限、計費同 standard             |
| 跨雲 egress | 出 AWS 計 egress                             | 出 GCP 計 egress；穩態應讓 producer 就近 publish         |
| 監控        | CloudWatch（隨用量計費）                     | Cloud Monitoring                                         |

**判讀**：穩態成本兩者量級相近、真正的成本差在 *遷移期* — dual publish 雙雲並行加跨雲對帳搬運是一次性高峰、不是穩態。把這段窗口縮短、是控制跨雲遷移成本的關鍵、不是去比 SQS 跟 Pub/Sub 的單價。扇出重度的系統遷到 Pub/Sub 後、少掉 SNS 那一層、扇出的計費結構也變簡單。

## 整合 / 下一步

### 遷移後事件可直接落 GCP 資料平台

遷到 Pub/Sub 的一個結構性好處、是事件可以用 BigQuery subscription 直接寫進 BigQuery、不需要再寫 Dataflow pipeline 搬運；或用 Cloud Storage subscription 批次落 GCS。這正是「workload 重心在 GCP」這條 driver 的回報 — 事件層跟資料平台同雲、省掉跨雲搬運。這也是評估是否該跨雲遷移時、要放進 ROI 的一邊。

### 跟 Kafka 遷移的結構對照

| 篇                                                                            | 主導差異維度                                   | 結構                              |
| ----------------------------------------------------------------------------- | ---------------------------------------------- | --------------------------------- |
| [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) | Paradigm（高）                                 | partial + 長期混合                |
| SQS → Pub/Sub（本篇）                                                         | Operational（高）+ components / topology（高） | operational hybrid + 高維度獨立段 |

**結論**：SQS → Pub/Sub 不是 paradigm shift（兩端都是 cloud-managed 訊息服務、可收斂成單一目標）、是 operational redesign 為主、消費抽象重設計為輔的跨雲遷移；結構由主導差異維度（operational）決定主軸、高維度（components / topology）抽獨立段補充。

## 相關連結

- Source / target vendor：[AWS SQS](/backend/03-message-queue/vendors/aws-sqs/) / [Google Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/)
- 平行 vendor：[Kafka](/backend/03-message-queue/vendors/kafka/) / [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) / [NATS](/backend/03-message-queue/vendors/nats/)
- 平行 migration playbook：[Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/)
- 引用案例：[3.C64 Mercari Item Feed DLT](/backend/03-message-queue/cases/pubsub-mercari-item-feed-dlt/) / [3.C61 Spotify autoscaling](/backend/03-message-queue/cases/pubsub-spotify-autoscaling-consumers/)
- Methodology：[Migration Playbook 寫作方法論](/posts/migration-playbook-methodology/)
- 上游概念：[0.3 非同步選型](/backend/00-service-selection/async-delivery-selection/) / [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)
