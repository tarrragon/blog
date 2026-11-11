---
title: "Communication Protocol"
date: 2026-04-23
description: "說明不同系統如何對齊資料交換與錯誤語意"
weight: 128
---

Communication Protocol 的核心概念是「雙方對資料格式、順序、錯誤與互動方式達成一致的規則」。它描述的是通訊雙方如何交換資料，以及在失敗時如何解讀結果。 可先對照 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 跟其他概念的關係

Communication Protocol 位在 application、client、broker、[API Gateway](/backend/knowledge-cards/api-gateway/) 或 service 之間，決定兩端如何交換資料與解讀狀態。

## 可觀察訊號

系統需要 communication protocol 明確化的訊號是多個元件開始共用同一種資料交換方式。若格式不穩定，錯誤就會出現在解析、版本相容、重試語意或欄位命名上。

## 接近真實網路服務的例子

請求/回應型通訊、queue message schema、webhook payload 與簽章驗證，都屬於 communication protocol 問題。這類約定需要被拆到更具體的子卡，才能維持原子性。

## 判斷條件與後果

Communication protocol 的判斷對象是通訊雙方的行為裡，哪些已經寫成約定。版本相容沒有約定時，一端改了欄位或格式，另一端在解析時失敗；錯誤處理沒有約定時，兩端對同一個失敗回應各自解讀，一端認為該重試、另一端認為已經處理，重試語意因此分歧。欄位演進與測試方式沒有寫下來時，共用同一種資料交換方式的元件越多，每一對元件之間的隱含格式越多，改一個欄位要逐一確認所有呼叫端。格式越複雜，雙方要約定的行為越多，所以格式的複雜度收斂到雙方實際要交換的內容。
