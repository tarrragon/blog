---
title: "CloudWatch Alarms 與 Composite Alarms 操作實務"
date: 2026-06-22
description: "說明 CloudWatch Metric Alarm、Anomaly Detection alarm、Composite Alarm 設計、alarm actions、missing data 處理與 cost 考量"
weight: 11
tags: ["backend", "observability", "cloudwatch", "alarm", "alerting"]
---

> 本文是 [AWS CloudWatch](/backend/04-observability/vendors/aws-cloudwatch/) 的 vendor deep article，深化 overview「Alarm + Composite alarm + EventBridge rule」段。初次接觸 CloudWatch 的讀者建議先讀 [CloudWatch 服務頁](/backend/04-observability/vendors/aws-cloudwatch/)。

## 問題情境

CloudWatch Alarm 是 AWS 原生的告警機制，跟 Prometheus Alertmanager 或 Datadog Monitor 的定位相同 — 把 metric 異常轉成可操作通知。CloudWatch Alarm 的特性是跟 AWS 服務深度整合（Auto Scaling、SNS、Lambda、Systems Manager），但告警邏輯表達力比 PromQL alerting rule 弱。Composite Alarm 是 CloudWatch 用來降低 alert noise 的方式，把多個 alarm 的布林組合當成觸發條件。

## Metric Alarm 基礎

### Alarm 參數

每個 metric alarm 由五個參數決定行為：

| 參數               | 說明                                                   | 常見設定                                  |
| ------------------ | ------------------------------------------------------ | ----------------------------------------- |
| Metric             | 要監控的 metric（namespace + metric name + dimension） | `AWS/EC2 CPUUtilization InstanceId=i-xxx` |
| Statistic          | 聚合方式（Average / Sum / Maximum / Minimum / p99）    | 根據 metric 性質選擇                      |
| Period             | 每個 data point 的時間窗                               | 60s（standard）/ 10s（high-resolution）   |
| Evaluation periods | 連續幾個 period 超過閾值才觸發                         | 3-5 個 period 減少 flapping               |
| Threshold          | 觸發閾值                                               | 跟 SLO 對齊                               |

Evaluation periods 的意義是「連續 N 個 period 都違反閾值才進入 ALARM 狀態」。設太低（1 個 period）容易 flapping，設太高（10 個 period）會延遲告警。多數場景 3 個 period × 60 秒 = 3 分鐘是合理起點。

### Datapoints to Alarm

除了 evaluation periods，CloudWatch 還有 `Datapoints to Alarm` 參數 — 在 evaluation periods 的窗口中，至少幾個 datapoint 超過閾值就觸發。例如 `3 of 5` 代表最近 5 個 period 中有 3 個超過閾值就觸發。

這個設計讓告警在有缺失 datapoint 的環境下更穩健。容器重啟、Lambda cold start 或 scrape timeout 都可能造成某些 period 沒有 datapoint，`M of N` 模式避免因為缺失資料而延遲告警。

## Anomaly Detection Alarm

### 用途

Anomaly Detection alarm 用機器學習模型建立 metric 的 baseline band，metric 偏離 band 就觸發。適合沒有固定閾值的 metric — 例如 request count 在白天高、晚上低，用固定閾值會在晚上誤報或白天漏報。

### 設定

```bash
aws cloudwatch put-anomaly-detector \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=app/my-alb/xxx \
  --stat Sum
```

Anomaly Detection 需要至少兩週的歷史資料才能建立可靠 baseline。新服務上線初期先用固定閾值 alarm，等累積足夠資料後再切換。

### Band width 控制

Anomaly Detection band 的寬度用標準差倍數控制（預設 2）。band 太窄（1x）容易誤報，太寬（3x）漏報。生產經驗是 API latency 用 2x、batch job duration 用 3x（batch 的自然波動較大）。

## Composite Alarm

### 問題：Alert noise

單一 metric alarm 太多時，on-call 會收到大量相關但重複的通知。一個下游服務故障可能同時觸發 latency alarm、error rate alarm、timeout alarm、queue lag alarm — 都指向同一個根因，但各自通知。

### 解法：布林組合

Composite Alarm 用布林表達式組合多個 alarm，只在組合條件成立時觸發。

```text
ALARM("checkout-latency-high")
AND ALARM("payment-error-rate-high")
AND NOT ALARM("scheduled-maintenance-window")
```

這個組合代表：checkout latency 高且 payment error rate 也高，但排除了計畫維護視窗 — 才通知 on-call。

### 設計原則

Composite Alarm 的設計應該反映事故判讀邏輯，而非機械式組合。三個常見模式：

**Symptom + cause 組合**：外部症狀（latency 高）加上內部原因（DB connection pool 飽和）同時成立才通知。避免 latency 短暫抖動就告警。

**Cross-service correlation**：多個服務同時出現異常時觸發「可能是 shared dependency 問題」的 composite alarm。一個服務異常可能是部署問題，多個同時異常更可能是共用依賴（load balancer、DNS、shared database）。

**Suppression window**：用 maintenance window alarm 做 NOT 條件，在計畫維護期間抑制告警。

### 限制

- Composite Alarm 最多引用 5 個 child alarm
- 巢狀深度最多 1 層（composite 不能引用另一個 composite）
- Composite Alarm 本身不產生 metric，只做觸發邏輯

超過 5 個 child alarm 時，需要把相關 alarm 先組成一個 composite，再讓上層 composite 引用。但因為不支援巢狀，實際能組合的 alarm 數量有限。複雜告警邏輯需要用 EventBridge rule 搭配 Lambda 處理。

## Alarm actions

### 常見 action 類型

Alarm 進入 ALARM 狀態時可以觸發多種 action：

| Action 類型             | 用途                                              | 設定方式                                     |
| ----------------------- | ------------------------------------------------- | -------------------------------------------- |
| SNS Topic               | 通知 on-call（email、SMS、PagerDuty integration） | alarm action → SNS ARN                       |
| Auto Scaling policy     | 自動擴容                                          | alarm action → scaling policy ARN            |
| Lambda function         | 自訂邏輯（建 ticket、關閉服務、修改 config）      | alarm action → Lambda ARN（透過 SNS）        |
| Systems Manager runbook | 自動執行 remediation runbook                      | alarm action → SSM automation ARN            |
| EC2 action              | 停止 / 重啟 / 終止 instance                       | alarm action → EC2 action（僅限 EC2 metric） |

生產環境通常同時設定 ALARM 跟 OK action — ALARM 時通知 on-call，回到 OK 時自動 resolve incident。忘記設 OK action 會造成 on-call 收到告警但不知道何時恢復。

### 跟 EventBridge 整合

CloudWatch Alarm 狀態變更會自動送到 EventBridge（事件類型 `CloudWatch Alarm State Change`）。EventBridge rule 可以做更靈活的路由：

- 根據 alarm name pattern 路由到不同 SNS topic
- 根據 alarm description 中的 severity tag 決定通知管道
- 多個 alarm 同時進入 ALARM 時觸發 incident 建立

EventBridge 的路由能力彌補了 CloudWatch Alarm 本身路由邏輯簡單的限制。

## Missing data 處理

### 四種策略

Alarm evaluation 遇到缺失 datapoint 時，有四種處理方式：

| 策略           | 行為           | 適合場景                                    |
| -------------- | -------------- | ------------------------------------------- |
| `missing`      | 維持上一個狀態 | 多數場景的預設選擇                          |
| `breaching`    | 視為超過閾值   | metric 消失本身就是問題（heartbeat metric） |
| `notBreaching` | 視為正常       | metric 在低流量時段自然消失                 |
| `ignore`       | 跳過該 period  | 不影響 evaluation window                    |

`breaching` 適合 heartbeat 類型的 metric — 服務應該持續回報 metric，停止回報代表服務掛了。`notBreaching` 適合流量驅動的 metric — 凌晨沒有 request 時自然沒有 latency datapoint，不應該觸發告警。

選錯 missing data 策略是 alarm flapping 的常見原因。Lambda function 的 metric 在沒有 invocation 時沒有 datapoint，用預設的 `missing` 或 `breaching` 都會造成問題。Lambda metric alarm 應該用 `notBreaching`。

## Cross-region 限制

CloudWatch Alarm 跟 metric 綁定在同一個 region。跨 region 告警的兩種方式：

**Cross-account observability**：monitoring account 可以看到 source account 的 CloudWatch 資料，但 alarm 仍然必須建在 metric 所在的 region。

**Custom metric replication**：用 Lambda 或 Kinesis 把 metric 從 source region publish 到 central region，在 central region 建立統一 alarm。增加複雜度跟延遲，但能集中管理告警。

多數團隊選擇在每個 region 建各自的 alarm，用統一的 SNS topic（跨 region publish 到 central topic）收斂通知。告警邏輯去中心化，通知管道集中化。

## Cost 考量

CloudWatch Alarm 的主要成本來自：

| 計費項目                     | 計費方式                          | 常見數量                |
| ---------------------------- | --------------------------------- | ----------------------- |
| Standard resolution alarm    | 每 alarm / month                  | 多數服務 10-50 個 alarm |
| High-resolution alarm（10s） | 每 alarm / month（3 倍 standard） | 只用在關鍵 SLI          |
| Anomaly Detection alarm      | 每 alarm / month（含 ML 模型）    | 比 standard 貴約 2-3 倍 |
| Composite Alarm              | 免費                              | 只算 child alarm        |

數量控制的判準：每個服務 10-30 個 metric alarm 加 2-5 個 composite alarm 是合理範圍。超過 100 個 alarm 時先檢查是否有冗餘（同一 metric 不同 period 的重複 alarm）。

## 整合與下一步

- 告警設計原則：alarm 跟 dashboard 的搭配，見 [4.4 Dashboard 與 Alert 設計](/backend/04-observability/dashboard-alert/)
- SLI/SLO 對齊：把 alarm 閾值跟 SLO 對齊，見 [4.6 SLI 量測與 SLO 訊號設計](/backend/04-observability/sli-slo-signal/)
- Log-based alerting：從 log 產生 metric 再建 alarm，見 [CloudWatch Logs Insights 查詢與日誌治理](../logs-insights-governance/)
- 事故響應整合：alarm → EventBridge → PagerDuty / incident tool，見 [08 Incident Response 模組](/backend/08-incident-response/)
