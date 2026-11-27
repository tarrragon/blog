---
title: "Flutter 實機效能量測的排查：integration_test 的打字、無障礙樹、頁面監聽與背景等待，以及 flutter drive 解除安裝 APP 時的資料保全"
slug: "flutter-integration-test-profile-measurement-pitfalls"
date: 2026-11-28
draft: false
description: "用 integration_test 加 flutter drive --profile 在手機上量效能，數字跟預期對不上、量測卡到逾時，或量完發現 APP 與資料不見時讀"
tags: ["flutter", "integration_test", "flutter-drive", "performance", "android", "adb", "sqlite"]
---

事件發生在 2026 年 11 月 27 日到 28 日。環境是一個 Flutter 3.41 的書庫 APP、Android 實機 Samsung SM-S9010（Android 16），以及一台 macOS 的開發機。操作是用 `integration_test` 寫的量測測試，以 `flutter drive --profile` 在手機上量合成的 5 萬本書庫的冷啟動、記憶體、打字與捲動時的 frame、搜尋套用到書單更新的時間，以及往空書庫匯入 5 萬本的進度與停止；前後跑了十幾次。同一支手機上，這個 APP 平常存著使用者真實的書庫資料（14 本），量測之前要先備份、量完再還原。

這篇整理量測本身的缺陷：`enterText` 的字沒有送進 APP、`testWidgets` 預設建無障礙樹、測試直接讀一個沒有元件監聽的頁面資料、APP 在背景時 `tester.pump()` 等不到 frame、錄 timeline 時連不回 VM service、量測期間碰到螢幕，以及螢幕關掉讓量測被終止；還有量測對手機資料的影響：`flutter drive` 結束時解除安裝 APP，以及用 `sqlite3` 查看備份時改到了備份。這些量測修正之後量到的數字分在三篇：冷啟動與記憶體在 [Flutter 書庫 APP 冷啟動時間的排查：把全部的書載入記憶體、資料庫單例的並行開檔與每次啟動的完整性檢查](/work-log/flutter-cold-start-database-open-and-integrity-check/)，匯入的進度與耗時在 [Flutter drift 匯入大量書籍時的寫入耗時排查：手機上 SQLite 在背景 isolate 的逐條往返、一次送出的語句記錄器，以及依提交時間調整批次大小](/work-log/flutter-drift-batch-write-isolate-round-trip/)，捲動與搜尋套用在 [Flutter 書單捲動與換搜尋結果時的慢 frame 拆解：timeline 分段、排版細項、中文字串的排版時間與字型實驗](/work-log/flutter-list-jank-cjk-text-layout-breakdown/)。

## integration_test 量測的缺陷出現的條件

這些缺陷出現在用 `integration_test` 套件寫量測、在實機上以 `flutter drive` 執行的情形。`integration_test` 的 `IntegrationTestWidgetsFlutterBinding` 讓測試在真實的 APP 行程裡跑，但它沿用 `flutter_test` 的許多預設值，那些預設值是為功能測試設的。量測腳本只負責送出動作與收集時間，動作有沒有改變 APP 的狀態，腳本不會自己檢查。這些缺陷的表現各不相同：打字沒送進 APP 與無障礙樹讓量測照樣產出數字，量到的卻是別的事；沒有元件監聽的頁面讓量測逾時；背景時的 `pump` 與系統手勢讓 APP 進背景，量測卡住而不逾時；錄 timeline 時連不回 VM service，量測一開始就失敗；螢幕關閉讓量測被終止。逾時與卡住的那幾種，查原因的人查不查得出來，要看失敗訊息或 log 裡有沒有當下的狀態。

## 打字沒有送進 APP

量測要量「打字時的 frame」：在書單頁的搜尋框依序輸入「一」「一丁」「一丁七」「一丁」，每次之後等 250 ms（超過 APP 的 150 ms 延遲套用（debounce），也就是停止輸入 150 ms 之後才套用搜尋條件），再甩動（fling）書單。這個量測沒有檢查搜尋條件是否改變；字沒有送進 APP 時，frame 統計照樣落在合理範圍，讀數字的人看不出這個缺陷。

錄下這一段的 timeline（`binding.traceAction`），並在 APP 的查詢流程上打計時點（`q.ids.start` 這類 `Timeline.instantSync`）之後，讀 timeline 的人才看得出這個缺陷：打字那一段一筆查詢的計時點都沒有，只有捲動時讀頁面的計時點。打字沒有觸發任何查詢，代表搜尋條件沒有變。

成因是 `IntegrationTestWidgetsFlutterBinding` 不攔截文字輸入：`tester.enterText` 送出的字進了手機真正的輸入法（log 裡有 `ImeTracker onShown`），沒有進到 APP 的 TextField。控制它的是 binding 的 `registerTestTextInput`：Flutter API 文件寫明單元測試用它把文字輸入換成假的鍵盤，integration test 會把它設成 false，好測真實的輸入法或鍵盤；這個預設服務的是要測輸入法本身的整合測試。量效能時字要進到 APP，所以量測在打字之前呼叫 `tester.testTextInput.register()`，`enterText` 才會改走測試的文字輸入。

修完之後另外在每一次打字後加一條斷言：讀 APP 的搜尋條件，確認它等於剛打的字，不等就讓量測失敗。有了這條斷言，字沒有送進 APP 時量測會失敗，不再產出數字。

## `testWidgets` 預設建立的無障礙樹

timeline 上每個 frame 都有 1.3 到 2 ms 的 `SEMANTICS` 階段。手機上沒有開任何輔助功能（`adb shell settings get secure accessibility_enabled` 回 0，`enabled_accessibility_services` 是 null），使用者的 APP 不會建無障礙樹。`testWidgets` 的 `semanticsEnabled` 預設是 true，測試框架因此在回呼開始前呼叫 `ensureSemantics()`，替每個 frame 建無障礙樹；Flutter API 文件的 `testWidgets` 一頁只寫了這個效果，沒有說明這個預設值服務的情境。這支手機沒開輔助功能，所以量效能時改成跟使用者一致。

量測改成 `testWidgets(..., semanticsEnabled: false, ...)`，另外在同一次執行裡用 `final handle = tester.ensureSemantics();` 開著無障礙樹把同樣的動作量一次、量完 `handle.dispose()`，對照兩者。關掉無障礙樹時 122 個 frame 裡 3 個超過 16.7 ms，開著時 121 個裡 1 個，兩者差兩個 frame。開著的那一輪排在第二輪、輸入的是另一組字，兩輪有順序與輸入的差別，所以這個對照只支持較弱的結論：這次的 APP 上，看不出無障礙樹是慢 frame 的主因。兩種設定放在同一次執行裡對照，是因為同一支手機兩次執行之間，文字排版的時間可以差 30% 左右（量測在 [Flutter 書單捲動與換搜尋結果時的慢 frame 拆解：timeline 分段、排版細項、中文字串的排版時間與字型實驗](/work-log/flutter-list-jank-cjk-text-layout-breakdown/)）。

## 測試讀的頁面沒有元件在監聽

量測「搜尋套用到書單更新」時，腳本改了搜尋條件之後，反覆讀兩個 Riverpod provider：符合條件的 id 清單，以及書單第一頁的書，直到兩者都換成新的結果。在量測前面加了一段「甩動全書單四次」之後，這一步開始等 5 秒逾時。

把當下的狀態寫進失敗訊息（搜尋條件、id 清單長度、預期長度、第一頁有幾本）之後，一次就看出原因：id 清單已經換對了，第一頁是 null。第一頁的 provider 是 `autoDispose` 的，只有畫面上第一頁的列在監聽它；甩動之後書單停在中段，第一頁的列不在畫面上，沒有任何元件監聽第一頁。測試直接 `container.read` 一個沒有監聽者的 `autoDispose` provider，讀到的是剛建立、還沒讀到資料就被丟掉的空值。

修法是甩動之後把書單跳回最上面，讓第一頁的列回到畫面上：

```dart
tester
    .state<ScrollableState>(find.descendant(of: list, matching: find.byType(Scrollable)).first)
    .position
    .jumpTo(0);
```

`list` 是書單的 `ListView` 的 finder。另一種做法是讓量測自己用 `container.listen` 持有那個 provider，代價是量到的第一頁不再代表「畫面上的那一頁」。

## APP 在背景時 `pump` 等不到 frame

匯入的量測要驗證 APP 進背景時匯入會暫停：在匯入到第 1 萬本時，腳本依序送出 `inactive`、`hidden`、`paused` 三個生命週期狀態，等匯入暫停、等 3 秒、確認已處理的本數沒變，再送出回前景的狀態。腳本等待的迴圈每一輪都 `await tester.pump()`。

這一次量測停在送出 `paused` 之後，十幾分鐘沒有任何進度，也沒有逾時。手機上 APP 的資料庫在那一刻之後就沒有再寫入，代表匯入照設計暫停了；卡住的是腳本。APP 在背景時 Flutter 不產生 frame，`tester.pump()` 一直等一個不會來的 frame，腳本走不到「送出回前景」那一行。

修法是用一個旗標標出背景期間，背景時等待迴圈只用 `Future.delayed` 等真實時間，不呼叫 `pump`；送出回前景的狀態之後才恢復 `pump`。

## 錄 timeline 時連不回 VM service

`binding.traceAction(...)` 要從 APP 裡連回 APP 自己的 VM service 錄 timeline。用預設的 `flutter drive` 執行時，量測一開始就失敗，訊息是 `SocketException: Connection refused`；加 `--no-dds` 之後，`traceAction` 正常回傳錄下的 timeline。DDS（Dart Development Service）是 `flutter drive` 預設啟動的一層服務，依 Dart SDK 的 DDS README，它接收 VM service 用戶端的請求、轉送給 VM service，並另外提供擴充功能。APP 連不回自己的確切成因是推論：DDS 接手 VM service 之後，APP 裡記的那個位址不再接受連線。錄 timeline 本身會讓 APP 變慢，所以錄的那一次只拿來看各段時間的比例，驗收的數字用沒有錄的那一次。

## 量測期間碰到螢幕

有一次量測的 log 裡出現一串 `Some possible finders for the widgets at Instance of 'Offset'`，後面列出 `KeycapButton`、`ShellHeader`、`ListView` 這類元件。這串訊息是 `integration_test` 列出觸控位置上有哪些元件。依 Flutter API 文件，binding 的 `shouldPropagateDevicePointerEvents` 預設是 false，裝置上的觸控被丟掉、不送進 APP；文件沒有說明這個預設值服務的情境，從機制推論，它讓腳本的操作不被手上的觸控打斷。觸控不會改到 APP，但系統手勢（下拉通知、回主畫面）會讓 APP 進背景，量測就停住；所以量測開始前，持有手機的人放著它不動。

## `flutter drive` 結束時解除安裝 APP

`flutter drive` 跑完之後，`adb shell pm list packages | grep <applicationId>` 找不到 APP：`flutter drive` 在結束時解除安裝 APP，APP 的資料庫跟著刪掉。這次有一次在中途停掉 `flutter drive`，APP 沒有被解除安裝；這只觀察到一次，保住資料的做法仍是每一次量測之前備份。`flutter drive --help` 列出的 `--keep-app-running` 只說明測試之後要不要停掉 APP，沒有寫到解除安裝，所以這次沒有拿它當保住資料的做法。

手機上有使用者真實的書庫時，量測之前先備份，量測之後還原並確認。這次用的備份步驟：

```bash
adb shell am force-stop com.example.app
adb shell run-as com.example.app ls -l databases > backup-perms.txt
for f in book_overview.db book_overview.db-shm book_overview.db-wal; do
  adb exec-out run-as com.example.app cat "databases/$f" > "backup/$f"
  adb push "backup/$f" "/data/local/tmp/restore_$f"
done
shasum backup/* > backup.sha1
```

`com.example.app` 換成自己 APP 的 applicationId（在 `android/app/build.gradle` 裡）；`databases/` 是這個 APP 放資料庫的目錄，`book_overview.db` 是它的檔名，兩者都依資料庫套件與 APP 而不同，自己的 APP 先用 `adb shell run-as <applicationId> find . -name '*.db*'` 列出實際的路徑。資料庫用 WAL 模式時三個檔都要拉：寫入先記進 `-wal`，checkpoint 時才併回主檔（這個機制叫預寫日誌，見 [Write-Ahead Log](/backend/knowledge-cards/write-ahead-log/) 卡），最近的寫入可能還在 `-wal` 裡。`backup/` 是電腦上的備份目錄。`force-stop` 排在第一行，先停掉 APP，複製期間三個檔才不會再被寫入；`shasum` 記下的雜湊在還原之前用來確認備份沒有被動過（下面〈查看備份時改到備份〉就是靠它發現的）。`run-as` 只對可除錯（debuggable）的版本有效：這次手機上帶著使用者資料的正是 debug 版，所以備份做得了；資料在 release 版或商店版的 APP 裡時，`run-as` 讀不到，這個備份方式不適用。`ls -l` 那一行記下資料庫檔的權限，還原時照它改回。迴圈裡的 `adb push` 把三個檔各放一份在手機上，還原時不必從電腦再傳。

還原的步驟：

```bash
flutter install --debug                       # 裝回 debug 版，只安裝、不啟動（這一行沒有實測）
adb shell am force-stop com.example.app
adb shell run-as com.example.app mkdir -p databases
adb shell run-as com.example.app chmod 771 databases
for f in book_overview.db book_overview.db-shm book_overview.db-wal; do
  adb shell run-as com.example.app cp "/data/local/tmp/restore_$f" "databases/$f"
done
adb shell run-as com.example.app chmod 600 databases/book_overview.db databases/book_overview.db-shm databases/book_overview.db-wal
```

重裝之後先不打開 APP：APP 一開就會建一個新的空資料庫，蓋在要還原的位置上。`force-stop` 擋住的是同一件事，複製期間 APP 不能開著。`cp` 把推上去時加的 `restore_` 前綴改回原本的檔名。權限照備份前 `ls -l` 看到的值改回（這支手機上是目錄 `771`、資料庫檔 `600`：擁有者是 APP 的使用者；目錄的擁有者與群組可以讀寫、進入，其他使用者只能進入；資料庫檔只給擁有者讀寫）；重新安裝的 APP 還沒開過時 `databases/` 不存在，所以先 `mkdir -p` 再改權限。還原之後把資料庫拉回電腦，用一組固定的查詢（每本書的 id 與書名、標籤關聯、自訂標籤）列出內容，跟備份當下列出的清單逐行比對，相同才算還原完成。這次十幾次量測，每一次都照這個流程還原並比對。

會寫入資料的量測（匯入）在一個空的資料庫上跑，量測寫進的資料才不會混進使用者的書庫：量測之前刪掉手機上 APP 的資料庫檔，讓 APP 開起來建一個空的，量完再還原。

## 螢幕關掉讓量測被終止

有一次匯入的量測在開始後約 72 秒被終止。測試開始時螢幕已經是關的：`adb shell dumpsys power | grep mWakefulness` 回 `Dozing`。約 72 秒之後，`flutter drive` 的 log 結尾是 `DriverError … Service connection disposed`；logcat 裡 ActivityManager 記下 APP 被 `force-stop`，行程以 `signal 9` 結束，送出 `force-stop` 的是 flutter 工具，在連線斷掉之後。螢幕關閉與連線中斷之間的因果是推論：這一版的測試沒有印匯入進度，看不出 APP 進背景之後是否照設計暫停；能確定的是讓螢幕常亮之後，同一個量測重跑正常。

量測期間用 `adb shell svc power stayon usb` 讓手機接著 USB 時螢幕不關。這個指令改的是系統設定 `stay_on_while_plugged_in`，它決定接上電源時螢幕要不要保持亮著；預設是 0（不保持），接著電源時螢幕照一般的逾時關閉，跟沒接電源時一樣（從設定的作用推論）。改之前先用 `adb shell settings get global stay_on_while_plugged_in` 讀出原本的值並記下，量完用 `adb shell settings put global stay_on_while_plugged_in <剛才讀到的值>` 改回去（這支手機原本是 0）。

## 查看備份時改到備份

備份做好之後，對備份的主檔直接跑了 `sqlite3 backup/book_overview.db "PRAGMA user_version; SELECT COUNT(*) FROM books;"` 確認版本與筆數。之後要還原時，備份目錄裡主檔的 SHA1 變了，`-wal` 變成空檔。`sqlite3` 以一般模式開啟 WAL 模式的資料庫，關檔時做了 checkpoint，把 WAL 的內容寫進主檔。內容沒有變（還原後逐行比對相同），但備份已經不是當初複製下來的那一份。查看備份時先複製一份再開，唯讀模式也開副本：SQLite 的文件寫明 checkpoint 由可寫入的連線發起，由此推論 `sqlite3 -readonly` 不會把 WAL 併回主檔；它會不會寫入 `-shm`，文件沒有說明，所以唯讀模式保不保得住備份的雜湊，判斷不出來。

## 判斷標準：量測的代表性、測試框架的預設值與手機上的資料

量測裡有一條斷言確認那個動作改變了 APP 的狀態時，數字才代表那個動作；沒有這條斷言時，動作沒發生的量測跟動作發生的量測產出同一種數字，這次打字沒生效的那幾次就是這樣。量測逾時時，失敗訊息寫出當下的狀態（條件、清單長度、頁面資料有沒有讀到），才看得出是 APP 慢還是量測沒做到。

測試框架的預設值跟使用者的執行環境不同時（文字輸入的攔截、無障礙樹），量到的成本在使用者的手機上不存在，或使用者手機上的成本沒被量到；要知道某個預設值的影響，在同一次執行裡開與不開各量幾次，差別要超出同一個設定重複量的起伏才算數（這支手機上，同一個樣式的文字排版在兩次執行之間就差約 ±30%）。

量測前備份了全部的資料庫檔、量測後逐行比對過還原結果時，才確定手機上的資料保住了。`flutter drive` 跑完會解除安裝 APP，中途停掉時不解除安裝只觀察到一次，不足以依賴；查看備份時開的是副本，備份本身只在還原時讀，備份的雜湊才跟量測前記下的值相同。
