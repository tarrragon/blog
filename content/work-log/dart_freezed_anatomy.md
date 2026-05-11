---
title: "Freezed 的三層結構解剖：with、_$、為什麼要這樣拆"
date: 2026-05-11
draft: false
description: "從實作日結 API 時看到的 `abstract class DailySettlementRow with _$DailySettlementRow implements SettlementAmountsView` 出發，解構 freezed 為什麼長這個樣子、`with` 與 `_$` 各自的角色、以及如果沒有 freezed 在 Dart 怎麼做這件事。最後回答一個更深的問題：需要這樣拆是不是設計不當？"
tags: ["dart", "flutter", "freezed", "code-generation", "language-design"]
---

> **觸發場景**：實作 POS 日結 API、寫了一個 freezed model
> **疑問來源**：`abstract class DailySettlementRow with _$DailySettlementRow implements SettlementAmountsView` 這一行包含太多陌生語法
> **整理目的**：把「為什麼長這樣」的脈絡記錄下來、避免下次又從零開始查
> **本文邊界**：這是一篇 work-log，目標是回溯一次具體實作中的理解成本；它不取代 freezed 官方文件，也不把某個 POS 專案的模型分層當成通用規則。

---

## 事件起點

今天在 POS 專案新增日結結算 API，跟交班結算共用領域模型、各自有獨立的 DTO。為了讓兩個 DTO 共用 sections builder、抽了一個 `SettlementAmountsView` 介面、讓兩邊的 `*Row` 都 `implements` 它。

寫完後盯著這行程式碼看了一下：

```dart
@freezed
abstract class DailySettlementRow
    with _$DailySettlementRow
    implements SettlementAmountsView {
  const factory DailySettlementRow({
    required String date,
    // ... 18 個欄位
  }) = _DailySettlementRow;
}
```

短短四行裡塞了好幾個需要分層理解的語法：`abstract` 為什麼能配 `factory`、`with _$DailySettlementRow` 在做什麼、`_$` 這個前綴代表什麼、`= _DailySettlementRow` 如何接到生成類，以及為什麼要分成「我寫的 abstract」+「生成的 mixin」+「生成的具體類」三層。

這篇筆記把那次停下來查證的路徑整理成可重讀的判斷脈絡。

---

## 第一層：`with` 是什麼

`with` 是 Dart 的 **mixin 語法**、把另一個型別的成員「混入」當前 class。當前 class 就會擁有那些成員、不必自己寫實作。

### 三個關鍵字的差異

```dart
abstract class DailySettlementRow
    with _$DailySettlementRow         // ← mixin：接上生成 API surface
    implements SettlementAmountsView  // ← interface：拿到契約
```

| 關鍵字       | 拿到什麼                        | 是否要自己寫實作                |
| ------------ | ------------------------------- | ------------------------------- |
| `extends`    | 繼承父類別（單一）              | 可選擇覆寫                      |
| `implements` | 只拿型別契約                    | **要自己全部實作**              |
| `with`       | 拿到 mixin 成員，可含實作或要求 | 取決於 mixin 內的成員是否已實作 |

`extends` 佔據唯一父類別位置，適合真正的 is-a 關係；`implements` 只拿契約，適合用型別描述能力；`with` 在中間，適合把一組生成或共用的成員接到 class 上。

### 在 freezed 中的角色

`_$DailySettlementRow` 是 build_runner 跑完後在 `daily_settlement_dto.freezed.dart` 裡產出的 mixin，角色是把 Freezed 生成的 API surface 接到你宣告的 `DailySettlementRow` 門面上。

- 欄位 getter 的契約或 forwarding surface（`date`、`cash`、`tc` 等）
- `==` 和 `hashCode` 相關生成邏輯
- `copyWith`
- `toString`
- `toJson` / `fromJson` 的接口

所以 `abstract class DailySettlementRow with _$DailySettlementRow` 在做的事是：

> 「我這個 class 是抽象門面，Freezed 會把生成 API 放在 `_$DailySettlementRow` mixin 與 `_DailySettlementRow` 具體類裡；門面透過 `with` 接上生成 surface，factory 再回傳真正持有欄位的生成類。」

這裡最容易誤解的是「mixin 等於所有實作」。在 Freezed 的常見生成模式裡，mixin 會宣告或提供部分生成成員，真正持有 `final` 欄位並滿足 getter 的通常是 factory 指向的 `_DailySettlementRow` 具體類。`with _$DailySettlementRow` 的價值是讓門面型別擁有一致的生成 API 形狀，而不是把每個欄位的儲存都塞進 mixin。

### 為什麼 freezed 用 mixin 而不是 extends

- **mixin 不佔「父類別」的獨生子位置**：Dart 只允許單一 `extends`、freezed 如果用 extends 強佔了、你就不能讓 model 繼承自己的 base class。`with` 可以無限疊加、給你自由度
- **mixin 支援多個疊加**：`class Foo with A, B, C` 會把 A、B、C 的方法依序混入。Freezed 利用這個語法位置，把生成 API 接到使用者宣告的門面類
- **`implements SettlementAmountsView` 在這裡剛好成立**：`SettlementAmountsView` 要求的是一組 getter 契約，而 Freezed 會讓生成的 `_DailySettlementRow` 具體類依照 factory 參數產生對應欄位。門面類宣告 `implements`，具體類回傳時提供欄位實作，所以不需要再手寫 18 個 forwarding getter

### 簡化的等價心智模型

```dart
// 你寫的：
abstract class DailySettlementRow
    with _$DailySettlementRow
    implements SettlementAmountsView { ... }

// 大致等於（觀念上）：
abstract class DailySettlementRow implements SettlementAmountsView {
  // 門面接上 generated API surface：
  DailySettlementRow copyWith(...);
}

class _DailySettlementRow implements DailySettlementRow {
  // 具體生成類持有欄位並滿足 interface getters：
  @override final String date;
  @override final Decimal cash;
  @override final Decimal tc;
  // ... 等等所有 factory 參數對應的欄位
}
```

這不是生成檔的逐行還原，而是心智模型：`with` 接上 generated surface，`factory = _DailySettlementRow` 接到真正的資料承載類。

---

## 第二層：`_$` 命名約定

第一次看到 `_$DailySettlementRow` 容易以為這是某個 framework 的特殊符號。實際上是**兩個獨立慣例疊加**的結果。

### `_` 和 `$` 各自的角色

| 符號 | 來源                                                                  | 意義                                                |
| ---- | --------------------------------------------------------------------- | --------------------------------------------------- |
| `_`  | **Dart 語言本身**的規則                                               | 開頭底線 = library-private、只有同個 library 看得到 |
| `$`  | **codegen 工具的慣例**（freezed、json_serializable、retrofit 都遵守） | 「這個名字是機器產的、請別自己取一樣的名字」        |

組合起來：

- `_$DailySettlementRow` → 機器產的 + 只給內部用（你不該在外部檔案引用它）
- `$DailySettlementRowCopyWith` → 機器產的 + 公開介面（呼叫 `instance.copyWith(...)` 時要看得到型別）

兩個前綴分別代表不同意圖——freezed 透過 `_` 的有無、區分「實作細節」跟「公開介面」。

### `_$Foo` 為什麼你的檔案看得到

Dart 的 library-private（`_` 前綴）並非「檔案私有」、是「**library 私有**」。預設一個 `.dart` 檔就是一個 library、但 **`part` 指令會把多個檔案併成同一個 library**。

freezed model 檔案開頭那兩行：

```dart
part 'daily_settlement_dto.freezed.dart';
part 'daily_settlement_dto.g.dart';
```

就是在說：「這三個檔屬於同一個 library」。

結果：generated 檔裡的 `_$DailySettlementRow` 雖然 `_` 開頭、但因為 `part` 連通、你的主檔還是看得見、可以 `with` 它。其他 import 你檔案的人就看不到、正好符合「只給內部生成檔用」的意圖。

這也是為什麼**忘記寫 `part 'xxx.freezed.dart';` 會編譯失敗**——不是因為「找不到檔案」、是因為「`_$Foo` 不在同一個 library 內、外部不能引用」。

### 一個快速辨認方式

下次看 freezed / codegen 產出的名字、可以這樣判斷：

- `_$Foo` → mixin / 實作類（內部用）
- `$Foo` → public 介面（給外部呼叫）
- `_Foo` → 純內部 class（如 `_DailySettlementRow` 是 freezed 為你的 factory 產的具體類）
- `Foo` → 你自己寫的 abstract class、是門面（facade）

所以這次寫的：

```dart
abstract class DailySettlementRow with _$DailySettlementRow implements SettlementAmountsView
//             ↑ 門面            ↑ 內部 mixin           ↑ 你定義的介面
```

三層職責分得很乾淨：你自己寫的門面類、機器產的實作、你自己定義的契約。

---

## 第三層：為什麼要這樣拆——是設計不當嗎

`with _$Foo` 加 `part` 加 `abstract class` 加 `factory` 加 `_$ / $ / _ / 無前綴` 四種命名……理解到這裡會自然冒出一個問題：**這個拆分本身、是不是 freezed 設計不當？**

我的看法：**這個拆分不是 freezed 設計不當、但它確實暴露了 Dart 語言層的能力缺口**。換個角度、「需要這樣拆」是症狀、不是病因——病因在語言本身。

### 拆分到底解決了什麼問題

把那幾個元素還原成「想做的事 vs 不得不這樣寫」：

| 想做的事                                         | 在 Dart 中需要的東西                     | 為什麼要拆                                       |
| ------------------------------------------------ | ---------------------------------------- | ------------------------------------------------ |
| 不可變物件 + `copyWith`                          | `==`、`hashCode`、`toString`、`copyWith` | Dart 沒有 record / data class、必須產生          |
| JSON 序列化                                      | `fromJson` / `toJson`                    | Dart 沒有 reflection（AOT 砍了）、只能 codegen   |
| Sum types（多個 constructor + pattern matching） | sealed class + 多個 factory              | Dart 3 才有 sealed、pattern matching 也是 Dart 3 |
| 把上面塞進**一個**讓人能寫的 class               | abstract class + mixin + factory         | 這是「組裝零件」的膠水、不是真實功能             |

前 3 行是真實需求；最後一行是「為了實現前 3 行、Dart 缺工具、所以要組裝」。

### 對比其他語言處理同樣問題

```kotlin
// Kotlin —— 語言內建
data class DailySettlement(val date: String, val cash: BigDecimal)
// copyWith、equals、hashCode、toString 全部自動、0 行 codegen
```

```rust
// Rust —— derive macro 內建在語言
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
struct DailySettlement { date: String, cash: Decimal }
```

```typescript
// TypeScript —— 結構型別 + 解構即拷貝
type DailySettlement = { date: string; cash: Decimal };
const next = { ...prev, cash: newCash };  // copyWith 不用存在
```

```swift
// Swift —— struct 是值類型
struct DailySettlement: Codable, Equatable {
    let date: String; let cash: Decimal
}
```

```dart
// Dart 2 —— 你只能這樣寫（沒 freezed 的話）
class DailySettlement {
  final String date;
  final Decimal cash;
  const DailySettlement({required this.date, required this.cash});
  DailySettlement copyWith({String? date, Decimal? cash}) =>
      DailySettlement(date: date ?? this.date, cash: cash ?? this.cash);
  @override bool operator ==(...) => ...;
  @override int get hashCode => ...;
  @override String toString() => ...;
  factory DailySettlement.fromJson(Map<String, dynamic> json) => ...;
  Map<String, dynamic> toJson() => ...;
}
// 18 個欄位 × 6 個樣板 ≈ 150 行手寫、每加一個欄位要改 5 個地方
```

Freezed 是在這個現實下做的工程權衡：**用一個外部工具、把這上百行壓回十幾行宣告**。代價就是看到的「分三層」。

### Freezed 自己有沒有設計可議的地方

Freezed 的設計可議之處集中在抽象洩漏，而不是功能是否成立：

- **`part` directive 是漏出的實作細節**：使用者必須知道 library / part 的概念才能寫對。Freezed 依賴 `part`，是因為生成檔需要和主檔落在同一個 library，讓 `_` 開頭的 generated member 可以被主檔看到
- **`with _$Foo` 暴露了 codegen 接線**：理想上 `@freezed` 只描述資料形狀，使用者不用知道生成 mixin 的名字。現行 codegen surface 需要使用者把生成 mixin 接上去，這就是學習成本來源
- **`abstract class` + `factory` 需要語言模型支撐**：abstract class 不能直接 `new`，但 `factory` 可以回傳具體子類。Freezed 產生 `_DailySettlementRow`，因此這個寫法在語言上成立；直覺成本來自「門面類」和「具體生成類」分離

### 那「設計得不當」的真正主體是誰

這個問題要拆成三層看：

1. **你的 model 設計**：宣告一個 immutable DTO 並實作金額視圖契約，這個方向成立
2. **Freezed 的設計**：它用 codegen 換掉大量樣板，代價是 `part`、`with _$Foo`、factory redirect 這些接線露在使用者面前
3. **Dart 的語言能力**：Dart 長期缺少穩定的 data class / static metaprogramming 能力，讓資料模型的重複樣板需要靠 build_runner 與外部 codegen 補齊

### 未來改善方向不是 macros 這條直線

Dart 官方在 2025-01-29 宣布停止 macros 工作，因此「等 Dart macros 穩定後，這層拆分自然消失」已經不是可靠判斷。更務實的觀察是：Dart 仍會改善資料建模與 codegen 體驗，但方向可能是更專門的 data language features、build_runner 改善或 augmentations，而不是通用 macros。

理想中的資料模型語法可能長得像這樣：

```dart
@Data()
class DailySettlementRow implements SettlementAmountsView {
  final String date;
  final Decimal cash;
  // ... 18 個欄位
}
// 目標是讓資料形狀、序列化、value equality、copyWith 更接近語言級宣告
```

這段只能當作「期待中的語言表達能力」，不能當作 Dart 已承諾的 roadmap。對今天的專案來說，Freezed 仍然是把資料模型樣板壓低的成熟工具；它的成本是 build_runner、生成檔、以及本文拆解的三層心智模型。

---

## 第四層：沒有 freezed 怎麼做

如果規劃時就決定不裝 freezed、Dart 怎麼處理「immutable + JSON + copyWith + equality」這組需求？

### 路線一：純手寫

把 freezed 產的東西自己寫一遍：

```dart
class DailySettlementRow implements SettlementAmountsView {
  final String date;
  final int memberOrderCount;
  final Decimal cash;
  // ... 其他 16 個欄位

  const DailySettlementRow({
    required this.date,
    required this.memberOrderCount,
    required this.cash,
    // ...
  });

  factory DailySettlementRow.fromJson(Map<String, dynamic> json) {
    return DailySettlementRow(
      date: json['date'] as String,
      memberOrderCount: json['member_order_count'] as int,
      cash: jsonToDecimal(json['cash']),
      // ... 重複 18 次
    );
  }

  Map<String, dynamic> toJson() => {
        'date': date,
        'member_order_count': memberOrderCount,
        'cash': cash.toString(),
        // ... 重複 18 次
      };

  DailySettlementRow copyWith({
    String? date,
    int? memberOrderCount,
    Decimal? cash,
  }) =>
      DailySettlementRow(
        date: date ?? this.date,
        memberOrderCount: memberOrderCount ?? this.memberOrderCount,
        cash: cash ?? this.cash,
        // ... 重複 18 次
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DailySettlementRow &&
          other.date == date &&
          other.memberOrderCount == memberOrderCount &&
          other.cash == cash;
          // ... 重複 18 次

  @override
  int get hashCode => Object.hash(date, memberOrderCount, cash /* 18 個 */);

  @override
  String toString() => 'DailySettlementRow(date: $date, ...)';
}
```

**18 個欄位 × 6 個樣板 ≈ 150 行**、每加一個欄位要改 5 處（constructor、fromJson、toJson、copyWith、==、hashCode）。漏改一處 → 隱性 bug。

### 路線二：只 codegen 序列化、其他手寫

只用 `json_serializable`（比 freezed 輕量很多）：

```dart
@JsonSerializable()
class DailySettlementRow {
  final String date;
  @JsonKey(name: 'member_order_count') final int memberOrderCount;
  @DecimalConverter() final Decimal cash;
  // ...

  const DailySettlementRow({required this.date, ...});

  factory DailySettlementRow.fromJson(Map<String, dynamic> json) =>
      _$DailySettlementRowFromJson(json);
  Map<String, dynamic> toJson() => _$DailySettlementRowToJson(this);

  // 不寫 ==、hashCode、copyWith
}
```

省掉 fromJson / toJson 的樣板（最容易出錯的部分）、但仍要自己寫 `==` 和 `copyWith`（如果需要）。

### 路線三：Dart 3 Records

```dart
typedef DailySettlementRow = ({
  String date,
  int memberOrderCount,
  Decimal cash,
  // ...
});

// 建立
final row = (
  date: '2026-05-11',
  memberOrderCount: 0,
  cash: Decimal.zero,
  // ...
);

// 「copyWith」就是用解構重組
final next = (
  date: row.date,
  cash: newCash,
  memberOrderCount: row.memberOrderCount,
  // ...
);
```

Record 是 Dart 3 內建的不可變值型別，適合短距離攜帶一組值：

- 支援：自動 `==` / `hashCode` / `toString`
- 支援：不可變
- 限制：無名 → 不能 `implements SettlementAmountsView`、不能加方法、不能 `extends`
- 限制：JSON 還是要手寫
- 限制：沒有 named constructor → 無法做「from raw API JSON」的轉換邏輯

對「跨模組共享、需要實作介面、需要 fromJson」的 DTO，record 的語意承載力不足。對「函式內部短暫的多回傳值」，record 很合適。

---

## 真正該問的問題：你需要的是哪幾項

回頭把「freezed 給你的功能」拆開看、對 DTO 真正用得到的有：

| 功能                  | DTO 需求程度 | 為什麼                                                        |
| --------------------- | ------------ | ------------------------------------------------------------- |
| `fromJson` / `toJson` | 必要         | 後端來的 raw JSON、必須轉成型別                               |
| Immutable（`final`）  | 必要         | DTO 被多處引用、可變會引入難追的 bug                          |
| `==` / `hashCode`     | 看用法       | 若放進 `RxBool`、`Set`、`Map` 才需要；單純傳遞用不到          |
| `copyWith`            | 通常不需要   | DTO 從 API 來就餵給 domain layer，修改通常發生在 domain model |
| Sealed union          | 不需要       | DTO 是固定形狀、不是「多種變體擇一」                          |
| `toString` 除錯       | 看情境       | 開發 / 除錯時方便、prod 用不到                                |

這個 DTO 情境的核心需求是 JSON 轉換與 immutable；其他能力是 Freezed 順手提供的附加價值，是否有用取決於後續資料流。

### 過剩功能不是壞事、但會誤導

用了 freezed 後會傾向「reach for `copyWith`」，因為它就在那。如果一開始只用 `json_serializable`，可能根本不會在 DTO 上做修改。較穩定的 DTO 用法是把 DTO 視為 API 邊界的快照；需要變更行為時，轉成 domain model 再承載狀態變化。

### Freezed 真正的價值在 domain model、不在 DTO

Domain 物件（如 `ShoppingCart`、`Order`）有大量「在現有狀態上做小修改」的場景、這時 `copyWith` + sealed union 才賺得回來那層拆分成本。

---

## 規劃有沒有瑕疵

整體判斷：**規劃沒瑕疵、但有兩個值得反思的點**。

### 1. 工具選擇是「一致性 vs 適配度」的取捨

整個 codebase 用 freezed 的收益：

- **一致性**：所有 model 一樣寫、新人不用學兩套
- **未雨綢繆**：今天 DTO 不需要 `copyWith`、明天可能要（例如做 optimistic update 時要短暫修改 DTO）
- **降低決策成本**：不用每個 model 問「這個需要 copyWith 嗎？」

成本：

- **DTO 上「邊際過剩」**：用不到的功能也產出來、多花 build_runner 時間
- **抽象洩漏**：使用者必須懂 `_$` / `part` / mixin

這個取捨**沒標準答案**、看團隊規模和維護週期。POS 這種長期維護的金融系統、**一致性的價值 > 邊際過剩的成本**。

### 2. 真正可能的「規劃瑕疵」在另一處

不在「用了 freezed」、而在於——**是否需要 DTO 與 domain model 兩層分離**？

我們的 codebase 結構：

```text
RecordSettlementRow（DTO、貼著 API）
       ↓ service 轉換
SettlementSummary（domain、貼著 UI / 列印）
```

兩層是分開的。這個分層有成本：

- 多寫一個 model
- 多寫一份轉換邏輯
- 多一份要維護

但價值：

- 後端改 API 欄位名 → 只動 DTO 層、domain 不受影響
- UI 要新增顯示邏輯 → 只動 domain 層、DTO 不受影響
- 列印報表的格式可以脫離 API 變化

對金融 / POS 場景，這層分離通常值得；對短期 prototype，這層分離的維護成本可能高於收益。

### 一個反向思考

如果**沒有 freezed**、會怎麼做？

我猜會：

1. DTO 只用 `json_serializable`（最輕量）
2. domain model 手寫（反正欄位通常比 DTO 少）
3. 用 immutable 慣例但不強制（`final` 欄位 + 沒有 setter）

這樣寫出來會比現在**少一層拆分但多一些手寫樣板**。誰好誰壞、看 trade-off 什麼：

| 維度       | 用 freezed           | 不用 freezed     |
| ---------- | -------------------- | ---------------- |
| 寫起來     | 短                   | 長               |
| 讀起來     | 多層、要懂 mixin     | 直白             |
| 改起來     | 改一處               | 改多處           |
| 學習門檻   | 高                   | 低               |
| 出錯機率   | 低（codegen 不會錯） | 高（手寫易漏改） |
| Build 時間 | 多幾秒               | 沒影響           |
| Debug 體驗 | IDE 跳轉差           | 直接看到         |

---

## 結論

1. **「拆」不是 model 設計不當，而是 Freezed 在 Dart 現有 codegen surface 下的工程妥協**：它用三層結構換掉大量手寫樣板
2. **`with _$Foo` 和 `part` 是漏出的實作細節**：使用者需要理解 library、mixin、factory redirect，才能讀懂 Freezed 生成模型
3. **對 DTO 用 Freezed 可能是邊際過剩，對 domain model 通常更貼近需求**：但統一用法換來的一致性，在長期維護的專案上可能值得
4. **Dart macros 不是可期待的解法路線**：官方已停止 macros 工作，後續改善更可能來自 data features、build_runner 或 augmentations
5. **真正要檢討的是分層邊界**：DTO 與 domain model 分離是否值得，比 `with _$Foo` 本身更接近架構決策

換個角度說：當你寫 `with _$DailySettlementRow` 時，你是在接受一個 codegen 工具的心智模型，用它補上資料類型在手寫 Dart 裡會產生的大量樣板。

---

## 附錄：今日實作中相關的設計決策

這次新增日結 API 時、面對的關鍵設計選擇是「沿用 `RecordSettlementRow`、還是新增 `DailySettlementRow`」。

選擇了新增、然後抽 `SettlementAmountsView` 介面共用 sections builder。理由與本文的 trade-off 思考一脈相承：

| 選項                                                  | 優點                           | 缺點                                                    |
| ----------------------------------------------------- | ------------------------------ | ------------------------------------------------------- |
| A. 沿用 `RecordSettlementRow`、把獨有欄位改 optional  | 共用一個 model、少寫 18 個欄位 | 兩個語意完全不同的東西放在一起、型別會說謊              |
| B. 新增 `DailySettlementRow`、各自獨立                | 語意清楚、各自演化             | 18 個欄位重複（但 freezed 處理得很好、維護成本低）      |
| C. 新增 + 抽 `SettlementAmountsView` 介面共用 builder | 兼顧 A 的 DRY + B 的清楚       | 多一個 interface 檔案、需理解 freezed `implements` 用法 |

選 C。`SettlementAmountsView` 只覆蓋「金額部分」、員工 / 班次 / 日期等識別欄位刻意留給各自的 row 自管、避免介面變成 god interface。

關鍵點：Freezed 讓門面類接上 generated API surface，並讓 factory 指向的具體生成類持有欄位；因此 `DailySettlementRow` 可以實作 `SettlementAmountsView` 這種純 getter 介面。這是 Dart + Freezed 常見的用法，但前提是你要懂門面、mixin、具體生成類各自承擔什麼責任。

---

## 參考資料

- [freezed 套件](https://pub.dev/packages/freezed)
- [Dart language tour - Mixins](https://dart.dev/language/mixins)
- [Dart language tour - Libraries and imports](https://dart.dev/language/libraries)
- [Dart Blog - An update on Dart macros & data serialization](https://dart.dev/blog/an-update-on-dart-macros-data-serialization)
- [Dart Records](https://dart.dev/language/records)
- [既有的 freezed 選型評估筆記](../freezed/)
