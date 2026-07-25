---
title: "值物件的 Dart 實作路徑"
date: 2026-07-20
description: "一個領域值該不該脫離裸的通用型別、以及在 Dart 用哪種載體實作時使用。手寫 immutable class、freezed 產生器、extension type 零成本包裝的成本結構不同——欄位數、要不要 runtime 身份、boilerplate 容忍度決定選哪條，以及從原始型別遷移過去怎麼鎖住行為不變。"
weight: 3
tags: ["flutter", "dart", "value-object", "extension-type", "freezed", "copywith", "type-design"]
---

值物件在實作層的責任是把一個領域值裝進專用型別、讓型別開放的運算限縮成領域有意義的封閉集合。金額只該加減、乘數量、乘倍率；識別碼只該比對與傳遞；日期範圍只該判包含與交疊。底層的通用型別（數字、字串）開放的運算遠多於這個集合，差集裡的每個運算都是一個等著被誤用的 API——把值物件建起來，就是把差集從型別上關掉。

「這個領域值該不該升級成值物件」的判定屬於理論層，判準是同一性語意與語意封閉、與語言無關，見 [entity 與 value object 的判準](/ddd/entity-vs-value-object/) 與 [value object](/ddd/knowledge-cards/value-object/) 卡。本章接手判定之後的問題：在 Dart 裡，同一個「值物件」有三種實作載體，成本結構與適用情境各異——選哪條由這個值的欄位數、要不要 runtime 身份、以及專案對產生器的容忍度決定。

## 判斷：什麼領域值值得升級

值得升級的訊號是一個領域概念以裸的通用型別跨模組流通、而它的合法運算明顯少於底層型別。金額用 `double` 或 `Decimal`、識別碼用 `String`、數量用 `int`——這些型別在模組之間傳遞時，型別系統對「金額乘金額」「識別碼相加」這類無意義運算全部放行，因為它們在底層型別的世界裡都合法。合法運算集合小於底層集合、且裸型別已經跨越模組邊界，包一層的價值就成立。

這裡有兩個常被壓成一個的獨立問題。精度是底層表示的問題——浮點數累加金額會把誤差堆到分位，換一個高精度數字型別就解決。語意是運算邊界的問題——換完精度型別後，「任何人都能對這個值做任意運算」原封不動。解掉第一個問題的當下第二個問題完整存在，而它要等夠多「拿金額亂算」的路徑累積後才顯形。把兩者混為一談的後果是換完 `Decimal` 就宣告收工、語意缺口留在原地。

反過來，不是每個領域值都值得升級。合法運算集合幾乎等於底層型別的集合時（一個真的就是任意整數的計數器），封閉沒有差集可關、專用型別只是多一層轉換。裸型別從不跨越模組邊界、只在單一函式內部短暫存在時，誤用的窗口太小、升級的維護成本收不回。判準操作化成一句話：盤點這個概念的合法運算清單、跟底層型別的運算集合做差集，差集非空且裸型別在模組間流動，才動手。

## 實作路徑的成本結構

三種載體對應兩條軸：這個值是單一底層值還是多欄位複合值、以及需不需要 runtime 的型別身份。單一底層值（金額包一個數字、識別碼包一個字串）走 extension type 最省；多欄位複合值（地址、日期範圍、含幣別的金額）需要一個真正的物件裝多個欄位，走 class 路徑，class 又分手寫與 freezed 產生兩種。runtime 身份的需求橫切這兩軸——需要 `is Money` 在執行期為真、或需要反射看得到型別時，只有 class 路徑滿足。

Dart 3 的 record 是多欄位載體、還自帶結構相等，看起來像多欄位複合值的第四條路徑，但它不入選值物件的載體、原因在型別語意。record 是結構型別而非名目型別：兩個欄位形狀相同的概念（`(String, String)` 的地址與姓名）在型別系統裡是同一個 record 型別、拿不到 `DateRange` 這種領域名字，也就換不到「傳錯型別編譯期就擋」的保護。record 沒有建構子、無處掛不變式檢查，也無法限縮 API——任何拿到它的程式碼都能讀所有欄位、組任意新值。值物件要的名目身份、建構期不變式、封閉介面，record 結構上三個都不給。它適合的是函式的匿名多回傳與臨時分組，不是需要領域約束的值物件。

### 手寫 immutable class 與 copyWith

手寫 immutable class 是最直接的載體：所有欄位 `final`、建構子帶不變式檢查、要「改」就造一個新實例。多欄位複合值在這條路徑上用 [copyWith](/flutter/knowledge-cards/copywith/) 做逐欄位覆寫——傳要改的欄位、其餘保留原值、回傳新實例，這對欄位組合全部合法的值語意清晰。成本在 boilerplate：`==` 與 `hashCode` 要手寫且要涵蓋所有參與相等性的欄位、`copyWith` 每加一個欄位就要同步一行，漏一個欄位的相等性比對是安靜的 bug。

這條路徑的邊界在 copyWith 的適用範圍。對欄位組合全部合法的資料袋與純值物件，copyWith 是正確工具；對有領域方法、欄位之間有不變式約束的型別，全欄位 public 的 copyWith 是繞過領域方法的逃生口——領域方法從「唯一變更路徑」降級成「建議路徑」。判準是型別有沒有「不允許任意組合的欄位」，有的話那些欄位就不該讓 copyWith public 可寫。完整機制見 [copyWith 是逃生口，不是設計](/work-log/dart_copywith_entity_escape_hatch/)。

### freezed 產生器

[freezed](/flutter/knowledge-cards/freezed/) 是把手寫 class 的 boilerplate 壓到接近零的產生器：標記 `@freezed` 後自動產生 copyWith、`==` / `hashCode`、`toString()`、以及 sealed union。多欄位複合值需要完整相等性與序列化、又不想手工維護每個欄位的同步時，freezed 是這條路徑的主流選擇；它的 sealed union 在枚舉分層上另有價值——exhaustive switch 讓「忘記決定新成員歸哪類」在編譯期就走不通。

成本結構有兩面。一面是工具依賴：freezed 走 `build_runner` 產生程式碼，專案要接受產生器的建置步驟與產物管理。另一面是預設路徑的一視同仁——freezed 不區分資料袋和有領域方法的 entity，每個被標記的 class 都得到全欄位 public copyWith，包含狀態欄位與稽核欄位。規範說「請走領域方法」、工具預設給全欄位 copyWith，兩者衝突時預設會贏。在 entity 上使用 freezed 需要額外收窄：把 copyWith 改 private、或從參數列移除受約束的欄位。結構細節見 [Freezed 三層結構解剖](/work-log/dart_freezed_anatomy/)。

### extension type 零成本包裝

[extension type](/flutter/knowledge-cards/extension-type/) 是 Dart 3.3 起提供的載體，把單一底層值包成一個新名字、限縮可用的 API、而 runtime 不存在額外物件——編譯後就是底層型別本身，所有約束活在編譯期。單一底層值的語意封閉、又在高頻路徑上流通（金額在每筆訂單明細累加、識別碼在每次查詢傳遞）時，這條路徑用零 runtime 開銷換到型別安全。它跟 class 路徑是互斥的實作選擇：class 走 runtime、有型別身份也有 overhead；extension type 走編譯期、零 overhead 但 runtime 透明，`is` 與 `as` 看到的是底層型別。

用 extension type 時要在設計期定 subtype 決策——它是底層型別的 subtype（寬鬆：可隱式 upcast 回底層、封裝邊界弱）還是獨立型別（嚴格：只能顯式拆封、每個銜接點都要拆）。金額的做法是 `implements Object` 而只有 Object：既有的格式化入口 `formatAmount(Object)` 能直接吃它、不必改簽名；同時它不是數字型別的 subtype，於是不能被傳進任何收數字型別的參數，裸運算沒有回來的路。這條路徑不搭 copyWith——extension type 沒有 runtime 物件可以逐欄位覆寫，逐欄位覆寫語意只在 class 路徑上成立。

三條路徑的選型錨點收在下表，每一列的成本結構與適用情境在上面各自的段落展開：

| 載體                 | 適用的值形狀             | 成本結構                               | runtime 身份 |
| -------------------- | ------------------------ | -------------------------------------- | ------------ |
| 手寫 immutable class | 多欄位複合值             | 手寫 `==` / `hashCode` / copyWith      | 有           |
| freezed              | 多欄位複合值、要完整相等 | build_runner 依賴、預設全欄位 copyWith | 有           |
| extension type       | 單一底層值、高頻流通     | 零 runtime 開銷、runtime 透明          | 無           |

## 從原始型別遷移過去

值物件多半在裸型別的誤用累積之後才補上去，於是實作值物件常常等於一次型別遷移。一個金額欄位的遷移軌跡把兩個獨立問題各解一段：最初是浮點數、累加誤差堆到分位；第一段換成高精度數字型別、精度問題解決；金額仍然是裸的通用數字、任何拿到它的程式碼都能做任意運算，於是第二段把它包進 extension type，開放的運算限於領域有意義的集合。運算列表本身就是領域規則的宣告：金額加減可以、乘數量可以、乘倍率可以（刻意跟數量分開簽名），金額乘金額不存在、因為介面沒開放。想對它做底層型別的任意運算，得先顯式呼叫拆封方法，那一行拆封程式碼就是 code review 的攔截點。這條軌跡的完整素材見 [金額型別的三段遷移](/work-log/dart_money_extension_type_migration/)。

遷移動的是全專案的欄位，安全網是 characterization test——遷移前對著舊實作寫、鎖住當前輸出（包含當前的邊界行為，例如找零算出負數時歸零），遷移後全綠就證明型別替換沒有帶入行為變化。它跟一般測試的差別在斷言的性質：它驗證「行為不變」、不驗證「行為正確」。正確性是另一批測試的事——把兩個問題混在同一批測試裡，遷移期間的紅燈就分不清是「換壞了」還是「本來就錯」。做法展開見 [測「不變」、不測「正確」：characterization test](/work-log/flutter_characterization_test_migration_safety_net/)。

## 取值出口：封裝的對象是運算、不是取值

值物件封住的是「任意運算」、不是「取原始值」本身。基礎設施邊界對原始值有正當需求——快取需要 key、資料庫需要 column 值、序列化需要原始表示、格式化銜接層需要底層型別。正確做法是給原始值一個語意明確的官方出口，而不是禁止取值逼下游硬撬。金額的拆封方法 `toDecimal()` 就是這種出口，註解直接寫明供哪種場合使用；序列化給 `toDbValue()` 這類名字說明用途的方法；UI 顯示給 `displayValue`。有官方出口的世界裡「誰在拆封」是可 grep 的（搜出口方法名就是完整清單），封裝邊界是明示的。

把取值本身當違規會來回撞牆。一個 App 的識別碼型別的封裝政策擺盪過兩輪：先追「零個外部取值」把公開介面只留 `toString()`，撞上基礎設施層的正當需求後又把取值 getter 加回來、改名叫「相容性介面」。兩個極端各自的撞牆點是同一個病的兩面——完全封裝逼正當消費把 `toString()` 當取值 API 用（語意寄生，`toString()` 哪天為除錯改格式、快取 key 就靜默換一批），零封裝則讓 ISBN 校驗、ID 格式這些不變式失去強制點。穩態在中間：原始值有官方出口、出口有語意、邊界寫進決策記錄。擺盪的完整軌跡見 [Value Object 的封裝擺盪](/work-log/flutter_value_object_encapsulation_oscillation/)，出口設計的理論層展開見 [建構路徑設計](/ddd/construction-path-design/)。

## 邊界

本章處理值物件在 Dart 的實作載體選擇，是實作層知識。三個上游判定不在本章：一個型別該不該模型化成領域模型（入口判準見 [資料袋與領域模型](/ddd/data-bag-vs-domain-model/)）、模型化之後該用 entity 還是 value object（同一性判準見 [entity 與 value object 的判準](/ddd/entity-vs-value-object/)）、以及約束該落在文件層、型別層還是執行層（見 [不變式的強制層次](/ddd/invariant-enforcement-layers/)）。值物件把封閉做在型別層，防的是無心誤用——刻意用反射或 dynamic 拆封仍然繞得過，威脅模型是「防止意外」而不是「防止刻意」。

型別層防護的另一半責任落在 entity 而非 value object：entity 的同一性由身份定義、有生命週期、變更要走領域方法，那條路徑的收窄（copyWith 逃生口、稽核軌跡凍結）跟本章的值物件封閉是相鄰但不同的問題，路由到 [狀態轉換與稽核軌跡](/ddd/state-transition-and-audit-trail/)。

## 下一步

三條實作路徑各有 case 可深讀：copyWith 的適用邊界在 [copyWith 是逃生口，不是設計](/work-log/dart_copywith_entity_escape_hatch/)、freezed 的結構在 [Freezed 三層結構解剖](/work-log/dart_freezed_anatomy/)、extension type 的 subtype 決策與遷移在 [金額型別的三段遷移](/work-log/dart_money_extension_type_migration/)。取值出口的封裝邊界在 [Value Object 的封裝擺盪](/work-log/flutter_value_object_encapsulation_oscillation/)、遷移安全網在 [characterization test](/work-log/flutter_characterization_test_migration_safety_net/)。理論地基從 [DDD 指南的模型設計主梯](/ddd/) 進，值物件在其中的位置是 [entity 與 value object 的判準](/ddd/entity-vs-value-object/) 的語意封閉段。
