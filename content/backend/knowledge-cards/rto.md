---
title: "RTO"
tags: ["復原時間目標", "RTO"]
date: 2026-04-23
description: "說明恢復時間目標如何約束事故回復策略"
weight: 159
---

RTO 的核心概念是「事故後服務恢復到可接受狀態所需的最長時間」。它是產品承諾與技術設計之間的時間約束。 可先對照 [Downtime](/backend/knowledge-cards/downtime/)。

## 跟其他概念的關係

RTO 連接 [downtime](/backend/knowledge-cards/downtime/)、[failover](/backend/knowledge-cards/failover/) 與 [rollback-strategy](/backend/knowledge-cards/rollback-strategy/)。更短 RTO 通常需要更高操作準備與基礎設施成本。

## 可觀察訊號與例子

系統需要 RTO 的訊號是停機時間會直接影響收入或合約責任。付款服務若目標 RTO 為 15 分鐘，值班流程與切換能力都要圍繞這個目標設計。

## 判斷條件與後果

一個 RTO 數字成立的條件，是值班流程與切換能力在目標時間內完成恢復。付款服務的目標 RTO 是 15 分鐘時，偵測、通知、判斷與切換加起來都要在這 15 分鐘內完成，任何一段沒有指定負責的角色，時間就花在找人上。RTO 越短，需要的預先準備與基礎設施成本越高，所以 RTO 依服務的分級設定，不同分級的服務各有自己的目標。沒有用演練或真實事故的恢復時間驗證過的 RTO 只是目標，實際恢復時間可能遠超過它；演練的頻率決定這份驗證多久之後就過時。
