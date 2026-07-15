---
title: "一行查詢放哪、一個測試留不留：結構改動後的兩次「還需要存在嗎」"
date: 2026-07-15
draft: false
description: "修完一個應收金額 bug 收尾時，兩個『還需不需要』的問題浮出來。一段『過濾出已結帳品項』的查詢該掛哪一層——inline 在 widget 是洩漏、開一個 service 是儀式，判準是『查詢誰擁有的資料就掛給誰』，答案是既有的 repository。一個為了鎖住修復而寫的測試該不該留——當修復是靠刪掉舊函式、移除參數達成時，那個 bug 被結構免疫了，測試變贅述；判準是『這測試守的失敗模式，結構是否已經替它擋掉』。"
tags: ["flutter", "dart", "ddd", "clean-architecture", "testing", "refactoring", "yagni"]
---

> **觸發場景**：POS 的一個應收金額 bug（未結帳份數被重複扣減）修完後收尾。修法是刪掉舊的 `unsettledCartView(cart, snapshotItems)` 純函式、把邏輯搬進沒有 snapshot 參數的 `ShoppingCart.unsettledView()`。收尾時剩兩塊要決定：一段「過濾出已提前結帳品項」的查詢還 inline 在 widget 裡，該搬哪；一個當初為了鎖住修復而寫的測試，還要不要留
> **疑問來源**：這兩件事表面無關——一個是分層放置、一個是測試取捨；但被同一句話串起來：「這東西，還需要存在嗎？」
> **整理目的**：記下「查詢的責任歸屬」與「被結構免疫掉的測試」兩個判準，以及它們共用的收尾動作
> **本文邊界**：素材是 unipos POS 這次修復收尾的決策記錄。被刪的 `unsettledCartView` 原貌見[「該收多少錢」抽成 pure function](/work-log/dart_unsettled_cart_pure_function/)；查詢層膨脹的前例見[異步查詢系統的過度設計震盪](/work-log/flutter_async_query_overdesign_oscillation/)

---

## 一段查詢的四個候選家

畫面要顯示「已結帳」清單，需要這桌已提前結帳的品項。這份資料只在線上點單快照——一份從後端同步下來、唯讀的線上訂單副本——的 `IOnlineOrderRepository.itemsByCart` 裡，過濾條件是 `isCheckedOut`。收尾當下它長這樣，inline 在桌位卡片 widget：

```dart
final checkedOutItems =
    (Get.find<IOnlineOrderRepository>().itemsByCart.value[cart.id] ??
            const <RemoteOrderSnapshotItem>[])
        .where((item) => item.isCheckedOut)
        .toList();
```

（`Get.find<T>()` 是 GetX 從 DI 容器直接抓服務實例——widget 裡出現這行，等於 UI 層自己伸手到基礎設施拿東西。）

這段程式碼在這次收尾之前，已經在四個家之間搬過：

| 放置點                                 | 問題                                                                                         |
| -------------------------------------- | -------------------------------------------------------------------------------------------- |
| inline 在 widget                       | widget 直接 `Get.find` repository、還知道 `itemsByCart` 結構與 `isCheckedOut` 欄位——分層洩漏 |
| 獨立的 `ICheckedOutItemsQuery` service | 為一個 `.where` 開一個 interface + impl + DI 註冊——儀式；查詢層前科見前例                    |
| controller 自己過濾                    | 能拿掉 widget 的 `Get.find`，但把「怎麼判定 isCheckedOut」放進 presentation 層               |
| 既有的 online-order repository         | 查詢掛在資料擁有者身上                                                                       |

前兩個是兩個相反方向的錯：inline 是**放得太低**（widget 碰基礎設施），獨立 service 是**包得太重**（單一用途的空殼服務，跟前例那輪「先做起來放」的膨脹同一種形狀）。

還有兩個 clean-architecture / DDD 讀者會立刻想到的正統對手，得先擋掉。一個是 **use-case / interactor 層**：把 `.where(isCheckedOut)` 放進一個 interactor。但 `isCheckedOut` 是這份快照的內在查詢、不是跨聚合的業務編排，沒有需要 interactor 承擔的東西，開一層等於又一種儀式。另一個是 **domain 衍生**：上一節才把 `unsettledView` 搬成 `ShoppingCart` 的 domain 方法，這段為何不比照做成 cart 的 computed getter？因為那份快照的擁有者是 repository、不是 cart——cart 手上根本沒有 `itemsByCart` 這份資料可以衍生。

擋掉這兩個之後，真正的問題只剩一個——`Get.find<IOnlineOrderRepository>()` 出現在 widget 裡。要拿掉它，widget 就得改成呼叫 `controller.xxx`；於是剩下的選擇是：過濾邏輯放 controller，還是放 repository。

## 判準：查詢誰擁有的資料，就掛給誰

controller 能做，但它的職責是替 UI 組合、轉接，不是回答「這份快照裡哪些是已結帳」。那份快照的擁有者是 repository——它 own 了 `itemsByCart`，「哪些 item 是 checked out」這個問題落在它的查詢職責內。以責任區分，這行 `.where` 屬於 repository：

```dart
// IOnlineOrderRepository
List<RemoteOrderSnapshotItem> checkedOutItemsFor(String cartId);

// 實作：從自己擁有的快照過濾
@override
List<RemoteOrderSnapshotItem> checkedOutItemsFor(String cartId) =>
    (itemsByCart.value[cartId] ?? const <RemoteOrderSnapshotItem>[])
        .where((item) => item.isCheckedOut)
        .toList();
```

資料流變成 `widget → controller（薄轉接）→ repository.checkedOutItemsFor`。widget 不再知道快照長怎樣，也不知道 `isCheckedOut` 這個欄位存在；controller 只是入口，不含判斷。

這跟「開一個 service」的差別是關鍵：獨立 service 是一個**只為這個查詢而生**的新型別，帶來新的 interface、新的實作、新的 DI 節點；掛回 repository 是把查詢加到一個**本來就存在、也本來就擁有這份資料**的層上——零新型別、零額外註冊。判準是「這份資料歸誰，查詢就歸誰」，而不是「該不該有個地方放查詢」。

這個判準有適用邊界：它針對**單一擁有者的資料內在查詢**。資料橫跨多個 repository、得聚合才答得出來時，「誰擁有」沒有單一答案，那是 use-case 的活；純粹是畫面衍生的概念（哪些要標紅、怎麼排序）不是資料的內在屬性，留在 controller / presentation 反而對。`isCheckedOut` 落在前者——它是快照上實際存在的欄位、跟畫面無關，所以歸 repository。

一個容易被誤判成阻礙的細節：反應式沒有因為多隔一層而斷。多數細粒度反應式系統（GetX、Vue、MobX、Solid 都是）靠「一次重繪過程中同步讀了哪些值」來決定訂閱關係——只要新增的層是同步呼叫、讀取仍發生在同一次重繪內，訂閱就不會斷。對應到 GetX：它追蹤的是 `.value` 讀取發生在哪個 `Obx`（反應式重繪範圍）的執行棧內，只要 `widget → controller → repository` 這條鏈是同步呼叫，`itemsByCart.value` 的讀取仍在 `Obx` 的反應式脈絡裡，快照更新時卡片照樣重繪。「把邏輯往下推一層會不會失去反應式」在同步呼叫下是假問題。

## 一個被結構免疫掉的測試

修復當時，為了鎖住「`unsettledView` 不再重複扣減」，寫了一條測試：餵一車明細、斷言全部呈現、數量不被任何已結帳概念扣掉。收尾時的問題是——這條還有必要嗎？

要回答，得看修復是**怎麼**達成的。舊 bug 的形狀是：`unsettledCartView(cart, snapshotItems)` 假設 `cart.details`（購物車的品項明細）是含已結帳的總量，於是拿 snapshot 的 `isCheckedOut` 從 details 再扣一次；但 details 其實已是淨額，這一扣就把未結帳品項誤刪、應收少算。修法是**刪掉那個吃 snapshot 的函式**、把邏輯搬進 `ShoppingCart.unsettledView()`——一個**沒有 snapshot 參數**的方法，而不是加一個 flag 叫它別扣。

這裡是重點：要重犯同樣的錯，得有人**刻意**替 `unsettledView()` 重新加一個 snapshot 參數、再寫一次扣減。那不是重構時會不小心踩到的東西——扣減所需的輸入根本不在方法簽章裡。這個 bug 被**結構**免疫了。一條斷言「沒有扣減」的測試，守的是一個結構已經擋掉的失敗模式，它變成贅述：它記錄了「我們曾經修過 X」，但不再有機會抓到舊機制的回歸。

這裡要先擋一個反方。有人會說：這條測試守的是一個更寬的正向不變量——「`unsettledView` 呈現的數量不被任何已結帳概念扣減」，而不只是「snapshot 減法」這個特定 bug；就算舊函式已刪，未來若有人拿**全新來源**重寫 `unsettledView`、又悄悄引入扣減，這條 pin 住「數量等於輸入」的測試仍抓得到。這個讀法成立。但那個不變量現在已經由「`unsettledView` 的來源就是淨額 `cart.details`」在資料來源層鎖死——測試只是重述型別與來源已經保證的事。冗餘斷言剩下的是維護成本與假安全感，所以仍然選刪；理由是它冗餘，不是它「不可能再有價值」。

## 判準：測試守的失敗模式，結構是否已經替它擋掉

同一個測試檔裡，另外幾條測的是合併邏輯，跟扣減無關：

| 測試                                         | 守的行為                            | 結構是否免疫                                                      |
| -------------------------------------------- | ----------------------------------- | ----------------------------------------------------------------- |
| ~~全部 details 呈現、不被扣減~~              | 不重複扣減                          | 是——刪函式、移除參數後不可能重犯 → **刪**                         |
| 同 spec 不同 product.id 要合併（regression） | 合併不受 product 物件 identity 影響 | 否——merge loop 還在，換人重構就可能踩 → **留**                    |
| 同 spec 不同 customizations 不可合併         | 合併 key 含口味維度                 | 否——有人簡化 `isSameItem` 就會錯 → **留**                         |
| 合併累加數量 + 收集 `sourceDetailIds`        | 回寫依據不漏                        | 否——`sourceDetailIds` 收集是非平凡的回寫依據、重構可能漏 → **留** |

差別在：「不扣減」靠刪掉舊法就自動免疫；合併的 key 維度、`sourceDetailIds`、product.id 迴歸，是 `unsettledView` 真正非平凡、重構仍可能打破的部分。一個測試的價值，是它抓到**未來**回歸的機率，不是它記錄了**過去**修過什麼。前者才是留下的理由。

這裡有個順帶的陷阱：product.id 那條迴歸，是這個子系統之前就有的守護（真實發生過——`/shoppingCart` 跟 `/products` 兩支 API 回的 product 物件 hash 不一致）。如果因為「不扣減不用測了」順手把整個檔案刪掉，會**連帶失去它**——把一個修過的 bug 重新暴露。「因為 A 不必測、順手砍掉守 B 的測試」是拆測試時常見的連帶失誤。

## 拆測試要連敘事一起改

刪掉「不扣減」那條後，還有一步：檔案層 doc 原本寫「這些測試把『不重複扣減』這個修正鎖住」，group 叫「合併與呈現」。留下的四條全在測合併，沒有一條在測扣減了——敘事跟內容對不上。後人讀到「把不重複扣減鎖住」卻找不到對應的 case，會困惑這檔案到底在守什麼。

所以 doc 改寫成「守住合併的 key 維度與 product 物件 identity 不影響合併」，group 名 `合併與呈現` → `合併`。測試的內容改了，它**自稱在做什麼**也要跟著改——註解和斷言要指向同一個意圖。

## 同一個收尾動作

兩件事表面無關，底下是同一個動作：**結構改動之後，對「還存在的東西」重新問一次「它還需要存在嗎」**。

- 查詢的放置：把 `unsettledView` 從吃 snapshot 改成純從 cart 導出、又把查詢層的空殼 service 拆掉之後，那段 `checkedOutItems` 的舊寫法（inline `Get.find`）就該重新評估——它現在該掛哪一層。
- 測試的取捨：把舊函式刪掉、參數移除之後，那條鎖住舊 bug 的測試也該重新評估——它守的失敗模式還在不在。

判準是同一句：**這東西守的 / 做的事，結構是否已經替它做了？** 是，就拿掉（贅測、儀式）；否，就留下、並放到責任正確的位置。收尾是「把不再需要的東西一起清掉」——包括測試，而不只是「把新加的東西留著」。
