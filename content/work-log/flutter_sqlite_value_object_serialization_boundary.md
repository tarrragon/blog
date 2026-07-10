---
title: "SQLite 只吃三種型別 — value object 在持久化邊界的序列化契約"
date: 2026-07-10
draft: false
description: "把 value object 直接塞給 sqflite 會炸 Invalid argument——SQLite 只接受 num / String / Uint8List，VO 必須在 repository 邊界拆成基本型別、讀回時重建。用 toString/fromString 當轉換通道是權宜：它依賴兩者對稱這條沒人強制的隱性契約，正解是語意明確的序列化方法。"
tags: ["flutter", "dart", "sqlite", "sqflite", "value-object", "serialization", "repository"]
---

> **觸發場景**：Flutter 書籍管理 App 的資料庫整合測試全面失敗，錯誤訊息：`Invalid argument 整合測試作者 with type BookAuthor. Only num, String and Uint8List are supported`——所有涉及 SQLite 的 CRUD 操作都掛
> **疑問來源**：同一個 map 裡 `id` 跟 `title` 都存得進去，為什麼 `author` 炸了？
> **整理目的**：記下 value object 跨持久化邊界的轉換責任、以及 toString/fromString 這條隱性契約的風險
> **本文邊界**：素材是該專案 v0.10.6 的修復規劃記錄；sqflite 的型別限制是 SQLite 本身的特性、不是套件的設計選擇

---

## 錯誤現場：三個欄位、兩種寫法

炸點在 repository 把 entity 轉成資料庫 map 的方法：

```dart
Map<String, dynamic> _bookToMap(Book book) {
  return {
    'id': book.id.toString(),        // BookId → String，存得進去
    'title': book.title.toString(),  // BookTitle → String，存得進去
    'author': book.author,           // BookAuthor 物件直接塞 → 炸
    ...
  };
}
```

sqflite 底下的 SQLite 只接受 `num`、`String`、`Uint8List` 三種型別。`BookAuthor` 是帶內部狀態的 value object（作者清單、譯者），直接放進 map 就是把一個 Dart 物件遞給不認識它的儲存引擎。錯誤訊息其實說得很清楚——難的不是修，是這個錯誤揭露的責任問題：**誰負責把領域型別拆成儲存型別？**

## 責任歸位：轉換發生在 repository 邊界

修法本身一行：`'author': book.author.toString()`；讀回的方向 `_mapToBook` 已經在用 `BookAuthor.fromString(map['author'])` 重建。架構上這是 adapter 的職責放在 repository 層——domain 的 value object 不知道 SQLite 存在、SQLite 不知道 value object 存在，兩個世界的轉換集中在 I/O 邊界的 `_bookToMap` / `_mapToBook` 一對方法裡。

這個歸位讓錯誤的形態變得可預測：**每個新的 VO 欄位都要在這對方法裡出現一次**，漏掉序列化端會炸 Invalid argument（吵、好抓）、漏掉反序列化端會在讀取時炸型別轉換（也吵）。真正安靜的坑在第三種情況——兩端都寫了、但不對稱。

## 隱性契約：toString 與 fromString 的對稱性沒人強制

用 `toString()` / `fromString()` 當序列化通道，工作的前提是 `fromString(x.toString()) == x`——而這條契約沒有任何機制在守。修復記錄自己就把風險寫進了已知限制：複雜物件轉字串可能遺失部分內部狀態、未來需要更精細的序列化機制。

具體的斷裂點兩種。其一，`toString()` 的本業是除錯表示，哪天有人為了 log 可讀性把格式改成 `BookAuthor(name: ...)`，資料庫裡從此存進去的是新格式、舊資料用新 `fromString` 讀不回來——**兩個消費者（除錯與持久化）寄生在同一個方法上、變更理由不同步**。其二，格式本身有損：這個專案的 `BookAuthor` 把多作者序列化成「作者1, 作者2」、譯者成「作者 (譯者 譯)」——作者名字裡出現逗號或括號時，roundtrip 就不再對稱。

正解方向修復記錄也留了：語意明確的序列化介面（`toDbValue()` / 專用 `Serializable`、或 JSON 結構化），讓「持久化格式」成為一個有自己名字、自己測試、自己變更理由的東西。過渡期至少要補上對稱性測試——對每個 VO 斷言 `fromString(v.toString()) == v`、含邊界值（空作者、多作者、含譯者），把隱性契約變成會紅的測試。

## 判讀徵兆

- `Invalid argument ... with type X. Only num, String and Uint8List are supported`——X 就是漏轉換的 VO、去 `_toMap` 系方法找它
- repository 的 map 轉換裡混用「物件直接放」跟「`.toString()`」兩種寫法——前者是還沒炸的候選
- `toString()` 同時服務除錯輸出跟持久化 / 快取 key——語意寄生，兩個消費者遲早有一個要改格式
- VO 有 `fromString` 但測試裡沒有任何 roundtrip 斷言——對稱契約處於未驗證狀態

## 相關閱讀

- 出口語意的原則版：[VO 封裝擺盪](/work-log/flutter_value_object_encapsulation_oscillation/)——那篇論證「原始值要有語意明確的官方出口」，本文是 `toString()` 被當出口用的實際風險清單
- 持久化邊界的另一面：[功能完成卻從未持久化](/work-log/flutter_feature_complete_never_persisted/)——那篇是欄位沒進出邊界、本文是進了邊界但轉換錯誤，roundtrip 測試同時守住兩者
- 概念地基：[DDD 領域驅動設計指南](/ddd/) 的 entity 持久化邊界章節
