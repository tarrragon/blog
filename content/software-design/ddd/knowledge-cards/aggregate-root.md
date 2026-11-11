---
title: "Aggregate Root"
tags: ["聚合根", "Aggregate Root"]
date: 2026-07-10
description: "跨物件一致性的邊界設計時使用。聚合根是對外代表一組資料一致性的邊界物件——外部只跟它互動、它保證內部的不變式。"
weight: 4
aliases: ["/ddd/knowledge-cards/aggregate-root/"]
---

聚合根是對外代表一組資料一致性的邊界物件。外部操作只跟聚合根互動、不直接碰內部的 [entity](/software-design/ddd/knowledge-cards/entity/) 或 [value object](/software-design/ddd/knowledge-cards/value-object/)；聚合根負責保證邊界內所有[不變式](/software-design/ddd/knowledge-cards/invariant/)在每次操作結束時成立。一致性的範圍就是聚合的邊界——邊界內是同一個事務、邊界外是最終一致。

## 跟其他概念的關係

聚合根是本模組尚未展開的章節主題（模組 backlog）。目前在教學章中以例子形態出現：一個 POS 專案的商品從扁平結構長成雙層聚合——商品作為聚合根、規格作為子層——欄位歸屬的判斷標準是「兩個規格會不會不同」（[資料袋與領域模型](/software-design/ddd/data-bag-vs-domain-model/)）。聚合的邊界跟 [entity](/software-design/ddd/knowledge-cards/entity/) 的生命週期邊界是兩個獨立的設計決策。

## 可觀察訊號

多個物件的修改必須一起成功或一起失敗、而這些物件目前散在不同的存取路徑——缺少聚合根把它們收在同一個一致性邊界裡。

## 判斷條件與後果

聚合的邊界大小決定一次事務鎖住多少物件。邊界劃得太大時，彼此沒有共同不變式的物件被收進同一個事務，修改其中一個也要鎖住其餘的，併發的寫入因此互相等待；邊界劃得太小時，一條必須一起成立的不變式跨了兩個聚合，沒有一個聚合根負責檢查它，這份一致性的檢查推到應用層，由呼叫端自己協調。兩種情形的分界是「哪些不變式必須在同一次操作內成立」：被同一條不變式綁住的物件收進同一個聚合，其餘的留在邊界外、接受最終一致。
