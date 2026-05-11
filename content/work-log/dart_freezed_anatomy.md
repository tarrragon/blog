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

短短四行裡塞了一堆陌生語法——`abstract` 為什麼能配 `factory`、`with _$DailySettlementRow` 在做什麼、`_$` 這個前綴是什麼意思、`= _DailySettlementRow` 是什麼魔法、為什麼要分成「我寫的 abstract」+「生成的 mixin」+「生成的具體類」三層。

不查清楚每次看到都會被打斷一次。整理成筆記。

---

## 第一層：`with` 是什麼

`with` 是 Dart 的 **mixin 語法**、把另一個型別的成員「混入」當前 class。當前 class 就會擁有那些成員、不必自己寫實作。

### 三個關鍵字的差異

```dart
abstract class DailySettlementRow
    with _$DailySettlementRow         // ← mixin：拿到實作
    implements SettlementAmountsView  // ← interface：拿到契約
```

| 關鍵字       | 拿到什麼            | 是否要自己寫實作   |
| ------------ | ------------------- | ------------------ |
| `extends`    | 繼承父類別（單一）  | 可選擇覆寫         |
| `implements` | 只拿型別契約        | **要自己全部實作** |
| `with`       | 拿到 mixin 內的實作 | 自動有實作、可覆寫 |

`extends` 最強硬（佔據獨一無二的父類別位置）、`implements` 最寬鬆（只是契約）、`with` 在中間（拿實作但不佔父類別）。

### 在 freezed 中的角色

`_$DailySettlementRow` 是 build_runner 跑完後在 `daily_settlement_dto.freezed.dart` 裡產出的 mixin、幫你寫好了：

- 所有 `final` 欄位的 getter（`date`、`cash`、`tc` 等）
- `==` 和 `hashCode`
- `copyWith`
- `toString`
- `toJson` / `fromJson` 的接口

所以 `abstract class DailySettlementRow with _$DailySettlementRow` 在做的事是：

> 「我這個 class 是 abstract 的、但 freezed 已經幫我把所有實作放在 `_$DailySettlementRow` mixin 裡了、我直接 `with` 進來、就立刻擁有完整功能。」

### 為什麼 freezed 用 mixin 而不是 extends

- **mixin 不佔「父類別」的獨生子位置**：Dart 只允許單一 `extends`、freezed 如果用 extends 強佔了、你就不能讓 model 繼承自己的 base class。`with` 可以無限疊加、給你自由度
- **mixin 支援多個疊加**：`class Foo with A, B, C` 會把 A、B、C 的方法依序混入。Freezed 利用這點、把不同責任（equality、json、copyWith）分散在多個 mixin 裡組合
- **`implements SettlementAmountsView` 在這裡剛好成立**：因為 `_$DailySettlementRow` 提供了所有 `date / cash / tc / ...` 的 getter 實作、剛好涵蓋了 `SettlementAmountsView` 介面要求的成員、所以 `implements` 不需要我們手動寫一份 getter——「介面契約」被「mixin 的實作」自動滿足了。這是為什麼我們敢加 `implements` 而不會被編譯器罵「沒實作 18 個 getter」

### 簡化的等價心智模型

```dart
// 你寫的：
abstract class DailySettlementRow
    with _$DailySettlementRow
    implements SettlementAmountsView { ... }

// 大致等於（觀念上）：
abstract class DailySettlementRow implements SettlementAmountsView {
  // 把 _$DailySettlementRow 裡的東西「複製」進來
  @override String get date => ...;
  @override Decimal get cash => ...;
  @override Decimal get tc => ...;
  // ... 等等所有 freezed 產出的東西
}
```

只是你不用真的去複製、`with` 在編譯期幫你接上。

---

## 第二層：`_$` 命名約定

第一次看到 `_$DailySettlementRow` 會以為這是某個 framework 的魔法符號。實際上是**兩個獨立慣例疊加**的結果。

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

**前 3 行是真實需求；最後一行是「為了實現前 3 行、Dart 缺工具、所以要組裝」。**

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

有、誠實說：

- **`part` directive 是「漏出來的實作細節」**：使用者必須知道 library / part 的概念才能寫對。一個好抽象不該讓你看到底下的機器。但 freezed 只能用 part、否則 `_$Foo` 在外部 library 看不見——這是 Dart 限制逼出來的
- **`with _$Foo` 暴露了「我是 codegen」**：理想中 `@freezed` 應該是個透明的標註、使用者只寫資料形狀就好。但因為 Dart 沒有 macro（直到 2024 才實驗性引入）、freezed 必須讓使用者自己把生成的 mixin「接上去」
- **`abstract class` + `factory` 的怪異組合**：abstract class 不能直接 `new`、但 `factory` 可以回傳具體子類（freezed 產的 `_DailySettlementRow`）。功能對、但對新人來說「一個 abstract class 居然能被建構」是反直覺的

### 那「設計得不當」的真正主體是誰

層層往下追：

1. **你的 model 設計？** → 沒有不當。你只是宣告「這是 immutable record」
2. **Freezed 的設計？** → 受限於 Dart、這已經是合理的妥協
3. **Dart 的設計？** → **這裡才是真正的根因**：
   - 直到 2024 才開始實驗性引入 [macros](https://dart.dev/language/macros)
   - 直到 Dart 3（2023）才有 sealed class、pattern matching、records
   - records 是 immutable + value equality、但只是 tuple-like、沒辦法有 named class 名字（不能 `extends`、不能加方法）
   - 換句話說 Dart 用了快 10 年才補上其他語言一開始就有的能力

### 未來會變好嗎

會。**Freezed 的 maintainer 已經公開表態要遷到 Dart macros**。屆時寫的會大致變成：

```dart
@Data()
class DailySettlementRow implements SettlementAmountsView {
  final String date;
  final Decimal cash;
  // ... 18 個欄位
}
// 不需要 part、不需要 with _$、不需要 abstract、不需要 factory
// 編譯期 macro 直接展開所有 boilerplate
```

到那時才會說：「原來之前的拆是不必要的」。在 Dart macro 穩定之前、**現在的拆是『能寫得出來的最少拆』**。

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

Record 是 Dart 3 內建的不可變值型別：

- ✅ 自動 `==` / `hashCode` / `toString`
- ✅ 不可變
- ❌ 無名 → 不能 `implements SettlementAmountsView`、不能加方法、不能 `extends`
- ❌ JSON 還是要手寫
- ❌ 沒有 named constructor → 無法做「from raw API JSON」的轉換邏輯

對「跨模組共享、需要實作介面、需要 fromJson」的 DTO、record 不夠用。對「函式內部短暫的多回傳值」、record 完美。

---

## 真正該問的問題：你需要的是哪幾項

回頭把「freezed 給你的功能」拆開看、對 DTO 真正用得到的有：

| 功能                  | DTO 真的需要嗎 | 為什麼                                               |
| --------------------- | -------------- | ---------------------------------------------------- |
| `fromJson` / `toJson` | ✅ 必要        | 後端來的 raw JSON、必須轉成型別                      |
| Immutable（`final`）  | ✅ 必要        | DTO 被多處引用、可變會引入難追的 bug                 |
| `==` / `hashCode`     | ⚠️ 看用法       | 若放進 `RxBool`、`Set`、`Map` 才需要；單純傳遞用不到 |
| `copyWith`            | ❌ 通常不需要  | DTO 從 API 來就餵給 domain layer、本來就不該被修改   |
| Sealed union          | ❌ 不需要      | DTO 是固定形狀、不是「多種變體擇一」                 |
| `toString` 除錯       | ⚠️ 看情境       | 開發 / 除錯時方便、prod 用不到                       |

**真實的需求只有兩項：JSON 轉換 + immutable**。其他都是 freezed 順手送的。

### 過剩功能不是壞事、但會誤導

用了 freezed 後會傾向「reach for `copyWith`」、因為它就在那。如果一開始只用 `json_serializable`、可能根本不會在 DTO 上做修改——而那才是正確的 DTO 用法（DTO 是 API 邊界的「快照」、不該被修改、要改就轉成 domain model 再改）。

### Freezed 真正的價值在 domain model、不在 DTO

Domain 物件（如 `ShoppingCart`、`Order`）有大量「在現有狀態上做小修改」的場景、這時 `copyWith` + sealed union 才賺得回來那層拆分成本。

---

## 規劃有沒有瑕疵

整體判斷：**規劃沒瑕疵、但有兩個值得反思的點**。

### 1. 工具選擇是「一致性 vs 適配度」的取捨

整個 codebase 用 freezed 的好處：

- ✅ **一致性**：所有 model 一樣寫、新人不用學兩套
- ✅ **未雨綢繆**：今天 DTO 不需要 `copyWith`、明天可能要（例如做 optimistic update 時要短暫修改 DTO）
- ✅ **降低決策成本**：不用每個 model 問「這個需要 copyWith 嗎？」

壞處：

- ❌ DTO 上「邊際過剩」：用不到的功能也產出來、多花 build_runner 時間
- ❌ 抽象洩漏：使用者必須懂 `_$` / `part` / mixin

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

**對金融 / POS 場景、這層分離幾乎一定要做**。對玩具 app 或快速 prototype、這層分離是 over-engineering。

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

1. **「拆」不是設計不當、是 Dart 在 immutability / macros 上歷史性能力不足的產物**——freezed 在這個現實下做了最好的設計、但它確實揭露了 Dart 的能力缺口
2. **`with _$Foo` 和 `part` 是「漏出來的實作細節」**——好的抽象不該逼使用者懂 library 系統和 mixin、但 Dart 沒給 freezed 別的選擇
3. **對 DTO 用 freezed 是「邊際過剩」、對 domain model 才是「剛剛好」**——但統一用 freezed 換來的一致性、在長期維護的專案上值得
4. **Dart macros 穩定後這層討論會自然消失**——屆時 `@Data` 標記就完事、三層拆分變一行
5. **真正的瑕疵不在這層**——而在 Dart 直到 2024 還在補其他語言 2015 年就有的能力。Freezed 是這個時代下、能寫出來的最好版本

換個角度說：**當你寫 `with _$DailySettlementRow` 時、你不是在用一個複雜的工具、你是在替 Dart 語言補上 10 年前就該有的能力**。

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

關鍵點：**因為 freezed 用 mixin 提供 getter、可以安全地 `implements` 一個純抽象介面**——這是 Dart 對 freezed 的 idiomatic 用法、但前提是你要懂上面四層拆解。寫完這篇筆記後、這個用法的代價終於可以講得清楚。

---

## 參考資料

- [freezed 套件](https://pub.dev/packages/freezed)
- [Dart language tour - Mixins](https://dart.dev/language/mixins)
- [Dart language tour - Libraries and imports](https://dart.dev/language/libraries)
- [Dart 3 macros（實驗性）](https://dart.dev/language/macros)
- [Dart Records](https://dart.dev/language/records)
- [既有的 freezed 選型評估筆記](../freezed/)
