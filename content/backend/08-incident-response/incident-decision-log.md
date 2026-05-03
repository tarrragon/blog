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

Incident decision log 的核心價值是讓事故決策可回放。事故現場的關鍵是每次都能說清楚「為何這樣選、基於什麼證據、何時該回退」。

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

## 判讀訊號

- 事故結束後沒人記得為何選擇 rollback 而非 degradation
- IC handoff 後，新 IC 需要重問所有背景
- 對外通訊內容與內部決策依據對不起來
- 復盤時只能翻聊天紀錄拼時間線
- 同一決策被重複討論，因為缺少已決事項紀錄

常見場景是 containment 與 rollback 在不同頻道同步進行，事後很難重建為什麼先做 A 再做 B。decision log 若能同步記錄選項、證據與回退條件，PIR 可以直接把差異轉成改進項目。

## 交接路由

- 08.2 incident command roles：定義誰維護 decision log
- 08.3 containment / recovery：記錄止血與回復決策
- 08.4 incident communication：對外更新引用同一組事實
- 08.12 IC handoff：交班時使用 decision log
- 08.5 post-incident review：把決策紀錄轉成復盤材料
- 04.17 telemetry data quality：標示 evidence 限制與偏誤
