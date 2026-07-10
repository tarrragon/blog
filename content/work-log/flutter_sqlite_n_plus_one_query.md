---
title: "1000 本書、1001 次 SQL — N+1 查詢藏在 async mapper 裡"
date: 2026-07-10
draft: false
description: "N+1 查詢由兩個各自合理的函式組合而成：單筆轉換函式順便查關聯（mapper 做 IO）、列表方法用 Future.wait 把它乘以 N。修法是 IO 上移——一次批次 IN 查詢、記憶體組裝、轉換函式變純。mapper 簽名是 async 就是訊號；開發期資料量小、惡化是上線後隨資料成長的乘法。"
tags: ["flutter", "dart", "sqlite", "sqflite", "performance", "n-plus-one", "repository"]
---

> **觸發場景**：Flutter 書籍管理 App 進效能優化階段（UC-08）的現況盤點，抓到一個 P0：`getAllBooks()` 對 1000 本書發出 1001 次 SQL 查詢、耗時約 2 秒；推算 10000 本書要 20 秒、UI 完全卡死
> **疑問來源**：沒有人寫過「對每本書查一次資料庫」這種程式碼——這個 N+1 是怎麼長出來的？
> **整理目的**：記下 N+1 在 ORM 之外的手寫形態（async mapper）、修法的結構、以及為什麼它在開發期永遠感覺不到
> **本文邊界**：素材是該專案 v0.19.0 的 Phase 0 評估記錄；耗時數字是該記錄的影響評估、量級可信

---

## 形成：兩個各自合理的函式、組合出災難

問題程式碼拆開看，每一半都寫得很自然：

```dart
// 單筆轉換：把一列 DB map 轉成 Book——順便把它的 tags 查出來
Future<Book> _mapToBook(Map<String, dynamic> map) async {
  final db = await _database;
  final tagResult = await db.query('book_tags', ...);   // 每本書一次
  ...
}

// 列表查詢：撈全部、逐筆轉換
Future<List<Book>> getAllBooks() async {
  ...
  return Future.wait(result.map((map) => _mapToBook(map)));
}
```

`_mapToBook` 單看合理——Book 有 tags、轉換時補齊關聯是「完整的轉換」；`getAllBooks` 單看也合理——每筆都用同一個轉換函式、`Future.wait` 還做了並行。**N+1 不存在於任何一行、它存在於組合**：一個做 IO 的轉換函式、被一個列表方法乘以 N。

結構性的病灶是**mapper 做了 IO**。轉換函式的職責是「資料形狀的映射」，把查詢塞進去的那一刻，它的成本從 O(1) 記憶體操作變成一次網路 / 磁碟往返——而呼叫端從簽名上看不出來（回傳本來就是 Future、多一次 await 沒有任何警訊）。

## 為什麼開發期永遠感覺不到

影響評估的三個數字說明了它的隱身機制：100 本約 200ms、1000 本約 2 秒、10000 本約 20 秒。開發跟測試用的資料集是幾十本——200ms 以下、混在正常的載入時間裡無法察覺。**N+1 的惡化是使用者資料量的線性函數**，寫下它的人永遠不會遇到它爆炸的那天，遇到的是半年後書最多的那批使用者。

這也解釋了為什麼它由效能盤點抓到、而不是被任何測試抓到：功能測試的資料量跟開發期一樣小，而「查詢次數」不在任何斷言的守備範圍——除非專門寫「操作 X 的 SQL 次數 ≤ K」這種預算型測試。

## 修法：IO 上移、mapper 變純

修法的設計把查詢次數從 N+1 收斂到 2：

```dart
Future<List<Book>> getAllBooks() async {
  // 1. 一次撈所有書
  final books = await db.query('books', orderBy: 'added_date DESC');

  // 2. 一次撈所有標籤（IN 批次）
  final bookIds = books.map((b) => b['id']).toList();
  final allTags = await db.query('book_tags',
    where: 'book_id IN (${bookIds.map((_) => '?').join(',')})',
    whereArgs: bookIds);

  // 3. 記憶體組裝
  final tagsByBookId = _groupTagsByBookId(allTags);
  return books.map((b) => _mapToBookWithTags(b, tagsByBookId)).toList();
}
```

結構上的重點勝過次數本身：**IO 全部上移到列表方法、轉換函式變純**——`_mapToBookWithTags` 收「這本書的列」跟「查好的 tags 索引」、不碰資料庫。純轉換函式拿回了三個性質：成本可預期（呼叫 N 次就是 N 次記憶體操作）、可單獨測試（餵 map 斷言 Book）、且**結構上不可能再退化成 N+1**——它沒有 db 可查。這跟 [pure function 領域計算](/work-log/dart_unsettled_cart_pure_function/)是同一個藥方在資料層的應用：IO 在邊界、計算（轉換）在核心。

## 伴生發現：能力早就存在、預設路徑不經過它

同一次盤點還抓到第二個 P0——`allBooksProvider` 直呼 `getAllBooks()` 全量載入、記憶體隨書量膨脹。反直覺的是修這個問題**不用寫新能力**：repository 早就有 `getBooks(limit, offset)` 分頁方法、批次新增也有、快取系統也完整。能力都在、只是 UI 的預設路徑（`allBooksProvider`）不經過它們。

「有能力」跟「預設路徑用它」是兩回事——provider 是所有畫面拿書的入口、它選全載、分頁能力就是死碼。這是[工具的預設行為決定使用者習慣](/work-log/tool_default_behavior_shapes_user_habit/)的資料層版本：要讓分頁被用、要嘛預設 provider 就是分頁的、要嘛全載入口加上明確的成本標記，靠「大家記得用分頁版」跟靠任何慣例一樣不可靠。

## 判讀徵兆

- **mapper / 轉換函式的簽名是 `async`**——最便宜的掃描：`rg "Future<\w+> _mapTo" lib/`，每個命中都問它裡面的 await 在等什麼
- 迴圈或 `Future.wait` 裡呼叫「單筆處理」函式、而該函式含查詢——N+1 的標準組合形
- 某操作的耗時隨資料量線性惡化、但單筆操作很快——次數問題、不是單次效能問題
- repository 有分頁 / 批次 API、但 provider / service 層的預設入口全量載入——能力與預設路徑脫節

## 相關閱讀

- 同藥方的領域計算版：[「該收多少錢」抽成 pure function](/work-log/dart_unsettled_cart_pure_function/)——IO 在邊界、核心保持純，資料層與領域層各一個現場
- 預設路徑的原則：[工具的預設行為決定使用者習慣](/work-log/tool_default_behavior_shapes_user_habit/)——分頁能力閒置的機制跟工具預設值是同一件事
- 查詢預算的守法：[紅燈在量什麼](/work-log/flutter_test_signal_credibility_three_layers/)——效能特性要用專門的量測管道守、不是塞計時斷言進單元測試
