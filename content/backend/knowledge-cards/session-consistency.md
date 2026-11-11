---
title: "Session Consistency"
date: 2026-05-13
description: "同一使用者工作階段內維持讀寫一致、跨工作階段允許短暫不一致"
weight: 247
---

Session consistency 的核心概念是「同一 session 內讀到自己剛寫入的資料」，但不保證全域即時一致。它的責任是在體感一致與系統延遲之間提供可操作折衷，位在 [external-consistency](/backend/knowledge-cards/external-consistency/) 與 eventual consistency 之間。

## 跟其他概念的關係

Session consistency 常出現在多區域資料庫的可調一致性模型，介於 [external-consistency](/backend/knowledge-cards/external-consistency/) 與 eventual consistency 之間。它常用於高互動產品路徑，降低讀者看到「我剛改完卻看不到」的落差。

## 可觀察訊號與例子

需要 session consistency 的訊號是「同一使用者回看自己操作結果時，短暫不一致會造成信任下降」，例如個人設定、遊戲狀態、用戶偏好。若是跨使用者共享狀態，仍要額外評估全域一致需求。

## 判斷條件與後果

Session consistency 的保證只在同一個 session 內成立，所以 session 的邊界畫在哪裡，決定使用者實際拿到多少「讀得到自己寫入」的保證。Session 以連線或 token 為邊界時，連線中斷而 token 沒有續存，重連後就是新的 session，使用者看不到自己剛寫入的資料；同一個使用者從手機與電腦操作時，兩個裝置是兩個 session，手機上的修改在電腦上可能還讀不到；web、app 與 API 各自定義 session 時，同一個操作在一個入口讀得到、在另一個入口讀不到，除錯時要先查出各入口的 session 定義，才分得出這是設計內的行為還是錯誤。跨使用者共享的狀態在這個保證之外，需要的話另外評估全域一致性。
