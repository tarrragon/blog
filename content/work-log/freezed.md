---
title: "Freezed 選型評估"
date: 2026-03-26
draft: false
tags: ["flutter", "dart", "freezed", "code-generation"]
---

> **關聯 Ticket**：0.2.0-W5-007
> **決策結論**：移除 freezed，採用 json_serializable + Equatable

<!-- 前言 -->

我設定了一個新的需求開了一個專案，我沒有專門指定開發的框架或者細節，我只有很簡單的先建立我需求的 spec 文件，這個文件當然並不完整，我是希望先讓AI做一個 原形，我會在 prototype 符合我的需求動起來之後再介入去調整設計。

我的初始技術規範就只有我要用 flutter 去寫，所以AI就動了，但是在中間我發現 AI使用了 Freezed ，我並不喜歡在我 build 之外還要做一次
code generation 的動作，所以我就跟AI討論一次關於 Freezed 這種做法的必要性，至少在原形階段我覺得單純一點的 model 檔案沒有什麼不好，也不大會出錯，整體討論下來我選擇 捨棄 已有的 Freezed 程式碼，重構成更簡易的 版本，但是我覺得這個評估還是很有價值，所以讓AI重新整理了一次討論的內容作為備查。

---

## 1. Freezed 是什麼

Freezed 是 Dart 的自動程式碼產生（code generation）套件，專門用來幫你自動生成資料類別（data class）裡那些重複的樣板程式碼（boilerplate），包括：

- `copyWith`：複製一份物件，但可以只改其中幾個欄位，常用在狀態管理時產生新狀態
- `==` / `hashCode`：值相等比較（value equality），讓兩個內容相同的物件被判定為「相等」
- `toString`：把物件轉成易讀的字串，方便除錯
- `fromJson` / `toJson`：JSON 序列化與反序列化，搭配 json_serializable 使用，處理前後端資料交換
- 聯合型別（Union types）/ 密封類別（sealed class）：用 `@freezed` 的多建構子語法，實現型別安全的多態模式

**解決的核心問題**：Dart 的類別預設是可變的（mutable），而且比較兩個物件時只看記憶體位址是否相同（identity equality），不會比較欄位內容。如果要手刻一個有 10 個欄位的不可變資料物件（immutable value object），大約需要 80-120 行程式碼，而且每次修改欄位都要同步更動 6 個地方（欄位宣告、建構子、`copyWith`、`==`、`hashCode`、`toJson`），非常容易漏改出錯。

---

## 2. 優缺點分析

### 優點

| 功能                 | 說明                                          | 受益程度                 |
| -------------------- | --------------------------------------------- | ------------------------ |
| copyWith             | 建立修改後的新實例，State 管理必備            | 高（State 類別頻繁使用） |
| == / hashCode        | Value equality，Riverpod 用於判斷狀態是否變更 | 中                       |
| fromJson / toJson    | JSON 序列化，WebSocket 通訊必備               | 高                       |
| Immutability 保證    | 編譯期強制不可變                              | 中                       |
| Union types / sealed | 型別安全的多態模式                            | 視需求（本專案未使用）   |

### 缺點

| 問題              | 說明                                                          | 影響程度       |
| ----------------- | ------------------------------------------------------------- | -------------- |
| build_runner 依賴 | 每次改模型需執行 `dart run build_runner build`                | 高（開發體驗） |
| 生成檔案膨脹      | 12 個類別產生約 20 個 `.freezed.dart` / `.g.dart` 檔案        | 中             |
| 編譯時間          | code generation 拖慢整體編譯                                  | 中             |
| 學習成本          | 需理解 `part`、`_$ClassName`、code generation 機制            | 中（新手門檻） |
| 版本耦合          | freezed 3.x + json_serializable + build_runner 三者版本需相容 | 高（升級風險） |

---

## 3. 適用場景判斷表

| 指標             | 適合 freezed                     | 不需要 freezed                   |
| ---------------- | -------------------------------- | -------------------------------- |
| 模型數量         | 50+ 個                           | < 20 個                          |
| 欄位變動頻率     | 頻繁新增/修改欄位                | 欄位穩定（如對應後端 struct）    |
| Union types 需求 | 大量使用（BLoC State/Event）     | 無或極少                         |
| 巢狀 copyWith    | 深層巢狀物件需逐層複製           | 結構扁平                         |
| 團隊規模         | 多人協作，需統一生成減少出錯     | 小團隊或個人                     |
| 狀態管理         | BLoC（State/Event union 是標配） | Riverpod（不依賴 union）         |
| Dart 版本        | < 3.0（無原生 sealed class）     | >= 3.0（原生 sealed class 可用） |

---

## 4. 替代方案比較

| 方案                             | 描述                                                   | copyWith              | == / hashCode                         | JSON                     | 維護成本 | code gen |
| -------------------------------- | ------------------------------------------------------ | --------------------- | ------------------------------------- | ------------------------ | -------- | -------- |
| A：維持 freezed                  | 現狀不變                                               | 自動                  | 自動                                  | 自動                     | 低       | 需要     |
| B：json_serializable + Equatable | 保留 JSON 生成，手寫 copyWith，Equatable 處理 equality | 手寫（僅 2 個 State） | Equatable（零 code gen）              | 自動                     | 中       | 僅 JSON  |
| C：完全手寫                      | 移除所有 code generation                               | 手寫                  | 手寫                                  | 手寫                     | 高       | 不需要   |
| D：Dart 3 原生特性               | 使用 `sealed class` + `record` + `final class`         | 手寫                  | record 自帶；class 需手寫或 Equatable | 手寫或 json_serializable | 中       | 可選     |

### 方案 B 詳細說明（本專案推薦）

- **JSON 序列化**：保留 json_serializable（10 個模型仍需 `fromJson` / `toJson`），build_runner 僅用於 JSON
- **Value equality**：使用 Equatable 套件，繼承 `Equatable` 並宣告 `props` 即可，零 code generation
- **copyWith**：僅 2 個 State 類別（SessionListState、ConversationState）需要，手寫工作量極小
- **Immutability**：使用 `final` 欄位 + 命名建構子，Dart 語言層級保證

### 方案 D 補充說明（Dart 3 原生特性）

Dart 3.0+ 引入的原生特性可部分替代 freezed：

| Dart 3 特性             | 替代 freezed 功能           | 限制                       |
| ----------------------- | --------------------------- | -------------------------- |
| `sealed class`          | Union types / when / switch | 不自動生成 copyWith、==    |
| `final class`           | Immutability 保證           | 不自動生成 boilerplate     |
| Records `(int, String)` | 輕量 value type（自帶 ==）  | 無命名欄位語法糖有限       |
| Pattern matching        | exhaustive switch           | 僅用於控制流，不生成程式碼 |

---

## 5. 與狀態管理框架的關係

### Riverpod 的 Value Equality 機制

**常見誤解**：「Riverpod 需要 freezed 才能正確判斷狀態變更」。

**事實釐清**：

1. Dart 預設是 **identity equality**（比較記憶體位址）。兩個欄位完全相同的新物件，`==` 仍為 `false`
2. Riverpod 在 `state = newValue` 時使用 `==` 判斷是否通知 listener rebuild。相同則不通知
3. Riverpod **本身不做任何額外 equality 優化**，完全依賴物件自身的 `==` 運算子

### 此專案的實際影響

在本專案中，不使用 value equality 的影響極小：

| 因素            | 說明                                                                   |
| --------------- | ---------------------------------------------------------------------- |
| 狀態更新來源    | 每次都是收到 WebSocket 新訊息才更新，值幾乎必然不同                    |
| AsyncData 包裝  | Riverpod 的 `AsyncData` 每次都是新實例，外層已經不等                   |
| UI rebuild 成本 | Flutter 本身的 Widget diff 機制已足夠高效，多餘 rebuild 不構成效能問題 |

**結論**：Equatable 零 code generation 即可解決 value equality 需求。在本專案場景下，甚至完全不處理也感受不到效能差異。

---

## 6. 決策流程

```text
是否需要 freezed?
    |
    v
模型數量 > 50?
    +-- 是 --> 強烈建議使用 freezed
    +-- 否 ↓
    |
使用 union types / sealed class?
    +-- 大量使用 --> 建議使用 freezed（或 Dart 3 sealed class）
    +-- 未使用 ↓
    |
欄位頻繁變動?
    +-- 是 --> 建議使用 freezed（減少同步維護）
    +-- 否 ↓
    |
需要深層巢狀 copyWith?
    +-- 是 --> 建議使用 freezed
    +-- 否 ↓
    |
需要 JSON 序列化?
    +-- 是 --> json_serializable 即可
    +-- 否 ↓
    |
需要 value equality?
    +-- 是 --> Equatable 或手寫 ==
    +-- 否 --> 完全不需要 freezed
```

---

## 7. 本專案評估結論

### 現況盤點

| 項目             | 數量  | 說明                                 |
| ---------------- | ----- | ------------------------------------ |
| `@freezed` 類別  | 12 個 | 規模小                               |
| 資料模型（JSON） | 10 個 | SessionInfo, SessionEvent 等         |
| UI State         | 2 個  | SessionListState, ConversationState  |
| Union types 使用 | 0 個  | 未使用 freezed 殺手功能              |
| 巢狀 copyWith    | 0 處  | 結構扁平                             |
| 欄位變動頻率     | 低    | 對應 Go struct，後端穩定後前端不常改 |

### 評估對照

| 指標          | 本專案狀況           | 結論   |
| ------------- | -------------------- | ------ |
| 模型數量      | 12 個（< 20）        | 不需要 |
| 欄位穩定度    | 對應 Go struct，穩定 | 不需要 |
| Union types   | 0 個                 | 不需要 |
| 狀態管理      | Riverpod（非 BLoC）  | 不需要 |
| 巢狀 copyWith | 無                   | 不需要 |
| 團隊規模      | 小                   | 不需要 |

### 決策

**移除 freezed，採用方案 B**：保留 json_serializable 處理 JSON 序列化，使用 Equatable 處理 value equality，手寫 copyWith（僅 2 個 State 類別）。

**理由**：freezed 在本專案中只用到最基礎功能（copyWith、==、JSON），全部可被更輕量的方案替代。移除後減少 build_runner 依賴範圍、消除生成檔案膨脹、降低版本耦合風險。

---

## 8. 遷移檢查清單

### 準備階段

- [ ] 確認所有 `@freezed` 類別清單（12 個）
- [ ] 備份現有生成檔案
- [ ] 確認 json_serializable 獨立使用的配置方式

### 資料模型遷移（10 個）

- [ ] 移除 `@freezed` 註解，改為 `@JsonSerializable` + `final class`
- [ ] 保留 `part '*.g.dart'`（json_serializable 仍需要）
- [ ] 移除 `part '*.freezed.dart'`
- [ ] 繼承 `Equatable`，宣告 `props`
- [ ] 手寫建構子（`const` 建構子 + `final` 欄位）
- [ ] 確認 `fromJson` / `toJson` 正常運作

### UI State 遷移（2 個）

- [ ] 同上資料模型遷移步驟
- [ ] 手寫 `copyWith` 方法
- [ ] 確認 Riverpod 狀態更新行為正確

### 清理階段

- [ ] 刪除所有 `.freezed.dart` 生成檔案
- [ ] 從 `pubspec.yaml` 移除 `freezed` 和 `freezed_annotation` 依賴
- [ ] 執行 `dart run build_runner build` 確認 json_serializable 正常
- [ ] 執行全量測試確認無回歸
- [ ] `dart analyze` 0 issues

---

## 參考資源

- [freezed 套件](https://pub.dev/packages/freezed)
- [json_serializable 套件](https://pub.dev/packages/json_serializable)
- [equatable 套件](https://pub.dev/packages/equatable)
- [Dart 3 Patterns and Sealed Classes](https://dart.dev/language/patterns)

---

**Last Updated**: 2026-03-26
**Version**: 1.0.0
