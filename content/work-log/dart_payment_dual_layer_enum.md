---
title: "16 種支付渠道、4 種行為分類 — 分層 enum：保真層與行為層的粒度分工"
date: 2026-07-10
draft: false
description: "同一個分類系統要同時服務序列化（要無損）跟 UI 行為分流（要粗粒度）時，單一 enum 選哪個粒度都錯。解法是分層：保真層無損對齊後端完整列舉、行為層收斂成行為真正分歧的少數大類、層間用 exhaustive switch 衍生——粒度轉換獲得編譯期保證。"
tags: ["dart", "flutter", "enum", "ddd", "type-design", "pos", "payment"]
---

> **觸發場景**：POS 專案的支付方式建模。後端 API 的支付 type 是 1 到 16 的完整列舉（現金、錢包、信用卡、支付寶、微信、Touch'n Go、各種商城資產……），前端 UI 的行為分歧卻只有四種：要不要找零、限不限會員、要不要驗證支付結果
> **疑問來源**：一個 enum 做 16 個成員、每個掛行為謂詞？還是做 4 個大類、序列化時想辦法？兩個方向都彆扭
> **整理目的**：記下「分類系統的粒度由消費者決定、多種消費者就分層」的建模方式
> **本文邊界**：素材是該專案現行的 payment model；三層結構（16 → 4 → 3）是這個 domain 的結果、分層的推導方式可遷移

---

## 兩個消費者、兩種粒度需求

支付方式這個概念在系統裡有兩類消費者，粒度需求相反：

**序列化要無損。** 後端的 `type` 欄位是 1 到 16 的完整列舉，而且不只結帳請求用——`payment_logs` 記錄實際扣款渠道時，會回到細分等級（商城 TC、商城 UC、USDN）。前端若把 16 種壓成 4 大類存，資料回不去了：兩筆 log 一筆走支付寶一筆走微信，壓縮後都是「第三方支付」，對帳時無從區分。

**行為分流要粗。** UI 關心的問題是「要不要開找零輸入」「這個支付方式非會員能不能選」「結帳前要不要跑驗證」——這些行為在 16 種渠道上高度重複：七種第三方支付的答案全部相同。把行為謂詞掛在 16 個成員上，是 16 × N 個決策、其中大半是複製貼上，新增渠道時要重答一整排實際上沒有分歧的問題。

單一 enum 不管選哪個粒度，都是犧牲其中一個消費者。

## 分層解法：channel 保真、type 承行為、category 是橋

這個專案的做法是兩個 enum 各司其職：

```dart
/// 後端的支付方式 type（1~16 完整對應，無損）
enum PaymentChannel {
  cash, walletLegacy, creditCard, alipay, wechatPay, touchNGo,
  payNow, favePay, grabPay, vnPay, mallTC, mallUC, mallUSDN,
  visaUCard, exchangeUSDN, exchangeUSDT, ...;

  /// 對應的大分類
  PaymentType get category => switch (this) {
    cash => PaymentType.cash,
    walletLegacy || mallTC || mallUC || ... => PaymentType.wallet,
    creditCard || visaUCard => PaymentType.creditCard,
    alipay || wechatPay || ... => PaymentType.thirdPartyPayment,
    ...
  };
}

/// 前端行為分流的四大類
enum PaymentType {
  cash, wallet, creditCard, thirdPartyPayment, unknown;

  bool get requiresChange => switch (this) { cash => true, ... };
  bool get requiresMemberLogin => switch (this) { wallet => true, ... };
  bool get isMemberOnly => switch (this) { wallet => true, ... };
}
```

`category` 這座橋用 exhaustive switch 實作，買到的是**編譯期的完整性保證**：後端加了第 17 種渠道、前端 enum 補成員的那一刻，switch 不涵蓋就編譯失敗——「新渠道歸哪類」這個決策無法被遺忘。行為謂詞同樣全部用 exhaustive switch，`PaymentType` 加成員時每個行為問題都會被編譯器逐一逼答。

實際上還有第三層：`CheckoutPattern`（三種結帳流程——標準、後端請款、POS 請款）由 `PaymentType.checkoutPattern` 衍生。三層的粒度各自對應一種消費者：**序列化要 16、UI 行為要 4、結帳流程要 3**——每一層都是「這個消費者眼中真正有分歧的數量」。

## 保真層承載的、行為層放不下的知識

分層之後，後端行為的細節知識有了正確的歸宿——它們屬於個別渠道、不屬於大類：

- `walletLegacy` 是會員錢包的總入口：會員不指定動用哪種資產、後端依 TC → UC → USDN 順序混合扣款、`payment_logs` 回實際扣到的細分渠道
- 部分商城資產不開放單獨結帳（`legacyWalletMergedChannels`）、只供 walletLegacy 動用，因此不列入 POS 的支付選項
- 交易所資產的餘額目前拿不到，前端對這兩個 channel 直接放行、由後端在實際扣款時裁決

這些知識若硬塞進 4 大類的行為層，wallet 那一類會長出「有些成員其實……」的例外註解——例外是粒度選錯的訊號。放在 channel 層，每條知識就是它所屬成員的屬性或註解，自然原子。

## 判準與對照

收束成可操作的一句：**分類系統的粒度不是自己的屬性、是消費者的屬性**。消費者只有一種，單一 enum 就夠；消費者多種且粒度需求不同，分層、層間用 exhaustive switch 衍生。判斷分幾層的方式是列消費者：這個 case 是「序列化、UI 行為、結帳流程」三個消費者、所以三層。

反向的對照組在同族案例裡有兩個：[一個 `ReadingStatus` enum 混裝閱讀狀態、書籍格式、書籍來源三種概念](/work-log/flutter_exception_error_category_invariant/)所引的分類軸不正交問題——那是把多個**正交軸**壓進一個 enum；本文的 16 vs 4 則是同一個軸的**不同粒度**。前者的修法是拆軸、本文的修法是分層，訊號都是例外與重複開始增生。

## 相關閱讀

- 分類軸不正交的姊妹篇：[Exception 型別綁 ErrorCategory 的建構不變式](/work-log/flutter_exception_error_category_invariant/)——軸錯了分層救不了、要先拆軸
- 同專案的 model 分工：[同一個品項、四個 model](/work-log/dart_pos_item_four_lifecycle_models/)——那篇是生命週期軸的分模型、本文是粒度軸的分層，同一個「一個結構不硬撐多種語意」的原則
- 概念地基：[DDD 領域驅動設計指南](/ddd/)——value object 與枚舉也是建模的一部分
