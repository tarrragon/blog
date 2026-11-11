---
title: "Data Reconciliation"
date: 2026-04-23
description: "說明多個資料來源不一致時如何比對、修復與留下證據"
weight: 88
---

Data reconciliation 的核心概念是「比對多個資料來源，找出差異並修復到可接受狀態」。它常用在付款對帳、資料 [migration](/backend/knowledge-cards/migration/)、事件漏處理、報表修復與第三方同步。

## 跟其他概念的關係

Reconciliation 是 eventual consistency 的修復流程。Kubernetes 文件裡的 reconcile 指的是控制器把實際狀態拉回期望狀態，是另一個概念，見 [Control Loop](/backend/knowledge-cards/control-loop/)。即使系統設計了事件、[retry policy](/backend/knowledge-cards/retry-policy/) 與 [outbox pattern](/backend/knowledge-cards/outbox-pattern/)，仍需要定期或事件後比對正式結果，修復漏送、重複或半成功。

## 可觀察訊號與例子

系統需要 reconciliation 的訊號是兩個系統都聲稱有狀態，但結果可能不同。付款 provider 顯示已扣款，訂單系統顯示未付款時，需要對帳流程依 [source of truth](/backend/knowledge-cards/source-of-truth/) 判斷正式結果並修復訂單狀態。

## 判斷條件與後果

Reconciliation 的結果能拿來修復到什麼程度，看它事前定了哪幾項。沒有指定比對來源與優先權時，付款 provider 顯示已扣款而訂單系統顯示未付款，對帳流程判斷不出哪一邊是正式結果。沒有差異分類時，漏送、重複與半成功混在同一份差異清單裡，而三者的修復動作不同。修復動作沒有記進 [audit log](/backend/knowledge-cards/audit-log/) 時，事後分不出一筆資料的現狀來自原始寫入還是修復；沒有人工介入條件時，自動修復會處理到需要人判斷的差異。金錢、權限這類高風險資料的修復沒有保留修復前後的證據時，修錯了無法還原，也無法向稽核說明改了什麼。
