---
title: "Impact Scope"
tags: ["影響範圍", "Impact Scope"]
date: 2026-04-24
description: "說明事故中如何盤點受影響範圍，支持通報、回復與責任判讀"
weight: 269
---

Impact scope 的核心概念是「用一致規則界定事故影響到哪些資產、流程與利害關係人」。它是事故通報與回復排序的共用基礎。 可先對照 [Blast Radius](/backend/knowledge-cards/blast-radius/)。

## 跟其他概念的關係

Impact scope 位在 [blast-radius](/backend/knowledge-cards/blast-radius/)、[incident-timeline](/backend/knowledge-cards/incident-timeline/)、[post-incident-review](/backend/knowledge-cards/post-incident-review/) 與 [mttr](/backend/knowledge-cards/mttr/) 之間。它把技術事件映射到業務影響。

## 可觀察訊號與例子

系統需要影響面盤點的訊號是技術異常已確認，但受影響名單與業務衝擊仍不清楚。資料外送事件、供應鏈事件與跨部門中斷都需要 impact scope。

## 判斷條件與後果

影響面盤點在事件進行中做，對象是技術異常已確認、受影響名單還不清楚的那段時間，通報與回復的排序都要等這份清單。盤點粒度沒有事先定好時（以客戶、帳號還是單筆交易為單位），各團隊交出的數字對不起來，同一個事件在通報裡出現幾個不同的影響數字；資料來源沒有指定時，名單的內容取決於誰去查了哪一份紀錄。清單要等完整才交出去時，通報與回復都要等盤點完成才能開始。先交出一份寫明涵蓋範圍的最小清單，再由指定的負責人依事先定好的更新節奏補精度，通報與回復可以先照這份清單開始，代價是清單每更新一次，通報對象要再收到一次更正。
