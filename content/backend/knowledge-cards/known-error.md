---
title: "Known Error（已知錯誤）"
date: 2026-10-14
description: "已經確認、還沒修好、影響小到不必開事故的問題要讓客服與值班知道時，查 ITIL 的已知錯誤與已知錯誤資料庫（KEDB）記錄什麼、它與事故在 ITIL 裡的關係、本站流程裡清單與事故的分流，以及清單沒有維護時的失效"
weight: 483
tags: ["backend", "incident-response", "customer-support"]
---

Known error（已知錯誤）是 ITIL 問題管理的用語。ITIL v3 的定義是根因已經記錄、而且有替代做法（workaround）的問題；ITIL 4 放寬成已經分析過、還沒解決的問題。存放這些紀錄的地方叫已知錯誤資料庫（KEDB，Known Error Database），內容是症狀、根因、替代做法與修正的進度。客服以它當場答覆使用者，是 [Tiered Support（分層支援）](/backend/knowledge-cards/tiered-support/) 一線答得出來的資訊之一；它的條目常由 [Knowledge-Centered Service（KCS）](/backend/knowledge-cards/knowledge-centered-service/) 的流程在處理回報時寫下。

## 概念位置

ITIL 把三種紀錄分開：事故（incident）是一次服務中斷或品質下降，包括單一使用者遇到的；問題（problem）是一個或多個事故的原因或可能的原因，建立問題紀錄時根因通常還不知道；問題分析過、還沒解決的，就是已知錯誤。在 ITIL 裡事故是事件、已知錯誤是原因，兩者會同時存在：每一位撞上同一個已知錯誤的使用者回報，都是一筆連到它的事故，以已知錯誤裡的替代做法處理。

本站的事故流程另有一條分界，用的「事故」是需要指揮處理、影響可能擴大的那一類（接近 ITIL 的 major incident）：影響固定、有替代做法的問題列進已知錯誤清單，由客服與值班照著處理；影響正在擴大、需要有人指揮的，走 [Incident Severity](/backend/knowledge-cards/incident-severity/) 與事故流程。

## 可觀察訊號與例子

短網址服務的統計頁在某一款舊版瀏覽器上圖表空白，換瀏覽器就看得到：影響只限那一款瀏覽器的使用者，不會擴大，有替代做法，修正排在下一次發布。這一則列進已知錯誤清單，寫明症狀、受影響的瀏覽器版本、客服給使用者的替代做法與追蹤單號。客服接到「統計頁空白」時先查清單，符合的當場答覆，不轉給工程。

## 判讀方式

清單的價值取決於它是否跟上現況。修好上線的條目沒有移除，客服會繼續給使用者一個已經不需要的替代做法；新確認的問題沒有寫進去，同一類回報就繼續轉給工程。維護責任因此要指定給確認問題與發布修正的人：確認時寫入、修正上線時移除。客服怎麼用這份清單、工程什麼時候寫入，見 [8.24 客服回報的處理](/backend/08-incident-response/support-escalation-and-engineering-reply/)。
