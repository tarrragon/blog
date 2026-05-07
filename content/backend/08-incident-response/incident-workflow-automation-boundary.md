---
title: "8.21 Incident Workflow Automation Boundary"
date: 2026-05-02
description: "定義哪些事故流程適合自動化，哪些決策需要保留人工確認"
weight: 21
---

## 大綱

- automation boundary 的責任：把可自動化的事故工作與需要人工判斷的決策分開
- 適合自動化：channel creation、role reminder、template update、status sync、evidence collection、ticket creation
- 需要人工確認：severity upgrade、customer impact statement、rollback execution、security disclosure、compensation
- guardrail：approval、dry run、rollback condition、audit log、rate limit
- 風險：自動化誤升級、誤通知、錯誤 rollback、過度信任 enrichment
- 跟 vendor / IR platform 的關係：工具支援流程，決策邊界仍需由團隊定義
- 跟 07 的交接：高風險自動化需要權限、稽核與安全例外治理
- 反模式：把所有 incident workflow 都交給 bot；bot 產生錯誤 status update；自動化沒有停止條件

Incident workflow automation boundary 的價值是把速度與責任同時保住。事故流程中有大量可標準化動作，適合自動化；但分級、回退、對外說法與資安披露仍需要情境判斷，必須保留人類決策責任。

## 概念定位

Incident workflow automation boundary 是事故流程自動化的決策邊界，責任是讓工具減少手動摩擦，同時保留高風險決策的人類確認。

這一頁處理的是自動化取捨。事故流程有大量可預期動作，但 severity、rollback、對外說法與資安披露都帶有情境判斷與責任風險。

邊界定義越清楚，工具越有價值。當團隊先定義好「可自動化動作」與「需人工確認動作」，bot 才能專注減少摩擦，而不會擴大決策風險。

## 核心判讀

判讀 automation boundary 時，先看動作是否可逆，再看錯誤自動化的影響範圍。

重點訊號包括：

- 自動化動作是否只建立容器、收集資料或提醒角色
- 高風險動作是否有 approval 與 audit log
- bot 產出的資訊是否標示 confidence 與來源
- workflow 是否有 stop condition 與 manual override
- 自動化是否支援 IC，並保留 IC 的決策責任

| 動作類型       | 自動化適配 | 安全護欄               |
| -------------- | ---------- | ---------------------- |
| 流程容器建立   | 高         | 頻道命名規範、角色模板 |
| 證據彙整與同步 | 高         | 來源標示、信心標示     |
| 分級與回退決策 | 低         | 人工核准、雙重確認     |
| 對外狀態更新   | 中         | 審核流程、回退機制     |
| 高風險操作觸發 | 低         | 權限隔離、audit log    |

## 自動化分層

Incident workflow automation boundary 的分層責任是把「節省摩擦」和「替人決策」分開。越接近容器建立與資料彙整，越適合自動化；越接近分級、回復、對外聲明與資安披露，越需要人工確認。

| 層級                | 適合自動化內容                           | 風險                     |
| ------------------- | ---------------------------------------- | ------------------------ |
| Workflow setup      | 建頻道、建 ticket、套模板、提醒角色      | 命名錯誤、重複建立       |
| Evidence collection | 拉 dashboard、query、status、deploy      | 資料過期、來源誤解       |
| Enrichment          | 加 owner、service map、recent change     | 關聯錯誤、信心未標示     |
| Recommendation      | 建議 severity、runbook、next action      | 建議被誤當決策           |
| Execution           | rollback、traffic shift、customer update | 次生事故、法務或資安風險 |

Workflow setup 適合高度自動化。這層動作可逆、低風險，能讓 IC 省下開頻道、拉人、建文件與貼模板的時間。

Evidence collection 適合自動化，但要標示來源與時間。bot 可以貼 dashboard、query、vendor status、recent deploy 與 support ticket，但應標示 timestamp、source 與 confidence。

Enrichment 適合輔助判讀。service owner、dependency map、runbook、recent change 與 feature flag 狀態可以自動補上，但要允許 IC 修正。

Recommendation 應保持建議語氣。bot 可以建議 severity、runbook 或 next action，但 IC 需要確認，並把採納或拒絕寫進 [decision log](/backend/knowledge-cards/incident-decision-log/)。

Execution 是高風險層。rollback、traffic shift、status page publish、customer email、security disclosure 與 compensation 都應有人工確認、權限隔離與 audit log。

## 人工確認邊界

人工確認邊界的責任是保留責任判斷。自動化可以加速準備與整理，但高風險決策需要有人確認情境、證據與後果。

| 需要確認的動作            | 原因                         | 最小護欄                          |
| ------------------------- | ---------------------------- | --------------------------------- |
| Severity upgrade          | 影響通訊、值班與 stakeholder | IC 確認、impact evidence          |
| Customer impact statement | 影響外部信任與合約           | Comms / IC review、confidence     |
| Rollback execution        | 可能影響資料、版本與流量     | service owner approval、dry run   |
| Security disclosure       | 涉及法規、證據與對外責任     | security lead、legal route        |
| Compensation              | 涉及金額與商務政策           | business owner、reconciled impact |

Severity upgrade 需要 IC 確認。bot 可以根據 burn rate、ticket 數與 status page 建議升級，但 severity 會改變通訊節奏與資源分配，需要保留人類責任。

Customer impact statement 需要 comms 與 IC 協作。自動化可以產生初稿，但對外文字要反映已確認事實、confidence 與下一次更新時間。

Rollback execution 需要 service owner 確認。回滾可能受到 migration、feature flag、cache、client contract 與資料相容性影響，錯誤率只是判斷輸入之一。

Security disclosure 需要資安與法務路由。涉及資料外洩、權限濫用或合規通知時，自動化只能建立容器與 evidence checklist，披露決策需要專責角色確認。

## Guardrail 設計

Automation guardrail 的責任是讓自動化行為可控、可停、可審計。每個 bot action 都應有範圍、權限、回退與紀錄。

| Guardrail          | 責任                       | 適用動作                          |
| ------------------ | -------------------------- | --------------------------------- |
| Approval           | 高風險動作前取得確認       | rollback、status update、severity |
| Dry run            | 先展示將要做的改變         | rollback、ticket bulk update      |
| Audit log          | 保存誰觸發、何時、做了什麼 | 所有自動化                        |
| Rate limit         | 限制通知、查詢與變更頻率   | paging、ticket、status sync       |
| Manual override    | 允許 IC 停用或接管 bot     | 所有事中自動化                    |
| Confidence label   | 標示資料來源與可信度       | enrichment、recommendation        |
| Rollback condition | 定義自動化後如何撤回       | workflow update、routing change   |

Approval 適合高風險動作。批准者應是對後果有責任的人，例如 IC、service owner、security lead、comms lead 或 business owner。

Dry run 能降低自動化黑箱感。bot 在執行前顯示即將改動的 status page、rollback target、ticket list 或 notification recipient，讓人類能快速檢查。

Manual override 是事故流程的基本安全閥。IC 需要能暫停 bot、停用自動更新、切換到手動流程，並留下 decision log。

Confidence label 能避免 enrichment 被誤當事實。自動補出的 owner、recent deploy、vendor status 或 impact estimate 都應顯示來源與時間。

## 判讀訊號

- bot 自動開 incident，但沒有人確認 severity
- status page 被 template 自動更新，內容與實際影響不一致
- rollback 被自動觸發後，團隊才發現資料 migration 還在進行
- enrichment 資料來源過期，但被當成事實使用
- 自動化成功率高，但事故期間沒有人知道如何停用

典型場景是 bot 能快速建立 incident channel、拉齊角色與初版模板，這些都能穩定節省時間；但若 bot 直接執行 rollback 或發布對外影響描述，錯誤成本會急遽上升。邊界的責任就是把這條線畫清楚。

## Vendor / IR Platform 關係

IR platform 的責任是支援流程，決策邊界仍由團隊定義。Pager、incident channel、status page、postmortem template 與 workflow engine 都需要由團隊配置 owner、approval、field schema 與 audit route。

On-call 與 IR 工具適合自動化流程容器。它們可以建立 incident、指派角色、同步 status、建立 ticket、提醒 handoff 與收集 evidence。

Status page 工具適合自動化草稿與同步。公開發布前仍需要 IC 或 comms lead 確認，因為影響描述、confidence 與補償語氣都會影響客戶信任。

Postmortem 工具適合自動收集 timeline、decision log 與 action item。復盤結論仍需要人類判讀，把事故教訓回寫到 04、06、07 與產品流程。

## 常見反模式

Incident workflow automation 的反模式通常來自把工具速度當成流程成熟度。速度有價值，但責任邊界、資料可信度與人工確認才決定事故流程是否可靠。

| 反模式                 | 表面現象                         | 修正方向                           |
| ---------------------- | -------------------------------- | ---------------------------------- |
| Bot 接管所有流程       | 分級、通訊、rollback 都自動執行  | 分層 automation boundary           |
| Status update 自動發布 | 對外文字與實際 impact 不一致     | 草稿自動化，發布人工確認           |
| Enrichment 無來源      | bot 補的 owner / impact 被當事實 | 標示 source、timestamp、confidence |
| 無 stop condition      | 自動化錯誤後持續擴散             | manual override、rate limit        |
| 無 audit log           | 事後不知道誰觸發了什麼           | 所有 bot action 留紀錄             |

Bot 接管所有流程會讓事故責任模糊。工具可以準備資料、提示角色與建議下一步，但 IC 仍要負責分級、優先序與高風險決策。

Enrichment 無來源會製造錯誤安全感。自動補充的 owner、recent deploy 或 customer impact 若沒有 timestamp 與來源，團隊容易把推測當成事實。

無 audit log 會破壞復盤。自動化動作也是事故事件的一部分，應能被 decision log 與 post-incident review 回放。

## 與資安治理的關係

Incident workflow automation 需要接到資安權限與例外治理。自動化越靠近 rollback、traffic shift、status publish、customer data 或 security disclosure，越需要 least privilege、approval、audit log 與 exception review。

高風險自動化應使用分離權限。建立 incident channel 與讀 dashboard 可以是低權限；執行 rollback、讀 audit log、匯出客戶資料或發布對外聲明，需要更高權限與明確核准。

## 交接路由

- 08.1 severity trigger：定義哪些升級可自動建議、哪些需人工確認
- 08.2 incident command roles：讓 bot 支援角色提醒與交接
- 08.4 incident communication：保護對外通訊的人類確認邊界
- 08.19 incident decision log：自動化動作也要留下決策紀錄
- 07.14 security exception / tripwire：高風險自動化接安全例外治理
- 05 deployment platform：rollback / rollout automation 的實作邊界
