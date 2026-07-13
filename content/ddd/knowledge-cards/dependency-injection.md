---
title: "Dependency Injection"
tags: ["依賴注入", "dependency-injection"]
date: 2026-07-13
description: "物件的依賴該由誰提供、測試怎麼換掉真實依賴時使用。依賴注入把「建構依賴」跟「使用依賴」分成兩個責任——使用方宣告需要什麼、提供方在組裝時決定給什麼。"
weight: 10
---

依賴注入（dependency injection、DI）把「建構依賴」跟「使用依賴」分成兩個責任：物件宣告它需要什麼（通常以 [port](/ddd/knowledge-cards/port/) 這樣的介面表達）、實例由外部在組裝時提供——最基本的形式是建構子參數。物件自己建構依賴時、依賴的選擇被寫死在使用處；改由外部注入後、同一段程式碼在 production 拿到真實 [adapter](/ddd/knowledge-cards/adapter/)、在測試拿到替身。

## 概念位置

DI 容器是框架提供的註冊與解析機制、把「哪個介面對應哪個實作」收成一份註冊表：啟動時註冊、使用時解析——每一條可解析的註冊項就是一個注入項、部分生態稱它 provider。注入的集中點是 [composition root](/ddd/knowledge-cards/composition-root/)：全部具體型別在這裡被決定。測試框架的 override 機制（用替身蓋過註冊項）是 DI 給測試的 [seam](/ddd/knowledge-cards/test-seam/)。

## 可觀察訊號

建構子收介面、具體實作的選擇集中在組裝處，是注入責任歸位的訊號。類別內部直接建構自己的依賴（new 具體型別、呼叫全域單例）時、該依賴在測試裡換不掉、技術選擇散落各層。

## 設計責任

注入讓「誰提供真實作」成為一個獨立責任。這個責任有沒有被履行——每個注入項在無 override 環境解析得了——在行為測試裡沒有證言（綠燈證明不了它）、要由 [接線測試](/ddd/knowledge-cards/wiring-test/) 驗證；教學層展開見 [組裝層的可達性](/ddd/composition-root-reachability/)。
