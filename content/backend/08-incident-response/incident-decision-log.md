---
title: "8.19 Incident Decision Log"
date: 2026-05-02
description: "把事中假設、決策、證據、回退條件與責任人留下可復盤紀錄"
weight: 19
---

## 大綱

- decision log 的責任：保留事故期間的關鍵假設、決策、證據與責任人
- 欄位：timestamp、decision、context、evidence、owner、expected effect、rollback condition
- 決策類型：severity change、containment、rollback、degradation、customer communication、vendor escalation
- evidence 連結：dashboard、log query、trace、status page、customer report、audit log
- 事中使用：支援 handoff、multi-incident coordination、stakeholder update
- 事後使用：支援 post-incident review、action item、runbook update
- 跟 scribe 的關係：scribe 記錄事實，decision log 強調決策與證據鏈
- 反模式：Slack 討論就是紀錄；事後才補決策理由；rollback 條件沒寫清楚

[Incident decision log](/backend/knowledge-cards/incident-decision-log/) 的核心價值是讓事故決策可回放。事故現場的關鍵是每次都能說清楚「為何這樣選、基於什麼證據、何時該回退」。

## 概念定位

Incident decision log 是事故期間的決策紀錄，責任是讓團隊能回看當時基於哪些證據做了哪些取捨。

這一頁處理的是事中決策可追溯性。事故期間的資訊通常不完整；decision log 的責任是保留每個決策的時間、證據、owner 與回退條件。

decision log 也是交班工具。當事故跨班次或跨時區，新的 IC 只要接上決策序列與證據鏈，就能在幾分鐘內接手，而不需要重建整段背景。

## 核心判讀

判讀 decision log 時，先看決策是否有 evidence，再看決策是否有預期效果與回退條件。

重點訊號包括：

- severity 變更是否留下理由與 impact scope
- containment / rollback 是否有 owner 與 rollback condition
- customer communication 是否連到當時已知事實
- handoff 是否能靠 decision log 接上脈絡
- post-incident review 是否能直接引用決策紀錄

| 決策欄位           | 最小可用判準         | 判讀價值           |
| ------------------ | -------------------- | ------------------ |
| Decision / Time    | 有清楚決策內容與時間 | 建立決策先後與節奏 |
| Context / Evidence | 有對應證據與限制     | 避免事後合理化     |
| Owner              | 有責任人可追蹤       | 提升執行一致性     |
| Expected Effect    | 有預期影響描述       | 判斷決策是否有效   |
| Rollback Condition | 有回退門檻           | 控制次生風險       |

## 欄位模型

Incident decision log 的欄位模型要同時支援事中交班與事後復盤。欄位過少會失去證據鏈，欄位過多會讓事故現場寫不下去。

| 欄位               | 責任                          | 範例                                |
| ------------------ | ----------------------------- | ----------------------------------- |
| Timestamp          | 記錄決策時間                  | 2026-05-02T10:15Z                   |
| Decision           | 寫清楚採取或暫緩的動作        | rollback API v42                    |
| Context            | 說明當時問題與限制            | p95 latency 超 SLO，trace sample 低 |
| Evidence           | 連到 dashboard、query、ticket | burn rate chart、support case       |
| Owner              | 指定執行或追蹤責任人          | IC、service owner、comms lead       |
| Expected effect    | 說明預期改善或風險            | 10 分鐘內 error rate 下降           |
| Rollback condition | 說明何時回退這個決策          | queue lag 超門檻即停止              |
| Follow-up          | 標記後續查證或復盤項目        | 補 runbook、補 alert                |

Timestamp 要使用一致時間基準。事故跨工具、跨時區、跨 vendor 時，decision log 應保留標準化時間，必要時也保留來源原始時間。

Decision 欄位要寫具體動作。`處理中`、`觀察一下` 這類描述難以支援復盤；`rollback API v42`、`disable feature flag checkout_new_route`、`escalate to vendor support` 才能回放。

Context 欄位要保留限制。事故期間的資料常有缺口，decision log 應寫出 evidence 的 completeness、freshness、confidence 與已知盲區。

Expected effect 與 rollback condition 是控制次生風險的核心。每個止血或回復決策都應說明預期看到什麼改善，以及看到什麼訊號時要撤回或改路線。

## 決策類型

Incident decision log 需要覆蓋事故期間會改變路由的決策。聊天可以保留在原頻道；每個會影響分級、止血、回復、通訊或責任的動作都應進 log。

| 決策類型               | 記錄重點                          | 下游用途           |
| ---------------------- | --------------------------------- | ------------------ |
| Severity change        | impact scope、customer pain、SLO  | 對齊分級與通訊節奏 |
| Containment            | 降級、限流、隔離、停用功能        | 判斷止血是否有效   |
| Rollback / failover    | 版本、流量、資料相容性            | 支援回復與復盤     |
| Customer communication | 對外說法、已知事實、限制          | 保持內外部訊息一致 |
| Vendor escalation      | vendor、ticket、ETA、替代方案     | 管理外部依賴事故   |
| Security split         | 資安 evidence、access、disclosure | 分流到 security IR |

Severity change 需要留下 impact scope。升級或降級事故等級時，decision log 應能回答哪些客戶、功能、區域、SLO 或商業風險支撐這個決策。

Containment 決策需要留下副作用。限流、降級、停用功能或隔離 tenant 都會改變使用者體驗，decision log 應記錄預期影響與解除條件。

Rollback / failover 決策需要留下資料相容性。版本回退、流量切換與資料 migration 可能互相影響，log 應記錄當時對資料風險的判斷。

Customer communication 決策需要與 evidence 對齊。對外說法應引用當時已確認事實，並標示仍在查證的範圍，避免內外部敘事分裂。

## 判讀訊號

- 事故結束後沒人記得為何選擇 rollback 而非 degradation
- IC handoff 後，新 IC 需要重問所有背景
- 對外通訊內容與內部決策依據對不起來
- 復盤時只能翻聊天紀錄拼時間線
- 同一決策被重複討論，因為缺少已決事項紀錄

常見場景是 containment 與 rollback 在不同頻道同步進行，事後很難重建為什麼先做 A 再做 B。decision log 若能同步記錄選項、證據與回退條件，PIR 可以直接把差異轉成改進項目。

## 事中使用

Decision log 的事中責任是支援 handoff、multi-incident coordination 與 stakeholder update。它讓事故團隊在壓力下維持共同記憶。

IC handoff 時，decision log 應提供最近決策、未完成動作、回退條件與目前 evidence 限制。新 IC 不需要重新翻整段聊天，就能接上決策脈絡。

Multi-incident coordination 時，decision log 能避免資源衝突。若兩個事故都需要同一組 database owner、comms lead 或 rollback window，決策紀錄能幫 IC pool 排序。

Stakeholder update 時，decision log 能保護對外敘事。status page、客戶通知與管理層更新應引用同一組已確認事實，並同步更新 impact assessment。

## 事後使用

Decision log 的事後責任是支援 post-incident review。復盤需要理解當時的資訊條件，再用事後結果評估判讀品質與流程缺口。

Post-incident review 應從 decision log 取出三種材料：正確決策、錯誤假設與缺少 evidence 的決策。三者對應不同改善方向。

正確決策可以變成 runbook。若某次降級、rollback 或 vendor escalation 路線有效，應把 decision log 中的條件與步驟回寫到 runbook。

錯誤假設可以變成 readiness 或 experiment 題目。若當時相信 fallback 會吸收失敗但實際沒有，這個假設應回寫到 06 的 chaos 或 DR drill。

缺少 evidence 的決策可以回寫到 04。若團隊因 telemetry data quality、trace 斷鏈或 impact scope 不清而延遲決策，缺口應回到 observability readiness 與 data quality。

## 常見反模式

Incident decision log 的反模式通常來自把聊天紀錄當作決策紀錄。聊天紀錄保存討論，decision log 保存「已決事項與證據鏈」。

| 反模式           | 表面現象                    | 修正方向                            |
| ---------------- | --------------------------- | ----------------------------------- |
| Slack 討論即紀錄 | 復盤時翻聊天拼脈絡          | 獨立 decision log 欄位              |
| 事後補決策理由   | PIR 才重建當時為何這樣做    | 事中記錄 context / evidence         |
| 回退條件缺失     | rollback 後不知道何時改路線 | 每個高風險決策寫 rollback condition |
| Evidence 不連結  | 決策只寫結論                | 連到 dashboard / query / ticket     |
| Owner 不明       | 決策已定但無人追蹤          | 每筆決策指定 owner                  |

Slack 討論即紀錄會讓復盤成本升高。聊天頻道保留的是互動過程，decision log 應抽出可回放的決策摘要。

事後補決策理由容易產生 hindsight bias。事中記錄當時的 evidence 與限制，才能讓 PIR 同時評估判讀品質、流程品質與結果。

## 交接路由

- 08.2 incident command roles：定義誰維護 decision log
- 08.3 containment / recovery：記錄止血與回復決策
- 08.4 incident communication：對外更新引用同一組事實
- 08.12 IC handoff：交班時使用 decision log
- 08.5 post-incident review：把決策紀錄轉成復盤材料
- 04.17 telemetry data quality：標示 evidence 限制與偏誤
