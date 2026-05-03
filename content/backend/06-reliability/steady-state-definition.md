---
title: "6.22 Steady State Definition"
date: 2026-05-02
description: "在 chaos 與 failover 前先定義系統應維持的穩定狀態與可接受退化"
weight: 22
---

## 大綱

- steady state 的責任：定義實驗期間系統應維持的可接受狀態
- 穩態來源：SLO、business KPI、queue lag、error rate、latency、throughput、customer impact
- 可接受退化：degradation mode、fallback、load shedding、partial outage
- 實驗假設：故障注入後哪些訊號應保持穩定，哪些訊號可暫時退化
- 觀測要求：dashboard、alert、trace、synthetic probe、client-side signal
- 跟 chaos 的關係：沒有 steady state，chaos 只能證明系統被打壞
- 跟 incident response 的關係：steady state 也定義事故恢復完成條件
- 反模式：只定義故障動作，不定義成功條件；只看 server 指標，不看使用者影響

Steady state definition 的價值是讓實驗與事故有共同終點。穩態定義建立後，團隊可以同時回答「壞到什麼程度可接受」與「什麼時候算恢復」。

## 概念定位

Steady state definition 是可靠性實驗的成功條件，責任是讓團隊知道故障發生後系統應該維持什麼服務能力。

這一頁處理的是穩態定義。Chaos、failover 與 DR drill 都需要先定義系統的可接受狀態，才能判斷實驗是在驗證韌性，還是在製造混亂。

穩態是一組服務承諾，通常同時包含成功率、延遲、資料正確性與使用者影響，並對應不同故障情境下的可接受退化範圍。

## 核心判讀

判讀 steady state 時，先看穩態是否貼近使用者，再看退化是否有明確邊界。

重點訊號包括：

- steady state 是否包含 success rate、latency、queue lag 與 user impact
- degraded mode 是否說明哪些功能保留、哪些功能暫停
- stop condition 是否連到 steady state breach
- dashboard 是否能同時呈現系統指標與使用者旅程
- recovery complete 是否有可量測門檻

| 穩態元素 | 最小可用判準                             | 判讀價值                   |
| -------- | ---------------------------------------- | -------------------------- |
| 服務成功 | success rate / error budget 在可接受範圍 | 判斷是否需要升級事故       |
| 體驗延遲 | latency 與 queue lag 在門檻內            | 判斷是否進入 degraded mode |
| 資料正確 | 無資料遺失或可接受補償策略               | 判斷是否可宣告恢復         |
| 恢復條件 | recovery complete 有量測閾值             | 判斷事故何時可關閉         |

## 判讀訊號

- chaos 實驗只記錄「節點被關掉」，沒有記錄服務是否維持
- failover 後 server healthy，但用戶核心流程仍失敗
- degraded mode 啟動後，團隊不知道何時能解除
- recovery 宣告依賴人工感覺，而非 SLO / synthetic probe / queue drain
- 事故與演練使用不同的恢復完成定義

典型場景是 failover 後基礎 health check 全綠，但核心交易成功率仍低於承諾。若 steady state 只看系統健康，團隊會過早宣告恢復；若 steady state 包含 user journey，則會持續修復直到服務承諾回線。

## 交接路由

- 04.6 SLI/SLO signal：把穩態轉成可量測訊號
- 04.10 client-side / synthetic / RUM：補使用者感知訊號
- 06.4 chaos testing：把 steady state 作為實驗前提
- 06.7 DR / rollback rehearsal：把 steady state 作為恢復完成條件
- 08.3 containment / recovery：事故恢復宣告使用同一組穩態門檻
