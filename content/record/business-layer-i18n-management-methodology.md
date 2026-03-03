---
title: "分層 i18n 管理方法論 - 業務層國際化的正確實踐"
date: 2026-03-04
draft: false
description: "定義 Domain、ViewModel、UI 各層的 i18n 責任分工，禁止硬編碼使用者訊息，確保多語言支援的正確架構"
tags: ["i18n", "國際化", "分層架構", "ViewModel", "訊息管理"]
---

在開發書庫管理 Flutter 應用的過程中，我們踩進了一個多語言專案幾乎必經的坑：i18n 訊息出現在不該出現的地方。Domain 層的 repository 開始直接拋出中文錯誤訊息，ViewModel 裡散落著硬編碼字串，UI 層還要自己判斷 errorCode 決定顯示什麼文字。每增加一種語言，就要在三個地方同時動手。

<!--more-->

## 問題的根源

幾個典型的失控情境：

Domain 層的 Service 直接回傳中文字串作為錯誤訊息，要支援英文時就必須深入業務邏輯層去改。ViewModel 裡出現 `errorMessage: '找不到書籍'` 這樣的程式碼，看起來無害，但需要國際化時根本不知道有多少個地方要改。UI 層開始承擔它不應該承擔的邏輯，自行根據 errorCode 決定顯示什麼文字。

問題的共同根源：沒有清楚定義每一層對 i18n 的責任邊界。

## 核心原則

一個簡單的原則統治一切：**Domain 層不知道 UI 呈現方式，UI 層不承擔訊息決策邏輯**。

具體化成三條規則：Domain 層使用技術語言（錯誤碼），ViewModel 層負責轉換為使用者語言，所有使用者可見的字串禁止硬編碼。

## Domain 層：回傳錯誤碼，不回傳訊息

Domain 層用 `ErrorCode` 枚舉表達失敗狀態，它只知道「找不到書」這個事實，不知道這個事實要用哪種語言告訴使用者：

```dart
enum BookErrorCode {
  notFound,
  invalidIsbn,
  networkTimeout,
  serverError,
}

class BookRepository {
  Future<Result<Book, BookErrorCode>> fetchBook(String id) async {
    try {
      final response = await api.getBook(id);
      return Result.success(Book.fromJson(response));
    } on NotFoundException {
      return Result.failure(BookErrorCode.notFound);
    } on TimeoutException {
      return Result.failure(BookErrorCode.networkTimeout);
    }
  }
}
```

不可違反的規則：不引入任何 i18n 相關的 import，不依賴 `BuildContext`，不出現任何使用者可見的字串。

## ViewModel 層：轉換錯誤碼為使用者訊息

ViewModel 是整個 i18n 流程的轉換點。三個合法的訊息來源：i18n 系統（靜態訊息）、ErrorHandler 轉換器（集中管理錯誤碼對應）、Domain 層直接回傳的動態訊息。

```dart
class BookDetailViewModel extends Notifier<BookDetailState> {
  @override
  BookDetailState build() => BookDetailState.initial();

  Future<void> loadBook(String id) async {
    state = state.copyWith(isLoading: true);

    final result = await ref.read(bookRepositoryProvider).fetchBook(id);

    result.when(
      success: (book) {
        state = state.copyWith(isLoading: false, book: book);
      },
      failure: (errorCode) {
        final l10n = ref.read(localizationsProvider);
        final message = ErrorHandler.getMessage(errorCode, l10n: l10n);
        state = state.copyWith(isLoading: false, errorMessage: message);
      },
    );
  }
}
```

`ErrorHandler` 集中管理所有錯誤碼到 i18n key 的映射，不讓這段邏輯散落在各個 ViewModel：

```dart
class ErrorHandler {
  static String getMessage(BookErrorCode code, {required AppLocalizations l10n}) {
    switch (code) {
      case BookErrorCode.notFound:
        return l10n.bookNotFound;
      case BookErrorCode.invalidIsbn:
        return l10n.invalidIsbn;
      case BookErrorCode.networkTimeout:
        return l10n.networkTimeout;
      case BookErrorCode.serverError:
        return l10n.serverError;
    }
  }
}
```

動態參數的情況，ARB 檔案定義佔位符，ViewModel 負責組裝：

```json
{
  "bookNotFoundWithId": "找不到書籍（ID: {bookId}）",
  "@bookNotFoundWithId": {
    "placeholders": {
      "bookId": { "type": "String" }
    }
  }
}
```

```dart
final message = l10n.bookNotFoundWithId(bookId);
state = state.copyWith(errorMessage: message);
```

## UI 層：只負責顯示

UI 層的工作極度單純：顯示 ViewModel 準備好的狀態，不判斷錯誤碼，不組裝字串：

```dart
class BookDetailScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(bookDetailViewModelProvider);

    if (state.isLoading) return const CircularProgressIndicator();

    if (state.errorMessage != null) {
      return ErrorDisplay(message: state.errorMessage!);
    }

    return BookDetailContent(book: state.book!);
  }
}
```

`build` 方法裡不應該出現任何 `switch (errorCode)` 或 `l10n.xxx` 來組裝錯誤訊息。

## 常見反模式

**Domain 層包含使用者訊息**：repository 直接回傳 `'找不到這本書'`，要改成英文就得進業務邏輯層動手，Domain 層不應該對 UI 語言有任何感知。

**ViewModel 硬編碼訊息**：`state.copyWith(errorMessage: '找不到書籍')` 讓字串散落各處，修改時不知道有幾個地方要同步改動。

**UI 層自行組裝訊息**：Widget 的 `build` 方法裡出現 `switch (state.errorCode)`，同一段決策邏輯開始在不同 Widget 裡複製出現。

**跨層傳遞 BuildContext**：把 `BuildContext` 傳入 Domain 層，Domain 層不應該依賴 Flutter 框架的任何概念，這樣的程式碼幾乎無法進行單元測試。

## 實際效益

新增語言支援時，只需要在 ARB 檔案裡補翻譯，確認 `ErrorHandler` 映射完整，不需要搜索整個 codebase 找散落的字串。

Domain 層的測試變乾淨，只需驗證正確的 `ErrorCode` 被回傳，不用比對任何字串內容。每次在 Domain 層看到中文字串，或在 UI 層看到 i18n key 被呼叫，就是一個警示信號——訊息的生成和轉換，只屬於 ViewModel 層。
