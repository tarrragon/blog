---
title: "型別取代 doc 的收益曲線：強型別語言的 doc 該有多短"
date: 2026-05-05
draft: false
description: "型別系統強化等於 doc 表達力轉移——很多 doc 內容應該下移到型別。整理 null safety / enum / wrapper / Result / typestate 各能消除哪類 doc、型別表達不了的剩餘部分（業務動機、性能、副作用、時序）以及收益曲線的邊際遞減點。"
tags: ["type-system", "documentation", "api-design", "code-quality", "methodology"]
---

> **核心命題**：型別系統強化等於 doc 表達力轉移——很多 doc 內容應該下移到型別。
> **設計原則**：能用型別表達的限制，不要用 doc 表達；doc 是型別表達不了的剩餘資訊的家。

> 本篇是 [函式文件分層設計](../function-doc-layered-design/) 的 Layer 1（名稱與型別簽章）展開——把「型別承擔哪些原本寫在 doc 的內容」拉成獨立主題討論。

---

## 起點：型別越強、doc 的職責範圍就越窄

「型別系統越強、function doc 也越能寫得短」——這是個普遍但不被刻意利用的現象。

當你看到一個 Dart / TypeScript / Rust 的 function doc 寫得跟 Python / JavaScript 一樣長、多半有東西可以下移到型別。把可下移的內容下移、doc 表面變短、實質上的好處更深：

- **編譯期被檢查**——型別說的事不會 outdated（doc 會）
- **IDE 補全提示**——使用者看到型別就懂、不用切到文件頁
- **重構時連動**——改型別會逼所有 caller 跟著改、doc 改了沒人逼你檢查

這篇整理：哪些常見的 doc 內容能被型別取代、哪些下移了會破壞別的東西、以及型別越加越強時要怎麼平衡 ergonomic 跟表達力。

---

## 可被型別取代的常見 doc 內容

下面 8 類 doc 內容、共通特徵是「可以從 doc 約定升級成型別約束」——升級之後、保護從「靠使用者讀並記住」變成「靠編譯器強制」、執行力跟一致性都比 doc 強。每類列出弱（doc 約定）vs 強（型別約束）的對比。

### 1. 「必須是正整數」「必須非空」「必須在範圍內」

```dart
// 弱：依賴 doc 警告
/// [quantity] 必須為正整數（>= 1）
void increase(int quantity) {
  if (quantity < 1) throw ArgumentError(...);
}

// 強：refinement type / value object
class PositiveInt {
  final int value;
  PositiveInt(this.value) {
    if (value < 1) throw ArgumentError(...);
  }
}
void increase(PositiveInt quantity) { ... }

// 最強（語言支援的話）：refinement types
void increase(int quantity) where quantity > 0 { ... }
```

Dart 沒有 native refinement type，但用 wrapper class 一樣能達到「**呼叫端要顯式建構合法值才能呼叫**」的效果。validation 從「呼叫進入 function 後才檢查」前移到「建構 value object 時檢查」，contract 變成型別系統的一部分。

### 2. 「可能為 null」「找不到時回傳 null」

```dart
// 弱（前 null safety 時代）：
/// [name] 可為 null，[email] 不可為 null
class User {
  String? name;
  String email;
}
/// 找不到時回傳 null
User getUser(String id);

// 強（null safety）：
class User {
  String? name;       // 型別已說可為 null
  String email;       // 型別已說不可為 null
}
User? getUser(String id);  // 型別已說可能找不到
```

Dart / TypeScript / Kotlin / Swift 的 sound null safety 把「可為 null」從 doc 約定升級成型別約定——升級之後、「[X] 可為 null」這類 doc 變成 redundant noise（型別已經精準說了、重複寫只是稀釋訊號、改型別時忘了同步 doc 還會誤導讀者）。

### 3. 「會 throw 某 exception」

```dart
// 弱：靠 doc
/// 找不到時 throw [NotFoundException]
/// 網路錯誤時 throw [NetworkException]
Future<User> getUser(String id);

// 強：用 Result / Either / sealed class
Future<Result<User, GetUserError>> getUser(String id);

sealed class GetUserError {}
class NotFoundError extends GetUserError {}
class NetworkError extends GetUserError {
  final int statusCode;
}
```

Result / Either pattern 把 error 從「invisible exception」升級成「型別簽章可見的回傳值」。Caller 必須處理（編譯不過 if not handled），不會漏掉 error path。

代價：寫法比 throw 多一些；不是所有 codebase 都採用這個 pattern。但對核心 service 介面值得。

### 4. 「合法值是 A、B 或 C」

```dart
// 弱：String flag + doc
/// [mode] 可選值：'manual'、'auto'、'hybrid'
void setMode(String mode);

// 強：enum
enum Mode { manual, auto, hybrid }
void setMode(Mode mode);
```

String flag 是「**doc 約束代替型別約束**」的最常見例子。改用 enum 之後：

- IDE 自動補全
- 拼錯立刻編譯錯
- 新增 / 刪除 mode 時所有 caller 編譯出錯（迫使你檢查每個地方該怎麼處理）

### 5. 「狀態 X 才能呼叫」

```dart
// 弱：靠 doc + 執行期檢查
/// 必須在 [open] 之後、[close] 之前呼叫；否則 throw [StateError]
void write(String data);

// 強：typestate / phantom types（Rust 友善，Dart 較吃力）
class OpenConnection { void write(String data) { ... } }
class ClosedConnection { /* no write method */ }

OpenConnection open() { ... }
ClosedConnection close(OpenConnection conn) { ... }
```

typestate 把「必須在某狀態下才能呼叫」變成「**那個狀態才存在那個方法**」。Rust / Haskell 寫起來最自然；Dart / Java 可以用建構子分流模擬，但 ergonomic 較差。

對核心 lifecycle（connection、transaction、stream subscription）值得用；一般 service 不必。

### 6. 「兩個參數互斥」「某參數有時必填」

```dart
// 弱：positional args + doc
/// 同時提供 [token] 和 [credentials] 會 throw
/// 至少要提供一個
User auth(String? token, Credentials? credentials);

// 強：sealed class 表達互斥
sealed class AuthMethod {}
class TokenAuth extends AuthMethod { final String token; }
class CredentialsAuth extends AuthMethod { final Credentials creds; }

User auth(AuthMethod method);
```

「至少一個 / 至多一個 / 互斥」這類條件用 sealed class / discriminated union 表達。caller 看到型別就知道兩條路擇一，不需要 doc 說明組合規則。

### 7. 「這個 collection 是 read-only / 不要修改」

```dart
// 弱：靠 doc 約定
/// 不要修改回傳的 list
List<Item> getItems();

// 強：immutable collection 型別
List<Item> getItems() => List.unmodifiable(_items);
// 或：
Iterable<Item> getItems() => _items;  // Iterable 不暴露 mutation
// 或（用 built_collection）：
BuiltList<Item> getItems();
```

「請別修改」doc 警告靠的是「使用者願意讀且記住」，型別約束是強制的。

### 8. 「測量單位」（公里 vs 英里、秒 vs 毫秒）

```dart
// 弱：靠 doc 標單位
/// [timeout] 單位：毫秒
void setTimeout(int timeout);

// 強：用語義型別
void setTimeout(Duration timeout);
setTimeout(Duration(seconds: 30));  // 不需要記得是哪個單位
```

混淆單位是真實事故來源（Mars Climate Orbiter 級別的）。`Duration` / `Money` / `Distance` 等領域 wrapper 型別把單位編進型別系統，呼叫端不會傳錯。

---

## 型別表達不了的部分（doc 仍是該寫的家）

把可下移的下移之後，doc 還剩什麼？這些是型別表達不了的：

### 1. 業務動機 / 為什麼這個契約存在

```dart
/// 會員價只能用 wallet 付款
/// （業務規則：會員價是 wallet 餘額的折扣回饋）
void chargeMemberPrice(Member m);
```

「為什麼只能用 wallet」是業務規則，不在型別系統的射程內。這類**有來源的業務動機**仍然要寫 doc——但要有來源，不是憑想像。

### 2. 性能特性

```dart
/// O(log n) 查詢；插入 O(n)
T find(int id);
```

Big-O / 延遲特性 / 記憶體 footprint 等性能契約，型別表達不了。如果這個性能特性是 caller 需要知道才能正確選用（例如「這個 method 不適合在迴圈裡呼叫」），就要寫進 doc。

### 3. 對外部系統的副作用

```dart
/// 寫入 audit log（第三方系統，可能延遲到資料庫）
void recordTransaction(Tx tx);
```

跟外部系統的互動（log、analytics、cache invalidation、cloud sync）是型別表達不了的副作用。caller 需要知道這些副作用才能規劃整體流程。

### 4. 時序契約（eventually consistent、retry 行為）

```dart
/// 寫入後最多 1 秒內所有 read replica 會看到新值
Future<void> updateProfile(Profile p);
```

「最多多久內 consistent」「失敗多少次後放棄 retry」「某事件多久觸發一次」——這類**跨呼叫、跨時間的契約**，型別系統無法表達。

### 5. 使用情境的限制（threading / isolation）

```dart
/// 必須在 main isolate 呼叫；否則 throw `IsolateError`
void registerPlatformChannel(String name);
```

「哪個 thread / isolate / context 才能呼叫」這類資訊，多數型別系統無法強制（Rust 的 Send/Sync 是少數例外）。

### 6. 跨方法 invariant

```dart
/// 跟 [withdraw] 配對使用：每次 [reserve] 之後必須對應一次
/// [withdraw] 或 [release]，否則餘額會被 reserved 卡住
void reserve(Decimal amount);
```

「呼叫了 X 之後必須在 Y 時間內呼叫 Z」這類**跨方法的 protocol**，typestate 能部分表達但寫法繁瑣，多數情況靠 doc 是合理的。

---

## 各語言實際範例

### Dart：null safety 的影響

Dart 2.12 引入 sound null safety 後，**至少消除了 30% 的 doc 內容**——不再需要寫「可為 null」「不可為 null」「null 時的行為」。

升級前後對比：

```dart
// 前（Dart 2.10）
/// [name] 可為 null
/// 找不到時回傳 null
class User {
  String name;  // 實際可能為 null，doc 提醒
}
User findUser(String id);  // 實際可能為 null

// 後（Dart 3.x）
class User {
  String? name;  // 型別說明
}
User? findUser(String id);  // 型別說明
```

如果你的 Dart codebase 升了 null safety 但 doc 還在寫「可為 null」之類字句，說明還沒充分利用型別系統的成果。

### Rust：ownership 與 borrow 消除一整類 doc

```rust
// C 風格：靠 doc 警告
/// 注意：caller 必須在 buffer 釋放前完成讀取
/// 不要把 buffer 傳給其他 thread
fn process(buffer: *const u8, len: usize);

// Rust：型別表達
fn process(buffer: &[u8]);  // borrow，編譯期保證 lifetime
fn process_owned(buffer: Vec<u8>);  // own，move 後 caller 不能再用
fn process_shared(buffer: Arc<[u8]>);  // 跨 thread 安全共享
```

Rust 的 ownership / borrow 系統把記憶體管理 / 並發安全相關的 doc 幾乎完全變成型別。寫 Rust 的 function doc 多半短得驚人——大部分 contract 已經編進簽章。

### TypeScript：discriminated union 取代條件 flag doc

```typescript
// 弱：靠 doc 解釋 flag 之間的關係
/**
 * @param type 'success' or 'error'
 * @param data 當 type='success' 時必填，否則為 null
 * @param error 當 type='error' 時必填，否則為 null
 */
interface Response {
  type: string;
  data?: any;
  error?: string;
}

// 強：discriminated union
type Response =
  | { type: 'success'; data: ResponseData }
  | { type: 'error'; error: string };

// 使用時 TypeScript narrowing：
if (response.type === 'success') {
  console.log(response.data);  // 型別已知是 ResponseData
} else {
  console.log(response.error);  // 型別已知是 string
}
```

discriminated union 把「flag 跟其他欄位的關聯」編進型別。這比 doc 警告強多了。

---

## 收益曲線：什麼時候強型別開始邊際遞減

把所有可下移的 doc 都下移，是不是型別越強越好？不是。**型別強化有邊際成本**：

| 階段                                         | 型別強化 | 收益                               | 成本                              |
| -------------------------------------------- | -------- | ---------------------------------- | --------------------------------- |
| 1. 加 null safety                            | 高       | 消除大量 null 相關 doc + 防 NPE    | 低（語言原生支援）                |
| 2. 加 enum 取代 string flag                  | 高       | 消除「合法值列表」doc + 編譯期檢查 | 低                                |
| 3. 加 wrapper value object（PositiveInt 等） | 中       | 消除範圍檢查 doc + 前移 validation | 中（多寫 class）                  |
| 4. 加 Result / Either                        | 中       | 消除 throw doc + 強迫處理 error    | 中（API 寫法改變、要套件 / 自寫） |
| 5. 加 typestate / phantom types              | 低       | 消除「狀態相關呼叫順序」doc        | 高（程式碼變複雜、學習曲線陡）    |
| 6. 加 dependent types / refinement types     | 低       | 編譯期完整契約                     | 極高（需要特殊語言支援）          |

實務 sweet spot 通常落在 1-4 之間。5-6 在 systems / safety-critical 程式碼有意義，一般 app 加進去 ergonomic 變差，回收不到。

---

## 一個 review 的問題：「這條 doc 能變型別嗎？」

review code 看到 doc 時，問三個問題：

1. **這條 doc 描述的是輸入合法範圍嗎？**
   - 是 → 能不能用 wrapper type / refinement / enum 表達？
2. **這條 doc 描述的是回傳的可能性（null、error、特殊值）嗎？**
   - 是 → 能不能用 nullable / Result / sealed class 表達？
3. **這條 doc 描述的是「這時候才能呼叫」嗎？**
   - 是 → 能不能用 typestate / 不同型別的方法分流表達？

任一答案是「能」、先試型別。如果型別寫起來 ergonomic 不好（例如 wrapper class 太多、call site 變難讀）、再退回 doc——「先試型別」比「預設寫 doc」更能逼出可下移的部分。

---

## 一句話 heuristic

把整個討論濃縮：

> doc 是「**型別表達不了的剩餘資訊**」的家——型別越強、剩餘越少。

寫 doc 之前先問「能用型別表達嗎」。能 → 改型別。不能 → 寫 doc，但只寫那條型別表達不了的部分（業務動機、性能、副作用、時序契約、跨方法 protocol）。

---

## 收束：型別系統升級是文件設計升級的契機

每一次語言升級（Dart 2 → 3、TypeScript 加新型別功能、Rust 穩定新 lifetime feature），都是**重新檢視既有 doc** 的機會：

- 哪些 doc 可以下移到新引入的型別功能？
- 下移之後，剩下的 doc 是不是更精準了？
- 是不是有新的型別組合能表達以前只能靠 doc 的契約？

把語言升級當成 doc 整理的契機，不只是「換個編譯器」。**程式碼品質的關鍵改善往往來自把約定升級為約束**——doc 是約定，型別是約束。約定靠人記住，約束靠工具強制。每次升級都是一次「把約定變約束」的機會窗口。

下次看到自己寫了三行 doc 解釋一個 function 的合法輸入範圍，停下來想：**「這三行能不能變成型別簽章？」**——多半可以。
