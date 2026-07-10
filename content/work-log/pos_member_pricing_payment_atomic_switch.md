---
title: "會員身分、計價、支付方式必須一起換 — 耦合欄位的原子切換"
date: 2026-07-10
draft: false
description: "多個狀態欄位被同一條業務規則綁住時，分開的 setter 會製造不一致的中間態；把切換收成單一方法、一次狀態更新內同步全部欄位，並注意衍生值重算的順序。以 POS 結帳的會員登出重算為例，含不變式收進 model 的 canCheckout 設計。"
tags: ["dart", "flutter", "ddd", "invariant", "state-management", "pos"]
---

> **觸發場景**：POS 結帳流程有一條業務規則：會員用會員價、且只能用會員資產（wallet）支付；非會員用售價、支付方式排除 wallet。追「結帳中登出會員」的實作時，發現這個切換牽動三個欄位跟一個重算順序
> **疑問來源**：`updateMember` 為什麼強制要求呼叫端同時提供新的支付方式、放棄了單純 setter 的簡單介面？
> **整理目的**：記下「被同一條業務規則綁住的多個欄位」的切換設計——原子性、順序、以及不變式該住在哪
> **本文邊界**：素材是一個 Flutter POS App 的結帳 model；GetX 的 Rx 是實作載體、原子切換的推導不綁框架

---

## 三個欄位、一條規則

結帳 context 的商業規則寫在 class 註解上：

> - 會員：僅能使用會員資產（wallet），因為計價走 memberPrice
> - 非會員：所有啟用的支付方式，但排除 wallet
> - 消費者若要改用其他支付方式，員工需先從結帳頁登出會員，讓計價回到 sellingPrice

拆開看，「會員身分」牽動兩個下游：**計價**（`subtotal` 依 `hasMember` 對每個品項取 `memberPrice` 或 `sellingPrice`）跟**可用支付方式**（會員限 wallet、非會員排除 wallet）。三者被同一條規則綁住：任何一個單獨變動，狀態就進入業務上不存在的組合——例如「身分是會員、支付方式停在現金、計價卻走會員價」。

## 分開的 setter 是不一致中間態的製造機

如果 model 提供獨立的 `setMember()` 跟 `setPaymentMethod()`，正確的切換就要靠每個呼叫端自己記得兩個都呼叫、而且順序對。UI 是響應式的（`Obx` 監聽狀態流、副屏透過 `stateStream` 同步實收找零），兩次分開的狀態更新之間，那個不一致的中間態會真的被渲染出來、也會真的被推到副屏。

這個專案的做法是把切換收成一個方法、強制原子性：

```dart
void updateMember(Member? newMember, {required PaymentMethod? targetPaymentMethod}) {
  final resolvedPayment = targetPaymentMethod ?? _state.value.paymentMethod;
  _state.value = _state.value.copyWith(
    member: newMember,
    memberId: newMember?.id,
    paymentMethod: resolvedPayment,
  );
  // 應付金額依更新後的會員身分重算，故實收金額在 member 寫入後才重設
  resetInputAmount();
}
```

兩個設計點。第一，`targetPaymentMethod` 是 `required`——呼叫端無法「只換會員、支付方式以後再說」，簽名本身就把「兩者要一起決定」寫死了（這是把約束做進介面、不是寫在文件請大家記得）。第二，member 跟 paymentMethod 在**同一次** `copyWith` 內寫入，狀態流的訂閱者永遠看不到只換了一半的組合。

## 順序敏感：衍生值要在來源更新之後重算

第三個欄位 `inputAmount`（員工輸入的實收金額）的處理暴露了一個容易寫錯的順序問題。應付金額 `subtotal` 是衍生值——它依「當下的會員身分」對品項逐一取價。登出會員時實收金額要重設為新的應付金額，而這個重設**必須發生在 member 寫入之後**：先重設的話，`subtotal` 還在用舊身分計價、重設進去的是舊金額。

程式碼裡那行註解（「應付金額依更新後的會員身分重算，故實收金額在 member 寫入後才重設」）就是在守這個順序。characterization test 把行為釘死：

```dart
// 會員價 90 × 2 = 180
expect(ctx.subtotal.toString(), '180');
ctx.updateMember(null, targetPaymentMethod: PaymentMethod.cash());
// 售價 100 × 2 = 200、實收同步重設
expect(ctx.subtotal.toString(), '200');
expect(ctx.inputAmount.toString(), '200');
```

一般化的判讀：**耦合欄位群裡若有衍生值，切換順序是「來源先、衍生後」**；把重算寫在來源更新的同一個方法尾端（而不是交給呼叫端），順序就不會在某個呼叫點被弄反。

## 不變式住在 model：UI 只問、不拼

「能不能結帳」的完整判斷也收在同一個 model 裡：`canCheckout` 依序檢查空車、金額足夠（wallet 走餘額檢查、現金走輸入金額比對、第三方支付暫時信任後端）、需要會員的支付方式有沒有會員、需要 consumer token 的有沒有有效 token；`cannotCheckoutError` 回傳對應的錯誤碼枚舉供 UI 顯示。外層 UI 的職責縮到最小：

```dart
if (!context.canCheckout) {
  final error = context.cannotCheckoutError;
  Popup.exception(code: error!.code, message: error.messageKey.tr);
  return;
}
```

判斷邏輯集中的價值在演化時顯現：支付方式的種類會長（這個專案的第三方支付跟信用卡驗證都還標著 todo），每長一種只改 model 的判斷、所有 UI 呼叫點不動。反向的做法——每個結帳按鈕自己拼「空車嗎、錢夠嗎、會員登入了嗎」——會讓每次規則變動都要掃全部呼叫點。

## 相關閱讀

- 概念地基：[DDD 領域驅動設計指南](/ddd/) 的不變式強制層次章節——本文的 `required` 參數與單次狀態更新是「把約束做進介面」的實例
- 原則層：[#222 約束要讓違反路徑走不通](/report/design-intent-needs-enforcement-layer/)——分開的 setter 就是一條沒關的逃生口
- 同專案同 model 的另一個切面：[桌子跟購物車是兩個聚合](/work-log/pos_table_cart_lifecycle_decoupling/)——那篇談生命週期解耦、本文談耦合欄位的原子性，一個拆、一個綁，判準都來自業務規則本身
