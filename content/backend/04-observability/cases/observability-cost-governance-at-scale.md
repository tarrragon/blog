---
title: "4.C14 觀測平台成本治理：從帳單驚嚇到可預測成本"
date: 2026-06-22
description: "觀測帳單持續超線性成長時，用 cost attribution、cardinality budget、log tiering 跟 adaptive sampling 建立可預測成本模型。"
weight: 14
tags: ["backend", "observability", "case-study", "cost", "cardinality"]
---

觀測成本治理案例來自多家企業的共同經驗：觀測平台帳單每季成長 30%，管理層問「為什麼監控這麼貴」但沒人能歸因。問題的核心不是「花太多」而是「花在哪不知道」— 沒有 per-team cost attribution 的觀測平台，成本優化只能靠全域砍 retention 或降 sampling，兩者都會傷害觀測品質。

## 業務背景

這個案例綜合三個組織的經驗模式：

一家中型 SaaS 公司用 Datadog 做全端觀測（APM + logs + metrics + RUM）。月帳單從 $15K 成長到 $60K，兩年內四倍。CFO 問 CTO「這筆錢買到什麼」，CTO 轉問 platform team，platform team 說不出哪些團隊佔多少。

一家金融科技公司自建 Grafana Stack（Prometheus + Loki + Tempo + Mimir）。自建沒有 SaaS 帳單，但 Kubernetes 節點跟 storage 的成本持續增加。infra team 知道 Mimir 的 storage 在成長，但不知道是哪些 metric label 造成的 cardinality 爆炸。

一家遊戲公司用 CloudWatch 做 AWS 原生觀測。Logs 的 ingestion 費用佔帳單 70%，但追查後發現 90% 是 debug-level log，只在排錯時用到，平常沒人查。

## 技術挑戰

### 沒有 cost attribution

觀測帳單通常是 organization-level 的一筆支出。SaaS 帳單按 hosts、custom metrics、log volume、APM spans 計費；自建平台按 compute 跟 storage 計費。兩種模式都缺少「這些費用是哪個 team / service 造成的」的歸因。

沒有 attribution 的後果是所有優化都是全域操作 — 砍 retention 從 30 天到 7 天影響所有人，降 sampling 從 100% 到 10% 影響所有服務。需要觀測資料的團隊被平均到成本節省裡，不需要的團隊搭便車。

### Cardinality 爆炸

Metrics 成本的主要 driver 是 cardinality — unique label combination 的數量。常見的 cardinality 爆炸來源：

- 把 user ID 或 request ID 放進 metric label（每個 unique user 產生一組 series）
- 動態的 endpoint path（`/api/users/123` 每個 user ID 是一個 label value）
- 多租戶 label 過細（tenant × region × service × endpoint 的笛卡兒積）

一個失控的 label 可以讓 series 數量從 10 萬跳到 1000 萬。SaaS 的計費是 per custom metric，自建的代價是 Prometheus / Mimir 的 memory 跟 storage。

### Log volume 失控

Debug-level log 在開發階段有用，但 production 環境裡通常只在排錯時被查。全量 debug log 送進 hot tier（Elasticsearch、Loki、CloudWatch Logs）的 ingestion 跟 storage 成本是最大的 log 成本來源。

問題是沒人敢降 debug log — 「萬一出事需要 debug log 怎麼辦」。恐懼驅動的 log level 設定讓 log volume 只升不降。

### Trace sampling 恐懼

類似的恐懼存在於 trace sampling — 「如果剛好那筆有問題的 request 被 sample 掉怎麼辦」。100% tracing 的成本在中等規模（每秒數萬 request）就開始顯著。

## 解法

### Cost attribution by team / service

第一步是讓成本可見，歸因先於優化。

SaaS 平台：用 Datadog 的 usage attribution 或 Grafana Cloud 的 usage reporting 把 ingestion 按 service tag / team tag 拆分。每個 team 看到自己的 metric series、log volume 跟 span 數量。

自建平台：在 Mimir / Loki 的 tenant 維度或 Prometheus 的 namespace 維度拆分 storage 跟 query cost。用 [4.15 Cost Attribution](/backend/04-observability/cost-attribution/) 的框架把 infra cost 按 service ownership 分配。

Attribution 本身就能驅動行為改變 — 當團隊看到自己佔了 40% 的 log volume、而且 95% 是 debug level 時，他們會主動調 log level。

### Cardinality budget per team

Attribution 之後，為每個 team / service 設定 cardinality budget（active series 上限）。超出 budget 的 series 進入 review 流程 — team 決定哪些 label 可以 aggregate 或移除，而非由 platform 單方面 drop。

Budget 的設定依據是 baseline measurement + growth rate，不是拍腦袋。先觀察 3 個月的 cardinality 趨勢，把 budget 設在 baseline 的 1.5 倍，每季 review。

### Log tiering

把 log 從「全部進 hot tier」改成分層：

| Log level    | 目的地                           | Retention | 查詢延遲   |
| ------------ | -------------------------------- | --------- | ---------- |
| Error / Warn | Hot tier（Loki / Elasticsearch） | 30 天     | 即時       |
| Info         | Warm tier（壓縮 + 延遲查詢）     | 14 天     | 秒到分鐘   |
| Debug        | Cold archive（object storage）   | 7 天      | 分鐘到小時 |

Debug log 仍然保留，但不進昂貴的 hot tier。需要排錯時從 cold archive 拉回 — 多等幾分鐘的代價遠低於全量 hot tier 的持續成本。

### Adaptive sampling

Trace sampling 從 uniform 改成 adaptive：

- 錯誤 request 100% 保留
- 高 latency request（> p99）100% 保留
- 正常 request 依 traffic volume adaptive sampling（高流量 endpoint 低 sample rate、低流量 endpoint 高 sample rate）

Adaptive sampling 保留了排錯最需要的 trace（error 跟 outlier），砍的是正常 request 的重複 trace。

## 取捨

| 面向       | 不治理                                  | 治理後                                                    |
| ---------- | --------------------------------------- | --------------------------------------------------------- |
| 成本趨勢   | 隨 traffic 超線性成長                   | 跟 traffic 線性成長或低於線性                             |
| 觀測覆蓋   | 全量（但可能是低品質的全量）            | 分層（high-value 資料保留全量、low-value 降級）           |
| Debug 體驗 | 所有資料都在 hot tier、查得快           | 部分資料要從 cold archive 拉、多等幾分鐘                  |
| 團隊自主性 | 無限制（cardinality 跟 log level 隨意） | 有 budget 跟 policy 約束                                  |
| 治理人力   | 零（直到帳單爆炸才開始）                | 需要 platform team 持續維護 attribution + budget + policy |

治理的最大風險是「砍過頭」— 在事故期間發現 debug log 被移到 cold archive 查不到、或 trace 被 sample 掉找不到問題 request。Adaptive sampling 跟 error retention 100% 是安全網，但安全網的設計本身需要定期 review（例如 error 的定義是否涵蓋了所有異常模式）。

## 回寫教材的連結

- [4.15 Cost Attribution](/backend/04-observability/cost-attribution/)：per-team cost visibility 是治理的起點。
- [4.7 Cardinality 治理](/backend/04-observability/cardinality-cost-governance/)：cardinality budget 跟 label review 的操作流程。
- [4.11 Telemetry Pipeline](/backend/04-observability/telemetry-pipeline/)：log tiering 跟 adaptive sampling 是 pipeline 的 routing 跟 processing 層配置。

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- 觀測帳單每季成長 > 20%，但服務的 request volume 成長遠小於此 — cardinality 或 log volume 可能在失控成長
- 管理層問「監控花多少錢、誰在用」但沒人能回答
- 曾經做過「全域降 retention」或「全域降 sampling」的成本優化，但幾個月後成本回升
- Platform team 花大量時間處理「Prometheus OOM」或「Elasticsearch disk full」而非改善觀測品質
- 團隊的 debug log level 在 production 預設開著，理由是「不知道什麼時候需要」
