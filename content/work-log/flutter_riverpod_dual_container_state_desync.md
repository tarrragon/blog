---
title: "App 永遠卡在載入畫面 — Riverpod 的 provider 是配方、容器才持有狀態"
date: 2026-07-10
draft: false
description: "main() 自建 ProviderContainer 對它觸發初始化、UI 跑在 runApp 的 ProviderScope 裡——兩個容器各持一份 provider 狀態、互不相通，UI 監聽的那份永遠停在初始值。Riverpod 的全域 provider 宣告只是配方、狀態屬於容器實例；跨容器操作是靜默的無效操作。"
tags: ["flutter", "dart", "riverpod", "state-management", "provider", "debugging"]
---

> **觸發場景**：Flutter App 啟動後永遠停在載入畫面。初始化的 provider 狀態永遠是 `notStarted`、初始化流程從未執行——但初始化邏輯的單元測試是綠的
> **疑問來源**：`main()` 裡明明呼叫了 `initialize()`，為什麼 UI 看到的狀態完全沒動？
> **整理目的**：記下 Riverpod「provider 宣告全域、狀態屬於容器」的心智模型、以及跨容器操作靜默失效的機制
> **本文邊界**：素材是該專案 v0.10.1 的修復記錄（Riverpod 2.x 時期）；「配方 vs 廚房」的心智模型跨版本成立

---

## 症狀與現場

出問題的 `main()` 長這樣：

```dart
final container = ProviderContainer();
container.read(appInitializationProvider.notifier).initialize();  // 對外部容器操作

runApp(ProviderScope(child: BookLibraryApp()));                    // UI 在另一個容器裡
```

兩行各自都「正確」：`initialize()` 真的被呼叫、真的執行完；`ProviderScope` 裡的 UI 真的在監聽 `appInitializationProvider`。但 UI 的狀態永遠是 `notStarted`——因為**它們操作的是兩份不同的狀態**。

## 機制：provider 宣告是配方、容器持有狀態

Riverpod 的 provider 宣告寫在全域：

```dart
final appInitializationProvider = NotifierProvider<...>(...);
```

全域宣告製造了「狀態也是全域」的錯覺。實際上這個全域物件只是**配方**——描述「這個狀態怎麼建、怎麼變化」。狀態本身活在容器裡：`ProviderContainer()` 建一個容器、`ProviderScope` 在 widget tree 裡也建一個容器（它內部就是包了一個 container）。同一份配方在兩個容器裡各煮出一份互不相干的狀態。

於是 `container.read(...).initialize()` 改的是外部容器那份狀態——改成功了、沒有任何錯誤；UI 監聽的是 Scope 容器那份——從頭到尾沒人動它。**跨容器操作不會報錯、它只是安靜地作用在你以為之外的地方**，這是這類 bug 難查的原因：每一段程式碼單獨看都在正常工作。

## 修法：把觸發點移進唯一的容器

修復選的方案是移除外部容器、讓初始化在 widget tree 內觸發：

```dart
// main.dart：只負責 runApp
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: BookLibraryApp()));
}

// _AppWrapper：偵測未初始化、在首幀後觸發
if (initState.status == AppInitializationStatus.notStarted) {
  WidgetsBinding.instance.addPostFrameCallback((_) {
    ref.read(appInitializationProvider.notifier).initialize();
  });
}
```

兩個細節。`addPostFrameCallback` 把觸發延到首幀之後——build 期間直接改 provider 狀態是另一類錯誤（widget tree 建置中修改 provider 會炸）。觸發條件掛在 `notStarted` 狀態上，讓「誰負責啟動初始化」有唯一答案：看到未初始化的第一個 wrapper。

如果情境真的需要在 `runApp` 之前操作 provider（例如讀取啟動設定），正解是讓兩邊共用同一個容器——自建的 container 透過 `UncontrolledProviderScope` 傳進 widget tree，而不是各建一個。判準收成一句：**一個 App 裡活著的容器數量應該是一、每多一個都要能說出它為什麼必須隔離**（測試裡的 `ProviderContainer(overrides: ...)` 就是正當的隔離）。

## 為什麼單元測試沒抓到

初始化 Notifier 的單元測試是綠的——它驗證「這份配方煮出來的狀態會正確走完初始化」，在測試自己的容器裡完全成立。bug 不在配方、在**佈線**：兩個容器的存在是 `main()` 的組裝問題，單元測試的邊界不含組裝。這類 bug 的守備範圍在整合層——一條「啟動 App、斷言最終離開載入畫面」的 widget 測試就能攔住。修復記錄還留了一個測試環境的絆腳石：初始化流程裡的 `Future.delayed` 計時器跟 widget test 的 pending-timer 檢查不相容，這也是當時整合測試缺席的原因之一——計時器類的延遲在可測性上要優先考慮可注入的 clock 或可等待的 Future。

## 判讀徵兆

- 「狀態改了但 UI 沒反應」且雙方程式碼各自看都正確——先數容器：全專案搜 `ProviderContainer(`，每一個實例都問「它跟 UI 的 Scope 是同一個嗎」
- `main()` 裡出現 `ProviderContainer()` 又出現 `ProviderScope`——幾乎就是本文的 bug 形態
- provider 狀態「永遠是初始值」——比「狀態錯誤」更指向無人操作這份實例、該查操作方作用在哪個容器

## 相關閱讀

- 同屬狀態管理框架的跨界 bug：[Dart test 的跨檔案 GetX 狀態污染](/work-log/dart_test_getx_cross_file_state_pollution/)——GetX 的問題是全域單例讓狀態「太共享」、Riverpod 這裡是容器隔離讓狀態「太不共享」，兩篇合看是狀態作用域的兩個失敗方向
- 靜默失效的同構：[#221 檢查規則的作用域要顯式列舉](/report/lint-scope-must-be-explicit-fact/)——作用在錯的作用域、不產生任何錯誤訊號，症狀在遠處浮現
