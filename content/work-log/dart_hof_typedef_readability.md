---
title: "為什麼這個場景適合用高階函式？以 Flutter 設定更新為例，比較 typedef 改寫前後"
date: 2026-06-01
slug: "dart_hof_typedef_readability"
draft: false
description: "高階函式的適用判準（流程固定、變化點單一且開放）與裸函式型別 vs typedef 的可讀性取捨並排比較。"
tags: ["dart", "flutter", "higher-order-function", "typedef", "readability", "design-tradeoff", "DRY", "ValueNotifier"]
---

> **核心議題**：高階函式是特定場景的自然解 — 當「流程固定、變化點單一且開放」時，把變化點抽成函式參數最省。要不要用它，由場景特徵決定。本文先論證這個場景為何適合 HOF，再比較同一 pattern 的兩種表達（裸函式型別 vs `typedef`）各自的優缺點。
> **案例骨幹**：`SettingsController.update(transform)` — 9 個設定欄位共用同一條「取值→算新值→去重→通知」流程，唯一的變化是「改哪個欄位」。

---

## 1. 案例：一個收函式的設定更新方法

設定有 9 個欄位（字型、顏色、描邊、時間格式、目標螢幕、開機啟動…）。每個欄位變更都要走同一串流程：取當前設定 → 算出新設定 → 比對是否確實改變 → 賦回並通知 UI 重繪。把這串流程封裝成一個方法：

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

`update` 收的這個參數本身是「一個函式」 — 把函式當成可傳遞的值。這就是 higher-order function。

### 簽章的型別與名字拆解

這個簽章的關鍵是分清「哪裡是型別、哪裡是名字」。它是一個普通的參數宣告，順序跟常見的 `int count`、`Color color` 一樣是 **`型別 名字`**，只是這次型別換成了較長的函式型別：

```dart
void update(SettingsModel Function(SettingsModel current)  mutate)
//          └──────────── 型別（函式型別）────────────┘  └名字┘
```

`mutate` 是**這個參數的名字** — 方法內部靠它指涉傳進來的那個函式：

```dart
void update(SettingsModel Function(SettingsModel current) mutate) {
  final SettingsModel next = mutate(value);  // ← 用名字 mutate「呼叫」傳進來的函式
}
```

容易混淆的是型別裡面那個 `current`：它和 `mutate` 不同層級 — `current` 只是函式型別內標記參數的名字，**純文件性**，寫成 `SettingsModel Function(SettingsModel)` 行為完全一樣，只是讓型別讀起來更清楚。換句話說，前半的函式型別規定「這個名字必須是什麼形狀的函式」，最後的 `mutate` 則是「這個函式參數叫什麼」。下一節先補 HOF 的基礎，第 4 節再回頭談「前半那串型別裸寫在簽章」造成的閱讀摩擦。

---

## 2. Higher-order function 是什麼（最小定義）

**把函式當資料處理的函式** — 接收函式當參數，或回傳函式，符合其一即是。前提是語言把函式視為一等公民（first-class），能像變數一樣傳遞。Dart、JS、Kotlin、Swift 皆成立。

常見的 `list.map((x) => x*2)`、`list.where((x) => x>0)`、`onPressed: () => ...` 都屬此類。`update((s) => ...)` 是同一家族。

---

## 3. 為什麼這個場景適合用 HOF

這個場景有三個特徵，剛好對上 HOF 的強項 — HOF 適不適用，由這些特徵決定。

### 3.1 流程固定、變化點單一

9 個欄位的更新，**流程 100% 相同**（取值、去重、賦回、通知），**唯一差異**是中間那一步「`copyWith(哪個欄位: 值)`」。

當「共用流程」與「變化點」能這樣切乾淨時，HOF 正好對上這個結構：把固定流程寫死在 `update` 裡，把變化點抽成函式參數 `transform` 由呼叫端帶入。`map` 對「走訪迴圈（固定）+ 元素變換（變化）」做的是同一件事。

### 3.2 模型不可變，本來就是「current → next」

`SettingsModel` 是不可變物件（`@immutable` + 全 `final`）：要改 `fillColor`，得用 `copyWith` 產生新副本、再把整個物件替換回去。

也就是說，不可變模型下的更新，在語意上**就是一個 `(current) => next` 的函式** — 拿舊值算出新值。用函式參數表達這件事，是最貼合的形狀。

### 3.3 變化點開放、難以列舉

「未來會改哪些欄位、怎麼組合」是開放的（可能同時改兩個欄位、可能有條件邏輯）。函式參數能表達任意轉換；若改用「enum 指定欄位 + switch」則被固定的列舉鎖死，每加一種改法都要動 `update` 內部。HOF 把「怎麼改」的決定權留在呼叫端，`update` 不需要知道。

反過來說，當「變化集合是封閉的、而且需要被序列化或跨層比對」時，enum + switch 反而較好 — 例如要把「使用者改了哪個欄位」存進 undo 堆疊、或透過網路傳給後端，列舉值是可序列化的資料，閉包不是。本案例的變化點純粹發生在呼叫端、不需要 persist，HOF 才站得住。所以「開放」算不算優點，要跟「變化是否需要被當資料搬運」一起看。

> 判準：**流程固定 + 變化點單一 + 變化開放** 三者同時成立時，HOF 幾乎總是比「列舉 + 分支」或「複製多個方法」更省。

對照反例放進具體場景更清楚。假設一個只有「深色模式開關」單一布林設定的 controller，更新邏輯就是 `value = !value`，既沒有共用流程、也沒有開放的變化點 — 這時把它包成收函式的 `update`，只是逼讀者解析一串函式型別去做一件 `toggleDarkMode()` 就講完的事，抽象成本大於收益。另一種反向情境是：9 個欄位看似共用流程，實際每個的更新路徑各不相同（有的要打 API、有的要寫檔、有的純記憶體），那麼「固定流程」的前提根本不成立，硬抽進 `update` 反而把三條不同的路徑塞進同一個殼裡。三條件少一條，具名方法通常更省 — 場景不對時硬用，才是過度設計。

---

## 4. 原始寫法的優缺點（裸函式型別）

```dart
void update(SettingsModel Function(SettingsModel current) mutate) {
  final SettingsModel next = mutate(value);
  if (next != value) value = next;
}
```

### 什麼是「函式型別裸寫在簽章」

這是整個討論的起點，值得單獨講清楚。把術語拆三個詞：

- **函式型別**：描述「一個函式長什麼樣」的型別，例如 `SettingsModel Function(SettingsModel current)` — 收一個 `SettingsModel`、回傳一個 `SettingsModel`。
- **裸寫**：把完整型別**整串攤開寫出來**，沒有先取名包裝（對比「裸數字 / magic number」直接寫 `120` 而非具名常數）。
- **在簽章**：寫在方法的參數列（signature）裡。

合起來就是：**把那串 `SettingsModel Function(SettingsModel current)` 原封不動塞進參數位，而不是先用 `typedef` 取個名字再引用。**

```dart
// 裸寫：函式型別整串長在簽章裡
void update(SettingsModel Function(SettingsModel current) mutate)
//          └────────── 這一整串就是「裸寫的函式型別」──────────┘
```

為什麼偏偏是「函式型別」會因為裸寫而卡住，一般型別卻不會？因為 `int`、`Color` 這類型別已經是短名稱，裸寫毫無負擔；而函式型別的完整語法 `X Function(Y)` 較長、巢狀時更難讀，**讀者得當場在腦中解析「這是收什麼、回什麼的函式」**。讀程式碼第一眼卡住的，正是這串裸寫的函式型別 — 它才是這篇要討論「要不要抽 typedef」的真正觸發點。下面的優缺點，都圍繞「裸寫 vs 取名」這個軸展開。

### 優點

- **型別就地可見**：函式的形狀（收什麼、回什麼）直接寫在簽章上，讀者不必跳到別處查定義。
- **零額外宣告**：不需要為了一個參數多定義一個型別別名。

### 缺點

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

### 優點

- **簽章簡潔、概念命名**：`SettingsMutator` 把函式型別升格成領域詞彙，認知從「解析 `X Function(Y)`」降到「讀一個名詞」。
- **命名精準**：`transform`（轉換）貼合不可變語境，不再暗示就地修改。
- **有錨點**：doc comment 的範例讓第一次使用者立即知道怎麼傳。
- **錯誤訊息更易讀**：型別對不上時，編譯器印的是 `SettingsMutator` 這個名字，而不是整串 `SettingsModel Function(SettingsModel)`；裸寫版的錯誤訊息會把完整型別攤開，較難一眼定位。
- **可重用**：同一個 `SettingsMutator` 型別若日後被多個 API 共用，定義集中一處。

### 缺點

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

關鍵：**兩者是同一個 pattern（HOF + ValueNotifier）的兩種表達**。取捨重點在「型別就地可見」對上「簽章簡潔 + 概念命名」—— 當函式型別會被多處使用、或語法門檻造成實際閱讀摩擦時，typedef 划算；若只用一次且團隊熟悉函式型別語法，裸寫也完全合理。

改寫的驗證也印證它停在「表達層」：呼叫端傳 lambda 不依賴參數名 → 零修改；行為不變；全套測試原封不動通過。

---

## 7. 收斂

- HOF 適合的場景特徵：**流程固定 + 變化點單一 + 變化開放**。三者齊備時，把變化點抽成函式參數最省；場景不符（欄位少、流程各異）則具名方法更直白。
- 不可變模型的更新本質就是 `(current) => next`，用函式參數表達是語意上最貼合的形狀。
- 兩種寫法的取捨：裸函式型別型別就地可見、零宣告；typedef 簽章簡潔、命名成概念、可重用，但多一層 indirection。
- 選擇依據：函式型別是否多處共用、語法是否造成實際閱讀摩擦。摩擦明顯就抽 typedef，否則裸寫無妨。

> **延伸**：本文 §3.2「模型不可變」是整個 HOF 適配的前提之一。`SettingsModel` 那種 `@immutable` + `copyWith` 結構怎麼產生、以及更好懂的替代路徑，見 [Freezed 的三層結構解剖](/work-log/dart_freezed_anatomy/)。
