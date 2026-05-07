---
title: "6.6 SLO 與 Error Budget 政策"
date: 2026-05-01
description: "把可靠性目標轉成可驗證量測與凍結條件"
weight: 6
---

## 概念定位

SLO 與 error budget 是把可靠性從口號變成政策的工具。SLO 定義的是服務要對哪個使用者旅程負責，error budget 定義的是這個責任在一段時間內可以承受多少退化。當這兩個條件被寫清楚，可靠性就能從「感覺上應該穩」變成「超過哪個門檻就要暫停、降風險或修復」。

這個節點先處理目標，再處理門檻。先問服務要守住什麼體驗，再問這個體驗要用哪些訊號衡量，最後才決定 burn rate 到多少時要 freeze。這樣寫的好處是，讀者會先理解政策責任，再理解數字本身。

## 大綱

- SLI 選型：user-journey-centric vs system-metric
- SLO 目標訂定：可達性、商業意義、頻率窗
- error budget：burn rate、policy、freeze 條件
- 跟 [04 觀測](/backend/04-observability/) 的訊號交接
- 跟 [6.8 release gate](/backend/06-reliability/release-gate/) 的凍結觸發
- 跟 [8.1 事故分級](/backend/08-incident-response/incident-severity-trigger/) 的門檻對齊
- 反模式：cargo-cult 99.99%、SLO 無人擁有、burn rate 無 alert

## 核心判讀

SLO 的責任是讓團隊知道自己到底在保護什麼。當讀者看到一個 SLO 時，第一個問題是這個數字是否對應使用者行為、商業風險與回復成本；數字高低要放在這個脈絡中判讀。

error budget 的責任是把風險傳導成決策。當 burn rate 開始上升時，團隊先確認 budget 還剩多少、目前的變更是否會放大風險、freeze 條件是否已經被觸發。這裡的重點是路由清楚，數字只是路由的輸入。

## SLI 選型

SLI 選型的責任是把使用者旅程轉成可量測訊號。好的 SLI 先描述使用者能否完成重要任務，再選擇最能代表該任務的 log、metric、trace 或 client-side signal。

| SLI 類型     | 適用旅程                          | 常見訊號                         |
| ------------ | --------------------------------- | -------------------------------- |
| Availability | request、checkout、login 是否成功 | success rate、valid response     |
| Latency      | 使用者等待是否在可接受範圍        | latency histogram、p95 / p99     |
| Freshness    | 資料是否足夠新                    | replication lag、index delay     |
| Correctness  | 回應是否符合業務語意              | reconciliation error、mismatch   |
| Durability   | 寫入是否可保留與回復              | write success、replay validation |

Availability 適合描述同步 API 與 user-facing request。它需要清楚定義分母與分子，例如只計算有效請求、排除客戶端取消，或把 timeout、5xx 與 business failure 分開。

Latency 適合描述體驗壓力。平均值容易掩蓋長尾，可靠性政策通常需要 percentile 或 histogram，並且要對應使用者旅程，再用單一 process 的 handler time 作為診斷輔助。

Freshness 適合描述資料管線、search index、cache projection 與 read model。這類服務即使 API 回應成功，資料過舊仍會破壞使用者體驗。

Correctness 適合描述金流、帳務、庫存、資料同步與 migration。這類可靠性目標需要資料校驗與 reconciliation，而不只看 request 成功率。

Durability 適合描述 queue、event log、object storage 與資料寫入。它關心寫入後能否找回、重播、備份與回復，常和 RPO / RTO 一起定義。

## SLO 政策

SLO 政策的責任是把可靠性目標轉成團隊行為。數字本身只是門檻，政策要說明目標的 owner、時間窗、例外條件、檢視頻率與觸發後動作。

| 政策欄位       | 責任                         | 判讀用途                      |
| -------------- | ---------------------------- | ----------------------------- |
| User journey   | 定義受保護體驗               | 避免 SLO 停在系統資源層       |
| SLI formula    | 定義分母、分子與資料來源     | 保護 SLO 可重算與可解釋       |
| Objective      | 定義目標值與時間窗           | 連接可靠性承諾與風險預算      |
| Owner          | 指定維護與決策責任           | 讓 policy 能被檢視與調整      |
| Burn alert     | 定義消耗速度與通知條件       | 讓風險在 budget 耗盡前被看見  |
| Freeze action  | 定義暫停發布或限制變更的條件 | 把可靠性風險接到 release gate |
| Review cadence | 定義檢視頻率與調整機制       | 避免目標跟服務現況脫節        |

User journey 是 SLO 的錨點。checkout、login、message delivery、search freshness、invoice generation 都比 CPU 或 memory 更適合承載可靠性承諾，因為它們能直接對應使用者結果。

SLI formula 需要可重算。分母包含哪些 request、分子如何判定成功、資料來源來自 server-side 還是 client-side、sampling 有哪些限制，都需要寫進政策。

Objective 需要結合商業風險與回復成本。99.9% 與 99.99% 的差異不只是小數點，而是代表可接受 downtime、工程投資、成本與變更節奏的差異。

Freeze action 讓 error budget 進入工程決策。當 budget 消耗過快時，團隊需要知道哪些變更暫停、哪些修復可繼續、哪些例外需要 owner 核准。

## Error Budget 與 Burn Rate

Error budget 的責任是把可靠性退化轉成可管理的風險餘額。它讓團隊在「追求穩定」與「持續變更」之間有共同語言。

| 狀態             | 判讀訊號                    | 常見動作                       |
| ---------------- | --------------------------- | ------------------------------ |
| Budget healthy   | burn rate 低於門檻          | 維持正常發布節奏               |
| Budget warning   | 短窗 burn rate 上升         | 檢查近期變更與高風險發布       |
| Budget critical  | 多窗口 burn rate 同時超門檻 | 暫停高風險變更，優先修復可靠性 |
| Budget exhausted | error budget 用盡或接近用盡 | 啟動 freeze、復盤與可靠性改善  |
| Policy mismatch  | SLO 長期過鬆或過緊          | 調整 SLI、objective 或時間窗   |

Burn rate 要看短窗與長窗。短窗能捕捉快速事故，長窗能避免一次性尖峰造成過度反應；兩者一起使用，才適合觸發 page、ticket 或 release freeze。

Budget warning 適合做風險整理。團隊可以檢查近期 deploy、feature flag、migration、capacity、dependency 與 incident review action item，判斷是否需要降低變更速度。

Budget critical 適合觸發 release gate。此時可靠性風險已經從觀測層進入決策層，團隊需要把發布、rollback、capacity 與 incident readiness 放在同一張表中判讀。

Budget exhausted 適合觸發可靠性改善。改善內容可能是修 bug、補 capacity、降低 alert noise、補 runbook、重設 SLO 或清理 reliability debt。

## 判讀訊號

- SLO 數字無 owner、過半年沒檢視
- burn rate 無 alert、只有 monthly review
- error budget 耗盡但 deployment 節奏不變
- SLI 用 system metric（CPU / memory）、不對應 user journey
- 目標數字是抄來的（99.9 / 99.99）、無商業 anchor

## 案例對照

Google 提供的是制度原點，因為它把 SLO、[post-incident review](/backend/knowledge-cards/post-incident-review/) 與 toil budget 串成可管理的可靠性文化。Honeycomb 提供的是訊號層的延伸，因為 high-cardinality 與 burn rate alert 讓 SLO 可以在真實流量下被看見。Stripe 則把 SLO 風格的決策壓到交易語義上，讓 idempotency 與 migration 不會因為重試而失真。

當讀者把這三個案例放在一起，就會看見 SLO 不只是「填一個百分比」，而是把不同層級的風險接到同一條路由：制度、訊號與交易正確性。這也是本節章節要建立的核心能力。

## 控制面

SLO 與 error budget 的控制面是把可靠性訊號接到發布、事故與改善流程。SLO 只有在能改變團隊行為時，才會成為政策。

1. SLI 設計回到 [4.6 SLI 量測與 SLO 訊號設計](/backend/04-observability/sli-slo-signal/)。
2. 資料品質限制回到 [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)。
3. Budget warning 進入 release risk review。
4. Budget critical 進入 [6.8 Release Gate](/backend/06-reliability/release-gate/)。
5. 事故觸發與復盤回寫進入 [8.1 事故分級](/backend/08-incident-response/incident-severity-trigger/) 與 [8.5 復盤](/backend/08-incident-response/post-incident-review/)。

SLO policy 需要定期校準。服務規模、使用者旅程、依賴型態與商業風險變化後，原本的 SLI、objective 與 freeze 條件也要重新檢視。

SLO policy 也需要例外流程。重大資安修補、合規變更、資料修復或客戶承諾可能需要在 budget 緊張時繼續推進；例外應記錄 owner、理由、風險與回退條件。

## 常見反模式

SLO 反模式通常來自把目標數字當成可靠性制度本身。數字需要對應旅程、資料、owner 與決策，才有工程意義。

| 反模式             | 表面現象             | 修正方向                       |
| ------------------ | -------------------- | ------------------------------ |
| Cargo-cult 99.99%  | 目標抄自外部範例     | 從 user journey 與商業風險回推 |
| System metric SLO  | SLO 看 CPU / memory  | 改用成功率、延遲、freshness    |
| SLO 無 owner       | 目標存在但無人調整   | 指定 policy owner 與 review    |
| Burn rate 無 alert | budget 耗盡後才開會  | 建立短窗 / 長窗 burn alert     |
| Freeze 無路由      | 可靠性風險不影響發布 | 接到 release gate 與例外流程   |

Cargo-cult 99.99% 的問題在於缺少服務脈絡。高可用目標會增加架構、成本、演練與值班負擔；低可用目標則會增加使用者與商業風險。合理目標要從服務承諾回推。

System metric SLO 會讓可靠性偏向基礎設施視角。CPU 健康不代表 checkout 成功，pod running 不代表資料新鮮；系統指標適合支援 diagnosis，user journey 指標適合承載 SLO。

## 交接路由

- 04 訊號治理：SLI / burn rate metric 設計
- 06.8 release gate：error budget 耗盡觸發 freeze
- 06.9 capacity / cost：容量不足傳導為 SLO 風險
- 06.14 dependency budget：依賴可靠性納入 SLO 算式
- 08 事故閉環：burn rate alert 啟動條件
- 08.13 repeated / toil：error budget 撥用 toil reduction
- 06.18 reliability metrics：SLO 跟 DORA / SPACE 的指標分層
