---
title: "Safety Stock（安全庫存）"
date: 2026-07-09
description: "決定一顆料的安全庫存該設多厚、或懷疑現有緩衝在積壓現金時查閱"
weight: 40
tags: ["business", "procurement", "knowledge-cards"]
---

Safety Stock（安全庫存，也常以 Buffer Stock 指稱）的核心概念是「為了吸收需求與交期波動而常態保留的緩衝庫存」。它讓產線在需求突增或交期延遲時仍有料可用，是防 [斷料](/business/procurement-planning/cards/stockout/) 的常態機制。Safety Stock 的高度由 [Lead Time](/business/procurement-planning/cards/lead-time/)、需求波動與停線代價共同決定。

## 概念位置

Safety Stock 跟 [Risk Buy](/business/procurement-planning/cards/risk-buy/) 都在備料，但性質不同：Safety Stock 是常態保留、對抗日常波動；Risk Buy 是事件驅動、針對特定缺料訊號一次性加碼。常用料會跟供應商談 [寄售](/business/procurement-planning/cards/consignment/) 或預備庫存，把 safety stock 的持有成本轉一部分給供應商，而不是所有料都等 PO（採購訂單）才開始備。

## 可觀察訊號與例子

判讀 safety stock 該設多高的訊號：這顆料的需求波動大不大、LT 長不長、缺這顆料造成的停線代價有多重。長 LT 加高波動的關鍵料，safety stock 要設厚；短 LT 又穩定的料，設太厚只是積壓現金。常用料談寄售或供應商端預備庫存，是把 safety stock 的形式從「自己囤」改成「供應商替你囤、你用了才付」。

## 判讀方式

設定 safety stock 時，用「LT 長度、需求波動、停線代價」三個面向綜合判斷厚度，而不是一律設固定天數；厚度隨交期放大的推導（累積偏差約按交期的平方根成長），展開在 [需求分層與備料策略](/business/procurement-planning/demand-tiered-stocking/)。常見陷阱有兩個：一是所有料都設同樣安全天數，讓短交期料積壓、長交期料仍不足；二是把 safety stock 當成不會動的死庫存，忘了它要隨淡旺季與 LT 變化調整。Safety stock 是動態的緩衝，不是設一次就不管的固定值。
