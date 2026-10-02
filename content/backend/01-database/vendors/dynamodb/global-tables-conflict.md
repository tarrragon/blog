---
title: "DynamoDB Global Tables：multi-region active-active、LWW conflict 與 cross-device sync 正向用例"
date: 2026-05-27
description: "Global Tables 不只是 conflict 痛點、也是 cross-device sync / global read / DR failover 的正向工程方案；本文展開 B2B SaaS vs B2C 業務 driver、LWW conflict resolution、reconciliation pipeline，含 Genesys 99.999% 跨 15 region 跟 Disney+ 跨裝置同步的對照"
weight: 34
tags: ["backend", "database", "dynamodb", "global-tables", "multi-region", "conflict-resolution", "deep-article"]
---

這篇整理 [DynamoDB](/backend/01-database/vendors/dynamodb/) Global Tables 的 multi-region active-active 設計：決定要不要上 Global Tables 的業務 driver、cross-device sync 與 global read 這類正向用例、LWW（Last Writer Wins）conflict resolution，以及 application 端的 conflict 偵測與 [reconciliation](/backend/knowledge-cards/data-reconciliation/)。

Global Tables 用 LWW 在 region 之間非同步複寫，多個 region 同時寫入同一筆資料時，資料不會自動保持一致，conflict 的偵測與 reconciliation 要由 application 自己加。同一個機制也承擔正向用例：Disney+ 用它做跨裝置的播放進度同步，Genesys 用它在 15 個 region 撐起 99.999% 可用性的 B2B 客服平台。

> **Workload 適配本 vendor 才繼續**：DynamoDB 4 軸判讀（PK 天然均勻 / control plane vs data plane / consistency 可接受 eventual / access pattern 穩定）軸見 [single-table-design-pattern 開頭 4 軸前置判讀](../single-table-design-pattern/#dynamodb-適用度前置判讀)。Global Tables 是 *已選 DynamoDB 後* 的拓樸決策；strong global consistency 必要的 workload 應走 Spanner / Cosmos DB strong consistency level、不是用 LWW 補。

## B2B SaaS vs B2C 業務 driver 對比

Global Tables 不是預設選擇、是 *業務性質* 決定的工程投資。Genesys 揭露兩條關鍵 frame — 可用性目標的業務 driver、跟每多一個 9 的 cost 指數成長。

| 業務性質     | 典型可用性目標           | 年停機容忍           | Multi-region 投資邏輯                           |
| ------------ | ------------------------ | -------------------- | ----------------------------------------------- |
| B2C 大型網站 | 99.9%                    | 8.76 小時            | 通常單 region + PITR / cross-region backup 划算 |
| B2B SaaS     | 99.95% 或 99.99%（合約） | 4.4 小時 / 52.6 分鐘 | 合約義務、客戶 SLA 違約有金錢損失、ROI 正向     |
| 客服平台類   | 99.999%（合約客戶）      | 5.26 分鐘            | 客戶停線損失極大、15 region 投資合理（Genesys） |

**B2C 大型網站**通常 99.9% SLA、年停機 8.76 小時可接受、單 region + PITR + cross-region backup 是常見配置；改 Global Tables 邊際成本高、ROI 通常不正向。

**B2B SaaS** 99.95% 或 99.99% SLA 多半寫進合約、違約有具體金錢損失；Global Tables 的 N region cost 對比 SLA 違約成本通常 ROI 正向。critical 的是 *合約義務* 不是 *技術完美*。

**客服平台類** 99.999% 是極端可用性目標、年停機 5.26 分鐘、Genesys 撐 8000+ orgs 的客服平台、客戶停線損失極大、跨 15 region 的 active-active 是合理投資。但 *不是每個 SaaS 都該追 99.999%*、是 *業務性質決定下限*。

**成本對比**（Genesys 案例揭露）：15 region 成本約 = 1 region 的 15x（base table cost）+ 跨 region replication WCU。每多一個 9、容量規劃跟運維成本指數成長。

> **Scope warning（指標口徑紀律）**：99.999% 是「12 個月滾動歷史值、不代表未來持續達成」（Genesys 案例頁的警示段）。可用性是滾動指標、不是恆久承諾。引用 Genesys 99.999% 數字時要明示口徑（滾動 / customer-facing），不要寫成「DynamoDB 保證 99.999%」。

## 正向 access pattern：不只 conflict 議題

Global Tables 不只是 DR / availability、也是正向 access pattern 的工程方案。先建立正向用例的判讀、再進 conflict 細節。

**Cross-device sync**（Disney+ 揭露）：用戶在手機看到一半、晚上回家用電視繼續、播放進度跨裝置同步。Global Tables 自然解這個 access pattern — 用戶在不同 region 登入同帳號、寫入自動同步、最終一致性可接受場景。

**Global read（latency 優化）**：跨地域用戶讀取就近 region 副本、latency 從 200ms 降到 < 10ms。read 比 write 多很多倍的 workload（feed / catalog / user profile）受益最大。

**DR failover**：region-level outage 時 application 切到 secondary region 繼續服務、RTO 通常 < 5 分鐘（DNS / routing 切換時間、不含 application 端 reconnect）。

**B2C 也可能划算的場景**：cross-device sync 是 *user-facing experience*、不是合規 / SLA driver。B2C 大規模平台（Disney+ / Spotify 類）也可能投資 Global Tables。判讀軸是「sync 體驗是否核心 UX」、不只「合約 SLA」。

## 核心機制：LWW conflict resolution

Global Tables 的 first-class concept：

- **Multi-region active-active**：每個 region 都能寫、async replication；typical replication latency < 1s 但 *無 SLA*
- **LWW by 內部 timestamp**：conflict 由 DynamoDB 逐 item 比較寫入的內部 timestamp 決定、timestamp 最新的寫入勝出；不是 logical clock、不是 vector clock。`aws:rep:updatetime` 這組屬性由 2017.11.29（Legacy）版本自動寫進每個 item，截至 2026-09 的官方文件建議新 global table 一律用 2019.11.21（Current）版，Current 版的文件沒有列出這組屬性
- **同 region read-your-write**：本 region 寫立即可讀（同 region quorum 內）、其他 region 看到要等 replication
- **Capacity 獨立**：每個 region 自己的 RCU/WCU、`ReplicatedWriteCapacityUnits` 是跨 region replication 額外 WCU、按 region 數倍計

對應 knowledge card：[consistency level](/backend/knowledge-cards/consistency-level/)、[rto](/backend/knowledge-cards/rto/)、[rpo](/backend/knowledge-cards/rpo/)。

## 設計流程

從 access pattern 分類到 reconciliation pipeline 的設計流程：分類 access pattern、啟用 Global Tables、選寫入策略、設計 idempotency、偵測 conflict、建 reconciliation pipeline。

#### 分類 access pattern

把 table 中的資料分兩類：

- **region-pinned data**：user 主要 region（合規 / 地理 affinity）；不啟用 Global Tables、用 region-pinned cluster
- **global data**：跨 region read / cross-device sync；啟用 Global Tables

不是所有 table 都該上 Global Tables；user profile 跨 region 同步、但用戶交易紀錄可能該 pin 在合規 region。

#### 啟用 Global Tables

```bash
aws dynamodb update-table \
  --table-name orders \
  --replica-updates \
  '[{"Create": {"RegionName": "us-east-1"}}]'
```

加 region 後 vendor 自動 backfill；backfill 期間 capacity 雙倍（原 region + 新 region 同步流量）、要預留 capacity buffer。

#### 選 application 寫入策略

兩種寫入策略：

- **home region write**：每 user 固定一個 home region 寫、避免 conflict；user 跨 region 漫遊時透過 routing 仍寫 home
- **nearest region write**：latency 優先、user 寫就近 region；conflict 機率高、必須加 idempotency 跟 reconciliation

選擇：

| 場景                | 寫入策略             | 理由                             |
| ------------------- | -------------------- | -------------------------------- |
| user profile / 設定 | home region write    | conflict 少、簡單                |
| cross-device sync   | nearest region write | 用戶在不同裝置同時操作、容忍 LWW |
| 訂單 / 金流         | home region write    | 業務不容許 conflict 損失         |

#### 設計 idempotency

每筆 write 加 `request_id` 或 `client_timestamp`、application 端去重：

```python
def write_with_idempotency(user_id, action, request_id):
    table.put_item(
        Item={
            "PK": f"USER#{user_id}",
            "SK": f"ACTION#{action}#{request_id}",
            "ts": datetime.utcnow().isoformat(),
            "request_id": request_id,
        },
        ConditionExpression="attribute_not_exists(request_id)"
    )
```

`ConditionExpression` 在同一 region 內擋重複；跨 region eventual 仍可能 race，conflict 落到 LWW + reconciliation。

> **Scope warning**：用 `request_id` 或 `client_timestamp` 去重屬通用工程實作。PayPay 案例公開的是需求分層（通知不可丟失、訊息另行處理），沒有公開它的 idempotency 實作。

#### 偵測 conflict

DynamoDB Streams 訂閱、Lambda 比較 stream record 的 `ApproximateCreationDateTime` 跟 application timestamp、抓出可疑 conflict 進 reconciliation queue（2019.11.21 版的 item 上沒有 `aws:rep:updatetime` 可讀，時間改取 stream record 自帶的建立時間，精度到秒）：

```python
def detect_conflict(stream_event):
    new_image = stream_event["dynamodb"]["NewImage"]
    repl_time = datetime.fromtimestamp(
        stream_event["dynamodb"]["ApproximateCreationDateTime"], tz=timezone.utc
    ).isoformat()
    app_time = new_image["client_timestamp"]["S"]

    if abs(parse(repl_time) - parse(app_time)) > timedelta(seconds=5):
        # 可疑 conflict、進 reconciliation
        sqs.send_message(
            QueueUrl=RECONCILIATION_QUEUE,
            MessageBody=json.dumps(stream_event)
        )
```

> **Scope warning**：用 DynamoDB Streams 偵測 conflict 屬通用工程實作；PayPay 案例沒有公開是否使用 Streams。

#### 建 reconciliation pipeline

```text
Conflict event → SQS queue → Lambda / human review → merge logic → write back
```

merge logic 視業務而定：

- 訂單金額 conflict：抓最大值（避免少收）
- 用戶設定 conflict：抓最新（user-facing 行為一致）
- watchlist conflict：union（兩裝置加的都保留）

**驗證點**：DR drill 演 region outage、確認 secondary region 接管後 read / write 都正常；`ReplicationLatency` p99 < 1s。

**Rollback boundary**：region 可逐個移除、但 active-active 改 active-passive 期間 application 需配合路由切換；先 application 切再移 region、不可同時做。

## 失敗模式

實際部署常見的 5 種失敗：

#### LWW 默默吃掉 write

跨 region 同一 record concurrent update、後到的 write 因 timestamp 較大蓋過先到的；business 看到「我送出的更新沒了」、稽核 log 才發現 conflict。修法：critical write 加 `ConditionExpression` 比較 `version` attribute、conflict 時 application 端 retry + merge；不要依賴 LWW 作為 conflict 解。

#### Clock skew 讓 LWW 倒置

一個 region 的時鐘因 NTP skew 快了 200ms，它先寫入的那筆帶著較大的 timestamp，另一個 region 稍後對同一筆的寫入 timestamp 反而較小，LWW 於是讓較舊的寫入贏。修法：依靠 application timestamp + monotonic counter、不依賴 server wall clock；critical write 用 conditional version + retry。

> **Scope warning**：「200ms NTP skew」具體數字屬通用工程估算、case 未揭露具體 skew 範圍。

#### Replication lag 撞 SLO

大 batch write 期間 replication lag 從 1s 變 30s、跨 region read 看到 30s 前資料、application 端 user 操作異常。修法：偵測 `ReplicationLatency` 升高時 application 端切 home region read、避免跨 region eventual read；把 replication lag 加進 SLO 監控、設 alarm。

#### DR 切換後 stale data 持續 propagate

primary region outage 切到 secondary、舊 primary 恢復後仍把 outdated data 推回去、覆蓋 secondary 期間的新寫入。修法：DR runbook 含「舊 primary 恢復後人工 reconciliation 或重建」step、不可全自動 catch-up；舊 primary 恢復前先確認 replication 方向是「從 secondary catch up」而非「推舊資料回 secondary」。

#### 跨 region transaction 失敗

application 試圖跨 region `TransactWriteItems`、API 不支援跨 region transaction、原子性破裂。修法：transaction 限同 region 內、跨 region 用 [saga](/backend/knowledge-cards/saga/) + idempotent + reconciliation；不要把同 region 的 transaction 假設搬到跨 region。

**Anti-recommendation**：single-region availability 已達 99.95% + RTO 可接受 1 小時 + 預算敏感（特別 B2C 場景）→ 用 PITR + 跨 region backup 而非 Global Tables；Global Tables cost = N × single region cost 不止（對應 B2B vs B2C driver 對比）。

## 容量與觀測

CloudWatch metric：

- `ReplicationLatency`：p99 通常 < 1s、建議 SLO 設 5s alarm
- `PendingReplicationCount`：積壓量、batch write 期間會升高
- `ReplicatedWriteCapacityUnits`：跨 region replication 額外 WCU、按 region 數倍計

DynamoDB Streams + Lambda：抓 conflict event、寫進獨立 audit table；reconciliation job 從 audit table 跑、不直接動 base table。

**Region-level dashboard**：每個 region 獨立 capacity / latency / error rate panel；DR drill 看是否能在 RTO 內切換。

**Cost monitoring**：

- Global Tables cost ≈ N region × base cost + replication WCU
- 4 region 成本約 4.5x single region；15 region（Genesys 規模）約 15x
- 每多一個 region 都要重新算 ROI（[On-Demand vs Provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) 裡 DynamoDB 與自管 cluster 的 cost crossover 判讀的延伸）

**指標口徑紀律**（重要）：99.99% / 99.999% SLA 是 *滾動指標 + 歷史值*、不是永久承諾；引用 Genesys 99.999% 時明示「12 個月滾動 / customer-facing」、不寫成「DynamoDB 保證 99.999%」。

接回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)。

## 邊界與整合

### region-pinned Global Tables 吸收合規邊界

Global Tables 不只是高可用工具、也是 *合規邊界*（[Data Residency](/backend/knowledge-cards/data-residency/) 拓樸）的吸收層。DynamoDB 在 vendor capability 層級支援 *region-pinned replication* — 每張 table 可獨立決定哪些 region 參與 replication group、部分 region 可不加入。這個 capability 同時服務三類場景：合規分離（受監管市場資料不跨境）、cost / latency 取捨（資料只在主要服務 region 同步）、災備拓樸（少數 region 純讀備援）。Genesys 15 region 揭露的是 *延遲就近接入* 的 B2B SaaS 拓樸（客戶服務延遲敏感、必須在客戶所在地有 region）— case 原文沒明示合規應用、但 region-pinned capability 在 Genesys 規模下天然能容納合規市場分離、是同 capability 的 *可能應用維度*、不是 case 已驗證的具體實踐。

跨 vendor 對照：

| Vendor              | 合規吸收機制                                                            | 拓樸特性                                             |
| ------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------- |
| DynamoDB            | region-pinned Global Tables（按 region 開關 replication、各市場可分離） | 仍是 active-active、但 replication 範圍可控          |
| Aurora              | fleet 拓樸（每市場獨立 cluster、合規禁止跨境 = Global Database 反指標） | active-passive per market、跨市場不複製              |
| CockroachDB         | locality + placement（邏輯一個 cluster + region pinning + Outposts）    | 單 logical cluster、physical row 鎖在合規 region     |
| MongoDB / Cosmos DB | cluster-per-region（無 row-level locality 等價物、整 cluster 切割）     | 各 region 獨立 cluster、application 層做市場 routing |

**為什麼跨境合規在 DynamoDB 上需要的結構改造最少**：Global Tables 的 region 開關是 *table 級* 設計（每張 table 可獨立決定哪些 region 參與）、不像 Aurora 必須整 cluster 拆。讀者要把「跨境合規 + 高可用」雙重需求兼顧時、DynamoDB 是最少結構性改造的路徑 — 但代價是 LWW conflict 跟 reconciliation 設計仍要自己做。

**何時 region-pinned 而非 active-active**：受監管金融 / 個資跨境禁止的市場（如 GDPR strict 條款區、中國個資法 PIPL、巴西 LGPD）— 該 region 仍開 DynamoDB table、但 *不加入 Global Tables replication group*、跟其他 region 完全切割。capability 設計上支援這種按 region 開關 replication 的拓樸；具體是否套用、要看 *讀者自己的市場合規清單*、不是把 Genesys 規模當必然證據（Genesys case 揭露的是延遲就近接入、未明示合規分離實踐）。

### Disney+ vs Genesys：UX driver 與合約 driver

Disney+ 跟 Genesys 是 Global Tables 兩種不同的工程動機：

- **Disney+**：cross-device sync 是 user-facing UX、watchlist + 播放進度跨裝置同步、B2C 但 sync 是 core experience
- **Genesys**：99.999% B2B SaaS 合約義務、15 region active-active、客服平台停線損失極大

兩個 case 都用 Global Tables、但動機完全不同 — Disney+ 是 UX driver、Genesys 是合約 driver。設計文件要寫明這張 table 的 Global Tables 屬於 UX driver 還是合約 driver，兩者的 cost 容忍度跟 conflict 容忍度完全不同。

### Sibling 與 cross-link

- [consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/) — 同 region eventual / strong 取捨、本篇是跨 region 延伸
- [on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) — 多 region capacity 規劃放大、DBA / SRE 工時釋放在 multi-region 更顯著
- [partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) — hot partition 跨 region 同樣存在、每個 region 的 partition 都要均勻
- [single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) — single-table 設計在 multi-region 仍適用、access pattern 反推 PK/SK 不變
- 替代路由：global strong consistency 必要 → Spanner / Cosmos DB strong consistency level
- Migration playbook：single-region → Global Tables 屬 topology re-layout、對應 [migration playbook methodology](/posts/migration-playbook-methodology/) Type F
- [Genesys：用 DynamoDB 在 15 region 跑出 99.999% 可用性](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)：B2B SaaS 合約 driver 下的多 region 可用性工程
- [Disney+：DynamoDB 撐每日數十億動作的觀看歷史](/backend/09-performance-capacity/cases/disney-plus-content-metadata/)：cross-device sync 作為正向 access pattern
- [PayPay：行動支付每日 3 億訊息的 DynamoDB 後端](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/)：需求分層（通知 vs 訊息）；本篇的 idempotency 與 Streams 寫法是通用工程實作，PayPay 沒有公開具體實作
