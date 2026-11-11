---
title: "Alert Fatigue"
date: 2026-06-22
description: "說明過多低品質告警如何降低 on-call 反應品質"
weight: 111
tags: ["backend", "observability"]
---

Alert fatigue 的核心概念是「過多低品質告警讓處理者對告警失去敏感度」。當告警常常沒有使用者影響、沒有行動步驟或頻繁自動恢復，[on-call](/backend/knowledge-cards/on-call/) 會開始忽略訊號 — 包括真正需要處理的那些。

## 跟其他概念的關係

Alert fatigue 是可觀測性設計的失敗模式，跟 [alert](/backend/knowledge-cards/alert/) 的品質治理直接相關。告警應代表需要人介入的產品風險；其他訊號可以進 [dashboard](/backend/knowledge-cards/dashboard/)、ticket、報表或自動修復流程。

常見的 fatigue 來源：false positive（條件觸發但實際沒問題）、redundant alert（同一問題觸發多個 alert）、stale alert（條件已不適用但 rule 沒更新）。

## 使用情境

系統需要治理 alert fatigue 的訊號是 noise rate > 30%（超過三成的 alert 不需要行動），或 on-call 工程師反應「收到 alert 先 ack 再看、有時直接 resolve 不看」。

## 判斷條件與後果

Alert fatigue 的治理從量到 noise 開始。on-call 在 ack 時標記這則告警是 actionable 還是 noise，noise rate 才有數字，高 noise 的 alert rule 才排得出處理順序；沒有這個標記時，每一條 rule 看起來同樣重要，治理只能憑印象挑。找出高 noise 的 rule 之後，處置依 noise 的成因而定：閾值設在正常波動範圍內的，調整閾值；偵測內部原因而使用者沒有受影響的，改成 [symptom-based](/backend/knowledge-cards/symptom-based-alert/)；同一個原因引出一串症狀的，加 [inhibition](/backend/knowledge-cards/alert-inhibition/)（原因的告警成立時壓下它造成的症狀告警），或用 grouping 把同一件事的多則通知合成一則；條件已經不適用的 stale alert，刪除。審視沒有固定節奏時，noise 會隨服務演進重新累積，所以這套審視接進 [4.8 訊號治理閉環](/backend/04-observability/signal-governance-loop/) 的節奏。

跨領域詞源與因果鏈（false positive → noise → alert fatigue）見 [TIL 跨領域術語：alert fatigue](/til/terms/alert-fatigue/)。
