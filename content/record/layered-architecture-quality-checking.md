---
title: "架構合規交給機制，不交給自律"
slug: "layered-architecture-quality-checking"
date: 2026-03-04
draft: false
description: "分層架構在文件上完整、而 codebase 三個月後依賴方向已經走樣時，用來把架構規則轉成 commit 前就會擋下來的自動檢查"
tags: ["Clean Architecture", "品質檢查", "分層架構", "依賴方向", "架構合規"]
---

在 Flutter 專案裡導入 Clean Architecture 並不難，難的是讓每一次 commit 都確實遵守它。架構設計文件寫得完整、而三個月後打開 codebase 出現 Widget 裡藏著業務規則、Controller 自己做驗證、UseCase 直接依賴具體資料庫實作時，缺的不是文件，是讓「做錯事」變困難的機制。

<!--more-->

## 架構腐化的來源是成本差

Clean Architecture 的核心是依賴方向：外層可以依賴內層，內層不依賴外層。這個原則陳述起來簡單，而每一次違規的當下都有成本上的理由。一個業務驗證邏輯，放在 Widget 裡只要三行；搬到 Domain 層要新增 Entity 方法、更新 UseCase、再補上測試。

時間壓力下，成本低的那條路勝出。

腐化因此是漸進的：第一次違規很小，第二次引用第一次當前例，到了第六次，層級的邊界已經無法辨識。

方向是把架構規則轉化成可以自動執行的檢查——判定不依賴當下的自制力，依賴一個會擋下 commit 的程式。

## 用檔案路徑判斷層級歸屬

檔案路徑是層級的明確宣告：一個檔案放在什麼目錄，就代表它屬於哪一層。

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

這讓層級歸屬可以用字串比對判斷：這個 PR 動了哪些層的檔案。一張 Ticket 聲稱只修改展示層，而 diff 裡出現 `lib/domain/` 的檔案，這個落差就是需要解釋的訊號。

測試目錄採用相同的對應結構：

```text
test/
├── ui/           // 對應展示層修改
├── application/  // 對應應用行為層修改
├── usecases/     // 對應 UseCase 層修改
└── domain/       // 對應 Domain 層修改
```

修改了某個層，對應的測試目錄裡就要有覆蓋。「測試覆蓋率」從一個抽象數字變成具體的結構性要求。

## 三種可以機械辨識的違規模式

架構違規落在三種模式上，共同點是它們都能從檔案位置與型別依賴看出來。

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

「什麼樣的書算新書」是業務邏輯，定義在 Domain 層。Widget 做的是把資料渲染成畫面。

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

「ISBN 必須為 13 碼」是業務規則，住在 `Book` Entity 或 Value Object 裡。Controller 的角色是協調。

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

依賴介面讓 UseCase 在測試時注入 Mock、生產環境注入真實實作，兩者互換。

## 把檢查機制自動化

辨識出這三種模式之後，它們可以寫進工具。

### Pre-commit Hook

```bash
#!/bin/bash
./scripts/check_single_layer_modification.sh || exit 1
flutter test --coverage || exit 1
```

`check_single_layer_modification.sh` 分析 commit 的 diff，確認被修改的檔案是否都屬於同一個架構層。一個本來只應動展示層的 commit，若同時修改了 Domain 層的檔案，腳本退出並阻止 commit。

### CI/CD 整合

Pre-commit Hook 可以被 `--no-verify` 繞過，CI/CD 不會：

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

## 自動化擋不住的那一半

工具處理可以被程式判斷的規則，剩下的部分在 commit 前手動過一遍：

- 這次修改的檔案，是否都屬於同一個架構層？
- import 方向是否正確——只有外層依賴內層？
- 測試檔案路徑和被測試程式碼是否在對應的層級目錄？
- 有沒有 Widget 直接做業務計算、Controller 直接做驗證？

四個問題三十秒可以過完，而它們攔下的是路徑與型別看不出來的那一類：命名對、位置對，職責錯放。

## 這套機制換到的是什麼

架構層面的問題在進入 review 之前就被攔截時，review 的內容會集中到邏輯正確性與設計決策上——「這段邏輯不應該放在 Widget 裡」這類判斷不必每次重講一遍。

對後來加入這個 codebase 的人也一樣：不需要先把架構文件讀熟才能開始寫，走錯方向時工具會給出位置明確的反饋。

架構的生命力在於它能不能在日常開發壓力下被維護下去——而壓力不會消失，能改的是違規的成本。

Ticket 層級怎麼切才不會一張跨四層，走 [層級隔離](../layered-ticket-methodology/)；Clean Architecture 五層在這個專案怎麼定義，走 [Clean Architecture 實作方法論](../clean-architecture-implementation-methodology/)。
