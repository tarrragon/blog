---
title: "Test Seam"
tags: ["測試 seam", "test-seam", "testing"]
date: 2026-07-13
description: "測試想把真實依賴換成替身、該從哪裡換時使用。seam 是不修改程式本體就能替換其中一段行為的位置——介面加注入點是物件導向最常見的形式。"
weight: 11
---

測試 seam 是不修改程式本體就能替換其中一段行為的位置——術語出自 Michael Feathers 的《Working Effectively with Legacy Code》。物件導向程式最常見的 seam 是介面加注入點：[port](/ddd/knowledge-cards/port/) 宣告需求、[依賴注入](/ddd/knowledge-cards/dependency-injection/) 提供替換的入口，測試在這裡把真實 [adapter](/ddd/knowledge-cards/adapter/) 換成 mock、讓 domain 邏輯脫離資料庫與網路單獨驗證。

## 概念位置

seam 是分層架構測試承諾的兌現機制：「domain 可以脫離 infrastructure 測試」的具體操作、就是在 seam 換上替身。DI 容器的 override（測試用替身蓋過註冊項）是 seam 的容器化形式；[composition root](/ddd/knowledge-cards/composition-root/) 集中的組裝、正是 seam 替換的對象。

## 可觀察訊號

測試不碰 production 程式碼就能把資料庫、網路、時鐘換成替身，是 seam 工作中的訊號。想測某段邏輯必須連上真實服務、或得修改本體才塞得進替身，是 seam 缺席的訊號。

## 設計責任

seam 有一體兩面：替換掉的正是 production 的組裝、於是「組裝有沒有完成」在以 seam 為基礎的測試裡沒有證言（綠燈證明不了組裝完成）。mock 測試全綠與功能可用之間的缺口由 [接線測試](/ddd/knowledge-cards/wiring-test/) 補；這道影子的完整推導見 [組裝層的可達性](/ddd/composition-root-reachability/)。
