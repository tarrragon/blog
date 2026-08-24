---
title: "行為優先的 TDD：測試耦合行為、不耦合結構"
slug: "behavior-first-tdd-methodology"
date: 2026-03-04
draft: false
description: "重構時測試大量壞掉、或在「該不該 mock 這個協作者」上需要一個可執行的立場時，本站對兩派 TDD 分歧的選擇與推導"
tags: ["TDD", "Sociable Unit Tests", "Behavior Testing", "Kent Beck", "Clean Architecture"]
---

本站在 TDD 的兩派分歧上採行為優先：測試透過模組的公開 API 互動、只 mock 跨越應用邊界的外部依賴，也就是 Sociable Unit Tests 這一派。這篇記錄這個選擇的推導與操作方式；兩派各自最強的原著該讀哪本、每本代表什麼位置，由書單的 [驗證自己寫對了](/books/craft/verification/) 承接。

<!--more-->

## 問題的形狀：測試耦合到了結構

「每個 class 寫一個 test class、每個 method 寫一個 test method」是常見的入門教法。照這個教法寫出來的測試，耦合的對象是程式的**結構**而不是**行為**：把一個 class 拆成兩個、把方法搬到新類別——外部行為完全沒變，測試卻大量壞掉。

判讀訊號可以直接拿重構的 diff 來看：測試的改動量跟生產程式碼相當甚至更多、而這次改動沒有改變任何外部行為時，測試耦合的就是結構。這種處境下「維護測試的成本高於它提供的保護、還不如不寫」是一個理性的結論——要修的不是「採不採用 TDD」，是測試耦合的對象。

Kent Beck 與 Kelly Sutton 後來在 [Test Desiderata](https://testdesiderata.com/) 把這件事寫成兩條獨立的性質：**behavioral**（測試要對受測程式的行為改變敏感）與 **structure-insensitive**（程式結構改變時，測試的結果不應該跟著變）。重構時測試大量壞掉，違反的是第二條。

## 測試是可執行的需求規格

這個立場建立在一個前置認知上：測試不是「驗證實作正確的工具」，而是**用程式碼表達的需求規格**。

需求定義系統應該做什麼，實作是怎麼做的其中一種方式。需求保持穩定、實作隨時可換——Martin Fowler 在《Refactoring》給重構的定義正是這個分界：在不改變外部行為的前提下，調整程式的內部結構。耦合在行為上的測試，在這個定義下的重構裡自然保持穩定。

## 兩派的分歧在「單元」的定義

TDD 的兩派差在把什麼當成測試的單元。

**Classical TDD**（Kent Beck、Martin Fowler 的做法）把單元定義為模組——一個或多個協同工作的類別組合，對外提供公開 API。測試只透過這個 API 互動，看不到模組內部有哪些類別、它們怎麼協作；需要 mock 的只有真正的外部依賴——資料庫、檔案系統、外部服務。這種風格稱為 **Sociable Unit Tests**。

**Mockist TDD**（倫敦學派）把單元定義為單一 class，mock 掉所有協作者。這種風格稱為 **Solitary Unit Tests**。

核心差異在耦合線的數量：

```text
Sociable: Test → [Module API] → Module Implementation（黑盒）
Solitary: Test → Mock(B) → Class A → Class B
                 Mock(C)           → Class C
```

Sociable 只有一條耦合線，Solitary 有多條，而每一條耦合線都是日後的維護成本——內部結構每動一次，掛在結構上的耦合線就要跟著修一次。

## 兩種測試長什麼樣

以訂單提交為例，Sociable 測試只 mock 跨邊界的 Repository：

```dart
test('使用者提交訂單成功', () async {
  // Given: 只 mock 外部依賴（Repository）
  when(mockRepository.save(any))
      .thenAnswer((_) async => SaveResult.success('order-123'));

  // When: 透過 Use Case API 提交訂單
  final result = await submitOrderUseCase.execute(order);

  // Then: 驗證可觀察的行為結果
  expect(result.isSuccess, true);
  expect(result.orderId, 'order-123');
  // 測試不知道 Order 內部如何計算、驗證
  // 測試使用真實的 Domain Entities
});
```

Solitary 測試把協作者全部換成 mock、驗證的是呼叫本身：

```dart
test('OrderService.submitOrder calls Repository.save', () async {
  // Given: mock 所有協作者
  final mockOrder = MockOrder();          // 連 Order 也 mock 了
  final mockValidator = MockOrderValidator();
  final mockCalculator = MockPriceCalculator();

  when(mockValidator.validate(mockOrder)).thenReturn(true);
  when(mockCalculator.calculate(mockOrder)).thenReturn(100);
  when(mockRepository.save(mockOrder))
      .thenAnswer((_) async => SaveResult.success('order-123'));

  // Then: 驗證方法呼叫次數（實作細節）
  verify(mockRepository.save(mockOrder)).called(1);
  // OrderService 的內部邏輯一重構，這個測試就會壞掉
});
```

## 重構安全性的自我檢驗

手上的測試耦合到哪裡，可以用一個操作程序驗出來：改變模組的內部邏輯、調整類別結構、重新命名內部方法——外部行為保持不變。全部測試依然通過、一個都不用改，測試耦合的是行為；有任何測試要跟著改，那些測試耦合的就是結構，耦合線的位置也同時現形——要修的就是它們。

## Test-First 的優勢在問題被發現的時間點

Test-First（先寫測試）比 Test-Last（先寫程式再補測試）快，差別在設計問題暴露的時間點。

Red-Green-Refactor 的循環把「這個功能怎麼用、介面好不好用」的思考排在寫實作之前——介面設計的問題在寫測試的當下就暴露，那是修復成本最低的時刻。Test-Last 的順序是程式寫完了才發現難以測試，而難以測試多半意味著設計問題，這時要改動的範圍已經大了。Kent Beck 說 TDD 更快，指的是這個時間點差，而不是打字比較少。

## BDD 是命名修正，不是新方法

Dan North 在 2006 年提出 [BDD](https://dannorth.net/introducing-bdd/)，動機是修正「Test」這個詞造成的誤導：這個詞讓人以為要測試每個類別和方法，換成「Behavior」之後，意圖回到原位——測的是行為，不是程式結構。這跟 Kent Beck 2003 年在《Test Driven Development: By Example》示範的做法一致，換的是更難被誤解的詞。

《Software Engineering at Google》的測試章給了同一條規則，直接寫成小節標題：Test Behaviors, Not Methods。

## 跟 Clean Architecture 的組合

Sociable Unit Tests 跟 Clean Architecture 建立在同一條前提上——業務邏輯獨立於外部世界——所以兩者組合起來沒有額外的對接成本。

Clean Architecture 的 Use Cases 層是業務邏輯的進入點：對外提供公開 API，對內只使用 Domain Entities、透過介面隔離外部依賴（Repository、Gateway）。這個結構直接給出 Sociable 需要的三個條件：Use Case 的公開 API 是測試邊界，Domain Entities 用真實物件，要 mock 的只有 Repository 這一層。

這個組合多買到一件事：對 Use Case 的單元測試同時就是業務驗收測試。一個名為「使用者提交訂單成功」的測試案例，不需要啟動 UI、不需要真實資料庫，驗證的卻是完整的業務流程——Alistair Cockburn 的 Hexagonal Architecture 把測試當成系統的另一種使用者，講的是同一個結構性質。

## 邊界：Solitary 合理的場景

數學演算法、加密系統這類需要細粒度驗證的場景，「壞掉時精確定位到具體類別」比「重構時測試不動」更有價值，用 Solitary 合理。

第二類是行為快照——替沒有測試的程式碼先架一層保護再動手，Feathers 的入場技術。這類測試斷言的是現狀而不是正確性，耦合結構是它的工作方式。它原本的定位是短期的入場資格：拆解依賴的期間先有回饋，正確性測試補上之後就移除。程式碼交給 agent 大幅改寫成為常態之後，這個定位的規模變了——每一次交出去的重構都需要先錄下現有行為的一層保護，而那層保護的存續期間跟著重構的節奏走，不再是一次性的。

存續變長帶來一個要主動管理的責任：退場條件。同一段行為被正確性測試覆蓋之後，快照要移除，否則兩份對同一行為的斷言會各自演化並分岔，而分岔的那一刻沒有人會知道該相信哪一份。判準與操作方式在 [characterization test](/testing/knowledge-cards/characterization-test/) 那張卡。

多數商業應用的長期測試不屬於這兩類。

## 這個立場處理的是哪一半

Sociable 與 Solitary 的分歧問的是「單元怎麼定義」，而這個問題預設行為由寫程式的人決定：測試該耦合行為不耦合結構，前提是那個行為就是想要的行為。程式碼由 agent 產出時多出一個問題——行為由誰決定、憑什麼相信它是需求要的那一個。

這不是同一個問題的延伸，是它旁邊的另一個問題。本篇的立場在那個情境下照舊成立，而且理由更強：agent 重構的頻率與幅度都比人高，耦合在結構上的測試誤報成本隨之上升。「agent 可以順手把壞掉的測試修好」不構成反駁——測試在重構後被重新產生，意味著它重新對齊了新的實作，包含新引入的缺陷，修好的那一刻它作為回歸網的功能就歸零。

改變的是這個立場不再足夠。判準的來源與可信度那一層由 [模組六：Agent 產出程式碼的驗證](/testing/06-agent-authored-code/)承接。

Test-First 在同一個情境下也多了一個理由。本篇給的理由是設計問題暴露的時間點，服務的是人的認知負荷；先寫測試在 agent 產出時另外製造出一件事——實作沒有可照抄的對象，於是判準的來源與實作分開。判斷一組測試還剩多少驗證力，第一個問題就是它的預期值從哪裡長出來——[判準的推導來源](/testing/06-agent-authored-code/test-provenance-independence/)那一章處理這件事。

## 這個立場接到哪裡

兩派原著與對倫敦學派的系統性批評該讀哪本，走書單的 [驗證自己寫對了](/books/craft/verification/)——Kent Beck 的原始定義、Freeman 與 Pryce 的倫敦學派完整主張、Khorikov 的四支柱批評，各本的位置那篇有交代。

測試分層怎麼設計、協議整合怎麼驗證，走 [Testing 測試策略](/testing/)；診斷完之後斷言與 mock 邊界實際怎麼改，走 [測試設計判斷](/testing/05-test-design-judgment/)；程式碼由 agent 產出而不打算逐行讀時，判準該落在哪走 [模組六](/testing/06-agent-authored-code/)；沒有測試的既有程式碼要先取得入場資格，走書單的 [改既有的程式](/books/craft/changing-existing-code/)。

---

參考資料：

- Kent Beck，《Test Driven Development: By Example》，2003
- Kent Beck 與 Kelly Sutton，[Test Desiderata](https://testdesiderata.com/)
- Martin Fowler，《Refactoring: Improving the Design of Existing Code》，第二版 2018
- Dan North，[Introducing BDD](https://dannorth.net/introducing-bdd/)，2006
- Google，《Software Engineering at Google》，2020
- Valentina (Cupać) Jemuović，[TDD and Clean Architecture - Driven by Behaviour](https://www.youtube.com/watch?v=3wxiQB2-m2k)
