---
title: "金額型別的三段遷移：double、Decimal、再到 Money extension type"
date: 2026-07-10
draft: false
description: "金額欄位從 double 換 Decimal 只解決精度、沒解決「任何人都能對它做無意義運算」；用 Dart extension type 包成 Money 之後，型別系統只開放領域有意義的運算。含 implements Object 的 subtype 設計、以及大規模型別遷移前先寫 characterization test 鎖行為的做法。"
tags: ["dart", "flutter", "extension-type", "decimal", "value-object", "ddd", "refactoring"]
---

> **觸發場景**：整理 POS 專案的金額處理時，發現 git 歷史上金額型別換過兩次——`double` 到 `Decimal`、再從 `Decimal` 到自訂的 `Money`。第二次遷移乍看多餘：精度問題 `Decimal` 已經解掉了
> **疑問來源**：`Decimal` 哪裡不夠？第二次遷移買到的是什麼？
> **整理目的**：記下「精度」跟「語意」是金額型別的兩個獨立問題、以及 Dart extension type 在第二個問題上的實作手法
> **本文邊界**：以該專案的實際遷移軌跡為素材；extension type 是 Dart 3 的機制、其他語言的對應手法（newtype / value class）思路相同但細節不同

---

## 第一段：double 的精度問題

最初所有金額欄位是 `double`，JSON 轉換器把後端的 number 或 string 統一存成 `double`。浮點數處理金額的問題是經典的：`0.1 + 0.2 != 0.3`，累加訂單明細時誤差會累積到分位。

第一次遷移（單一 PR 內兩個 commit）把所有 model 的金額欄位換成 `Decimal`，API 接入層用 `jsonToDecimal` 統一處理後端可能回 number 或 string 的格式差異。精度問題到此解決。

## 第二段：Decimal 解決了精度、沒解決語意

換完 `Decimal` 之後，金額仍然是一個**裸的通用數字型別**。任何拿到 `Decimal` 的程式碼都能對它做任意運算：兩個金額相乘（語意上不存在的運算）、金額跟折扣率直接相加、拿金額當數量用。型別系統對這些錯誤全部放行，因為它們在 `Decimal` 的世界都是合法運算。

這是 primitive obsession 的標準形態：值的表示對了、值的**語意邊界**還是沒有。三個月後的第二次遷移把金額包進 `Money`：

```dart
extension type const Money._(Decimal _raw) implements Object {
  Money operator +(Money other) => Money._(_raw + other._raw);
  Money operator -(Money other) => Money._(_raw - other._raw);
  Money operator -() => Money._(-_raw);              // 退款 / 折讓
  Money operator *(int quantity) => ...;             // 金額 × 數量
  Money multiplyByRate(Decimal rate) => ...;         // 會員價率、服務費率
  Money clamp(Money min, Money max) => ...;
  ...
}
```

運算列表本身就是領域規則的宣告：金額加金額可以、金額乘整數（數量）可以、金額乘倍率（`Decimal`，刻意跟數量分開簽名）可以——**金額乘金額不存在**，因為介面沒開放。想對 `Money` 做 `Decimal` 的任意運算，得先顯式呼叫 `toDecimal()` 拆封，那一行拆封程式碼就是 code review 的攔截點。

## implements Object 的取捨：要當 Object、不當 Decimal

extension type 宣告 `implements Object` 而只有這個，是一個精確的 subtype 決策：

- **是 `Object` 的 subtype**：既有的格式化入口 `formatAmount(Object)` 可以直接吃 `Money`、不用改簽名
- **不是 `Decimal` 的 subtype**：如果宣告 `implements Decimal`，`Money` 就能被傳進任何收 `Decimal` 的參數、所有裸運算又回來了——包裝等於白做

extension type 在 runtime 是零開銷的（編譯後就是底層的 `Decimal`），所有約束都活在編譯期。這也意味著它的保護是編譯期的：反射或 dynamic 繞得過去，威脅模型是「防止無心的誤用」而不是「防止刻意拆封」。

## 遷移安全網：characterization test 先鎖行為

第二次遷移動的是全專案的金額欄位，怎麼確認換型別沒改行為？這個專案在遷移前先寫了一批 characterization test，測試檔開頭直接註明用途：

> Characterization test —— 鎖住 CheckoutContext 結帳金額計算的現有行為。在 Money value object 遷移（階段 5）前建立。涵蓋應付金額 fold、現金找零（含負數歸零分支）、金額足夠判斷。

characterization test 跟一般測試的差別在斷言的性質：它不驗證「行為正確」、驗證「行為不變」。遷移前對著舊實作寫、鎖住當前輸出（包含當前的邊界行為，例如找零算出負數時歸零），遷移後全綠就證明型別替換沒有帶入行為變化。正確性是另一個問題、留給另一批測試——把兩個問題混在同一批測試裡，遷移期間的紅燈就分不清是「換壞了」還是「本來就錯」。

## 收束：兩個問題、兩次遷移

金額型別有兩個獨立的問題，這個專案的軌跡恰好一段解一個：

| 問題 | 症狀                       | 解法                   |
| ---- | -------------------------- | ---------------------- |
| 精度 | 浮點誤差累積到分位         | `double` 換 `Decimal`  |
| 語意 | 任何人都能對金額做任意運算 | `Decimal` 包成 `Money` |

第一段遷移完成時「金額用 Decimal」看起來已經是終點，語意問題要等到夠多「拿金額亂算」的路徑存在後才顯形。判讀訊號是：**一個領域概念的合法運算集合、明顯小於它底層型別的運算集合**時，包一層 domain type 的價值就成立——差集裡的每個運算都是一個等著被誤用的 API。

## 相關閱讀

- 概念地基：[DDD 領域驅動設計指南](/ddd/) 的 value object 章節（本文是 primitive obsession 到 domain type 的實機案例）
- 同族判準：[copyWith 是逃生口，不是設計](/work-log/dart_copywith_entity_escape_hatch/)——那篇的判準「有沒有不允許任意組合的欄位」在型別層的對應是「有沒有不允許的運算」，兩篇都是把約束從慣例層上移到型別層
