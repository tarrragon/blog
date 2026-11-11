---
title: "CQRS"
tags: ["cqrs", "read-model", "repository"]
date: 2026-07-20
description: "有人提議「上 CQRS」、或想知道讀寫分離該做到多徹底時使用。CQRS 是把讀操作與寫操作的模型拆開的架構決定——寫側守一致性、讀側服務查詢形狀，兩者可以各自有獨立的儲存與更新節奏。"
weight: 21
aliases: ["/ddd/knowledge-cards/cqrs/"]
---

多數系統預設讀寫共用同一個模型：同一組 entity 既承接寫入的一致性檢查、也承接查詢的形狀需求。CQRS（Command Query Responsibility Segregation）是把這兩個責任拆開的架構決定——寫側走 [aggregate root](/software-design/ddd/knowledge-cards/aggregate-root/)、守住不變式與一致性邊界；讀側走 [read model](/software-design/ddd/knowledge-cards/read-model/)、只服務查詢要的形狀，不承擔寫入責任。

## 跟其他概念的關係

CQRS 是一道讀側設計階梯的頂端、而非二選一的開關。讀側的設計從「消費端自行投影 aggregate 形狀」開始，中間經過「抽獨立讀 port」「查詢形狀專用投影」，到頂端才是 CQRS 全套——讀寫獨立儲存、由 [domain event](/software-design/ddd/knowledge-cards/domain-event/) 同步讀模型。多數專案的正確位置在階梯低處、不是頂端，升級由訊號驅動而非架構偏好。

## 可觀察訊號

讀寫分離的討論從「查詢方法該不該搬出 repository」，逐漸變成「讀模型需不需要自己的儲存、能不能接受跟寫側短暫不一致」，是逼近階梯頂端的訊號——第四階的代價是最終一致性進入系統語意，畫面可能短暫顯示舊值，而這是設計內行為，不是 bug。

## 判斷條件與後果

CQRS 全套的代價是讀寫各自儲存、由 domain event 同步讀模型，最終一致性因此進入系統語意，畫面可能短暫顯示舊值。讀需求還能從 aggregate 的形狀投影出來時，專案停在階梯低處，消費端自行投影或抽一個讀 port 就滿足查詢，這時上全套等於替還沒出現的讀需求付出兩份儲存與同步延遲。讀需求增生、形狀偏離、負載分歧、新鮮度分級、獨立演進這五個訊號命中時，讀側的形狀、負載或演進節奏已經跟寫側分岔，繼續共用一個模型會讓 aggregate 同時服務一致性與查詢形狀，往上升一階的代價才換得到收益。每個訊號的定義與它對應到階梯的哪一階，在 [讀模型的升級條件](/software-design/ddd/read-model-upgrade-signals/)。
