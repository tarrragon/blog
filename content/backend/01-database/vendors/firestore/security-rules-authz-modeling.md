---
title: "Firestore Security Rules 授權建模與可測試化：把規則當程式碼治理"
date: 2026-06-16
description: "Firestore client 直連模型把整個授權控制面壓在 Security Rules 這套 DSL 裡；本文展開規則的求值模型、把授權拆成可組合 function、用 emulator 寫單元測試、五個把規則寫成資安漏洞的 production 踩坑，以及規則複雜度撞牆時把授權拉回後端的邊界"
weight: 12
tags: ["backend", "database", "firestore", "security-rules", "authorization"]
---

> 本文是 [Firestore](/backend/01-database/vendors/firestore/) overview 的 deep article。寫作參照 [Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)。規則語法以 [官方 Security Rules 文件](https://firebase.google.com/docs/firestore/security/get-started) 為準、最後檢查日 2026-06-16。

## 問題情境：授權沒有後端可以藏

自建後端的授權有一個天然的藏身處：所有讀寫都過 API，權限檢查寫在 service 層，前端拿不到的資料就是拿不到。Firestore 的 client 直連模型把這個藏身處拿掉了——前端 SDK 直接連資料庫，唯一擋在「任何人都能讀整個 collection」與「正確授權」之間的，就是 Security Rules。規則寫錯一條，等於把資料庫對公網敞開。

這個責任轉移最常見的引爆點是上線後的滲透測試或 bug bounty：報告指出「未登入就能用 REST API 拉出整張 `users` collection」。根因幾乎都是同一類——開發期為了方便把規則設成 `allow read, write: if true`，上線忘了收。Firestore 的規則是控制面的全部，這篇處理它的求值模型、如何把它寫成可測試的程式碼、以及它撐不住時的退場路線。

## 核心概念：規則的求值模型

Firestore Security Rules 是一套宣告式 DSL，掛在 `match` path 上、對每個讀寫請求求值。理解它要抓住四個跟後端授權不同的點：

**規則不是 filter，是 allow/deny 判定**。一條 `allow read: if <condition>` 不會「只回傳符合條件的 document」——它是對「這次請求能不能執行」的布林判定。query 若可能讀到任何不符合規則的 document，整個 query 被拒絕，不是默默過濾。這逼著 client 的 query 必須自帶與規則一致的條件（例如 `where('ownerId', '==', uid)`），規則才放行。

**規則預設拒絕**。沒有 `match` 命中的 path 一律拒絕。`rules_version = '2'` 下，`match /{document=**}` 遞迴匹配所有 subcollection，要小心別用一條寬鬆的遞迴規則蓋掉底下該嚴格的 path。

**請求脈絡來自 `request` 與 `resource`**。`request.auth` 是已驗證的身分（`request.auth.uid`、`request.auth.token` 的 custom claims）；`request.resource.data` 是寫入後的 document 狀態；`resource.data` 是寫入前的既有狀態。授權與資料驗證都在這幾個物件上展開。

**跨 document 查詢用 `get()` / `exists()`**。判斷「這個 user 是不是這個 project 的成員」要去讀另一份 document，用 `get(/databases/$(database)/documents/projects/$(pid)/members/$(uid))`。每個 `get()` 是一次額外讀取、計入計費，也有每請求次數上限（規則內 document access 有上限，設計時要省著用）。

基本骨架：

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /notes/{noteId} {
      allow read: if request.auth != null
                  && resource.data.ownerId == request.auth.uid;
      allow create: if request.auth != null
                    && request.resource.data.ownerId == request.auth.uid;
      allow update, delete: if request.auth != null
                            && resource.data.ownerId == request.auth.uid;
    }
  }
}
```

`read` 用 `resource.data`（既有 document），`create` 用 `request.resource.data`（沒有既有狀態），`update` 兩者都要看——把 `read` / `create` / `update` / `delete` 分開是建模的起點，混成一條 `allow read, write` 是後面所有漏洞的源頭。

## 配置：把授權拆成可組合 function

規則一旦超過幾個 collection，inline 的 `if` 條件會重複且難讀。把授權判斷抽成 `function`，讓每條規則讀起來像在描述意圖，是讓規則可維護的核心手段：

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    function isSignedIn() {
      return request.auth != null;
    }

    function isOwner(docData) {
      return isSignedIn() && docData.ownerId == request.auth.uid;
    }

    function isProjectMember(projectId) {
      return isSignedIn()
        && exists(/databases/$(database)/documents/projects/$(projectId)/members/$(request.auth.uid));
    }

    function hasRole(projectId, role) {
      return isProjectMember(projectId)
        && get(/databases/$(database)/documents/projects/$(projectId)/members/$(request.auth.uid)).data.role == role;
    }

    // 寫入時欄位白名單：禁止 client 竄改 ownerId / createdAt
    function fieldsUnchanged(fields) {
      return request.resource.data.diff(resource.data).affectedKeys().hasOnly(fields);
    }

    match /projects/{projectId} {
      allow read: if isProjectMember(projectId);
      allow update: if hasRole(projectId, 'admin')
                    && fieldsUnchanged(['name', 'description', 'updatedAt']);
      allow delete: if hasRole(projectId, 'owner');

      match /tasks/{taskId} {
        allow read: if isProjectMember(projectId);
        allow create: if isProjectMember(projectId)
                      && request.resource.data.createdBy == request.auth.uid;
        allow update, delete: if isProjectMember(projectId);
      }
    }
  }
}
```

這裡有三個建模手段值得展開。第一，`isProjectMember` / `hasRole` 把「成員資格」與「角色」的判斷集中成單一定義，授權邏輯改一處全站生效，避免同一條規則散落在十個 collection。第二，`fieldsUnchanged` 用 `diff().affectedKeys().hasOnly()` 把「這次 update 只准動哪些欄位」寫成白名單——這擋掉 client 直接改 `ownerId` 把別人的資料佔為己有的攻擊，是 client 直連模型必備的欄位級防護。第三，custom claims（`request.auth.token.role`）適合放跨專案、低頻變動的全域角色；per-resource 的成員資格用 `get()` 查 membership document，因為 claims 改動要等 token 刷新、不適合表達即時變動的權限。

## 配置：用 emulator 把規則寫成單元測試

規則是安全邊界，改一條就要驗證沒開新洞——這要求規則像程式碼一樣有測試。Firebase Emulator + `@firebase/rules-unit-testing` 讓規則在本地用真實求值引擎跑斷言，不必碰雲端：

```javascript
// rules.test.js — 用 Jest / Mocha 跑
const {
  initializeTestEnvironment,
  assertFails,
  assertSucceeds,
} = require('@firebase/rules-unit-testing');
const { setDoc, getDoc, doc } = require('firebase/firestore');

let testEnv;

beforeAll(async () => {
  testEnv = await initializeTestEnvironment({
    projectId: 'demo-notes',
    firestore: { rules: require('fs').readFileSync('firestore.rules', 'utf8') },
  });
});

afterAll(async () => { await testEnv.cleanup(); });
beforeEach(async () => { await testEnv.clearFirestore(); });

test('owner 能讀自己的 note', async () => {
  // 用 admin context 預先種一筆資料、繞過規則
  await testEnv.withSecurityRulesDisabled(async (ctx) => {
    await setDoc(doc(ctx.firestore(), 'notes/n1'), { ownerId: 'alice' });
  });
  const alice = testEnv.authenticatedContext('alice').firestore();
  await assertSucceeds(getDoc(doc(alice, 'notes/n1')));
});

test('非 owner 不能讀別人的 note', async () => {
  await testEnv.withSecurityRulesDisabled(async (ctx) => {
    await setDoc(doc(ctx.firestore(), 'notes/n1'), { ownerId: 'alice' });
  });
  const bob = testEnv.authenticatedContext('bob').firestore();
  await assertFails(getDoc(doc(bob, 'notes/n1')));
});

test('未登入完全擋下', async () => {
  const anon = testEnv.unauthenticatedContext().firestore();
  await assertFails(getDoc(doc(anon, 'notes/n1')));
});

test('client 不能竄改 ownerId', async () => {
  await testEnv.withSecurityRulesDisabled(async (ctx) => {
    await setDoc(doc(ctx.firestore(), 'notes/n1'), { ownerId: 'alice', text: 'hi' });
  });
  const alice = testEnv.authenticatedContext('alice').firestore();
  await assertFails(setDoc(doc(alice, 'notes/n1'), { ownerId: 'bob', text: 'hi' }));
});
```

啟動方式 `firebase emulators:exec --only firestore "npm test"`，讓測試在 CI 跑。測試要覆蓋的不只是 happy path——每條規則至少要有「正向放行」「越權拒絕」「未登入拒絕」「欄位竄改拒絕」四類斷言。`assertFails` 比 `assertSucceeds` 更重要：它證明的是「該擋的有擋住」，正是滲透測試會打的點。把這套測試接進 release gate，規則變更才有 evidence 可交（對應 [6.8 release gate](/backend/06-reliability/release-gate/)）。

## 故障演練：五個把規則寫成漏洞的 production 踩坑

#### Case 1：`allow read, write: if true` 上線沒收

開發期為了快，把規則開全放，上線忘改。任何人用公開的 project config（前端 bundle 裡就有）就能 REST 拉整個資料庫。修法：規則預設從 deny 起手，開發期的寬鬆規則進不了 main branch；CI 跑一條 lint 掃 `if true`，命中即 fail。這是 [1.5 資料層紅隊](/backend/01-database/red-team-data-layer/) 越權查詢路徑的最便宜目標。

#### Case 2：`read` 沒拆 `get` 與 `list`

`allow read` 同時涵蓋讀單一 document（`get`）與查整個 collection（`list`）。規則只想開「讀自己那筆」，卻因為沒拆 `list`，讓 client 能 `list` 整個 collection 撈別人的資料。修法：對 collection-level query 敏感的 path，把 `read` 拆成 `allow get` 與 `allow list`，`list` 條件更嚴或直接關閉、改走後端彙整。

#### Case 3：信任 `request.resource.data` 的內容沒驗證

`create` 規則只檢查 `request.auth != null`，沒驗證寫入內容。client 自己塞 `role: 'admin'` 或 `balance: 999999` 進 document。修法：寫入規則要驗證關鍵欄位的值與型別（`request.resource.data.role == 'member'`、`request.resource.data.amount is int`），敏感欄位（角色、金額、狀態）的權威值不該由 client 寫入、改由 Cloud Function 或後端寫。

#### Case 4：遞迴 `match /{document=**}` 蓋掉嚴格規則

頂層放一條 `match /{document=**} { allow read: if isSignedIn(); }` 圖方便，結果它遞迴命中所有 subcollection，把底下本來該按成員資格嚴格控管的 `members` collection 也開成「登入即可讀」。修法：避免寬鬆的遞迴萬用規則；授權顆粒不同的 path 各自寫明確 `match`。

#### Case 5：規則複雜到沒人能 review

授權邏輯長到幾百行、巢狀 `get()` 互相依賴，改一條沒人敢保證沒開新洞、也沒有測試。修法：這是規則撐不住的訊號（見下方邊界段）——超過這個複雜度，授權該拉回後端中介層，而不是繼續在 DSL 裡長。

## 容量與觀測：`get()` 計費與規則複雜度上限

規則內的每個 `get()` / `exists()` 是一次 document 讀取，計入計費，且單次請求的 document access 有數量上限（以 [官方限制](https://firebase.google.com/docs/firestore/security/rules-conditions) 為準）。高頻讀取路徑若每次都 `get()` 查 membership，成本與延遲都會浮現。優化方向有二：把低頻變動的權限（全域角色）放進 custom claims，從 token 直接讀、零額外 document access；把成員資格設計成可由 document path 直接判斷（例如 membership document 的 ID 就是 uid，用 `exists()` 而非 `get()` 撈整份）。

觀測上，授權問題不會在規則層留下豐富 log——被拒的請求 client 端收到 `permission-denied`。要把這類錯誤從 client 回報、或在關鍵寫入路徑改走 Cloud Function 以取得 server 端 audit log，接回 [7.7 稽核軌跡](/backend/07-security-data-protection/)。規則本身的變更要進版本控制、每次 deploy 留 diff，授權變更才可回溯。

## 邊界與整合：規則撐不住時把授權拉回後端

Security Rules 適合表達「資源的擁有者與成員能做什麼」這類 resource-scoped 授權。它撐不住的訊號很明確：授權依賴跨多個 document 的複雜聚合判斷、需要呼叫外部系統、規則複雜到無法 review、或業務規則頻繁變動到規則 deploy 跟不上。撞到這些訊號時，正確的動作是把該塊授權移出 client 直連路徑，而非把規則寫得更巧：

- **敏感寫入改走 Cloud Function / 後端 API**：金額、狀態機轉換、跨實體一致性的寫入，由 server 端驗證後以 admin 權限寫入，規則對 client 直接關閉這些 path 的寫入
- **複雜授權整體下沉**：當規則複雜度本身成為風險，這是 [Firestore → 自建 relational](/backend/01-database/vendors/firestore/migrate-to-relational/) playbook 裡「授權控制面失控」這面牆——把授權拉回後端中介層是遷移的 driver 之一

判讀的單位仍是逐路徑：簡單的 owner-scoped 資料留在規則 + client 直連，複雜或敏感的部分走後端。不是非此即彼。

## 下一步路由

- 上層：[Firestore overview](/backend/01-database/vendors/firestore/)（服務定位與查詢邊界）
- 安全驗證：[1.5 資料層紅隊](/backend/01-database/red-team-data-layer/)（越權查詢與資料外洩路徑）
- 遷移 driver：[Firestore → 自建 relational](/backend/01-database/vendors/firestore/migrate-to-relational/)（授權控制面失控的退場）
- 發布證據：[6.8 release gate](/backend/06-reliability/release-gate/)（規則測試接進 gate）
- 官方：[Security Rules get started](https://firebase.google.com/docs/firestore/security/get-started)、[Rules unit testing](https://firebase.google.com/docs/rules/unit-tests)、[Rules conditions limits](https://firebase.google.com/docs/firestore/security/rules-conditions)
