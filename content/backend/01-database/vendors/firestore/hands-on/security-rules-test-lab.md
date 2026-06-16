---
title: "Firestore Security Rules Test Lab"
date: 2026-06-16
description: "用 @firebase/rules-unit-testing 在 emulator 上把 Security Rules 寫成自動化測試：放行 / 越權拒絕 / 未登入拒絕 / 欄位竄改拒絕四類斷言、firebase emulators:exec 在 CI 跑、把規則測試接進 release gate"
tags: ["backend", "database", "firestore", "hands-on", "security-rules", "testing"]
---

> 本文是 [Firestore Hands-on 操作路線](/backend/01-database/vendors/firestore/hands-on/) 的 lab，實作 [Security Rules 授權建模](/backend/01-database/vendors/firestore/security-rules-authz-modeling/) deep article 的測試方法。前置環境見 [Local emulator quickstart](/backend/01-database/vendors/firestore/hands-on/local-emulator-quickstart/)。測試 API 以 [Rules unit testing 文件](https://firebase.google.com/docs/rules/unit-tests) 為準、最後檢查日 2026-06-16。

Firestore Security Rules test lab 的核心責任是把授權規則變成可自動驗證的測試。規則是 client 直連模型的整個控制面，改一條就要證明沒開新洞——這個 lab 用 `@firebase/rules-unit-testing` 在 emulator 上對規則跑斷言，產出可接進 CI 與 release gate 的測試 evidence。

本文的驗收標準是：你能對一組規則寫出「放行 / 越權拒絕 / 未登入拒絕 / 欄位竄改拒絕」四類斷言、用 `firebase emulators:exec` 一鍵跑完、並看到 `assertFails` 確實證明該擋的有擋住。

## Lab 環境與依賴

沿用 [quickstart](/backend/01-database/vendors/firestore/hands-on/local-emulator-quickstart/) 的工作區與 `firebase.json` / `firestore.rules`。再裝測試依賴。

```bash
cd /tmp/firestore-lab
npm install --save-dev @firebase/rules-unit-testing firebase jest
```

驗收前置是 `firestore.rules` 存在（quickstart 已建立 owner-scoped 規則）與 `firebase.json` 宣告了 Firestore emulator。

## 升級規則：加入欄位竄改防護

quickstart 的規則擋了越權讀寫，但還沒擋「owner 改自己 note 時偷改 `ownerId` 把資料轉走」。先把規則升級到帶欄位白名單，讓測試有更多面向可驗。

```bash
cat > firestore.rules <<'RULES'
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    function isSignedIn() { return request.auth != null; }

    function ownsExisting() {
      return isSignedIn() && resource.data.ownerId == request.auth.uid;
    }

    function onlyChanges(fields) {
      return request.resource.data.diff(resource.data).affectedKeys().hasOnly(fields);
    }

    match /notes/{noteId} {
      allow read: if ownsExisting();
      allow create: if isSignedIn()
                    && request.resource.data.ownerId == request.auth.uid;
      allow update: if ownsExisting() && onlyChanges(['text', 'updatedAt']);
      allow delete: if ownsExisting();
    }
  }
}
RULES
```

`onlyChanges(['text', 'updatedAt'])` 是這版的重點：update 只准動 `text` 與 `updatedAt`，碰 `ownerId` 直接拒絕。下面的測試會驗證它。

## 寫測試：四類斷言

測試的核心責任是覆蓋「該放行的放行、該拒絕的拒絕」。`initializeTestEnvironment` 載入規則、`authenticatedContext` 模擬登入身分、`assertSucceeds` / `assertFails` 對操作斷言。預先種資料用 `withSecurityRulesDisabled` 繞過規則。

```bash
cat > rules.test.js <<'JS'
const {
  initializeTestEnvironment, assertFails, assertSucceeds,
} = require('@firebase/rules-unit-testing');
const { doc, getDoc, setDoc, updateDoc } = require('firebase/firestore');
const fs = require('fs');

let testEnv;

beforeAll(async () => {
  testEnv = await initializeTestEnvironment({
    projectId: 'demo-firestore-lab',
    firestore: { rules: fs.readFileSync('firestore.rules', 'utf8') },
  });
});
afterAll(async () => { await testEnv.cleanup(); });
beforeEach(async () => {
  await testEnv.clearFirestore();
  await testEnv.withSecurityRulesDisabled(async (ctx) => {
    await setDoc(doc(ctx.firestore(), 'notes/n1'),
      { ownerId: 'alice', text: 'hi', updatedAt: 0 });
  });
});

// 1. 放行：owner 讀自己的
test('owner reads own note', async () => {
  const db = testEnv.authenticatedContext('alice').firestore();
  await assertSucceeds(getDoc(doc(db, 'notes/n1')));
});

// 2. 越權拒絕：非 owner 讀別人的
test('non-owner cannot read', async () => {
  const db = testEnv.authenticatedContext('bob').firestore();
  await assertFails(getDoc(doc(db, 'notes/n1')));
});

// 3. 未登入拒絕
test('unauthenticated denied', async () => {
  const db = testEnv.unauthenticatedContext().firestore();
  await assertFails(getDoc(doc(db, 'notes/n1')));
});

// 4. 欄位竄改拒絕：owner 偷改 ownerId
test('owner cannot change ownerId', async () => {
  const db = testEnv.authenticatedContext('alice').firestore();
  await assertFails(updateDoc(doc(db, 'notes/n1'), { ownerId: 'bob' }));
});

// 4b. 正當 update 放行
test('owner can edit text', async () => {
  const db = testEnv.authenticatedContext('alice').firestore();
  await assertSucceeds(updateDoc(doc(db, 'notes/n1'), { text: 'edited', updatedAt: 1 }));
});
JS
```

四類斷言裡 `assertFails` 比 `assertSucceeds` 更重要——它證明的是攻擊路徑被擋住，正是滲透測試會打的點。每條規則至少要有「正向放行 + 至少一條拒絕」配對，光測 happy path 證明不了授權安全。

## 一鍵跑：emulators:exec

跑測試的核心責任是讓它在乾淨 emulator 上自動化執行。`firebase emulators:exec` 啟動 emulator、跑指定命令、結束後關閉——適合 CI，不需要手動開關 emulator。

```bash
cat > package.json.test <<'JSON'
{ "scripts": { "test:rules": "jest rules.test.js" } }
JSON
# 把 test:rules script 併進既有 package.json 後執行：

firebase emulators:exec --only firestore --project demo-firestore-lab "npx jest rules.test.js"
```

預期輸出五個測試全 pass：

```text
PASS  ./rules.test.js
  owner reads own note (passed)
  non-owner cannot read (passed)
  unauthenticated denied (passed)
  owner cannot change ownerId (passed)
  owner can edit text (passed)

Test Suites: 1 passed, 1 total
Tests:       5 passed, 5 total
```

（Jest 預設 reporter 每行會印一個通過標記、此處以 `(passed)` 文字呈現，實際終端輸出為工具自身格式。）

## 故意改壞驗證測試有效

測試的價值在於它會抓到回歸。把規則改回 `allow read, write: if true` 再跑，應看到「越權拒絕」「未登入拒絕」「欄位竄改拒絕」三個測試 fail——這證明測試確實守在攻擊路徑上，而不是恆綠的假測試。

```bash
# 暫時把規則改成全放行
printf "rules_version='2';\nservice cloud.firestore{match /databases/{db}/documents{match /{d=**}{allow read,write:if true;}}}" > firestore.rules
firebase emulators:exec --only firestore --project demo-firestore-lab "npx jest rules.test.js"
# 預期：3 個 assertFails 測試 fail（該擋的沒擋）
# 驗證完改回上面的正確規則
```

## Artifact 與驗收

| Artifact   | 來源                  | 驗收                         |
| ---------- | --------------------- | ---------------------------- |
| 規則測試檔 | `rules.test.js`       | 四類斷言 + 正向 update       |
| 測試結果   | `emulators:exec` 輸出 | 正確規則下全 pass            |
| 回歸證明   | 改壞後重跑            | 3 個 assertFails 測試轉 fail |

## 接進 release gate

規則測試的下游責任是成為發布證據。把 `firebase emulators:exec ... jest` 接進 CI pipeline，規則變更的 PR 必須通過才能 merge——這把「規則改動沒開新洞」從人工推敲變成 gate 條件，對齊 [6.8 release gate](/backend/06-reliability/release-gate/) 的 `Gate decision / Checks / Stop condition`。授權翻譯的正確性是安全邊界，這個 gate 比一般功能測試更該設為硬性 stop condition。

## Cleanup

```bash
# emulators:exec 跑完會自動關 emulator；清依賴與工作區
rm -rf /tmp/firestore-lab
```

## 引用路徑

- 上游：[Firestore Hands-on 操作路線](/backend/01-database/vendors/firestore/hands-on/)
- Deep article：[Security Rules 授權建模與可測試化](/backend/01-database/vendors/firestore/security-rules-authz-modeling/)
- 安全驗證：[1.5 資料層紅隊](/backend/01-database/red-team-data-layer/)
- 發布證據：[6.8 release gate](/backend/06-reliability/release-gate/)
- 官方：[Rules unit testing](https://firebase.google.com/docs/rules/unit-tests)、[emulators:exec](https://firebase.google.com/docs/emulator-suite/install_and_configure)
