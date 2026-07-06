---
title: "模組四：觸發器與排程"
date: 2026-07-06
description: "用 Apps Script 的時間觸發器把累積的原始瀏覽 log 定時彙總成看得懂的日報，以及觸發器的每日執行配額"
weight: 5
tags: ["automation", "apps-script", "triggers", "aggregation", "scheduling"]
---

回答「原始 log 怎麼變成看得懂的報表、而且不用手動跑」。beacon 一直 append 進來的是一列一列的原始瀏覽紀錄，這種 raw log 直接看沒意義——要的是「昨天每篇文章被看幾次」。這一章用 Apps Script 的時間觸發器（time-driven trigger）自動排程：每天固定時間把前一天的原始 log 彙總成一張日報表，人打開就看得懂。

觸發器是 Apps Script 從「被動等人呼叫」變成「主動定時執行」的機制。它的成本要放在心上：個人帳號的觸發器每天總執行時間上限是 90 分鐘（見[模組零](/automation/00-mental-model/free-tier-and-tool-choice/)），所以彙總邏輯要寫得有效率，別在觸發器裡做會逼近上限的重活。

## 章節文章

| 文章                                                                                             | 主題                                                                |
| ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| [時間觸發器：把 raw log 彙總成日報](/automation/04-triggers-automation/time-driven-aggregation/) | 設定每日定時、group by 彙總邏輯、在 90 分鐘配額內只讀增量的效率寫法 |
| [表單與事件觸發器](/automation/04-triggers-automation/form-and-event-triggers/)                  | `onFormSubmit` / `onEdit`、simple 與 installable 觸發器的權限分界   |

## 跨分類引用

- → [模組三：Sheets 當資料庫](/automation/03-sheet-as-database/)：被彙總的 raw log 從哪來
- → [Monitoring：漏斗分析](/monitoring/08-business-analytics/funnel-analysis/)：彙總後的資料能做什麼分析
