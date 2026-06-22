---
title: "CloudWatch Logs Insights 查詢與日誌治理"
date: 2026-06-22
description: "說明 CloudWatch Logs Insights 查詢語法、log group 設計、retention policy、cross-account aggregation、subscription filter 與 cost governance"
weight: 10
tags: ["backend", "observability", "cloudwatch", "logs", "cost-governance"]
---

> 本文是 [AWS CloudWatch](/backend/04-observability/vendors/aws-cloudwatch/) 的 vendor deep article，深化 overview「Logs Insights query」跟「Logs lifecycle」段。初次接觸 CloudWatch 的讀者建議先讀 [CloudWatch 服務頁](/backend/04-observability/vendors/aws-cloudwatch/)。

## 問題情境

CloudWatch Logs 的成本模型跟 self-hosted log stack 不同 — ingestion、storage 跟 query 分開計費，每一層都有明確的 cost lever。理解 log group 設計、retention 設定與 subscription filter 的組合，才能在 AWS-native 環境下控制日誌成本而不犧牲事故判讀能力。

## Log group 設計

### 拆分粒度

Log group 是 CloudWatch Logs 的計費與 retention 邊界。同一個 log group 內的所有 log stream 共用 retention policy 和 access control（IAM resource policy）。

合理的拆分粒度是 **一個服務一個 log group**，而非一個帳號一個或一個 container 一個。服務級拆分讓 retention、查詢範圍與 IAM 權限自然對齊服務 ownership。

| 拆分策略                            | 適合場景                       | 風險                                       |
| ----------------------------------- | ------------------------------ | ------------------------------------------ |
| 一個服務一個 log group              | 多數 production 服務           | log group 數量增長需要 naming convention   |
| 一個環境一個 log group              | 非常小的團隊、staging/dev 環境 | 混合多個服務的日誌，查詢時需要額外 filter  |
| 一個 Lambda function 一個 log group | Lambda 預設行為                | Lambda 數量多時 log group 爆量，管理成本高 |

Lambda 的預設行為是每個 function 自動建一個 log group（`/aws/lambda/<function-name>`）。function 數量超過數十個後，需要用 naming convention 加 tag 控制，否則 retention policy 難以統一套用。

### Naming convention

推薦格式：`/<environment>/<service>/<component>`，例如 `/prod/checkout-api/app`、`/prod/checkout-api/access-log`。統一前綴讓 Logs Insights 的 multi-log-group query 用 prefix matching 篩選。

## Logs Insights 查詢語法

### 核心語法

Logs Insights 的查詢結構是 pipe-based：每行用 `|` 分隔，依序處理。

```text
fields @timestamp, @message, @logStream
| filter @message like /ERROR/
| parse @message "order_id=* status=*" as order_id, status
| stats count(*) as error_count by status
| sort error_count desc
| limit 20
```

常用 command 對照：

| Command   | 用途                               | 注意事項                                   |
| --------- | ---------------------------------- | ------------------------------------------ |
| `fields`  | 選擇要顯示的欄位                   | `@timestamp`、`@message` 是內建欄位        |
| `filter`  | 條件篩選                           | 支援 `like /regex/`、`=`、`>`、`in []`     |
| `parse`   | 從非結構化 log 擷取欄位            | glob pattern 用 `*`、regex 用 `/pattern/`  |
| `stats`   | 聚合計算                           | `count`、`avg`、`sum`、`min`、`max`、`pct` |
| `sort`    | 排序                               | 預設 `@timestamp desc`                     |
| `display` | 只顯示指定欄位（跟 `fields` 互補） | 用在 `stats` 後只要看聚合結果              |

### JSON 自動解析

CloudWatch Logs 會自動辨識 JSON 格式的 log event。JSON 欄位用 dot notation 存取：

```text
fields @timestamp, requestId, level, message
| filter level = "ERROR"
| stats count(*) by bin(5m)
```

如果 log 是 JSON 格式，`parse` 通常不需要 — 直接用欄位名稱。混合格式（部分 JSON、部分 plain text）時，需要用 `isPresent()` 判斷欄位是否存在。

### 效能考量

Logs Insights 的查詢成本按掃描的 data 量計費（每 GB scanned），不按結果數。減少掃描量的方式：

- 縮短時間範圍：事故判讀先查最近 30 分鐘，確認 pattern 後再擴大
- 指定 log group：避免對所有 log group 做全域查詢
- 用 `limit` 限制結果集大小（不影響掃描量，但減少資料傳輸）

跨 log group 查詢最多同時查 50 個 log group。超過時需要拆成多次查詢或用 subscription filter 把資料匯到集中儲存。

## Retention policy

### 設定方式

Retention policy 在 log group 級別設定。每個 log group 可以獨立選擇 1 天到 10 年、或永不過期。

```bash
aws logs put-retention-policy \
  --log-group-name /prod/checkout-api/app \
  --retention-in-days 30
```

常見 retention 策略按服務性質分：

| 服務類型                          | 建議 retention       | 理由                                                                                      |
| --------------------------------- | -------------------- | ----------------------------------------------------------------------------------------- |
| 核心交易路徑（checkout、payment） | 90-365 天            | 事故回溯、合規稽核                                                                        |
| 一般 API 服務                     | 30-90 天             | 事故回溯足夠，cost 可控                                                                   |
| Background job / worker           | 14-30 天             | 失敗時看最近數天即可                                                                      |
| Lambda / short-lived function     | 7-14 天              | 高量低價值，過期快速清理                                                                  |
| Audit log                         | 365 天以上或永不過期 | 法規要求，見 [4.12 Audit Log Governance](/backend/04-observability/audit-log-governance/) |

未設定 retention 的 log group 預設永不過期 — 這是 CloudWatch 日誌成本超支的常見原因。新 log group 建立後應立即設定 retention。

### FinTech 合規場景的 log group 分離

[FinTech 審計證據案例](/backend/04-observability/cases/fintech-audit-evidence-observability/)揭露一個常見問題：audit log 跟 operational log 混在同一個 log group，retention 只能統一設定。結果要嘛 operational log 為了合規被迫留太久（成本浪費）、要嘛 audit log 跟著 operational log 的短 retention 被刪掉（合規風險）。

CloudWatch 的 log group 設計天然支援這種分離 — audit log 跟 operational log 用不同 log group、各自設定 retention：

| Log 類型                        | Log group 命名              | Retention       | Log class         |
| ------------------------------- | --------------------------- | --------------- | ----------------- |
| 交易 audit log                  | `/prod/checkout-api/audit`  | 2555 天（7 年） | Infrequent Access |
| Application operational log     | `/prod/checkout-api/app`    | 30 天           | Standard          |
| Access log（ALB / API Gateway） | `/prod/checkout-api/access` | 90 天           | Standard          |

Audit log group 的額外治理：

- **IAM 權限分離**：audit log group 的讀取權限（`logs:GetLogEvents`）限縮到 compliance team 跟 security team，application developer 只能讀 operational log group。避免 audit log 被隨意查詢或汙染
- **Immutability**：CloudWatch Logs 本身不支援 WORM（write once read many），合規要求 immutable 存檔時用 subscription filter 把 audit log 同步送到 S3 + Object Lock
- **Cross-account 集中**：audit log 的 cross-account aggregation（見下方段落）的 IAM 權限要比 operational log 嚴格 — aggregated sink 的 destination 只能由 security team 控制

### Infrequent Access log class

CloudWatch Logs 提供兩種 log class：**Standard**（完整查詢、即時 subscription filter、metric filter）跟 **Infrequent Access**（僅支援 Logs Insights 查詢、不支援即時 subscription filter 跟 metric filter、ingestion 成本約降 50%）。

Audit log 的存取模式通常是「寫入頻繁、查詢極少（只在稽核或事故時才查）」— 正好符合 Infrequent Access 的定位。把 7 年 retention 的 audit log group 設成 Infrequent Access，ingestion 成本直接砍半。

注意 Infrequent Access 的限制：不能用 subscription filter 即時轉發到 Lambda 或 Kinesis，不能用 metric filter 從 log 產生 CloudWatch metric。如果 audit log 需要即時異常偵測（例如偵測大量失敗交易），要用 Standard class + subscription filter 做即時處理、再用 Lambda 寫到長期 audit log group（Infrequent Access）。

### 自動化套用

用 AWS Config rule 或 CloudFormation / CDK 的 log group 定義統一設定 retention。Lambda function 自動建立的 log group 不會自動套用 retention，需要額外自動化（Lambda post-hook 或 EventBridge rule + Lambda 設定 retention）。

## Cross-account log aggregation

### 架構模式

多帳號環境下，常見做法是設立一個「觀測帳號」（observability account），把其他帳號的 logs 匯入。

兩種匯入方式：

**Subscription filter + Kinesis Data Firehose**：每個 source 帳號的 log group 設 subscription filter，把 log event 送到 observability 帳號的 Kinesis Data Firehose，再寫到 S3 或 OpenSearch。適合需要長期存檔或進階查詢的場景。

**CloudWatch cross-account observability**：AWS 原生功能，在 monitoring account 直接查詢 source accounts 的 CloudWatch 資料（metrics、logs、traces）。設定較簡單，但查詢延遲較高，且 Logs Insights 的 cross-account 查詢有 region 限制。

| 匯入方式                       | 適合場景                                       | 限制                                         |
| ------------------------------ | ---------------------------------------------- | -------------------------------------------- |
| Subscription filter + Firehose | 需要 S3 archive、OpenSearch 全文搜尋、離線分析 | 每個 log group 最多 2 個 subscription filter |
| Cross-account observability    | 只需要 CloudWatch console 統一查詢             | 同 region 限制、查詢延遲較高                 |

### Subscription filter 實務

Subscription filter 可以把 log event 送到 Lambda（即時處理）、Kinesis Data Stream（緩衝）、Kinesis Data Firehose（直接寫 S3/OpenSearch）或另一個 log group。

每個 log group 最多 2 個 subscription filter — 這是硬限制。如果同一個 log group 需要同時送 S3 archive 跟即時 alerting，要用 Kinesis Data Stream 做 fan-out，讓 stream 下游各自消費。

filter pattern 語法支援 JSON 欄位匹配：

```text
{ $.level = "ERROR" }
```

只把 ERROR 級別的 log 送到 alerting pipeline，可以大幅降低下游處理量跟成本。

## Cost governance

### 計費結構

CloudWatch Logs 的成本由三個維度組成：

| 計費項目               | 計費方式           | 常見比例      |
| ---------------------- | ------------------ | ------------- |
| Ingestion              | 每 GB ingested     | 通常佔 50-70% |
| Storage                | 每 GB-month stored | 通常佔 20-40% |
| Query（Logs Insights） | 每 GB scanned      | 通常佔 5-15%  |

Ingestion 是最大成本。降低 ingestion 的手段：

- **調整 log level**：production 只保留 INFO 以上，DEBUG 只在問題排查時短暫開啟
- **去除重複資訊**：access log 跟 application log 不要記錄相同欄位
- **用 metric filter 替代 log query**：高頻計數（error count、request count）用 CloudWatch Metric Filter 從 log 產生 metric，查詢成本從 log scan 轉成 metric query

### 成本觀測

用 CloudWatch 自己的 metric 觀測 log 成本：

- `IncomingBytes`（per log group）：監控哪個 log group ingestion 最大
- `IncomingLogEvents`（per log group）：監控 event 數量
- AWS Cost Explorer 按 CloudWatch 拆分：看 log ingestion vs storage vs API call 的比例

### 降本決策樹

判斷成本是否合理的順序：

1. 最大 ingestion 的 log group 是哪個？是否合理（核心服務的 access log 量大是正常的）
2. Retention 是否都有設定？未設定的 log group 會持續累積 storage 成本
3. 是否有 DEBUG 級別 log 在 production 長期開啟？
4. 是否有 subscription filter 把全量 log 送到外部？能否加 filter pattern 只送需要的部分

## 整合與下一步

- 觀測管線整合：CloudWatch Logs → Subscription Filter → Kinesis Firehose → S3 / OpenSearch，見 [4.11 Telemetry Pipeline](/backend/04-observability/telemetry-pipeline/)
- Audit log 治理：合規場景的 log retention 跟 access control，見 [4.12 Audit Log Governance](/backend/04-observability/audit-log-governance/)
- Evidence package：把 Logs Insights query link 跟時間窗放進 evidence，見 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
- OTel 整合：ADOT 可以把 log 送到 CloudWatch Logs 或其他 backend，見 [OpenTelemetry Collector 部署模式](/backend/04-observability/vendors/opentelemetry/collector-deployment-patterns/)
