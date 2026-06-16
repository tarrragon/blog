---
title: "Firestore 高頻寫入與 distributed counter：單 document contention 邊界與分片計數"
date: 2026-06-16
description: "Firestore 單一 document 有持續寫入的軟上限、高頻計數寫爆 contention 是常見事故；本文展開寫入 contention 的成因、distributed counter 分片計數的實作與讀取彙總、shard 數量與讀寫成本的取捨、五個高頻寫入踩坑，以及計數需求超過分片能處理時改走外部聚合的邊界"
weight: 13
tags: ["backend", "database", "firestore", "distributed-counter", "high-frequency-write"]
---

> 本文是 [Firestore](/backend/01-database/vendors/firestore/) overview 的 deep article。寫作參照 [Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)。寫入限制以 [官方 best practices](https://firebase.google.com/docs/firestore/best-practices) 為準、最後檢查日 2026-06-16。

## 問題情境：一個讚數欄位拖垮整條寫入

直播平台上線一個「即時按讚數」功能：每個貼文一個 document，按讚就 `update` 它的 `likes` 欄位 `+1`。內測沒問題，上了熱門直播——同一個貼文每秒湧入上千次按讚，寫入開始大量失敗、retry，延遲飆高，連帶其他寫入路徑被拖累。

根因是流量全壓在**單一 document** 上，而非流量總量超過 Firestore。Firestore 對單一 document 的持續寫入有軟上限（官方長期建議維持在每秒個位數量級、以當前文件為準），因為每次寫入要更新該 document 的所有索引、且並行寫同一 document 會觸發 contention 重試。把高頻變動的值塞進一個 document，等於替自己造一個寫入熱點。這篇處理 contention 的成因、用 distributed counter 把熱點打散的實作，以及這個手段的能力邊界。

## 核心概念：寫入 contention 從哪來

Firestore 的寫入成本不只是「寫一個值」。理解 contention 要抓三點：

**每次寫入維護該 document 的所有索引**。document 上有幾個被索引的欄位，一次寫入就要更新幾份索引條目。索引越多、單次寫入越重，這是寫入吞吐與索引數量綁定的根因。

**並行寫同一 document 會序列化**。Firestore 保證單一 document 的寫入一致性，並行的 `+1` 不能各寫各的——它們競爭同一份狀態，後到的要重試。`transaction` 與 `FieldValue.increment()` 都受這個限制：`increment` 省掉「讀-改-寫」的來回，但多個 increment 打同一 document 仍在同一個寫入熱點上排隊。

**熱點是 per-document，不是 per-collection**。把 1000 個貼文的讚數分在 1000 個 document，每個 document 每秒個位數寫入，完全沒問題；問題只在「單一 document 每秒上千寫入」。所以解法的方向是**把一個邏輯計數拆成多個物理 document**。

## 配置：distributed counter 分片計數

distributed counter 的核心是把「一個計數」拆成 N 個 shard document，寫入時隨機挑一個 shard `+1`，讀取時把所有 shard 加總。寫入壓力被分散到 N 個 document，每個 shard 的寫入頻率降為原本的 1/N。

資料結構：在計數目標下建一個 `shards` subcollection，N 個 shard document，每個存一段 partial count。

```javascript
// counter.js（用 Firebase Web SDK v9 modular API）
import {
  doc, collection, runTransaction, getDocs,
  writeBatch, increment,
} from 'firebase/firestore';

const NUM_SHARDS = 10;

// 初始化：建立 N 個 shard、每個 count = 0
export async function createCounter(db, counterRef) {
  const batch = writeBatch(db);
  for (let i = 0; i < NUM_SHARDS; i++) {
    batch.set(doc(counterRef, 'shards', String(i)), { count: 0 });
  }
  await batch.commit();
}

// 寫入：隨機挑一個 shard +1（用 increment 省掉 read-modify-write）
export async function incrementCounter(db, counterRef) {
  const shardId = Math.floor(Math.random() * NUM_SHARDS);
  const shardRef = doc(counterRef, 'shards', String(shardId));
  await setDoc(shardRef, { count: increment(1) }, { merge: true });
}

// 讀取：加總所有 shard
export async function getCount(db, counterRef) {
  const snap = await getDocs(collection(counterRef, 'shards'));
  let total = 0;
  snap.forEach((s) => { total += s.data().count; });
  return total;
}
```

三個設計點要展開。第一，寫入用 `increment(1)` 而非 transaction 的讀-改-寫：`increment` 是 atomic 的 server-side 操作，省掉一次讀取，且本身就避開了「讀到舊值再寫」的 race。第二，shard 選擇用隨機分佈，讓寫入均勻打散到 N 個 shard——這是分片有效的前提，若選 shard 有偏（例如按 user id hash 但 user 分佈不均），熱點會在某幾個 shard 復現。第三，讀取要讀 N 個 document 加總，這是分片的代價：寫入便宜了，讀取從「讀 1 筆」變成「讀 N 筆」，計費與延遲都乘以 N。

如果即時讀取頻率也很高（每個觀眾畫面都要顯示即時讚數），讀 N 個 shard 的成本會反過來變成瓶頸。這時把彙總值定期寫回一個 summary document，client 訂閱 summary 而非每次加總：

```javascript
// 由 Cloud Function 定時（或 onWrite 觸發 + debounce）彙總寫回 summary
export async function aggregateToSummary(db, counterRef) {
  const total = await getCount(db, counterRef);
  await setDoc(doc(counterRef, 'summary', 'current'), {
    count: total,
    updatedAt: serverTimestamp(),
  });
}
```

這把「即時精確」換成「近即時」：summary 有刷新間隔的延遲，但讀取從 N 筆降回 1 筆。讚數、觀看數這類「差幾個不影響體驗」的計數，這個取捨幾乎總是對的。

## 故障演練：五個高頻寫入踩坑

#### Case 1：直接 `increment` 單一 document 沒分片

最常見的起手——以為 `FieldValue.increment()` 就解決了並行，忽略它仍在單一 document 的寫入熱點上。低流量沒事、熱門事件寫爆。修法：判斷該計數的峰值寫入頻率，超過單 document 軟上限就上 distributed counter；不確定峰值就先分片，分片對低流量無害（只是多讀幾筆）。

#### Case 2：shard 數量拍腦袋定太小

設了 3 個 shard，峰值流量下每個 shard 仍每秒上百寫入、照樣 contention。修法：shard 數要對齊峰值寫入頻率除以單 shard 安全寫入率（每秒個位數）。預期峰值每秒 500 寫入、單 shard 安全 5/s，就需要約 100 個 shard。寧可估高。

#### Case 3：shard 太多拖垮讀取

反向錯誤——為了保險設 1000 個 shard，結果每次讀計數要讀 1000 個 document，讀取計費與延遲爆炸。修法：shard 數是寫入分散與讀取成本的取捨；高寫入低讀取用多 shard + 直接加總，高寫入高讀取用多 shard + summary 彙總，別用「讀 N 筆加總」硬扛高頻讀取。

#### Case 4：選 shard 有偏導致熱點復現

用 `userId` 的 hash 選 shard、但活躍 user 集中在少數，寫入仍打在某幾個 shard 上。修法：shard 選擇要與寫入來源無關的隨機分佈，不要綁任何可能傾斜的 key。

#### Case 5：把分片計數當強一致餘額用

把 distributed counter 拿來記帳戶餘額、庫存這類需要強一致與精確讀的值。分片計數的讀取是「加總當下各 shard」，並行寫入下讀到的是近似值，不適合做扣款判斷。修法：強一致的計數（餘額、庫存、配額）不該用分片計數，也通常不該用 Firestore 的單欄位累加——這類值要走 transaction 嚴格控制、或放關聯式資料庫用 row lock，見邊界段。

## 容量與觀測：shard 數的估算與監控

shard 數量的估算從峰值寫入頻率反推：`shard 數 ≈ 峰值每秒寫入 / 單 shard 安全寫入率`。單 shard 安全寫入率以官方當前的單 document 持續寫入建議為基準（個位數量級），估算時取保守值。讀取成本同步要算：每次讀計數 = N 次 document read，乘上讀取頻率與日活，這是 distributed counter 的隱性帳。

監控的訊號是寫入失敗率與 contention 重試。寫入大量失敗 + retry 是 contention 的直接徵兆；單一 shard 的寫入頻率若明顯高於其他 shard，是 shard 選擇有偏的徵兆。這些訊號接回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)，把高頻寫入的健康度當成可觀測指標而非事故才發現。

容量規劃還要考慮 shard 數的可調整性：shard 數寫死在 client 程式裡，事後要加 shard 得同時改寫入與讀取邏輯、並補建新 shard document。預期會成長的計數，起步就把 shard 數設在峰值對應的量級，比事後擴容省事。

## 邊界與整合：什麼計數不該用分片，什麼該離開 Firestore

distributed counter 解的是「高頻、可接受近似、不需強一致」的計數——讚數、觀看數、瀏覽量、即時參與人數。它的邊界很清楚：

- **需要強一致與精確的計數**：帳戶餘額、庫存、配額扣減。這些要嘛用 Firestore transaction 嚴格序列化（但就回到單 document 寫入上限的限制、不適合高頻），要嘛放關聯式資料庫用 row-level lock 與交易保護（見 [1.3 transaction 與一致性邊界](/backend/01-database/transaction-boundary/)）
- **需要任意維度聚合的計數**：要算「各地區、各時段的累計」這類多維彙總，分片計數表達不了，該把事件流寫進分析系統或關聯式資料庫做 aggregation
- **計數本身是核心交易資料**：當計數驅動扣款、結算這類有金錢後果的流程，把它留在 client 直連的 Firestore 是控制面風險，該移到後端——這呼應 [Firestore → 自建 relational](/backend/01-database/vendors/firestore/migrate-to-relational/) 的成本與授權 driver

判讀順序是先問「這個計數能不能容忍近似與最終一致」。能，distributed counter 是 Firestore 內的正解；不能，這個計數從一開始就不該用 Firestore 的單欄位累加表達。

## 下一步路由

- 上層：[Firestore overview](/backend/01-database/vendors/firestore/)（容量特性與寫入熱點）
- 一致性邊界：[1.3 transaction 與一致性邊界](/backend/01-database/transaction-boundary/)（強一致計數的去處）
- 容量背景：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- 觀測：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)（寫入失敗率與 contention 監控）
- 官方：[Firestore best practices](https://firebase.google.com/docs/firestore/best-practices)、[Distributed counters solution](https://firebase.google.com/docs/firestore/solutions/counters)
