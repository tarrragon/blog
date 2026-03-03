---
title: "BDD 測試方法論"
date: 2026-03-04
draft: false
description: "行為驅動開發測試策略，整合 Clean Architecture 和 TDD 流程，透過測試行為而非實作降低維護成本"
tags: ["測試", "BDD", "方法論", "Clean Architecture", "TDD"]
---

三個月的重構週期結束後，我們檢視了測試套件，發現一個令人沮喪的問題：每次修改內部實作，即使業務邏輯完全沒變，也需要跟著修改大量測試。一個 Repository 實作替換，導致二十幾個測試需要逐一調整。

這不是測試該有的樣子。問題根源在於測試耦合了實作細節，而非行為。

<!--more-->

## BDD 的核心定位

BDD 不是 TDD 的替代，而是 TDD 的演進。它要求測試描述系統的「行為」而非「實作」。

行為是使用者視角觀察到的系統反應；實作是程式內部的技術細節。這個區別看起來簡單，實際撰寫測試時卻很容易模糊。

BDD 解決三個問題：

**測試維護成本高**。傳統單元測試緊密耦合實作細節，重構時即使行為沒變，測試仍需大量修改。BDD 讓重構時測試保持穩定。

**需求追溯困難**。測試充滿技術細節，無法對應業務需求。Given-When-Then 場景即是需求文件，測試即規格。

**溝通成本高**。開發、測試和業務人員用不同語言描述系統行為。BDD 統一使用業務語言，建立共通溝通基礎。

我們的分工是：Clean Architecture 定義架構分層，TDD 四階段流程定義開發節奏，BDD 定義測試內容和撰寫規範。

## Given-When-Then 結構

Given 描述系統的初始狀態，必須明確完整，只包含與此場景相關的資料。常見錯誤是前置條件模糊，或包含大量無關測試資料。

When 描述使用者執行的操作，必須是單一動作，使用業務語言。「呼叫 Repository 的 save 方法」是技術術語；「使用者提交訂單」是業務語言。一個 When 不能包含多個動作。

Then 描述執行後的狀態變化或結果，必須是可觀察的行為。「Repository 的 save 方法被呼叫一次」是實作細節；「訂單成功儲存並回傳訂單編號」是可觀察的行為。

判斷行為還是實作的方法很簡單：使用者能否觀察到？改變實作會影響這個結果嗎？產品經理需要關心嗎？都是「能觀察、不影響、需要關心」就是行為，反之是實作細節。

## 行為測試和實作測試的差異

測試實作：

```dart
test('OrderRepository.save should call database.insert', () {
  repository.save(order);
  verify(database.insert('orders', order.toJson()));
});
```

這個測試關注「如何儲存」，替換資料庫或重構儲存邏輯就會失敗。

測試行為：

```dart
test('使用者提交訂單 - 訂單成功儲存', () async {
  // Given: 使用者已選擇商品並填寫完整資訊
  final order = validOrder;

  // When: 使用者提交訂單
  final result = await submitOrderUseCase.execute(order);

  // Then: 系統確認訂單已儲存
  expect(result.isSuccess, true);
  expect(result.orderId, isNotEmpty);
});
```

這個測試關注「訂單是否成功儲存」，重構儲存機制不會影響結果。

測試描述的視角同樣重要。從技術元件角度：

```dart
test('當 Repository 回傳 null 時 UseCase 拋出例外', () { ... });
```

從使用者視角：

```dart
test('使用者提交訂單失敗 - 商品庫存不足', () {
  // Given: 商品庫存為 0
  // When: 使用者嘗試提交訂單
  // Then: 系統回應「庫存不足」錯誤
});
```

## 分層測試策略

BDD 不適用所有架構層級，每層特性不同，測試策略也不同。

**UseCase 層**是 BDD 的核心應用層，代表完整的使用者操作流程，必須使用 Given-When-Then 結構，涵蓋所有業務場景。

**Domain 層**包含核心業務規則、值物件驗證和實體不變量，需要細緻的邊界條件測試，單元測試更適合。

**Behavior 層**負責 ViewModel 轉換和事件處理，只有複雜轉換邏輯需要獨立測試，簡單轉換由 UseCase 層覆蓋即可。

**UI 層**測試成本高，只測試關鍵互動路徑，使用整合測試。

**Interface 層**只定義契約，沒有實作邏輯，不需要測試。

## Mock 策略

核心原則：只 Mock 外層依賴，不 Mock 內層邏輯。

外層依賴（Repository、Service、Event Publisher）透過 Interface 進行 Mock，隔離外部系統。內層邏輯（Domain Entity、Value Object）必須使用真實物件，確保測試涵蓋真實業務邏輯。

正確寫法：

```dart
test('使用者提交訂單成功', () async {
  // Mock Repository（外層依賴）
  final mockRepository = MockOrderRepository();
  when(mockRepository.save(any))
      .thenAnswer((_) async => SaveResult.success('order-123'));

  // 使用真實的 Domain Entity（內層邏輯）
  final order = Order(
    amount: OrderAmount(100),
    userId: UserId('user-001'),
  );

  final useCase = SubmitOrderUseCase(repository: mockRepository);
  final result = await useCase.execute(order);

  expect(result.isSuccess, true);
  expect(result.orderId, 'order-123');
});
```

錯誤寫法是 Mock Domain Entity：

```dart
test('使用者提交訂單成功', () {
  final mockOrder = MockOrder();
  when(mockOrder.validate()).thenReturn(true);
  // 沒有測試到任何真實業務邏輯
});
```

## 與 TDD 四階段整合

**階段一（功能設計）**：從需求識別使用者行為場景。「使用者可以提交訂單」需要提取多個場景：成功提交、庫存不足失敗、金額無效失敗等，每個場景涵蓋正常流程、異常流程和邊界條件。

**階段二（測試設計）**：將行為場景轉換為可執行的測試程式碼，先建立結構，設置 Mock，再依 Given-When-Then 填入邏輯。

**階段三（實作策略）**：測試先行。先完成所有測試場景並確認失敗（Red），才開始實作 UseCase 讓測試通過（Green）。

**階段四（重構優化）**：重構時，行為測試必須保持穩定。重構導致測試需要修改，代表測試耦合了實作。

判斷重構品質的標準很清楚：替換 Repository 實作、改變演算法，不應讓測試失敗；改變業務規則、調整可觀察的錯誤訊息，才應讓測試失敗。

## 常見挑戰

### 測試覆蓋率盲點

BDD 強調測試「重要行為」，可能讓某些程式碼未被覆蓋。混合策略解決這個問題：UseCase 層 100% BDD 測試，Domain 層複雜邏輯 100% 單元測試，整體維持 80% 程式碼覆蓋率目標。

### 學習曲線

從「測試實作」轉向「測試行為」需要思維轉換，初期容易寫出「假行為測試」（實際上還是在測試實作）。建立範例庫和測試模板很有幫助：

```dart
test('[業務場景描述] - 成功', () async {
  // Given: [前置條件]
  final input = [準備測試資料];
  [設置 Mock 行為];

  // When: [觸發動作]
  final result = await useCase.execute(input);

  // Then: [預期結果]
  expect(result.isSuccess, true);
  expect([驗證業務結果]);
});
```

### 邊界條件容易被忽略

業務場景描述容易遺漏技術性的邊界條件（null、異常、極端值）。每個 UseCase 最少需要：一個正常流程、兩個異常流程、三個邊界條件。建立技術性測試檢查清單並在 Code Review 重點確認。

### 測試設置複雜度

UseCase 層的 BDD 測試需要 Mock 多個依賴，建立 Test Helper 和 Builder Pattern 減少重複：

```dart
class UseCaseTestHelper {
  static MockOrderRepository createMockRepository({
    required SaveResult saveResult,
  }) {
    final mock = MockOrderRepository();
    when(mock.save(any)).thenAnswer((_) async => saveResult);
    return mock;
  }
}

class OrderBuilder {
  int _amount = 100;
  String _userId = 'user-001';

  OrderBuilder withAmount(int amount) {
    _amount = amount;
    return this;
  }

  Order build() => Order(
    amount: OrderAmount(_amount),
    userId: UserId(_userId),
  );
}
```

### 行為粒度

粒度太粗，失敗時難以定位；太細則接近單元測試，失去 BDD 優勢。採用「一個 UseCase 等於一個核心行為」的原則：UseCase 代表完整業務流程，名稱以動詞開頭（Submit, Cancel, Query），所有測試場景屬於同一個業務流程。

### 業務需求變更

需求變更時測試場景仍需更新。集中管理業務規則常數減少影響範圍：

```dart
class OrderBusinessRules {
  static const int freeShippingThreshold = 1000;
  static const int maxOrderAmount = 100000;
  static const int minOrderAmount = 1;
}
```

## 完整範例

以「使用者提交訂單」為例：

```dart
group('SubmitOrderUseCase', () {
  late MockOrderRepository mockRepository;
  late MockInventoryService mockInventoryService;
  late MockEventPublisher mockEventPublisher;
  late SubmitOrderUseCase useCase;

  setUp(() {
    mockRepository = MockOrderRepository();
    mockInventoryService = MockInventoryService();
    mockEventPublisher = MockEventPublisher();
    useCase = SubmitOrderUseCase(
      repository: mockRepository,
      inventoryService: mockInventoryService,
      eventPublisher: mockEventPublisher,
    );
  });

  group('正常流程', () {
    test('使用者提交訂單成功', () async {
      // Given: 使用者已選擇商品且填寫完整資訊
      final order = Order(
        amount: OrderAmount(100),
        userId: UserId('user-001'),
        items: [OrderItem(productId: 'prod-001', quantity: 2)],
        shippingAddress: Address(city: '台北市', district: '信義區'),
      );
      when(mockInventoryService.checkStock('prod-001'))
          .thenAnswer((_) async => StockStatus.available);
      when(mockRepository.save(any))
          .thenAnswer((_) async => SaveResult.success('order-123'));

      // When: 使用者點擊「提交訂單」
      final result = await useCase.execute(order);

      // Then: 系統確認訂單已儲存並回傳訂單編號
      expect(result.isSuccess, true);
      expect(result.orderId, 'order-123');
      verify(mockEventPublisher.publish(any.having(
        (e) => e.type, 'event type', EventType.orderCreated,
      ))).called(1);
    });
  });

  group('異常流程', () {
    test('使用者提交訂單失敗 - 商品庫存不足', () async {
      // Given: 選擇的商品庫存為 0
      final order = Order(
        amount: OrderAmount(100),
        userId: UserId('user-001'),
        items: [OrderItem(productId: 'prod-001', quantity: 2)],
      );
      when(mockInventoryService.checkStock('prod-001'))
          .thenAnswer((_) async => StockStatus.outOfStock);

      // When: 使用者點擊「提交訂單」
      final result = await useCase.execute(order);

      // Then: 系統回應庫存不足錯誤，不儲存訂單
      expect(result.isSuccess, false);
      expect(result.error, ErrorType.outOfStock);
      verifyNever(mockRepository.save(any));
    });

    test('使用者提交訂單失敗 - Repository 儲存失敗', () async {
      // Given: Repository 無法儲存（網路錯誤）
      final order = Order(
        amount: OrderAmount(100),
        userId: UserId('user-001'),
        items: [OrderItem(productId: 'prod-001', quantity: 1)],
      );
      when(mockInventoryService.checkStock(any))
          .thenAnswer((_) async => StockStatus.available);
      when(mockRepository.save(any))
          .thenAnswer((_) async => SaveResult.failure('網路連線失敗'));

      // When: 使用者點擊「提交訂單」
      final result = await useCase.execute(order);

      // Then: 系統回應訂單提交失敗
      expect(result.isSuccess, false);
      expect(result.error, ErrorType.saveFailed);
    });
  });

  group('邊界條件', () {
    test('使用者提交訂單失敗 - 訂單金額為 0', () async {
      final order = Order(
        amount: OrderAmount(0),
        userId: UserId('user-001'),
        items: [],
      );
      final result = await useCase.execute(order);
      expect(result.isSuccess, false);
      expect(result.error, ErrorType.invalidAmount);
    });

    test('建立負數金額訂單拋出例外', () {
      expect(
        () => Order(amount: OrderAmount(-100), userId: UserId('user-001')),
        throwsA(isA<InvalidAmountException>()),
      );
    });

    test('使用者提交訂單失敗 - 訂單金額超過上限', () async {
      final order = Order(
        amount: OrderAmount(1000001),
        userId: UserId('user-001'),
        items: [OrderItem(productId: 'prod-001', quantity: 10000)],
      );
      final result = await useCase.execute(order);
      expect(result.isSuccess, false);
      expect(result.error, ErrorType.amountExceedsLimit);
    });
  });
});
```

## 結論

回頭看最初那個重構週期，二十幾個因為替換 Repository 實作而失敗的測試，問題很清楚：測試在監視實作細節，而不是守護業務行為。

切換到 BDD 之後，同樣的重構只需確認業務行為沒有改變，測試套件就能保持穩定。

但 BDD 不是萬靈丹。它需要思維轉換，需要建立明確規範，需要持續 Code Review 維持品質。混合策略（UseCase 層 BDD、Domain 層單元測試、UI 層整合測試）才能真正發揮效果。
