---
title: "Real-Backend Verification Test（真實後端驗證測試）"
date: 2026-07-17
description: "對共用測試環境常駐斷言後端業務行為的測試；紅、綠、跳過各有語意，承接假後端固化行為的漂移警報"
weight: 7
tags: ["testing", "real-backend", "integration-test"]
---

當[語意級假後端](/testing/knowledge-cards/semantic-fake-backend/)把後端行為固化成「已知」，真實後端驗證測試承擔配對的另一半責任：對真實後端常駐斷言這些行為，讓後端行為漂移有地方現形。兩者是同一份行為知識的兩面——假後端寫「我們認為後端會這樣做」，驗證測試證明「後端現在確實這樣做」。

## 跟其他概念的關係

與 [protocol integration test](/testing/knowledge-cards/protocol-integration-test/) 的拆卡邊界是 transport vs workflow：protocol integration test 驗證協議契約（連線、握手、編碼），對可本機啟動的服務實例執行；真實後端驗證測試斷言業務行為（後端動詞的效果：建立、釋放、狀態轉換），適用於後端無法本機啟動、只有共用測試環境的情境。

## 可觀察訊號與例子

它的識別特徵是紅、綠、跳過三態各有語意：綠代表後端行為與假後端固化的版本一致，紅代表行為漂移或防線腐化（登入被拒），跳過代表環境暫時不可達。非同步生效的區分（同步生效、非同步生效、未生效）曾為前後端責任歸因提供定案手段（[症狀相同、成因兩種 — 用測試切開前後端責任](/testing/cases/dual-semantics-attribution/)）。

## 判斷條件與後果

這層測試的四項決策，各自對應一種讓漂移偵測失效的狀態。形態上沒有寫成正規測試、沒有併入整合套件或預設不可執行時，測試只在有人手動啟動時才跑，後端行為在兩次執行之間的漂移沒有地方現形。請求層繞過產品自己的 API client 時，測試驗證的是另一條呼叫路徑，產品實際送出的請求是否被後端接受沒有被驗到。劇本沒有現場復原時，共用測試環境留著前一次執行建立的資料，下一次執行的前提跟著改變。CI 節奏沒有依連通性對應時，連不到測試環境的 CI 每次都回報跳過，三態判讀退化成只剩跳過一種結果。每一條決策對應的歧路與防線設計在[真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)章。
