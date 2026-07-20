---
title: "Repository"
tags: ["repository", "aggregate-root", "port"]
date: 2026-07-20
description: "查詢方法該留在 repository、還是該抽成獨立讀模型時使用。repository 是 aggregate 的存取抽象——回傳的形狀是 aggregate 的形狀，不是讀的形狀。"
weight: 18
---

repository 把「怎麼存、怎麼查」包裝成領域語言的介面：呼叫端看到的是存書、查書這類操作，看不到底層是資料庫、檔案還是記憶體。它是一種 [port](/ddd/knowledge-cards/port/)——依賴方向朝內、簽名只用領域型別——差別在 repository 專職 [aggregate root](/ddd/knowledge-cards/aggregate-root/) 的存取。repository 回傳的形狀是 aggregate 的形狀（entity 或 entity 集合），這條界線是它跟 [read model](/ddd/knowledge-cards/read-model/) 分工的起點。

## 概念位置

repository 預設是 pull 介面：呼叫端主動問「現在的資料長怎樣」，一次拿到一份 aggregate 形狀的答案。它不天生具備「資料變了通知我」的推送能力——這條能力屬於 [observation outlet](/ddd/knowledge-cards/observation-outlet/)，是 repository 介面之上的另一層職責，需要另外設計才會出現。

## 可觀察訊號

repository 介面開始長出 `getMonthlyStatistics()`、`searchWithPagination()` 這類回傳統計值或反正規化形狀的方法，是讀的形狀混進 aggregate 介面的訊號——查詢集合已經大到值得思考該不該抽獨立的讀側介面，量測與升級路徑見 [讀模型的升級判準](/ddd/read-model-upgrade-signals/)。

## 設計責任

repository 的設計責任是守住 aggregate 一致性邊界的存取入口，不是最佳化每一種讀需求的效能與形狀——後者是 read model 的責任。repository 是否該同時扛下變更通知，判準不是「需求來自誰」而是介面用什麼語言表達，完整推導見 [觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/)。
