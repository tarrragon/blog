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

[Steady state](/backend/knowledge-cards/steady-state/) definition 的價值是讓實驗與事故有共同終點。穩態定義建立後，團隊可以同時回答「壞到什麼程度可接受」與「什麼時候算恢復」。

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

## 穩態來源

Steady state 的來源是服務承諾與操作訊號。它需要把 SLO、business KPI、系統指標與客戶感知訊號放在同一個判讀模型中。

| 來源          | 責任                     | 常見訊號                           |
| ------------- | ------------------------ | ---------------------------------- |
| SLO / SLI     | 定義可靠性承諾           | success rate、latency、freshness   |
| Business KPI  | 定義業務結果是否維持     | checkout success、order volume     |
| Queue / async | 定義背景流程是否可追上   | queue lag、DLQ、retry rate         |
| Client signal | 定義使用者感知是否正常   | RUM、synthetic probe、mobile error |
| Data signal   | 定義資料是否正確且可回復 | reconciliation、replication lag    |

SLO / SLI 是 steady state 的主要來源。它們讓實驗與事故判讀有共同基準，避免每次演練都重新討論什麼算可接受狀態。

Business KPI 能補足純技術指標的盲區。checkout success、payment authorization、message delivery、document publish 與 invoice generation 這些業務結果，能直接反映使用者旅程是否維持。

Queue / async 訊號能保護延遲性風險。同步 API 可能恢復，但 queue lag、DLQ、retry storm 或 backfill backlog 仍在累積；steady state 應包含這些後段壓力。

Client signal 能補 server-side 盲區。CDN、mobile network、browser runtime、third-party script 與 regional routing 可能讓 server 看起來健康，但使用者仍感知到失敗。

Data signal 能保護正確性。failover、migration、replay 與 DR drill 都需要確認資料沒有遺失，或至少有明確補償與 reconciliation 路徑。

## 可接受退化

可接受退化的責任是定義故障期間哪些能力要維持、哪些能力可以暫停、哪些能力需要補償。它讓團隊在壓力下有一致的降級語言。

| 退化模式        | 適用情境                      | 穩態判準                          |
| --------------- | ----------------------------- | --------------------------------- |
| Read-only mode  | 寫入風險高、讀取仍可服務      | 讀取成功率維持，寫入明確暫停      |
| Fallback        | 下游依賴失效                  | 使用替代資料，標示 freshness 限制 |
| Load shedding   | 流量超過容量                  | 保核心旅程，拒絕低優先請求        |
| Partial outage  | 區域、tenant 或功能局部受影響 | 影響範圍可界定且持續收斂          |
| Manual recovery | 自動回復不足                  | 人工步驟有 owner、timeline、證據  |

Read-only mode 適合保護資料正確性。若寫入路徑風險高，暫停寫入但保留查詢，可以讓服務維持部分價值，同時避免資料修復成本擴大。

Fallback 適合吸收下游失效。fallback 需要明確資料新鮮度、適用功能與使用者提示，讓服務承諾暫時降到可接受範圍。

Load shedding 適合處理容量壓力。它需要先定義核心旅程與低優先請求，讓系統在高壓下保住最重要的使用者結果。

Partial outage 適合處理 blast radius 已被限制的事故。穩態定義應說明受影響 region、tenant、功能與預期恢復路徑，避免把局部可控誤讀成全域恢復。

## 判讀訊號

- chaos 實驗只記錄「節點被關掉」，沒有記錄服務是否維持
- failover 後 server healthy，但用戶核心流程仍失敗
- degraded mode 啟動後，團隊不知道何時能解除
- recovery 宣告依賴人工感覺，而非 SLO / synthetic probe / queue drain
- 事故與演練使用不同的恢復完成定義

典型場景是 failover 後基礎 health check 全綠，但核心交易成功率仍低於承諾。若 steady state 只看系統健康，團隊會過早宣告恢復；若 steady state 包含 user journey，則會持續修復直到服務承諾回線。

## 實驗假設

Steady state 是 experiment hypothesis 的成功條件。故障注入前，團隊要先寫清楚哪些訊號應維持、哪些訊號可退化、退化多久仍可接受。

| 假設欄位            | 責任                 | 範例                           |
| ------------------- | -------------------- | ------------------------------ |
| Injected failure    | 說明要注入的失效     | 關閉一個 cache node            |
| Expected behavior   | 說明系統應如何吸收   | request latency 短暫上升       |
| Stable signals      | 說明應維持穩定的訊號 | checkout success rate 維持門檻 |
| Allowed degradation | 說明可接受退化       | p99 latency 10 分鐘內回線      |
| Stop condition      | 說明何時終止         | error budget burn 超門檻       |
| Recovery complete   | 說明何時算恢復       | queue lag drain 到基準線       |

Injected failure 只是實驗輸入。可靠性實驗真正要驗證的是 expected behavior，也就是系統面對失效時是否維持約定服務能力。

Stable signals 需要同時包含 server-side 與 user-facing 訊號。pod healthy、CPU 正常、database 可連線都很有用，但最後仍要回到核心旅程是否成功。

Allowed degradation 能避免過度反應。某些實驗預期會造成短暫 latency 上升或 fallback 啟動，只要在可接受時間窗內回線，就代表系統符合預期。

Recovery complete 應該可量測。queue lag drain、error rate 回到 baseline、synthetic probe 連續通過、reconciliation 完成，都比「看起來好了」更適合作為關閉條件。

## 事故恢復

Steady state 也是事故恢復宣告的共同基準。事故處理需要知道服務何時從 containment 進入 recovery，何時可以對內外部宣告恢復，何時進入 post-incident review。

| 階段        | Steady state 責任            | 事故決策                     |
| ----------- | ---------------------------- | ---------------------------- |
| Triage      | 判斷是否已偏離穩態           | 啟動或升級 incident          |
| Containment | 判斷退化是否維持在可接受範圍 | 降級、限流、切換             |
| Recovery    | 判斷核心旅程是否回到門檻     | 宣告服務恢復                 |
| Review      | 判斷穩態定義是否足以支援判讀 | 回寫 SLO、dashboard、runbook |

Triage 階段，steady state 幫助團隊把異常轉成事故門檻。若 success rate、latency、queue lag 或 customer impact 偏離穩態，就有足夠理由啟動分級。

Containment 階段，steady state 幫助團隊判斷退化策略是否有效。fallback、load shedding 或 read-only mode 啟動後，團隊要看核心旅程是否回到可接受範圍。

Recovery 階段，steady state 幫助團隊避免過早關閉事故。基礎 health check 回綠只是其中一個訊號，核心旅程、資料正確性與長尾 backlog 都要回到門檻。

Review 階段，steady state 會回寫到 04 與 06。若事故期間發現穩態指標缺失、門檻過鬆或 dashboard 不支援判讀，就要回到 SLO、observability readiness 或 reliability readiness。

## 常見反模式

Steady state 的反模式通常來自只定義故障動作，缺少成功條件。成功條件能讓 chaos、failover 與 DR drill 證明系統如何承受失效，而不只證明系統被打壞。

| 反模式             | 表面現象                       | 修正方向                           |
| ------------------ | ------------------------------ | ---------------------------------- |
| 只定義故障動作     | 實驗說明只有關機、斷線、切流量 | 補 stable signals 與成功條件       |
| 只看 server 指標   | health check 綠燈就宣告恢復    | 加入 user journey 與 client signal |
| 退化模式無邊界     | fallback 啟動後無時間窗與限制  | 定義 allowed degradation           |
| 恢復完成靠感覺     | IC 以主觀判斷關閉事故          | 定義 recovery complete metric      |
| 實驗與事故標準不同 | drill 通過但事故時用另一套門檻 | 共用 steady state 與 runbook       |

只看 server 指標會讓恢復宣告偏早。服務健康需要同時看基礎設施、後端旅程、client-side signal 與資料正確性，才能支援對外通訊。

退化模式無邊界會讓 fallback 變成隱性事故。fallback 可用時，團隊仍需要知道資料新鮮度、功能限制、時間窗與客戶影響。

## 交接路由

- 04.6 SLI/SLO signal：把穩態轉成可量測訊號
- 04.10 client-side / synthetic / RUM：補使用者感知訊號
- 06.4 chaos testing：把 steady state 作為實驗前提
- 06.7 DR / rollback rehearsal：把 steady state 作為恢復完成條件
- 08.3 containment / recovery：事故恢復宣告使用同一組穩態門檻
