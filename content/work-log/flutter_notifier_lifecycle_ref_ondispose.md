---
title: "手寫 dispose() 沒有呼叫者 — Notifier 的依賴與清理都歸 build() 管"
date: 2026-07-16
draft: false
description: "Notifier 用建構子注入依賴、或手寫 dispose() 釋放 Timer 與訂閱時使用。Notifier 的建構與銷毀都由容器管理——UI 不會呼叫 dispose()、掛在方法上的清理等於沒掛；依賴在 build() 內 ref.watch、清理在 ref.onDispose 註冊。"
tags: ["flutter", "dart", "riverpod", "lifecycle", "dependency-injection", "state-management"]
---

> **觸發場景**：Flutter 書籍管理 App 的掃描器 ViewModel 用建構子接收三個 service、provider 工廠手動 `new` 具體類別傳進去；資源清理寫在自訂的 `dispose()` 方法裡
> **疑問來源**：這個 `dispose()` 誰呼叫？盤點後答案是沒有人——UI 透過 provider 取用 Notifier、從頭到尾沒有拿到過需要它負責釋放的物件
> **整理目的**：記下 Notifier「生與死都歸容器管」的機制、建構端與銷毀端各自的正確掛法
> **本文邊界**：素材是該專案 v0.31.1 的 DI 一致性重構記錄；屬架構調整、不是崩潰事故——風險是結構性的（清理掛在無人呼叫的方法上）

---

## 機制：Notifier 的建構與銷毀都不歸使用者管

Riverpod 的 Notifier 生命週期兩頭都由容器控制。**建構端**：provider 工廠（`NotifierProvider(ViewModel.new)`）在容器第一次需要這個狀態時實例化 Notifier、接著呼叫 `build()`；**銷毀端**：容器判定節點該回收時（scope 銷毀、autoDispose 無人監聽）觸發 dispose 流程。使用者的程式碼在這兩頭都沒有控制點——UI 拿到的是 `ref.watch(provider.notifier)` 的引用、它不建構也不銷毀。

在這個前提下，兩種常見寫法都是跟容器搶生命週期控制權：

- **建構子注入依賴**：工廠得手動 `new` 依賴傳進建構子——依賴的建構脫離 provider 圖，`BookService()` 直接實例化、不經過 `bookServiceProvider`，測試 override 摸不到它、依賴的依賴也斷鏈。
- **手寫 `dispose()` 方法**：方法宣告在那裡、等一個呼叫者——但 Notifier 的持有者是容器、容器只認自己的 dispose 流程，UI 沒有任何一處會呼叫這個方法。掛在裡面的 Timer 取消、StreamSubscription 釋放，等於沒掛。

## 遷移：兩頭都收進 build()

```dart
// 之前：建構子注入 + 手寫 dispose
class IsbnScannerViewModel extends Notifier<IsbnScannerState> {
  IsbnScannerViewModel(this._bookService, this._cameraService, this._validator);
  final BookService _bookService;
  // ...
  void dispose() { _cancelScanning(); }   // 沒有呼叫者
}

final isbnScannerViewModelProvider = NotifierProvider<IsbnScannerViewModel, IsbnScannerState>(
  () => IsbnScannerViewModel(BookService(), CameraService(), IsbnValidationService()),
);
```

```dart
// 之後：依賴在 build() 內 ref.watch、清理在 ref.onDispose 註冊
class IsbnScannerViewModel extends Notifier<IsbnScannerState> {
  late final BookService _bookService;
  late final CameraService _cameraService;
  late final IsbnValidationService _isbnValidationService;

  @override
  IsbnScannerState build() {
    _bookService = ref.watch(bookServiceProvider);
    _cameraService = ref.watch(cameraServiceProvider);
    _isbnValidationService = ref.watch(isbnValidationServiceProvider);
    ref.onDispose(_cancelScanning);   // 容器銷毀節點時執行
    return IsbnScannerState.initial();
  }
}

final isbnScannerViewModelProvider = NotifierProvider<IsbnScannerViewModel, IsbnScannerState>(
  IsbnScannerViewModel.new,          // 工廠只負責實例化、不碰依賴
);
```

改完之後的責任分佈：工廠回到 `ViewModel.new` 一行、依賴全部經 provider 圖取得（可 override、可追蹤）、清理掛在容器一定會走的 hook 上。`ref.onDispose` 跟手寫方法的差別就是「誰保證執行」——前者由容器的 dispose 流程保證、後者由一個不存在的呼叫者保證。

## 兩個附帶的工程紀律

這次重構的執行記錄留了兩件跟主題無關、但可轉移的事：

**Pre-existing 失敗要用 baseline 重跑確認**。改完後跑測試、一個多語系版型測試在小螢幕溢位失敗。判定它跟本次改動無關的方式是機械的：`git stash` 還原變更、在 baseline 重跑同一個測試、同樣失敗——確認是既有問題、記錄待追蹤、不混進本次範圍。「看起來無關」是猜測、baseline 重跑是證據。

**Worktree 的 dart analyze 要先 pub get**。在 git worktree 裡跑 `dart analyze`、它會向上解析到主 repo 的舊版 `package_config` 造成假錯誤；先在 worktree 內 `flutter pub get` 產生本地設定檔才能得到真結果。

## 判讀徵兆

- Notifier / ViewModel 類別裡有自訂的 `dispose()` 或 `close()` 方法——先找呼叫者，找不到就是本文的形態：清理掛在無人呼叫的方法上、改掛 `ref.onDispose`
- provider 工廠裡出現 `new` 具體類別（`SomeService()`）傳進建構子——依賴脫離 provider 圖、測試 override 失效，改成 `build()` 內 `ref.watch`
- 工廠寫法不是 `ViewModel.new` 一行——通常代表建構子還揹著依賴
- 改動後測試失敗、懷疑是既有問題——stash 還原跑 baseline、用同樣失敗證明、不用直覺判定

## 相關閱讀

- 生命週期的另一頭：[await 回來的時候、頁面已經關了](/work-log/flutter_unmounted_ref_async_gap/)——本文管銷毀時的清理、那篇管銷毀後的 `ref` 使用
- provider 圖的整體邊界：[Riverpod 的 reactive 邊界](/flutter/riverpod-reactive-boundary/)——依賴經 `ref.watch` 取得才在圖上、正是本文遷移的理由
- DI 的概念地基：[Dependency Injection](/ddd/knowledge-cards/dependency-injection/)——建構與使用分成兩個責任、Notifier 的工廠與 build() 是這個分工的框架版
