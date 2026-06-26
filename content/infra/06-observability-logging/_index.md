---
title: "模組六：可觀測性與 log 一併寫進 code"
date: 2026-06-26
description: "log group、metric、alarm 跟基礎設施同生命週期管理，出事時追得到查得到"
weight: 6
tags: ["infra", "observability", "logging", "alarm"]
---

可觀測性要跟它監控的資源同生命週期：log group、metric 與 alarm 寫進建立資源的同一套 IaC，資源開出來的那一刻監控就在線，而非等出事才補。少了這條規則的代價很具體：凌晨資料庫 CPU 飆到 100%、API 開始逾時，值班工程師打開 console 想看 log，卻發現那個服務根本沒接 log group、metric 也只有 vendor 預設的幾條粗線，追不到呼叫鏈、查不到錯誤訊息，只能靠重啟賭它恢復。

## observability 跟 infra 同一套 code、同生命週期

可觀測性是基礎設施的一部分，承擔「讓資源在出事時可被追查」的責任，因此它的建立、變更與銷毀要跟被監控的資源綁在同一個生命週期裡。一個 RDS 實例、一個 Lambda、一個 ECS service 被 IaC 建立時，它的 log group、它的關鍵 metric alarm 應該在同一份 plan 裡一起 apply；這個資源被 destroy 時，對應的 alarm 也一起收掉，不留下對著空資源狂叫的孤兒告警。

把監控外掛在資源之外會製造兩種漂移。第一種是新資源沒有監控：service 透過 PR 加上去了，但 alarm 要某人事後手動進 console 點，於是有些 service 有 alarm、有些沒有，覆蓋率取決於誰記得。第二種是死資源留下殘響：資源砍了但 alarm 還在，半夜對著不存在的 target 噴 `INSUFFICIENT_DATA`，值班的人學會忽略它，告警疲勞讓真的事故也被一起忽略。兩種漂移的共同根因都是監控跟資源不在同一個 apply 單位裡。

判讀訊號很直接：如果有人能回答「這個服務有沒有 alarm」要去翻 console 而不是讀 code，監控就已經跟資源脫鉤了。修法是把監控宣告收進該資源的 module——模組四（環境分離與模組化）談的模組化在這裡延伸成「每個服務模組自帶它的 observability 宣告」，模組五（核心服務上 IaC）談的每個核心服務也應該在同一個 module 裡帶上自己的 log 與 alarm。

## log group 與 retention 設計

Log group 是日誌的歸屬與保存單位，它要回答兩個治理問題：留多久、誰能讀。這兩個問題寫進 IaC 才能稽核，而非依賴 vendor 的隱性預設。許多雲端服務在你沒宣告 log group 時會自動建一個、套上「永久保留」的預設值，於是日誌無限堆積、帳單緩慢長大，而真正敏感的內容反而沒人管控存取。

Retention 是成本、合規與除錯需求的三方取捨。除錯通常只需要近幾天到幾週的熱資料；合規（如稽核軌跡、金流紀錄）可能要求保留數年；而每多留一天就多一天的儲存費。划算的做法是按日誌類型分層：高頻、除錯用的 application log 設短 retention（例如 14 到 30 天），稽核相關的 access log 按合規要求設長期保留，必要時再把冷資料歸檔到更便宜的物件儲存。把這些值寫進 IaC，讓「為什麼這條 log 留 90 天」是一個能在 PR 上被討論的決定。

```hcl
resource "aws_cloudwatch_log_group" "api" {
  name              = "/app/${var.env}/api"
  retention_in_days = var.env == "prod" ? 30 : 7
  kms_key_id        = aws_kms_key.logs.arn
}
```

「誰能讀」是 retention 之外的另一半，因為 log 經常夾帶 PII、token 或內部結構，讀取權限要跟身分地基一起管。存取控制掛在模組二（身分與憑證地基）建立的 IAM 角色上，加密金鑰則對應模組三、模組七一路延伸的金鑰治理。常見陷阱是 log 在傳輸與儲存都加密了，卻對整個團隊開放讀取，等於把敏感資料攤在所有人面前；read 權限應該縮到值班與稽核需要的最小集合。應用層該怎麼決定哪些欄位根本不該進 log，屬於資料保護的範圍，可往 `/backend/07-security-data-protection/` 對齊。

## metric 與 alarm 寫進 IaC

Metric 與 alarm 寫進 IaC，目的是讓「資源被建立的同時就帶著它的健康判準」。Alarm 不只是一個閾值，它是一份對「這個資源什麼狀態算不正常」的成文約定：哪條 metric、跨多長的評估窗口、超過什麼值要通知誰。把這份約定寫進 code，它就能被 review、被版本控制、被跨環境複用，而不是散落在某個人腦中或 console 的某個角落。

Alarm 的價值在於它連到動作，而非只是亮一盞燈。一條有用的 alarm 至少要綁定通知去向（on-call 的 SNS topic、PagerDuty、Slack），並寫清楚 `INSUFFICIENT_DATA` 怎麼處理——資料不足到底算正常還是異常，取決於這條 metric 平常是否持續有資料。閾值設計是訊號與雜訊的取捨：設太敏感會頻繁誤報、養出告警疲勞，設太鈍則錯過真正的劣化。划算的起點是針對「使用者已經受影響」的症狀型 metric 設 alarm（錯誤率、p99 延遲、佇列積壓），而把成因型指標（CPU、記憶體）留作 dashboard 上的診斷線索，避免每個成因都獨立告警。

```hcl
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
  alarm_actions       = [aws_sns_topic.oncall.arn]
}
```

判讀訊號是：每次新服務上線都要有人「記得」去加 alarm，代表 alarm 還沒進 module 模板。修法是把基礎告警（錯誤率、延遲、健康檢查失敗）做成服務模組的預設輸出，讓開新服務時 alarm 跟著資源一起生出來，調整閾值才是該服務 owner 的選配。

## 跟 monitoring 系列的分工：基礎設施訊號 vs 客戶端行為訊號

本模組的可觀測性處理基礎設施訊號，monitoring 系列處理客戶端與業務行為訊號，兩者觀測的對象不同、生命週期也不同，因此分屬不同的 code 與不同的章節。基礎設施訊號是資源層的健康狀態：log group、CPU、佇列深度、5xx 比例、實例存活，它們跟著資源被 IaC 建立與銷毀，回答「這個系統還活著嗎、哪裡壞了」。

客戶端行為訊號則是 SDK、Collector、業務埋點那一層：使用者點了什麼、轉換漏斗、前端錯誤、自訂事件，它們跟著產品功能演進、不跟著基礎設施資源同生共滅，所以放在 `/monitoring/`。判讀分界的問法是：這個訊號是「資源建立時就該存在」還是「功能開發時才埋」。前者進本模組的 IaC，後者進 monitoring 那層的應用程式碼。兩者在事故排查時會合流——基礎設施 alarm 告訴你哪個資源異常，客戶端訊號告訴你使用者實際受了什麼影響——但它們的擁有者、變更節奏與部署管道不同，混在一起會讓「誰負責這條訊號」變模糊。

收斂成一句判準：資源建立時就該存在的訊號歸本模組的 IaC，功能開發時才埋的客戶端行為訊號歸另一層；各條延伸章節見下方跨分類引用。

## 章節文章

| 文章                                                                                         | 主題                                                                              |
| -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| [可觀測性與 log 同生命週期管理](/infra/06-observability-logging/log-metric-alarm-lifecycle/) | log group、metric、alarm 寫進同一套 IaC，讓監控跟資源同生共滅，出事時追得到查得到 |

## 跨分類引用

- → [Monitoring 監控體系](/monitoring/)：客戶端 SDK / Collector 那層的監控
- → [模組五：核心服務上 IaC](/infra/05-core-services/)：每個核心服務帶自己的 log 與 alarm
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：observability 變更也走 PR 與自動化護欄
- → [backend 模組七：資安與資料保護](/backend/07-security-data-protection/)：哪些欄位不該進 log、PII 處理
