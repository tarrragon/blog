---
title: "Flutter drift 匯入大量書籍時的寫入耗時排查：手機上 SQLite 在背景 isolate 的逐條往返、一次送出的語句記錄器，以及依提交時間調整批次大小"
slug: "flutter-drift-batch-write-isolate-round-trip"
date: 2026-11-28
draft: false
description: "Flutter APP 的批次寫入在測試裡很快、在手機上慢幾十倍到上百倍，或分批處理的長工作越到後面進度更新越慢時讀；資料庫用 drift 跑在背景 isolate，或 sqflite 經平台通道的情形"
tags: ["flutter", "dart", "sqlite", "drift", "performance", "isolate", "batch"]
---

事件發生在 2026 年 11 月 28 日。環境是一個 Flutter 3.41 的書庫 APP，資料庫用 drift 2.35 與 APP 自帶的 SQLite，正式執行時以 `NativeDatabase.createInBackground` 跑在背景 isolate；單元測試與驅動整段匯入流程的測試用 `NativeDatabase.memory()`。操作是在 Android 實機（Samsung SM-S9010，Android 16）上以 profile 版往空書庫匯入一份 5 萬本的匯出檔，做匯入功能的實機驗收。

這篇整理手機上逐條 `await` 的 SQL 為什麼比測試慢上百倍，以及怎麼從每本書的 SQL 條數推到成本在跨 isolate 的訊息往返（round trip）；把同一套寫入邏輯對著一個語句記錄器跑、再用 drift 的 batch 一次送出的做法，包括拿不到逐條結果與變更通知要合併這兩處調整；以及書庫越大、一批提交越久時，依提交時間調整批次大小，讓進度至少每秒更新一次。讀取端的同類成本（讀取時對每本書各查一次關聯的 N+1 查詢）在 [1000 本書、1001 次 SQL — N+1 查詢藏在 async mapper 裡](/work-log/flutter_sqlite_n_plus_one_query/)。

## 跨 isolate 逐條寫入變慢的條件

isolate 是 Dart 的執行單位，各自有獨立的記憶體、彼此只能傳訊息，所以不同 isolate 之間的每一次呼叫，都要把資料打包傳過去、再等結果傳回來。這一類耗時出現在幾個條件同時成立時：資料庫的執行器跟呼叫端不在同一個 isolate（drift 的 `createInBackground`；sqflite 在 Android 上經由平台通道（platform channel）把呼叫交給原生端），寫入程式對每一條 SQL 各 `await` 一次，以及一次要寫入的筆數多到上千。任何一個條件不成立，量耗時的人都看不出異常：執行器在同一個 isolate 時，每條 SQL 沒有額外的往返；一次只寫一兩本時，多出來的往返是一本約 50 到 60 ms（這支手機上每條約 4 到 5 ms，換算方式在〈測試與手機上每條 SQL 的單位成本〉），遠低於匯入驗收的 1 秒門檻。

這個 APP 換成 drift 之前，Mac 上的測試用 `sqflite_common_ffi` 的記憶體資料庫（只用在 Mac 的測試），匯入 1,000 本新書約 1 秒，效能測試通過；換成 drift、加上背景的匯入工作之後，測試仍然用同一個 isolate 的記憶體資料庫。兩種測試設定都量不到跨 isolate 或平台通道的往返。這次的紀錄裡沒有換套件之前在手機上大量匯入的量測，所以這些證據比不出 sqflite 與 drift 在手機上誰快。以 drift 在實機上開始匯入之後，到第 1 萬本花了約 9.5 分鐘，一批 500 本約 28 秒。

## 每本書寫入的 SQL 條數

匯入寫入一本書時，repository 在一個 transaction 裡做這些事：

- 寫入書本身的一列（`INSERT OR REPLACE INTO books ...`），一條。
- 清掉這本書舊的標籤關聯（`DELETE FROM book_tags WHERE book_id = ?`），一條。
- 每個標籤（作者、ISBN、閱讀狀態、來源這類）各寫兩條：`INSERT OR IGNORE INTO tags` 與 `INSERT OR IGNORE INTO book_tags`。

這份匯出檔的書約有 5 個標籤，合計約 12 條，一批 500 本約 6,000 條。repository 的寫入方法對著執行器介面逐條 `await txn.insert(...)`。

## 測試與手機上每條 SQL 的單位成本

一段寫入的耗時等於 SQL 的條數乘上每一條的單位成本。條數在測試與手機上相同，差在單位成本：

- `NativeDatabase.memory()` 讓 SQLite 跟呼叫端在同一個 isolate，`await` 一條 SQL 的成本幾乎只有 SQLite 本身的執行時間。
- `NativeDatabase.createInBackground` 讓 SQLite 跑在另一個 isolate。主 isolate 每送出一條，都要把語句與參數傳過去、等對方執行完、再把結果傳回來；這一次往返是每條 SQL 額外的成本。

手機上一批 500 本約 28 秒、約 6,000 條，每條約 4 到 5 ms（28 秒 ÷ 6,000 條約 4.7 ms；條數是估計值）。這是總時間的平均，不是單次往返本身的量測：匯入期間主 isolate 同時在規劃下一批、畫 frame，背景 isolate 的回覆要等它的事件迴圈空出來，監聽查詢也可能在資料庫 isolate 裡排隊，這些成分沒有拆開（推論）。在 Mac 上用跟手機一樣的執行器量同一段寫入：用 `NativeDatabase.createInBackground(File(<暫存檔>))` 開一個檔案資料庫，量 `writeBooks` 寫入一批 500 本，結果是 270 到 350 ms。Mac 與手機同樣是背景 isolate，每一次往返的成本仍差了將近百倍，所以 Mac 上的這個數字量不出手機上的量級。成本在逐條往返而不是 SQLite 本身，證據是〈一次送出：語句記錄器〉修法前後的對照：只把逐條送出改成一次送出、SQL 一條都沒少，Mac 上同一批從 270 到 350 ms 降到 50 到 72 ms。

資料庫轉接層（APP 自己的 `SqlDatabase`，repository 經由它呼叫資料庫）另外有一個模仿 sqflite `batch()` 的批次物件：它把 insert、update、delete 收進一個清單，提交時在 transaction 裡逐條 `await`，只有標籤的 repository 在用。書的批次寫入沒有用它，另外寫在 transaction 裡逐條 `await`。兩者介面不同，送出的往返次數都跟逐條寫相同，耗時不會因為叫做批次而下降。

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

`_insertSql` 是正式執行器組 SQL 時用的同一個函式，所以記錄下來的語句跟逐條執行時送出的一字不差。一次送出記錄下來的語句的函式是 `runRecorded`：

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

repository 的批次寫入改成：在 transaction 裡建一個記錄器，原本的寫書與寫標籤方法對著記錄器跑，最後 `runRecorded`。同樣的做法用在補算衍生欄位上：這個 APP 把搜尋、排序與去重要用的欄位（例如搜尋用的 `search_text`、排序用的 `sort_title`）由書的屬性算好存在 `books` 表裡，匯入之後每本書要用一條 `UPDATE books SET ...` 補上。

改用記錄器之後，逐條結果的檢查與變更通知要跟著調整：

- **拿不到逐條的結果**：原本更新一本書時，`update` 回傳影響的列數，0 代表書不存在、丟出例外，整批回滾。記錄器的 `update` 只能回傳一個假設的值，所以改成送出之前先用一條查詢（`SELECT id FROM books WHERE id IN (...)`）確認每本要更新的書都在，有一本不在就丟出例外，什麼都不送。
- **變更通知要合併**：一次送出寫到 `books`、`tags`、`book_tags` 三張表，逐表各通知一次的話，監聽這幾張表的查詢（首頁的本數、書單）會被觸發三次。既有的測試「一批寫入只讓 watch 重查一次」在逐表通知時失敗，合成一次 `notifyUpdates` 之後通過。

改完之後，Mac 上同樣用背景 isolate 量：一批 500 本從 270 到 350 ms 降到 50 到 72 ms，補算衍生欄位從 40 到 63 ms 降到 21 到 39 ms。實機上，從開始匯入到第 10,500 本約 4.4 秒（修改之前到第 1 萬本約 9.5 分鐘）。5 萬本全部匯入約 31 秒，其中含量測腳本刻意讓 APP 進背景的 3 秒（背景量測的寫法在 [Flutter 實機效能量測的排查：integration_test 的打字、無障礙樹、頁面監聽與背景等待，以及 flutter drive 解除安裝 APP 時的資料保全](/work-log/flutter-integration-test-profile-measurement-pitfalls/)）。

## 進度更新間隔與每批提交時間

匯入的驗收條件是進度每秒至少更新一次。匯入工作把每一批先在記憶體裡規劃（解析、比對重複），再在一個 transaction 裡提交，提交後回報進度；規劃期間另外每隔一段時間回報一次。

一批固定 500 本、規劃期間每 1 秒回報時，量到兩次進度更新的最大間隔 1008 ms。把規劃期間的回報改成每 0.8 秒一次之後量了兩次，最大間隔是 1205 ms 與 1014 ms，沒有變短。在 1014 ms 那一次，讓量測回報最大的三個間隔各自在哪兩次更新之間：1014 ms 在 42500→43000、871 ms 在 42000→42500、719 ms 在 41500→42000，三個都在匯入到 4 萬多本時的相鄰兩批之間，一批的提交要 0.7 到 1.0 秒。

一批的提交在一個 transaction 裡完成，進度只在提交前後回報，所以兩次更新的間隔至少是一批提交的時間；規劃期間回報得再密，也縮不短提交。一批提交的時間隨書庫長大：500 本在書庫剛開始時提交得很快，到 4 萬多本時接近 1 秒。成因推論是每寫入一本要更新的全文索引、衍生欄位，以及畫面監聽的本數查詢，都隨書庫的大小變貴；各項各佔多少沒有拆開量。其中畫面監聽的本數查詢是每批提交之後的附帶工作，匯入期間暫停或合併這類重查、匯入完成之後才建全文索引，都可能比縮小批次更便宜，這次沒有實測。推論換一支比較慢的手機，同樣的本數下提交會更久，這一點沒有量過。

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

提交時間大致跟批次大小成正比（這是演算法的假設，沒有另外量），超過 0.4 秒時照比例縮小，下一批就回到 0.4 秒附近；0.4 秒是 1 秒的更新門檻扣掉規劃與排程的餘裕。上限 500 是原本固定的批次大小，書庫剛開始、提交很快時維持原本的吞吐量；下限 50 擋住批次縮得太小，因為每一批另有固定成本（開 transaction、回報進度），批次越小、固定成本佔的比例越高。規劃期間每 0.8 秒回報一次的設定保留下來：剛好 1 秒時加上排程的誤差會超過門檻（量到的 1008 ms 就是這種情形）。

改完之後最大間隔 613 ms，落在 25500→26000，也就是還是 500 本、提交超過 0.4 秒而觸發縮小的那一批；其次的 606 ms 與 579 ms 落在 28864→29322、29322→29628 這兩個縮小過的批次之間。全部時間 31 秒，固定 500 本時也是約 31 秒，因為總工作量不變，只是切得比較細。

## 判斷標準：測試的代表性、逐條往返與批次大小

測試的資料庫執行器跟正式執行的結構不同時（測試用同一個 isolate 的記憶體資料庫、正式執行用背景 isolate），測試量到的只有 SQLite 本身的時間，跨 isolate 的往返完全沒被量到，寫入的條數越多兩邊差得越遠。Mac 上用跟手機相同的 `createInBackground` 開檔案資料庫，重現的是往返的次數，不是每一次往返的成本；這次兩邊同一批差了將近百倍，所以代表手機的數字只來自實機，或來自「條數 × 實機上每條的平均成本」的估計；這個平均含排隊與等待，換一個 APP 或一段不同忙碌程度的工作時要在自己的實機上重量。

一段寫入在 transaction 裡逐條 `await` 時，它的耗時含逐條往返的成本；資料庫轉接層那個收集操作、提交時逐條 `await` 的批次物件也屬於這一種；語句收齊之後一次送出時，往返只有一次。耗時跟寫入的條數成正比、而不跟資料量成正比時，從機制推論成本在往返；這次的證據是只改送出方式、條數不變，耗時就下降。

分批工作的最長一次提交落在更新門檻之內時，進度兩次更新之間的間隔不會因為提交而超過門檻；最大間隔越到工作後段越長、而且落在相鄰兩批的提交之間時，代表一批的提交時間隨資料量變長，而批次大小固定不變；這時縮短規劃期間的回報間隔，最大間隔不會變，要改的是批次大小。
