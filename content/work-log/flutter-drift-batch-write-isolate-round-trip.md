---
title: "匯入大量書籍時的寫入耗時排查：手機上 SQLite 在背景 isolate 的逐條往返、一次送出的語句記錄器，以及依提交時間調整批次大小"
slug: "flutter-drift-batch-write-isolate-round-trip"
date: 2026-11-28
draft: false
description: "Flutter APP 的批次寫入在測試裡很快、在手機上慢幾十倍到上百倍，或分批處理的長工作越到後面進度更新越慢時讀；資料庫用 drift 或 sqflite 跑在背景 isolate 的情形"
tags: ["flutter", "dart", "sqlite", "drift", "performance", "isolate", "batch"]
---

事件發生在 2026 年 11 月 28 日。環境是一個 Flutter 3.41 的書庫 APP，資料庫用 drift 2.35 與 APP 自帶的 SQLite，正式執行時以 `NativeDatabase.createInBackground` 跑在背景 isolate；單元測試與流程測試用 `NativeDatabase.memory()`。操作是在 Android 實機（Samsung SM-S9010，Android 16）上以 profile 版往空書庫匯入一份 5 萬本的匯出檔，做匯入功能的實機驗收。

這篇整理三件事：手機上逐條 `await` 的 SQL 為什麼比測試慢上百倍，以及怎麼從每本書的 SQL 條數推到成本在跨 isolate 的往返；把同一套寫入邏輯對著一個語句記錄器跑、再用 drift 的 batch 一次送出的做法，包括拿不到逐條結果與變更通知要合併這兩處調整；以及書庫越大、一批提交越久時，依提交時間調整批次大小，讓進度至少每秒更新一次。讀的是 N+1 查詢這類讀取端的同類情形時，[1000 本書、1001 次 SQL — N+1 查詢藏在 async mapper 裡](/work-log/flutter_sqlite_n_plus_one_query/) 處理的是讀取時對每本書各查一次。

## 情境條件

這一類耗時出現在三個條件同時成立時：資料庫的執行器跟呼叫端不在同一個 isolate（drift 的 `createInBackground`、sqflite 在 Android 上經由平台通道），寫入程式對每一條 SQL 各 `await` 一次，以及一次要寫入的筆數多到上千。三個條件缺任何一個，耗時都看不出異常：執行器在同一個 isolate 時每條的額外成本接近零，一次寫一兩筆時多出來的往返只有幾毫秒。

這個 APP 的匯入在 Mac 的流程測試裡，1,000 本新書約 1 秒完成，測試通過。實機上開始匯入之後，到第 10,500 本花了約 9.5 分鐘，一批 500 本約 28 秒。

## 每本書寫幾條 SQL

匯入寫入一本書時，repository 在一個 transaction 裡做這些事：

- 寫入書本身的一列（`INSERT OR REPLACE INTO books ...`），一條。
- 清掉這本書舊的標籤關聯（`DELETE FROM book_tags WHERE book_id = ?`），一條。
- 每個標籤（作者、ISBN、閱讀狀態、來源、重要程度、自訂標籤）各寫兩條：`INSERT OR IGNORE INTO tags` 與 `INSERT OR IGNORE INTO book_tags`。

一本書約 5 到 6 個標籤，合計約 12 到 14 條，一批 500 本約 6,000 到 7,000 條。repository 的寫入方法對著執行器介面逐條 `await txn.insert(...)`。

## 測試與手機的單位成本不同

一段寫入的耗時等於 SQL 的條數乘上每一條的單位成本。條數在測試與手機上相同，差在單位成本：

- `NativeDatabase.memory()` 讓 SQLite 跟呼叫端在同一個 isolate，`await` 一條 SQL 的成本幾乎只有 SQLite 本身的執行時間。
- `NativeDatabase.createInBackground` 讓 SQLite 跑在另一個 isolate。主 isolate 每送出一條，都要把語句與參數傳過去、等對方執行完、再把結果傳回來；這一次往返是每條 SQL 額外的成本。

要確認成本落在往返而不是 SQLite 本身，在 Mac 上用跟手機一樣的執行器量同一段寫入：用 `NativeDatabase.createInBackground(File(<暫存檔>))` 開一個檔案資料庫，量 `writeBooks` 寫入一批 500 本。結果是 270 到 350 ms；同一批在記憶體資料庫裡快得多。換了執行器之後，Mac 上的耗時也上升了一個數量級，代表成本來自執行器的結構，手機只是在每次往返上更慢。

原本的 repository 其實有一個「批次」物件：它把 insert、update、delete 收進一個清單，提交時在 transaction 裡逐條 `await`。介面看起來是批次，往返的次數跟逐條寫一樣，所以它解決不了這一類耗時。

## 一次送出：語句記錄器

drift 的 `batch` 把一組語句一次送到背景 isolate，在那裡依序執行；在 transaction 裡呼叫時，它沿用那個 transaction。要用它，寫入的 SQL 得先組成一份清單。

寫入一本書的邏輯分散在好幾個方法（寫書、清標籤、寫標籤與關聯），每個方法都對著執行器介面 `SqlExecutor` 寫。另寫一份「批次版」的寫入邏輯，兩份之後要保持一致；所以做法是加一個實作同一個介面的語句記錄器，讓原本的方法對著它跑一遍：

```dart
/// 只記下寫入、不執行；之後一次送出
class SqlStatementRecorder implements SqlExecutor {
  final statements = <RecordedStatement>[];

  @override
  Future<int> insert(String table, Map<String, Object?> values,
      {SqlConflict? conflictAlgorithm}) async {
    statements.add(RecordedStatement(
        _insertSql(table, values, conflictAlgorithm), values.values.toList(),
        table: table, kind: UpdateKind.insert));
    return 0; // 記錄當下沒有 rowid
  }
  // update、delete、execute 同樣只記錄；rawQuery、query 丟出例外
}
```

`_insertSql` 是正式執行器組 SQL 時用的同一個函式，所以記錄下來的語句跟逐條執行時送出的一字不差。送出的那一側：

```dart
Future<void> runRecorded(SqlStatementRecorder recorder) async {
  await _db.batch((b) {
    for (final s in recorder.statements) {
      b.customStatement(s.sql, s.args);
    }
  });
  // 寫到的表合成一次通知
  final updates = {
    for (final s in recorder.statements)
      if (s.table != null) TableUpdate(s.table!, kind: s.kind),
  };
  if (updates.isNotEmpty) _db.notifyUpdates(updates);
}
```

repository 的批次寫入改成：在 transaction 裡建一個記錄器，原本的寫書與寫標籤方法對著記錄器跑，最後 `runRecorded`。同樣的做法用在補算衍生欄位（每本書一條 `UPDATE books SET ...`）上。

這個做法有兩處要跟著調整：

- **拿不到逐條的結果**：原本更新一本書時，`update` 回傳影響的列數，0 代表書不存在、丟出例外，整批回滾。記錄器的 `update` 只能回傳一個假設的值，所以改成送出之前先用一條查詢（`SELECT id FROM books WHERE id IN (...)`）確認每本要更新的書都在，有一本不在就丟出例外，什麼都不送。
- **變更通知要合併**：一次送出寫到 `books`、`tags`、`book_tags` 三張表，逐表各通知一次的話，監聽這幾張表的查詢（首頁的本數、書單）會被觸發三次。既有的測試「一批寫入只讓 watch 重查一次」在逐表通知時失敗，合成一次 `notifyUpdates` 之後通過。

改完之後，Mac 上同樣用背景 isolate 量：一批 500 本從 270 到 350 ms 降到 50 到 72 ms，補算衍生欄位從 40 到 60 ms 降到 21 到 39 ms。實機上，從開始匯入到第 10,500 本從約 9.5 分鐘降到約 4.4 秒；5 萬本全部匯入（含中途 3 秒的暫停）約 31 秒。

## 書庫越大，一批提交越久

匯入的驗收要求進度每秒至少更新一次。匯入每一批先在記憶體裡規劃（解析、比對重複），再在一個 transaction 裡提交，提交後回報進度；規劃期間另外每隔一段時間回報一次。

一批固定 500 本、規劃期間每 1 秒回報時，量到兩次進度更新的最大間隔 1014 ms。把規劃期間的回報間隔改成 0.8 秒之後，最大間隔是 1205 ms，沒有變短。讓量測回報最大的三個間隔各自在哪兩次更新之間，三個都在匯入到 4 萬多本時的相鄰兩批之間（42000→42500、42500→43000），一批的提交要 0.7 到 1.0 秒。

提交是不能從中間回報的單位，所以兩次更新的間隔至少是一批提交的時間；規劃期間回報得再密，也縮不短提交。而一批提交的時間隨書庫長大：每寫入一本要更新的全文索引、衍生欄位，以及畫面監聽的本數查詢，都隨書庫的大小變貴。500 本在書庫剛開始時提交得很快，到 4 萬本時接近 1 秒；換一支比較慢的手機，同一個時間點會更久。

修法是依量到的提交時間決定下一批的大小：

```dart
int _nextBatchSize(int current, Duration took) {
  final target = targetCommitTime.inMicroseconds; // 0.4 秒
  final spent = max(took.inMicroseconds, 1);
  if (spent > target) {
    return max(minBatchSize, (current * target / spent).floor()); // 照比例縮小，不低於 50
  }
  if (spent < target ~/ 2) return min(batchSize, current * 2); // 快很多就加倍，不超過 500
  return current;
}
```

提交時間大致跟批次大小成正比，超過 0.4 秒時照比例縮小，下一批就回到 0.4 秒附近；0.4 秒是 1 秒的回報門檻扣掉規劃與排程的餘裕。改完之後最大間隔 613 ms，最大的幾個間隔落在 28864→29322、29322→29628 這種縮小過的批次之間；全部時間 31 秒，跟固定 500 本時差不多，因為總工作量不變，只是切得比較細。

## 判斷標準

測試裡的寫入耗時能不能代表手機，看測試的資料庫執行器跟正式執行是不是同一種結構。測試用同一個 isolate 的記憶體資料庫、正式執行用背景 isolate 時，測試量到的是 SQLite 本身的時間，跨 isolate 的往返完全沒被量到；寫入的條數越多，兩邊差得越遠。這時要在實機上量，或在 Mac 上用跟手機相同的 `createInBackground` 開一個檔案資料庫量。

一段寫入是不是付了逐條往返的成本，看它在 transaction 裡是逐條 `await`，還是把語句收齊之後一次送出；介面叫做批次、內部逐條 `await` 的，屬於前一種。耗時跟寫入的條數成正比（而不是跟資料量成正比）時，成本在往返。

分批工作的進度間隔守不守得住，看最長的那一次提交有沒有落在回報間隔之內。最大間隔越到工作後段越長、而且落在相鄰兩批的提交之間時，批次大小要依提交時間調整；只縮短規劃期間的回報間隔，最大間隔不會變。
