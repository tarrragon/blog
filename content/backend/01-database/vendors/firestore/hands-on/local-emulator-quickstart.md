---
title: "Firestore Local Emulator Quickstart"
date: 2026-06-16
description: "用 Firebase CLI 啟動 Firestore emulator、寫 firestore.rules、用 admin SDK seed 資料、跑 query baseline 與 cleanup，建立後續 Security Rules 與 distributed counter lab 共用的本地環境"
tags: ["backend", "database", "firestore", "hands-on", "emulator"]
---

> 本文是 [Firestore Hands-on 操作路線](/backend/01-database/vendors/firestore/hands-on/) 的基礎 lab。指令以 [Firebase CLI 文件](https://firebase.google.com/docs/cli) 與 [Emulator Suite 文件](https://firebase.google.com/docs/emulator-suite) 為準、最後檢查日 2026-06-16。

Firestore local emulator quickstart 的核心責任是建立後續 Security Rules 測試與 distributed counter lab 共用的本地環境。這個 lab 把 Firestore 從抽象服務轉成可觀察的 emulator、規則檔、seed 資料與 query 結果，全程不碰雲端專案。

本文的驗收標準是：你能在本地啟動 Firestore emulator、用 admin SDK 寫入並查詢一組 seed 資料、看到 emulator UI 裡的資料，並知道 cleanup 路徑。

## Lab 環境與前置

Lab 在本地資料夾跑，需要 Node.js 與 Firebase CLI。以下命令建立一個可刪除的工作區並裝好工具。

```bash
mkdir -p /tmp/firestore-lab
cd /tmp/firestore-lab

# Firebase CLI（已裝可跳過）；用 npx 也可避免全域安裝
npm install -g firebase-tools

# 本 lab 的 Node 依賴
npm init -y
npm install firebase-admin
```

emulator 需要 Java runtime（Firestore emulator 跑在 JVM 上）。`java -version` 確認存在；缺的話先裝 JDK 再繼續。驗收 artifact 是 `/tmp/firestore-lab` 工作區。

## Emulator 設定

`firebase.json` 的核心責任是宣告要啟動哪些 emulator 與對應 port。這裡只開 Firestore 與 UI，不需要真實 Firebase 專案——emulator 用一個 demo project id 即可，`demo-` 前綴讓 CLI 知道這是純本地、不連雲端。

```bash
cat > firebase.json <<'JSON'
{
  "emulators": {
    "firestore": { "port": 8080 },
    "ui": { "enabled": true, "port": 4000 }
  },
  "firestore": {
    "rules": "firestore.rules"
  }
}
JSON
```

## Baseline 規則

`firestore.rules` 的核心責任是定義授權。Quickstart 先用一組明確的 owner-scoped 規則（不是 `allow read, write: if true`，那是 [deep article Case 1](/backend/01-database/vendors/firestore/security-rules-authz-modeling/) 的漏洞）。這份規則後續在 [Security Rules test lab](/backend/01-database/vendors/firestore/hands-on/security-rules-test-lab/) 會被測試覆蓋。

```bash
cat > firestore.rules <<'RULES'
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
RULES
```

## 啟動 emulator

啟動 emulator 的核心責任是讓本地有一個可寫可查的 Firestore。用 demo project id 啟動，emulator UI 在 `http://localhost:4000` 可看到資料。

```bash
firebase emulators:start --only firestore --project demo-firestore-lab
```

這個指令會 foreground 跑住 emulator。保持它開著，另開一個 terminal 做 seed 與 query。終端輸出會印出 Firestore emulator 的位址（預設 `localhost:8080`）與 UI 位址。

## Seed 資料（admin SDK 繞過規則）

Seed 的核心責任是建立可重跑的測試資料。admin SDK 連到 emulator 時繞過 Security Rules（模擬後端的特權寫入），適合種資料。關鍵是設 `FIRESTORE_EMULATOR_HOST` 環境變數——有了它，admin SDK 的寫入全部導向 emulator、不需要任何雲端 credential。

```bash
cat > seed.js <<'JS'
const admin = require('firebase-admin');
admin.initializeApp({ projectId: 'demo-firestore-lab' });
const db = admin.firestore();

async function main() {
  await db.collection('notes').doc('n1').set({
    ownerId: 'alice', text: 'Alice first note', createdAt: Date.now(),
  });
  await db.collection('notes').doc('n2').set({
    ownerId: 'bob', text: 'Bob first note', createdAt: Date.now(),
  });
  console.log('seeded 2 notes');
}
main().then(() => process.exit(0));
JS

# 在新 terminal、同 lab 目錄下
export FIRESTORE_EMULATOR_HOST=localhost:8080
node seed.js
```

預期輸出 `seeded 2 notes`。打開 `http://localhost:4000/firestore` 應看到 `notes` collection 下兩筆 document。

## Query baseline

Query 的核心責任是確認資料可讀、access pattern 入口可用。admin SDK 同樣繞過規則，這裡驗證的是資料與查詢本身（規則的放行 / 拒絕在下一個 lab 用 client context 驗）。

```bash
cat > query.js <<'JS'
const admin = require('firebase-admin');
admin.initializeApp({ projectId: 'demo-firestore-lab' });
const db = admin.firestore();

async function main() {
  const snap = await db.collection('notes')
    .where('ownerId', '==', 'alice').get();
  console.log(`alice notes: ${snap.size}`);
  snap.forEach((d) => console.log(d.id, d.data().text));
}
main().then(() => process.exit(0));
JS

export FIRESTORE_EMULATOR_HOST=localhost:8080
node query.js
```

預期輸出 `alice notes: 1` 與 `n1 Alice first note`。這證明 `where('ownerId', '==', ...)` 的 access pattern 成立——它也正是 client 端要自帶、好讓 owner-scoped 規則放行的查詢條件。

## Artifact 與驗收

| Artifact        | 路徑 / 來源           | 驗收                        |
| --------------- | --------------------- | --------------------------- |
| emulator config | `firebase.json`       | Firestore + UI port 宣告    |
| 規則檔          | `firestore.rules`     | owner-scoped、非 `if true`  |
| seed 結果       | `seed.js` output + UI | `notes/n1`、`notes/n2` 存在 |
| query 結果      | `query.js` output     | `alice notes: 1`            |

## Cleanup

Cleanup 的核心責任是讓 lab 可重跑。emulator 的資料在 process 結束時預設不持久化（除非設了 `--export-on-exit`），所以停掉 emulator 等於清空資料。

```bash
# 停掉 emulator：在 emulator terminal 按 Ctrl-C
# 移除整個工作區
rm -rf /tmp/firestore-lab
```

若想保留 emulator 資料跨 session，啟動時加 `--import=./data --export-on-exit=./data`；lab 預設不持久化，保持每次乾淨起步。

完成本篇後，下一步進 [Security Rules test lab](/backend/01-database/vendors/firestore/hands-on/security-rules-test-lab/)（把上面的規則寫成自動化測試）或 [Distributed counter lab](/backend/01-database/vendors/firestore/hands-on/distributed-counter-lab/)。

## 引用路徑

- 上游：[Firestore Hands-on 操作路線](/backend/01-database/vendors/firestore/hands-on/)
- Deep article：[Security Rules 授權建模](/backend/01-database/vendors/firestore/security-rules-authz-modeling/)
- 官方：[Install Firebase CLI](https://firebase.google.com/docs/cli)、[Connect to Firestore emulator](https://firebase.google.com/docs/emulator-suite/connect_firestore)
