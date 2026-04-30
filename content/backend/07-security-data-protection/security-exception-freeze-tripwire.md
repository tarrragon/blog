---
title: "7.17 例外、凍結與 Tripwire：資安決策如何避免過期"
tags: ["治理例外", "Tripwire", "Release Freeze"]
date: 2026-04-30
description: "建立資安例外、發佈凍結與 tripwire 之間決策關係的大綱"
weight: 87
---

本篇的責任是說明資安決策如何避免過期。現實服務一定會有例外、凍結與暫時接受風險的時刻，成熟度在於每個決策都有期限、補償控制與重評估觸發器。

## 核心論點

[Tripwire](/backend/knowledge-cards/tripwire/) 的核心概念是「讓風險接受決策在條件改變時自動回到檯面」。[Security Exception](/backend/knowledge-cards/security-exception/) 與 [Release Freeze](/backend/knowledge-cards/release-freeze/) 都需要 tripwire，因為它們本質上是有期限的治理狀態。

## 讀者入口

本篇適合銜接 [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 與 [7.14 資安治理例外與 Tripwire](/backend/07-security-data-protection/security-governance-exception-and-tripwire/)。它也會連到 [Release Gate](/backend/knowledge-cards/release-gate/) 與 incident workflow。

## 三種治理狀態與責任

資安決策在服務生命週期常見三種治理狀態：

| 狀態                                                               | 核心責任                     | 產出                                 |
| ------------------------------------------------------------------ | ---------------------------- | ------------------------------------ |
| [Security Exception](/backend/knowledge-cards/security-exception/) | 限制風險接受範圍與期限       | 例外紀錄、補償控制、關閉條件         |
| [Release Freeze](/backend/knowledge-cards/release-freeze/)         | 暫停高風險變更進入正式環境   | 凍結範圍、放行條件、解除條件         |
| [Tripwire](/backend/knowledge-cards/tripwire/)                     | 定義重評估觸發時機與升級路徑 | 觸發條件、告警對象、回到決策會議流程 |

三者共同目標是維持「可追蹤、可關閉、可回寫」。

## Exception 設計協議

[Security exception](/backend/knowledge-cards/security-exception/) 協議的責任是把暫時接受風險變成可管理狀態。每筆 exception 需要六欄位：

1. Risk scope：接受風險的資產與範圍。
2. Expiry：到期日與下次審查時間。
3. Compensating controls：過渡期間的防護補強。
4. Owner：業務 owner 與技術 owner。
5. Exit criteria：例外關閉條件。
6. Write-back target：關閉後回寫的位置。

## Release Freeze 設計協議

[Release freeze](/backend/knowledge-cards/release-freeze/) 的責任是保護正式環境，直到關鍵風險收斂。freeze 設計至少要回答：

1. Freeze scope：凍結哪些系統、哪些變更類型。
2. [Allowlist](/backend/knowledge-cards/allowlist/)：哪些必要變更可以例外放行。
3. Validation gate：放行前要通過哪些驗證。
4. Unfreeze condition：什麼條件可以解除凍結。

freeze 與 exception 的關係是：exception 定義風險接受，freeze 定義變更節奏。兩者都要掛在 tripwire 上。

## Tripwire 設計協議

[Tripwire](/backend/knowledge-cards/tripwire/) 的責任是讓決策在條件改變時自動回到檯面。每個 tripwire 都要有：

1. Trigger signal：可觀測且可量測的觸發訊號。
2. Threshold：達到什麼門檻觸發。
3. Escalation owner：誰負責啟動重評估。
4. Decision route：觸發後回到哪個決策流程。

建議把 tripwire 拆成三層：

| 層級     | 觸發來源                       | 例子                                                                                |
| -------- | ------------------------------ | ----------------------------------------------------------------------------------- |
| 技術訊號 | 監控、掃描、驗證結果           | [artifact provenance](/backend/knowledge-cards/artifact-provenance/) 驗證失敗率超標 |
| 流程訊號 | 發佈節奏、例外到期、審查逾期   | freeze 超過預設窗口仍未重評估                                                       |
| 外部訊號 | 公開漏洞、供應鏈公告、法規變更 | 上游供應商通報高風險憑證事件                                                        |

## 供應鏈情境下的連動設計

供應鏈情境的責任是把三種治理狀態串成閉環：

1. Exception：在修復窗口內接受有限風險，限制到特定資產。
2. Freeze：暫停高風險 [artifact provenance](/backend/knowledge-cards/artifact-provenance/) 部署，僅 [allowlist](/backend/knowledge-cards/allowlist/) 放行。
3. Tripwire：監測 artifact 驗證、secrets 輪替、版本恢復演練訊號。
4. Close：條件達成後解除 exception / freeze，回寫到 problem cards 與 workflow。

這條路徑可以對應 [發佈凍結缺少重評估觸發器](/backend/07-security-data-protection/red-team/problem-cards/fp-release-freeze-without-tripwire/) 與 [例外缺少期限與關閉條件](/backend/07-security-data-protection/red-team/problem-cards/fp-exception-without-expiry/)。

## 判讀訊號、風險與下一步路由

| 判讀訊號                                                                                                                      | 代表風險                         | 下一步路由                                |
| ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ----------------------------------------- |
| [Security exception](/backend/knowledge-cards/security-exception/) 項目沒有到期日                                             | 風險接受狀態失去關閉機制         | 回到 7.14 補 expiry 與 close criteria     |
| [Release freeze](/backend/knowledge-cards/release-freeze/) 已啟動但沒有 [allowlist](/backend/knowledge-cards/allowlist/) 契約 | 關鍵修復與運維操作被一併阻斷     | 補 freeze scope 與 allowlist              |
| 有 [Tripwire](/backend/knowledge-cards/tripwire/) 名稱但沒有量化門檻                                                          | 觸發條件不可驗證，決策回收不穩定 | 補 threshold 與 escalation owner          |
| [Security exception](/backend/knowledge-cards/security-exception/) 關閉後沒有回寫                                             | 同類風險下次仍靠人工記憶         | 回寫到 problem cards 與 incident workflow |

## 可直接套用的決策模板

```text
Decision ID:
Risk scope:
Exception expiry:
Compensating controls:
Freeze scope / allowlist:
Tripwire signal + threshold:
Escalation owner:
Close criteria:
Write-back target:
```

模板責任是讓治理決策可重用，不讓每次事件都重頭設計欄位。

## 邊界與常見誤判

本篇邊界是治理決策協議，不替代 incident 指揮細節與修復 runbook。常見誤判如下：

1. 把 freeze 當永久策略：正確做法是 freeze 有解除條件與評估節奏。
2. 把 tripwire 當提醒文字：正確做法是有量化門檻與 owner。
3. 把 exception 當管理同意：正確做法是例外協議包含補償控制與關閉條件。

## 必連章節

- [7.9 服務生命週期的資安風險節奏](/backend/07-security-data-protection/security-lifecycle-risk-cadence/)
- [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- [7.14 資安治理例外與 Tripwire](/backend/07-security-data-protection/security-governance-exception-and-tripwire/)
- [發佈凍結缺少重評估觸發器](/backend/07-security-data-protection/red-team/problem-cards/fp-release-freeze-without-tripwire/)
- [例外缺少期限與關閉條件](/backend/07-security-data-protection/red-team/problem-cards/fp-exception-without-expiry/)

## 完稿判準

完稿時要讓讀者能設計一個例外決策模板。模板至少包含風險接受條件、到期日、補償控制、tripwire、關閉條件與回寫位置。
