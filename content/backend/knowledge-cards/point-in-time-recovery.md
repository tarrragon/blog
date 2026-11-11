---
title: "Point-in-Time Recovery"
date: 2026-05-22
description: "說明如何用完整備份加上後續變更日誌，把資料庫還原到任意時間點"
weight: 350
---

Point-in-Time Recovery（PITR）的核心概念是用一份完整備份，加上備份之後累積的變更日誌，把資料庫還原到過去任意一個時間點。它讓「還原到誤操作發生的前一刻」成為可能，而不只是還原到最近一次備份。它依賴 [Write-Ahead Log](/backend/knowledge-cards/write-ahead-log/) 之類的變更日誌，是達成 [RPO](/backend/knowledge-cards/rpo/) 的具體機制。

## 跟其他概念的關係

Point-in-Time Recovery 位在備份還原機制中、比「還原到最近備份」更精細的一端。[RPO](/backend/knowledge-cards/rpo/) 與 [RTO](/backend/knowledge-cards/rto/) 是還原的目標（可接受的資料損失與停機時間），PITR 是達成這些目標的機制：base backup 決定起點、持續歸檔的變更日誌決定能還原到多近的時間點。它和 [Rollback Strategy](/backend/knowledge-cards/rollback-strategy/) 一起構成事故的資料復原能力。

## 可觀察訊號與例子

需要 PITR 的訊號是事故型態包含「某個時間點之後的資料被汙染」 — 誤刪、錯誤的批次更新、應用 bug 寫壞資料。只有定期備份時，還原會把備份之後的正常資料一起丟掉；PITR 讓還原點可以精準停在汙染發生前。常見的隱性風險是變更日誌歸檔斷掉，PITR 的可還原窗口其實有缺口卻沒被發現。

## 判斷條件與後果

PITR 能還原到哪些時間點，由 base backup 與變更日誌的持續歸檔一起決定。歸檔中斷時，中斷之後的時間點都還原不了，而這個缺口在平時不會顯現，到事故需要還原時才被發現；base backup 間隔拉長時，還原要 replay 的日誌變多，還原時間變長，[RTO](/backend/knowledge-cards/rto/) 可能超出目標；可還原窗口短於事故被發現所需的時間時，汙染發生的那一刻已經在窗口之外。設定本身證明不了備份與日誌是完整的，所以 PITR 定期實際還原到指定時間點演練一次，同時量出 RTO；平時監控日誌歸檔是否連續，以及最舊可還原時間點是否符合 [RPO](/backend/knowledge-cards/rpo/)。
