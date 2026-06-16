---
title: "AWS SQS：Visibility timeout、long polling 與 Lambda event source 的成本與失敗形狀"
date: 2026-06-16
description: "SQS deep article：visibility timeout 對齊 consumer 處理時間（ChangeMessageVisibility）、long vs short polling 的 cost 取捨（WaitTimeSeconds）、SQS + Lambda event source mapping（batch size / batch window / 並行 ramp-up）、DLQ + redrive policy（maxReceiveCount）、message size 與 extended client、per-request cost 模型；含 5 個 production 故障演練（VT < 處理時間 redelivery、polling 設定省成本、Lambda 部分失敗整批重投、DLQ maxReceiveCount、FIFO 吞吐上限）"
weight: 12
tags: ["backend", "message-queue", "aws-sqs", "visibility-timeout", "lambda", "cost", "deep-article"]
---

> 本文是 [AWS SQS](/backend/03-message-queue/vendors/aws-sqs/) overview 的 implementation-layer deep article。本文的 CLI 指令語法經 LocalStack round-trip 驗證、真實 AWS 的 scaling 行為、Lambda event source mapping 細節與計費數字依 AWS 官方文件。

## SQS 沒有 broker ACK，delivery 控制全靠 visibility timeout

SQS 跟自管 broker（RabbitMQ / Kafka）最大的操作差異是：consumer 不會跟 broker 維持一條長連線、也沒有 channel-level 的 ack / nack 協議。SQS 的整個 delivery 保證建立在一個計時器上 — visibility timeout。訊息被 `ReceiveMessage` 拉走後進入 in-flight 狀態、在 timeout 視窗內對其他 consumer 不可見；consumer 處理成功就呼叫 `DeleteMessage` 把它移除、處理失敗或當機則什麼都不做、等 timeout 到期訊息自動回到 queue 重新可見。

這個設計把「確認處理完成」的責任從 broker 連線狀態轉移到 consumer 的主動刪除。好處是 consumer 可以隨時死掉、重啟、水平擴縮、不需要維持任何 session 狀態 — 訊息不會因為連線斷掉而遺失。代價是 visibility timeout 這個數字變成最容易設錯、後果最隱蔽的參數：設太短訊息會在 consumer 還在處理時就重新可見、被另一個 consumer 重複領走；設太長則 consumer 當機後訊息要等很久才回到 queue、retry 延遲拉長。

實機建立一個 queue 並查 default、可以確認這個視窗的起點。新建 queue 的 `VisibilityTimeout` 預設 30 秒：

```bash
# 不帶任何 attribute 建 queue
aws sqs create-queue --queue-name demo-default

# 查 default visibility timeout
aws sqs get-queue-attributes \
  --queue-url <url> \
  --attribute-names VisibilityTimeout
# => "VisibilityTimeout": "30"
```

30 秒對「處理時間穩定在數百毫秒」的 task 綽綽有餘、對「呼叫第三方 API、跑批次轉檔、寫多個下游」的 task 則經常不夠。下一節先把這個參數設對，後面的故障演練再展開它設錯時的具體徵兆。

## 對齊 visibility timeout 與 consumer 處理時間

設定 visibility timeout 的判準是「略高於 consumer 處理單則訊息的最大時間」、不是平均時間。Capital One 的官方 tech blog 在講 SQS + Lambda 時明示這條原則：visibility timeout 應比最大處理時間略高 — 因為決定 redelivery 的是尾端那幾則最慢的訊息、不是中位數。處理時間 p50 是 2 秒、p99 是 25 秒時、visibility timeout 要對齊 p99 加緩衝、設到 30-40 秒、而不是看 p50 設 10 秒。

建 queue 時直接帶 `VisibilityTimeout` attribute，或對既有 queue 用 `set-queue-attributes` 調整：

```bash
# 建立時指定（單位：秒；上限 12 小時 = 43200）
aws sqs create-queue \
  --queue-name demo \
  --attributes VisibilityTimeout=60

# 對既有 queue 調整
aws sqs set-queue-attributes \
  --queue-url <url> \
  --attributes VisibilityTimeout=120
```

處理時間本身不可預測的場景（例如轉檔大小差異大、下游 API 偶發慢）、用一個固定的 queue-level visibility timeout 會兩頭不討好：對齊最壞情況會讓正常訊息當機後 retry 太慢、對齊正常情況會讓慢訊息 redelivery。SQS 給的工具是 `ChangeMessageVisibility` — consumer 在處理過程中發現這則會花更久時，主動延長這一則訊息的 visibility timeout，而不影響 queue default：

```bash
# consumer 拿到 ReceiptHandle 後，動態把這則延長到 120 秒
aws sqs change-message-visibility \
  --queue-url <url> \
  --receipt-handle <receipt-handle> \
  --visibility-timeout 120
```

實務上長任務 consumer 的常見寫法是「heartbeat extension」：每處理一段就呼叫一次 `ChangeMessageVisibility` 往後推、形成一個續命迴圈、直到處理完成才 `DeleteMessage`。這把「我還活著、還在處理這則」的訊號明確化、避免用一個保守的 queue-level 大數字一刀切。`ReceiptHandle` 是每次 `ReceiveMessage` 回傳的一次性 token、不是 message id — 同一則訊息被重新領取後 ReceiptHandle 會變、延長操作必須用當次領取拿到的那一個。

## Long polling 決定空輪詢成本，short polling 是預設陷阱

Polling 模式直接決定 SQS 的 request 帳單，因為 SQS 按 request 數計費、而 `ReceiveMessage` 即使沒拿到訊息也算一次 request。Short polling（預設、`WaitTimeSeconds=0`）的行為是「立即回應」：consumer 發 `ReceiveMessage`、SQS 抽樣一部分 server 立刻回、queue 空的時候回一個空 response。Consumer 為了即時拿到訊息會緊接著再發一次、形成高頻空輪詢 — 在低流量 queue 上、絕大多數 request 都是空回、帳單全花在「問有沒有訊息」上。

Long polling（`WaitTimeSeconds` 設 1-20 秒）改變這個行為：SQS 收到 `ReceiveMessage` 後、若 queue 當下沒訊息、會 hold 住這條連線最多 `WaitTimeSeconds` 秒、期間一有訊息到達就立刻回傳、整段時間都沒訊息才回空。對 consumer 端來說一個 20 秒的 long poll 取代了 20 秒內可能發出的數十次 short poll、空 request 數量大幅下降。

```bash
# long polling：等到有訊息或最多 20 秒才回
aws sqs receive-message \
  --queue-url <url> \
  --wait-time-seconds 20
```

設定 long polling 有兩個位置：per-request 帶 `--wait-time-seconds`、或 queue-level 設 `ReceiveMessageWaitTimeSeconds` attribute 讓所有 receive 預設走 long polling。後者更穩、不依賴每個 consumer 都記得帶參數。20 秒幾乎總是對的選擇：它把空輪詢壓到最低、而 latency 代價只在「queue 剛好空、訊息在 poll 結束後才到」這個邊界出現 — 大多數有持續流量的 queue 根本碰不到 20 秒上限。唯一要留意的是 consumer 的 socket timeout 必須大於 `WaitTimeSeconds`、否則 client 會在 SQS 還在 hold 連線時自己先 timeout 斷線。

## SQS + Lambda：event source mapping 把 polling 交給 AWS

把 SQS 接上 Lambda 時、polling 這件事整個從應用程式碼消失、改由 Lambda 的 event source mapping 接管。Event source mapping 是 Lambda service 內部一組 managed poller、持續對 queue 做 long polling、把拉到的訊息打包成 batch 同步 invoke 函式、函式正常返回就由 service 代為 `DeleteMessage`。Consumer 端不再寫 receive / delete 迴圈、只寫處理單一 batch 的 handler。

這套 managed poller 的 scaling 不是線性的、有 ramp-up 上限。Capital One 觀察到的行為是：Lambda 初始開 5 個並行的 long polling 連線、隨 queue 累積每分鐘最多增加 60 個 instance、standard queue 的並行 batch 上限到 1000。這意味著 queue 突然湧入大量訊息時、Lambda 不會瞬間炸開到滿並行、而是分鐘級爬升 — 容量規劃時要把這段 ramp-up 期算進 backlog 消化時間、不能假設「訊息一到就有足夠 consumer」。

兩個核心參數決定每次 invoke 的形狀：

| 參數         | 作用                                                                 | 取捨                                                        |
| ------------ | -------------------------------------------------------------------- | ----------------------------------------------------------- |
| Batch size   | 一次 invoke 最多打包幾則訊息（standard 上限 10000、FIFO 上限 10）    | 大 batch 省 invoke 數與成本、但放大「部分失敗整批重投」風險 |
| Batch window | 累積訊息的最長等待時間（`MaximumBatchingWindowInSeconds`、0-300 秒） | 拉長視窗讓 batch 更滿、代價是 latency；流量稀疏時尤其明顯   |

Batch size 拉大表面上省錢 — invoke 次數少、每則訊息分攤的 request 成本低。但它跟下一節的部分失敗處理直接耦合：batch 越大、一則毒訊息拖累整批重投的範圍越大。Batch window 則是流量稀疏時讓 batch 攢滿的手段、流量本來就密集時設不設都差不多、反而會引入不必要的 latency。

## DLQ 與 redrive policy：用 maxReceiveCount 隔離毒訊息

毒訊息（永遠處理失敗的訊息 — 格式損壞、引用了已刪除的資源、觸發 consumer 確定性 bug）會在 visibility timeout 機制下無限重投：處理失敗、timeout 到期、重新可見、再次被領取、再次失敗。沒有上限的話這則訊息會永遠佔用 consumer 資源、且其他正常訊息的處理被它反覆插隊。Dead-letter queue（DLQ）加 `maxReceiveCount` 是 SQS 對這個問題的標準解 — 訊息被接收超過 N 次後、SQS 自動把它移到另一個指定的 queue（DLQ）、主 queue 不再被它卡住。

設定分兩步：先建一個普通 queue 當 DLQ、取它的 ARN、再對主 queue 設 redrive policy 指向這個 ARN 並設 `maxReceiveCount`：

```bash
# 1. 建 DLQ 並取得 ARN
aws sqs create-queue --queue-name demo-dlq
aws sqs get-queue-attributes \
  --queue-url <dlq-url> \
  --attribute-names QueueArn
# => "QueueArn": "arn:aws:sqs:us-east-1:000000000000:demo-dlq"

# 2. 對主 queue 設 redrive policy（被接收 5 次後送 DLQ）
aws sqs set-queue-attributes \
  --queue-url <main-url> \
  --attributes '{"RedrivePolicy":"{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:000000000000:demo-dlq\",\"maxReceiveCount\":\"5\"}"}'
```

DLQ 不是訊息的墳場、是待診斷的暫存區。對應 [poison message quarantine](/backend/knowledge-cards/poison-message-quarantine/) 的思路、DLQ 累積要分兩種根因處理：訊息格式錯（永遠失敗、需要修 producer 或人工丟棄）vs 下游服務暫時 down（訊息本身沒問題、修好下游後可以重放）。後者用 redrive 把訊息從 DLQ 批次放回主 queue 重新處理、對應 [dlq drain](/backend/knowledge-cards/dlq-drain/) 的排空流程。判斷之前先看 DLQ 裡訊息的內容、不要不加判斷地 redrive — 把毒訊息 redrive 回去只會再走一輪 maxReceiveCount 又回到 DLQ。

`maxReceiveCount` 設多少是取捨：太小（例如 1-2）會讓「下游短暫抖動」這種暫時性失敗被誤判成毒訊息、過早送進 DLQ；太大（例如 100）會讓真正的毒訊息浪費大量 consumer 重試。多數 task queue 設 3-5 是合理起點 — 足以吸收幾次暫時性失敗、又不至於讓確定性失敗的訊息空轉太久。

## Message size 限制與 extended client

SQS 單則訊息上限是 256 KB（含 message body 與 attributes）。這對純事件通知、id 引用、小型 payload 足夠、但對「訊息本身要攜帶大檔案內容」的場景不夠 — 例如要傳一份報表、一張圖、一段長文字。直接的反模式是把大內容塞進 message body、撞上 256 KB 限制後 `SendMessage` 直接報錯。

標準解是 claim-check 模式：大 payload 寫到 S3、訊息只攜帶 S3 的物件引用（bucket + key）、consumer 收到訊息後再去 S3 取內容。AWS 提供的 Extended Client Library（Java / Python 等 SDK）把這個模式封裝起來 — `SendMessage` 時若 payload 超過門檻、library 自動把內容寫 S3、訊息只帶 pointer；consumer 端 `ReceiveMessage` 時 library 自動從 S3 取回、對應用程式碼透明。

選擇門檻時要把 S3 的 request 成本與 latency 算進來：每則大訊息變成「一次 S3 PUT + 一次 SQS Send」、consumer 端「一次 SQS Receive + 一次 S3 GET」。對大多數 payload 都超過 256 KB 的 queue、這是必要成本；對 payload 多數很小、偶爾爆量的 queue、extended client 只在超門檻時走 S3、混合成本可接受。Payload 普遍很大且高頻的場景、要重新評估 SQS 是否適合 — 可能該改用 streaming（Kinesis / Kafka）或乾脆讓 producer / consumer 直接交換 S3 引用、SQS 只傳通知。

## Cost：按 request 計費，每一次操作都是一個 request

SQS 的計費模型是 per-request、不是 per-message-stored、也沒有固定月費。每一次 API call — `SendMessage`、`ReceiveMessage`（含空回）、`DeleteMessage`、`ChangeMessageVisibility` — 都算一個 request。這個模型對成本估算的影響是：帳單由「操作次數」驅動、而非「訊息量」或「儲存時長」。一則訊息從 producer 到 consumer 的最小生命週期是 send（1）+ receive（1）+ delete（1）= 3 個 request；空輪詢、retry、visibility 延長都會額外加 request。

兩個降低 request 數的主要手段：

第一是 batch 操作。`SendMessageBatch` 與 `DeleteMessageBatch` 一次最多打包 10 則、而 SQS 把一個 batch call 算作一個 request（實際計費以 64 KB 為一個 request 單位、一個 batch 在此範圍內仍是少數 request）。把 10 則訊息的 send 從 10 個 request 壓成 1 個 batch request、在高頻 queue 上是數量級的成本差異：

```bash
aws sqs send-message-batch \
  --queue-url <url> \
  --entries 'Id=m1,MessageBody=a' 'Id=m2,MessageBody=b'
```

第二是 long polling 消滅空 request — 前面 polling 段已經展開。低流量 queue 的帳單若異常高、第一個要查的就是有沒有開 long polling、consumer 是不是在 short polling 下高頻空轉。

Data transfer cost 只在跨 region 時出現 — 同 region 內 producer / consumer 與 SQS 之間的傳輸不計流量費。把 producer、consumer、queue 放在同一個 region 是預設、跨 region 設計要把 egress 成本明確算進來。FIFO queue 的 per-request 單價比 standard 高、是用成本換 ordering 與去重保證 — 不需要嚴格順序的場景用 standard、把這筆溢價省下來。

Rapid7 的規模參考點說明這個計費模型在極端規模下的份量：Rapid7 公開引述 SQS 撐住「每天數十億則訊息」。在這個量級、per-request 計費乘以訊息數是一筆需要認真建模的成本 — batch、long polling、避免不必要的 visibility 延長、控制 retry 次數、每一項節省都被訊息量放大。SQS 在數十億級可用、但成本結構必須被當作架構參數對待、不是事後才看帳單。

## Production 故障演練

### 故障一：visibility timeout 短於處理時間，訊息被重複處理

**徵兆**：consumer log 顯示同一個 message id 在短時間內被處理多次、下游出現重複的副作用（重複扣款、重複寄信、重複寫入）；CloudWatch 的 `ApproximateNumberOfMessagesNotVisible`（in-flight 數）異常高、`NumberOfMessagesReceived` 遠大於 `NumberOfMessagesDeleted`。

**根因**：visibility timeout 設定值低於 consumer 實際處理單則訊息的時間。訊息在 consumer 還沒處理完、還沒呼叫 `DeleteMessage` 之前、timeout 就到期、訊息重新可見、被另一個 consumer（或同一個 consumer 的下一輪 poll）領走。新建 queue 的 default 是 30 秒 — 處理時間長於此就會踩到：

```bash
aws sqs get-queue-attributes \
  --queue-url <url> \
  --attribute-names VisibilityTimeout
# 看到 30 而 consumer 處理時間 > 30s，就是這個問題
```

**修法**：把 visibility timeout 對齊 consumer 處理時間的 p99 加緩衝、用 `set-queue-attributes` 調高；處理時間變異大的長任務改用 `ChangeMessageVisibility` heartbeat 在處理中動態延長。同時、因為 SQS standard 是 at-least-once、重複投遞在故障與 retry 下本來就會發生、consumer 的處理邏輯必須冪等 — 對齊 visibility timeout 降低重複頻率、冪等性才是真正消除重複副作用的防線。

### 故障二：short polling 預設導致低流量 queue 帳單異常

**徵兆**：一個訊息量很低的 queue、月度 SQS 帳單卻很高；CloudWatch 顯示 `NumberOfEmptyReceives` 佔 `ReceiveMessage` 總數的絕大比例 — 大量 request 是空回。

**根因**：consumer 走 short polling（`WaitTimeSeconds=0`、預設值）、在 queue 空的時候緊密地反覆發 `ReceiveMessage`、每次都立即空回、每次都計一個 request。流量越低、空回比例越高、帳單越是花在「問有沒有訊息」上。

**修法**：在 queue-level 設 `ReceiveMessageWaitTimeSeconds=20` 讓所有 receive 預設走 long polling、或在每個 `ReceiveMessage` 帶 `--wait-time-seconds 20`。Queue-level 設定更穩、不依賴每個 consumer 記得帶參數。設定後 consumer 在 queue 空時會 hold 住連線最多 20 秒、空 request 數量級下降、帳單同步下降。同時確認 consumer 的 socket timeout 大於 20 秒、避免 client 先於 SQS 斷線。

### 故障三：Lambda batch 部分失敗，整批訊息被重投

**徵兆**：一個 batch 裡只有少數訊息處理失敗、但整批訊息（含已成功的）全部回到 queue 重新處理；下游對已成功的訊息出現重複副作用；DLQ 累積速度遠超實際毒訊息數量。

**根因**：Lambda event source mapping 的 default 行為是「整批成敗一體」— 函式只要拋出錯誤、整個 batch 被視為失敗、所有訊息（包含已經處理成功的）都不會被刪除、全部重新可見重投。Batch size 越大、一則失敗拖累的成功訊息越多。

**修法**：啟用 partial batch response — event source mapping 設 `ReportBatchItemFailures`、handler 返回時只回報失敗的 message id 清單、SQS 只把這些重投、已成功的正常刪除。這把失敗的爆炸半徑從「整批」縮到「真正失敗的那幾則」。配合縮小 batch size 進一步降低單批風險、並確保 handler 冪等以承受不可避免的重投。Handler 必須正確實作 partial response 的返回格式 — 漏回報某則失敗會讓它被當成成功刪除、訊息靜默遺失。

### 故障四：maxReceiveCount 設定不當，毒訊息空轉或誤判

**徵兆**：兩種相反的故障形狀。一是 DLQ 幾乎為空但主 queue 有訊息反覆重試數十次、consumer log 同一 message id 重複出現、佔用處理容量 — maxReceiveCount 設太大。二是 DLQ 快速累積大量其實沒問題的訊息、redrive 回去又能正常處理 — maxReceiveCount 設太小、把下游短暫抖動誤判成毒訊息。

**根因**：redrive policy 沒設、或 `maxReceiveCount` 與「暫時性失敗的正常重試次數」不匹配。沒設 redrive policy 時毒訊息無限重投；設太大時毒訊息空轉太久才進 DLQ；設太小時正常訊息在下游抖動期間被過早判死。

**修法**：對主 queue 設 redrive policy、`maxReceiveCount` 取 3-5 作為起點 — 足以吸收幾次暫時性失敗、又不讓確定性失敗的訊息空轉太久。觀察 DLQ 的累積模式再微調：DLQ 累積的多是「下游修好後 redrive 能成功」的訊息就調高、累積的多是「redrive 回去又進 DLQ」的真毒訊息就維持或調低。對 DLQ 設 CloudWatch alarm 監控 `ApproximateNumberOfMessagesVisible`、累積超過閾值就告警人工介入、區分 redrive vs 丟棄。

### 故障五：FIFO queue 撞上吞吐上限

**徵兆**：把 standard queue 換成 FIFO 取得 ordering 後、高峰流量下 producer 端開始收到 throttling、訊息積壓、`SendMessage` 報限流錯誤；吞吐怎麼加 consumer 都上不去。

**根因**：FIFO queue 為了維持順序與去重、吞吐遠低於 standard。FIFO 的基礎吞吐是每秒 300 則訊息（API call）、開啟 batching 後到每秒 3000 則。更關鍵的是順序保證的粒度在 `MessageGroupId` — 同一個 group 內的訊息嚴格串行處理、跨 group 才能並行。若所有訊息共用一個 group id、實際並行度退化成 1、無論加多少 consumer 都無法並行消化。

```bash
# FIFO send 必須帶 MessageGroupId（決定順序與並行粒度）
aws sqs send-message \
  --queue-url <fifo-url> \
  --message-body "ordered-1" \
  --message-group-id "group-a"
```

**修法**：先確認是否真的需要全域順序 — 多數場景只需要「同一個實體（同一用戶、同一訂單）內部有序」、不需要跨實體有序。把 `MessageGroupId` 設成業務實體 id（用戶 id、訂單 id）、讓不同實體的訊息能跨 group 並行、吞吐隨 group 數量擴展。確定需要嚴格全域順序且吞吐撞頂的場景、FIFO 的設計上限就是天花板 — 此時要重新評估是否該換成 streaming（Kafka 的 partition 模型在 per-key 有序下提供更高並行）、或拆分 queue。不需要任何順序保證的場景、退回 standard queue、把 FIFO 的吞吐限制與成本溢價一起省掉。

## 整合與下一步

### 跟 consumer 設計能力對接

本文的 visibility timeout heartbeat、partial batch response、冪等處理都是 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/) 的具體落地 — consumer-design 講語言無關的 consumer 模式、本文是 SQS 上的實作形狀。retry 與 replay 的交接路徑見 [queue consumer retry replay handoff](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)。

### 跟知識卡對位

DLQ 段對應 [poison message quarantine](/backend/knowledge-cards/poison-message-quarantine/)（毒訊息隔離）與 [dlq drain](/backend/knowledge-cards/dlq-drain/)（DLQ 排空）兩張卡 — SQS 的 redrive policy + maxReceiveCount 是這兩個概念在 managed queue 上的具體機制。visibility timeout 的 in-flight 概念見 [in-flight](/backend/knowledge-cards/in-flight/)。

### 跟 case 對位

visibility timeout 與 Lambda event source 的 ramp-up 行為來自 [3.C50 Capital One](/backend/03-message-queue/cases/sqs-capital-one-visibility-timeout/)；at-least-once + DLQ 在工作排程的取捨來自 [3.C48 Airbnb Dynein](/backend/03-message-queue/cases/sqs-airbnb-dynein-delayed-jobs/)；per-request cost 在極端規模的份量來自 [3.C59 Rapid7](/backend/03-message-queue/cases/sqs-rapid7-scale-billion-messages/)。

### 何時 revisit

FIFO 吞吐撞頂、需要 replay / streaming、或 cost 在 streaming 模型下更划算時、回 [SQS overview 的「何時改走其他服務」](/backend/03-message-queue/vendors/aws-sqs/) 重新選型。跨雲 managed queue 的對照見 [Google Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/)。
