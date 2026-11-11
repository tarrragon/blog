---
title: "DLQ Drain"
date: 2026-06-16
description: "說明把 dead-letter queue 累積的訊息重新處理或排空的受控流程"
weight: 382
---

DLQ drain 的核心概念是「把 dead-letter queue 累積的訊息重新處理或清空的受控流程」。訊息進 DLQ 只是被隔離，drain 決定它們最終被修復重送、丟棄還是歸檔，是 DLQ 不無限長大的收尾步驟。 可先對照 [Dead-letter Queue](/backend/knowledge-cards/dead-letter-queue/)。

## 跟其他概念的關係

DLQ drain 接在 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 之後、[poison-message quarantine](/backend/knowledge-cards/poison-message-quarantine/) 隔離訊息之後。drain 前要先確認根因已修，否則重送只會再次失敗、訊息又繞回 DLQ。

## 可觀察訊號與例子

DLQ depth 持續上升代表有未處理的失敗累積；修好 consumer bug 後，用 redrive（SQS）或重新 publish 把 DLQ 訊息送回主 queue 重處理。無法修復的（過期、業務上已失效）則歸檔後刪除，而非放著佔空間。

## 判斷條件與後果

Drain 的時機與送出速度決定它是修復還是第二次故障。根因還沒修好時重送，訊息再次失敗、繞回 DLQ，drain 只增加了一輪無效的負載。根因修好之後一次全量重送，剛恢復的下游同時收到整段故障期間累積的訊息，請求量遠高於平常，下游可能再次逾時或失敗；分批重送、每一批之後看成功率，失敗率回升時還停得下來。Drain 的時點、批量與結果沒有記錄時，之後分不出哪些訊息已經重送過，同一批訊息可能被送第二次，所以這三項記進 decision log。
