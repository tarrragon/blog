---
title: "4.14 Anomaly Detection"
date: 2026-06-22
description: "把 ML / statistical baseline 訊號跟 rule-based alert 整合"
weight: 14
tags: ["backend", "observability"]
---

## 大綱

- Anomaly detection 跟 rule-based alert 的分工
- Baseline 模型類別
- Anomaly 訊號的處理路徑
- False positive 與 alert noise 共用預算
- Explainability：anomaly 要能定位到維度
- Vendor 定位
- 反模式

## 概念定位

Anomaly detection 是用統計基線或模型找出偏離常態的訊號，責任是補上 rule-based alert 難以事先列舉的變化。

Rule-based alert 抓已知模式 — 團隊事先定義「error rate > 1% 就告警」。Anomaly detection 抓未知模式 — 系統觀察到「今天的 latency 分布跟過去 30 天的同時段不同」。兩者互補：rule-based 精確但只能抓團隊已預見的問題，anomaly detection 有噪音但能發現團隊沒想到的退化。

Anomaly 適合作為提示層（hint），通常先進 dashboard 或低 severity 路由，再由 SLO 判讀或人工確認決定是否升級。把 anomaly 直接接 page 是噪音爆量的常見原因。

## 跟 Rule-based Alert 的分工

| 面向            | Rule-based alert         | Anomaly detection                   |
| --------------- | ------------------------ | ----------------------------------- |
| 觸發條件        | 固定閾值或 burn rate     | 偏離統計基線                        |
| 抓什麼          | 已知模式（團隊事先定義） | 未知模式（歷史基線判斷）            |
| 精確度          | 高（閾值明確）           | 低到中（統計偏差 = 候選，需要確認） |
| False positive  | 閾值對齊時低             | 較高（季節性未建模、促銷、release） |
| 適合的 severity | Critical / Warning       | Info / Warning（確認後才升級）      |
| 維護成本        | 隨服務變化需調整閾值     | 模型要持續 retrain 或校正           |

最有效的整合方式：rule-based alert 處理已知的 SLO violation（symptom-based、高 severity），anomaly detection 處理趨勢異常跟 novel failure mode（低 severity、dashboard widget）。兩者共用 [alert fatigue](/backend/knowledge-cards/alert-fatigue/) 的 noise budget — anomaly 的 false positive 也算進整體 noise rate。

## Baseline 模型類別

### Seasonal baseline

按日夜、週末、節慶、促銷等週期建立基線。同一個指標的「正常範圍」在週一上午跟週日凌晨不同。Seasonal model 用歷史同期資料建立預期帶（expected band），偏離帶外視為 anomaly。

Seasonal baseline 的失敗模式是週期性假設錯誤 — 業務改變後流量模式跟歷史不同（新產品上線改變了週末流量），模型用錯誤的基線判斷。需要定期驗證模型跟實際流量的吻合度。

### Moving window baseline

用過去 N 分鐘 / 小時的資料建立動態基線。比 seasonal model 簡單、延遲更低，但對突發變化更敏感（release 後 latency 自然變化可能觸發 anomaly）。

Moving window 適合不需要週期性建模的指標 — 連線數、queue depth、goroutine count 等「預期穩定、突變代表問題」的指標。

### ML-based（forecast / clustering）

用機器學習模型做時間序列預測（Prophet、ARIMA）或高維度聚類（isolation forest、DBSCAN）。能處理複雜的多變量異常（A 指標上升 + B 指標下降 = 異常，但各自單獨看都在正常範圍）。

ML 模型的成本是訓練、retrain、模型版本管理跟 explainability。多數團隊的起步方式是先用 seasonal + moving window（不需要 ML pipeline），等 false positive 管理穩定後再引入 ML。

## Anomaly 訊號的處理路徑

Anomaly detection 的輸出是「這個指標在這段時間偏離基線」— 候選訊號，不是確認的問題。處理路徑決定 anomaly 是有用的提示還是噪音來源。

**Dashboard widget**：anomaly 標記在 time series panel 上（標色、annotation），讓巡視 dashboard 的工程師注意到。低成本、零噪音（不通知任何人）、但需要有人主動看。

**Low severity alert（info / warning）**：anomaly 進入 alerting pipeline，但 severity 設為 info 或 warning。不 page on-call、但記錄在 alert history 中。事故發生後可以回溯「事故前有沒有 anomaly 提早預警」。

**Conditional escalation**：anomaly 搭配 rule-based 條件升級。「Latency 偏離基線 + error rate 超過 SLO [burn rate](/backend/knowledge-cards/burn-rate/)」→ 升級為 critical。單獨的 anomaly 不足以 page，但跟其他訊號組合時有判讀價值。

## Explainability

Anomaly 觸發時，工程師需要回答「為什麼異常」 — 是哪個服務、哪個 endpoint、哪個 tenant、哪個地區導致的。只告訴你「overall latency 異常」但不說維度，診斷價值有限。

可操作的 explainability 有兩層：

**維度歸因**：anomaly detection 系統自動拆分異常到子維度 — 「overall latency 異常，主要來自 region=us-east + endpoint=/api/search」。Datadog Watchdog 跟 New Relic AI 提供這種維度下鑽能力。

**Root cause hint**：anomaly 跟其他訊號（deploy event、config change、dependency error spike）的時間關聯。「Latency anomaly 開始的時間跟 v2.3.1 deploy 吻合」— 提示 root cause 可能跟 deploy 有關。

## Vendor 定位

| Vendor           | 定位                              | 特點                                    |
| ---------------- | --------------------------------- | --------------------------------------- |
| Datadog Watchdog | 託管 anomaly + 維度歸因           | 跟 APM / log / metric 整合、auto-detect |
| New Relic AI     | 託管 anomaly + root cause suggest | 全棧觀測整合                            |
| Prophet（自建）  | 開源 time series forecast         | 需要自建 pipeline、training、serving    |
| Anomalo          | 資料品質 anomaly                  | 偏 data pipeline、非 infra 觀測         |

自建 vs 託管的判準：團隊是否有 ML pipeline 維運能力。託管方案的好處是零 ML 運維、跟觀測平台深度整合；自建的好處是可控性高、可以針對業務邏輯客製模型。

## 核心判讀

Anomaly detection 最常見的失敗是 baseline 沒對齊流量週期（週末自然下降被判成異常）跟異常觸發後無法歸因到具體維度（只知道「latency 異常」但看不出是哪個 service、哪個 region）。

重點訊號包括：

- Baseline 是否理解日夜、週末、節慶與促銷週期
- Anomaly 是否能指出 service、tenant、region 或 endpoint 維度
- False positive 是否納入 alert noise governance
- Anomaly 與 rule-based alert 是否有清楚分工

## 判讀訊號

- Alert 規則寫到數百條、仍漏掉 novel failure mode
- 已知 anomaly 訊號被忽略、靠人工巡視 dashboard
- Anomaly 觸發後無人能解釋「為什麼異常」
- 模型未對齊週期性（週末 / 節慶 / promo）造成噪音
- 同一指標 anomaly + rule alert 重複觸發、無協調

## 反模式

| 反模式                        | 表面現象                                    | 修正方向                                        |
| ----------------------------- | ------------------------------------------- | ----------------------------------------------- |
| Anomaly 直接接 page           | On-call 被統計偏差淹沒                      | Anomaly 先走 info/warning、conditional 才升級   |
| Baseline 沒對齊季節性         | 週末 / 節慶流量自然變化觸發 false positive  | 用 seasonal model 或 exclude 已知事件窗口       |
| Anomaly 跟 rule alert 重複    | 同一問題兩個來源觸發、noise 翻倍            | 共用 noise budget、anomaly 在 rule 已觸發時抑制 |
| 模型不可解釋                  | Anomaly fired 但工程師不知道看什麼          | 要求維度歸因能力、否則只作 dashboard widget     |
| 自建 ML 但無 retrain pipeline | 模型用半年前的 baseline、precision 持續下降 | 建立定期 retrain 或改用託管方案                 |

## 交接路由

- [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/)：anomaly 升級 alert 的條件
- [4.6 SLI/SLO](/backend/04-observability/sli-slo-signal/)：跟 SLO burn rate 的訊號分工
- [4.8 signal governance](/backend/04-observability/signal-governance-loop/)：anomaly false positive 的淘汰
- [4.18 operating model](/backend/04-observability/observability-operating-model/)：anomaly 系統的 ownership
