---
title: "同一個類別被判成兩個型別 — Dart import 的相對路徑與 package 路徑衝突"
date: 2026-07-10
draft: false
description: "錯誤訊息出現 LibraryId/*1*/ 與 LibraryId/*2*/、兩行 from 一個指 lib/ 一個指 package:，就是同一個檔案被兩種 URI 匯入——Dart 的 library 身份由匯入 URI 決定、不由檔案決定，相對路徑跨進 lib/ 會製造出平行的型別宇宙。修法是全案統一 package 路徑並用 lint 規則封死。"
tags: ["dart", "flutter", "import", "type-system", "lint", "debugging"]
---

> **觸發場景**：Flutter 專案的大量測試突然因「型別不匹配」失敗——明明傳入的就是 `LibraryId`、參數要的也是 `LibraryId`。錯誤訊息裡藏著答案：`'LibraryId/*1*/' is from 'lib/domains/library/value_objects/library_id.dart'`、`'LibraryId/*2*/' is from 'package:book_overview_app/domains/library/value_objects/library_id.dart'`
> **疑問來源**：兩行 from 指向的是**同一個實體檔案**，為什麼編譯器認為是兩個型別？
> **整理目的**：記下 Dart library 身份的判定機制、錯誤訊息的辨識法、以及讓這類衝突不再發生的 lint 封鎖
> **本文邊界**：素材是該專案 v0.2.1 的全案修復記錄（13+ 檔）；機制是 Dart 語言層的、跟 Flutter 無關

---

## 機制：library 的身份是 URI、不是檔案

Dart 把每個匯入來源視為一個 library，而 library 的身份由**匯入 URI** 決定。同一個實體檔案可以被兩種 URI 指到：

```dart
// 寫法一：相對路徑（從 test/ 一路爬回 lib/）
import '../../../lib/domains/library/value_objects/library_id.dart';

// 寫法二：package 路徑
import 'package:book_overview_app/domains/library/value_objects/library_id.dart';
```

兩個 URI 不相等，編譯器就載入**兩份獨立的 library**——同一個檔案的內容被實體化兩次，裡面的 `LibraryId` 是兩個互不相容的型別。用寫法一建出來的物件、傳進用寫法二宣告參數的函式，型別檢查如實地失敗：它們真的不是同一個 class。

錯誤訊息的 `/*1*/`、`/*2*/` 後綴就是編譯器在標注「同名、不同 library」。看到這個後綴、再看兩行 `is from` 一個以 `lib/` 開頭（file URI）一個以 `package:` 開頭，診斷就完成了——不用懷疑業務邏輯，是匯入方式分裂。

## 為什麼會混用：test/ 是重災區

lib/ 內部檔案互相引用時，相對路徑（`../entities/book.dart`）跟 package 路徑解析出來的 URI 形式一致、不會分裂。分裂發生在**從 lib/ 外面往裡面伸手**的時候——test/、工具腳本用 `../../../lib/...` 爬進去，URI 就成了 file 形式，跟 lib/ 內部或其他測試用的 package 形式撞出兩個宇宙。

這個專案的分佈證實了這點：修復的 13+ 個檔案幾乎全是測試（整合測試、單元測試、widget 測試、mock）加上兩個根目錄的驗證腳本。混用不是誰的失誤，是兩種寫法在各自的檔案裡都「能跑」、IDE 的自動匯入又兩種都可能生成——衝突要等兩個宇宙的物件在某個函式簽名相遇才爆炸，而那可能是好幾週後。

## 修法與封鎖

修復本身是機械的：全案統一成 package 路徑（策略上用系統性 grep 掃描所有 import 語句、批次修復，比逐個追錯誤訊息有效率——一條錯誤只暴露一對衝突、掃描才看得到全部）。

比修復更重要的是封死再犯路徑。這類問題「修完之後每個新檔案都是再犯機會」，靠的不能是團隊記憶：

- **lint 規則**：Dart 官方 linter 有現成的 `always_use_package_imports`，開在 `analysis_options.yaml` 裡讓相對路徑匯入 lib/ 直接被 analyzer 標紅
- **CI 檢查**：analyzer 進 CI，混用在 PR 階段就擋下

這是「約束要落在工具層、不落在文件層」的小號實例：開發指南寫「請用 package 路徑」擋不住 IDE 自動匯入的手滑，lint 規則可以。

## 判讀徵兆

- 錯誤訊息同名型別帶 `/*1*/`、`/*2*/` 後綴——直接確診，去看兩行 from 的 URI 形式
- 「明明型別一樣卻不匹配」且發生在測試傳物件給 lib/ 函式的邊界——優先懷疑匯入分裂、不是業務邏輯
- test/ 檔案裡出現 `import '../` 且路徑含 `lib/`——還沒爆的候選，`rg "import '\.\./.*lib/" test/` 一次掃完
- 同一個 class 的 IDE「跳到定義」從不同檔案跳到同一處、但 analyzer 又報型別錯——兩份 library 的實體化證據

## 相關閱讀

- 約束落點的原則層：[#222 約束要讓違反路徑走不通](/report/design-intent-needs-enforcement-layer/)——「開發指南寫請用 package 路徑」是文件層意圖，lint 規則才是讓違反走不通的工具層落點
- 同專案的另一個 Dart 語言機制陷阱：[late final 欄位不能用欄位覆蓋](/work-log/late_final_field_override_getter_setter/)——同屬「語言規則跟直覺相左、錯誤訊息是最快入口」的家族
