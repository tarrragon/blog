---
title: "Freezed 的三層結構解剖：with、_$、以及更好懂的替代路徑"
date: 2026-05-11
draft: false
description: "freezed `class X with _$X implements Y` 的分層結構解剖：`with` 與 `_$` 各自的角色、沒有 freezed 怎麼手做、中間投影物件 vs DTO 直接 implements 的維護取捨。"
tags: ["dart", "flutter", "freezed", "code-generation", "language-design"]
---

> **觸發場景**：實作營運端報表 API、寫了一個 freezed model
> **疑問來源**：`abstract class PeriodReportRow with _$PeriodReportRow implements ReportAmountsView` 這一行包含太多陌生語法
> **整理目的**：把「為什麼長這樣」與「是否有更好懂做法」的脈絡記錄下來、避免下次又從零開始查
> **本文邊界**：這是一篇 work-log，目標是回溯一次具體實作中的理解成本；它不取代 freezed 官方文件，也不把某個專案的模型分層當成通用規則。

---

## 事件起點

今天在某個營運端 Flutter 專案新增週期彙總報表 API，這份報表和既有的單次作業報表共用呈現邏輯、各自有獨立的 DTO。為了讓兩個 DTO 共用 sections builder、抽了一個 `ReportAmountsView` 介面、讓兩邊的 `*Row` 都 `implements` 它。

寫完後盯著這行程式碼看了一下：

```dart
@freezed
abstract class PeriodReportRow
    with _$PeriodReportRow
    implements ReportAmountsView {
  const factory PeriodReportRow({
    required String date,
    // ... 18 個欄位
  }) = _PeriodReportRow;
}
```

短短四行裡塞了好幾個需要分層理解的語法：`abstract` 為什麼能配 `factory`、`with _$PeriodReportRow` 在做什麼、`_$` 這個前綴代表什麼、`= _PeriodReportRow` 如何接到生成類，以及為什麼要分成「我寫的 abstract」+「生成的 mixin」+「生成的具體類」三層。

這篇筆記把那次停下來查證的路徑整理成可重讀的判斷脈絡。

---

## 第一層：`with` 是什麼

`with` 是 Dart 的 **mixin 語法**、把另一個型別的成員「混入」當前 class。當前 class 會接上 mixin 提供的成員；如果 mixin 宣告了抽象成員，最後的具體類仍要提供實作。

### 三個關鍵字的差異

```dart
abstract class PeriodReportRow
    with _$PeriodReportRow         // ← mixin：接上生成 API surface
    implements ReportAmountsView  // ← interface：拿到契約
```

| 關鍵字       | 拿到什麼                        | 是否要自己寫實作                |
| ------------ | ------------------------------- | ------------------------------- |
| `extends`    | 繼承父類別（單一）              | 可選擇覆寫                      |
| `implements` | 只拿型別契約                    | **要自己全部實作**              |
| `with`       | 拿到 mixin 成員，可含實作或要求 | 取決於 mixin 內的成員是否已實作 |

`extends` 佔據唯一父類別位置，適合真正的 is-a 關係；`implements` 只拿契約，適合用型別描述能力；`with` 在中間，適合把一組生成或共用的成員接到 class 上。

### 在 freezed 中的角色

`_$PeriodReportRow` 是 build_runner 跑完後在 `period_report_dto.freezed.dart` 裡產出的 mixin，角色是把 Freezed 生成的 API surface 接到你宣告的 `PeriodReportRow` 門面上。

- 欄位 getter 的契約或 forwarding surface（`date`、`grossAmount`、`channelA` 等）
- `==` 和 `hashCode` 相關生成邏輯
- `copyWith`
- `toString`
- JSON 相關的 generated function / method 接線（取決於是否搭配 `json_serializable` 與 `fromJson` factory）

所以 `abstract class PeriodReportRow with _$PeriodReportRow` 在做的事是：

> 「我這個 class 是抽象門面，Freezed 會把生成 API 放在 `_$PeriodReportRow` mixin 與 `_PeriodReportRow` 具體類裡；門面透過 `with` 接上生成 surface，factory 再回傳真正持有欄位的生成類。」

這裡最容易誤解的是「mixin 等於所有實作」。在 Freezed 的常見生成模式裡，mixin 會宣告或提供部分生成成員，真正持有 `final` 欄位並滿足 getter 的通常是 factory 指向的 `_PeriodReportRow` 具體類。`with _$PeriodReportRow` 的價值是讓門面型別擁有一致的生成 API 形狀，而不是把每個欄位的儲存都塞進 mixin。

### 為什麼 freezed 用 mixin 而不是 extends

- **mixin 不佔「父類別」的獨生子位置**：Dart 只允許單一 `extends`、freezed 如果用 extends 強佔了、你就不能讓 model 繼承自己的 base class。`with` 可以無限疊加、給你自由度
- **mixin 支援多個疊加**：`class Foo with A, B, C` 會把 A、B、C 的方法依序混入。Freezed 利用這個語法位置，把生成 API 接到使用者宣告的門面類
- **`implements ReportAmountsView` 在這裡剛好成立**：`ReportAmountsView` 要求的是一組 getter 契約，而 Freezed 會讓生成的 `_PeriodReportRow` 具體類依照 factory 參數產生對應欄位。門面類宣告 `implements`，具體類回傳時提供欄位實作，所以不需要再手寫 18 個 forwarding getter

### 簡化的等價心智模型

```dart
// 你寫的：
abstract class PeriodReportRow
    with _$PeriodReportRow
    implements ReportAmountsView { ... }

// 大致等於（觀念上）：
abstract class PeriodReportRow implements ReportAmountsView {
  // 門面接上 generated API surface：
  PeriodReportRow copyWith(...);
}

class _PeriodReportRow implements PeriodReportRow {
  // 具體生成類持有欄位並滿足 interface getters：
  @override final String date;
  @override final Decimal grossAmount;
  @override final Decimal channelA;
  // ... 等等所有 factory 參數對應的欄位
}
```

這是心智模型：`with` 接上 generated surface，`factory = _PeriodReportRow` 接到真正的資料承載類。

---

## 第二層：`_$` 命名約定

第一次看到 `_$PeriodReportRow` 容易以為這是某個 framework 的特殊符號。實際上是**兩個獨立慣例疊加**的結果。

### `_` 和 `$` 各自的角色

| 符號 | 來源                                                                  | 意義                                                |
| ---- | --------------------------------------------------------------------- | --------------------------------------------------- |
| `_`  | **Dart 語言本身**的規則                                               | 開頭底線 = library-private、只有同個 library 看得到 |
| `$`  | **codegen 工具的慣例**（freezed、json_serializable、retrofit 都遵守） | 「這個名字是機器產的、請別自己取一樣的名字」        |

組合起來：

- `_$PeriodReportRow` → 機器產的 + 只給內部用（你不該在外部檔案引用它）
- `$PeriodReportRowCopyWith` → 機器產的 + 公開介面（呼叫 `instance.copyWith(...)` 時要看得到型別）

兩個前綴分別代表不同意圖——freezed 透過 `_` 的有無、區分「實作細節」跟「公開介面」。

### `_$Foo` 為什麼你的檔案看得到

Dart 的 library-private（`_` 前綴）並非「檔案私有」、是「**library 私有**」。預設一個 `.dart` 檔就是一個 library、但 **`part` 指令會把多個檔案併成同一個 library**。

freezed model 檔案開頭那兩行：

```dart
part 'period_report_dto.freezed.dart';
part 'period_report_dto.g.dart';
```

就是在說：「這三個檔屬於同一個 library」。

結果：generated 檔裡的 `_$PeriodReportRow` 雖然 `_` 開頭、但因為 `part` 連通、你的主檔還是看得見、可以 `with` 它。其他 import 你檔案的人就看不到、正好符合「只給內部生成檔用」的意圖。

這也是為什麼**忘記寫 `part 'xxx.freezed.dart';` 會編譯失敗**——不是因為「找不到檔案」、是因為「`_$Foo` 不在同一個 library 內、外部不能引用」。

### 一個快速辨認方式

下次看 freezed / codegen 產出的名字、可以這樣判斷：

- `_$Foo` → mixin / 實作類（內部用）
- `$Foo` → public 介面（給外部呼叫）
- `_Foo` → 純內部 class（如 `_PeriodReportRow` 是 freezed 為你的 factory 產的具體類）
- `Foo` → 你自己寫的 abstract class、是門面（facade）

所以這次寫的：

```dart
abstract class PeriodReportRow with _$PeriodReportRow implements ReportAmountsView
//             ↑ 門面            ↑ 內部 mixin           ↑ 你定義的介面
```

三層責任可以被辨認：你自己寫的門面類、機器產的實作、你自己定義的契約。它不是透明抽象，因為使用者仍要看懂 `part`、`with _$Foo` 與 factory redirect 這些接線。

---

## 第三層：為什麼要這樣拆——是設計不當嗎

`with _$Foo` 加 `part` 加 `abstract class` 加 `factory` 加 `_$ / $ / _ / 無前綴` 四種命名……理解到這裡會自然冒出一個問題：**這個拆分本身、是不是 freezed 設計不當？**

我的看法：**這個拆分不是 freezed 設計不當、但它確實暴露了 Dart 語言層的能力缺口**。換個角度、「需要這樣拆」是症狀、不是病因——病因在語言本身。

### 拆分到底解決了什麼問題

把那幾個元素還原成「想做的事 vs 不得不這樣寫」：

| 想做的事                                         | 在 Dart 中需要的東西                     | 為什麼要拆                                                    |
| ------------------------------------------------ | ---------------------------------------- | ------------------------------------------------------------- |
| 不可變 class DTO + `copyWith`                    | `==`、`hashCode`、`toString`、`copyWith` | Dart 有 records，但沒有能取代 class DTO 的 nominal data class |
| JSON 序列化                                      | `fromJson` / `toJson`                    | Dart 沒有 reflection（AOT 砍了）、只能 codegen                |
| Sum types（多個 constructor + pattern matching） | sealed class + 多個 factory              | Dart 3 才有 sealed、pattern matching 也是 Dart 3              |
| 把上面塞進**一個**讓人能寫的 class               | abstract class + mixin + factory         | 這是「組裝零件」的膠水、不是真實功能                          |

前 3 行是真實需求；最後一行是「為了實現前 3 行、Dart 缺工具、所以要組裝」。

### 對比其他語言處理同樣問題

```kotlin
// Kotlin —— 語言內建
data class PeriodReport(val date: String, val grossAmount: BigDecimal)
// copy、equals、hashCode、toString 全部自動、0 行 codegen
```

```rust
// Rust —— derive macro 內建在語言
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
struct PeriodReport { date: String, grossAmount: Decimal }
```

```typescript
// TypeScript —— 結構型別 + 解構即拷貝
type PeriodReport = { date: string; grossAmount: Decimal };
const next = { ...prev, grossAmount: newAmount };  // copyWith 不用存在
```

```swift
// Swift —— struct 是值類型
struct PeriodReport: Codable, Equatable {
    let date: String; let grossAmount: Decimal
}
```

```dart
// Dart 2 —— 你只能這樣寫（沒 freezed 的話）
class PeriodReport {
  final String date;
  final Decimal grossAmount;
  const PeriodReport({required this.date, required this.grossAmount});
  PeriodReport copyWith({String? date, Decimal? grossAmount}) =>
      PeriodReport(date: date ?? this.date, grossAmount: grossAmount ?? this.grossAmount);
  @override bool operator ==(...) => ...;
  @override int get hashCode => ...;
  @override String toString() => ...;
  factory PeriodReport.fromJson(Map<String, dynamic> json) => ...;
  Map<String, dynamic> toJson() => ...;
}
// 18 個欄位 × 6 個樣板 ≈ 150 行手寫、每加一個欄位要改 5 個地方
```

Freezed 是在這個現實下做的工程權衡：**用一個外部工具、把這上百行壓回十幾行宣告**。代價就是看到的「分三層」。

### Freezed 自己有沒有設計可議的地方

Freezed 的設計可議之處集中在抽象洩漏，而不是功能是否成立：

- **`part` directive 是漏出的實作細節**：使用者必須知道 library / part 的概念才能寫對。Freezed 依賴 `part`，是因為生成檔需要和主檔落在同一個 library，讓 `_` 開頭的 generated member 可以被主檔看到
- **`with _$Foo` 暴露了 codegen 接線**：理想上 `@freezed` 只描述資料形狀，使用者不用知道生成 mixin 的名字。現行 codegen surface 需要使用者把生成 mixin 接上去，這就是學習成本來源
- **`abstract class` + `factory` 需要語言模型支撐**：abstract class 不能直接 `new`，但 `factory` 可以回傳具體子類。Freezed 產生 `_PeriodReportRow`，因此這個寫法在語言上成立；直覺成本來自「門面類」和「具體生成類」分離

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
class PeriodReportRow implements ReportAmountsView {
  final String date;
  final Decimal grossAmount;
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
class PeriodReportRow implements ReportAmountsView {
  final String date;
  final int primaryOrderCount;
  final Decimal grossAmount;
  // ... 其他 16 個欄位

  const PeriodReportRow({
    required this.date,
    required this.primaryOrderCount,
    required this.grossAmount,
    // ...
  });

  factory PeriodReportRow.fromJson(Map<String, dynamic> json) {
    return PeriodReportRow(
      date: json['date'] as String,
      primaryOrderCount: json['primary_order_count'] as int,
      grossAmount: jsonToDecimal(json['gross_amount']),
      // ... 重複 18 次
    );
  }

  Map<String, dynamic> toJson() => {
        'date': date,
        'primary_order_count': primaryOrderCount,
        'gross_amount': grossAmount.toString(),
        // ... 重複 18 次
      };

  PeriodReportRow copyWith({
    String? date,
    int? primaryOrderCount,
    Decimal? grossAmount,
  }) =>
      PeriodReportRow(
        date: date ?? this.date,
        primaryOrderCount: primaryOrderCount ?? this.primaryOrderCount,
        grossAmount: grossAmount ?? this.grossAmount,
        // ... 重複 18 次
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PeriodReportRow &&
          other.date == date &&
          other.primaryOrderCount == primaryOrderCount &&
          other.grossAmount == grossAmount;
          // ... 重複 18 次

  @override
  int get hashCode => Object.hash(date, primaryOrderCount, grossAmount /* 18 個 */);

  @override
  String toString() => 'PeriodReportRow(date: $date, ...)';
}
```

**18 個欄位 × 6 個樣板 ≈ 150 行**、每加一個欄位要改 5 處（constructor、fromJson、toJson、copyWith、==、hashCode）。漏改一處 → 隱性 bug。

### 路線二：只 codegen 序列化、其他手寫

只用 `json_serializable`（比 freezed 輕量很多）：

```dart
@JsonSerializable()
class PeriodReportRow {
  final String date;
  @JsonKey(name: 'primary_order_count') final int primaryOrderCount;
  @DecimalConverter() final Decimal grossAmount;
  // ...

  const PeriodReportRow({required this.date, ...});

  factory PeriodReportRow.fromJson(Map<String, dynamic> json) =>
      _$PeriodReportRowFromJson(json);
  Map<String, dynamic> toJson() => _$PeriodReportRowToJson(this);

  // 不寫 ==、hashCode、copyWith
}
```

省掉 fromJson / toJson 的樣板（最容易出錯的部分）、但仍要自己寫 `==` 和 `copyWith`（如果需要）。

### 路線三：Dart 3 Records

```dart
typedef PeriodReportRow = ({
  String date,
  int primaryOrderCount,
  Decimal grossAmount,
  // ...
});

// 建立
final row = (
  date: '2026-05-11',
  primaryOrderCount: 0,
  grossAmount: Decimal.zero,
  // ...
);

// 「copyWith」就是用解構重組
final next = (
  date: row.date,
  grossAmount: newAmount,
  primaryOrderCount: row.primaryOrderCount,
  // ...
);
```

Record 是 Dart 3 內建的不可變值型別，適合短距離攜帶一組值：

- 支援：自動 `==` / `hashCode` / `toString`
- 支援：不可變
- 限制：無名 → 不能 `implements ReportAmountsView`、不能加方法、不能 `extends`
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

### 這次 DTO 只吃到 Freezed 的部分價值

Freezed 在 DTO 上仍有價值，尤其是 immutable、JSON 轉換接線、欄位同步與 `toString` 除錯。這次報表 DTO 的資料流比較單純，主要吃到的是 JSON 轉換與 immutable；`copyWith`、sealed union、複雜狀態轉移這些能力比較像附加值。

Domain 物件（如 `ShoppingCart`、`Order`）常有「在現有狀態上做小修改」或「多種狀態擇一」的場景，這時 `copyWith` 與 sealed union 更容易回收那層拆分成本。比較精確的判斷不是「Freezed 不適合 DTO」，而是「不同 model 層吃到的 Freezed 價值不同」。

---

## 第五層：更好懂的路徑是中間投影物件

重新用 WARP 看這個設計時，決策錨點不是「怎樣讓 builder 少寫一次」，而是「下一個維護者能不能快速看懂資料怎麼從後端 row 變成報表 sections」。如果這個錨點成立，讓 DTO 直接 `implements ReportAmountsView` 的寫法就不一定是最佳答案。

目前的做法把共用點放在 DTO 型別上。兩種報表 row 都是後端 API row，卻為了共用 `_buildGeneralSections` / `_buildAccountSections`，一起實作一個 18 個 getter 的 `ReportAmountsView`。這在型別上可行，但讀者要同時理解 Freezed 生成類、mixin、interface、DTO 與報表 builder，才能知道為什麼這行能編譯。

### 共用 builder 的三個局部方案

| 方案                    | 核心做法                        | 讀者要理解什麼                        | 主要成本                       |
| ----------------------- | ------------------------------- | ------------------------------------- | ------------------------------ |
| 1. DTO 直接實作共用介面 | 兩個 row 都 `implements View`   | Freezed + mixin + interface + builder | 抽象位置偏早，型別關係較難讀   |
| 2. 直接重複兩份 builder | 兩種報表各自寫 sections builder | 每個 builder 自己讀自己的 row         | 重複邏輯，後續欄位變動要改兩處 |
| 3. 先投影成報表金額模型 | row 先轉 `ReportAmounts`        | API row → 報表金額投影 → sections     | 多一個 model 與兩份 mapping    |

方案 1 是目前寫法。它的優點是 `_buildGeneralSections` / `_buildAccountSections` 可以直接共用，而且沒有額外 mapping；缺點是共用介面綁在 API DTO 上，讓「後端資料形狀」和「報表需要的共同金額視圖」混在同一層。這種寫法對熟悉 Freezed 的人不難，但對第一次接手的人，理解成本集中在一行 class 宣告上。

方案 2 是最直白的寫法。每種報表 row 用自己的 builder，讀者不用理解跨 DTO 介面；缺點是兩份 builder 很容易長得幾乎一樣。當報表欄位增加或文字調整時，維護者要記得同步兩邊，重複會變成一致性風險。

方案 3 把共用點移到更貼近需求的中間層。DTO 仍然只描述 API 回傳形狀，報表 builder 只吃 `ReportAmounts`，兩個 row 各自用 extension 或 mapper 明確轉成報表需要的共同資料。

```dart
class ReportAmounts {
  const ReportAmounts({
    required this.primaryOrderCount,
    required this.primaryTurnover,
    required this.grossAmount,
    // ...其餘報表需要的金額欄位
  });

  final int primaryOrderCount;
  final Decimal primaryTurnover;
  final Decimal grossAmount;
}

extension SingleRunReportRowAmounts on SingleRunReportRow {
  ReportAmounts toAmounts() => ReportAmounts(
        primaryOrderCount: primaryOrderCount,
        primaryTurnover: primaryTurnover,
        grossAmount: grossAmount,
      );
}

extension PeriodReportRowAmounts on PeriodReportRow {
  ReportAmounts toAmounts() => ReportAmounts(
        primaryOrderCount: primaryOrderCount,
        primaryTurnover: primaryTurnover,
        grossAmount: grossAmount,
      );
}
```

這個 mapping 看起來重複，但它是有價值的重複：它明確標出「哪些 API 欄位被投影成報表金額」。後端欄位名稱或語意改變時，維護者會在 mapper 裡看到轉換邊界，而不是在一個 18-getter interface 裡推理兩個 DTO 為什麼剛好長得一樣。

### 重新判斷

以好懂與好維護為核心，方案 3 比方案 1 更穩。它多寫一個 `ReportAmounts` 和兩份 mapping，但把複雜度放在比較合理的位置：DTO 層接 API，projection 層接報表語意，builder 層只處理畫面 / 呈現 sections。

方案 1 可以短期保留，因為它型別安全、改動小、和既有 Freezed 寫法一致。但若這段程式會長期被不同人維護，或未來還會增加其他 report row，應把 `ReportAmountsView` 換成明確的 `ReportAmounts` 投影模型。

實作落地時還有一個命名細節：如果已經從「共用介面」改成「中間投影模型」，檔名也應從 `report_amounts_view.dart` 改成 `report_amounts.dart`。否則程式碼雖然改成 projection，讀者仍會被舊的 View 命名帶回「DTO 實作介面」的心智模型。

### 實作後驗證

這輪實作已經把 `ReportAmountsView` 移除，改成 `ReportAmounts` 投影模型與兩個 `toAmounts()` extension。局部 `flutter analyze` 對修改檔案通過，並補了 `report_amounts_test.dart` 驗證兩種報表 row 的共同金額欄位投影正確。

這個驗證證明 projection 邊界在型別與欄位對應上可行，但它還沒有驗證呈現版面或實際 API response 的完整結果。後續若報表內容有差異，應回到 sections builder 或 API 欄位語意，而不是回頭讓 DTO 重新實作共用介面。

---

## 規劃有沒有瑕疵

整體判斷：**使用 Freezed 本身不是瑕疵，但共用 builder 的抽象位置值得調整**。

### 1. 工具選擇是「一致性 vs 適配度」的取捨

這類專案統一使用 freezed 的收益：

- **一致性**：所有 model 一樣寫，接手者不用學兩套
- **未雨綢繆**：今天 DTO 不需要 `copyWith`、明天可能要（例如做 optimistic update 時要短暫修改 DTO）
- **降低決策成本**：不用每個 model 問「這個需要 copyWith 嗎？」

成本：

- **DTO 上「邊際過剩」**：用不到的功能也產出來、多花 build_runner 時間
- **抽象洩漏**：使用者必須懂 `_$` / `part` / mixin

這個取捨**沒標準答案**、看團隊規模和維護週期。若系統長期維護、多人接手、既有專案已經採用 Freezed、而 build_runner 成本可接受，一致性的價值通常會高於 DTO 上的邊際過剩。

### 2. DTO 與 domain model 兩層分離仍然合理

不在「用了 freezed」、而在於——**是否需要 DTO 與 domain model 兩層分離**？

這類專案結構：

```text
SingleRunReportRow（DTO、貼著 API）
       ↓ service 轉換
ReportSummary（domain、貼著 UI / 呈現）
```

兩層是分開的。這個分層有成本：

- 多寫一個 model
- 多寫一份轉換邏輯
- 多一份要維護

但價值：

- 後端改 API 欄位名 → 只動 DTO 層、domain 不受影響
- UI 要新增顯示邏輯 → 只動 domain 層、DTO 不受影響
- 呈現報表的格式可以脫離 API 變化

對長期維護、資料語意敏感的營運系統，這層分離通常值得；對短期 prototype，這層分離的維護成本可能高於收益。

### 3. 共用 builder 的抽象位置可能放太早

`ReportAmountsView` 把報表需要的共同欄位直接壓到 API DTO 上，這是目前寫法最需要檢討的地方。更清楚的分層是：DTO 先完整接住後端 row，再由 mapper 投影成 `ReportAmounts`，最後由 sections builder 使用這個報表模型。

這個調整不會否定 Freezed，也不會否定 DTO / domain 分層。它只是把「共同報表金額」從 API DTO interface 移到報表投影層，讓型別關係更接近讀者真正要理解的資料流。

### 一個反向思考

如果**沒有 freezed**、會怎麼做？

我猜會：

1. DTO 只用 `json_serializable`（最輕量）
2. domain model 手寫（反正欄位通常比 DTO 少）
3. 用 immutable 慣例但不強制（`final` 欄位 + 沒有 setter）

這樣寫出來會比現在**少一層拆分但多一些手寫樣板**。誰好誰壞、看 trade-off 什麼：

| 維度       | 用 freezed                         | 不用 freezed |
| ---------- | ---------------------------------- | ------------ |
| 寫起來     | 短                                 | 長           |
| 讀起來     | 多層、要懂 mixin                   | 直白         |
| 改起來     | 改一處                             | 改多處       |
| 學習門檻   | 高                                 | 低           |
| 出錯機率   | 欄位同步漏改風險低，但有工具鏈風險 | 手寫易漏改   |
| Build 時間 | 增加 build_runner 成本             | 沒影響       |
| Debug 體驗 | IDE 跳轉差                         | 直接看到     |

---

## 結論

1. **「拆」是 Freezed 在 Dart 現有 codegen surface 下的工程妥協**：它用三層結構換掉大量手寫樣板
2. **`with _$Foo` 和 `part` 是漏出的實作細節**：使用者需要理解 library、mixin、factory redirect，才能讀懂 Freezed 生成模型
3. **不同 model 層吃到的 Freezed 價值不同**：DTO 常吃到 immutable / JSON / 欄位同步，domain model 更容易吃到 `copyWith` / union / 狀態轉移能力；統一用法換來的一致性，在長期維護的專案上可能值得
4. **Dart macros 不是可期待的解法路線**：官方已停止 macros 工作，後續改善更可能來自 data features、build_runner 或 augmentations
5. **真正要檢討的是分層邊界**：DTO 與 domain model 分離是否值得，比 `with _$Foo` 本身更接近架構決策
6. **目前 `implements ReportAmountsView` 可行但不一定最好懂**：若核心目標是長期維護，`ReportAmounts` 投影模型通常比讓 API DTO 直接實作共用介面更清楚；落地時連檔名也要改成 projection 命名，避免舊抽象殘留

換個角度說：當你寫 `with _$PeriodReportRow` 時，你是在接受一個 codegen 工具的心智模型，用它補上資料類型在手寫 Dart 裡會產生的大量樣板。

---

## 附錄：今日實作中相關的設計決策

這次新增週期彙總報表 API 時，面對的關鍵設計選擇是「沿用既有 row、還是新增一個獨立 row」。

當下選擇了新增，然後抽 `ReportAmountsView` 介面共用 sections builder。這個決策當時在 A/B/C 三個選項裡合理，但重新用「好懂、好維護」作為錨點審查後，應該補上第四個選項：

| 選項                                              | 優點                           | 缺點                                                    |
| ------------------------------------------------- | ------------------------------ | ------------------------------------------------------- |
| A. 沿用既有 row、把獨有欄位改 optional            | 共用一個 model、少寫 18 個欄位 | 兩個語意完全不同的東西放在一起、型別會說謊              |
| B. 新增獨立 row、各自獨立                         | 語意清楚、各自演化             | 報表 sections builder 可能重複                          |
| C. 新增 + 抽 `ReportAmountsView` 介面共用 builder | 兼顧 A 的 DRY + B 的清楚       | 多一個 interface 檔案、需理解 Freezed `implements` 用法 |
| D. 新增 + 投影成 `ReportAmounts`                  | DTO 與報表語意分層清楚         | 多一個投影 model 與兩份 mapping                         |

選項 A 的主要問題是型別會說謊。既有 row 有單次作業、操作者、時間等語意，新的 row 是跨作業週期彙總；把兩種欄位塞進同一個 row，會讓 optional 欄位承擔太多語意分支。

選項 B 的主要問題是同步成本。它最容易讀，但如果兩種報表的 sections 幾乎一致，後續調整顯示項目時就要維護兩份相似邏輯。

選項 C 是當下採用的路徑。`ReportAmountsView` 只覆蓋「金額部分」、操作者 / 作業週期 / 日期等識別欄位刻意留給各自的 row 自管，避免介面變成 god interface；但它也讓 API DTO 直接承擔報表共用介面，讀者必須理解 Freezed 的門面類、generated mixin 與具體生成類。

選項 D 是重新審查後更好的候選。它保留兩種報表 row 各自獨立，也保留 sections builder 共用，但把共用點移到 `ReportAmounts` 這個報表投影模型。這樣多寫的 mapping 是刻意暴露資料轉換邊界，而不是無效樣板。

因此，本文更新後的判斷是：**當下選 C 可以理解，但若要讓程式碼更好懂、更好維護，實作上應改成 D**。

---

## 參考資料

- [freezed 套件](https://pub.dev/packages/freezed)
- [Dart language tour - Mixins](https://dart.dev/language/mixins)
- [Dart language tour - Libraries and imports](https://dart.dev/language/libraries)
- [Dart Blog - An update on Dart macros & data serialization](https://dart.dev/blog/an-update-on-dart-macros-data-serialization)
- [Dart Records](https://dart.dev/language/records)
- [既有的 freezed 選型評估筆記](../freezed/)
