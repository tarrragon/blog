---
title: "MTTR"
tags: ["平均修復時間", "MTTR"]
date: 2026-04-23
description: "說明平均修復時間如何作為事故處理能力指標"
weight: 161
---

MTTR 的核心概念是「從事故開始到恢復的平均時間」。它幫助團隊追蹤處置效率趨勢，但不能單獨代表可靠性品質。 可先對照 [Incident Severity](/backend/knowledge-cards/incident-severity/)。

## 跟其他概念的關係

MTTR 連接 [incident severity](/backend/knowledge-cards/incident-severity/)、[alert](/backend/knowledge-cards/alert/)、[runbook](/backend/knowledge-cards/runbook/) 與 [post-incident-review](/backend/knowledge-cards/post-incident-review/)。不同等級事故應分開計算，避免指標失真。

## 可觀察訊號與例子

系統需要 MTTR 的訊號是團隊想驗證事故流程是否改進。若新增 runbook 與升級策略後 MTTR 持續下降，表示流程變更有實際效果。

## 判斷條件與後果

MTTR 是平均值，樣本數少時，一次特別長或特別短的事故就能移動它，數字的變化反映的是那一次事故，不是流程的趨勢。不同嚴重度的事故混在一起算時，一個月裡多了幾次容易修的小事故，MTTR 就下降，而重大事故的修復時間可能沒有改變；分開計算時，每個等級的趨勢才對得上那個等級的處置流程。只看時間、不看影響範圍時，修得快而影響全部使用者的事故，與修得慢而只影響少數使用者的事故被算成同一種結果。MTTR 下降本身被當成目標時，提早宣告恢復或把一次事故拆成幾筆紀錄都會讓數字下降，而修復能力沒有改變；拿它驗證新增 runbook、升級策略或演練這類流程變更的效果時，數字的變化才對應到一個追溯得到的原因。
