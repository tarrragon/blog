---
title: "1101 行自建測試基礎設施、重構刪掉 82.5% — 過度工程的三種形態"
date: 2026-07-10
draft: false
description: "自建測試基礎設施前先問框架的標準做法是什麼：mock 純資料物件、helper 帶並發鎖與記憶體洩漏防護、mock 放進 lib/ 進生產依賴圖，三種形態都在重新發明 Riverpod overrideWith 一行就有的東西。精緻的設計文件不是價值證明——它可以精心規劃一個不需要存在的系統。"
tags: ["flutter", "dart", "testing", "riverpod", "over-engineering", "refactoring", "mock"]
---

> **觸發場景**：Flutter 書籍管理 App 的 Widget 測試基礎設施，設計階段產出 783 行的完整規格、實作 1101 行；下一個 Phase 的重構審查判定整套重做，刪到剩 193 行（-82.5%）、其中核心 helper 62 行
> **疑問來源**：一套經過完整設計流程、有架構圖有依賴規範的基礎設施，為什麼是該刪的？審查依據是什麼？
> **整理目的**：把這次刪除拆成三種可辨識的過度工程形態、以及「寫測試工具之前」的檢查點
> **本文邊界**：素材是該專案 v0.7.0 的 Phase 1 設計文件與 Phase 4 重構記錄——同一個東西的誕生與死亡、對照完整

---

## 被刪掉的是什麼

四個檔案、一個目錄：

| 檔案                                                 | 行數 | 職責                                                         |
| ---------------------------------------------------- | ---- | ------------------------------------------------------------ |
| `lib/mocks/widget_test_mocks.dart`                   | 389  | Mock 架構（含 `MockBook`、Mock Provider 群）                 |
| `lib/helpers/multi_language_widget_test_helper.dart` | 388  | 多語系測試工具（Mutex 狀態鎖、記憶體洩漏防護、三類溢位檢測） |
| `lib/helpers/widget_test_helper.dart`                | 193  | 自建測試環境建立工具                                         |
| `lib/helpers/test_logger.dart`                       | 131  | 自製測試日誌系統                                             |

取代它們的是 62 行的 helper 加標準 Riverpod 模式：

```dart
WidgetTestHelper.createFullTestApp(
  const LibraryDisplayPage(),
  [libraryDisplayViewModelProvider.overrideWith(() =>
      LibraryDisplayViewModelForTest(LibraryDisplayState()))],
);
```

功能沒有變少——變少的是「為了用這套工具而要學的東西」。

## 形態一：重新發明框架已有的輪子

整套 Mock Provider 架構要解的問題——「測試時把真實依賴換成受控替身」——Riverpod 內建的 `overrideWith` 一行就是官方解。389 行的 Mock 架構等於是在框架旁邊蓋了一座平行的依賴注入系統，每個新測試都得學它、每次框架升級它都可能斷。

寫測試工具前的第一個檢查點就是這條：**先問「這個框架 / 生態的標準做法是什麼」、再問「標準做法哪裡不夠」**。答不出第二題，自建工具的每一行都是純負債——它不是產品碼、卻要跟產品碼一樣被維護。

## 形態二：解決不存在的問題

388 行的多語系測試 helper 是精緻度的巔峰：Mutex 狀態鎖、記憶體洩漏防護機制、三類版面溢位檢測（RenderFlex、文字截斷、螢幕邊界）。每個機能單獨看都「很完備」——但當時的 Widget 測試需求是「讓測試能編譯、能跑」，多語系切換測試根本還不在任何 use case 裡。重構記錄的判語：「解決一個不存在的問題」。

這個形態跟[異步查詢系統的第一輪膨脹](/work-log/flutter_async_query_overdesign_oscillation/)同構——設計期用「系統該有的完備性」取代「操作需要的能力」。測試工具的完備性想像還更容易失控，因為它不受產品需求審查：沒有 PM 會問「為什麼測試 helper 需要 Mutex」。

## 形態三：mock 了不需要 mock 的東西、放在不該放的地方

兩個架構層級的錯：

**`MockBook` 取代真 domain entity。** mock 的正當對象是有副作用、慢、或不可控的依賴（網路、資料庫、時間）；`Book` 是純資料物件、建構它比 mock 它便宜——真 entity 直接用就好。mock 純物件的代價是雙重維護：entity 加欄位、MockBook 也要加，兩者漂移時測試守的是一個不存在的形狀。

**mock 放在 `lib/` 而不是 `test/`。** 測試碼進了生產依賴圖——而且這不是手滑，Phase 1 設計文件把 `test/ → lib/mocks/ → lib/core/` 畫成正式的單向依賴規範。方向本身「乾淨」，但前提就錯了：`lib/` 的語意是「會被打包進 App 的程式碼」，mock 不屬於那裡。

## 精緻的設計文件不是價值證明

這個 case 最值得記的一點：被刪掉的系統有 783 行設計文件、有架構圖、有依賴方向規範、有驗收條件——**整個設計流程認真地規劃了一個不需要存在的東西**。精緻度讓它更難殺：看起來像紮實的工程產出，審查者要先推翻「這麼認真的東西應該有價值」的直覺才下得了手。

同專案的另一個記錄（同步 domain 架構評分 A- 但不能編譯）是同一課的另一面：**評價「做得好不好」之前，先評價「該不該做」**。Phase 4 重構記錄把這個順序寫成了方法論建議——「優先考慮刪除：先問『這個真的需要嗎？』再問『如何改善？』」。

## 判讀徵兆

- mock 類別 mock 的是純資料物件（entity / value object）——真物件更便宜、直接用
- 測試 helper 出現 framework 級機能（並發鎖、洩漏防護、自製 logger）——問是哪個測試需求逼出來的、答不出來就是完備性想像
- `lib/` 底下出現 `mocks/` 或 `test` 字樣的目錄——測試碼在生產依賴圖裡
- helper 的行數超過用它的測試——工具比問題大
- 「用這套工具寫測試」需要先讀文件——標準模式的優勢正是新人零學習成本

## 相關閱讀

- 同機制的產品側版本：[異步查詢系統的過度設計震盪](/work-log/flutter_async_query_overdesign_oscillation/)——設計期完備性想像的兩個現場
- mock 該放哪、多少才夠：[192 個測試全過、實機全壞](/work-log/testing_three_layer_strategy/)——那篇談 mock 過多遮蔽真實、本文談 mock 系統本身過重，同一個「mock 是手段不是資產」的兩面
- 原則層：[#77「現在不決定」是合法選項](/report/decide-later-as-valid-option/)——多語系測試工具的正確處置是等需求出現、不是先蓋起來放
