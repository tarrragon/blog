---
title: "Sociable vs Solitary Unit Test（單元的兩種定義）"
date: 2026-08-25
description: "在「這個協作者該不該換成替身」上卡住、或讀到兩本測試書給出相反建議時，用來定位分歧的源頭"
weight: 24
tags: ["testing", "unit-test", "tdd", "mock", "sociable", "solitary"]
---

Unit test 的「單元」有兩個並存的定義，所以「這裡該不該換成 [test double](/testing/knowledge-cards/test-double-taxonomy/)」這個問題在兩派下有不同的正確答案。差別在測試邊界畫在哪一層。

**Sociable** 把單元定義為模組——一組協同工作的類別，對外提供公開 API。測試只透過這個 API 互動，替換掉的只有跨越應用邊界的依賴，也就是跨出本應用進程、需要外部世界回應的那些（資料庫、檔案系統、外部服務、時鐘、亂數）。

**Solitary** 把單元定義為單一類別，把所有協作者換成 test double（在測試裡頂替真實協作者的物件），測試看得見類別之間的每一次呼叫。

想要一句最小分流：內部的類別劃分未來會不會反覆重組？會，畫在模組；已經定案而失敗定位很花時間，畫在類別；已經定案而定位本來就不花時間，兩者皆可，這時看真實協作者造起來與跑起來的代價。完整的判讀方式——邊界畫錯時看得出來的症狀、以及每個症狀先試哪個不移動邊界的解法——在 [TDD 的兩種做法](/record/behavior-first-tdd-methodology/)。

## 概念位置

分野的後果落在**耦合線**上。一條耦合線是測試依賴的一個結構點：測試知道它長什麼樣，它一改，測試就要跟著改。計數規則是受測對象算一個，每個替身各算一個。

```text
Sociable                                    耦合線
  Test ──→ Module 公開 API                    1
             └─ Class A · B · C（黑盒，測試看不見）

Solitary
  Test ──→ Class A（受測對象）                 1
  Test ──→ Double(B)（設定回應、斷言呼叫）      2
  Test ──→ Double(C)（設定回應、斷言呼叫）      3
             Class A 對 B、C 的呼叫方式，測試全都知道
```

條數本身不是重點，兩種條各自的穩定性才是。Sociable 那一條是模組的公開契約，它本來就被設計成不常變；Solitary 多出來的那幾條是模組內部的協作協定，沒有人承諾過它穩定，而它正是重構會動到的東西。所以維護成本不看條數的絕對值，看的是有幾條掛在「沒有人承諾穩定」的東西上。

Solitary 因此多承擔一種盲區：類別之間的真實協作行為在測試裡不可見。機制與 [mock 遮蔽](/testing/knowledge-cards/mock-masking/)相同——替身忠實模擬方法簽名、跳過被替換那一方的實際行為——差別在範圍。那一篇處理的是替換發生在應用邊界時被跳過的兩層：協議層（訊息的序列與錯誤語意）與環境層（真實延遲與資源限制）。這裡被跳過的是模組內部類別之間的協作。兩派替換掉的外部依賴一樣多，多出來的替身全在模組內。

書市對兩派另有一組慣稱：Sociable 是古典學派（classicist）寫出來的測試形態，Solitary 是倫敦學派（mockist、London school）的。兩組詞的差別在命名者關注的是測試的社交性，還是學派的傳承來源。兩派的原始定義、最完整的一次陳述、以及對倫敦學派的系統性批評各在哪本，見書單的 [驗證自己寫對了](/books/craft/verification/)。

## 可觀察訊號與例子

判斷手上一套測試屬於哪一派，有一個操作程序（前提是手上已經有一套測試；零測試的專案不適用，它還沒有派別可判）：改變模組的內部邏輯、調整類別結構、重新命名內部方法，讓外部行為保持不變。全部測試依然通過就是 Sociable；有測試要跟著改，那些測試就是 Solitary 的，而且耦合線的位置同時現形。用重構的 diff 也看得出來：測試的改動量跟生產程式碼相當、而這次改動沒有改變任何外部行為時，測試耦合的是結構。

這個程序判的是**測試現在耦合在什麼上，不判對錯**。結果是 Solitary 而那個模組確實有它的理由（結構已凍結、失敗定位很貴、或替身是拿來逼出還不存在的介面），那是正確的設計；理由一個都不成立，才是該重畫邊界的訊號。理由清單在 [TDD 的兩種做法](/record/behavior-first-tdd-methodology/)。

兩種定義寫出來的測試長什麼樣，以訂單提交為例。兩者斷言不同的對象。Sociable 只替換跨邊界的 Repository，驗證的是可觀察的結果：

```dart
test('使用者提交訂單成功', () async {
  when(mockRepository.save(any))
      .thenAnswer((_) async => SaveResult.success('order-123'));

  final result = await submitOrderUseCase.execute(order);

  expect(result.isSuccess, true);
  expect(result.orderId, 'order-123');
  // Order、OrderValidator、PriceCalculator 都是真實物件
});
```

Solitary 把協作者全部換成替身，驗證的是呼叫本身：

```dart
test('OrderService.submitOrder calls Repository.save', () async {
  final order = Order.sample();          // 值物件用真實實例，兩派都不替換
  final mockValidator = MockOrderValidator();
  final mockCalculator = MockPriceCalculator();
  final mockRepository = MockOrderRepository();

  when(mockValidator.validate(order)).thenReturn(true);
  when(mockCalculator.calculate(order)).thenReturn(100);
  when(mockRepository.save(order))
      .thenAnswer((_) async => SaveResult.success('order-123'));

  await orderService.submitOrder(order);

  verify(mockRepository.save(order)).called(1);
  verify(mockValidator.validate(order)).called(1);
});
```

## 設計責任

選單元定義的人同時選定了測試失敗時會拿到什麼樣的訊號。Sociable 的紅燈說「這個模組的對外行為變了」，定位範圍是整個模組，而它變紅時外部行為確實變了。Solitary 的紅燈定位精確到類別，代價是重構期間的誤報——測試變紅而外部行為沒壞，成因是內部結構動了，跟 [flaky](/testing/05-test-design-judgment/flaky-test-root-cause/) 那種每次跑結果不同的不確定性來源不同。兩者是把誤報成本與定位成本分配到不同位置，不是精度的高低之分。

替身的角色分布是這個選擇的下游結果。邊界畫在模組時替身只出現在應用邊界，多半是 [stub](/testing/knowledge-cards/stub/)（寫死回應資料）或 fake（有狀態、可運作的簡化實作），任務是讓外部依賴可控；邊界畫在類別時替身深入模組內部，多半是 mock（預設期望、呼叫不符即失敗）與 spy（記錄呼叫供事後檢查），任務是斷言互動。選錯角色的後果在 [test double 分類](/testing/knowledge-cards/test-double-taxonomy/)那張卡。

有一類測試落在兩種定義的分類之外，用它們的判準評會得到誤導的結論：[characterization test](/testing/knowledge-cards/characterization-test/) 斷言的是現狀而非正確性，判準與退場條件在那張卡。

兩派都預設行為由寫程式的人決定，所以兩者都沒有回答「這條斷言的預期值從哪裡來」。那是分野之外的另一個問題，見 [判準的推導來源](/testing/06-agent-authored-code/test-provenance-independence/)。
