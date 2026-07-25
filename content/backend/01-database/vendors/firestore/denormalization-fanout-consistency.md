---
title: "Firestore document 反正規化與一致性維護：fan-out write、副本同步與資料修復"
date: 2026-06-16
description: "Firestore 沒有 JOIN，查詢能力逼著把關聯資料反正規化複製多份；本文展開反正規化的建模決策、fan-out write 維護副本一致、batch 與 transaction 的選擇、五個副本不一致的 production 踩坑，以及反正規化複雜到該回關聯式的邊界"
weight: 14
tags: ["backend", "database", "firestore", "denormalization", "consistency"]
---

> 本文是 [Firestore](/backend/01-database/vendors/firestore/) overview 的 deep article。寫作參照 [Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)。

## 問題情境：改一個使用者名稱要改一千筆

一個社群 app 的貼文列表要顯示作者頭像與名稱。關聯式思路是貼文存 `authorId`、查詢時 JOIN `users` 表。但 Firestore 沒有 JOIN——要嘛 client 每顯示一則貼文就多查一次 `users`（列表 20 則就 20 次額外讀取），要嘛在貼文 document 裡直接存一份 `authorName` 與 `authorAvatar` 副本。為了讀取效率，多數人選後者。

副本一上線就埋了一致性債：使用者改了名稱，他過去發的一千則貼文裡的 `authorName` 還是舊的。改名這個動作從「更新一筆 `users` document」變成「更新一千筆貼文 document」。這篇處理 Firestore 反正規化的建模決策、如何用 fan-out write 維護副本一致、以及這套手段撐不住時的退場。

## 核心概念：反正規化是查詢邊界逼出來的

關聯式資料庫預設正規化，靠 JOIN 在查詢時組合資料；Firestore 沒有 server 端 JOIN，組合資料只有兩條路：client 多次查詢自己組，或寫入時就把要一起讀的資料存在一起。後者就是反正規化——它不是 Firestore 的「壞習慣」，是 client 直連 + 無 JOIN 的查詢模型逼出來的必然建模。

反正規化的判斷單位是 access pattern，不是資料的「正規與否」。問題不是「該不該複製」，而是「這份資料在哪些讀取路徑上要被一起讀到，複製它的一致性維護成本，比每次多查一次划不划算」。判斷有三個輸入：

**讀寫比**。讀多寫少的資料適合反正規化——複製成本攤在少數寫入上、省下大量讀取的額外查詢。作者名稱顯示在每則貼文（高讀），但改名很少（低寫），複製划算。反過來，高頻變動的資料複製多份，每次變動要 fan-out 到所有副本，成本可能超過省下的讀取。

**副本數量的可預測性**。複製到「一個 user 的 profile 摘要」這種固定副本可控；複製到「該 user 的所有貼文」這種隨資料成長無上限的副本，fan-out 的寫入量會隨規模膨脹，要特別評估。

**一致性容忍度**。副本短暫不一致（改名後幾秒內舊貼文還顯示舊名）能不能接受。能容忍最終一致的，反正規化的維護可以非同步、用 Cloud Function 慢慢 fan-out；不能容忍的，要嘛同步 fan-out（貴且有規模上限），要嘛這份資料根本不該複製。

## 配置：fan-out write 維護副本一致

fan-out write 是「一次邏輯更新，寫多個 document」。Firestore 的 `writeBatch` 讓多個寫入 atomic 提交（最多 500 個操作一批），是固定且可控副本數的標準手段：

```javascript
import { writeBatch, doc, collection, query, where, getDocs } from 'firebase/firestore';

// 改名：更新 users/{uid} + fan-out 到該 user 的所有貼文副本
async function renameUser(db, uid, newName) {
  // 1. 更新權威來源
  const userRef = doc(db, 'users', uid);

  // 2. 查出所有要同步的副本
  const postsSnap = await getDocs(
    query(collection(db, 'posts'), where('authorId', '==', uid))
  );

  // 3. batch 提交（超過 500 要分批）
  const ops = [{ ref: userRef, data: { displayName: newName } }];
  postsSnap.forEach((p) => {
    ops.push({ ref: p.ref, data: { authorName: newName } });
  });

  for (let i = 0; i < ops.length; i += 500) {
    const batch = writeBatch(db);
    ops.slice(i, i + 500).forEach((op) => batch.update(op.ref, op.data));
    await batch.commit();
  }
}
```

這裡的關鍵取捨是同步 fan-out 與非同步 fan-out。上面的同步版本在使用者點「儲存」時就把一千筆貼文改完，使用者等待時間隨副本數成長、且超過 500 要分批多次提交，副本數無上限時會撞到不可接受的延遲。非同步版本把權威來源（`users/{uid}`）同步更新，副本同步丟給 Cloud Function 在背景慢慢做：

```javascript
// Cloud Function：onUpdate users document 時 fan-out 到副本
exports.fanoutUserName = functions.firestore
  .document('users/{uid}')
  .onUpdate(async (change, context) => {
    const before = change.before.data();
    const after = change.after.data();
    if (before.displayName === after.displayName) return; // 名稱沒變不做

    const uid = context.params.uid;
    const postsSnap = await admin.firestore()
      .collection('posts').where('authorId', '==', uid).get();

    // 分批 fan-out，背景執行、使用者不等待
    const docs = postsSnap.docs;
    for (let i = 0; i < docs.length; i += 500) {
      const batch = admin.firestore().batch();
      docs.slice(i, i + 500).forEach((d) =>
        batch.update(d.ref, { authorName: after.displayName }));
      await batch.commit();
    }
  });
```

非同步 fan-out 把「使用者體驗的即時性」與「副本的最終一致」分開：權威來源立刻更新、副本最終收斂。代價是中間有一段不一致窗口（改名後到 fan-out 完成前，舊貼文顯示舊名），這對社群 app 的顯示名稱通常可接受。`writeBatch` 與 `transaction` 的選擇在這裡也要分清：fan-out 是「寫多個獨立 document、不依賴彼此既有值」用 `writeBatch`；若更新要依賴讀到的當前值（例如同時扣 A 加 B 且要看當前餘額）才用 `transaction`，但 transaction 在大量 document 的 fan-out 上不適用。

## 故障演練：五個副本不一致的 production 踩坑

#### Case 1：複製了卻沒建 fan-out 路徑

貼文存了 `authorName` 副本，但改名邏輯只更新 `users`，沒人寫 fan-out。副本永遠停在建立時的值。修法：反正規化的建模決策必須連同「誰負責同步副本」一起定，複製一份資料就要有對應的 fan-out write 路徑，沒有 fan-out 的副本是一致性債。

#### Case 2：同步 fan-out 撞到副本數上限

改名時同步更新所有貼文，某個高產出使用者有幾萬則貼文，提交分成幾十批、使用者等了半分鐘還在轉圈、甚至 timeout。修法：副本數無上限的 fan-out 改非同步（Cloud Function 背景做），同步 fan-out 只用在副本數固定且小的場景。

#### Case 3：fan-out 中途失敗留下部分更新

非同步 fan-out 跑到一半 function 掛了，前 500 筆改了、後面沒改，副本處於半新半舊。修法：fan-out function 要可重入（重跑能補完未完成的），或記錄 fan-out 進度；殘留的不一致由[對帳](/backend/knowledge-cards/data-reconciliation/)流程掃出修復（對應 [1.9 Reconciliation 與 Data Repair](/backend/01-database/reconciliation-data-repair/)）。

#### Case 4：雙向反正規化造成更新環

A 存 B 的副本、B 也存 A 的副本，改 A 觸發 fan-out 改 B、又觸發 fan-out 改回 A，function 互相觸發成環。修法：反正規化要有明確的權威方向（誰是 source of truth、誰是副本），副本不反向觸發權威來源的更新。

#### Case 5：把副本當權威來源讀來做判斷

拿貼文裡的 `authorName` 副本去做權限或業務判斷，而非讀 `users` 權威來源。副本在不一致窗口內是舊值，判斷出錯。修法：副本只供顯示，任何需要正確性的判斷讀權威來源；明確標示哪個 document 是 [source of truth](/backend/knowledge-cards/source-of-truth/)、哪些是顯示副本。

## 容量與觀測：fan-out 寫入量與不一致窗口

反正規化的容量帳要算 fan-out 的寫入放大。一次邏輯更新放大成 N 次寫入，N 是副本數，這 N 次寫入計入計費。高頻變動 + 高副本數的組合會讓寫入成本失控——這正是判斷「該不該反正規化」的成本面：省下的讀取 vs 放大的寫入。

不一致窗口是要監控的健康指標：權威來源更新到所有副本收斂的延遲。非同步 fan-out 下這個窗口隨副本數與 function 吞吐變動，異常拉長是 fan-out 積壓的徵兆。觀測還要涵蓋 fan-out 失敗率與重試，接回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。定期跑對帳掃描副本與權威來源的差異，是把潛在不一致從「使用者回報才知道」變成「主動發現修復」，對應 [1.9 Reconciliation](/backend/01-database/reconciliation-data-repair/) 的可驗證、可修復、可稽核流程。

## 邊界與整合：反正規化複雜到該回關聯式

反正規化適合「讀多寫少、副本數可控、能容忍最終一致」的顯示資料。它撐不住的訊號是複製關係長成一張難以追蹤的網——資料被複製到十幾個地方、fan-out 路徑互相依賴、改一個欄位要同步的副本沒人說得清、對帳越來越頻繁。撞到這些訊號時，方向不是把 fan-out 寫得更巧：

- **關聯查詢成為主導需求**：當資料的核心價值在「任意關聯與聚合」（報表、跨實體分析），反正規化是在用副本模擬 JOIN，成本與複雜度都不划算。這是 [Firestore → 自建 relational](/backend/01-database/vendors/firestore/migrate-to-relational/) 的報表牆——relational 的 JOIN 在查詢時組合，省掉整套副本維護
- **副本維護成本超過查詢省下的成本**：高頻變動的資料反正規化，fan-out 放大的寫入成本超過正規化後多查一次的成本，反正規化的前提就不成立
- **巢狀結構保留比拆表更省**：相反方向——有些一起讀寫、不需獨立查詢的關聯資料，在 Firestore 用巢狀 map / array 保留在同一 document 反而比拆 collection 簡單，遷到 relational 時用 [PostgreSQL JSONB](/backend/01-database/vendors/postgresql/jsonb-deep-dive/) 保留，不是所有東西都要拆成正規表

判讀的起點永遠是 access pattern 與讀寫比，不是「正規化是對的、反正規化是妥協」這種預設立場。在 Firestore 裡反正規化是正解，問題只在它的維護成本何時翻轉。

## 下一步路由

- 上層：[Firestore overview](/backend/01-database/vendors/firestore/)（資料形狀與查詢邊界）
- 資料修復：[1.9 Reconciliation 與 Data Repair](/backend/01-database/reconciliation-data-repair/)（副本不一致的對帳與修復）
- 狀態歸屬：[1.8 State Ownership 與 Query Boundary](/backend/01-database/state-ownership-query-boundary/)（權威來源與派生副本的分辨）
- 遷移 driver：[Firestore → 自建 relational](/backend/01-database/vendors/firestore/migrate-to-relational/)（報表牆與反正規化還原）
- 官方：[Firestore data model](https://firebase.google.com/docs/firestore/data-model)、[Batched writes](https://firebase.google.com/docs/firestore/manage-data/transactions)
