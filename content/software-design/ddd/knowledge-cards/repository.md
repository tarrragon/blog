---
title: "Repository"
tags: ["repository", "aggregate-root", "port"]
date: 2026-07-20
description: "查詢方法該留在 repository、還是該抽成獨立讀模型時使用。repository 是 aggregate 的存取抽象——回傳的形狀是 aggregate 的形狀，不是讀的形狀。"
weight: 18
aliases: ["/ddd/knowledge-cards/repository/"]
---

repository 把「怎麼存、怎麼查」包裝成領域語言的介面：呼叫端看到的是存書、查書這類操作，看不到底層是資料庫、檔案還是記憶體。它是一種 [port](/software-design/ddd/knowledge-cards/port/)——依賴方向朝內、簽名只用領域型別——差別在 repository 專職 [aggregate root](/software-design/ddd/knowledge-cards/aggregate-root/) 的存取。repository 回傳的形狀是 aggregate 的形狀（entity 或 entity 集合），這條界線是它跟 [read model](/software-design/ddd/knowledge-cards/read-model/) 分工的起點。

## 跟其他概念的關係

repository 預設是 pull 介面：呼叫端主動問「現在的資料長怎樣」，一次拿到一份 aggregate 形狀的答案。它不天生具備「資料變了通知我」的推送能力——這條能力屬於 [observation outlet](/software-design/ddd/knowledge-cards/observation-outlet/)，是 repository 介面之上的另一層職責，需要另外設計才會出現。

## 可觀察訊號

repository 介面開始長出 `getMonthlyStatistics()`、`searchWithPagination()` 這類回傳統計值或反正規化形狀的方法，是讀的形狀混進 aggregate 介面的訊號——查詢集合已經大到值得思考該不該抽獨立的讀側介面，量測與升級路徑見 [讀模型的升級條件](/software-design/ddd/read-model-upgrade-signals/)。

## 判斷條件與後果

一個方法是否屬於 repository，看它回傳的形狀與它的簽名用什麼語言表達。回傳 aggregate 形狀（entity 或 entity 集合）的方法屬於 repository，它是 aggregate 一致性邊界的存取入口；回傳統計值或反正規化形狀的方法放進來時，repository 同時服務寫側的一致性與讀側的各種形狀，介面隨查詢數增長，這類方法屬於 [read model](/software-design/ddd/knowledge-cards/read-model/)。變更通知的歸屬用同一種判斷：簽名只用語言標準庫與 domain entity 寫得出來的觀測方法，跟 pull 方法一起放在 domain repository 介面；要用到框架型別才寫得出來的部分，歸 adapter 或組裝層。歸屬依各層產出的表達語言決定，提出需求的是哪一個畫面不改變它，完整推導見 [觀測出口的職責三分](/software-design/ddd/observation-outlet-responsibility-split/)。
