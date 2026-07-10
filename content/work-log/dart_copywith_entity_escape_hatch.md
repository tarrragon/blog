---
title: "copyWith 是逃生口，不是設計 — 從一個測試 bug 追到 entity 稽核軌跡的洞"
date: 2026-07-10
draft: false
description: "copyWith 對純資料載體是正確工具，對有領域方法的 entity 是繞過不變式的逃生口。從一個 3 字元 ID 觸發的例外，追出同族語意錯誤、被繞過的領域方法、以及從未被強制的註解約束。"
tags: ["dart", "flutter", "copywith", "ddd", "entity", "domain-model", "retrospective"]
---

> **觸發場景**：修一個效能基準測試的 `InvalidBookIdException`，追根因時發現它是同族語意錯誤的第二起
> **疑問來源**：「copyWith 是方便的做法，但通常不是最好的設計」——這個直覺是否成立？
> **整理目的**：把「copyWith 什麼時候是對的工具、什麼時候是逃生口」的判斷邊界記下來，連同這個專案實際踩的三個坑
> **本文邊界**：這是一篇 work-log，回溯一次具體專案的設計檢視；它不主張消滅 copyWith——結論恰恰相反，問題從來不在 copyWith 本身

---

## 事件起點：一個 3 字元的 ID

書籍管理 App 專案的效能基準測試炸了一個例外：

```text
InvalidBookIdException: Book ID must be at least 5 characters long
```

炸點在測試的 Arrange 段：

```dart
final book = Book.createForTest(
  id: 'perf-bm-001-${i.toString().padLeft(4, '0')}',
  title: '效能基準測試書籍 $i',
  author: '作者 $i',
).copyWith(bookTags: [
  ...Book.createForTest(id: 'tmp').bookTags,   // <- 這行
  BookTag.primary(categoryId: TagCategoryIds.custom, value: '科幻'),
  // ...
]);
```

`'tmp'` 只有 3 個字元，`BookId` 的 value object 要求至少 5 個，於是炸了。

最小修法顯而易見：把 `'tmp'` 改成 `'tmp-12345'`。但這個修法是錯的。

## 長度是症狀，語意才是病

看那行的意圖：它想要「保留 `createForTest` 產生的預設 bookTags，再追加三個自訂 tag」。但它取預設值的方式，是**建一個立刻丟棄的物件，只為了拿它的一個欄位**。

正確的寫法是取自己的：

```dart
final baseBook = Book.createForTest(id: 'perf-bm-001-...', ...);
final book = baseBook.copyWith(bookTags: [
  ...baseBook.bookTags,   // 取自己的預設值
  BookTag.primary(...),
]);
```

把 `'tmp'` 改長只會讓例外消失，語意錯誤原封不動地留著。而且這不是孤例——同一個專案的測試資料產生器幾天前才修過一模一樣的寫法：

```dart
// 修復前：用一個全新預設書籍的 bookTags，
// 丟棄呼叫端指定的 author / isbn
copyWith(bookTags: [...Book.createForTest(id: bookId).bookTags, ...])
```

同一種錯誤在兩個檔案各出現一次。這時候該問的就不是「怎麼修」，而是「**為什麼這種寫法會自然長出來**」。

## 追問：copyWith 通常不是最好的設計？

這個直覺方向是對的，但不加限定會誤傷。精確的說法是：

**問題不在 copyWith，在於「public copyWith 掛在 entity 上」。**

copyWith 對純資料載體是正確工具——DTO、API model、UI state、小的 value object。這些東西沒有領域不變式，它們就是一袋欄位，逐欄位覆寫語意清晰、沒有代價。Dart 生態也是這樣用它的：freezed 幫每個 model 自動生成 copyWith，這在 data class 的世界完全合理。

但這個專案的 `Book` 不是一袋欄位。它是 entity，帶著一組**有意圖的狀態轉換方法**：

```dart
Book startEnrichment()     // 開始豐富化
Book completeEnrichment()  // 完成豐富化
Book markAsAvailable()     // 標記可用
Book setImportanceLevel(int level)
```

每個方法都會往 `modificationHistory` 追加一筆稽核紀錄——這是領域模型的核心價值：狀態怎麼變的，有跡可循。

然後，`Book` 同時有一個 public 的、18 個參數的 `copyWith`，而且參數列裡**包含 `status` 和 `modificationHistory`**。

## 實證一：領域方法被繞過，稽核軌跡有洞

有了 public copyWith，領域方法就從「唯一路徑」降級成「建議路徑」。grep 一下就找到繞過的實例：

```dart
// 書籍工廠層
).copyWith(status: BookStatus.available).setReadingStatus(readingStatus);
// ...
).copyWith(status: BookStatus.enriched);
```

這兩處直接改 `status`，繞過了 `markAsAvailable()` 和 `completeEnrichment()`。後果：這些狀態轉換**沒有進入 modificationHistory**。稽核軌跡有洞，而且是靜默的——沒有任何錯誤、警告或測試失敗會告訴你。

## 實證二：註解宣稱的約束，從未被強制

`completeEnrichment()` 的文件註解寫著：

```dart
/// 約束：只能從enriching狀態轉換，確保狀態流程正確
Book completeEnrichment() {
  final newHistory = _modificationHistory.addChange(...);
  return copyWith(status: BookStatus.enriched, modificationHistory: newHistory);
}
```

實作裡沒有任何 `if`、`assert` 或 `throw`。grep 計數是零。

這比「沒有約束」更糟——註解讓讀者**以為**有防護。而且就算方法內部加了檢查，`copyWith(status: ...)` 還是繞得過去。約束要成立，逃生口就得先關上。

## 實證三：測試作者自己也分不清兩條路徑

同專案更早的測試修復記錄裡有一筆直接的證言。一個測試用 `book.copyWith(readingStatus: ReadingStatus.reading)` 改狀態、然後期待 `modificationHistory` 出現兩條變更紀錄——實際只有一條、測試失敗。修法是改呼叫業務方法 `setReadingStatus()`、期待一條紀錄。

這個失敗的測試值得記，因為它證明混淆不是理論風險：**連寫測試的人都把 copyWith 當成了業務入口**、以為它會留稽核痕跡。兩條路徑（工具方法不記錄、業務方法記錄）並存在同一個 public 介面上，每個使用者都要自己記得哪條是哪條——而「要記得」的規則遲早有人忘。

## 逃生口機制：為什麼那種寫法會自然長出來

回到最初的測試 bug。為什麼有人會寫 `Book.createForTest(id: 'tmp').bookTags`？

因為 `Book.createForTest` 只接受 `id` / `title` / `author` / `isbn` 四個參數，**不接受 `bookTags`**。測試想表達「預設 tags 再加三個自訂 tag」，工廠給不了這個表達力，於是 copyWith 成了唯一的出路——而在用 copyWith 拼裝的當下，順手建個臨時物件撈預設值，就是最短路徑。

這就是 copyWith 作為逃生口的危險之處：**它總是有辦法讓你把物件拼出來，所以你永遠不會被迫去修那個表達力不足的工廠。** 建構路徑的缺陷被逃生口吸收掉，然後以語意錯誤的形式在別處復發——這個專案復發了兩次。

## 生態推力：預設路徑塑造習慣

還有一層值得說：Dart 生態在推你往 copyWith 走。freezed 自動生成它、教學範例到處用它、IDE 補全第一個跳出來的就是它。它是**預設路徑**。

這和之前寫過的〈工具的預設行為決定使用者習慣〉是同一件事：規範說「狀態轉換請走領域方法」，工具預設給你一個全欄位的 copyWith——**規範和預設打架時，預設會贏**。差別只在這次預設值站在錯的一邊。

## 修法方向：分層收窄，不是消滅

這個專案的 copyWith 呼叫點：`lib/` 301 處、`test/` 115 處。消滅它不現實，也不正確——大部分呼叫點在 value object 和 UI state 上，那裡它是對的工具。

收窄的方向分三層：

| 對象                             | 處置                                                                                                                            |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| value object / DTO / UI state    | 保留 copyWith，這裡它是正確工具                                                                                                 |
| 有領域方法的 entity（如 `Book`） | copyWith 改 private 僅供領域方法內部使用；或至少從參數列移除 `status`、`modificationHistory` 這類「必須經由領域方法變更」的欄位 |
| 測試建構                         | 讓 `createForTest` 接受 `bookTags`，消除用 copyWith 拼裝的動機——修工廠的表達力，不是修每一個拼裝點                              |

判斷準則濃縮成一句：**這個型別有沒有「不允許任意組合的欄位」？** 有，copyWith 就不該讓那些欄位 public 可寫；沒有，copyWith 就是正當的便利工具。

## 附註：即使在正當場景、copyWith 也有一個表達力缺口

value object 跟 UI state 上的 copyWith 是正確工具，但手寫時有一個 Dart 型別系統的缺口：`String? isbn` 這種 nullable 參數只有兩態（有值 / null），而 copyWith 的語意需要三態——「不改這欄」「改成某值」「清空成 null」。前兩態沒問題，第三態表達不出來：`copyWith(isbn: null)` 跟「沒傳 isbn」在函式內看起來一模一樣。

通用的補償手法是哨兵物件，兩個不同專案各自長出了同一份程式碼：

```dart
static const _sentinel = Object();

State copyWith({Object? member = _sentinel}) {
  return State(
    member: member == _sentinel ? this.member : member as Member?,
  );
}
```

有了哨兵，「登出會員（明確設 null）」這類操作才能經由 copyWith 表達。freezed 生成的 copyWith 內部就是用同樣的哨兵技巧處理這件事——手寫 immutable state 時這是要自己補的部分，漏掉的症狀是「清空欄位的操作靜默變成保留原值」。

## 收束：三個坑的共同結構

這次追出來的三個坑——語意錯誤的測試拼裝、被繞過的領域方法、從未強制的註解約束——共同結構是同一個：

**設計意圖只寫在文件層（註解、命名、慣例），沒有落在型別層或執行層。**

「請走領域方法」是慣例，copyWith 不擋你；「只能從 enriching 轉換」是註解，實作不查你；「測試該用工廠」是期望，工廠沒能力你就繞。每一個「請、應該、建議」都是一個沒關上的逃生口，而逃生口的使用者不是壞人——他們只是走了阻力最小的路。

要讓意圖成立，就得讓違反意圖的路徑**走不通**，而不是寫文件請大家不要走。

這次追出來的兩個可重用原則各自抽成 report 卡：意圖的強制層次在 [#222 約束要讓違反路徑走不通](/report/design-intent-needs-enforcement-layer/)、缺陷的轉移機制在 [#223 逃生口吸收建構路徑的缺陷](/report/escape-hatch-absorbs-construction-gap/)。
