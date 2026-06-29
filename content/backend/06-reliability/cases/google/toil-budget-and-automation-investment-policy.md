---
title: "Google：Toil Budget 與 Automation 投資政策"
date: 2026-05-07
description: "把 toil 從感受問題轉成預算問題：用時間配比與自動化回報機制，避免 on-call 壓力長期侵蝕可靠性工程。"
weight: 13
tags: ["backend", "reliability", "case-study"]
---

Toil budget 的核心責任是把重複手動工作變成可治理成本。Google SRE 的關鍵做法是先量化 toil，再把超額部分強制導向自動化投資，而不是持續靠人力吸收。

## 問題場景

許多團隊的可靠性工作會被 incident handling 與手動修復吃掉。短期看似把事情解決，長期會造成兩個後果：一是 on-call 壓力升高，二是系統問題持續累積。沒有 toil budget 時，團隊很難判斷何時該停止加功能、先補工程基礎。

## 決策機制

Toil budget 是把工時結果接到 release 與 backlog 決策的機制，單純統計工時只完成一半。

| 機制      | 核心問題                  | 實際輸出                     |
| --------- | ------------------------- | ---------------------------- |
| Toil 分類 | 哪些工作屬於可自動化 toil | toil taxonomy                |
| 時間配比  | toil 比例是否超過可承受區 | budget 門檻（例如 50%）      |
| 超標處理  | 超標後怎麼調整優先序      | 凍結部分 feature、轉投自動化 |
| 改善驗證  | 自動化是否真的回收工時    | closure 指標與 evidence      |

## 可觀測訊號

| 訊號                       | 判讀重點                 | 對應章節                                                            |
| -------------------------- | ------------------------ | ------------------------------------------------------------------- |
| toil ratio                 | 是否長期超出預算         | [6.21](/backend/06-reliability/reliability-debt-backlog/)           |
| incident manual-step count | 事故處理是否過度依賴人工 | [8.16](/backend/08-incident-response/runbook-lifecycle/)            |
| automation closure rate    | 改善項是否真的落地       | [8.22](/backend/08-incident-response/incident-evidence-write-back/) |
| on-call overload signal    | 值班負荷是否持續上升     | [8.6](/backend/08-incident-response/drills-and-oncall-readiness/)   |

## 常見陷阱

最常見錯誤是把 toil 視為「正常運維工作」，結果讓超標狀態常態化。另一個錯誤是只記錄工時，不把結果接到 release gate 與優先序調整。這兩種做法都會讓可靠性債繼續滾大。

## 下一步路由

把 toil budget 落地時，先在 [6.21 Reliability Debt Backlog](/backend/06-reliability/reliability-debt-backlog/) 建立分類與排序，再把超標條件接到 [6.8 Release Gate](/backend/06-reliability/release-gate/)。事後改善要回寫 [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)。

## 引用源

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [Google SRE Workbook](https://sre.google/workbook/table-of-contents/)
