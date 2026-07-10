---
title: "Entity"
tags: ["實體", "Entity"]
date: 2026-07-10
description: "判斷一個概念該建成 entity 還是 value object 時使用。entity 的同一性由身份定義——欄位全部改變、只要身份參照不變就是同一個。"
weight: 2
---

Entity 的同一性由身份定義：欄位可以全部改變、只要身份參照不變就是同一個；兩個欄位完全相同的 entity 仍然是兩個。這條定義推導出 entity 的設計形狀——有生命週期、狀態沿業務流程演進、變更要有路徑。跟 [value object](/ddd/knowledge-cards/value-object/) 相反：value object 的同一性由內容定義、替換實例對系統沒有影響。

## 概念位置

Entity 是領域模型的一種形態——型別先判定為領域模型（有[不變式](/ddd/knowledge-cards/invariant/)）、再判定身份語意（entity 或 value object）。判準是「操作需不需要 identity-based 回寫」：取消、改量、退貨這類要精確指到特定實體的操作，需要 entity；內容比對就足夠的操作用 value object。同一個業務概念的身份語意會隨生命週期階段改變——每個轉折點重問一次判準。

## 可觀察訊號

改量、取消這類操作用內容比對定位對象——同內容的其他實體會被誤中，這是模型該升級成 entity 的訊號。entity 的變更路徑通常經由領域方法——如果 entity 同時有領域方法與全開放的覆寫工具，變更路徑正在退化。

## 設計責任

Entity 需要決定身份的來源（資料庫序號、外部系統 ID、業務規則產生的識別碼）、生命週期的階段（何時誕生、何時交棒、何時成為歷史事實需要 [snapshot](/ddd/knowledge-cards/snapshot/)）、以及變更的路徑（領域方法的設計，見 [狀態轉換與稽核軌跡](/ddd/state-transition-and-audit-trail/)）。判準的完整展開見 [entity 與 value object 的判準](/ddd/entity-vs-value-object/)。
