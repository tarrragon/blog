---
title: "可觀測性與 log 同生命週期管理"
date: 2026-06-26
description: "log group、metric、alarm 寫進建立資源的同一套 IaC，讓監控跟資源同生共滅，出事時追得到查得到"
weight: 1
tags: ["infra", "observability", "logging", "alarm"]
---

可觀測性要跟它監控的資源同生命週期：log group、metric 與 alarm 寫進建立資源的同一套 IaC，資源開出來的那一刻監控就在線，而非等出事才補。這條規則的責任是讓基礎設施在出事時可被追查、在日常時可被量化，而它的建立與銷毀和被監控的資源綁在一起，則保證監控的覆蓋率不會隨時間衰退。

沒有同生命週期管理時，新服務上線後的監控覆蓋率取決於有沒有人記得手動建立 log group 和 alarm，而這個記憶在服務數量增長後會衰退。監控缺口在平時不被注意，在事故排查時才浮現 — 需要回溯「什麼時候開始劣化」時，可能發現劣化期間根本沒有對應的 metric 資料。

## 同生命週期的落地方式

可觀測性是基礎設施的一部分，它的建立、變更與銷毀要跟被監控的資源綁在同一個 apply 單位裡。一個 RDS 實例被 IaC 建立時，它的 log group、它的關鍵 metric alarm 應該在同一份 `terraform plan` 裡一起出現；這個資源被 destroy 時，對應的 alarm 也一起收掉。

落地方式是把監控宣告收進服務的 module。[模組四（環境分離與模組化）](/infra/04-environment-separation/)談的模組化在這裡延伸成「每個服務模組自帶它的 observability 宣告」。一個 database module 內部除了 `aws_db_instance`，還包含它的 log group、CPU alarm、連線數 alarm：

```hcl
# modules/database/monitoring.tf — 跟 database 資源同一個 module
resource "aws_cloudwatch_log_group" "db_slow_query" {
  name              = "/rds/${var.env}/${var.db_identifier}/slowquery"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.log_kms_key_arn
}

resource "aws_cloudwatch_metric_alarm" "db_cpu" {
  alarm_name          = "${var.env}-${var.db_identifier}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_actions       = [var.oncall_sns_arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.primary.identifier
  }
}
```

這樣 `terraform apply` 建資料庫的同一刻，監控就存在；`terraform destroy` 砍資料庫時，孤兒 alarm 也一起清掉。新環境套用同一個 module 時，監控覆蓋率自動跟著資源走，不需要額外的人工記憶。

## 監控脫鉤造成的兩類漂移

把監控外掛在資源之外（用另一份 IaC、另一個 repo、或手動在 console 設定）會製造兩種方向相反的漂移，兩者的共同根因都是監控跟資源不在同一個 apply 單位裡。

### 漂移一：新資源沒有監控

service 透過 PR 加上去了，但 alarm 的建立依賴某人事後手動進 console 設定，或等另一個 repo 的 PR 跟上。於是有些 service 有 alarm、有些沒有，覆蓋率取決於「誰記得」。沒有 alarm 的 service 出事時，事故發現路徑從「告警 → 排查」退化成「客訴 → 排查」，反應時間從分鐘級退化到小時級。

用一條查詢就能看出這個漂移有多嚴重：列出所有 RDS instance，比對各自有沒有對應的 CloudWatch alarm。沒有 alarm 的 instance 就是漂移的活證據。

```bash
# 列出所有 RDS instance，比對有沒有對應的 CloudWatch alarm
aws rds describe-db-instances \
  --query 'DBInstances[].DBInstanceIdentifier' --output text | tr '\t' '\n' | while read db; do
  count=$(aws cloudwatch describe-alarms \
    --alarm-name-prefix "${db}" --query 'MetricAlarms | length(@)')
  echo "${db}: ${count} alarms"
done
```

### 漂移二：死資源留下殘響

資源砍了但 alarm 還在，orphan alarm 對不存在的 target 持續報 `INSUFFICIENT_DATA`，跟有效 alarm 混在同一個通知頻道裡，降低告警的訊噪比。訊噪比低到一定程度後，有效的 `INSUFFICIENT_DATA`（某個服務停止送 metric）也被一起略過 — 告警疲勞讓 alarm 從保護機制退化成背景噪音。

漂移二的成本不只是注意力。殘留的 alarm 會佔用 CloudWatch alarm 的配額（每個帳號有配額上限），大量孤兒 alarm 累積後，新服務要加 alarm 可能需要先清理舊的 — 這在事故當下是最不該花時間的事。

修法是把 alarm 的生命週期綁進 module：資源 destroy 時 alarm 跟著 destroy，不需要另一個流程去「記得清理」。如果因為歷史原因已經有大量孤兒 alarm，可以用 alarm 的 `StateValue` 為 `INSUFFICIENT_DATA` 且持續超過 7 天作為清理候選的篩選條件。

## log group 設計

Log group 是日誌的歸屬與保存單位，它要回答兩個治理問題：留多久（retention）、誰能讀（access control）。這兩個問題寫進 IaC 才能稽核，而非依賴 vendor 的隱性預設。

### Retention：三方取捨

許多雲端服務在沒有明確宣告 log group 時會自動建一個、套上「永久保留」的預設值。永久保留的問題不是技術性的 — CloudWatch Logs 可以存到無限久 — 而是治理性的：日誌無限堆積、帳單緩慢長大，而沒有人做過「這條 log 該留多久」的顯式決定。

Retention 是成本、合規與除錯需求的三方取捨：

| 日誌類型                   | 除錯需求     | 合規需求       | 建議 retention      |
| -------------------------- | ------------ | -------------- | ------------------- |
| 應用 log（request、error） | 近 2-4 週    | 通常無特殊要求 | 14-30 天            |
| 資料庫 slow query log      | 近 1-2 週    | 通常無特殊要求 | 14 天               |
| 存取稽核 log（CloudTrail） | 偶爾回溯     | 1-7 年         | 90-365 天 + 歸檔 S3 |
| 金流 / 交易 log            | 對帳用、偶爾 | 依法規 3-7 年  | 短期保留 + 長期歸檔 |

較合理的做法是按日誌類型分層：高頻、除錯用的 application log 設短 retention，稽核相關的 access log 按合規要求設長期保留，必要時再把冷資料用 subscription filter 歸檔到更便宜的物件儲存（S3 + Glacier）。把這些值寫進 IaC，讓「為什麼這條 log 留 90 天」是一個能在 PR 上被討論的決定，而非某人半年前在 console 點的一個數字。成本參考：CloudWatch Logs 的儲存費用約 $0.03/GB/月。一個每天產生 10GB log 的服務，30 天 retention 的月費約 $9，7 天約 $2。retention 天數的選擇是合規需求（留多久才合規）與儲存成本的直接取捨，可以按 log 類型分層設定。

觀測平台的帳單在規模化後容易超線性成長，而缺乏 per-team cost attribution 的環境只能靠全域砍 retention 或降 sampling 來控制成本，兩者都會傷害觀測品質。把 log retention 跟 cardinality budget 的決定從全域級拆到團隊級（用 tag 歸因），才能做到「該省的省、該留的留」。這個取捨在 [4.C14 觀測平台成本治理](/backend/04-observability/cases/observability-cost-governance-at-scale/) 有多家企業的具體經驗。

```hcl
resource "aws_cloudwatch_log_group" "api" {
  name              = "/app/${var.env}/api"
  retention_in_days = var.env == "prod" ? 30 : 7
  kms_key_id        = aws_kms_key.logs.arn
}

resource "aws_cloudwatch_log_group" "audit" {
  name              = "/app/${var.env}/audit"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.logs.arn
}
```

Dev 環境的 retention 可以大幅縮短（7 天甚至 3 天），因為它不承擔合規責任，存取量也低，帳單節省直接對應這個差值。

### 存取控制與加密

「誰能讀」是 retention 之外的另一半。Log 經常夾帶 PII（使用者信箱、IP）、token 或內部結構，讀取權限要跟[模組二（身分與憑證地基）](/infra/02-identity-credentials/)建立的 IAM 角色一起管。

常見陷阱是 log 在傳輸與儲存都加密了（`kms_key_id` 有設），卻對整個團隊開放讀取。加密保護的是靜態資料不被未授權存取，但如果整個開發團隊都有 `logs:GetLogEvents` 權限，加密形同虛設 — read 權限應該縮到值班與稽核需要的最小集合。

```hcl
# 只允許 oncall role 讀取 prod log
data "aws_iam_policy_document" "log_read" {
  statement {
    actions   = ["logs:GetLogEvents", "logs:FilterLogEvents"]
    resources = [aws_cloudwatch_log_group.api.arn]
  }
}

resource "aws_iam_role_policy" "oncall_log_read" {
  role   = var.oncall_role_name
  policy = data.aws_iam_policy_document.log_read.json
}
```

應用層該怎麼決定哪些欄位根本不該進 log（例如在 logger 層做 PII masking），屬於資料保護的範圍，見 [backend 模組七：資安與資料保護](/backend/07-security-data-protection/)。

## metric 與 alarm 設計

Metric 與 alarm 寫進 IaC，目的是讓「資源被建立的同時就帶著它的健康判準」。Alarm 是一份成文約定：哪條 metric、跨多長的評估窗口、超過什麼值要通知誰。把這份約定寫進 code，它就能被 review、被版本控制、被跨環境複用。

### 症狀型 vs 成因型告警

閾值設計是訊號與雜訊的取捨。告警可以分成兩類：症狀型（symptom-based）對應的是「使用者已經受影響」的指標 — 5xx 錯誤率、p99 延遲、佇列積壓。成因型（cause-based）對應的是「某個元件在劣化但使用者可能還沒感知」的指標 — CPU 使用率、記憶體使用率、磁碟 IOPS。

收益最高的起點是：症狀型設 alarm 並綁通知，成因型留在 dashboard 上作為診斷線索。理由是成因和症狀之間不一定有直接關係 — CPU 在 80% 不代表使用者受影響（可能 auto-scaling 正在長新節點），而 CPU 在 30% 也不代表安全（可能是某個 goroutine 卡住了，CPU 反而閒下來）。如果每個成因指標都獨立設 alarm，告警數量會與資源數量等比增長，訊噪比下降後症狀型告警容易被成因型告警淹沒。

```hcl
# 症狀型 alarm：5xx 超過閾值代表使用者已受影響
resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name          = "${var.env}-api-5xx-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"
  alarm_actions       = [var.oncall_sns_arn]
}

# 成因型指標：CPU 放 dashboard、不設 alarm
# 除非確認「CPU 到 X% 一定代表服務即將不可用」這個因果關係
```

當成因和症狀之間有明確的因果閾值（例如 RDS 磁碟用量到 90% 就會開始拒絕寫入），那條成因也值得設 alarm — 關鍵是因果關係要確認過、而非假設。

### INSUFFICIENT_DATA 的處理

`treat_missing_data` 決定了「沒收到 metric 資料點」時 alarm 怎麼判定。這個設定常被忽略，但它在兩個情境下會造成顯著差異：

**持續有資料的 metric**（如 API request count）：資料突然消失通常代表服務掛了或 metric 管線斷了，應該設 `treat_missing_data = "breaching"` — 沒資料本身就是異常訊號。

**間歇性的 metric**（如錯誤 count、某個低頻 Lambda 的 invocation）：平常就沒有資料點，沒資料代表正常運作，應該設 `treat_missing_data = "notBreaching"` — 避免每次低谷時段都觸發假告警。

判讀方式是問自己：「這條 metric 如果 10 分鐘沒有任何資料，代表好事還是壞事？」好事用 `notBreaching`，壞事用 `breaching`，不確定用 `ignore`（不改變 alarm 狀態，等下一個有資料的評估週期再判定）。

### 告警必須連到動作

一條有用的 alarm 至少要綁定通知去向。`alarm_actions` 為空的 alarm 只會在 CloudWatch console 裡變色，而事故發生時沒有人會盯著 console 看 — alarm 的價值在於它主動推送到值班的人手上。

```hcl
resource "aws_sns_topic" "oncall" {
  name = "${var.env}-oncall-alerts"
}

resource "aws_sns_topic_subscription" "pagerduty" {
  topic_arn = aws_sns_topic.oncall.arn
  protocol  = "https"
  endpoint  = var.pagerduty_integration_url
}
```

通知去向也該寫進 IaC — SNS topic、subscription、整合端點都是基礎設施的一部分。手動建的 SNS subscription 跟手動建的 alarm 有同樣的問題：沒人記得、沒人維護、出事才發現斷了。

### 把基礎告警做成 module 預設

如果每次新服務上線都要有人「記得」去加 alarm，代表 alarm 還沒進 module 模板。把基礎告警（錯誤率、延遲、健康檢查失敗）做成服務模組的預設輸出，新服務 apply 時 alarm 跟著一起生出來：

```hcl
# modules/service/variables.tf
variable "alarm_5xx_threshold" {
  type    = number
  default = 10
}

variable "alarm_latency_p99_ms" {
  type    = number
  default = 3000
}
```

開新服務時 alarm 跟著資源一起生出來，調整閾值才是該服務 owner 的選配。預設值的選擇依據是「保守但不擾民」— 初始閾值設寬一點，上線穩定後再根據實際基線收斂。

觀測訊號的設計有一個容易忽略的盲區：aggregated metric 會遮蔽局部惡化。Discord 在三代儲存架構的遷移過程中反覆遇到同一個問題——整體 p95 延遲正常，但少數 hot partition 或大型群組的延遲已經飆升，直到使用者回報才發現。教訓是 alarm 的維度要跟業務的 fan-out 結構對齊，而非只看全域聚合。詳見 [4.C13 Discord：從儲存問題回推觀測缺口](/backend/04-observability/cases/discord-storage-growth-observability-gap/)。規模化後叢集的動態擴縮也會改變觀測模型——擴縮事件本身要成為觀測對象，見 [4.C8 Airbnb：K8s 規模化觀測訊號治理](/backend/04-observability/cases/airbnb-observability-k8s-scale-signals/)。

## 基礎設施訊號 vs 客戶端行為訊號

本模組的可觀測性處理基礎設施訊號，[Monitoring 監控體系](/monitoring/)處理客戶端與業務行為訊號。兩者觀測的對象不同、生命週期也不同，因此分屬不同的 code 與不同的部署管道。

基礎設施訊號是資源層的健康狀態：log group retention、CPU、佇列深度、5xx 比例、實例存活。它們跟著資源被 IaC 建立與銷毀，回答的問題是「這個系統還活著嗎、哪裡壞了」。

客戶端行為訊號則是 SDK、Collector、業務埋點那一層：使用者點了什麼、轉換漏斗在哪裡流失、前端 JS 錯誤率、自訂業務事件。它們跟著產品功能演進、不跟著基礎設施資源同生共滅。

判讀分界的問法是：這個訊號是「資源建立時就該存在」還是「功能開發時才埋」。前者進本模組的 IaC，後者進 monitoring 那層的應用程式碼。

兩者在事故排查時會合流 — 基礎設施 alarm 告訴值班「RDS CPU 飆到 95%」，客戶端訊號告訴產品團隊「結帳頁面的失敗率從 0.1% 跳到 12%」。把兩條訊號交叉比對才能判斷影響範圍。但它們的擁有者、變更節奏與部署管道不同 — 基礎設施 alarm 跟著 infra PR 走，前端埋點跟著產品 sprint 走。混在同一份 code 裡會讓「誰負責這條訊號的閾值」變模糊，也讓 infra PR 的 review 範圍擴大到不相干的業務邏輯。

## 跨分類引用

- → [monitoring 監控體系](/monitoring/)：客戶端 SDK / Collector 那層的監控
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：module 化在這裡延伸成「每個模組自帶 observability 宣告」
- → [模組五：核心服務上 IaC](/infra/05-core-services/)：每個核心服務帶自己的 log 與 alarm
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：observability 變更也走 PR 與自動化護欄
- → [backend 模組七：資安與資料保護](/backend/07-security-data-protection/)：哪些欄位不該進 log、PII 處理
