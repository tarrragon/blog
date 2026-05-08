---
title: "Netflix：FIT 證據交接與 Release Gate 回寫"
date: 2026-05-08
description: "用 Failure Injection Testing 產出的證據直接驅動 release gate：把實驗結果轉成可放行、可凍結、可回退的決策欄位。"
weight: 23
---

FIT（Failure Injection Testing）的核心責任不是做故障演示，而是產生可決策的證據。當實驗結果無法直接回答「能不能放行」，FIT 就只是測試活動，不是可靠性控制面。

## 問題場景

團隊常在故障注入後留下 dashboard 截圖與結論摘要，但 release decision 仍靠主觀討論。這種斷裂會讓同類風險反覆出現，因為每次都在重新辯論，而不是沿用同一套 evidence 欄位。

## 決策機制

要讓 FIT 成為 release gate 輸入，必須把實驗輸出結構化成決策欄位。

| 欄位                 | 核心問題                       | 決策用途                     |
| -------------------- | ------------------------------ | ---------------------------- |
| steady-state impact  | 注入後是否仍維持服務承諾       | 判斷能否繼續 rollout         |
| abort trigger record | 停止條件是否被觸發、何時觸發   | 判斷是否進入凍結與回退       |
| fallback result      | 降級路徑是否可用、恢復是否收斂 | 判斷事故時能否安全止血       |
| dependency drift     | 受影響依賴是否落在預期範圍     | 判斷 blast radius 是否可接受 |

## 可觀測訊號

| 訊號                  | 判讀重點                   | 對應章節                                                            |
| --------------------- | -------------------------- | ------------------------------------------------------------------- |
| verification evidence | 證據是否足以支持 release   | [6.23](/backend/06-reliability/verification-evidence-handoff/)      |
| rule rollout anomaly  | 規則推送後是否偏離預期     | [6.24](/backend/06-reliability/rule-rollout-safety-gate/)           |
| incident decision lag | 事故時是否可快速調用證據   | [8.19](/backend/08-incident-response/incident-decision-log/)        |
| evidence write-back   | 教訓是否回寫成下次驗證輸入 | [8.22](/backend/08-incident-response/incident-evidence-write-back/) |

## 常見陷阱

最常見錯誤是把 FIT 報告寫成敘事文件，沒有決策欄位，導致放行時無法直接引用。另一個錯誤是只記錄成功路徑，忽略 abort trigger 與 fallback 失敗，讓風險被低估。

## 下一步路由

先把 FIT 輸出整理到 [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/)，再接到 [6.24 Rule Rollout Safety Gate](/backend/06-reliability/rule-rollout-safety-gate/) 做放行判斷。事故發生時由 [8.19](/backend/08-incident-response/incident-decision-log/) 快速提取決策證據，最後回寫 [8.22](/backend/08-incident-response/incident-evidence-write-back/)。

## 引用源

- [FIT: Failure Injection Testing](https://netflixtechblog.com/fit-failure-injection-testing-35d8e2a9bb2e)
- [Netflix/chaosmonkey](https://github.com/Netflix/chaosmonkey)
