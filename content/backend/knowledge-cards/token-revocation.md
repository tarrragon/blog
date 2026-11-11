---
title: "Token Revocation"
tags: ["權杖撤銷", "Token Revocation"]
date: 2026-04-24
description: "說明事件中如何撤銷 token，縮短可利用窗口"
weight: 267
---

Token revocation 的核心概念是「在事件節奏內讓既有 token 失去授權效力」。它是第三方事件與身分事件中的關鍵收斂能力。 可先對照 [Authorization](/backend/knowledge-cards/authorization/)。

## 跟其他概念的關係

Token revocation 位在 [authorization](/backend/knowledge-cards/authorization/)、[secret-management](/backend/knowledge-cards/secret-management/)、[incident-severity](/backend/knowledge-cards/incident-severity/) 與 [runbook](/backend/knowledge-cards/runbook/) 之間。它常與 token 分域策略一起使用。

## 可觀察訊號與例子

系統需要 token 撤銷能力的訊號是供應商事件後 token 仍可存取敏感資產，或可疑 token 在事件後持續被使用。OAuth token、API token 與 service token 都屬於常見對象。

## 判斷條件與後果

Token 沒有分域時（一個 token 可以存取多個系統），只想切斷其中一個系統的存取時也只能撤掉整個 token，依賴它的正常功能一起中斷；分域之後，事件中只撤銷受影響的範圍。沒有優先級時，大量 token 要撤銷的事件裡無法決定先撤哪一批，高風險 token 可能排在後面而繼續被使用。批次策略決定撤銷的速度與對系統的衝擊：一次全部撤銷時，所有持有者同時重新取得授權，逐批撤銷較慢而負載可控。沒有可回查的紀錄時，事件後無法確認哪些 token 已經失效、哪些在撤銷之後仍被使用。事件中先撤銷高風險 token、再依業務優先級逐步恢復必要授權，這個順序靠的就是這四項。
