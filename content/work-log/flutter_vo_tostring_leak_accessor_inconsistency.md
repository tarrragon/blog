---
title: "取個原始值有四種寫法 — VO 的 toString 洩漏與 accessor 不一致"
date: 2026-07-10
draft: false
description: "value object 家族的取值 accessor 各自為政（displayValue、toString、裸欄位）時，殺傷力會在測試層爆開：自定義 toString 讓裸字串斷言全數過期、四種取法讓修復者自己都寫錯。止血是 helper 函數庫集中取值知識、根治是家族統一 accessor 命名。"
tags: ["flutter", "dart", "value-object", "testing", "api-design", "refactoring"]
---

> **觸發場景**：Flutter 書籍管理 App 引入 value object 之後，估計 100+ 個測試失敗——`expect(book.title, '測試書籍')` 這類斷言全數過期，因為 `book.title` 現在是 `BookTitle`、它的 `toString()` 回傳 `BookTitle:<測試書籍>`
> **疑問來源**：改斷言就好？改成什麼——`.value`、`.displayValue`、還是 `toString()`？追下去發現這個問題本身就是病灶
> **整理目的**：記下 VO 取值 accessor 不一致的兩層傷害、以及「集中取值知識」的止血法
> **本文邊界**：素材是該專案 v0.11.15 的測試修復計畫與執行記錄；accessor 混亂的成因（`.value` 的存廢擺盪）在[另一篇](/work-log/flutter_value_object_encapsulation_oscillation/)有完整弧線

---

## 第一層傷害：toString 洩漏讓裸字串斷言靜默過期

欄位從 `String` 升級成 value object 之後，型別變了、但舊斷言不會編譯失敗——`expect(actual, expected)` 的參數是 dynamic，`BookTitle` 跟 `'測試書籍'` 的比較合法地在 runtime 回 false。於是 VO 引入前累積的所有裸字串斷言，以「測試失敗」而不是「編譯錯誤」的形式集體過期，一次 100+ 個。

自定義 `toString()`（`BookTitle:<測試書籍>` 這種帶型別前綴的除錯格式）讓失敗訊息更迷惑：期望值跟實際值看起來「幾乎一樣」，差一層包裝。這是 toString 語意寄生的又一個現場——它的本業是除錯表示，被斷言、被序列化、被快取 key 借用時，每個借用者都對它的格式有隱性依賴。

## 第二層傷害：四種取法、連修復者都寫錯

修復計畫的第一版推薦「改用 `.value` 屬性」：

```dart
expect(book.title.value, '測試書籍');   // 修復計畫推薦的寫法
```

執行階段發現這個推薦本身是錯的——實際的 accessor 分佈是：`BookTitle` 跟 `BookAuthor` 用 `.displayValue`、`BookId` 只能 `toString()`、`isbn` 根本是裸 `String?` 不用取值。**「取原始值」在四個相鄰型別上是四種寫法**，連專門來修這個問題的人都先踩了一次。

這是介面不一致的可測量代價：API 的使用知識無法從一個型別遷移到下一個，每次使用都是一次查閱或一次賭注。而這個混亂不是誰設計出來的——它是 `.value` 存廢擺盪的沉積物：封裝重構移除了 `.value`、留下 `toString()` 跟 `displayValue` 兩個出口、緊急修復又給部分型別加回 `.value`，幾輪下來每個 VO 停在擺盪的不同相位上。

## 止血：helper 函數庫集中取值知識

逐個改 100+ 斷言的過程中，策略從「批次改寫」轉向「建輔助函數庫」：

```dart
// test/helpers/value_object_test_helpers.dart
expectBookTitleEquals(book.title, '測試書籍');
expectBookAuthorEquals(book.author, '作者名');
```

helper 把「每個 VO 怎麼取原始值」的知識**集中在一個檔案**：斷言的呼叫端不再需要知道 `BookTitle` 用 `displayValue` 而 `BookId` 用 `toString()`——它們長得一樣、內部各自處理差異。附帶的複利是未來 accessor 再變動（例如統一成單一名字）時，要改的位置從 100+ 個斷言縮成一個 helper 檔。

要分清楚的是：helper 是**止血、不是根治**。它讓不一致的 API 可以被一致地使用，但不一致本身還在——lib/ 端的每個新消費者仍會面對四種取法。根治是家族統一 accessor（同名、同語意、同回傳型別），而那要先解決擺盪篇談的「出口語意」問題：先決定每個出口給誰用，名字才定得下來。

## 判讀徵兆

- 型別升級（String → VO）後測試大量失敗、失敗訊息的期望與實際「差一層包裝」——裸值斷言過期，別逐個修、先決定統一的比較方式
- 同一家族的型別、取原始值的寫法超過一種——API 知識不可遷移，每個消費者都在重新學
- 修復計畫裡寫的 accessor 跟實作對不上——不一致已經騙到文件層了，這是「先盤點再動手」的訊號
- 測試 helper 裡出現 per-type 的比較函數——止血有效，但把「統一 accessor」記進債務清單，別讓 helper 的存在掩蓋根治的必要

## 相關閱讀

- 成因的完整弧線：[VO 封裝擺盪](/work-log/flutter_value_object_encapsulation_oscillation/)——四種取法是全移除、完全封裝、加回 getter 幾輪擺盪的沉積物
- toString 語意寄生的另一個現場：[SQLite 只吃三種型別](/work-log/flutter_sqlite_value_object_serialization_boundary/)——除錯表示被借去當持久化通道
- 概念地基：[DDD 領域驅動設計指南](/ddd/)——value object 的介面也是模組的公開契約、家族一致性是契約的一部分
