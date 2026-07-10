---
title: "只活在結帳流程裡的領域物件 — ephemeral model 與「Rx 外殼、immutable 內核」"
date: 2026-07-10
draft: false
description: "流程型狀態（結帳中的輸入金額、支付方式、會員）建模成生命週期等於流程的 ephemeral 物件：結完即丟、下次全新，殘留狀態忘記重置的 bug 被結構性消滅。實作形態是 reactive 外殼包 immutable 內核——對外只開語意化變更方法、每次變更是原子的狀態替換。"
tags: ["flutter", "dart", "getx", "state-management", "ddd", "immutable", "pos"]
---

> **觸發場景**：POS 專案的結帳流程有一批只在結帳期間有意義的狀態——輸入金額、選定的支付方式、掃碼取得的 consumer token、結帳模式。常見的歸宿是散落在 controller 的欄位裡、流程結束後逐一重置
> **疑問來源**：這批狀態在這個專案被收進一個叫 `CheckoutContext` 的物件、註解明寫「結帳完成或取消後，此物件即被丟棄」——為什麼要為短命狀態建一個正式的 model？
> **整理目的**：記下 ephemeral 領域物件的建模價值、以及「Rx 外殼 + immutable 內核」這個 GetX 生態下的狀態設計形態
> **本文邊界**：素材是該專案現行的 `CheckoutContext` 實作；Rx 是 GetX 的機制、「reactive 外殼包 immutable 內核」的形態在其他狀態方案（ValueNotifier、signal）同樣成立

---

## 為什麼短命狀態值得一個正式的 model

「結帳流程」是一個有明確開始與結束的業務概念，它期間的狀態既不屬於任何 entity（輸入到一半的收款金額不是訂單的屬性）、也不該活得比流程久。散落在 controller 欄位的版本有兩個慢性病：狀態的邊界看不見（哪些欄位屬於「這次結帳」、哪些是頁面的，全靠記憶），以及**流程結束後的重置靠人工逐欄清**——同專案家族裡[新增欄位忘記同步 reset](/work-log/reset_state_leak_cross_test/) 那類 bug 的溫床。

ephemeral 物件把兩個問題一次解掉：進入結帳時 `CheckoutContext.create(...)` 建新物件、結完或取消即丟棄引用。**丟棄就是重置**——下次結帳拿到的是全新物件，「殘留狀態」在結構上不存在，欄位加再多也不會多出一條「記得清它」的義務。生命週期的語意也直接寫在型別上：看到 `CheckoutContext` 就知道這批狀態活多久、誰擁有它。

建構工廠同時表達了業務情境的分岔：`create(cart: ...)` 從遠端購物車建（餐廳模式、有桌位與掛單）、`createFromLocalCart(items: ...)` 從本地品項建（零售模式、無遠端 cart）——兩種模式的差異被收在建構路徑、流程中的其餘程式碼對此無感。

## Rx 外殼、immutable 內核

實作形態是兩層各司其職：

```dart
class CheckoutContext {
  final Rx<_CheckoutState> _state;          // reactive 外殼：私有

  Money get subtotal => _state.value.subtotal;      // 讀：委託 getter
  bool get canCheckout => _state.value.canCheckout;

  void updateInputAmount(Money amount) {             // 寫：語意化方法
    _state.value = _state.value.copyWith(inputAmount: amount);
  }
}

class _CheckoutState {                       // immutable 內核：私有 class
  final Money inputAmount;
  final PaymentMethod paymentMethod;
  ...
  _CheckoutState copyWith({...}) => _CheckoutState(...);
}
```

分工是：**immutable 內核**保證每次變更是一次原子的整體替換——`_state.value = old.copyWith(...)`，訂閱者永遠看到一致的快照、不會撞見改到一半的狀態（[會員/計價/支付的原子切換](/work-log/pos_member_pricing_payment_atomic_switch/)就是靠這層保證成立的）。**Rx 外殼**提供響應性——UI 用 `Obx(() => Text('應付: ${context.subtotal}'))` 自動跟著變、副屏透過 `stateStream` 訂閱同一個狀態流同步實收與找零。

同樣重要的是**沒有開放的東西**：`_state` 私有、`_CheckoutState` 私有，外部拿不到 Rx 也拿不到內核——變更的唯一入口是 `updateInputAmount` 這批語意化方法。對照直接暴露 `Rx<CheckoutState>` 讓呼叫端自己 `.value = ...` 的寫法：那會把「哪些變更是合法的」交還給每個呼叫端。這是把逃生口關掉的狀態管理版。

## 不變式住在內核、錯誤是結構化的

「能不能結帳」的判斷收在內核的 `canCheckout` / `cannotCheckoutError`，後者回傳的不是布林也不是字串、是 enum：

```dart
enum CheckoutErrorCode implements ErrorCode {
  cartEmpty('CK001', 'shopping_cart_empty'),
  balanceInsufficient('CK002', 'balance_insufficient'),
  memberNotLogin('CK004', 'member_not_login'),
  consumerTokenMissing('CK007', 'checkout_error_consumer_token_missing'),
  ...
}
```

每個錯誤碼帶穩定代碼（CK001）跟翻譯 key——UI 拿到直接 `error.messageKey.tr` 顯示、log 記代碼可追。這是[Domain 層硬編碼中文](/work-log/flutter_domain_layer_i18n_hardcoded_text/)那篇分層原則的正面實作：model 回代碼、呈現層翻譯，而且從第一天就長對、不用事後遷移 947 處。

## 判讀徵兆

- controller 裡有一批欄位在某個流程結束時要「記得全部重置」——ephemeral 物件的候選，丟棄比重置可靠
- 流程狀態的擁有者不明（頁面退出時該不該清？跨頁要不要帶？）——生命週期沒有型別化，先回答「這批狀態跟哪個業務流程同壽命」
- reactive 狀態直接暴露可寫的 `.value` / `.state` 給呼叫端——變更入口失控的起點，收斂成語意化方法
- 狀態變更方法一次只改一個欄位、耦合欄位靠呼叫端連續呼叫——中間態會被訂閱者看到，改成單次 copyWith 的原子替換

## 相關閱讀

- 同一個 model 的另外兩個切面：[會員/計價/支付原子切換](/work-log/pos_member_pricing_payment_atomic_switch/)（耦合欄位的單次替換）、[桌子跟購物車是兩個聚合](/work-log/pos_table_cart_lifecycle_decoupling/)（結帳模式兩布林的組合空間）
- 被結構性消滅的 bug 家族：[新增欄位忘記同步 reset](/work-log/reset_state_leak_cross_test/)——人工重置清單 vs 丟棄即重置
- 概念地基：[DDD 領域驅動設計指南](/ddd/)——entity 生命週期章節、ephemeral 物件是「生命週期由業務流程定義」的極短端
