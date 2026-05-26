---
title: "寫測試時 sync try-catch 接不到 BotToast 的 async 錯誤：fire-and-forget API 的接管設計"
date: 2026-05-26
draft: false
description: "寫測試會撞到 type system 看不到的三類 runtime 契約：service locator 注入、widget tree state、late init。以 BotToast 的 sync assert + async LateInit 雙失敗模式為例，拆解為什麼 sync try-catch 不夠、用 runZonedGuarded 同時罩 sync 與 async、以及 fallback 訊息的可識別 signature 設計。"
tags: ["dart", "flutter", "test", "async", "zone", "runZonedGuarded", "service-locator", "fallback-design"]
---

> **核心議題**：寫測試時撞到 type system 看不到的 runtime contract — service locator 的注入契約、widget tree 的 framework state、async error 的 try-catch 邊界。三類都要 runtime 才會炸、test 跑到才會曝光。
> **案例骨幹**：`Popup.hint` 同一條呼叫路徑同時持有 sync 與 async 兩條失敗路徑（缺 service 注入、BotToast 同步 assert、BotToast 從 async gap 後拋 `LateInitializationError`）。用 `runZonedGuarded` 把兩條路徑收斂到同一個 fallback handler、用 fallback signature 設計讓訊息不被誤判為 error。

---

## 1. Type system 看不到的 runtime contract

`flutter analyze`（與一般的 type checker）的責任是檢查宣告與名稱層的契約 — 型別一致、import 能解析、識別字能對到符號。它驗證的是「靜態可決定的事」：missing import、undefined method、type mismatch 都會在 compile 前被攔下。

它**看不到**的是 runtime 才成立的契約，這正是寫測試最容易暴露的盲區：

- **Service locator 的注入契約**：GetX 的 `Get.find<T>()`、`get_it` 的 `GetIt.I<T>()`、Provider 的 `Provider.of<T>()` 都是 runtime 查找機制（Map lookup 或 widget tree 上溯，視實作而定）。「呼叫前 T 必須先註冊或在 ancestor 提供」是執行期前置條件，型別系統看不見。
- **Framework state 的存在前提**：BotToast 需要 widget tree 上有 `BotToastInit`、Navigator 需要 `MaterialApp` 包著。這是 framework 的執行期狀態，不是型別。
- **`late` 變數的跨呼叫順序契約**：宣告對了不代表用對了。analyzer 對單一檔案內某些 unsafe pattern 能出警告，但「A 函式必須在 B 函式前被呼叫」這類跨呼叫順序契約，型別系統看不見。

這個邊界對「寫測試」的意涵：test setUp 不只是準備資料，更是補上 type system 看不到的 runtime contract — 注入哪些 service、提供哪些 framework state、控制哪些 init 順序。**主程式裡那些「靠 widget tree」「靠 service locator」「靠 framework lifecycle」的契約，每一條都對應到 test setUp 的一個責任**。

---

## 2. 案例：一條呼叫路徑撞到三類邊界

下面以 `Popup.hint` 對 `BotToast.showNotification` 的呼叫為例。寫一個跑 `AuthService.afterLogin` 的 unit test 時，這條呼叫一次撞到 §1 列的三類邊界：service locator 注入缺失、widget tree 缺 `BotToastInit`、`late` 變數在 async 排程後讀取。三組訊號攤開：

| 訊號                                                                                                               | 性質                                                                                                              | sync try-catch 能接？           |
| ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `"LogService" not found.` 從 `Get.find<LogService>()` 拋出                                                         | 同步（service locator 查無注入）                                                                                  | 能，但這層該補 setUp 而非包 try |
| `Failed assertion: '_key.currentState != null'` 在 `BotToast.showNotification` 入口                                | 同步（widget tree 缺 `BotToastInit` 入口 assert）                                                                 | 能                              |
| `LateInitializationError: Local 'cancelFunc' has not been initialized.` 出現在 `===== asynchronous gap =====` 之後 | async + 跨呼叫順序契約破裂（`late cancelFunc` 預期在某次 init 之後才讀、但 BotToast 排到下一 frame 時順序對不上） | 不能                            |

第一條的修法是 setUp 補注入。第二條的同步 assert 單獨看，sync try-catch 接得住。但它跟第三條 async error 是**同一個 API 的兩種失敗模式** — 包 sync try-catch 只罩到同步那條、async 那條仍漏。

結論：要兩條都接到，需要一個同時 cover sync 與 async 的接管機制。

---

## 3. Sync try-catch 與 async error 的邊界

Sync `try-catch` 的作用範圍是同步調用棧：try block 執行期間棧上拋的錯誤會被接住。一旦執行流程穿越 async 邊界（Future、Timer、microtask 排程），原 try-catch 已經出 scope：

```text
Popup.hint() {
  try {
    BotToast.showNotification(...)   ← 同步返回，立刻離開 try
      └─ 內部排到下一個 frame 或 microtask {  ← 之後才跑
           ...拋 LateInitializationError...   ← try-catch 已經出 scope
         }
  } catch (e) { ... }
}
```

辨識 async unhandled error 的訊號是 stack trace 裡有 `===== asynchronous gap =====` — 它代表錯誤穿越了一個 async 邊界。從 caller frame 來看「沒人在 stack 上」，錯誤會上溯到 zone 的 uncaught error handler；root zone 把它印到 stderr，或讓 flutter_test runner 當作 test failure。

`async` 函式內的 try-catch 是常見混淆點：寫成 `try { await x; } catch (e)` 時，try-catch **能**接住 `await` 的 future rejection（`await` 把 async error rewire 成 sync throw）。但對沒 await 的 fire-and-forget 排程（直接呼叫一個會內部 schedule microtask 的 API），try-catch 的覆蓋範圍止於同步路徑。

### 風險：fire-and-forget API 特別容易踩

BotToast、analytics、Toast、SnackBar 這類 API 通常**同步返回**（讓 caller 不必 await），內部排到下一個 frame 或 microtask 做 UI 工作。caller 看到的是同步呼叫，但錯誤可能從 async 邊界後跑出來。caller 端的 sync try-catch 看起來罩住了，實際接不到。

---

## 4. 接管機制：runZonedGuarded 同時罩 sync 與 async

接 async unhandled error 要用 zone-aware 機制。`runZonedGuarded(body, onError)` 建立一個子 zone，**任何在這個 zone 內 schedule 的 async work，錯誤都會冒泡到 `onError`** — 不管錯誤穿越幾層 microtask、Timer、Stream。它同時也 cover 同步拋錯，可以取代 try-catch 包住整個 best-effort 邊界：

```dart
// toast 是 best-effort：BotToast 需要 widget tree (BotToastInit)，
// 在非 UI 環境（unit test、isolate）顯示失敗時保留 log、不向 caller 傳遞錯誤。
// 用 runZonedGuarded 因為 BotToast 部分錯誤從 async gap 後拋出，sync try-catch 接不到。
runZonedGuarded(() {
  BotToast.showNotification(
    title: (_) => Text(message, style: AppTheme.whiteTextButtonStyle),
    backgroundColor: contentColor,
    duration: const Duration(seconds: 2),
    animationDuration: const Duration(milliseconds: 300),
    animationReverseDuration: const Duration(milliseconds: 300),
  );
}, (error, stack) {
  if (kDebugMode) {
    debugPrint('[Popup.hint][fallback] BotToast 不可用，僅記 log：$error');
  }
});
```

機制重點：同一個 `onError` 同時接住同步的 `Failed assertion` 與 async 的 `LateInitializationError` — sync 與 async 兩條失敗路徑收斂到單一 fallback handler，不需要為兩條各寫一套錯誤處理。

---

## 5. runZonedGuarded 的責任邊界

`runZonedGuarded` 把整個邊界的錯誤導向 fallback handler，責任範圍要劃清楚：

| 情境                                                    | 行為               | 設計意涵                                        |
| ------------------------------------------------------- | ------------------ | ----------------------------------------------- |
| async work 自己處理掉錯誤（try-catch 或 `.catchError`） | 接不到             | zone 看不到已被吞的錯誤；要 zone 接，內層別自吞 |
| `onError` handler 自己拋錯                              | 上溯到 parent zone | handler 要簡短可靠；fallback 自己掛是上層責任   |
| 同步拋錯                                                | 也會被接住         | zone 同時 cover sync 與 async，可取代 try-catch |
| zone 內建立的 Timer / Stream                            | 屬於這個 zone      | spawn 出的 async 物件「記得」自己屬於哪個 zone  |

**zone ≠ thread**。Dart 是單線程的，zone 只是邏輯標籤、不涉及並發。它**只改變錯誤的去向、不會 cancel 已 schedule 的 work**。

### 注意事項：何時不該用

Zone 歸屬以 schedule 時的 zone 為準、不是執行時 — async 物件「屬於」schedule 它的那個 zone。這個規則讓跨 zone 操作 Timer、Stream 的行為偏離直覺。實務上踩雷最常見的場景是 `WidgetsFlutterBinding.ensureInitialized()` 在 root zone 註冊了 framework binding 後、才用 `runZonedGuarded` 包 `runApp`，binding 內部 callback 已綁在 root zone、外層 zone 接不到。[Flutter 官方明確建議](https://docs.flutter.dev/release/breaking-changes/zone-errors) `ensureInitialized()` 跟 `runApp()` 都在同一個 `runZonedGuarded` 內。

zone 適合包「整個邊界」：整個 isolate entry、整個 best-effort UI 工作、整個 background task。**不適合包關鍵 transaction logic** — 那是 try-catch + Future error handling 的責任，zone 是 fallback 收斂層、不是主要錯誤處理。

---

## 6. Fallback 訊息設計：可識別的 signature

Fallback path 跑通之後，留在 console 的訊息會被讀到很多次（每次 test 都會跑）。**訊息措辭要與設計意圖一致**，否則讀者每次都要花心力辨識「這是設計內降級、還是真的 bug」。

### 風險：fallback 長得像 error

直覺寫法 `debugPrint('toast 顯示失敗：$error')` 加上 framework 的 assert stack，字面看起來就是個 error。讀者第一眼會緊張、要花心力比對程式才能確認「這是設計內路徑」。test 跑很多次、每次都付一次辨識成本。

### 三條設計原則

**Fallback path 要有可識別的 signature**（標籤、prefix、特定字眼）、長得不像 error。對人類讀者，prefix 是視覺上一眼識別「設計內路徑」；對工具，`grep -v "\[fallback\]"` 可快速剔除 test 輸出裡的預期降級訊息。

**字眼要表達因果與處置**：「BotToast 不可用，僅記 log」比「顯示失敗」更完整 — 前者說了為什麼降級、後者只描述現象。寫 fallback 訊息要回答兩個問題：為什麼進這條路徑、降級到哪。

**主程式不該感知測試框架**：主程式 import `dart:io`、查 `Platform.environment['FLUTTER_TEST']` 等於「主程式對自己被 test 跑」有意識 — 這違反「主程式不該知道 test 存在」的原則，test 框架是 caller 的事、不是 callee 的事。違反後續成本：app 行為依賴環境變數時，QA / staging / production 的環境一致性會多一條檢查線。

### 三個候選方案在原則上的取捨

下列三個方案分別在「signature 識別度」「主程式對 test 框架感知」「dev 可見性」三條原則上做不同取捨：

| 維度                       | A. 標籤化（`[fallback]` prefix） | B. 偵測 `FLUTTER_TEST` 環境 silent | C. 完全靜默  |
| -------------------------- | -------------------------------- | ---------------------------------- | ------------ |
| 改動大小                   | +1 行                            | ~10 行 + 新 import                 | −1 行        |
| test 輸出乾淨度            | 仍有訊息，但 prefix 一眼識別     | 完全乾淨                           | 完全乾淨     |
| dev app 跑時可見性         | 保留                             | 保留                               | 失去         |
| 主程式對 test 框架的感知   | 無                               | 有（import dart:io 查 env）        | 無           |
| grep 友善度                | 好（`[fallback]` prefix）        | —                                  | —            |
| BotToast 真壞時 debug 難度 | 容易（訊號 + 標籤）              | 中（test 看不到、要切環境）        | 難（無線索） |

### 為什麼選 A

保留 dev 訊號（BotToast 在 dev app 真的壞時 console 仍會印） + 主程式對 test 框架無感知 + prefix 雙贏（人類視覺辨識 + grep 過濾）。方案 C 完全靜默會失去保險、dev 環境真壞時看不見；方案 B 雖然 test 輸出乾淨，代價是違反設計原則。

---

## 7. 設計副產物：修主程式對缺依賴的容錯

`Popup.hint` 對「沒有 widget tree」連環倒，這個失敗不只 unit test 會碰到 — isolate 內、background task 內、任何非 UI 環境都會炸。修 test 順手把主程式對缺依賴的容錯加上，是合理副產物：unit test 是觸發訊號、主程式被觸發後變得更能適應多元 caller 環境，這個改動的受益面大於原本 test 暴露的那個情境。

**主程式變 robust 的價值大於「讓 test 過」**。修主程式對 caller 環境的容錯時要分辨「容錯」與「掩蓋」的界線：log 仍要留、fallback signature 仍要可識別（§6），錯誤完全靜默會讓 dev app 真壞掉時也看不見。

---

## 適用範圍

`runZonedGuarded` 適用情境：

- **Fire-and-forget 的 UI 通知**：Toast、SnackBar、analytics 上報；這些是 best-effort，caller 連環倒不合理。
- **Isolate entry point**：spawn 出來的 isolate 沒有預設 error handler，包一層 zone 才不會靜默掛掉。
- **Background task / Timer 包裝**：long-running periodic job 內部錯誤不該炸掉整個 process。
- **flutter_test 內掛 Stream / Future 驗證**：把測試體包進 zone 才能完整接 async 拋出的東西。

「Type system 看不到的 runtime contract」適用任何用 service locator / DI 容器、framework state、late init 的 Flutter 專案。Test 是這些 runtime contract 的事實驗證者 — analyze 過了不代表這些契約沒破，test 跑到才會炸。

---

## 參考資料

- [Dart `runZonedGuarded` API](https://api.dart.dev/stable/dart-async/runZonedGuarded.html)
- [Dart Zone 概念與 zone-local variables](https://dart.dev/articles/archive/zones)
- [Flutter Zone mismatch breaking change](https://docs.flutter.dev/release/breaking-changes/zone-errors) — `ensureInitialized()` 與 `runApp()` 必須同 zone
- [`flutter_test` async error 處理機制](https://api.flutter.dev/flutter/flutter_test/FlutterTest-library.html)
- 同主題本站文章：[Dart test 的跨檔案 GetX 狀態污染](../dart_test_getx_cross_file_state_pollution/) — 另一種「test 環境組裝不完整」的 case
