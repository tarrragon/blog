---
title: "Bounded Context"
tags: ["bounded-context", "aggregate-root", "domain-event"]
date: 2026-07-20
description: "同一套架構判準在多服務之間還站不站得住時使用。bounded context 是模型與詞彙保持一致的邊界——邊界內的推導在邊界外不必然成立。"
weight: 19
---

bounded context 是一個模型與詞彙維持一致的邊界：邊界內，同一個詞（例如「訂單」）只有一種意義、同一套業務規則統一適用；跨過邊界，同一個詞可能換了意義、規則跟著換。[aggregate root](/ddd/knowledge-cards/aggregate-root/) 守的一致性邊界在單一 aggregate 內；bounded context 守的是更大一層——一整套模型、詞彙與規則在哪裡開始、哪裡結束。

## 概念位置

單一 bounded context 內的架構判準，跨過邊界不必然照搬。讀模型升級的四階梯（消費端投影 → 抽讀 port → 專用投影 → 事件同步的獨立儲存）假設操作發生在單一 bounded context 內；報表服務訂閱多個 domain 的事件建置共享視圖，是跨 bounded context 的讀模型，這時引入的關注點——跨服務事件契約穩定性、schema 演進、跨信任邊界的最終一致性——不是「多買一種能力」能概括，完整推導見 [讀模型的升級判準](/ddd/read-model-upgrade-signals/)。這類跨邊界溝通的常見載體是 [domain event](/ddd/knowledge-cards/domain-event/)，其中攜帶足量狀態給下游的作法見 [event-carried state transfer](/ddd/knowledge-cards/event-carried-state-transfer/)。

## 可觀察訊號

一個判準句在單一服務內成立、換到跨服務場景就開始要補額外的機制（契約版本、schema 遷移、補償流程），是踩到 bounded context 邊界的訊號——原本的判準沒有錯，是它的適用範圍被劃在邊界內，邊界外要重新論證。

## 設計責任

bounded context 的設計責任是替模型畫出「在哪裡可以直接假設一致」的邊界，邊界外的互動改走顯式的契約與轉換，不能沿用邊界內的內部語意。這條邊界也是判斷同一套架構結論能不能套用的分界——邊界內成立的推導，邊界外要重新論證，不是預設繼續有效。
