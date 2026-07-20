---
title: "CQRS"
tags: ["cqrs", "read-model", "repository"]
date: 2026-07-20
description: "有人提議「上 CQRS」、或想知道讀寫分離該做到多徹底時使用。CQRS 是把讀操作與寫操作的模型拆開的架構決定——寫側守一致性、讀側服務查詢形狀，兩者可以各自有獨立的儲存與更新節奏。"
weight: 21
---

多數系統預設讀寫共用同一個模型：同一組 entity 既承接寫入的一致性檢查、也承接查詢的形狀需求。CQRS（Command Query Responsibility Segregation）是把這兩個責任拆開的架構決定——寫側走 [aggregate root](/ddd/knowledge-cards/aggregate-root/)、守住不變式與一致性邊界；讀側走 [read model](/ddd/knowledge-cards/read-model/)、只服務查詢要的形狀，不承擔寫入責任。

## 概念位置

CQRS 不是二選一的開關、是一道階梯的頂端。讀側的設計從「消費端自行投影 aggregate 形狀」開始，中間經過「抽獨立讀 port」「查詢形狀專用投影」，到頂端才是 CQRS 全套——讀寫獨立儲存、由 [domain event](/ddd/knowledge-cards/domain-event/) 同步讀模型。多數專案的正確位置在階梯低處、不是頂端，升級由訊號驅動而非架構偏好。

## 可觀察訊號

讀寫分離的討論從「查詢方法該不該搬出 repository」，逐漸變成「讀模型需不需要自己的儲存、能不能接受跟寫側短暫不一致」，是逼近階梯頂端的訊號——第四階的代價是最終一致性進入系統語意，畫面可能短暫顯示舊值，而這是設計內行為，不是 bug。

## 設計責任

要不要上 CQRS 全套，不看「這個模式聽起來很適合」，看五個具體訊號（讀需求增生、形狀偏離、負載分歧、新鮮度分級、獨立演進）是否命中——本卡只回答「CQRS 是什麼、階梯怎麼分階」，訊號的完整推導與升級路徑是 [讀模型的升級判準](/ddd/read-model-upgrade-signals/) 這篇的內容，要判斷自己的專案該停在哪一階、讀那篇。
