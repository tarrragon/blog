---
title: "Firestore realtime listener 扇出與成本：snapshot 訂閱、re-read 計費與連線規模"
date: 2026-06-16
description: "Firestore 的 snapshot listener 提供即時同步、但訂閱的扇出、查詢結果變動的 re-read 計費與連線數會在規模下變成成本與效能瓶頸；本文展開 listener 的推送模型、訂閱範圍設計、五個 realtime 成本踩坑，以及即時需求超過 listener 該換推送架構的邊界"
weight: 15
tags: ["backend", "database", "firestore", "realtime", "snapshot-listener"]
---

> 本文是 [Firestore](/backend/01-database/vendors/firestore/) overview 的 deep article。寫作參照 [Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)。計費模型以 [官方 pricing](https://firebase.google.com/docs/firestore/pricing) 為準、最後檢查日 2026-06-16。

## 問題情境：即時很爽，帳單很痛

Firestore 的 snapshot listener 是它最有吸引力的能力——client `onSnapshot` 訂閱一個 query，資料一變就即時推送，多裝置同步、協作介面幾乎免費得到。團隊很快把所有列表都改成 listener：訊息列表、通知、儀表板計數，全部即時更新，體驗很好。

帳單在用戶量上來後出問題。Firestore 對 listener 的計費規則是——query 結果裡每個被推送的 document 都計一次 read。一個列表有 100 名觀眾各自訂閱、列表變動推送 50 筆，就是 100 × 50 = 5000 次 read。即時的爽感建立在 re-read 計費上，扇出越大、變動越頻繁，成本成乘積成長。這篇處理 listener 的推送與計費模型、如何設計訂閱範圍把成本壓住、以及即時需求超過 listener 能力時的退場。

## 核心概念：listener 的推送與計費模型

snapshot listener 不是「推送變動的那一筆」這麼簡單。理解它的成本要抓三點：

**初次訂閱讀整個結果集，之後讀變動的部分**。`onSnapshot(query)` 第一次觸發時，query 結果的每個 document 計一次 read（跟一次性 `getDocs` 相同）。之後 query 結果有 document 新增、修改、移出，推送那些變動的 document，各計一次 read。所以 listener 的計費 = 初次結果集大小 + 後續每次變動推送的 document 數。

**計費是 per-listener 的**。同一個 query 被 N 個 client 各自訂閱，是 N 個獨立 listener，變動推送計 N 次。扇出（同一資料多少人在看）直接乘進成本。這跟自建後端用一個 WebSocket broadcast 推給 N 個連線的模型不同——那裡資料讀一次、推 N 份；Firestore listener 是每個訂閱各自從資料庫讀。

**query 範圍決定推送頻率**。訂閱一個寬的 query（整個 collection），collection 裡任何符合的 document 變動都推；訂閱窄的 query（只我相關的那幾筆），只有那幾筆變動才推。listener 成本的設計槓桿是「把訂閱範圍縮到 client 真正要即時看到的最小集合」。

```javascript
import { onSnapshot, query, collection, where, orderBy, limit } from 'firebase/firestore';

// 寬訂閱：整個 messages collection 任何變動都推（成本失控）
const wide = query(collection(db, 'messages'));

// 窄訂閱：只訂這個對話的最近 50 則（成本可控）
const narrow = query(
  collection(db, 'messages'),
  where('conversationId', '==', convId),
  orderBy('createdAt', 'desc'),
  limit(50)
);

const unsub = onSnapshot(narrow, (snap) => {
  snap.docChanges().forEach((change) => {
    // 只處理變動的部分，不是每次重畫整個列表
    if (change.type === 'added') { /* ... */ }
    if (change.type === 'modified') { /* ... */ }
    if (change.type === 'removed') { /* ... */ }
  });
});
// 畫面離開時務必取消訂閱，否則 listener 與計費持續
// unsub();
```

`docChanges()` 是控制成本與效能的關鍵——它只給「跟上次相比變動的 document」，而不是每次都拿整個結果集重畫。用 `limit` 把結果集封頂、用 `where` 把範圍縮到 client 相關，是 listener 成本設計的兩個主要手段。

## 配置：訂閱範圍與生命週期設計

listener 的成本與效能由訂閱範圍和生命週期決定。三個設計原則：

**訂閱跟著畫面生命週期**。listener 在畫面進入時建立、離開時 `unsubscribe()`。最常見的成本洩漏是忘記取消訂閱——使用者切走了，listener 還在背景持續接收推送計費。在元件 unmount、路由切換、app 進背景時取消所有 listener。

**用 `limit` 封頂結果集，配分頁**。即時列表只訂最近 N 筆，往前翻歷史用一次性 `getDocs` 分頁，不訂閱。歷史資料不會變、不需要即時，訂閱它只是白付 re-read。即時的部分小而精，歷史的部分按需一次性拉。

**高扇出的即時值改訂閱彙總 document**。一萬名觀眾要看同一個即時計數，正解是由後端把彙總值寫進一個 summary document、所有人訂閱那一份，而非各自訂閱原始資料加總。扇出仍是一萬個 listener，但每次變動只推一份小 document，而不是推整個結果集——把推送的 payload 壓到最小。這跟 [distributed counter](/backend/01-database/vendors/firestore/distributed-counter-high-frequency-write/) 的 summary 彙總是同一個手段的兩面：那裡解寫入熱點，這裡解讀取扇出。

## 故障演練：五個 realtime 成本踩坑

#### Case 1：把不需要即時的列表也做成 listener

歷史訊息、已讀通知、靜態設定全用 `onSnapshot`，這些資料根本不變或極少變，訂閱它們只是把一次性讀取變成持續掛著的 listener。修法：先問「這個資料 client 在看的時候會不會變、變了要不要立刻看到」，否才用 listener；不變或不需即時的用一次性 `getDocs`。

#### Case 2：忘記 unsubscribe 造成 listener 洩漏

路由切換、元件重建時建了新 listener 沒取消舊的，listener 越積越多、計費持續、記憶體也漏。修法：listener 的建立與取消綁死畫面生命週期，用框架的 cleanup hook（React `useEffect` return、Vue `onUnmounted`）統一管理，app 進背景時主動斷。

#### Case 3：訂閱寬 query 被無關變動轟炸

訂了整個 `orders` collection 想看自己的訂單，結果別人的訂單一變也推給你（雖然規則可能擋讀，但寬 query 本身設計就錯）。修法：query 用 `where` 縮到 client 相關的最小集合，訂閱範圍與 [Security Rules](/backend/01-database/vendors/firestore/security-rules-authz-modeling/) 的授權範圍對齊。

#### Case 4：每次 snapshot 重畫整個列表

`onSnapshot` callback 裡拿 `snap.docs` 整個重建 UI，而不用 `docChanges()`，列表大時每次推送都重畫、UI 卡頓。修法：用 `docChanges()` 只處理 added / modified / removed 的增量，UI 做局部更新。

#### Case 5：高扇出直接訂閱原始資料

直播觀看數讓每個觀眾訂閱原始事件流自己算，扇出 × 結果集大小的 re-read 爆炸。修法：後端彙總寫 summary document，觀眾訂閱 summary 一份，把推送 payload 與 re-read 都壓到最小。

## 容量與觀測：扇出 × 變動頻率的成本估算

listener 成本估算的公式是 `初次訂閱 read + Σ(訂閱數 × 每次變動推送的 document 數)`。把它拆開算：高扇出（很多人訂同一資料）× 高變動頻率（資料常變）× 大結果集（每次推很多筆）三者相乘，是成本爆炸的組合；任一維壓低都有效。設計時對每個 listener 問這三維的量級，乘起來對照預算。

連線數也有規模考量：Firestore 對並行連線與 listener 有規模上限（以官方當前限制為準），超大扇出（百萬級同時在線）會撞到連線層的天花板，而不只是計費問題。觀測上要監控 read 用量的來源拆分——哪些 collection 的 read 來自 listener 推送、哪些來自一次性查詢，把 listener 的 re-read 成本獨立出來看，接回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 與 [9.7 成本邊界](/backend/09-performance-capacity/)。

## 邊界與整合：即時需求超過 listener 該換推送架構

snapshot listener 適合「中等扇出、client 要即時看到自己相關資料變動」的場景——協作編輯、聊天、個人通知、儀表板。它撐不住的訊號是扇出或變動頻率推高 re-read 成本到不划算，或連線規模撞到天花板：

- **超高扇出的廣播**：百萬人看同一場直播的即時數據，per-listener 的 re-read 模型成本遠高於自建一次讀取、WebSocket broadcast 推 N 份的模型。這類純廣播（一份資料推給海量訂閱者）用專門的推送層（自建 WebSocket / SSE、或 pub/sub + 邊緣推送）更划算，見 [03 訊息佇列](/backend/03-message-queue/) 的 fan-out 設計
- **複雜事件處理的即時**：即時推送需要先做跨資料聚合、過濾、轉換，listener 只能訂 query 結果、表達不了。這類要後端處理後再推，listener 不是合適的傳輸層
- **即時是核心且規模化**：當即時同步是產品核心且扇出規模化，整個即時層自建是 [Firestore → 自建 relational](/backend/01-database/vendors/firestore/migrate-to-relational/) 裡「realtime / offline 要重建」這項工作量——遷移時這層最容易被低估

判讀的起點是「這份即時是 client 看自己相關的少量資料，還是海量訂閱者看同一份廣播」。前者 listener 是正解，後者從一開始就該用推送架構，而不是把 listener 的扇出推到極限。

## 下一步路由

- 上層：[Firestore overview](/backend/01-database/vendors/firestore/)（realtime / offline 能力與容量特性）
- sibling：[distributed counter 高頻寫入](/backend/01-database/vendors/firestore/distributed-counter-high-frequency-write/)（summary 彙總的另一面）
- 授權對齊：[Security Rules 授權建模](/backend/01-database/vendors/firestore/security-rules-authz-modeling/)（訂閱範圍與授權範圍一致）
- 推送架構：[03 訊息佇列](/backend/03-message-queue/)（超高扇出 broadcast 的去處）
- 成本邊界：[9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)
- 官方：[Firestore pricing](https://firebase.google.com/docs/firestore/pricing)、[Listen to realtime updates](https://firebase.google.com/docs/firestore/query-data/listen)
