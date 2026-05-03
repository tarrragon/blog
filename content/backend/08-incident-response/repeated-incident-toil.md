---
title: "8.13 Repeated Incident 與 Toil 治理"
date: 2026-05-01
description: "把同型事故反覆發生與重複手動修復作為工程化治理對象"
weight: 13
---

## 大綱

- 為何 repeated incident 需要獨立節點：單次 [post-incident review](/backend/knowledge-cards/post-incident-review/) 解不了系統性問題
- 識別 repeated pattern：靠 [8.9 事故型態庫](/backend/08-incident-response/incident-pattern-library/) 標籤分類、跨 incident 統計
- [toil](/backend/knowledge-cards/toil/) 的定義：重複、手動、無永久價值、可自動化（Google SRE Book）
- 從 manual runbook 到 automation 的演進路徑
- repeated incident 的根因類別：監控盲區、架構缺陷、流程斷點、人力不足
- error budget 撥用 [toil](/backend/knowledge-cards/toil/) reduction 的政策
- 跟 [8.5 post-incident review](/backend/knowledge-cards/post-incident-review/) 的差異：8.5 處理單事故、8.13 處理 pattern
- 跟 [6.6 SLO error budget](/backend/06-reliability/slo-error-budget/) 的整合：error budget 餘額分配給 [toil](/backend/knowledge-cards/toil/) reduction
- 反模式：每次事故 action items 都是「補 alert / 補 runbook」；[toil](/backend/knowledge-cards/toil/) 視為值班個人問題；repeated pattern 無人擁有

## 概念定位

Repeated incident 與 [toil](/backend/knowledge-cards/toil/) 治理是把同型事故反覆發生與重複手動修復當成工程化治理對象，責任是把「一直在處理」轉成「一次修掉」。

這一頁處理的是 pattern 層級問題。單次 [post-incident review](/backend/knowledge-cards/post-incident-review/) 只能修一個事件，重複事故需要的是跨事件的抽象與自動化。

## 核心判讀

判讀 repeated incident 時，先看是否真的重複，再看能否用 automation 吃掉手動成本。

重點訊號包括：

- 同類 alert 是否週期性觸發
- action items 是否在多次 [post-incident review](/backend/knowledge-cards/post-incident-review/) 重複出現
- [toil](/backend/knowledge-cards/toil/) 是否佔據過多值班時間
- 是否已經有明確 automation 路線

## 案例對照

- [GitHub](/backend/08-incident-response/cases/github/_index.md)：平台級事故常會形成重複修復與 [toil](/backend/knowledge-cards/toil/)。
- [Slack](/backend/08-incident-response/cases/slack/_index.md)：通知與協作流程容易留下固定 [toil](/backend/knowledge-cards/toil/)。
- [Datadog](/backend/08-incident-response/cases/datadog/_index.md)：監控依賴失效時，值班可能被重複告警拖住。

## 下一步路由

- 06.6 error budget：撥用 [toil](/backend/knowledge-cards/toil/) reduction 的政策
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：跨事故 pattern 分析
- 08.6 drills：[toil](/backend/knowledge-cards/toil/) 自動化後的演練更新
- 08.9 pattern library：repeated pattern 抽卡
- 08.14 multi-incident：同源事故合併判讀

## 判讀訊號

- 同類 alert 每週 / 每月固定觸發、靠值班手動處理
- [post-incident review](/backend/knowledge-cards/post-incident-review/) action items 跨多次事故重複出現
- 值班滿意度低、招募 / 留任困難
- 「這個我上次也修過」是值班共通語
- [toil](/backend/knowledge-cards/toil/) 占值班時間 > 50%、無工程化 budget

## 交接路由

- 06.6 error budget：撥用 [toil](/backend/knowledge-cards/toil/) reduction 的政策
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：跨事故 pattern 分析
- 08.6 drills：[toil](/backend/knowledge-cards/toil/) 自動化後的演練更新
- 08.9 pattern library：repeated pattern 抽卡
- 08.14 multi-incident：同源事故合併判讀
- 08.16 runbook lifecycle：[toil](/backend/knowledge-cards/toil/) 自動化後 runbook 退場
