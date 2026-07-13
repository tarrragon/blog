---
title: "Composition Root"
tags: ["composition-root", "dependency-injection"]
date: 2026-07-13
description: "依賴組裝、路由註冊該集中在哪、組裝斷裂去哪檢查時使用。composition root 是應用程式唯一的組裝起點——DI、路由、事件接線的集中處。"
weight: 9
---

composition root（組裝根）是應用程式唯一的組裝起點：所有 [port](/ddd/knowledge-cards/port/) 在這裡被插上 [adapter](/ddd/knowledge-cards/adapter/)——DI 容器的註冊、啟動流程的接線集中於此。它通常是 main 函式旁的一小塊：知道全部具體型別的地方、也是唯一該知道的地方。

## 概念位置

composition root 是組裝層的核心、不是組裝層的全部：路由表以單點註冊靠攏它，UI 事件的接線散佈在各畫面——位置不同、同屬組裝層的責任。組裝層守「正確的路徑走得通」，與 [invariant](/ddd/knowledge-cards/invariant/) 守「違反的路徑走不通」互為對偶。

## 可觀察訊號

具體型別的建構與註冊集中在一處，是組裝責任歸位的訊號。new 語句散落各層、或 provider 停在佔位 throw「requires override」，是組裝責任洩漏或組裝未完成——後者在 mock 測試下全綠、只有無 override 的解析會暴露。

## 設計責任

組裝有沒有完成，在以 mock 為基礎的測試套件裡沒有證言；補證言的接線測試、可達性作為不變式的強制層選擇，教學層展開見 [組裝層的可達性](/ddd/composition-root-reachability/)。
