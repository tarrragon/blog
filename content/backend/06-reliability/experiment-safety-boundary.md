---
title: "6.20 Experiment Safety Boundary"
date: 2026-05-02
description: "定義 chaos、load test、DR drill 的 blast radius、停止條件與權限約束"
weight: 20
---

## 大綱

- experiment safety boundary 的責任：讓可靠性實驗可控、可停、可回復
- 實驗類型：chaos test、load test、failover drill、rollback rehearsal、DR drill
- blast radius：服務、tenant、region、dependency、資料範圍
- 停止條件：SLO burn、error rate、latency、queue lag、customer impact、cost threshold
- 權限約束：誰能啟動、誰能停止、誰能擴大範圍
- evidence 要求：假設、步驟、觀測訊號、結果、回復時間、action item
- 跟 07 的交接：高風險演練需要權限與稽核約束
- 反模式：直接在 production 打 chaos；缺停止條件；實驗 owner 與 incident commander 不清楚

Experiment safety boundary 的價值在於讓失敗驗證可重播、可停止、可回復。實驗越接近真實失效，對團隊越有學習價值；同時也越需要清楚邊界，避免「為了驗證韌性」而產生額外事故。

## 概念定位

Experiment safety boundary 是定義可靠性實驗安全範圍的控制面，責任是讓團隊能主動驗證失敗，同時控制實驗造成的實際風險。

這一頁處理的是實驗邊界。可靠性實驗的價值來自接近真實失效，但越接近真實，越需要明確 blast radius、停止條件與回復路徑。

安全邊界是一組事前契約：誰能啟動、誰有停止權、觸發什麼門檻必須終止、終止後怎麼回復。契約存在時，團隊才能在實驗中保持速度，同時控制風險成本。

## 核心判讀

判讀 experiment safety 時，先看實驗假設是否明確，再看實驗失控時是否能立刻停止與回復。

重點訊號包括：

- experiment hypothesis 是否連到具體 failure mode
- blast radius 是否限制 service、tenant、region 或 traffic percentage
- stop condition 是否連到 SLO / customer impact / cost
- rollback / failover 是否在實驗前準備好
- observer、executor、approver 是否分工清楚

| 控制面   | 最小可用判準                              | 失控信號             |
| -------- | ----------------------------------------- | -------------------- |
| 範圍控制 | blast radius 限在服務 / 區域 / 流量百分比 | 影響擴散到非目標服務 |
| 停止條件 | stop condition 連到 SLO / impact / cost   | 超門檻仍持續實驗     |
| 權限治理 | 啟動者、停止者、核准者分離                | 需要額外查證誰在操作 |
| 回復能力 | rollback / failover 已預演                | 終止後回復時間失控   |
| 證據留存 | hypothesis 與結果可回放                   | 成功與失敗都不可重現 |

## 實驗類型

Experiment safety boundary 需要依實驗類型調整邊界。不同實驗打到的系統層不同，學習價值與實際風險也不同。

| 實驗類型           | 驗證問題                       | 主要邊界                          |
| ------------------ | ------------------------------ | --------------------------------- |
| Chaos test         | 依賴、節點、網路失效是否可承受 | service、region、dependency       |
| Load test          | 流量與資料量是否超過容量模型   | traffic percentage、cost、quota   |
| Failover drill     | 切換流程是否可執行             | region、data replication、routing |
| Rollback rehearsal | 回復到前一版本是否安全         | version、migration、feature flag  |
| DR drill           | 災難恢復是否符合 RTO / RPO     | data scope、region、access        |

Chaos test 的風險在於故障注入接近真實失效。它需要明確 [steady state](/backend/knowledge-cards/steady-state/)、觀測訊號與停止條件，讓團隊知道實驗如何驗證韌性。

Load test 的風險在於放大共享依賴。測試流量可能壓到 database、cache、broker、third-party API 或 observability pipeline，因此邊界要包含共享資源與成本上限。

Failover drill 的風險在於切換後的長尾狀態。流量切過去只是第一步，團隊還需要看資料同步、cache warmup、queue drain、DNS / routing propagation 與客戶端行為。

Rollback rehearsal 的風險在於資料與版本相容性。程式可回滾不代表 schema、message、cache、feature flag 與 client contract 都能同步回到安全狀態。

DR drill 的風險在於權限、資料與外部通訊。災難恢復通常涉及高權限操作、備份還原與跨團隊協作，因此需要額外 audit trail 與 incident communication 準備。

## Boundary 契約

Experiment boundary 契約的責任是讓實驗在開始前就具備可停止、可回復與可復盤條件。契約應被寫成實驗 artifact，並納入可回查的操作紀錄。

| 契約欄位       | 責任                          | 判讀用途                 |
| -------------- | ----------------------------- | ------------------------ |
| Hypothesis     | 說明要驗證的 failure mode     | 避免實驗變成任意故障注入 |
| Blast radius   | 限制服務、tenant、region 範圍 | 控制實際影響             |
| Steady state   | 定義實驗期間應維持的狀態      | 判斷實驗是否成功         |
| Stop condition | 定義終止門檻                  | 讓失控時能立刻停手       |
| Rollback path  | 定義回復步驟                  | 降低終止後的恢復成本     |
| Authority      | 定義啟動、停止與擴大權限      | 避免事中權責不清         |
| Evidence       | 定義要收集的觀測與決策紀錄    | 支援復盤與可重播         |

Hypothesis 是實驗的錨點。好的假設會說明「當 dependency timeout 發生時，checkout 應進入 degraded mode，SLO burn rate 應維持在門檻內」，而不只是「關掉某個服務」。

Blast radius 需要同時包含技術範圍與客戶範圍。技術範圍是 service、region、cluster、dependency；客戶範圍是 tenant、plan、traffic percentage 或 internal-only cohort。

Stop condition 需要對應使用者影響。CPU 上升可以作為輔助訊號，但停止條件更應包含 SLO burn、error rate、latency、queue lag、customer ticket、成本與安全事件。

Authority 需要事前分清。executor 可以啟動實驗，observer 可以判讀訊號，incident commander 或 designated stop owner 必須有權直接終止實驗。

## 判讀訊號

- chaos 實驗描述只有「打掉節點」，沒有 steady state 與停止條件
- load test 影響共享 dependency，其他服務被連帶拖垮
- DR drill 的停止擴大條件需要臨場討論
- 實驗成功但沒有 evidence，可重播性不足
- 實驗權限過寬，值班人員不知道誰在操作

常見事故型場景是 load test 誤傷共享依賴，導致無關服務一起退化。若實驗前有 boundary 契約，至少會先限制流量比例、設定跨服務告警與 stop condition，讓問題停留在演練範圍內。

## Stop Condition 設計

Stop condition 的責任是把「什麼時候停」變成可觀測門檻。實驗期間不應靠臨場感覺判斷是否繼續，應根據預先同意的訊號停止或縮小範圍。

| 停止條件        | 常見門檻                              | 路由                         |
| --------------- | ------------------------------------- | ---------------------------- |
| SLO burn        | 短窗 burn rate 超過 policy            | 終止實驗，進 incident intake |
| Customer impact | ticket、RUM、synthetic probe 異常     | 終止或降到 internal cohort   |
| Queue lag       | lag 超過 drain 能力                   | 暫停流量，啟動 drain plan    |
| Error rate      | 目標服務或相鄰服務錯誤率上升          | 縮小 blast radius            |
| Cost threshold  | cloud cost 或 observability cost 暴增 | 終止 load / trace 擴張       |
| Security signal | audit、WAF、IAM 異常                  | 停止實驗，轉 07 / 08 分流    |

SLO burn 是最適合作為 stop condition 的可靠性訊號。它能把多個低層訊號聚合成使用者影響，並且直接接到 error budget 與 release policy。

Customer impact 是停止條件的高優先訊號。即使 backend 指標尚未超標，只要 RUM、synthetic probe、support ticket 或 status page evidence 顯示客戶受影響，實驗就應縮小或終止。

Security signal 需要獨立路由。若實驗觸發異常權限、audit log gap、WAF event 或資料外送風險，應停止 reliability experiment，改由 security / incident response 流程判讀。

## Evidence 與復盤

Experiment evidence 的責任是讓實驗結果可被重播、比較與回寫。一次實驗不論成功或失敗，都應產出可被後續 readiness、release gate 與 incident drill 使用的證據。

| Evidence 欄位 | 責任                         | 後續用途                                                                         |
| ------------- | ---------------------------- | -------------------------------------------------------------------------------- |
| Hypothesis    | 保留原始假設                 | 判斷成功或失敗                                                                   |
| Timeline      | 記錄開始、注入、停止、回復   | 產生 incident / drill 時間線                                                     |
| Signal set    | 保存 dashboard、query、alert | 回寫 04 observability readiness                                                  |
| Decision log  | 保存停止、擴大、回復決策     | 支援 08 [incident decision log](/backend/knowledge-cards/incident-decision-log/) |
| Action items  | 保存缺口與 owner             | 進入 reliability debt backlog                                                    |

成功實驗也需要 evidence。成功代表某個假設在某個範圍內成立，未必代表所有流量、region、tenant 或依賴都安全；evidence 能保留適用範圍。

失敗實驗需要分清系統缺口與實驗缺口。系統缺口可能是 fallback 沒生效；實驗缺口可能是 stop condition 不清、dashboard 缺訊號或 owner 權限不足。兩者回寫路由不同。

## 常見反模式

Experiment safety 的反模式通常來自把可靠性實驗當成勇敢行為。可靠性實驗的價值在設計、控制與學習，風險承受只是需要被管理的成本。

| 反模式                  | 表面現象                      | 修正方向                          |
| ----------------------- | ----------------------------- | --------------------------------- |
| 直接打 production chaos | 真實但邊界不清                | 先定義 cohort、stop condition     |
| 無 steady state         | 只知道打壞了什麼              | 補 6.22 穩態定義                  |
| 無 stop owner           | 超門檻後仍等會議決定          | 指定有權停止的人                  |
| 缺 evidence             | 實驗做過但缺少重播材料        | 保存 hypothesis、timeline、signal |
| 權限過寬                | 任意工程師可擴大 blast radius | 啟動、停止、擴大權限分離          |

直接打 production chaos 的問題是風險與學習常被混在一起。production 實驗可以有價值，但需要從小 cohort、清楚 stop condition 與完整 rollback path 開始。

缺 evidence 會讓實驗只留下口頭記憶。可靠性能力需要累積，實驗結果應能回寫到 readiness、release gate、runbook 與 incident drill。

## 交接路由

- 04.16 observability readiness：確認實驗可被觀測
- 06.4 chaos testing：定義故障注入場景
- 06.7 DR / rollback rehearsal：定義回復路徑
- 06.22 steady state definition：定義實驗前 [steady state](/backend/knowledge-cards/steady-state/)
- 07.23 shared controls：接 containment、rollback、degradation 共用控制面
- 08.6 drills / on-call readiness：把實驗轉成值班演練
