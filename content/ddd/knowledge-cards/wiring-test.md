---
title: "Wiring Test"
tags: ["接線測試", "wiring-test", "testing"]
date: 2026-07-13
description: "行為測試全綠、還想知道組裝有沒有完成時使用。接線測試在組裝路徑零 override 的環境解析每個注入項、走真實路由表，只驗「port 插上了 adapter」。"
weight: 12
---

接線測試（wiring test）只回答一個問題：[port](/ddd/knowledge-cards/port/) 插上 [adapter](/ddd/knowledge-cards/adapter/) 了沒。做法是讓組裝路徑保持零 override——每個 [依賴注入](/ddd/knowledge-cards/dependency-injection/) 的注入項真實解析、路由表真實導航、UI 事件真實觸發——功能邏輯的對錯留給行為測試。

## 概念位置

一個測試通過時能證明的事（[本模組](/ddd/) 稱「證言」）由執行環境決定：在 [test seam](/ddd/knowledge-cards/test-seam/) 換上 mock 之後、綠燈對組裝再無證明力，接線測試因此是測試層面組裝證言的唯一來源（編譯期生成組裝碼的生態、編譯器先接住「缺實作」一類，其餘仍歸這裡）。跟端對端測試的分工是範圍換速度：E2E 在目標平台連行為一起驗、接線測試只驗接線，換取在 host 環境（開發機、非目標裝置）快速且確定地執行。

## 可觀察訊號

個別測試用 override 是正當的 seam 用法；訊號要看專案層級——連一個零 override 的解析測試都沒有時、組裝處於無人作證的狀態。

## 設計責任

零 override 的邊界是組裝路徑：domain 到入口之間不替換任何一段、最外圈的 infrastructure（遠端服務這類）可以在邊界替換。回傳假值的 [佔位](/ddd/knowledge-cards/placeholder/) 解析得了、導航也會發生、在接線測試眼中是正常構件，要靠行為斷言或發版冒煙走查。這條界線在應用程式層怎麼守、[組裝層的可達性](/ddd/composition-root-reachability/) 有完整推導。
