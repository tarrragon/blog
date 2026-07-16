---
title: "Port"
tags: ["port", "hexagonal-architecture"]
date: 2026-07-13
description: "判斷介面該宣告在哪一層、依賴方向該朝哪時使用。port 是 domain 對外宣告的介面——需求用領域語言說完、技術細節留在實作端。"
weight: 7
---

port 是 domain 對外宣告的介面：領域層用領域語言把需求說完——「我需要一個能存書、能查書的地方」——不提資料庫、不提網路。依賴方向因此朝內：實作端依賴介面、介面屬於領域，技術選型換掉時領域碼不動。port 的具體實作是 [adapter](/ddd/knowledge-cards/adapter/)、兩者插上的位置是 [composition root](/ddd/knowledge-cards/composition-root/)。

## 概念位置

port 跟一般 interface 的差別在歸屬與語言：宣告在領域層、以領域概念命名（BookRepository 而非 SqliteClient）、方法簽名只用領域型別。介面本身是型別層的約束載體——它強制了「呼叫方看不見技術細節」，與 [invariant](/ddd/knowledge-cards/invariant/) 的型別層強制同一個機制。

## 可觀察訊號

介面檔案位於 domain 目錄、簽名沒有框架型別，是 port 健康的訊號。介面裡出現 DatabaseConnection、HttpClient 這類技術型別時，port 已被實作細節滲透——呼叫方被迫認識它不該認識的層。

## 設計責任

port 定義「領域需要什麼」，不保證「有人供給它」——宣告了介面、沒有實作被插上，在 mock 測試裡不會有任何紅燈。供給的驗證屬組裝層，教學層展開見 [組裝層的可達性](/ddd/composition-root-reachability/)。port 的歸屬判準（逐型別問「這是誰的詞彙」）在 reactive 場景的完整推導見 [觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/)。
