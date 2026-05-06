---
title: "Error Budget"
date: 2026-04-23
description: "說明 SLO 允許的失敗額度如何影響發版與可靠性投入"
weight: 101
---


Error budget 的核心概念是「SLO 允許的失敗額度」。如果服務承諾 99.9% 可用，剩下 0.1% 就是可接受失敗空間；這個空間用來平衡功能交付與可靠性改善。 可先對照 [Release Gate](/backend/knowledge-cards/release-gate/)。

## 概念位置

Error budget 把可靠性討論轉成決策語言。Budget 消耗過快時，團隊應優先修可靠性；budget 充足時，可以承擔較多變更風險。 可先對照 [Release Gate](/backend/knowledge-cards/release-gate/)。

## 可觀察訊號與例子

系統需要 error budget 的訊號是發版速度與事故風險需要共同管理。Checkout 服務本月多次 timeout，若 error budget 已接近耗盡，團隊應暫停高風險變更。

## 設計責任

Error budget 要和 SLO、alert、incident review、[Release Gate](/backend/knowledge-cards/release-gate/) 連接。它應反映使用者影響，instance 存活只是底層健康訊號之一。
