---
title: "Firestore Distributed Counter Lab"
date: 2026-06-16
description: "在 emulator 上實作 distributed counter：建立 N 個 shard、隨機分片寫入、觀察 shard 分佈是否均勻、讀取彙總驗證總和正確，並說明 contention 本身是 emulator 不模擬的 production 特性"
tags: ["backend", "database", "firestore", "hands-on", "distributed-counter"]
---

> 本文是 [Firestore Hands-on 操作路線](/backend/01-database/vendors/firestore/hands-on/) 的 lab，實作 [distributed counter 高頻寫入](/backend/01-database/vendors/firestore/distributed-counter-high-frequency-write/) deep article 的機制。前置環境見 [Local emulator quickstart](/backend/01-database/vendors/firestore/hands-on/local-emulator-quickstart/)。

Firestore distributed counter lab 的核心責任是把「分片計數」從概念變成可觀察的寫入分佈與彙總結果。這個 lab 在 emulator 上建立 N 個 shard、隨機分片寫入大量 increment、檢查寫入是否均勻打散到各 shard、再讀取彙總驗證總和正確。

本文的驗收標準是：你能跑出一個 sharded counter、看到 N 個 shard 各自累積了大致均勻的 partial count、彙總後等於總寫入次數，並理解 emulator 能驗什麼、不能驗什麼。

## 先講清楚 emulator 的邊界

這個 lab 驗證的是**分片計數的機制正確性**：寫入是否均勻分佈、彙總是否等於總和、讀取要讀幾個 document。它不驗證的是 **contention 本身**——emulator 不強制 production 的單 document 持續寫入軟上限，所以「不分片會寫爆」這件事在 emulator 跑不出來。contention 是 production 的規模特性，要在雲端真實負載下才會出現。

這個分界本身是要學的判讀：emulator 證明「分片計數做對了」，雲端負載測試才證明「不分片會撞牆」。把兩者混為一談會誤以為 emulator 全綠就代表 production 安全。

## Lab 環境

沿用 [quickstart](/backend/01-database/vendors/firestore/hands-on/local-emulator-quickstart/) 的工作區與 emulator。確認 emulator 在跑（另一個 terminal）。

```bash
cd /tmp/firestore-lab
# 確認 emulator 已啟動：firebase emulators:start --only firestore --project demo-firestore-lab
export FIRESTORE_EMULATOR_HOST=localhost:8080
```

## 實作 sharded counter

counter 的核心責任是把一個邏輯計數拆成 N 個 shard document。寫入時隨機挑 shard `increment(1)`，讀取時加總所有 shard。這份 script 用 admin SDK 直接對 emulator 操作。

```bash
cat > counter.js <<'JS'
const admin = require('firebase-admin');
admin.initializeApp({ projectId: 'demo-firestore-lab' });
const db = admin.firestore();
const FieldValue = admin.firestore.FieldValue;

const NUM_SHARDS = 10;
const counterRef = db.collection('counters').doc('likes');

async function createCounter() {
  const batch = db.batch();
  for (let i = 0; i < NUM_SHARDS; i++) {
    batch.set(counterRef.collection('shards').doc(String(i)), { count: 0 });
  }
  await batch.commit();
}

async function incrementOnce() {
  const shardId = Math.floor(Math.random() * NUM_SHARDS);
  await counterRef.collection('shards').doc(String(shardId))
    .set({ count: FieldValue.increment(1) }, { merge: true });
}

async function getCount() {
  const snap = await counterRef.collection('shards').get();
  let total = 0;
  const perShard = {};
  snap.forEach((s) => { perShard[s.id] = s.data().count; total += s.data().count; });
  return { total, perShard };
}

module.exports = { createCounter, incrementOnce, getCount, NUM_SHARDS };
JS
```

三個設計點對應 deep article：用 `FieldValue.increment(1)` 而非讀-改-寫（避開 race）；隨機選 shard 讓寫入均勻打散；讀取要讀 N 個 shard 加總（這是分片的代價）。

## 跑寫入並觀察分佈

driver 的核心責任是製造大量 increment、然後檢查寫入是否均勻落在各 shard。均勻分佈是分片有效的前提——若 shard 選擇有偏，熱點會在某幾個 shard 復現。

```bash
cat > run.js <<'JS'
const { createCounter, incrementOnce, getCount, NUM_SHARDS } = require('./counter');

const TOTAL_WRITES = 1000;

async function main() {
  await createCounter();
  console.log(`created ${NUM_SHARDS} shards`);

  // 製造 1000 次 increment
  const tasks = [];
  for (let i = 0; i < TOTAL_WRITES; i++) tasks.push(incrementOnce());
  await Promise.all(tasks);

  const { total, perShard } = await getCount();
  console.log('per-shard counts:', perShard);
  console.log(`total = ${total} (expected ${TOTAL_WRITES})`);

  // 均勻度檢查：每個 shard 期望 ~100，看極差
  const counts = Object.values(perShard);
  const min = Math.min(...counts), max = Math.max(...counts);
  console.log(`min=${min} max=${max} spread=${max - min} (expected mean ~${TOTAL_WRITES / NUM_SHARDS})`);
}
main().then(() => process.exit(0));
JS

export FIRESTORE_EMULATOR_HOST=localhost:8080
node run.js
```

預期輸出類似（實際數字每次隨機分佈而異）：

```text
created 10 shards
per-shard counts: { '0': 98, '1': 105, '2': 92, ... }
total = 1000 (expected 1000)
min=88 max=112 spread=24 (expected mean ~100)
```

兩個驗收點：`total` 等於總寫入次數（彙總正確、沒有 increment 遺失），以及各 shard 的 count 大致落在均值附近（隨機分佈均勻、沒有單一 shard 吸走大部分寫入）。

## 對照實驗：讀取成本隨 shard 數成長

讀取的核心代價是讀 N 個 document。把 `NUM_SHARDS` 改大（例如 100）重跑，`getCount` 要讀的 document 從 10 變 100——這就是 deep article 講的「寫入便宜了、讀取乘以 N」的取捨。在 production 這直接反映成 read 計費。

```bash
# 編輯 counter.js 把 NUM_SHARDS 改為 100、重跑 run.js
# 觀察 per-shard counts 物件變成 100 個 key、getCount 讀取量 10x
```

這個對照讓「shard 數是寫入分散與讀取成本的取捨」從文字變成可觀察：多 shard 寫入更分散（每 shard 更少），但讀取要加總更多筆。高寫入高讀取的場景該配 summary 彙總（deep article 的進階手段），而非無限加 shard。

## Artifact 與驗收

| Artifact     | 來源            | 驗收                            |
| ------------ | --------------- | ------------------------------- |
| counter 實作 | `counter.js`    | `increment` 分片寫入 + 彙總讀取 |
| 寫入分佈     | `run.js` output | total = 寫入次數、各 shard 均勻 |
| 讀寫取捨     | NUM_SHARDS 對照 | shard 數↑ → 讀取 document 數↑   |

## 回到 production 判讀

emulator lab 證明了機制正確，但三個 production 判讀要回雲端確認：單 document 寫入軟上限（決定 shard 數要多少）、read 計費（決定 shard 數別太多 / 要不要 summary）、shard 選擇在真實流量下是否仍均勻。把 emulator 的機制驗證當第一道關，production 的容量與成本判讀見 [deep article 的容量段](/backend/01-database/vendors/firestore/distributed-counter-high-frequency-write/#容量與觀測shard-數的估算與監控)。

## Cleanup

```bash
# 停 emulator（Ctrl-C）或清整個工作區
rm -rf /tmp/firestore-lab
```

## 引用路徑

- 上游：[Firestore Hands-on 操作路線](/backend/01-database/vendors/firestore/hands-on/)
- Deep article：[高頻寫入與 distributed counter](/backend/01-database/vendors/firestore/distributed-counter-high-frequency-write/)
- 一致性邊界：[1.3 transaction 與一致性邊界](/backend/01-database/transaction-boundary/)
- 官方：[Distributed counters](https://firebase.google.com/docs/firestore/solutions/counters)、[Firestore best practices](https://firebase.google.com/docs/firestore/best-practices)
