---
title: "Snapshot"
tags: ["快照", "Snapshot"]
date: 2026-07-10
description: "歷史記錄是否應該凍結當時狀態時使用。Snapshot 是某一時刻的狀態複本——歷史不隨現在的資料漂移。"
weight: 6
aliases: ["/ddd/knowledge-cards/snapshot/"]
---

Snapshot 是某一時刻的狀態複本、凍結之後不隨來源資料的後續變更而改動。歷史訂單記錄下單當時的商品名稱與價格——商品後續改名、下架、調價，訂單仍顯示當時購買的內容。跟 live 參照相反：live 參照指向來源的當前狀態、來源改了就跟著變。兩者的選擇由「這筆資料有沒有成為事實」決定。凍結的是狀態；已發生的事實本身由 [domain event](/software-design/ddd/knowledge-cards/domain-event/) 承載——snapshot 記「當時的世界長什麼樣」、event 記「當時發生了什麼」。

## 跟其他概念的關係

Snapshot 跟 [entity](/software-design/ddd/knowledge-cards/entity/) 的生命週期有關——概念成為歷史事實之後、live 內容參照要凍結。凍結的同時身份參照通常繼續承重（退貨鍵、取消鍵）。Snapshot 也是稽核的端點——記錄事件發生當下的世界、而不是現在的世界（見 [狀態轉換與稽核軌跡](/software-design/ddd/state-transition-and-audit-trail/)）。

## 可觀察訊號

歷史記錄的顯示內容跟著現行資料變動（商品改名、訂單明細跟著變）——參照凍結時機漏掉了。進行中的資料不跟著最新狀態走（購物車品項的價格不跟會員身分變動）——凍結太早。

## 判斷條件與後果

凍結時機以「這筆資料成為事實了沒」為分界，偏向任一邊都有可觀察的失效。凍結得太晚時，歷史記錄仍持 live 參照，商品改名、下架或調價會改寫歷史訂單的顯示內容，訂單不再反映當時買了什麼；凍結得太早時，進行中的資料停在某一刻，購物車品項的價格不跟著會員身分的變動更新。業務流程有多個確認階段時，凍結點設在哪一個階段之後，取決於從那個階段起來源資料再漂移時，下游是否還能接受。凍結判斷標準的完整展開見 [entity 與 value object 的判斷標準](/software-design/ddd/entity-vs-value-object/)。
