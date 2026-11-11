---
title: "Bounded Context"
tags: ["bounded-context", "aggregate-root", "domain-event"]
date: 2026-07-20
description: "同一套架構判斷標準跨到另一個服務還成不成立？bounded context 是模型與詞彙保持一致的邊界——邊界內的推導在邊界外不必然成立。"
weight: 19
aliases: ["/ddd/knowledge-cards/bounded-context/"]
---

bounded context 是一個模型與詞彙維持一致的邊界：邊界內，同一個詞（例如「訂單」）只有一種意義、同一套業務規則統一適用；跨過邊界，同一個詞可能換了意義、規則跟著換。[aggregate root](/software-design/ddd/knowledge-cards/aggregate-root/) 守的一致性邊界在單一 aggregate 內；bounded context 守的是更大一層——一整套模型、詞彙與規則在哪裡開始、哪裡結束。

## 跟其他概念的關係

單一 bounded context 內的架構判斷標準，跨過邊界不必然照搬。讀模型升級的四階梯（消費端投影 → 抽讀 port → 專用投影 → 事件同步的獨立儲存）假設操作發生在單一 bounded context 內；報表服務訂閱多個 domain 的事件建置共享視圖，是跨 bounded context 的讀模型，這時引入的關注點——跨服務事件契約穩定性、schema 演進、跨信任邊界的最終一致性——不是「多買一種能力」能概括，完整推導見 [讀模型的升級條件](/software-design/ddd/read-model-upgrade-signals/)。這類跨邊界溝通的常見載體是 [domain event](/software-design/ddd/knowledge-cards/domain-event/)，其中攜帶足量狀態給下游的作法見 [event-carried state transfer](/software-design/ddd/knowledge-cards/event-carried-state-transfer/)。

## 可觀察訊號

一個判斷標準句在單一服務內成立、換到跨服務場景就開始要補額外的機制（契約版本、schema 遷移、補償流程），是踩到 bounded context 邊界的訊號——原本的判斷標準沒有錯，是它的適用範圍被劃在邊界內，邊界外要重新論證。

## 判斷條件與後果

兩個 bounded context 之間的互動方式，決定同一個詞會不會被讀成兩種意義。下游直接沿用上游的內部語意（把上游的「訂單」當成自己的「訂單」）時，上游改了那個詞在自己模型裡的意義或規則，下游照舊的理解讀錯資料，而兩邊都沒有任何一處報錯，原因是一個模型只在自己的邊界內保證詞義一致；互動改走顯式的契約與轉換時，兩邊詞義的對應寫在轉換那一處，上游改動模型時要對照的位置只有那份契約。同一條邊界也限制架構結論的適用範圍：在單一 bounded context 內推導成立的判斷標準，套到跨 context 的場景時會多出契約版本、schema 遷移、補償流程這些機制，當初的推導沒有算進它們的成本，所以邊界外要重新論證一次。
