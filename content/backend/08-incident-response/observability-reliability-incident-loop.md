---
title: "8.11 Observability / Reliability / Incident Response 閉環"
date: 2026-05-01
description: "把 04 / 06 / 08 三個模組的雙向反饋串成可判讀循環，定義閉環健康度判讀訊號"
weight: 11
---

服務的可靠性工程不是單向 pipeline、是循環反饋系統。觀測（04）偵測訊號驅動事故響應（08）、事故學習回寫到驗證設計（06）、驗證實踐又反過來定義觀測訊號（04）。任一段缺失閉環就斷裂、組織會以可預測的方式陷入特定失能模式。

本章把三個模組當一個閉環看、定義各方向交接、每個方向的健康度判讀訊號、與斷裂後的失能模式。本章不重複 04 / 06 / 08 各自的概念內容、只承擔「把三者串成閉環」的責任。

## 為何要把三者當閉環看

單獨看任一模組會錯估它的責任邊界：

- **04 單獨看**：把訊號當成「服務狀態的視覺化」、忽略訊號是 6.6 SLO 政策的依據、是 8.1 事故啟動條件的觸發器。
- **06 單獨看**：把驗證當成「測試完整度的驗證」、忽略驗證 hypothesis 來自事故 [post-incident review](/backend/knowledge-cards/post-incident-review/)、SLO 來自觀測訊號。
- **08 單獨看**：把事故當成「響應流程演練」、忽略事故 [post-incident review](/backend/knowledge-cards/post-incident-review/) 的價值在回寫 04 訊號與 06 驗證、不在響應本身。

閉環視角讓三個模組各自的設計受其他兩者約束、避免局部最佳化。

## 閉環四個方向

### 04 → 08：訊號驅動事故響應

最直觀的方向、訊號（SLO burn rate / error rate spike / latency p99 / queue lag）達標後觸發告警、進入事故響應流程。

判讀邊界由 04 定義（什麼算異常）、響應節奏由 08 定義（誰響應、怎麼分級、怎麼通訊）。交接點是 alert routing：[symptom-based alert](/backend/knowledge-cards/symptom-based-alert/) 連到 [alert runbook](/backend/knowledge-cards/alert-runbook/)、再連到事故指揮流程。

具體例子：

- Checkout API p99 latency 超過 SLO burn rate 2x → 觸發 PagerDuty alert → 進入 Sev2 事故流程
- Queue consumer lag 持續上升 → 訊號觸發 → 進入 capacity incident 流程
- Error rate spike 超過 baseline 5σ → alert → 進入 release rollback 流程

### 08 → 06：事故回寫驗證設計

事故 [post-incident review](/backend/knowledge-cards/post-incident-review/) 的 action items 不應該只是「補 runbook」這類局部修正、而應該回寫到事前驗證設計、讓下一次同類事故在 production 前被攔截。

交接點是 [post-incident review](/backend/knowledge-cards/post-incident-review/) action items 的分類：哪些回到 6.4 chaos experiment、哪些回到 6.7 DR rehearsal、哪些回到 6.8 release gate、哪些回到 6.6 SLO 政策。

具體例子：

- 事故揭露 cache 失效時 DB 雪崩 → 回寫到 6.4 chaos experiment（注入 cache failure）
- 事故揭露 region failover 演練不足 → 回寫到 6.7 DR rehearsal 排程
- 事故揭露 migration 沒測 rollback → 回寫到 6.8 release gate（migration check）
- 事故揭露 SLO 太鬆、導致客戶感知問題前沒人發現 → 回寫到 6.6 SLO 政策收緊

### 06 → 04：驗證需求驅動訊號設計

事前驗證會暴露當前訊號的不足：chaos experiment 需要新 metric 確認 steady state、load test 需要新 dashboard 看 capacity headroom、SLO 政策需要新 alert rule 偵測 burn rate。

交接點是 4.1（log schema）/ 4.2（metrics）/ 4.4（dashboard / alert）的擴充來源：哪些訊號是驗證 hypothesis 必要的、就應該在 04 提供。

具體例子：

- 6.4 Chaos experiment 注入 broker partition、需要新 metric 看 consumer rebalance 時間 → 4.2 補
- 6.6 SLO 定義要求 burn rate alert → 4.4 補對應 alert rule
- 6.7 DR rehearsal 需要看 cross-region replication lag → 4.4 補 dashboard

### 08 → 04：事故揭露偵測缺口

事故發生後、[post-incident review](/backend/knowledge-cards/post-incident-review/) 通常會發現「訊號其實有、但太晚 / 太雜 / 看不出 user impact」、這些是 04 的偵測缺口。

交接點跟 06 → 04 不同：06 → 04 是預期性新增訊號、08 → 04 是修正既有訊號治理問題。回寫到 [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 與 04 的訊號設計。

具體例子：

- 事故揭露 alert 太晚（用 cause-based 而不是 symptom-based）→ 回寫 alert design
- 事故揭露 dashboard cardinality 不足、看不到單一 user 影響 → 回寫 metric design
- 事故揭露 alert 太雜、值班疲乏錯過真實訊號 → 回寫 alert noise reduction（4.4 / [alert fatigue](/backend/knowledge-cards/alert-fatigue/)）

## 閉環健康度判讀訊號

閉環是否運作的判讀訊號 — 三個方向都應該定期觀察是否在動：

| 方向    | 健康訊號                                                                                                    | 失能訊號                                                                                                             |
| ------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 04 → 08 | 多數 Sev2+ 事故由 alert 觸發、不是客戶通報                                                                  | 客戶通報先於 alert 的比例上升、值班發現 alert 沒人接                                                                 |
| 08 → 06 | 每次 [post-incident review](/backend/knowledge-cards/post-incident-review/) 至少產出一個事前驗證 action     | [post-incident review](/backend/knowledge-cards/post-incident-review/) action items 都是 runbook 補丁、無事前驗證    |
| 06 → 04 | Chaos / SLO 工作會驅動新訊號出現                                                                            | 驗證活動孤立、不會反向擴充 04 訊號集                                                                                 |
| 08 → 04 | [post-incident review](/backend/knowledge-cards/post-incident-review/) 會具名指出哪個訊號不足、有 follow-up | [post-incident review](/backend/knowledge-cards/post-incident-review/) 提到「訊號不夠」但沒落實到具體 metric / alert |

## 閉環斷裂的失能模式

每個方向斷裂會導致可預測的問題：

- **04 → 08 斷**：alert 沒接 IR 流程、訊號變成「儀表板好看」但不驅動行動。常見於把 04 當成 BI 工具的團隊。
- **08 → 06 斷**：每次事故重複同類根因、[post-incident review](/backend/knowledge-cards/post-incident-review/) 變成 ritual、對下一次事故沒影響。常見於沒有 6.7 DR rehearsal 文化的團隊。
- **06 → 04 斷**：驗證活動成為孤立工程實踐、chaos 結果不影響 dashboard / alert 設計。常見於 SRE 跟 platform 團隊割裂時。
- **08 → 04 斷**：訊號治理停滯、alert noise 累積、值班疲乏。常見於沒有 [alert fatigue](/backend/knowledge-cards/alert-fatigue/) 主題的成熟度檢視。

## 從本章到實作

判讀完閉環現況後沿兩條 chain 進入 implementation：

1. **方向強化 chain**：找出最弱的方向、補對應模組的章節 — 04 → 08 弱補 4.4 alert design + 8.2 command；08 → 06 弱補 8.5 [post-incident review](/backend/knowledge-cards/post-incident-review/) 模板 + 6.6 / 6.7；06 → 04 弱補 6.6 SLO + 4.2 metrics；08 → 04 弱補 8.5 + 4.4。
2. **跨模組演練 chain**：用 6.6 [game day](/backend/knowledge-cards/game-day/) 同時驗證三個方向是否串通 — 注入故障、看 04 是否觸發、08 是否響應、[post-incident review](/backend/knowledge-cards/post-incident-review/) 是否回寫 06 / 04。
