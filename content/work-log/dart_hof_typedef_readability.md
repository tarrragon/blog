---
title: "「第一眼看不懂」是該重構還是該學？以 Dart 高階函式與 typedef 為例"
date: 2026-06-01
draft: false
description: "讀程式碼卡住時，先分辨成因：不熟悉慣用法，還是程式碼真的不良 — 兩者解法相反。以一個收 callback 的 SettingsController.update（higher-order function + ValueNotifier）為例，說明為什麼不該為了好懂而拆成一堆 setter（DRY 取捨），以及如何用 typedef、命名、範例註解三個低成本手段提升可讀性而不動 pattern。"
tags: ["dart", "flutter", "higher-order-function", "typedef", "readability", "refactor", "DRY", "code-review"]
---

> **核心議題**：「第一眼看不懂」有兩種成因 — 不熟悉慣用法（pattern unfamiliarity），或程式碼/命名確實不良。前者該學會 pattern，後者才該改 code。把兩者混為一談，會把「正確但陌生的設計」誤拆成「好懂但重複的爛設計」。
> **案例骨幹**：一個收轉換函式的 `SettingsController.update`（higher-order function + `ValueNotifier`）。pattern 是對的、不該動；但「函式型別裸寫在簽章」「參數命名」「缺範例」是真正可改的表層可讀性問題。用 typedef + 改名 + 範例註解三個小手術解決，行為與測試不變。

---

## 1. 案例：一個「收函式」的方法

設定面板有 9 個欄位（字型、顏色、描邊、時間格式…），任何一個變更都要走同一串流程：取當前設定 → 算出新設定 → 比對是否真的變了 → 賦回並通知 UI 重繪。原始寫法把這串流程封裝成一個方法：

```dart
class SettingsController extends ValueNotifier<SettingsModel> {
  /// 修改單一欄位的便利方法（避免外部寫死大量 copyWith 呼叫）。
  void update(SettingsModel Function(SettingsModel current) mutate) {
    final SettingsModel next = mutate(value);
    if (next != value) {
      value = next;
    }
  }
}
```

呼叫端長這樣：

```dart
controller.update((s) => s.copyWith(fillColor: c));
controller.update((s) => s.copyWith(fontSize: v));
```

第一次讀到 `void update(SettingsModel Function(SettingsModel current) mutate)` 這個簽章，多數人會卡一下：參數不是資料，而是「一個函式」。這就是 higher-order function。

---

## 2. Higher-order function 是什麼

定義很短：**把函式當成資料來處理的函式** — 接收函式當參數，或回傳一個函式，符合其一即是。

前提是語言把**函式視為一等公民（first-class）**：函式能像變數一樣被傳遞、儲存、回傳。Dart、JavaScript、Kotlin、Swift 都成立。

你其實天天在用，只是沒命名它：

| 寫法                                        | 高階函式           | 傳進去的函式             |
| ------------------------------------------- | ------------------ | ------------------------ |
| `list.map((x) => x * 2)`                    | `map`              | `(x) => x * 2`           |
| `list.where((x) => x > 0)`                  | `where`            | `(x) => x > 0`           |
| `onPressed: () => doSomething()`            | Widget 收 callback | `() => doSomething()`    |
| `controller.update((s) => s.copyWith(...))` | `update`           | `(s) => s.copyWith(...)` |

它的價值是**把「通用流程」和「具體邏輯」解耦**：`update` 管流程（取值、去重、通知），呼叫端只給邏輯（改哪個欄位）。`map` 管走訪迴圈，呼叫端只給「每個元素怎麼變換」。同一個道理。

---

## 3. 為什麼不拆成一堆「好懂」的 setter

看不懂時最直覺的「優化」是：改成 `setFillColor()`、`setFontSize()`… 一眼就懂。但這是陷阱。

`SettingsModel` 有 9 個欄位，這樣要寫 9 個幾乎一模一樣的方法：

```dart
void setFillColor(Color c) {
  final next = value.copyWith(fillColor: c);
  if (next != value) value = next;
}
void setFontSize(double v) {
  final next = value.copyWith(fontSize: v);
  if (next != value) value = next;
}
// ... 再 7 個
```

每個方法的差別只有 `copyWith(欄位: 參數)` 那一行，其餘「取值、去重、賦回、通知」完全重複。這嚴重違反 DRY：

- 哪天去重邏輯要改（例如加 log），得改 9 個地方。
- 新增第 10 個欄位，得再複製貼上一個方法。

`update` 用**一個**方法涵蓋所有欄位，把重複的流程收斂到唯一一處。這是正確的取捨：**用「呼叫端需要懂 HOF」這個一次性的學習成本，換「永遠不重複流程樣板」的長期維護收益。**

所以結論的第一半：**pattern 不該動**。

---

## 4. 關鍵分辨：「看不懂」的兩種成因

這是整篇的核心。讀 code 卡住時，先問自己：

| 成因               | 本質                           | 正確解法         | 錯誤解法                              |
| ------------------ | ------------------------------ | ---------------- | ------------------------------------- |
| A. 不熟悉慣用法    | pattern 是標準的，只是你沒見過 | **學會 pattern** | 把 pattern 拆掉改成「好懂」的重複寫法 |
| B. 程式碼/命名不良 | 設計或命名確實妨礙理解         | 重構 / 改名      | 加註解硬掰、或放著不管                |

判別準則：**這個寫法在這個語言/框架生態裡，是不是被廣泛使用的標準慣用法？**

- 是 → 偏成因 A。你不會因為第一次看到 `list.map(...)` 看不懂，就說 `map` 命名爛。`update` 收 callback 和 `map`/`setState((){...})` 是同一家族，屬慣用法。
- 否 → 偏成因 B，才考慮改 code。

把 A 誤判成 B 的代價最大：你會把一個正確但陌生的設計，拆成一個好懂但違反 DRY、難維護的設計 — 用長期的維護債，換一次性的「第一眼好懂」。不划算。

但反過來也要誠實：**判斷出主因是 A，不代表 code 完全無可改**。陌生的 pattern 仍可以「呈現得更友善」，這就是成因 B 的殘留部分。

---

## 5. 該做的：三個低成本可讀性改善

本案例主因是 A（HOF 是對的），但有三處屬 B、值得修，且都不動 pattern、不動行為。

### 5.1 用 typedef 幫「函式型別」取名（收益最大）

問題：函式型別裸寫在參數位，讀者要當場解析型別語法。

```dart
// 前：簽章夾著一長串 Function 型別
void update(SettingsModel Function(SettingsModel current) mutate)
```

```dart
// 後：把函式型別升格成有名字的概念
typedef SettingsMutator = SettingsModel Function(SettingsModel current);

void update(SettingsMutator transform)
```

`SettingsMutator`（設定轉換器）這個名字本身就說明「這是一條把舊設定變新設定的規則」。讀者的認知從「解析 `X Function(Y)` 語法」降到「讀一個名詞」。

> typedef 的價值不只是少打字，而是**把抽象的函式型別變成領域詞彙**。

### 5.2 命名貼合語境：`mutate` → `transform`

`SettingsModel` 是不可變物件（`@immutable` + 全 `final`）。`mutate`（變異／就地修改）和「不可變」語境矛盾 — 這裡實際是「拿舊值算出新值」，`transform`（轉換）語意更準確，不會誤導讀者以為它就地改了物件。

### 5.3 doc comment 補一個範例當錨點

對還不熟 HOF 的讀者，一個具體呼叫範例勝過十行抽象描述：

```dart
/// 套用一條「目前設定 → 新設定」的轉換規則（避免外部寫死大量 copyWith 呼叫）。
///
/// 傳入的 [transform] 收當前設定、回傳改好的新設定；本方法負責取值、去重
/// （值未變不重設）、賦回並通知監聽者重繪。
///
/// 範例：`controller.update((s) => s.copyWith(fillColor: c));`
void update(SettingsMutator transform) { ... }
```

---

## 6. 前後對照與驗證

```dart
// === 前 ===
void update(SettingsModel Function(SettingsModel current) mutate) {
  final SettingsModel next = mutate(value);
  if (next != value) value = next;
}

// === 後 ===
typedef SettingsMutator = SettingsModel Function(SettingsModel current);

/// 套用一條「目前設定 → 新設定」的轉換規則 …（含範例）
void update(SettingsMutator transform) {
  final SettingsModel next = transform(value);
  if (next != value) value = next;
}
```

- 呼叫端傳 lambda、不依賴參數名 → **零修改**。
- pattern（HOF + ValueNotifier）與行為 → **不變**。
- 全套單元測試 → **原封不動通過**。

「好的可讀性重構」的特徵就在這裡：**diff 小、風險低、行為不變、可讀性明顯提升**。如果一個「優化」需要動 pattern、改呼叫端、還可能影響測試，那它多半已經越過「可讀性」進到「重新設計」，需要更高規格的評估。

---

## 7. 收斂

- 讀 code 卡住，先分辨成因 A（不熟）還是 B（不良）；判別準則是「這是不是該生態的標準慣用法」。
- 成因 A 的解法是學會 pattern，**不是**把它拆成好懂但重複的寫法 — 否則用維護債換一次性的好懂。
- 即使主因是 A，陌生的 pattern 仍可「呈現得更友善」：typedef 命名函式型別、命名貼合語境、範例註解當錨點，三者都不動 pattern。
- 判斷一個重構是否安全：呼叫端要不要改？行為變不變？測試動不動？三個都「否」，才是純可讀性重構。
