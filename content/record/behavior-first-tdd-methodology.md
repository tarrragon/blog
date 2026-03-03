---
title: "行為優先的TDD方法論 - Sociable Unit Tests實踐指南"
date: 2026-03-04
draft: false
description: "基於行為驅動測試策略，解決TDD痛點根源，透過Sociable Unit Tests實現低維護成本和高重構安全性"
tags: ["TDD", "Sociable Unit Tests", "Behavior Testing", "Kent Beck", "Clean Architecture"]
---

曾經有一段時間，我們團隊對TDD又愛又恨。「寫測試讓我們更有信心」，但「重構時要改一堆測試，還不如不寫」。這種矛盾讓我們反覆懷疑：TDD到底有沒有用？

深入研究Kent Beck的原著和Valentina Jemuović的演講後，才發現問題根本不在TDD，而在於我們誤解了「測試單元」是什麼。

<!--more-->

## 痛苦的根本原因

許多團隊學TDD時，都被教導「每個class寫一個test class，每個method寫一個test method」。這個看似合理的原則，埋下了長期的痛苦。

問題在於，這樣的測試耦合到了程式的**結構**，而非**行為**。只要重構——把一個class拆成兩個、把方法提取到新類別——測試就跟著破裂。維護測試的時間甚至超過寫功能本身。

Kent Beck在《Test Driven Development By Example》第一頁就寫道：

> "Programmer tests should be sensitive to behavior changes and insensitive to structure changes."

測試應該對行為的改變敏感，對結構的改變不敏感。如果重構時測試跟著爆炸，原因就在這裡。

## 測試是可執行的需求規格

需要先轉換一個根本認知：測試不是「驗證實作正確的工具」，而是**用程式碼表達的需求規格書**。

需求定義系統「應該做什麼」，實作是「怎麼做」的一種方式。需求應該保持穩定，實作可以隨時改變。Martin Fowler在《Refactoring》中說：

> "Refactoring is a way of restructuring an existing body of code, altering its internal structure without changing its external behavior."

重構改變內部結構，不改變外部行為。耦合到行為的測試，在重構時自然保持穩定。

## Sociable Unit Tests：把Module當作測試單元

TDD有兩種截然不同的流派。

**Classical TDD**（Kent Beck、Martin Fowler的做法）把Unit定義為Module——一個或多個協同工作的類別組合，對外提供清晰的Public API。測試只透過這個Public API互動，不知道Module內部有哪些類別、它們如何協作。唯一需要Mock的是真正的外部依賴：資料庫、檔案系統、外部服務。這種風格稱為**Sociable Unit Tests**。

**Mockist TDD**（London School）把Unit定義為單一Class，Mock所有協作者。這種風格稱為**Solitary Unit Tests**。

核心差異不在寫法，而在耦合對象：

```
Sociable: Test → [Module API] → Module Implementation（黑盒）
Solitary: Test → Mock(B) → Class A → Class B
                 Mock(C)           → Class C
```

Sociable只有一條耦合線，Solitary有多條。每一條耦合線都是日後的維護成本。

## 重構安全性的驗證

判斷自己的測試是Sociable還是Solitary，有個簡單的驗證方法：

改變Module的內部邏輯、調整類別結構、重新命名內部方法。如果所有測試依然通過，不需要修改，那你寫的是Sociable（正確）。如果任何測試需要跟著改，那你寫的是Solitary（需要重新設計）。

以一個訂單提交的例子來說，Sociable測試看起來像這樣：

```dart
test('使用者提交訂單成功', () async {
  // Given: Mock外部依賴（只Mock Repository）
  when(mockRepository.save(any))
      .thenAnswer((_) async => SaveResult.success('order-123'));

  // When: 透過Use Case API提交訂單
  final result = await submitOrderUseCase.execute(order);

  // Then: 驗證可觀察的行為結果
  expect(result.isSuccess, true);
  expect(result.orderId, 'order-123');
  // 測試不知道Order內部如何計算、驗證
  // 測試使用真實的Domain Entities
});
```

而Solitary測試會是：

```dart
test('OrderService.submitOrder calls Repository.save', () async {
  // Given: Mock所有協作者
  final mockOrder = MockOrder();          // 連Order也Mock了
  final mockValidator = MockOrderValidator();
  final mockCalculator = MockPriceCalculator();

  when(mockValidator.validate(mockOrder)).thenReturn(true);
  when(mockCalculator.calculate(mockOrder)).thenReturn(100);
  when(mockRepository.save(mockOrder))
      .thenAnswer((_) async => SaveResult.success('order-123'));

  // Then: 驗證方法呼叫次數（實作細節）
  verify(mockRepository.save(mockOrder)).called(1);
  // 這個測試一旦重構OrderService的內部邏輯就會破裂
});
```

## Test-First的速度優勢

Test-First（先寫測試）比Test-Last（先寫程式再補測試）快，原因不是省了寫測試的時間，而是問題被發現的時間點不同。

Test-First的Red-Green-Refactor循環強迫你在寫實作之前先思考介面：「這個功能怎麼用？」、「測試容不容易寫？」介面設計問題在寫測試時（最早期）就暴露，修復成本最低。

Test-Last則是程式寫完了才發現難以測試，這時通常意味著設計有問題，要改動的範圍更大。Kent Beck說TDD更快，指的正是這個。

## BDD不是新方法，是修正命名

Dan North在2006年創造「BDD」，不是為了發明新東西，而是為了修正TDD命名造成的混淆。

他發現「Test」這個詞讓開發人員誤以為要測試每個類別和方法，於是用「Behavior」取代，讓意圖更清楚：測試的是行為，不是程式結構。這和Kent Beck 2003年說的完全一致，只是換了個能讓人更直覺理解的詞。

Google在《Software Engineering at Google》中也驗證同樣的結論：「Don't write a test for each method. Write a test for each behavior.」

## 與Clean Architecture的結合

Sociable Unit Tests和Clean Architecture是天然的組合，因為建立在相同原則上：業務邏輯獨立於外部世界。

在Clean Architecture中，Use Cases層是業務邏輯的進入點，對外提供清晰的API，對內只使用Domain Entities和透過介面隔離的外部依賴（Repository、Gateway等）。這個結構天然對應Sociable的需求：Use Cases的Public API就是測試邊界，Domain Entities用真實物件，只有Repository需要Mock。

更重要的是，對Use Cases的Unit Test同時就是業務驗收測試。一個寫著「使用者提交訂單成功」的案例，不需要啟動UI也不需要真實資料庫，但驗證了完整的業務流程。Alistair Cockburn在提出Hexagonal Architecture時說：「Tests are another user of the system.」

並非所有情況都適合Sociable。數學演算法、加密系統這類需要細粒度驗證的場景，精確定位到具體類別比重構穩定性更重要，用Solitary合理。但大多數商業應用不是這類。

## 結論

我們曾以為TDD很痛苦，但那是因為我們測試的是程式**長什麼樣子**，而不是它**做什麼**。

正確的做法只有一句話：測試透過Module的Public API互動，只Mock真正的外部依賴，使用真實的Domain Entities。

這樣的測試在重構時保持穩定，在功能改變時精準報警。Kent Beck、Dan North、Martin Fowler在不同年代說的是同一件事：**測試行為，而非結構**。

---

參考資料：
- Kent Beck，《Test Driven Development By Example》，2003
- Martin Fowler，《Refactoring: Improving the Design of Existing Code》，1999
- Dan North，《Introducing BDD》，2006
- Google，《Software Engineering at Google》，2020
- Valentina (Cupać) Jemuović，[TDD and Clean Architecture - Driven by Behaviour](https://www.youtube.com/watch?v=3wxiQB2-m2k)
