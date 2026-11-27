---
title: "Flutter 實機效能量測的排查：integration_test 的打字、無障礙樹、頁面監聽與背景等待，以及 flutter drive 解除安裝 APP 時的資料保全"
slug: "flutter-integration-test-profile-measurement-pitfalls"
date: 2026-11-28
draft: false
description: "用 integration_test 加 flutter drive --profile 在手機上量效能，數字看起來合理卻跟預期對不上、量測卡到逾時，或量完發現 APP 與資料不見時讀"
tags: ["flutter", "integration_test", "flutter-drive", "performance", "android", "adb", "sqlite"]
---

事件發生在 2026 年 11 月 27 日到 28 日。環境是一個 Flutter 3.41 的書庫 APP、Android 實機 Samsung SM-S9010（Android 16），以及一台 macOS 的開發機。操作是用 `integration_test` 寫的量測測試，以 `flutter drive --profile` 在手機上量 5 萬本書庫的冷啟動、記憶體、打字與捲動時的 frame、搜尋套用到書單更新的時間，以及往空書庫匯入 5 萬本的進度與停止；前後跑了十幾次，手機上同時有使用者真實的書庫資料。

這篇整理兩類事：量測本身的缺陷，包括 `enterText` 的字沒有送進 APP、`testWidgets` 預設建無障礙樹、測試直接讀一個沒有元件監聽的頁面資料、APP 在背景時 `tester.pump()` 等不到 frame、錄 timeline 時連不回 VM service，以及量測期間碰到螢幕；還有量測對手機資料的影響，包括 `flutter drive` 結束時解除安裝 APP、螢幕關掉讓 APP 進背景，以及用 `sqlite3` 查看備份時改到了備份。量到的效能數字與拆解在 [書單捲動與換搜尋結果時的慢 frame 拆解](/work-log/flutter-list-jank-cjk-text-layout-breakdown/)。

## 情境條件

這些缺陷出現在用 `integration_test` 套件寫量測、在實機上以 `flutter drive` 執行的情形。`integration_test` 的 `IntegrationTestWidgetsFlutterBinding` 讓測試在真實的 APP 行程裡跑，但它沿用 `flutter_test` 的許多預設值，那些預設值是為功能測試設的。量測腳本只負責送出動作與收集時間，動作有沒有真的改變 APP 的狀態，腳本不會自己檢查；所以下面每一個缺陷都讓量測照樣跑完、照樣產出數字。

## 打字沒有送進 APP

量測要量「打字時的 frame」：在書單頁的搜尋框依序輸入「一」「一丁」「一丁七」「一丁」，每次之後等 250 ms（超過 APP 的 150 ms 延遲套用），再甩動書單。前幾次量到的 frame 統計落在合理範圍，沒有人懷疑。

後來為了拆解時間，用 `binding.traceAction` 錄下這一段的 timeline，並在 APP 的查詢流程上打了計時點（`q.ids.start` 這類 `Timeline.instantSync`）。錄到的 timeline 裡，打字那一段一筆查詢的計時點都沒有，只有捲動時讀頁面的計時點。打字沒有觸發任何查詢，代表搜尋條件根本沒變。

成因是 `IntegrationTestWidgetsFlutterBinding` 預設不攔截文字輸入：`tester.enterText` 送出的字進了手機真正的輸入法（log 裡有 `ImeTracker onShown`），沒有進到 APP 的 TextField。在打字之前呼叫 `tester.testTextInput.register()`，`enterText` 才會改走測試的文字輸入。

修完之後另外在每一次打字後加一條斷言：讀 APP 的搜尋條件，確認它等於剛打的字，不等就讓量測失敗。這條斷言讓同一類缺陷之後不會再安靜地通過。

## 無障礙樹是測試框架開的

timeline 上每個 frame 都有 1.3 到 2 ms 的 `SEMANTICS` 階段。手機上沒有開任何輔助功能（`adb shell settings get secure accessibility_enabled` 回 0，`enabled_accessibility_services` 是 null），使用者的 APP 不會建無障礙樹；建它的是 `testWidgets` 的參數 `semanticsEnabled`，預設是 true。

量測改成 `testWidgets(..., semanticsEnabled: false, ...)`，另外在同一次執行裡用 `final handle = tester.ensureSemantics();` 開著無障礙樹把同樣的動作量一次、量完 `handle.dispose()`，對照兩者。結果是 122 個 frame 裡 3 個超過 16.7 ms，開著時 121 個裡 1 個；差別在誤差範圍內。這次的 APP 上，無障礙樹不是慢 frame 的主因；但兩種設定要在同一次執行裡對照，因為同一支手機兩次執行之間的數字可以差 30% 左右。

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

`binding.traceAction(...)` 要從 APP 裡連回 APP 自己的 VM service 錄 timeline。用預設的 `flutter drive` 執行時，量測一開始就失敗，訊息是 `SocketException: Connection refused`。`flutter drive` 預設啟動 DDS 轉接 VM service，APP 裡記的那個連接埠連不上；加 `--no-dds` 之後錄得到。錄 timeline 本身會讓 APP 變慢，所以錄的那一次只拿來看各段時間的比例，驗收的數字用沒有錄的那一次。

## 量測期間碰到螢幕

有一次量測的 log 裡出現一串 `Some possible finders for the widgets at Instance of 'Offset'`，後面列出 `KeycapButton`、`ShellHeader`、`ListView` 這類元件。這不是錯誤：`integration_test` 把量測期間螢幕上的觸控當成測試輸入，每次觸控都列出那個位置上有哪些元件。觸控會讓 APP 換頁或捲動，量到的就不是腳本的操作；量測開始前要請持有手機的人不要碰它。

## `flutter drive` 結束時解除安裝 APP

每一次 `flutter drive` 跑完（測試通過或失敗）之後，`adb shell pm list packages | grep <applicationId>` 都找不到 APP：`flutter drive` 在結束時解除安裝 APP，APP 的資料庫跟著刪掉。手機上有使用者真實的書庫時，量測之前要先備份，量測之後要還原並確認。這次用的步驟：

```bash
adb shell am force-stop com.example.app
for f in book_overview.db book_overview.db-shm book_overview.db-wal; do
  adb exec-out run-as com.example.app cat "databases/$f" > "backup/$f"
done
shasum backup/*
adb push backup/book_overview.db /data/local/tmp/restore_book_overview.db
```

`com.example.app` 換成自己 APP 的 applicationId（在 `android/app/build.gradle` 裡）；`book_overview.db` 換成自己的資料庫檔名，資料庫用 WAL 模式時三個檔都要拉，最近的寫入可能還在 `-wal` 裡；`backup/` 是電腦上的備份目錄。`run-as` 只對 debug 版有效，所以備份要在裝著 debug 版時做。最後那一行把備份也放一份在手機上，還原時不必從電腦再傳；`-shm` 與 `-wal` 照同樣的方式推上去。

還原是反過來做：重裝 debug 版，在 `run-as` 底下把 `/data/local/tmp/` 的檔案複製回 `databases/`，`chmod 771 databases`、資料庫檔 `chmod 600`。還原之後把資料庫拉回電腦，用一組固定的查詢（每本書的 id 與書名、標籤關聯、自訂標籤）列出內容，跟備份當下列出的清單逐行比對，相同才算還原完成。這次十幾次量測，每一次都照這個流程還原並比對。

會寫入資料的量測（匯入）不能用使用者的資料庫跑：量測之前刪掉手機上 APP 的資料庫檔，讓 APP 開起來建一個空的，量完再還原。

## 螢幕關掉讓 APP 進背景

有一次匯入的量測在開始後約 70 秒被終止，log 裡最後一行是 `Process ... exited due to signal 9`。`adb shell dumpsys power | grep mWakefulness` 回 `Dozing`，`dumpsys window` 顯示鎖定畫面開著：螢幕自動關閉，APP 進了背景，匯入照設計暫停，量測等不到進度。量測期間用 `adb shell svc power stayon usb` 讓手機接著 USB 時螢幕不關；先用 `adb shell settings get global stay_on_while_plugged_in` 讀出原本的值並記下（這支手機原本是 0），量完 `adb shell settings put global stay_on_while_plugged_in 0` 改回去。

## 查看備份時改到備份

備份做好之後，對備份的主檔直接跑了 `sqlite3 backup/book_overview.db "PRAGMA user_version; SELECT COUNT(*) FROM books;"` 確認版本與筆數。之後要還原時，備份目錄裡主檔的 SHA1 變了，`-wal` 變成空檔。`sqlite3` 以一般模式開啟 WAL 模式的資料庫，關檔時做了 checkpoint，把 WAL 的內容寫進主檔。內容沒有變（還原後逐行比對相同），但備份已經不是當初複製下來的那一份。查看備份時要先複製一份再開，或用 `sqlite3 -readonly`。

## 判斷標準

一份量測的數字代不代表它宣稱的動作，看量測裡有沒有一條斷言確認那個動作改變了 APP 的狀態。沒有這條斷言時，動作沒發生的量測跟動作發生的量測產出同一種數字；這次打字沒生效的那幾次就是這樣。等待逾時時，失敗訊息裡有沒有當下的狀態，決定了能不能分出是 APP 慢還是量測沒做到。

測試框架的預設值會不會進到量測，看它跟使用者的執行環境一不一樣：文字輸入的攔截、無障礙樹，在使用者的手機上都跟 `testWidgets` 的預設不同。不同的改成跟使用者一致；要知道某個預設值的影響時，在同一次執行裡開與不開各量一次。

手機上的資料保不保得住，看量測前有沒有備份全部的資料庫檔、量測後有沒有逐行比對還原的結果。`flutter drive` 每一次跑完都會解除安裝 APP（這次量測中途把它停掉的那一次，APP 還在）；查看備份時用唯讀模式或副本，備份本身只在還原時讀。
