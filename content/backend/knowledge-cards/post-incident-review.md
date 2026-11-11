---
title: "Post-Incident Review"
tags: ["事故後檢討", "Post-Incident Review"]
date: 2026-04-23
description: "說明事故後如何完成復盤、學習與改進閉環"
weight: 157
---

Post-incident review 的核心概念是「事故後把事實、原因與改進行動整理成可驗證輸出」。它的目標是提升系統與流程，不是追究個人。 可先對照 [Incident Timeline](/backend/knowledge-cards/incident-timeline/)。

## 跟其他概念的關係

復盤連接 [incident timeline](/backend/knowledge-cards/incident-timeline/)、[rca](/backend/knowledge-cards/rca/) 與 [runbook](/backend/knowledge-cards/runbook/) 更新。它也是可靠性改進與工程優先序調整的輸入來源。

## 可觀察訊號與例子

系統需要復盤流程的訊號是同類事故反覆發生。若每次都只做當下修補，沒有形成結構化改進，事故頻率通常不會下降。

## 判斷條件與後果

復盤能不能讓同類事故不再反覆，取決於它的產出是否可以驗證。只有影響摘要與時間線、沒有根因時，下一次同類事故仍然只能做當下的修補；只記有效措施、沒有無效措施時，下一次事故的處理者可能重試已經證明無效的處置；行動項沒有 owner 與完成標準時，它停在會議紀錄裡，沒有人負責推進，也判斷不了是否完成；沒有驗證期限時，改進做完之後，事故頻率是否下降不會被回頭檢查。
