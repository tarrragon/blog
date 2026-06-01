---
title: "為什麼這個場景適合用高階函式？以 Flutter 設定更新為例，比較 typedef 改寫前後"
date: 2026-06-01
draft: false
description: "一個收 callback 的 SettingsController.update（higher-order function + ValueNotifier）。先說明這個場景為什麼適合用 HOF（多欄位共用流程、不可變模型、變化點開放），再把『原始裸函式型別寫法』與『typedef 改寫後』的優缺點並排比較 — 兩者都是 HOF，差別在同一個 pattern 的表達方式與取捨。"
tags: ["dart", "flutter", "higher-order-function", "typedef", "readability", "design-tradeoff", "DRY", "ValueNotifier"]
---

> **核心議題**：高階函式不是「用了比較高級」，而是特定場景的自然解 — 當「流程固定、變化點單一且開放」時，把變化點抽成函式參數最省。本文先論證這個場景為何適合 HOF，再比較同一 pattern 的兩種表達（裸函式型別 vs `typedef`）各自的優缺點。
> **案例骨幹**：`SettingsController.update(transform)` — 9 個設定欄位共用同一條「取值→算新值→去重→通知」流程，唯一的變化是「改哪個欄位」。

---

## 1. 案例：一個收函式的設定更新方法

設定有 9 個欄位（字型、顏色、描邊、時間格式、目標螢幕、開機啟動…）。每個欄位變更都要走同一串流程：取當前設定 → 算出新設定 → 比對是否真的變了 → 賦回並通知 UI 重繪。把這串流程封裝成一個方法：

```dart
class SettingsController extends ValueNotifier<SettingsModel> {
  void update(SettingsModel Function(SettingsModel current) mutate) {
    final SettingsModel next = mutate(value);
    if (next != value) {
      value = next;
    }
  }
}
```

呼叫端只描述「改哪個欄位」：

```dart
controller.update((s) => s.copyWith(fillColor: c));
controller.update((s) => s.copyWith(fontSize: v));
```

`update` 的參數不是資料，是「一個函式」。這就是 higher-order function。

---

## 2. Higher-order function 是什麼（最小定義）

**把函式當資料處理的函式** — 接收函式當參數，或回傳函式，符合其一即是。前提是語言把函式視為一等公民（first-class），能像變數一樣傳遞。Dart、JS、Kotlin、Swift 皆成立。

你天天在用：`list.map((x) => x*2)`、`list.where((x) => x>0)`、`onPressed: () => ...`。`update((s) => ...)` 是同一家族。

---

## 3. 為什麼這個場景適合用 HOF

不是「能用就用」，而是這個場景有三個特徵，剛好對上 HOF 的強項。

### 3.1 流程固定、變化點單一

9 個欄位的更新，**流程 100% 相同**（取值、去重、賦回、通知），**唯一差異**是中間那一步「`copyWith(哪個欄位: 值)`」。

當「共用流程」與「變化點」能這樣切乾淨時，HOF 是教科書級的適配：把固定流程寫死在 `update` 裡，把變化點抽成函式參數 `transform` 由呼叫端帶入。`map` 對「走訪迴圈（固定）+ 元素變換（變化）」做的是同一件事。

### 3.2 模型不可變，本來就是「current → next」

`SettingsModel` 是不可變物件（`@immutable` + 全 `final`）。不能 `value.fillColor = c`，只能用 `copyWith` 產生新副本再整個替換。

也就是說，更新的本質**天生就是一個 `(current) => next` 的函式** — 拿舊值算出新值。用函式參數表達這件事，是語意上最貼合的形狀，而非硬套。

### 3.3 變化點開放、難以列舉

「未來會改哪些欄位、怎麼組合」是開放的（可能同時改兩個欄位、可能有條件邏輯）。函式參數能表達任意轉換；若改用「enum 指定欄位 + switch」則被固定的列舉鎖死，每加一種改法都要動 `update` 內部。HOF 把「怎麼改」的決定權留在呼叫端，`update` 不需要知道。

> 判準：**流程固定 + 變化點單一 + 變化開放** 三者同時成立時，HOF 幾乎總是比「列舉 + 分支」或「複製多個方法」更省。

對照反例：如果只有 1～2 個欄位、或每個欄位的更新流程其實不同，那 HOF 的抽象就不划算，直接寫具名方法更直白。場景不對時硬用才是過度設計。

---

## 4. 原始寫法的優缺點（裸函式型別）

```dart
void update(SettingsModel Function(SettingsModel current) mutate) {
  final SettingsModel next = mutate(value);
  if (next != value) value = next;
}
```

**優點**

- **型別就地可見**：函式的形狀（收什麼、回什麼）直接寫在簽章上，讀者不必跳到別處查定義。
- **零額外宣告**：不需要為了一個參數多定義一個型別別名。

**缺點**

- **簽章冗長、語法門檻**：`SettingsModel Function(SettingsModel current)` 對不熟函式型別語法的人構成解析負擔，一眼難消化。
- **命名與語境矛盾**：參數叫 `mutate`（變異／就地修改），但模型不可變、實際是「產生新副本」，名稱會誤導。
- **缺使用錨點**：簽章沒有範例，第一次用的人不知道該傳什麼形狀的 lambda。

---

## 5. typedef 改寫後的優缺點

```dart
/// 設定轉換規則：收當前設定、回傳改好的新設定（通常以 copyWith 實作）。
typedef SettingsMutator = SettingsModel Function(SettingsModel current);

/// 套用一條「目前設定 → 新設定」的轉換規則 …
/// 範例：`controller.update((s) => s.copyWith(fillColor: c));`
void update(SettingsMutator transform) {
  final SettingsModel next = transform(value);
  if (next != value) value = next;
}
```

**優點**

- **簽章簡潔、概念命名**：`SettingsMutator` 把函式型別升格成領域詞彙，認知從「解析 `X Function(Y)`」降到「讀一個名詞」。
- **命名精準**：`transform`（轉換）貼合不可變語境，不再暗示就地修改。
- **有錨點**：doc comment 的範例讓第一次使用者立即知道怎麼傳。
- **可重用**：同一個 `SettingsMutator` 型別若日後被多個 API 共用，定義集中一處。

**缺點**

- **多一層 indirection**：想知道 `transform` 的確切型別，得跳到 `typedef` 定義；只看 `update` 簽章看不到形狀。
- **多一個命名負擔**：`SettingsMutator` 本身要取得好；命名不當反而多一層要理解的東西。
- **對單一用途略顯重**：若這個函式型別只在一處使用，typedef 的「集中重用」優點用不上，只剩「命名」一項收益。

---

## 6. 並排比較

| 面向           | 原始（裸函式型別）    | typedef 改寫後             |
| -------------- | --------------------- | -------------------------- |
| 簽章可讀性     | 冗長、需解析語法      | 簡潔、讀一個名詞           |
| 型別形狀可見性 | 就地可見（優）        | 需跳到 typedef 定義（劣）  |
| 命名語意       | `mutate` 與不可變矛盾 | `transform` 貼合           |
| 使用門檻       | 無範例                | 有範例錨點                 |
| 額外宣告成本   | 無                    | 多一個 typedef 要命名/維護 |
| 多處共用時     | 各自裸寫、重複        | 集中定義、重用             |
| pattern / 行為 | HOF                   | HOF（不變）                |

關鍵：**兩者是同一個 pattern（HOF + ValueNotifier）的不同表達**，不是不同設計。取捨重點在「型別就地可見」對上「簽章簡潔 + 概念命名」—— 當函式型別會被多處使用、或語法門檻造成實際閱讀摩擦時，typedef 划算；若只用一次且團隊熟悉函式型別語法，裸寫也完全合理。

改寫的驗證也印證它停在「表達層」：呼叫端傳 lambda 不依賴參數名 → 零修改；行為不變；全套測試原封不動通過。

---

## 7. 收斂

- HOF 適合的場景特徵：**流程固定 + 變化點單一 + 變化開放**。三者齊備時，把變化點抽成函式參數最省；場景不符（欄位少、流程各異）則具名方法更直白。
- 不可變模型的更新本質就是 `(current) => next`，用函式參數表達是語意貼合，不是炫技。
- 裸函式型別 vs typedef 是「同一 pattern 的兩種表達」：前者型別就地可見、零宣告；後者簽章簡潔、命名成概念、可重用，但多一層 indirection。
- 選擇依據：函式型別是否多處共用、語法是否造成實際閱讀摩擦。摩擦明顯就抽 typedef，否則裸寫無妨。
