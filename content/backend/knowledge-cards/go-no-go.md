---
title: "Go/No-Go"
date: 2026-08-11
description: "說明在不可逆變更前的固定時點，由各職能分持一票宣告放行或停止的決策制度"
weight: 434
tags: ["backend", "knowledge-card", "reliability", "release-gate"]
---

Go/no-go 的核心概念是「在明確時點、由既定角色依事前判斷標準各自表態，任何一票 no-go 即停止」。它是 [gate decision](/backend/knowledge-cards/gate-decision/) 的會議形式——gate decision 說明證據怎麼轉成下一步，go/no-go 說明這個決策在什麼時點、由誰、以什麼儀式做出。名稱來自航太發射：發射前逐站點名，每個崗位回報 go 或 no-go，全數 go 才進入倒數。

## 概念位置

Go/no-go 位在 [release gate](/backend/knowledge-cards/release-gate/)、[cutover window](/backend/knowledge-cards/cutover-window/) 與 [stop condition](/backend/knowledge-cards/stop-condition/) 之間。Release gate 定義要過哪些檢查，cutover window 定義變更只能在哪個時段發生，go/no-go 把兩者收斂成一個決策時點：窗口開始前，該到的票都到、才放行。Stop condition 是 no-go 的事前定義——會議上的 no-go 應該是「某條 stop condition 成立」的宣告，而非臨場發明的疑慮。

三個成分讓它跟一般的上線會議不同：

- **明確時點**：決策掛在日曆上（窗口前三十分鐘、發布日前一天），拖過時點就是改期，決策有 deadline 而非持續醞釀
- **票的分持**：各職能各自表態（容量、資料、值班、產品），任何一票 no-go 即停——單一主管綜合各方意見後裁決的會議，票沒有分持、只是諮詢
- **判斷標準先於會議**：每張票對應事前定義的檢查與 stop condition，會議只是宣告結果；判斷標準在會議中臨時發明，是這個制度失效的訊號

## 可觀察訊號

系統需要 go/no-go 的訊號是：

- 變更不可逆或回退昂貴（資料 migration cutover、DNS 切換、合約生效）
- 多方依賴同一時點（上下游要同時切、對外公告已排定）
- 執行窗口有限（流量低谷、維護時段、監管核可期）
- 事後檢討發現「當時有人有疑慮但沒有說出來的位置」

## 接近真實網路服務的例子

服務把資料庫 migration 的讀寫切換排在凌晨低谷窗口。窗口前三十分鐘開 go/no-go：SRE 報容量與 error budget、DBA 報 replication lag 是否低於預定閾值、值班報當下有無進行中事故、產品報對外公告狀態。DBA 回報 lag 高於閾值——這是事前寫好的 stop condition，一票 no-go，切換改期到下一個窗口。沒有這個時點，同樣的 lag 數字會變成「應該還好吧」的滑行。

## 設計責任

Go/no-go 的設計要指定：時點與改期規則、哪些職能各持一票、每張票對應的檢查與 stop condition、以及 no-go 之後的路徑（改期、降範圍、還是取消）。決策結果與各票的依據要進 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 或發布記錄——事後回放「當時誰依什麼放行」是這個制度可稽核的原因。票的分持是制度的核心：主持人可以主持、但不能代投別人的票。
