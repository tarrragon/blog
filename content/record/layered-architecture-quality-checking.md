---
title: "層級架構品質檢查機制 - Clean Architecture 合規性驗證"
date: 2026-03-04
draft: false
description: "自動化檢查分層架構的依賴方向、命名規範和職責分離，確保 Clean Architecture 原則的持續遵守"
tags: ["Clean Architecture", "品質檢查", "分層架構", "依賴方向", "架構合規"]
---

在 Flutter 專案裡導入 Clean Architecture 並不難，難的是讓整個團隊在每一次 commit 都確實遵守它。我們曾有過這樣的經驗：架構設計文件寫得很完整，但三個月後打開 codebase，Widget 裡藏著業務規則、Controller 開始自己做驗證、UseCase 直接依賴了具體的資料庫實作。

問題不在於大家不懂架構，而在於沒有機制讓「做錯事」變得困難。

<!--more-->

## 為什麼架構會悄悄腐化

Clean Architecture 的核心是依賴方向：外層可以依賴內層，但內層絕對不能依賴外層。這個原則說起來簡單，但「快速解決問題」的衝動很容易讓人走捷徑。一個業務驗證邏輯，放在 Widget 裡只要三行；把它搬到正確的 Domain 層，可能需要新增 Entity 方法、更新 UseCase、再補上測試。

在時間壓力下，捷徑獲勝了。

更麻煩的是，這種腐化是漸進的。第一次違規很小；第二次引用了第一次的前例；到了第六次，層級的邊界已經模糊得看不清楚了。

解法是：不依賴自律，改依賴機制。把架構規則轉化為可以自動執行的檢查。

## 用檔案路徑判斷層級歸屬

我們採用的策略是**用檔案路徑作為層級的明確宣告**。一個檔案放在什麼目錄，就代表它屬於哪一層：

```text
lib/
├── ui/                    // 展示層（Layer 1）
├── application/           // 應用行為層（Layer 2）
├── usecases/              // UseCase 層（Layer 3）
├── domain/
│   ├── events/            // Domain 事件層（Layer 4）
│   ├── interfaces/        // 介面定義層（Layer 4）
│   ├── entities/          // Domain 實作層（Layer 5）
│   ├── value_objects/     // 值物件（Layer 5）
│   └── services/          // Domain 服務（Layer 5）
└── infrastructure/        // 基礎設施層
```

這讓我們可以用簡單的字串比對判斷：這個 PR 動了哪些層的檔案？一個 Ticket 聲稱只修改展示層，但 diff 裡出現了 `lib/domain/` 的檔案，那就是需要解釋的信號。

測試目錄也採用相同的對應結構：

```text
test/
├── ui/           // 對應展示層修改
├── application/  // 對應應用行為層修改
├── usecases/     // 對應 UseCase 層修改
└── domain/       // 對應 Domain 層修改
```

修改了某個層，對應的測試目錄裡就必須有覆蓋。「測試覆蓋率」從一個抽象數字，變成了具體的結構性要求。

## 三種最常見的違規模式

追蹤了幾十個架構違規案例之後，幾乎都落在以下三種模式。

### 展示層包含業務邏輯

Widget 直接呼叫過濾、排序、計算這類業務操作：

```dart
// 違規：Widget 自己做了業務邏輯
class BookListWidget extends StatelessWidget {
  Widget build(BuildContext context) {
    final books = _filterNewBooks(_getAllBooks());
    return ListView.builder(...);
  }
}

// 正確：Widget 只負責把 controller 的狀態渲染出來
class BookListWidget extends StatelessWidget {
  final BookListController controller;
  Widget build(BuildContext context) {
    return ListView.builder(items: controller.filteredBooks);
  }
}
```

「什麼樣的書算新書」是業務邏輯，應該在 Domain 層定義。Widget 只做一件事：把資料渲染成畫面。

### Controller 包含業務規則

```dart
// 違規：Controller 自己在做 ISBN 驗證
class BookController {
  Future<void> addBook(Book book) async {
    if (book.isbn.length != 13) {
      throw ValidationException('ISBN 必須為 13 碼');
    }
    await bookRepository.save(book);
  }
}

// 正確：Controller 只負責呼叫 UseCase
class BookController {
  final AddBookUseCase addBookUseCase;
  Future<void> addBook(Book book) async {
    await addBookUseCase.execute(book);
  }
}
```

「ISBN 必須為 13 碼」是業務規則，應該活在 `Book` Entity 或 Value Object 裡。Controller 的角色是協調，不是決策。

### UseCase 依賴具體實作

```dart
// 違規：依賴具體的 SQLite 實作
class SearchBookUseCase {
  final SqliteBookRepository repository;
}

// 正確：依賴抽象介面
class SearchBookUseCase {
  final IBookRepository repository;
}
```

依賴介面讓 UseCase 在測試時注入 Mock，生產環境注入真實實作，兩者互換自如。

## 把檢查機制自動化

辨識出違規模式之後，我們做的第一件事不是寫文件要求大家注意，而是把檢查寫進工具裡。

### Pre-commit Hook

```bash
#!/bin/bash
./scripts/check_single_layer_modification.sh || exit 1
flutter test --coverage || exit 1
```

`check_single_layer_modification.sh` 分析 commit 的 diff，確認被修改的檔案是否都屬於同一個架構層。一個本來只應動展示層的 commit，如果同時修改了 Domain 層的檔案，腳本就會退出並阻止 commit。

### CI/CD 整合

Pre-commit Hook 可以被繞過，但 CI/CD 不會：

```yaml
name: PR Architecture Check
on: [pull_request]
jobs:
  architecture_check:
    runs-on: ubuntu-latest
    steps:
      - name: 檢查單層修改原則
        run: ./scripts/check_single_layer_in_pr.sh
      - name: 執行測試並確認覆蓋率
        run: flutter test --coverage
```

架構合規性成為 PR 合併的硬性前置條件。

## 每次 commit 前的自我檢查

自動化工具處理可以被程式判斷的規則，剩下的需要開發者自己過一遍：

- 這次修改的檔案，是否都屬於同一個架構層？
- import 方向是否正確——只有外層依賴內層？
- 測試檔案路徑和被測試程式碼是否在對應的層級目錄？
- 有沒有 Widget 直接做業務計算、Controller 直接做驗證？

三十秒可以過完，但幾乎每次都能在 commit 前抓住一兩個值得重新考慮的決定。

## 機制比自律更可靠

導入這套機制之後，code review 上花的精力少了很多——大多數架構層面的問題在進入 review 之前就已經被攔截。reviewer 可以把注意力放在邏輯正確性和設計決策上，不用反覆提醒「這段邏輯不應該放在 Widget 裡」。

對新加入的開發者也很友善：不需要先把架構文件背熟才能開始開發，工具會在走錯方向時給出明確的反饋。

架構的生命力不在於設計之初有多完美，而在於它能不能在日常開發壓力下被維護下去。
