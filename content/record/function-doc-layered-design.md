---
title: "函式文件分層設計：型別、介面、實作各自該寫什麼"
date: 2026-05-05
draft: false
description: "函式文件分層設計：把資訊放在能表達它的最低層次（名稱 / 型別簽章 / 介面 doc / 實作 doc / 範例與測試）、上層留給「下層表達不了的剩餘」。整理各層該寫什麼、容易誤入的內容、配合反模式列表跟寫 doc 前 checklist 收斂出短而精準的文件。"
tags: ["documentation", "api-design", "code-quality", "methodology"]
---

> **核心命題**：doc 是塑造使用者決策的工具——寫不好的 doc 會反向誤導使用者選錯路。
> **設計原則**：把資訊放在能表達它的最低層次（名稱 / 型別 / 介面 doc / 實作 doc / 範例與測試）、上層留給「下層表達不了的剩餘」。

---

## 起點：doc 是塑造使用者決策的工具

API 設計者常忽略一件事：**文件本身會塑造使用者的決策**——讀者依照 doc 給的資訊選預設值、選呼叫方式、選用途，所以 doc 寫不好就會反向誤導使用者選錯路。

幾種常見的誤導模式：

- 把「需要明確選擇」的東西做成「最少打字的預設」（例如某些 stream / channel API 預設是單訂閱、多數 SQL column 預設 nullable）——使用者讀不到「該選什麼」的資訊，跟著預設走就出包
- 註解重複型別已說明的事，反而讓讀者懷疑「型別是不是不夠精確」
- 介面 doc 描述「目前實作怎麼做」而非「契約承諾什麼」——讓未來新實作以為要照抄
- 用憑想像的業務動機補完，後人讀了當真，反向影響其他相關決策

這些問題不是「沒寫 doc」，而是「**寫了誤導的 doc**」。要寫出不誤導的 doc，得先想清楚每個位置該放什麼資訊。

---

## 設計原則：資訊應該存在最低能表達它的層次

讀者讀一個 function 的閱讀順序：

1. **看簽章**（名稱、參數、回傳型別）
2. **讀 doc comment**
3. **跳進實作**
4. **找範例 / 測試**

每往下一層，閱讀成本就高一級。設計 doc 的原則：

> 能用上層表達的資訊，就不要往下層放。

對應的職責劃分：

| 層次        | 該裝什麼                             | 反例                                               |
| ----------- | ------------------------------------ | -------------------------------------------------- |
| 名稱        | 動詞 / 動作意圖                      | `getData()`、`process()`、`handle()`               |
| 型別簽章    | 輸入合法範圍、回傳保證               | `int qty`（允許負數）、`String?` 沒指明何時為 null |
| 介面 doc    | 契約承諾、所有實作都要遵守的行為     | 描述當前實作流程                                   |
| 實作 doc    | 實作特有的 invariant、bug workaround | 重複介面契約                                       |
| 範例 / 測試 | 抽象描述失敗的複雜用法               | 取代正常 doc                                       |

把資訊放在能表達它的最低層次，能讓上層 doc 更精簡、更精準。

---

## Layer 1：名稱與型別簽章

**強型別語言下，型別是文件的一部分**。很多 doc 內容本來就該由型別承擔。

### 用型別取代「參數說明」

```dart
// 弱：依賴 doc 警告
/// [quantity] 必須為正整數
void increase(int quantity) { ... }

// 強：型別本身就限制
void increase(PositiveInt quantity) { ... }
```

```dart
// 弱：String flag，靠 doc 說明可選值
/// [mode] 可選值：'manual', 'auto', 'hybrid'
void setMode(String mode) { ... }

// 強：用 enum
enum Mode { manual, auto, hybrid }
void setMode(Mode mode) { ... }
```

當型別能表達約束時，**不要用 doc 重複表達**——doc 是約束的弱形式（編譯不檢查、IDE 補全不提示），把 doc 當主要 enforcement 等於放棄型別系統的力氣。

### 用命名取代「這個參數做什麼」

```dart
// 弱：positional argument，靠 doc 解釋
/// [a] 是基準值，[b] 是新值
void update(int a, int b) { ... }

// 強：named argument 自說明
void update({required int from, required int to}) { ... }
```

`update(from: 5, to: 10)` 的呼叫端比 `update(5, 10)` 清楚得多，且**不需要任何 doc**。

### 用回傳型別表達失敗模式

```dart
// 弱：可能失敗，靠 doc 說「失敗時回傳 null」
/// 找不到時回傳 null
User getUser(String id) { ... }

// 強：型別本身表達 optionality
User? getUser(String id) { ... }

// 更強：分清 null 跟 error
Result<User, NotFoundError> getUser(String id) { ... }
```

簽章已經表達清楚的事，doc 不必再寫。

### 命名要表達意圖，不是實作

```dart
// 弱：implementation-leaking 命名
List<Item> getCachedItems() { ... }

// 強：意圖命名
List<Item> getItems() { ... }
```

「Cached」這個字洩漏實作（用了 cache）。如果之後改成不 cache，名字就要改、所有 caller 也要改——但**業務語義並沒變**。命名應該反映「呼叫者想要什麼」，不是「實作怎麼做」。

> 展開閱讀：[型別取代 doc 的收益曲線](../types-replacing-docs/)——整理 null safety / enum / wrapper / Result / typestate 各自能消除哪類 doc、以及型別表達不了的剩餘部分（業務動機、性能、副作用、時序契約）。

---

## Layer 2：介面 doc

介面 doc 是**契約**（contract）——對所有實作的承諾。它的讀者有兩類：

1. **使用者**：「我呼叫這個會發生什麼？需要注意什麼？」
2. **實作者**（包括寫 mock、寫新版實作的人）：「我必須遵守哪些規則？」

兩類讀者都不該為了讀懂契約而去讀任何單一實作。

### 該寫的：契約承諾、行為保證、隱性需求

- **何時 throw / 回傳特殊值**：「找不到時 throw `NotFoundException`」
- **副作用**：「呼叫後 `currentUser` 會被清空」
- **同步 / 非同步保證**：「呼叫後資料庫立即一致；快取要等下一次 refresh」
- **執行順序保證**：「listener 觸發順序不保證」
- **業務規則**（**只在有實際業務需求時寫，且要有來源**）：「會員價只能用 wallet 付款」

### 容易誤入介面 doc 的內容（屬於型別、實作或他處）

介面 doc 的職責是**契約描述**——所以「型別簽章已說的事」「特定實作怎麼做」「沒來源的業務動機」分屬其他層次（型別、實作 doc、issue tracker）、寫進介面 doc 反而稀釋契約本身的能見度。三個典型誤入：

#### 1. 型別已表達的內容（屬於型別簽章）

```dart
// 冗：
/// 回傳 User，找不到時為 null
User? findUser(String id);

// 簡：型別已說明，doc 留白或寫業務動機
User? findUser(String id);
```

#### 2. 當前實作的細節（屬於實作 doc）

```dart
// 冗：洩漏實作
/// 內部用 HashMap 存儲，O(1) 查詢
User? findUser(String id);

// 簡：純契約
User? findUser(String id);
```

實作細節寫在介面 doc 會誤導實作者「這個契約規定要用 HashMap」。如果未來有人寫一個用 B-tree 的實作，是合法的，但讀 doc 會以為違反契約。

#### 3. 憑想像補完的業務動機（屬於 issue tracker / 不寫）

```dart
// 冗（且可能錯）：
/// 為了符合 PCI-DSS 規範，這裡不能 log 完整 cardNumber
String maskCardNumber(String cardNumber);

// 簡（沒來源就只寫可觀察事實）：
/// 回傳遮罩後字串，僅保留尾 4 碼
String maskCardNumber(String cardNumber);
```

業務動機要有來源（規範文件、PM 決策、incident 紀錄）才寫；猜的不要寫。猜的動機被當真會反向影響後續決策——讀者拿這條沒來源的猜測當依據、推到「既然是因為 PCI-DSS、那 X 也要這樣處理」、就把錯誤論述擴散到下游。

### 介面 doc 越精簡越能被讀完

很多人覺得「寫得詳細才負責任」，結果介面 doc 三段五行，讀完也記不住。**好的介面 doc 通常只有 2-4 行**：

```dart
/// 從本地購物車移除指定商品
///
/// 找不到對應品項時不做事；不會拋例外。
void removeFromLocalCart(CartItem item);
```

第一行說 what、第二行說 edge case。寫到這就停。「指定商品」怎麼比對？無關契約，去看實作。

---

## Layer 3：實作 doc

實作 doc 的職責跟介面 doc**完全不同**：

- **介面 doc**：對外契約，所有實作共通
- **實作 doc**：這個實作特有的細節

### 該寫的：實作特有的 invariant、workaround、tradeoff

```dart
// ✅ 實作特有的 invariant
@override
void increaseItemQuantity(CartItem item) {
  // 順序關鍵：先 set lastChangedItem 再動 list，
  // 因為訂閱 localCartItems 的 worker 會在 list 變動時讀 lastChangedItem
  lastChangedItem.value = item;
  localCartItems[index] = ...;
}

// ✅ bug workaround
// Workaround for SQLite issue #1234: integer overflow on 32-bit Android,
// 拆成兩步 query 避開
final ids = await db.rawQuery('SELECT id FROM ...');
return await db.query('items', where: 'id IN (${ids.join(",")})');

// ✅ 性能 tradeoff
// 用 LinkedHashMap 而非普通 Map：插入 1k 次後查詢效能差 3-5 倍
final cache = LinkedHashMap<String, Item>();
```

這些都是**讀實作 code 也看不出「為什麼要這樣」**的決定，需要 doc 解釋。

### 契約只寫一處：實作不重複介面已寫的規則

實作 doc 的職責跟介面 doc 互補——契約描述歸介面層、實作層只補「該實作的特殊性」。同一條契約規則寫第二次（在實作層複述介面已寫的承諾）會破壞「契約只寫一次」原則：規則改的時候要同步兩處、少改一處就出現自相矛盾的文件、讀者看到也分不清以哪份為準。

```dart
// ❌ 介面 doc 已寫的規則，實作不再重複
@override
// 移除不視為「最後變更」，不更新 lastChangedItem
void removeFromLocalCart(CartItem item) {
  localCartItems.remove(item);
}
```

「移除不更新 lastChangedItem」是契約、介面層已寫。

如果擔心未來維護者誤以為「作者忘了寫」，留一個**指向介面**的最小提示比複述整條規則更安全：

```dart
@override
// 行為見 ICartService.removeFromLocalCart
void removeFromLocalCart(CartItem item) {
  localCartItems.remove(item);
}
```

不重複規則，只指向真相來源。

### Negative-space documentation

實作 doc 偶爾要寫「**為什麼這裡刻意沒寫某段程式**」。這類 doc 防的是「未來維護者順手補上」：

```dart
void processPayment(Payment p) {
  // NOTE: 這裡刻意不 retry —— payment gateway 是非冪等，
  // retry 會造成重複扣款。失敗一律拋給上層人工處理。
  return _gateway.charge(p);
}
```

沒這條註解，下個維護者看到網路 retry 是常見做法，可能會「順手加上」造成事故。

negative-space doc 用得好可以避免事故；用得多會變成處處防禦性註解，閱讀體驗變差。原則：**這個「刻意沒做」的決定，是不是違反讀者的合理直覺？** 違反才寫。

---

## Layer 4：範例與測試

複雜 API 的最後一層 doc 是**可執行範例**。

何時用 example：

- API 有多個正交參數，組合起來很多種用法
- 抽象描述比看程式碼難懂
- 邊界 case 用文字描述模糊（「如果 collection 是空、且 timeout 為 zero、且 retries 為 0…」）

何時不用 example：

- API 用法只有一種、簽章已說清
- 用法跟名稱字面意義一致

**測試也是 doc**。命名好的測試比 example 更有價值——不會 outdated（測試會跑、example 不會），且涵蓋 edge case。

```dart
test('returns null when item not in cart', () { ... });
test('decreases quantity when item exists with quantity > 1', () { ... });
test('removes item when quantity reaches 0', () { ... });
```

讀者看 function 不確定行為時，**跳到對應 test file 比讀冗長 doc 快**——測試案例的命名直接告訴你支援哪些 case，並且每個案例都有可執行的具體輸入輸出。

> 展開閱讀：[測試命名作為文件](../test-naming-as-documentation/)——測試是少數會自我驗證的文件、把命名寫成可執行 spec 條目就能取代不少 doc 的職責。

---

## 常見反模式

### 反模式 1：用 doc 取代不好的命名

**正向概念**：命名是契約的最強形式、doc 是命名表達不了的剩餘部分的家。命名先到位、doc 才有空間寫真正重要的事。

```dart
// 反：靠 doc 補救命名
/// 處理訂單，但只在訂單狀態為 pending 時做事
void handle(Order o);

// 正：命名表達意圖
void handlePendingOrder(Order o);
```

把 doc 當成命名失敗的補丁有兩個問題：(1)「需要讀 doc 才能用對」的 function 在 IDE 自動補全 / 快速瀏覽時看不到 doc、誤用機率高；(2) 命名其實沒變、別人改 code 時 doc 會跟不上、補丁本身又 outdated。「需要 doc 才能用對」通常是命名沒到位的訊號。

### 反模式 2：過度註解

**正向概念**：doc 是稀缺資源——讀者注意力的預算有限、把 doc 留給「值得花注意力讀」的事項。

```dart
// 反：句句都是 noise
class User {
  /// User 的 ID
  String id;
  /// User 的名字
  String name;
  /// User 的 email
  String email;
}

// 正：欄位名清楚就不寫
class User {
  String id;
  String name;
  String email;
}
```

「`User.name` 是 User 的名字」屬於命名已表達的訊息、寫進 doc 只是 redundant noise。整份 code 充斥這類 doc 會稀釋訊號——讀者習慣性 skip 所有 doc 之後、連真正重要的 invariant 跟 edge case 也會被一起跳過。

### 反模式 3：過去式 doc

**正向概念**：source code doc 描述「**現在**這份 code 在做什麼」、commit message 描述「**那一刻**為什麼要改」。兩種讀者要找的資訊不同、各歸各的家。

```dart
// 反：寫給歷史
/// 修了 issue #123 的 race condition
void process() { ... }

// 正：寫給未來讀者（保留 fix 的關鍵 invariant 即可）
void process() {
  // 必須在持有 lock 內 call observer，避免 observer 看到中間狀態
  ...
}
```

「修了什麼 bug」凍結在過去某一刻、屬於 commit message / changelog；「目前必須持有 lock」是契約限制、屬於 source code doc。把過去式直接塞進 source 等於用 source 重做一份 git log——但 git log 已經存在、且結構化、可搜尋、有 author / timestamp。

> 展開閱讀：[Commit message vs source code doc](../commit-message-vs-source-doc/)——時序敏感的資訊（為什麼這次改、考慮過什麼方案）放 commit、持續適用的契約放 source、配合 git blame 工作流讓考古路徑清楚。

### 反模式 4：同一條規則多處寫

**正向概念**：契約由介面層獨家承載、其他層引用即可。規則只有一個 SSoT（Single Source of Truth）、修改成本才可控。

```dart
// 反：規則寫三處
// 介面：「取消訂單後 3 天內不能重新下單」
// 實作：「取消後 3 天內不能重新下單」
// 測試：「驗證取消後 3 天內不能重新下單」

// 正：規則寫一處（介面），其他指向
// 介面：「取消訂單後 3 天內不能重新下單」
// 實作：（無 doc）
// 測試：test('cannot reorder within 3 days of cancellation')
```

一條規則複製到三處看起來保險、但會在改規則時暴露代價：要同步修三處、漏改一處就出現自相矛盾的 doc、讀者讀到不一致的版本反而會懷疑「以哪份為準」。把規則收斂到單一介面、其他層指向（測試命名 / 實作註解 `// 行為見 ...`）就夠了。

### 反模式 5：把語法選擇當成 doc 內容

**正向概念**：doc 描述業務目的跟行為契約——讀者要的是「這個 function 做什麼」、不是「為什麼用這個語法寫」。

```dart
// 反：寫實作層次的選擇細節
/// 用 Dart 3 的 record pattern destructure，比 .$1 / .$2 可讀
void handle((int, int) event) {
  final (a, b) = event;
  ...
}

// 正：寫業務動機 / 行為契約
/// 處理 (timestamp, value) 對的批次更新
void handle((int, int) event) { ... }
```

「為什麼用某語法」屬於 commit message / PR review 的討論記錄、不屬於 source code doc——換個語法寫法、業務行為沒變、但 doc 卻會 outdated。語法選擇的 why 在 git log / PR description 找得到、不需要 source 背這份歷史。

### 反模式 6：用 doc 警告使用者「請別這樣用」

**正向概念**：能用型別 / API 設計禁掉的誤用、把它編進型別系統；doc 警告留給型別表達不了的使用情境（時序、跨方法 invariant、執行環境）。

```dart
// 反：靠 doc 警告
/// **不要**直接修改回傳的 list，會造成內部狀態不一致
List<Item> getItems();

// 正：型別 / API 設計阻止誤用
List<Item> getItems() => List.unmodifiable(_items);
// 或回傳 Iterable / immutable 集合型別
```

doc 警告的執行力靠使用者「願意讀並且記住」、型別約束則是編譯期強制——當失敗成本高（內部狀態被破壞）、保護機制就值得從 doc 升到型別。型別表達不了的使用情境（例如「必須在 main isolate 呼叫」）才是 doc 警告該守的範圍。

---

## API 設計層面：doc 之外的塑造工具

doc 寫得再好，**API 設計本身**會更直接塑造使用者行為。要讓使用者選對，從設計層下手比寫 doc 有效。

### 預設值要選「多數情況下對的」

```dart
// 預設導向受限選項：使用者忘了選通用版本就出錯
StreamController<int> ctrl = StreamController();  // single

// 預設導向通用選項：忘了選受限版本不會出錯
StreamController<int> ctrl = StreamController.broadcast();
// 受限版本要顯式選 .singleSubscription()
```

當預設造成的失敗成本高、失敗模式又不易察覺、把多數人實際需要的選項變成預設、能消除整類「忘了選」的事故。doc 警告的執行力靠「使用者讀到並記住」、規模一大就守不住——把保護從約定升到結構。

### 把選擇從 default 取消（用型別禁掉）

```dart
// 弱：靠 doc 說「不該直接呼叫，請用 X」
@protected
void internalMethod() { ... }

// 強：型別系統禁掉
class _InternalImpl { void method() { ... } }
```

能用 visibility / sealed / private 收掉的「請別這樣用」、把它收進型別系統——比起 doc 提示、語言層級的禁用是無條件強制的、且不會在大型重構時被遺漏。

### Builder / fluent API 取代多參數

```dart
// 弱：positional / named 多參數，靠 doc 解釋
Request build(String url, [Map<String, String>? headers, Body? body, int timeout = 30]);

// 強：fluent API 自說明
Request.builder(url)
  .header('Accept', 'json')
  .body(payload)
  .timeout(Duration(seconds: 30))
  .build();
```

fluent API 的 method 名直接表達意圖，不需要 doc 解釋每個參數做什麼。

---

## 寫 function doc 的 checklist

寫一個 function doc 前，跑這個 checklist：

- [ ] **這條資訊型別能不能表達？** 能 → 改 type，不寫 doc
- [ ] **這條資訊命名能不能表達？** 能 → 改名，不寫 doc
- [ ] **這條資訊是契約還是實作細節？** 契約 → 介面 doc / 實作 → 實作 doc
- [ ] **這條規則是不是已經寫在介面 doc？** 是 → 實作不重複
- [ ] **這個業務動機有沒有來源？** 沒有 → 不寫，只寫可觀察事實
- [ ] **這個 doc 在描述什麼時候出問題？** 是 → 寫得明確（throw / null / edge case）
- [ ] **沒有這條 doc，讀者會誤判嗎？** 不會 → 不寫
- [ ] **同一條規則我寫了第二次嗎？** 是 → 砍一處，留一處

過完 checklist 留下的 doc 通常很短——**這是好現象**。

---

## 一句話 heuristic

把整個討論濃縮：

> doc 是「**型別、簽章、命名、結構都表達不了的剩餘資訊**」的家。

寫 doc 之前先問：

- 能用型別表達嗎？
- 能用命名表達嗎？
- 能用結構（fluent API、enum、sealed class）表達嗎？

三題都答「不能」、**而且**使用者不知道會出錯——這時才需要 doc。

這個原則的 corollary：**型別系統越強的語言、function doc 也越能寫得短**。如果發現 Dart / TypeScript / Rust 的 function doc 寫得跟 Python 一樣長、多半有東西可以下移到型別。

### 何時 doc 還是該寫得詳細

「能少寫就少寫」是預設、**但有些情境 doc 必須寫得詳細**——這些是型別跟結構覆蓋不到的場景：

- **跨方法 protocol**：「呼叫 `reserve` 之後必須在 X 內呼叫 `commit` 或 `release`」——typestate 能部分表達但寫法繁瑣、多數情況靠 doc 是合理的
- **時序契約**：「寫入後最多 1 秒內 read replica 可見」「retry 5 次後放棄」——跨呼叫、跨時間的契約、型別表達不了
- **副作用 / 對外部系統的影響**：「會寫入 audit log」「會發 webhook」——caller 需要知道才能規劃整體流程
- **業務規則 + 有來源**：「會員價只能用 wallet 付款（業務需求 #1234）」——有出處的業務動機要寫、避免後人誤刪
- **效能契約**：「O(log n) 查詢；不適合在熱迴圈呼叫」——caller 要根據這個資訊選用法

「短」不是目標、「精準」才是。把該下移的下移到型別、剩下的就值得詳細寫。

---

## 收束：doc 設計就是 API 設計

回到開頭——doc 寫不好會誤導使用者。但更深一層的觀察是：**「需要寫很多 doc 才能用對」本身就是 API 設計的紅旗**。

好的 API 用最少的 doc 就能讓使用者用對：

- 命名直接表達意圖
- 型別表達合法輸入與失敗模式
- 結構（enum、sealed、builder）防止誤用
- 預設值導向多數情況下正確的選擇
- 殘餘的契約與 edge case 用簡短介面 doc 說明
- 實作特有的 invariant 用簡短實作註解說明

寫 doc 的時候同時問「**這條 doc 想說的事，是不是該由 API 設計本身承擔？**」——這個問題能讓你的 doc 跟 API 同時變更好。
