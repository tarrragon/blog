---
title: "RabbitMQ → AWS SQS：交出 broker 維運、把 routing 收斂進 application"
date: 2026-06-16
description: "自管 RabbitMQ 叢集遷到 AWS SQS 是 operational redesign：protocol 不相容、application 要從 manual ack 改成 visibility timeout + delete、exchange routing 收斂成 SNS fan-out 或多 queue；本文跑 6 維 diff dimension audit（operational 差最大）、釐清什麼該遷什麼不該遷、5 個 production 故障演練（DLX → redrive policy / prefetch → batch + visibility / fan-out → SNS-to-SQS / 256KB 大小限制 / ordering 到 FIFO 的吞吐取捨）跟漸進 cutover"
weight: 12
tags: ["backend", "message-queue", "rabbitmq", "aws-sqs", "migration", "managed"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) 跟 [AWS SQS](/backend/03-message-queue/vendors/aws-sqs/)。對照 [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) 的 paradigm shift、本篇主導差異維度是 *operational model*：source 跟 target 都是任務隊列、能力大致對得上、但運維責任從「自管 broker 叢集」整批交給 AWS managed 服務。

RabbitMQ → AWS SQS 的核心是把 broker 運維責任轉移給 managed 服務、同時接受 SQS 沒有 exchange routing 這個事實、把路由邏輯收斂回 application 或改用 SNS fan-out。這個遷移不是 protocol drop-in（AMQP client 不能直接連 SQS）、application 端需要改 delivery 控制機制（manual ack → visibility timeout + delete）；但它也不是 paradigm shift（兩端都是 at-least-once 任務隊列、DLQ / 重試 / 解耦的語意一致）。主導差異落在 operational 維度、所以本文走 Type C operational redesign hybrid 結構。

## 為什麼遷：不想再養 RabbitMQ 叢集

觸發評估 SQS 的最常見壓力是 broker 維運成本、不是功能缺口。自管 RabbitMQ 叢集要承擔的運維責任包含 Erlang cluster 拓樸維護、network partition（腦裂）處理、quorum queue 的 Raft 一致性調校、disk / memory alarm 的容量規劃、版本升級的 rolling restart。這些責任需要至少 0.5-1 FTE 的持續投入、且在 [network partition](/backend/03-message-queue/vendors/rabbitmq/) 這類事故發生時需要熟悉 Erlang runtime 的人即時介入。

SQS 把這整層責任移除。沒有 broker 實例、沒有 cluster 拓樸、沒有 disk / memory watermark、沒有版本升級。換來的代價是 routing 能力消失（SQS 沒有 exchange）、application 要改 delivery 控制機制、以及 AWS 生態綁定。這個交換在三種情境下成立：

第一種是 AWS 生態原生服務。若 producer / consumer 已經跑在 Lambda、ECS、EKS 上、SQS 的 event source mapping 跟 IAM 整合讓 application 不必自管連線池跟認證。RabbitMQ 在 AWS 上要嘛自管 EC2 叢集、要嘛用 Amazon MQ（仍是 broker 模型、運維責任只是部分轉移）、都不如 SQS 的 serverless 整合直接。

第二種是 routing 邏輯本來就簡單。若 RabbitMQ 的用法是 direct exchange + 少數固定 routing key、或單純 worker pool 消費單一 queue、那 exchange 的靈活性本來就沒被用到、遷到 SQS 不損失能力。Airbnb 的 Dynein 分散式延遲任務系統就是這個形狀：用 SQS at-least-once + DLQ 取代原本受限於單 Redis 的 Resque、每 scheduler instance 達約 1000 QPS、水平擴展（見 [3.C48 Airbnb Dynein](/backend/03-message-queue/cases/sqs-airbnb-dynein-delayed-jobs/)）。任務排程對「不丟資料」的需求 at-least-once 足夠、不需要 broker 級 routing。

第三種是團隊規模不支撐 broker 專業。小團隊養一套 RabbitMQ 叢集、真正用到的是「可靠的任務隊列 + DLQ」、但要付出整套 Erlang 運維學習曲線。把這層交給 SQS、團隊把精力放回 application 邏輯。

## 6 維 diff dimension audit

遷移前先跑 [diff dimension audit](/posts/migration-playbook-methodology/)、對每個維度評估 source 跟 target 的差異程度、決定主導維度跟結構：

| 維度                   | RabbitMQ（self-managed）                 | AWS SQS（managed）                      | 差異 |
| ---------------------- | ---------------------------------------- | --------------------------------------- | ---- |
| Schema / API           | AMQP 0-9-1 協議、exchange / queue        | HTTP API、SendMessage / ReceiveMessage  | 中   |
| Operational model      | 自管 Erlang 叢集、cluster / disk / 升級  | Fully managed、無實例、無版本           | 高   |
| Abstraction / paradigm | 任務隊列 + 重試 + DLQ                    | 任務隊列 + 重試 + DLQ                   | 低   |
| Components（1 vs N）   | broker 一站式（routing 內建）            | SQS + 需要 SNS 補 fan-out routing       | 中   |
| Application change     | manual ack / nack、prefetch、AMQP client | visibility timeout + delete、batch、SDK | 中高 |
| Data topology          | 單叢集 / federation 拓樸                 | region-scoped queue、無拓樸概念         | 低   |

**主導維度是 operational（高）**：遷移的核心價值跟核心風險都在「broker 運維責任整批轉移」。Application change 維度評中高、因為 delivery 控制機制要改、但這是受控的 SDK 層改寫、不是 paradigm 重設計。Components 維度評中、因為 exchange routing 在 SQS 沒有對等物、要靠 SNS fan-out 或多 queue 補回來。其餘三維度低或中。

主導維度落在 operational、所以主結構走 Type C：以 operational redesign 對位開頭、phased 執行、故障演練聚焦在「以為對等其實不對等」的運維陷阱。Application change 跟 Components 兩個次高維度不硬塞進主結構、各自抽出獨立段（下面「application 改寫」跟「routing 收斂」兩段）。

### Operational redesign 對位

Operational 維度差異最大、先逐項對位「原本自己做的事、現在誰做、怎麼做」：

| 運維責任      | RabbitMQ（自己做）                       | SQS（managed / application）            |
| ------------- | ---------------------------------------- | --------------------------------------- |
| 高可用        | quorum queue + cluster + partition 處理  | AWS 跨 AZ 自動冗餘、無需配置            |
| 容量規劃      | disk / memory watermark、queue length 限 | 自動擴展、無實例容量概念                |
| 版本升級      | rolling restart、相容性驗證              | 無、AWS 維護                            |
| 監控          | Management UI + Prometheus exporter      | CloudWatch metric（depth / age）        |
| Delivery 控制 | broker-side ack / nack 狀態機            | client-side visibility timeout + delete |
| 重試 / DLQ    | DLX + dead-letter routing key            | redrive policy + maxReceiveCount        |
| Routing       | exchange + binding（broker 內建）        | application 或 SNS（broker 外）         |

前四列是純收益：責任消失、不需要對等實作。後三列是責任轉移、不是消失 — delivery 控制從 broker 移到 client、重試從 DLX 移到 redrive policy、routing 從 broker 移到 application。這三列正是故障演練聚焦的地方、因為「以為功能還在、其實機制換了」是這類遷移的主要事故來源。

監控這列值得展開。RabbitMQ 的 queue depth、unacked、consumer 數量是從 broker 直接讀；SQS 改看 CloudWatch 的 `ApproximateNumberOfMessagesVisible`（queue depth）跟 `ApproximateAgeOfOldestMessage`（lag 訊號）。差異在於 SQS 的 metric 是 approximate、且有分鐘級延遲、不適合用來做秒級的 backpressure 決策。原本靠 RabbitMQ Management UI 即時看 queue 狀態的 runbook 要改寫成 CloudWatch alarm 驅動。

## Application 改寫：manual ack → visibility timeout + delete

Application change 維度的核心是 delivery 控制機制換了一套模型。RabbitMQ 是 broker-side 維護訊息狀態、consumer 用 [ack/nack](/backend/knowledge-cards/ack-nack/) 回報處理結果；SQS 是 client-side 用 [visibility timeout](/backend/knowledge-cards/in-flight/) + 顯式 delete、broker 不維護「處理中」以外的狀態。

```python
# RabbitMQ 端：manual ack pattern
channel.basic_qos(prefetch_count=10)  # 一次最多領 10 條未 ack

def callback(ch, method, properties, body):
    try:
        process(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        # nack + requeue，或丟 DLX
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

channel.basic_consume(queue="orders", on_message_callback=callback)
channel.start_consuming()
```

```python
# SQS 端：visibility timeout + delete pattern
while True:
    resp = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,        # batch、對應 prefetch
        WaitTimeSeconds=20,            # long polling
        VisibilityTimeout=60,          # 處理中對其他 consumer 隱藏
    )
    for msg in resp.get("Messages", []):
        try:
            process(msg["Body"])
            sqs.delete_message(           # 顯式 delete = ack
                QueueUrl=queue_url,
                ReceiptHandle=msg["ReceiptHandle"],
            )
        except Exception:
            pass  # 不 delete、visibility timeout 後自動回 queue 重試
```

對應關係：

- RabbitMQ `basic_ack` → SQS `delete_message`：處理成功的訊息要顯式刪除、否則 visibility timeout 後重新可見。「不做事」在 SQS 等於「重試」、在 RabbitMQ 等於「卡住 unacked」。
- RabbitMQ `prefetch_count` → SQS `MaxNumberOfMessages`（上限 10）+ visibility timeout：併發控制從「broker 限制未 ack 數量」變成「一次 receive 的 batch 大小 + 隱藏時間窗」。
- RabbitMQ `basic_nack(requeue=False)`（丟 DLX）→ SQS redrive policy：失敗不再是 application 主動丟 DLX、而是「達到 maxReceiveCount 次數後 SQS 自動送 DLQ」。
- RabbitMQ push 模型（broker 主動推給 consumer）→ SQS pull 模型（consumer 主動 long polling）：consumer loop 結構不同、SQS 沒有 broker 主動推送、要嘛自己 poll、要嘛交給 Lambda event source mapping 代 poll。

application 邏輯改動集中在 consumer 的 receive / ack / 重試三段、producer 端從 `basic_publish` 改成 `send_message` 相對單純。整體改動量取決於原本用了多少 AMQP 特性、典型情境是 consumer 端 20-40% 改寫。

## Routing 收斂：exchange 沒了、靠 SNS fan-out 或多 queue

Components 維度的核心是 SQS 沒有 exchange、RabbitMQ 的 routing 能力要在 broker 外重建。RabbitMQ 的 [exchange](/backend/knowledge-cards/broker/) 在 broker 內承擔分流：一條訊息經 routing key 跟 binding 決定進哪些 queue。SQS 是裸 queue、producer 直接指定 queue、沒有中間分流層。

| RabbitMQ routing 模式  | SQS 對應方案                                           |
| ---------------------- | ------------------------------------------------------ |
| Direct（固定 key）     | 直接 send 到對應 queue、routing 收斂進 producer 程式碼 |
| Fanout（廣播）         | SNS topic → 多個 SQS queue 訂閱（SNS-to-SQS fan-out）  |
| Topic（層級 key 匹配） | SNS + message filtering（subscription filter policy）  |
| Headers                | SNS message attribute filtering                        |

判讀：

- **Direct exchange + 少數固定 key**：最容易遷。routing 邏輯本來就是「key X 進 queue X」、改成 producer 直接 `send_message` 到對應 queue url。routing 從 broker 收斂進 application、程式碼多幾行 if/else 或 map 查表。
- **Fanout（一條訊息給多個 downstream）**：用 SNS-to-SQS。SNS topic 當 fan-out 點、每個 downstream 訂閱一個自己的 SQS queue。Twitch EventSub 就是這個形狀（見 [3.C54 Twitch EventSub](/backend/03-message-queue/cases/sqs-twitch-eventsub-fanout/)）：SNS fan-out 到多個 SQS、各 consumer 獨立消費。這比 RabbitMQ fanout exchange 多一層 SNS、但換來 managed 運維。
- **Topic exchange（複雜層級匹配）**：SNS 的 subscription filter policy 能做 attribute-based 過濾、但表達力不如 AMQP topic 的 `*` / `#` 通配。複雜 topic routing 是「不該遷」的訊號（見下節）。

關鍵取捨：SQS + SNS 把 RabbitMQ 的單一 broker（routing 內建）拆成兩個 managed 服務（SQS 排隊 + SNS 分流）。好處是各自 managed、壞處是 routing 從宣告式 binding 變成要管 SNS topic + subscription + filter policy 的組合、跨服務除錯多一層。

## 什麼不該遷：保留 RabbitMQ 的訊號

SQS 的 managed 簡潔有代價、三類用法遷過去會損失能力或增加複雜度：

**複雜 topic routing**。若 RabbitMQ 重度使用 topic exchange 的 `*` / `#` 層級通配、binding 規則數十條、那 routing 的表達力是核心價值。SNS subscription filter 的 attribute 匹配做不到對等表達、勉強遷會把 broker 內的宣告式 routing 拆成散落在 SNS filter policy + application 程式碼的命令式邏輯、維護成本反而上升。GoCardless 用單一 topic exchange 當服務 mesh（見 [3.C26 GoCardless Hutch](/backend/03-message-queue/cases/rabbitmq-gocardless-hutch-service-mesh/)）這類設計、routing 就是架構本身、不該拆。

**需要 broker 級 ordering**。RabbitMQ 單 queue 預設 FIFO、consistent hash exchange 還能做 per-key ordering（見 [3.C28 WeWork hash ordering](/backend/03-message-queue/cases/rabbitmq-wework-consistent-hash-ordering/)）。SQS standard queue *無 ordering*；要 ordering 只能用 FIFO queue、而 FIFO 吞吐受限（每 MessageGroupId 有序、整體 3000 msg/sec with batching）。若 workload 同時要高吞吐跟嚴格 ordering、SQS FIFO 兩者不可兼得、RabbitMQ 反而更適合。

**RPC over messaging（request-reply）**。RabbitMQ 的 reply-to + correlation-id 做同步 RPC 模式、SQS 沒有原生 request-reply、要自己用兩條 queue + correlation 拼、延遲也不適合（SQS 是 task queue 不是低延遲傳輸）。這類用法該考慮 [NATS](/backend/03-message-queue/vendors/nats/) 的 request-reply 或直接 HTTP。

## Migration 結構：漸進 cutover

operational redesign 的 cutover 走 dual-run、按 queue（不是按整個叢集）漸進切、每步都保留回退邊界：

1. **Phase 0：scope 盤點** — 列出所有 exchange / queue / binding、標註 routing 模式（direct / fanout / topic）跟 ordering 需求。判斷哪些 queue 適合遷（簡單 routing、at-least-once 夠用）、哪些保留（複雜 topic、需 broker ordering、RPC）。
2. **Phase 1：SQS / SNS 基礎建設** — 對適合遷的 queue 建對應 SQS queue + DLQ（設 redrive policy + maxReceiveCount）、fanout 場景建 SNS topic + subscription。設好 IAM policy、visibility timeout 對齊 consumer 最大處理時間。
3. **Phase 2：consumer 改寫 + dual-consume** — application consumer 改成 SQS pull 模型（或 Lambda event source）、先讓新 consumer 跟舊 RabbitMQ consumer *並存*、producer 暫時雙寫到 RabbitMQ + SQS、驗證 SQS 端處理正確。
4. **Phase 3：producer cutover** — 逐 queue 把 producer 從 RabbitMQ 切到 SQS / SNS、停掉該 queue 的雙寫。這步可逆：發現問題切回 RabbitMQ producer 即可。
5. **Phase 4：下線 RabbitMQ queue** — 確認某 queue 在 SQS 穩定運行、且 RabbitMQ 端該 queue 已排空、才停掉 RabbitMQ 對應的 exchange / queue。這是不可逆步驟、不該過早。
6. **Phase 5：叢集退役** — 所有適合遷的 queue 都切完、RabbitMQ 只剩保留的複雜 routing queue（或完全清空）、才縮編或退役叢集。

漸進 cutover 的關鍵是 *按 queue 切、不按叢集切*。每條 queue 是獨立的遷移單元、各自走 Phase 2-4、互不阻塞。複雜 routing 的 queue 可以永遠留在 RabbitMQ、形成 RabbitMQ + SQS 長期共存的混合架構。

## Production 故障演練

### Case 1：DLX 改 redrive policy，重試語意不對等

**徵兆**：RabbitMQ 端用 DLX 配 message TTL 做「延遲重試 + 多層 escalation」（如 [3.C25 Indeed Delay + DLQ](/backend/03-message-queue/cases/rabbitmq-indeed-delay-dlq-escalation/) 的三層 retry）；遷到 SQS 後發現 redrive policy 只能設「失敗 N 次直接進 DLQ」、做不出原本的延遲重試階梯。

**根因**：RabbitMQ DLX 是 routing 機制、能配 TTL + 多個中繼 queue 組出任意 escalation 拓樸；SQS redrive policy 是單一規則（maxReceiveCount 到了就送 DLQ）、沒有中繼層。兩者都叫「DLQ」、但 RabbitMQ 的是可編程 routing、SQS 的是固定計數。

**修法**：

1. **指數退避用 visibility timeout 做**：失敗時 application 主動 `ChangeMessageVisibility` 延長隱藏時間、實現退避、而不是依賴 DLX TTL。
2. **多層 escalation 用多 queue 串**：若真需要 N 層、建 N 個 SQS queue、application 失敗時把訊息 send 到下一層 queue、每層設不同 redrive policy。複雜度比 DLX 高、是「複雜 routing 不該遷」的訊號之一。
3. **接受簡化**：多數 task queue 的重試需求是「重試幾次後進 DLQ 人工檢視」、SQS redrive policy 直接對應、不需要重建 escalation 階梯。

### Case 2：prefetch 改 batch + visibility，併發控制行為變了

**徵兆**：RabbitMQ 端 `prefetch_count=1` 確保 worker 一次只處理一條（公平派發、慢任務不囤積）；遷 SQS 後 consumer 一次 `receive_message` 領 10 條、其中一條慢任務拖累整批、且 visibility timeout 對整批同時計時、處理到一半超時導致前面已處理的訊息重複。

**根因**：RabbitMQ prefetch 是 per-message 的未 ack 上限、broker 逐條控制；SQS 的 batch 是一次領多條、visibility timeout 對 batch 內每條*獨立*計時、但 application 若同步處理整批、慢的那條會讓後面的訊息在處理前就接近超時。

**修法**：

1. **慢任務用 batch size 1**：對等 RabbitMQ `prefetch=1` 就設 `MaxNumberOfMessages=1`、一次領一條、避免批內互相拖累。
2. **visibility timeout 設成略高於最大處理時間**：Capital One 的 SQS + Lambda 實務明示這點（見 [3.C50 Capital One](/backend/03-message-queue/cases/sqs-capital-one-visibility-timeout/)）— timeout 太短重複處理、太長延遲 retry。長任務處理中主動 `ChangeMessageVisibility` 續期。
3. **逐條 delete 不等整批**：每條處理完立刻 `delete_message`、不要等整批做完才一起刪、降低整批超時導致部分重複的風險。

### Case 3：fanout 改 SNS-to-SQS，漏訂閱導致部分 downstream 收不到

**徵兆**：RabbitMQ fanout exchange 廣播到所有 binding queue、新增 downstream 只要 bind 上去就收得到；遷成 SNS-to-SQS 後、某個新 downstream 的 SQS queue 沒訂閱到 SNS topic、或 subscription filter policy 設錯、導致該 downstream 靜默漏訊息。

**根因**：RabbitMQ fanout 的廣播是 broker 內建語意、binding 一建立就生效；SNS-to-SQS 的 fan-out 是「每個 downstream 各自建 SQS queue + 訂閱 SNS topic + 設 queue policy 允許 SNS 投遞」三步、任一步漏掉或 filter policy 寫錯就靜默漏。多一層服務 = 多一層配置出錯點。

**修法**：

1. **訂閱關係 IaC 管理**：SNS subscription + SQS queue policy 用 Terraform / CloudFormation 宣告、避免手動建漏。
2. **驗證 fan-out 完整性**：cutover 前發測試訊息、確認*每個* downstream queue 都收到（對照 RabbitMQ 端 binding 清單逐一核對）。
3. **filter policy 預設寬鬆**：除非明確要過濾、subscription 不設 filter policy（全收）、避免「以為廣播、實際被 filter 擋掉」。

### Case 4：訊息超過 256KB，SQS 拒收

**徵兆**：RabbitMQ 對單訊息大小無硬性低上限（受 frame_max / memory 限制、實務常見 MB 級 payload）；遷 SQS 後、原本能傳的大 payload 訊息被拒、SendMessage 報 message 超過 256KB 上限。

**根因**：SQS 單訊息上限 256KB（含 message attribute）。RabbitMQ 沒有這個低上限、application 可能習慣直接把大 payload（如完整文件、序列化大物件）塞進訊息體。

**修法**：

1. **Claim-check pattern**：大 payload 存 S3、訊息只放 S3 物件的引用（key / presigned URL）、consumer 收到後從 S3 取。FINRA 的大檔案處理就是 S3 → SQS 模式（見 [3.C53 FINRA Large File](/backend/03-message-queue/cases/sqs-finra-large-file-service/)）。
2. **SQS Extended Client Library**：AWS 官方 library 自動把超過上限的 payload 透明存 S3、訊息存指標、consumer 端自動取回、application 程式碼幾乎不改。
3. **盤點 payload 大小分佈**：Phase 0 audit 時量測現有訊息大小、超 256KB 的比例決定是否需要 claim-check、避免 cutover 後才發現大量訊息被拒。

### Case 5：ordering 從 RabbitMQ 到 SQS FIFO，吞吐撞天花板

**徵兆**：RabbitMQ 單 queue 提供順序消費、原本靠這個保證同一筆訂單的事件有序處理；遷 SQS standard queue 後 ordering 消失、改用 SQS FIFO queue 恢復 ordering、但吞吐從原本的數萬 msg/sec 掉到 3000 msg/sec 上限、隊列堆積。

**根因**：SQS standard queue 無 ordering（為了吞吐跟可用性的設計取捨）；FIFO queue 提供 per-MessageGroupId 有序 + 去重、但整體吞吐上限 3000 msg/sec（with batching）。RabbitMQ 單 queue 的有序消費吞吐遠高於此。Twilio 的 webhook buffer 就遇到 FIFO 300 TPS（不 batch）/ 3000 TPS（batch）的限制（見 [3.C58 Twilio webhook](/backend/03-message-queue/cases/sqs-twilio-webhook-buffer/)）。

**修法**：

1. **重新審視 ordering 粒度**：用 MessageGroupId 把 ordering 限縮到真正需要的範圍（如 per-訂單、per-用戶）、不同 group 平行處理、整體吞吐 = group 數 × per-group 吞吐、繞過單 queue 3000 上限。
2. **拆分 ordered 跟 unordered 流量**：只有真需要 ordering 的訊息走 FIFO、其餘走 standard queue 拿高吞吐。多數 workload 只有一小部分需要嚴格 ordering。
3. **ordering 是「不該遷」的硬訊號**：若 workload 整體都需要高吞吐 + 嚴格 ordering、SQS FIFO 兩者不可兼得、保留 RabbitMQ 或考慮 [Kafka](/backend/03-message-queue/vendors/kafka/)（per-partition ordering + 高吞吐）。

## Capacity / cost 對照

| 維度          | RabbitMQ（self-managed EC2）           | AWS SQS（managed）                            |
| ------------- | -------------------------------------- | --------------------------------------------- |
| 叢集 baseline | 3 broker（HA）+ EBS                    | 無實例                                        |
| 運維 FTE      | 0.5-1 FTE                              | ~0.1 FTE（IAM / alarm 配置）                  |
| 計費模型      | EC2 instance hour + EBS + 流量         | per-request（每百萬 request）+ 跨 region 流量 |
| 吞吐上限      | 受 broker 規格 / 網路限制              | standard 近乎無限、FIFO 3000 msg/sec          |
| Ordering      | 單 queue 有序、consistent hash per-key | standard 無、FIFO per-group                   |
| Routing       | broker 內建 exchange                   | 無（需 SNS / application）                    |
| 訊息大小上限  | 受 frame_max / memory（MB 級可行）     | 256KB（超過用 S3 claim-check）                |
| 監控延遲      | 即時（Management UI）                  | CloudWatch approximate、分鐘級                |

**判讀**：低到中吞吐、簡單 routing、AWS 生態的 task queue、SQS 在運維成本上顯著划算（FTE 從 0.5-1 降到約 0.1）。高吞吐 + 嚴格 ordering、或重度 exchange routing 的 workload、SQS 的 per-request 成本跟能力限制可能讓 RabbitMQ（或 Kafka）反而合適。SQS 的 cost 是用量驅動、流量大時 per-request 費用要納入評估、對照 [0.6 成本取捨](/backend/00-service-selection/cost-risk-tradeoffs/)。

## 整合 / 下一步

### 混合架構是常見終態

多數遷移不會把 RabbitMQ 完全清空。簡單 task queue 遷 SQS、複雜 topic routing / broker ordering / RPC 留 RabbitMQ、形成長期共存：

```text
[簡單 task queue / fanout]              [複雜 topic routing / RPC / ordering]
        AWS SQS / SNS                              RabbitMQ
        │                                            │
   Lambda / ECS consumer                    自管叢集（縮編後）
```

按 queue 漸進切的結果就是混合架構 — 不需要為了「遷乾淨」勉強把不適合的 queue 也搬過去。

### 跟 RabbitMQ → Kafka 的對照

RabbitMQ 還有另一條遷移路徑是 [RabbitMQ → Kafka](/backend/03-message-queue/vendors/kafka/)（work queue → event streaming）。兩條路的差異：遷 SQS 是 *交出運維、能力對等簡化*（仍是 task queue）；遷 Kafka 是 *換 paradigm、要 replay / 高吞吐 streaming*（從任務隊列變 event log）。選哪條看的是「想擺脫運維」還是「需要 streaming 能力」、不是同一個決策。

### 跟前面 migration playbook 的結構對照

| 篇                     | 主導差異維度      | 結構                      |
| ---------------------- | ----------------- | ------------------------- |
| Kafka ↔ NATS           | Paradigm（高）    | partial + 混合            |
| RabbitMQ → SQS（本篇） | Operational（高） | Type C operational hybrid |

**結論**：兩篇都是 message queue 跨 vendor、但主導差異維度不同 — Kafka ↔ NATS 卡在 paradigm（不同抽象層）、RabbitMQ → SQS 卡在 operational（運維責任轉移）。結構由主導維度決定、不是 universal phased playbook。

## 相關連結

- Source / target vendor：[RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) / [AWS SQS](/backend/03-message-queue/vendors/aws-sqs/)
- 平行 vendor：[Google Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/) / [NATS](/backend/03-message-queue/vendors/nats/)
- 平行 migration playbook：[Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/)
- 引用案例：[3.C48 Airbnb Dynein](/backend/03-message-queue/cases/sqs-airbnb-dynein-delayed-jobs/) / [3.C50 Capital One](/backend/03-message-queue/cases/sqs-capital-one-visibility-timeout/) / [3.C54 Twitch EventSub](/backend/03-message-queue/cases/sqs-twitch-eventsub-fanout/) / [3.C58 Twilio webhook](/backend/03-message-queue/cases/sqs-twilio-webhook-buffer/)
- Methodology：[Migration Playbook 寫作方法論](/posts/migration-playbook-methodology/)
