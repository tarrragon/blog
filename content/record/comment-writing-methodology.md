---
title: "程式碼註解撰寫方法論"
date: 2026-03-04
draft: false
description: "定義程式碼註解的本質：需求保護器而非程式解釋器，建立維護者導向的註解撰寫標準，涵蓋事件驅動架構與 Widget 獨立性註解規範"
tags: ["方法論", "程式設計", "軟體架構", "註解規範", "需求管理","AI協作心得"]
categories: ["軟體工程", "開發方法論"]
keywords: ["程式碼註解", "需求保護", "維護指引", "設計意圖", "業務邏輯", "事件驅動", "Flutter Widget"]
---

接手一段六個月前的程式碼，看到 `processBook()`，旁邊的註解寫著「處理書籍相關邏輯」。完全沒有幫助——只是重述函式名稱，沒說背後有什麼業務限制、改了會影響哪裡、當初為什麼這樣設計。

這讓我們重新思考：註解到底是為了誰而寫的？

<!--more-->

## 註解的本質

程式碼註解不是程式的解釋員。它的存在是為了保護原始設計意圖，提供無法從程式碼本身推斷出來的訊息。

**不應該做的**：解釋程式在做什麼（好的程式碼應該自己說話）、描述函式使用方法（那是文件的工作）、充當 TODO 清單。

**應該做的**：作為需求保護器，防止維護時破壞原始需求；記錄設計意圖，保存業務邏輯的考量；提供維護指引，明確標示約束條件；建立程式碼與需求規格的連結。

## 第一原則：程式碼本身必須自說明

如果程式碼需要靠註解才能被理解，首先應該改善的是程式碼，不是補更多解釋。

`process(Book book)` 需要一行「檢查書籍狀態並更新進度」的註解，但如果直接命名為 `updateReadingProgressWhenStatusChanges(Book book)`，解釋性的註解就不需要了。此時真正值得寫下來的，是這個函式背後的業務需求和約束條件：

```dart
void updateReadingProgressWhenStatusChanges(Book book) {
  // 需求：UC-005 閱讀進度管理
  // 當使用者標記書籍為「閱讀中」時，自動設定進度為 0%
  // 當使用者標記為「已完成」時，自動設定進度為 100%
  // 約束：不可覆蓋使用者手動設定的進度值
}
```

變數也一樣：`final data = book.getInfo()` 毫無意義，`final enrichedBookMetadata = book.getMetadataWithEnrichment()` 就完全自說明了。

驗證標準：移除所有註解後，如果仍能理解程式邏輯，程式碼達標。需要猜測變數含義就重新命名，無法確定函式目的就拆分函式。

## 第二原則：註解記錄的是需求脈絡

程式碼自說明，不代表不需要註解——需要的是不同種類的註解。

每個業務邏輯函式都應該追溯到明確的需求來源：

```dart
/// 需求：UC-003.2 書籍分類管理
/// 使用者可以為書籍設定多個標籤進行分類
/// 約束：標籤名稱不可重複，最多 10 個標籤
void addTagToBook(BookId bookId, Tag tag) {
  // 實作...
}
```

這條註解告訴維護者：這個函式的存在依據是 UC-003.2，不可以被打破的規則是標籤不可重複且最多十個。

書籍狀態的轉換順序是業務規則，不是技術細節，也應該記錄：

```dart
/// 需求：BR-001 書籍狀態轉換規則
/// 書籍狀態變更順序：初始 → 資訊補充中 → 資訊補充完成 → 可用
/// 約束：不可跳過中間狀態，不可逆向轉換
/// 例外：管理員可以直接設定為任何狀態
BookStatus transitionBookStatus(BookStatus current, BookStatus target) {
  // 實作...
}
```

設計決策也要記錄。為什麼選懶載入加分頁？因為有效能需求：

```dart
/// 需求：NFR-002 效能需求
/// 書庫載入時間不可超過 2 秒
/// 設計決策：採用懶載入 + 分頁載入策略
/// 影響：首次載入只載入 20 本書，滾動時動態載入
List<Book> loadLibraryWithPagination(int page, int pageSize) {
  // 實作...
}
```

一個完整的業務邏輯註解必須包含：需求來源（UC 或 BR 編號）、業務描述、約束條件、以及修改此邏輯會影響哪些功能。

## 第三原則：維護指引必須明確

好的維護指引讓維護者修改程式碼之前就知道會影響哪裡。不應該隨意修改的邏輯，要主動發出警告：

```dart
/// 需求：UC-001.3 書籍唯一性檢查
/// 同一書庫內不可有相同 ISBN 的書籍
/// 警告：此邏輯關聯到資料一致性，修改前必須檢查：
/// - 書籍匯入流程 (ImportBookService)
/// - 書籍合併功能 (BookMergeService)
/// - 資料庫索引設計 (book_isbn_unique_index)
bool isDuplicateBook(String isbn, LibraryId libraryId) {
  // 實作...
}
```

預期會被擴展的邏輯，要提供擴展指引：

```dart
/// 需求：UC-004 書籍搜尋功能
/// 支援書名、作者、標籤的模糊搜尋
/// 擴展指引：新增搜尋條件時必須：
/// 1. 更新 SearchCriteria 值物件
/// 2. 修改索引策略以維持效能
/// 3. 更新搜尋測試案例涵蓋新條件
List<Book> searchBooks(SearchCriteria criteria) {
  // 實作...
}
```

模組間的耦合關係也需要標示：

```dart
/// 需求：UC-006 借閱管理
/// 計算書籍歸還到期日
/// 相依性警告：此邏輯與以下模組緊密耦合
/// - LoanReminderService（提醒計算）
/// - OverdueBookDetector（逾期偵測）
/// - LibraryStatistics（統計計算）
/// 修改歸還期限計算會影響上述所有模組
DateTime calculateDueDate(DateTime loanDate, int loanPeriodDays) {
  // 實作...
}
```

## 第四原則：結構一致的標準格式

把上面的原則整合成一個標準格式：

```dart
/// 需求：[需求編號] [簡短描述]
/// [詳細業務描述，說明使用者需求]
/// 約束：[限制條件和邊界規則]
/// [維護指引：修改須知、相依性警告、擴展要求]
[函式簽名]
```

複雜業務邏輯的範例：

```dart
/// 需求：UC-007.1 閱讀統計分析
/// 計算使用者的閱讀速度和預估剩餘時間
/// 約束：只統計狀態為「閱讀中」的書籍，頁數必須大於 0
/// 計算邏輯：(已讀頁數 / 實際閱讀時間) = 閱讀速度（頁/小時）
/// 維護指引：修改計算公式會影響：
/// - 閱讀目標設定功能
/// - 個人化推薦系統
/// - 學習分析報表
/// 相依模組：ReadingProgressTracker, BookMetadata, UserPreferences
ReadingSpeed calculateReadingSpeed(
  ReadingProgress progress,
  BookMetadata metadata,
  Duration actualReadingTime
) {
  // 實作...
}
```

## 禁止的註解模式

最常見的錯誤是重述程式碼行為。「設定書籍標題」對應的程式碼是 `book.setTitle(newTitle)`，完全多餘。「使用 Map 快速查找避免 O(n) 複雜度」也一樣，有經驗的開發者看程式碼就知道。

UI 層特別容易出現這類問題。以 Widget 選取回饋設計為例，錯誤做法是列出技術細節：

```dart
/// ❌ 錯誤：重複描述程式碼內容
/// BookListItem - 書庫列表項目 Widget
///
/// 視覺設計：
/// - 陰影刻痕變化（凸起→凹陷）
/// - AnimatedContainer 200ms 過渡動畫
///
/// 觸覺回饋：
/// - 選擇時：HapticFeedback.selectionClick()
/// - 取消選擇：HapticFeedback.lightImpact()
class BookListItem extends StatelessWidget {
  // ...
}
```

這些看程式碼就能看到。真正有價值的是背後的決策依據：

```dart
/// 【需求來源】UC-05: 雙模式書庫展示切換 - 書籍選擇互動
/// 【規格文件】docs/ui_design_specification.md#book-selection-feedback
/// 【設計決策】採用方案C-1基礎版 - 極簡視覺回饋設計
/// 【為什麼選擇陰影刻痕變化】
/// - 不影響文字可讀性：避免背景色干擾閱讀體驗
/// - 符合無障礙設計：不依賴顏色作為唯一視覺提示
/// 【為什麼選擇差異化觸覺回饋】
/// - 選中 vs 取消必須有不同的觸覺回饋類型
/// - selectionClick 提供明確的「確認」感受
/// - lightImpact 提供輕微的「狀態變更」提示
/// 【修改約束】
/// - 觸覺回饋時機不可調換（與使用者預期一致）
/// - 陰影變化動畫時長需保持 < 250ms（符合 Material Design 規範）
/// 【維護警告】
/// - 此 Widget 被 3 個書庫頁面使用
/// - 修改視覺回饋會影響整體使用者體驗一致性
class BookListItem extends StatelessWidget {
  // ...
}
```

模糊描述也不可取——「處理書籍相關邏輯」等於沒有描述。過時的 TODO 必須清除，否則會讓人以為某個功能還沒實作。

## 第五原則：事件驅動架構的特殊需求

在 UseCase 或 Domain 層，函式名稱包含 `handle*`、`on*`、`process*`、`emit*`、`dispatch*`，或回傳類型為 `Future<>`、`Stream<>` 的函式，都需要標示其在事件流中的角色：

```dart
/// 【需求來源】UC-01: Chrome Extension 匯入書籍資料
/// 【規格文件】docs/app-requirements-spec.md#chrome-extension-import
/// 【設計方案】方案C-1基礎版 (v0.12.7 Phase 1)
/// 【工作日誌】docs/work-logs/v0.12.7.md - 方案研究和設計決策
/// 【事件類型】BookAdded 事件處理
/// 【修改約束】修改時需確保事件流完整性，避免影響上游訂閱者
/// 【維護警告】此函式被 3 個 UseCase 依賴，修改前需檢查影響範圍
Future<void> handleBookAdded(BookAddedEvent event) async {
  // 實作...
}
```

以 `_` 開頭的私有輔助函式（`_isValid*`、`_format*`、`_convert*`、`_validate*` 等）不包含業務邏輯，豁免詳細業務註解。

## 第六原則：Widget 獨立性的明確標示

非私有命名（不以 `_` 開頭）、繼承自 `StatefulWidget`、`ConsumerWidget`、`StreamBuilder` 或 `FutureBuilder` 的 Widget，具備獨立狀態，需要明確記錄需求來源和修改約束：

```dart
/// 【需求來源】UC-05: 雙模式書庫展示切換
/// 【規格文件】docs/ui_design_specification.md#book-list-item
/// 【設計方案】方案C-1基礎版 - 陰影刻痕變化 + 觸覺回饋
/// 【工作日誌】docs/work-logs/v0.12.7.md - UI 互動設計
/// 【Widget 類型】獨立狀態管理 Widget
/// 【修改約束】此 Widget 具備獨立狀態，下層刷新不觸發上層重建
/// 【維護警告】修改前需確認子 Widget 依賴關係
class BookListItem extends StatefulWidget {
  // 實作...
}
```

私有的 `StatelessWidget`（如 `_BookTitleText`、`_ProgressBar`）和純展示型組件，只展示上層傳遞的資料，豁免詳細業務邏輯註解。

## 第七原則：工作日誌與規格文件的追溯鏈

設計決策涉及複雜研究或多方案比較時，幾行註解無法承載所有背景，需要建立追溯鏈：

```dart
/// 【工作日誌】docs/work-logs/v0.12.7.md - 方案C-1基礎版設計
```

維護者能循著這條鏈找到完整的決策記錄。業務邏輯也可以指向規格文件章節：

```dart
/// 【規格文件】docs/app-requirements-spec.md#section-name
/// 【規格文件】docs/event-driven-architecture-design.md#event-flow
```

這讓程式碼成為整個需求、設計、實作文件體系的一部分，而不是孤立的存在。

## 品質驗證：兩個測試

**可執行性測試**：維護者看到這條註解後，能理解業務需求嗎？修改約束明確嗎？需求來源可以追溯嗎？

**必要性測試**：移除這條註解後，是否會遺失業務脈絡？如果移除後仍能理解程式邏輯，就要檢查它是否只是在重述程式碼。如果內容過時，直接刪除，不要保留會誤導維護者的假資訊。

## 結論

好的程式碼是自說明的，但好的業務系統還需要一個跨越時間的溝通機制，讓六個月後接手的人能理解每個設計決策背後的原因，不會在不了解背景的情況下破壞原始設計。

這就是我們對程式碼註解的重新定位——不是程式碼的解釋員，而是需求的守護者。

這是需求保護機制，不是文書工作。
