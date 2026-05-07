---
title: "4.18 Observability Operating Model"
date: 2026-05-02
description: "定義 platform / service team / on-call 對訊號、dashboard、alert 與成本的 ownership"
weight: 18
---

## 大綱

- operating model 的責任：定義誰擁有訊號、誰維護 dashboard、誰處理 alert、誰承擔成本
- 角色分工：platform team、service team、on-call、incident commander、security / compliance
- ownership 欄位：owner、review cadence、retention、cost center、runbook link、deprecation date
- 生命週期：新增、審核、使用、修訂、淘汰
- 治理節奏：dashboard review、alert review、cost review、post-incident write-back
- 跟 04.15 cost attribution 的關係：成本歸屬是 operating model 的一部分
- 跟 08 的關係：事故時使用同一組 owner 與 escalation route
- 反模式：平台團隊擁有所有 alert；service team 不看 dashboard；成本無 owner

Observability operating model 的價值是把觀測從「工具責任」改成「服務責任」。平台團隊提供共用能力，服務團隊提供業務語意，on-call 使用這些資產做決策；operating model 負責固定三者的接口。

## 概念定位

Observability operating model 是把觀測資產的責任分配明確化的治理模型，責任是讓訊號有人維護、告警有人回應、成本有人決策。

這一頁處理的是 ownership。可觀測性需要平台工具、服務脈絡、操作責任與淘汰條件一起維持。

這層的判準是事故當下能否立刻知道誰要看哪個面板、誰有權調整閾值、誰負責決定淘汰過期訊號。dashboard 數量與 alert 覆蓋率只是輔助訊號。

## 角色分工

Observability operating model 的角色分工以「誰能做決策」為核心。owner 是有權維護、調整、下架或升級觀測資產的人，名義聯絡人只能作為補充欄位。

| 角色                  | 核心責任                              | 決策權限                           |
| --------------------- | ------------------------------------- | ---------------------------------- |
| Platform team         | 採集、儲存、查詢、成本與標準          | pipeline、schema convention、quota |
| Service team          | 服務語意、核心旅程與業務事件          | service dashboard、SLI、alert rule |
| On-call               | 事中判讀、runbook 使用與升級          | silence、escalate、incident intake |
| Incident commander    | 事故優先序、通訊節奏與決策紀錄        | severity、rollback、status update  |
| Security / compliance | audit log、PII、retention 與 evidence | retention、masking、access review  |
| Finance / cost owner  | 成本歸屬、預算與 chargeback           | quota、retention tier、cost review |

Platform team 的責任是維持共同語言。它需要定義 service name、environment、region、tenant、trace context、retention tier 與成本政策，讓跨服務查詢可行。

Service team 的責任是維持服務語意。它需要定義哪些 user journey 是核心、哪些錯誤影響用戶、哪些 dependency failure 需要 alert、哪些 dashboard 仍有操作價值。

On-call 的責任是把資產用在事中決策。alert 應能帶到 dashboard、runbook 與 owner，讓 operating model 真正進入操作流程。

Security / compliance 的責任是把觀測資料的證據價值與資料風險同時納入治理。audit log、PII redaction、retention 與 access review 需要在觀測模型中有明確 owner。

## 核心判讀

判讀 operating model 時，先看每個觀測資產是否有 owner，再看 owner 是否有權限與節奏採取行動。

重點訊號包括：

- dashboard 是否有明確使用者與 review cadence
- alert 是否有 [runbook](/backend/knowledge-cards/runbook/)、owner 與 escalation path
- 高成本訊號是否能對應服務價值與成本中心
- post-incident review 是否能回寫到訊號 owner
- orphan dashboard 與 stale alert 是否有清理流程

| 資產類型         | Owner                  | 週期   | 關閉條件               |
| ---------------- | ---------------------- | ------ | ---------------------- |
| Dashboard        | service team + on-call | 月檢   | 無使用者、無判讀價值   |
| Alert            | service owner          | 週檢   | 重複、誤報高、無行動   |
| Query / Schema   | platform + service     | 變更檢 | 欄位漂移、查詢成本失控 |
| Cost Attribution | cost owner             | 月檢   | 成本缺少服務價值對應   |

## 觀測資產欄位

Observability asset 需要像服務 artifact 一樣有 metadata。沒有 metadata 的 dashboard、alert、query 與 schema 會在幾個月後變成無人敢刪、無人敢改、也無人信任的資產。

| 欄位             | 責任                     | 判讀用途                          |
| ---------------- | ------------------------ | --------------------------------- |
| Owner            | 指定維護與決策責任       | 事故時知道找誰                    |
| User             | 說明誰會使用這個資產     | 判斷是否仍有操作價值              |
| Runbook link     | 連到下一步操作           | 讓 alert 能轉成行動               |
| Review cadence   | 定義檢視頻率             | 避免 stale dashboard / alert      |
| Cost center      | 對應服務或團隊成本       | 支援 chargeback 與 retention 決策 |
| Retention tier   | 指定保存時間與查詢粒度   | 平衡法規、事故與成本              |
| Deprecation date | 標示預計下架或重檢日期   | 避免觀測資產永久堆積              |
| Data limitation  | 標示抽樣、缺口與聚合限制 | 避免事中誤讀資料                  |

Owner 欄位要搭配權限才有意義。有效 owner 需要能調整 threshold、更新 dashboard、下架 query 或決定 retention，讓 ownership 成為可執行責任。

User 欄位能避免 dashboard 變成展示資產。面板若沒有明確使用者，例如 on-call、service owner、capacity planner 或 compliance reviewer，就很難判斷它是否仍值得維護。

Runbook link 是 alert 從通知變成行動的關鍵。每個可 page 的 alert 都應連到第一步查詢、初始判讀、升級條件與 rollback / degrade / wait 的決策路由。

Cost center 讓觀測成本有業務語意。高 cardinality、長 retention、full-fidelity trace 與大量 log indexing 都有價值，但價值需要由能受益的服務或團隊承擔與檢視。

## 生命週期

Observability operating model 的生命週期是新增、審核、使用、修訂與淘汰。這個生命週期讓訊號保持有用，並讓觀測資產累積在可治理範圍內。

1. 新增：服務變更、事故復盤、演練需求或合規要求產生新訊號。
2. 審核：確認 schema、成本、owner、runbook 與 retention。
3. 使用：進入 dashboard、alert、incident intake 或 SLO 計算。
4. 修訂：根據噪音、缺口、成本與使用頻率調整。
5. 淘汰：移除 stale alert、orphan dashboard、過期 query 與無價值高成本訊號。

新增訊號需要清楚的需求來源。最好的來源是 user journey、SLO、incident review、game day 或 audit requirement；最弱的來源是「可能有用」。

審核訊號需要同時看語意與成本。欄位是否穩定、cardinality 是否可控、retention 是否合理、PII 是否被遮罩、owner 是否能維護，都是訊號上線前的固定問題。

淘汰是 operating model 的必要能力。舊 alert 沒有人敢關，會增加 alert fatigue；舊 dashboard 沒有人敢刪，會讓事故時不知道哪個面板可信。

## 判讀訊號

- alert 觸發後沒人知道該由平台或服務團隊處理
- dashboard 存在但半年無人打開
- 成本暴增時只能找平台團隊吸收
- post-incident review 指派 action item，但沒有訊號 owner
- service team 調整欄位後，平台查詢與 dashboard 斷裂

實務上常見的治理斷點是「有 owner 名字，缺 owner 權限」。owner 需要能調整 alert、建立或下架 dashboard、分配成本，治理流程才會停在資產責任人，減少回流到平台集中處理的積壓。

## 治理節奏

Operating model 的治理節奏把觀測資產拉回日常工程流程。review cadence 的重點是定期回答「這個資產還能支援決策嗎」，會議只是其中一種執行形式。

| 節奏                     | 核心問題                         | 典型輸出                           |
| ------------------------ | -------------------------------- | ---------------------------------- |
| Dashboard review         | 面板是否仍有人用、是否對應旅程   | 更新、合併、下架                   |
| Alert review             | alert 是否可行動、噪音是否可接受 | threshold 調整、silence、runbook   |
| Cost review              | 成本是否對應服務價值             | retention tier、sampling policy    |
| Schema review            | 欄位是否穩定、是否跨服務一致     | schema migration、drift 修正       |
| Post-incident write-back | 復盤缺口是否回寫到訊號與 owner   | 新 alert、新 dashboard、新 runbook |

Dashboard review 應看使用情境與操作價值。面板需要支援 on-call 的前 10 分鐘、capacity planning 或 SLO review；脫離這些用途的面板適合合併、重命名或下架。

Alert review 應看行動品質。alert 若經常觸發但缺少明確處置，通常更適合變成 dashboard signal、ticket 或長期治理項。

Cost review 應看服務價值。觀測成本上升不一定是壞事，但需要能說明這些成本降低了哪一種事故風險、合規風險或容量風險。

## 常見反模式

Observability operating model 的反模式通常是責任集中或責任懸空。前者讓平台團隊成為所有訊號的瓶頸，後者讓服務團隊在事故時找不到可信入口。

| 反模式             | 表面現象                         | 修正方向                        |
| ------------------ | -------------------------------- | ------------------------------- |
| 平台擁有所有 alert | 服務語意缺失，告警只能看基礎設施 | service owner 擁有服務級 alert  |
| 服務各自為政       | 欄位、命名、retention 不一致     | platform 提供 schema convention |
| owner 缺權限       | 只能被追責，缺少資產修正能力     | owner 取得調整、下架與預算權限  |
| 成本無歸屬         | 高成本訊號由平台吸收             | cost center 與 retention tier   |
| 復盤無回寫         | action item 停在文件             | write-back 到 dashboard / alert |

平台擁有所有 alert 會讓服務語意被削弱。平台知道 pipeline 與 infra，但通常不知道某個錯誤是否影響 checkout、資料同步、帳單或客戶 SLA。

服務各自為政會讓跨服務事故難以判讀。每個服務都可以有自己的 dashboard，但 service name、environment、region、tenant、error class 與 trace context 需要共用標準。

復盤無回寫會讓 operating model 停在文件。post-incident review 揭露的偵測缺口、runbook 缺口與成本缺口都應回到對應 owner 的資產生命週期。

## 與事故流程的關係

Observability operating model 是事故流程的責任基礎。事故期間，IC 需要知道哪些訊號可信、哪個 owner 能解釋欄位、誰能調整 alert、誰能決定保留或匯出 evidence。

在 incident command 中，observability owner 不一定是 incident commander，但必須能提供訊號解釋與操作建議。當 telemetry data quality 有限制時，owner 需要把限制交給 scribe 或 [decision log](/backend/knowledge-cards/incident-decision-log/)。

在 runbook lifecycle 中，dashboard、alert 與 query 都應被視為 runbook 的依賴。runbook 更新時，如果沒有同步更新觀測資產，下一次事故仍會走到舊入口。

## 交接路由

- 04.4 dashboard / alert：設計 owner、runbook 與停止條件
- 04.8 signal governance loop：淘汰 stale alert 與 orphan dashboard
- 04.15 cost attribution：把成本接回 owner 與服務
- 08.2 incident command roles：事故時使用相同 ownership 模型
- 08.16 runbook lifecycle：把觀測資產接進 runbook 版本治理
