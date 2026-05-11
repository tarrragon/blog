---
title: "4.21 Rule-level CPU Signal Governance"
date: 2026-05-07
description: "把規則與策略執行成本變成可觀測訊號，避免控制面小變更在資料面形成 CPU 熱點。"
weight: 21
tags: ["backend", "observability"]
---

Rule-level CPU signal governance 的核心責任是讓規則與策略執行成本可被提前判讀，避免高成本規則在全域 rollout 後才以 5xx 與 latency 形式被動暴露。

## 概念定位

Rule-level CPU signal governance 是把「哪一條規則在吃 CPU」變成可量測、可回退、可治理的觀測能力，責任是補上服務級 CPU 指標看不到的規則層風險。

服務級 CPU 只告訴團隊「系統變慢了」，rule-level 訊號才告訴團隊「是哪個規則讓系統變慢」。兩者一起存在，事故才能從症狀快速收斂到可操作原因。

## 核心判讀

判讀順序是先看服務級異常，再下鑽到規則層成本分佈。若 CPU、latency、5xx 同步惡化，且 rule hit 分佈在短時間發生偏移，通常代表規則層出現新的成本熱點。

| 訊號                           | 代表意義                           | 第一波決策價值                       |
| ------------------------------ | ---------------------------------- | ------------------------------------ |
| Rule hit rate 突增             | 某規則命中流量異常放大             | 先核對最近規則推送與 traffic pattern |
| Rule-level CPU p95 / p99 上升  | 規則執行成本惡化                   | 先降級或回退高成本規則               |
| CPU hotspot 只集中在少數規則   | 問題可收斂到有限規則集合           | 優先處理 top-N 規則                  |
| 回退後 rule-level 成本快速回穩 | 異常與新規則高度關聯               | 凍結同批 rollout，進入 replay 驗證   |
| Rule trace 缺失                | 無法確認成本來自哪個分支與 payload | 先補埋點再擴大 rollout               |

## 訊號模型

Rule-level CPU 訊號模型的重點是同時保留成本、命中與上下文。只有成本沒有命中，無法判斷影響面；只有命中沒有成本，無法判斷風險等級。

| 訊號欄位               | 用途                             | 常見陷阱                      |
| ---------------------- | -------------------------------- | ----------------------------- |
| rule_id / rule_version | 對應具體規則版本                 | 規則改版未更新版本標記        |
| match_count            | 量測命中流量                     | 未按 tenant / region 分層     |
| exec_cpu_ms            | 量測規則執行成本                 | 只看平均值，忽略長尾          |
| input_class            | 區分 payload 類型與風險來源      | 缺少分類導致 replay 不可重現  |
| rollout_stage          | 對齊分批 rollout 狀態            | 觀測資料無法對應 rollout 階段 |
| fallback_action        | 記錄降級、旁路或阻擋策略是否觸發 | 事故後難以回放決策            |

## 控制面

Rule-level CPU signal governance 的控制面是把「測到異常後要怎麼停」直接接到 rollout 流程，而不是只做監控展示。

1. 對高風險規則建立 rule-level CPU baseline 與異常門檻。
2. 把 rule-level 訊號接到 staged rollout gate。
3. 對 top-N 高成本規則建立自動降級或回退條件。
4. 在 evidence package 記錄當次 rollout 的 rule-level 成本分佈與限制。
5. 在 post-incident review 回寫新 payload 類型與新風險樣式。

## 常見反模式

| 反模式               | 表面現象                     | 修正方向                           |
| -------------------- | ---------------------------- | ---------------------------------- |
| 只看服務級 CPU       | 知道有問題但找不到高成本規則 | 補 rule_id / version / cost 埋點   |
| 規則測試只跑功能正確 | 事故時才看見計算成本爆點     | 增加 representative payload replay |
| rollout 與觀測脫鉤   | 分批推送但缺乏階段判讀依據   | 把 rollout_stage 變成必填訊號欄位  |
| 回退無證據包         | 復盤只剩結論，缺成本時間線   | 接 4.20 evidence package           |

## 案例回扣

- [Cloudflare 2019 Regex CPU Outage](/backend/08-incident-response/cases/cloudflare/2019-regex-cpu-outage/)
- [6.24 規則推送安全閘門](/backend/06-reliability/rule-rollout-safety-gate/)

Cloudflare 2019 事故顯示高成本 regex 可以在全網同步推送下快速放大。Rule-level CPU 訊號治理的價值是把這類風險前移到 rollout 過程，而不是等到全球 5xx 才回頭排查。

## 交接路由

- 04.17： [Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)
- 04.20： [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
- 06.24： [Rule Rollout Safety Gate](/backend/06-reliability/rule-rollout-safety-gate/)
- 08.19： [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
