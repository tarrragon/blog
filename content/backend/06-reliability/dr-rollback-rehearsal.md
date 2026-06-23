---
title: "6.7 DR 演練與 Rollback Rehearsal"
date: 2026-05-01
description: "把回復路徑從紙面計畫變成定期可重播、可量測的驗證流程"
weight: 7
tags: ["backend", "reliability"]
---

## 概念定位

DR 演練與 rollback rehearsal 是把回復能力從「有計畫」變成「經過驗證」的工具。DR 關心的是系統在災難後能不能回來，rollback rehearsal 關心的是變更失敗時能不能退回安全狀態。兩者的責任是把回復路徑變成可驗證流程。

這個節點先處理路徑，再處理速度。先確認資料能不能回來、服務能不能切回來、回復後會不會再掉回去，然後才談 [RTO](/backend/knowledge-cards/rto/) / [RPO](/backend/knowledge-cards/rpo/)。這樣讀，會比直接背指標更接近真實系統的恢復成本。

## 核心判讀

DR 的責任是證明回復路徑存在，而且可實際走通。只要 backup 還沒被 restore 驗證過，它就只是備份，不是復原能力。只要 failover config 沒跟 production 對齊，它就只是文件，不是操作路由。

rollback rehearsal 的責任是把失敗變更的退路先跑過。當 deployment 出現問題時，團隊需要知道自己是能回退、必須 roll forward，還是必須先止血再處理資料。這個判斷來自平常 rehearsal 的累積，臨場才不會陷入猜測。

## Rollback vs Roll-forward 的判斷條件

變更失敗時的第一個決策是退回還是往前修。這個判斷取決於變更是否可逆，以及新資料是否已經依賴新版結構。

rollback 的前提是變更可逆：schema 仍向下相容、feature flag 可關閉、routing 可切回前一版。當這些條件成立時，rollback 通常比 roll-forward 更快收斂，因為退回的行為已經被驗證過（它就是前一版的 production 狀態）。

roll-forward 的前提是修復比退版快且安全。當新版已經寫入不可回退的資料（新欄位被使用、新格式被下游消費、交易已在新路徑完成），退版會造成資料遺失或不一致，此時 roll-forward 是被迫的選擇，不是偏好。

兩者之間存在灰色地帶：schema migration 已執行但流量尚未切換、feature flag 已開啟但影響範圍有限。這類情境需要事前在 rehearsal 中定義判斷條件，而不是事中討論。第三種常見路徑是先 rollback 止血（降低 customer impact），確認穩定後再推出修復版 roll-forward。這個 hybrid 策略的前提是 rollback 安全且修復方案已知。

[Stripe 的 expand/contract migration 模型](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/) 說明交易系統的 rollback 需要同時處理 schema 相容與冪等重播。當 idempotency key 與業務操作邊界一致時，rollback 後的重試才能產生正確結果。這個案例揭露的判讀條件是：rollback 安全性不只看部署層，還要看資料語義層。

| 條件          | 傾向 rollback                  | 傾向 roll-forward              |
| ------------- | ------------------------------ | ------------------------------ |
| Schema 相容性 | 舊版可讀新版資料、無破壞性變更 | 新欄位已被寫入、舊版無法解析   |
| 資料狀態      | 新版尚未產生不可回退的資料     | 交易、訂單或事件已在新路徑完成 |
| 修復時間      | 問題根因不明、修復時間不可預測 | 根因明確、修復可在分鐘內完成   |
| Feature flag  | flag 可關閉且影響範圍已知      | flag 關閉會觸發另一組問題      |
| 下游依賴      | 下游未消費新版輸出             | 下游已開始處理新格式資料       |

## Restore 驗證

備份的價值在還原時才能被證明。restore drill 的責任是證明備份能在需要時變成可用的服務狀態。

restore 驗證分三個層次，每一層回答不同的問題。

**資料完整性**：還原後的資料是否完整。驗證手段包含 row count 比對、checksum 校驗、reconciliation query。這一層的失敗模式通常是 backup 時段選擇不當（跨越 batch job 執行期）或 incremental backup 鏈條斷裂。

**服務可用性**：還原後的系統是否能正常回應。資料完整不代表服務可用 — config、secret、schema version、connection pool 設定都可能在 restore 後失效。這一層需要在 restore 完成後跑 smoke test 與 health check，確認服務能處理請求。

**恢復時間量測**：實際 [RTO](/backend/knowledge-cards/rto/) 是否符合承諾。如果承諾 4 小時 RTO 但 restore 本身需要 6 小時，這個承諾就是空的。量測要包含從決策啟動到服務恢復的完整時間，不只是資料還原時間。Roblox 2021 的 73 小時 outage 說明 recovery 不是切回流量就結束 — 資料一致性重建、快取預熱與依賴服務的啟動順序都會拉長實際恢復時間。

## 演練類型

| 類型                 | 目的                           | 典型輸出                                                                                   |
| -------------------- | ------------------------------ | ------------------------------------------------------------------------------------------ |
| tabletop             | 檢查決策路由與角色分工         | 角色清單、決策順序、通訊模板                                                               |
| partial failover     | 驗證局部區域或子系統能否切換   | 切換結果、回復時間、手動步驟                                                               |
| full region failover | 驗證整個區域是否能從災難中回來 | [RTO](/backend/knowledge-cards/rto/)、[RPO](/backend/knowledge-cards/rpo/)、資料一致性檢查 |
| data restore drill   | 驗證備份是否能真的還原資料     | restore log、校驗結果、缺口清單                                                            |

這些演練的共同點是：演練本身要留下證據。沒有輸出，就沒有辦法判斷回復能力到底有沒有被建立。

**Tabletop** 的重點是決策路由清晰度。參與者在紙上走一遍事故情境，回答「誰負責決定切換」「什麼條件觸發升級」「通訊延遲多長可接受」。這個類型成本最低、頻率應最高，適合用來發現流程漏洞與角色模糊。

**Partial failover** 的重點是切換腳本與監控覆蓋。選擇一個子系統或單一 availability zone 做真實切換，驗證自動化腳本是否可執行、監控是否能在切換過程中保持可見性。這個階段常暴露的問題是：腳本假設的前提條件在 production 不成立，或監控在切換過程中產生大量 false positive。

**Full region failover** 的重點是資料一致性與恢復順序。[Meta 的 2021 年事故](/backend/06-reliability/cases/meta/region-failover-and-reliability-boundaries/)顯示，跨區 failover 的最大風險在恢復順序 — 控制面與資料面共用路徑時，先恢復哪條路徑會直接決定整體恢復時間。當恢復動作本身依賴尚未恢復的控制面服務，恢復會陷入循環等待。

## 演練節奏與升級

演練是按風險層級安排的循環流程。

| 類型                 | 建議節奏 | 升級條件                                 |
| -------------------- | -------- | ---------------------------------------- |
| tabletop             | 季度     | 新增關鍵依賴、組織結構變更、重大事故後   |
| partial failover     | 半年     | tabletop 暴露切換路徑疑慮                |
| full region failover | 年度     | partial 驗證通過、業務需求（合規、審計） |
| data restore drill   | 季度     | 備份策略變更、資料量跳升、新增資料源     |

每輪演練產出的缺口應回寫到 [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/)，成為下一輪演練的驗證目標。[Google 的 postmortem action item closure 治理](/backend/06-reliability/cases/google/postmortem-action-item-closure-governance/)說明把事故教訓轉成有 owner 與完成條件的改進項，這個機制同樣適用於演練缺口：P0 缺口應在下個 release 週期前修復，P1 缺口應排入固定追蹤。

[Shopify 的 BFCM 準備流程](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)把年度高峰前的 game day 當作 DR 演練的自然觸發點。容量模型、隔離邊界與 failover 路徑在 game day 中一起驗證，每輪暴露的缺口回寫成下一輪的準備 checklist。這種做法讓演練節奏跟業務節奏對齊，不是額外負擔。

## DR 與 chaos 的邊界

DR 演練與 [chaos testing](/backend/06-reliability/chaos-testing/) 都涉及故障情境，但驗證目標不同。

Chaos 驗證的是系統在故障持續期間能否維持服務。它的成功條件是 [steady state](/backend/knowledge-cards/steady-state/) 不被破壞，停止條件是 steady state breach。chaos 實驗結束後，系統應該仍在運作。

DR 驗證的是系統在災難發生後能否回來。它的成功條件是恢復路徑可執行且符合 [RTO](/backend/knowledge-cards/rto/) / [RPO](/backend/knowledge-cards/rpo/) 承諾，停止條件是恢復時間超過 RTO 或資料遺失超過 RPO。DR 演練結束時，系統經歷了一次完整的失效與恢復循環。

兩者的交集是 failover drill：chaos 關心切換期間的服務退化程度，DR 關心切換完成後的恢復品質。在實務上，成熟團隊會把 chaos experiment 的結果作為 DR 演練的輸入 — chaos 發現的弱點變成 DR 演練的測試案例。[Amazon 的 cell boundary 與 static stability 設計](/backend/06-reliability/cases/amazon/shuffle-sharding-and-cell-boundary/)讓恢復可分批執行，同時服務 chaos 驗證（局部故障不擴散）與 DR 驗證（分批恢復可預測）。

## 產業情境：醫療系統

醫療系統的 DR 演練受合規（HIPAA / GDPR health data）和臨床連續性的雙重約束。演練設計需要同時滿足技術恢復目標與臨床安全要求。

演練排程需要跟臨床作業週期對齊。手術高峰、急診高峰與夜班交接時段都應避免做 failover 演練，因為演練造成的短暫服務中斷可能直接影響臨床決策。可執行窗口通常是週末凌晨或排定的維護時段。

恢復順序由臨床風險決定。EMR（電子病歷）系統優先於醫囑系統、PACS（影像系統）與行政系統。這個順序跟技術依賴不完全重疊 — 技術上 PACS 可能先恢復更快，但臨床上 EMR 的中斷風險更高。恢復順序的設計需要臨床代表參與，技術團隊單獨決定會漏掉臨床優先級。

Restore 驗證需要額外的 audit trail 完整性檢查。HIPAA 要求能追蹤誰在什麼時間存取了哪些病患資料，恢復後的資料若 audit trail 斷裂，即使資料本身完整也不符合合規要求。restore drill 的校驗清單需要把 audit trail 連續性納入必檢項。

醫療紀錄的 [RPO](/backend/knowledge-cards/rpo/) 通常比一般 SaaS 更嚴格，接近零資料遺失。遺失的醫療紀錄可能直接影響用藥決策或手術判斷，RPO 設定需要對齊臨床風險而非技術方便性。

演練證據本身也需要合規留存。DR 演練紀錄、恢復時間量測、缺口清單與改善追蹤都是合規審計的輸入。沒有留存的演練在審計視角等同未演練。

## 案例對照

| 案例       | DR 視角的教訓                                                                                   | 回讀章節                                                                                                                           |
| ---------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Meta M1    | 控制面與資料面共用路徑時，恢復順序決定整體恢復時間                                              | [6.14](/backend/06-reliability/dependency-reliability-budget/)、[8.14](/backend/08-incident-response/multi-incident-coordination/) |
| Amazon A1  | cell boundary 讓恢復可分批，不需要全域同步恢復                                                  | [6.20](/backend/06-reliability/experiment-safety-boundary/)                                                                        |
| Stripe S1  | 交易系統 rollback 需要同時驗證 schema 相容與冪等重播                                            | [6.11](/backend/06-reliability/migration-safety/)、[6.12](/backend/06-reliability/idempotency-replay/)                             |
| Shopify H1 | 年度高峰前的 game day 是 DR 演練的自然觸發點                                                    | [6.9](/backend/06-reliability/capacity-cost/)、[6.22](/backend/06-reliability/steady-state-definition/)                            |
| Google G2  | postmortem action item 轉成下一輪 DR 演練題目                                                   | [6.21](/backend/06-reliability/reliability-debt-backlog/)、[8.5](/backend/08-incident-response/post-incident-review/)              |
| Netflix N1 | [steady state](/backend/knowledge-cards/steady-state/) 定義同時作為 DR recovery complete 的判準 | [6.22](/backend/06-reliability/steady-state-definition/)                                                                           |
| Amazon A2  | static stability 讓資料面在控制面失效時仍能服務，恢復路徑不依賴已故障的控制面                   | [6.14](/backend/06-reliability/dependency-reliability-budget/)、[6.22](/backend/06-reliability/steady-state-definition/)           |
| Meta M2    | 回復工具依賴已故障的系統（BGP / DNS / 遠端存取），恢復陷入循環等待                              | [6.14](/backend/06-reliability/dependency-reliability-budget/)、[8.14](/backend/08-incident-response/multi-incident-coordination/) |

## 判讀訊號

| 訊號                                  | 判讀條件                                                        | 行動建議                                       |
| ------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------- |
| DR plan 寫在 wiki、過去 12 個月未演練 | 回復能力不可信 — plan 與 production 可能已漂移                  | 排入下季 tabletop + partial failover 演練      |
| backup 有排程、restore 從未跑過       | 備份完整性未知 — restore 是唯一能證明備份可用的手段             | 安排 restore drill、量測實際 RTO               |
| failover 配置與 production 漂移       | failover 路徑不可靠 — 任何 infra 變更都可能讓 failover 腳本失效 | 建 failover config diff 定期掃描               |
| RTO / RPO 是估值、不是量值            | 恢復承諾不可信 — 未被演練量測過的數字只是猜測                   | 用 restore drill 量測實際值、更新承諾          |
| rollback 需要手動 SQL 或脫離部署流程  | rollback 路徑高風險 — 手動操作在壓力下容易出錯                  | 把 rollback 步驟自動化進 deploy pipeline       |
| 演練缺口未回寫到 backlog              | 演練價值流失 — 發現問題但不追蹤等同未發現                       | 每次演練產出寫入 6.21 reliability debt + owner |

## 交接路由

- [05 部署平台](/backend/05-deployment-platform/)：blue-green / region failover 實作
- [6.4 chaos testing](/backend/06-reliability/chaos-testing/)：chaos 暴露的弱點變成 DR 演練題目
- [6.11 migration safety](/backend/06-reliability/migration-safety/)：migration rollback 演練
- [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)：replay 是 DR 回復的前提
- [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/)：演練缺口回寫
- [6.25 provider dependency release gate](/backend/06-reliability/provider-dependency-release-gate/)：provider 變更的 rollback 實作示範
- [8.3 止血回復](/backend/08-incident-response/containment-recovery-strategy/)：演練結果作為事中決策素材
- [8.6 演練與值班](/backend/08-incident-response/drills-and-oncall-readiness/)：DR 結果回饋到團隊技能建設
- [8.15 vendor 事故](/backend/08-incident-response/vendor-dependency-incident/)：多 vendor / 多區 failover 路徑
