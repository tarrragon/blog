# 在實機上以 profile mode 量效能：資料保全與量測本身的陷阱

> **何時讀**：用 `integration_test` 寫量測、以 `flutter drive --profile` 在 Android 實機上跑時。截圖驗證畫面的流程在本 skill 的 SKILL.md；這一份管量測跑之前、跑之中、跑之後要守的事。不適用：iOS 實機（沒有實測）、截圖驗證（見 SKILL.md）、資料不在 SQLite 的 APP（Hive、Isar 這類；本檔的內容清單與清資料都依 SQLite，沒有實測其他格式）。

實測的配置是 Samsung SM-S9010（Android 16）、Flutter 3.41、drift（SQLite 在背景 isolate）；其他配置照同樣的檢查自己量。標了「推論」或「沒有實測」的句子，在這個配置上也沒有跑過。

## 開始之前：設備與變數

這條路不走 SKILL.md 的〈前置〉與 `env.sh`，所以在 `<暫存目錄>/measure/` 底下另建一份變數檔（跟截圖流程的檔分開，同一個 session 先拍截圖再量效能時不會互相蓋掉），之後每一次 shell 呼叫都先 `source` 它（每次呼叫是新的 shell，前一次的 `export` 留不下來）：

```bash
"${ADB:-adb}" devices                     # 讀出手機的序號，狀態要是 device
mkdir -p <暫存目錄>/measure
cat > <暫存目錄>/measure/env.sh <<'EOF'
export ANDROID_SERIAL=<序號>               # 上一行讀到的序號
export APP_ID=<applicationId>              # android/app/build.gradle（或 .kts）的 applicationId
export APP_DIR=/data/user/0/<applicationId> # APP 的資料目錄，run-as 底下用絕對路徑
# export ADB=<adb 的完整路徑>               # adb 不在 PATH 時才寫，找法照 SKILL.md〈前置〉
EOF
```

本檔的 `adb` 指 `"${ADB:-adb}" -s "$ANDROID_SERIAL"`。`flutter drive`、`flutter build`、`flutter install` 都另外帶 `-d "$ANDROID_SERIAL"`。下文的 `<量測目錄>` 指 `<暫存目錄>/measure`；`<暫存目錄>` 是這次工作專屬、repo 以外的目錄。

`adb shell` 把後面的引數用空白串起來交給手機的 sh 再解析一次，本機 shell 先吃掉的引號與跳脫到了手機上就不見了。所以含引號、括號或萬用字元的遠端指令，整串用雙引號包起來交給 `adb shell`，裡面的引號與跳脫照手機端要看到的樣子寫（本檔的指令都這樣寫）。

## 跑之前：資料保全

`flutter drive` 跑完時會把 APP 解除安裝，APP 的資料跟著刪掉（實測）。測試失敗或中途停掉 `flutter drive` 時會不會解除安裝，沒有可依賴的實測（中途停掉的那一次 APP 還在，只觀察到一次），一律照會被解除安裝準備。`flutter drive --help` 列出的 `--keep-app-running` 只說明測試之後要不要停掉 APP，沒有寫到解除安裝，不拿它當保住資料的做法。

`adb shell pm path "$APP_ID"` 有輸出（APP 已經裝在這支手機上）時，〈記下使用者原本裝的版本〉到〈在手機上也放一份還原檔〉這五步一律要做，除非使用者在這次對話裡明說這支手機上的資料可以丟；執行者自認「這是測試機、沒有真實資料」，不改變本款結果。沒有輸出時，手機上沒有這個 APP 的資料可保，跳過這五步，在回報裡寫出 `pm path` 沒有輸出。〈清掉 APP 的資料〉與〈放入 APP 要讀的檔案〉照各自的條件做。做錯的代價是使用者的資料沒了。

這五步每個 session 只做一次：第二次以後的量測照〈第二次以後的量測〉做，不重跑這五步（重跑時 `>` 會用已經被解除安裝的 APP 的空結果，蓋掉第一次記下的版本與清單）。

1. **記下使用者原本裝的版本**：`adb shell "dumpsys package $APP_ID | grep -E 'versionName|versionCode'" > <量測目錄>/app-version.txt`，再問使用者這一版是怎麼建的（哪個 commit、debug 或 release、有沒有帶 `--dart-define-from-file` 這類參數），寫進同一個檔；使用者答不出時停下來，不往下做，因為還原時要裝回這一版。接著跑 `adb shell "run-as $APP_ID true"`：回 `package not debuggable` 時，使用者裝的是 release 或商店版，`run-as` 讀不到資料，本檔的備份做不下去。停下來，給使用者兩個選項：用 APP 自己的匯出功能備份、量完請使用者從原來的來源（商店）重裝並匯入；或改用一支沒有真實資料的手機。

2. **列出 APP 的全部檔案並存成清單**：資料庫放在哪個目錄由套件決定（sqflite 慣例是 `databases/`，drift 與其他套件常放在 `app_flutter/`、`files/`），不照預設路徑猜。

   ```bash
   adb shell "run-as $APP_ID find $APP_DIR -type f" > <量測目錄>/app-files.txt
   adb shell "run-as $APP_ID find $APP_DIR \\( -name '*.db*' -o -name '*.sqlite*' \\)" > <量測目錄>/db-files.txt
   ```

   `app-files.txt` 去掉 `cache/`、`code_cache/` 底下的檔，就是要備份的檔案集（資料庫、`shared_prefs/`、封面圖、使用者匯入的檔都在裡面，解除安裝時一起刪掉）。`db-files.txt` 是其中的 SQLite 資料庫檔（含 `-wal`、`-shm`：WAL 模式時最近的寫入可能還在 `-wal` 裡），用在內容清單、清資料與還原後的比對。之後每一步要用的目錄與檔名都從這兩份取，不靠對話裡的記憶。`db-files.txt` 是空的時，停下來問使用者資料存在哪裡；資料不在 SQLite 時本檔不適用（見檔頭）。

3. **停掉 APP，逐檔拉回並和手機上的原檔比對**：先停 APP，複製期間檔案才不會再被寫入。拉回時保留檔案在 `$APP_DIR` 底下的相對路徑，不同目錄裡的同名檔才不會互相蓋掉。

   ```bash
   adb shell am force-stop "$APP_ID"
   mkdir -p <量測目錄>/backup/<相對路徑的目錄>                                          # 每個目錄各建一次
   adb exec-out run-as "$APP_ID" cat "$APP_DIR/<相對路徑>" > <量測目錄>/backup/<相對路徑>  # 備份集的每個檔各跑一次
   (cd <量測目錄>/backup && find . -type f -exec shasum -a 256 {} +) > <量測目錄>/backup.sha256
   adb shell "run-as $APP_ID sh -c 'cd $APP_DIR && sha256sum <./相對路徑...>'" > <量測目錄>/device.sha256   # shell 的身分進不了 APP 目錄，cd 要在 run-as 裡做；路徑寫成跟 backup.sha256 一樣的 ./ 開頭
   adb shell "run-as $APP_ID ls -ld <每個資料目錄>; run-as $APP_ID ls -l <每個資料目錄>" > <量測目錄>/backup-perms.txt
   ```

   `backup.sha256` 與 `device.sha256` 的雜湊欄逐檔要相同，列數也要等於備份集的檔數。不同時那個檔重拉一次：`exec-out` 不分開 stderr，`run-as` 失敗時錯誤訊息會寫進備份檔（推論），雜湊對不上就是訊號。`backup-perms.txt` 記下目錄本身與檔案的權限，還原時照它改回。

4. **從副本產生一份內容清單**：把 `backup/` 整個複製成另一個目錄，用 `sqlite3 -readonly <副本>` 對 `db-files.txt` 的每個主檔跑一組固定的查詢（主要資料表的主鍵與關鍵欄位、關聯表，每條都 `ORDER BY` 主鍵，排序固定才比對得了），查詢存成 `<量測目錄>/content-queries.sql`，輸出存成 `<量測目錄>/content-list.txt`。不開備份本身：一般模式的 `sqlite3` 關檔時會做 checkpoint，把 WAL 併回主檔，備份的雜湊從此對不上；唯讀模式會不會寫入 `-shm`，SQLite 的文件沒有說明，所以也開副本。

5. **在手機上也放一份還原檔**：放在這次專屬的子目錄，跟別人放在 `/data/local/tmp/` 的檔分開，同名的既有檔也不會被蓋掉：

   ```bash
   adb push <量測目錄>/backup /data/local/tmp/"$APP_ID"-measure       # 目的地還不存在時，backup/ 的內容直接放進去（沒有實測）
   adb shell "cd /data/local/tmp/$APP_ID-measure && find . -type f -exec sha256sum {} +"
   adb shell "run-as $APP_ID ls /data/local/tmp/$APP_ID-measure/"
   ```

   第二行印出的路徑要跟 `backup.sha256` 的相對路徑一樣（多了一層 `backup/` 代表目的地原本就存在：列出那一層的路徑，下一次執行用列出的字面路徑刪掉再推），雜湊也逐檔相同。第三行確認 APP 的身分讀得到這個目錄（子目錄的權限沒有實測；列不出檔時先 `adb shell chmod 755 /data/local/tmp/"$APP_ID"-measure` 再查一次，仍然列不出就把還原檔直接放在 `/data/local/tmp/` 底下、檔名加上 `$APP_ID-` 前綴，這是實測過的放法）。之後還原時不必再從電腦傳，電腦上的暫存目錄被清掉時也還有一份。

6. **清掉 APP 的資料**（量測會寫入資料時）：會寫入的量測（匯入）要從已知的起點開始，不在使用者的資料上跑。檢查與刪除分兩次執行：
   - 第一次：`adb shell am force-stop "$APP_ID"`（APP 開著時刪檔，它會重建資料庫或寫回 WAL）；`adb shell "run-as $APP_ID sha256sum <db-files.txt 的路徑...>"`，跟 `device.sha256` 比對。不同代表備份之後又有寫入（例如使用者打開過 APP），回到〈停掉 APP，逐檔拉回並和手機上的原檔比對〉重做，不刪。
   - 第二次：用 `db-files.txt` 的絕對路徑逐一刪：`adb shell "run-as $APP_ID rm <絕對路徑>"`。

   這裡是 APP 停止時整檔刪除與替換，跟 `device-pitfalls.md`〈會寫入資料的點按〉禁止的「直接改 APP 的資料庫檔」（APP 執行中逐筆改內容）不同。

7. **放入 APP 要讀的檔案**（合成資料庫、匯入檔）：先 `adb push` 到 `/data/local/tmp/"$APP_ID"-measure/`，再用 `adb shell "run-as $APP_ID cp /data/local/tmp/$APP_ID-measure/<檔名> <db-files.txt 裡的目錄>/"` 複製進去。這一步會覆寫同名的檔，只在〈記下使用者原本裝的版本〉到〈在手機上也放一份還原檔〉做完之後做。

## 跑之前：手機與主機的狀態

- **螢幕要全程亮著**：螢幕關掉時 APP 進背景；做了「進背景就暫停」的 APP 會照設計停下來，量測就停住、等到逾時。先讀原本的設定 `adb shell settings get global stay_on_while_plugged_in`，把讀到的值寫進 `<量測目錄>/device-original.txt`（context 被壓縮之後，對話裡的值會讀不到）；量測期間 `adb shell svc power stayon usb`（接著 USB 時保持亮著），量完用 `adb shell settings put global stay_on_while_plugged_in <檔裡記下的原值>` 改回（實測的那支手機原本是 0，只是那支手機的值）。
- **量測期間不要碰手機**：系統手勢（下拉通知、回主畫面）會讓 APP 進背景，量測就停住。畫面上的點按會被測試框架攔下，log 印出 `Some possible finders for the widgets at Offset`（實測）；Flutter 的 `TestWidgetsFlutterBinding.shouldPropagateDevicePointerEvents` 預設是 false，API 文件寫明這時裝置上的觸控被丟掉、不送進 APP。開始前請使用者放著手機。
- **主機磁碟**：這個專案增量建置 profile 版約再用 1 GB；自己的專案在建置前後各看一次可用空間，就知道要留多少。不要清 Gradle 快取（`~/.gradle/caches`）或專案的 `build/` 來騰空間：它們是每次建置都要用的工作區，清掉之後下一次建置會整個建回來（實測清掉轉換快取騰出 4.2 GB，下一次建置用掉約 4 GB）。空間不夠時請使用者清專案以外佔用磁碟的檔案。

## 跑量測

```bash
flutter drive --profile -d "$ANDROID_SERIAL" \
  --driver=test_driver/integration_test.dart \
  --target=integration_test/<量測檔>.dart \
  > <量測目錄>/drive.log 2>&1
```

`--driver` 與 `--target` 填專案裡的路徑；要錄 timeline 時另加 `--no-dds`（見下面的陷阱表）。建置加量測可能跑上十幾分鐘，下這條指令的 shell 工具要給夠長的逾時，或放在背景跑、等它結束。結束之後讀 `drive.log` 的最後幾行：`All tests passed` 是通過，其餘是失敗，原因在前面的輸出。log 裡出現 `Uninstalling old version` 時，`flutter drive` 在安裝前先解除安裝了手機上的版本（推論：簽章或 versionCode 不同時會這樣），〈放入 APP 要讀的檔案〉放進去的檔也一起刪掉，這一次量到的不算，照〈第二次以後的量測〉重跑。

## 第二次以後的量測

改了程式重量，是這類工作的主要迴圈。第一次量完 APP 多半已經被解除安裝，`run-as` 回 `unknown package`，〈放入 APP 要讀的檔案〉做不了。所以每一次重量之前：

1. 先裝上一版能 `run-as` 的 APP：`flutter build apk --profile -d "$ANDROID_SERIAL"` 再 `flutter install --profile -d "$ANDROID_SERIAL"`（profile 版是否允許 `run-as` 沒有實測；`run-as $APP_ID true` 回 `package not debuggable` 時改裝 debug 版）。
2. 重做〈清掉 APP 的資料〉（量測會寫入時）與〈放入 APP 要讀的檔案〉，再照〈跑量測〉跑。

〈記下使用者原本裝的版本〉到〈在手機上也放一份還原檔〉不重做；`<量測目錄>` 裡的 `app-version.txt`、兩份清單、`backup/` 與雜湊，從第一次留到〈跑完之後：還原〉做完。

## 寫量測時：量測本身的陷阱

這幾個陷阱有兩種表現：量測照樣產出數字，量到的卻是別的事（文字輸入、無障礙樹、錄 timeline）；或量測卡住、逾時、連不上（`autoDispose`、背景期間 `pump`、DDS）。後一種要靠失敗訊息裡的狀態才分得出原因。

| 陷阱 | 後果 | 寫法 |
|------|------|------|
| `integration_test` 的 binding 預設不攔截文字輸入 | `tester.enterText` 的字送進手機的輸入法，沒有進 TextField；「打字時的效能」量到的只有其他動作 | 進要打字的頁面之後呼叫 `tester.testTextInput.register()` |
| `testWidgets` 的 `semanticsEnabled` 預設是 true | 每個 frame 多建一次無障礙樹；使用者沒開輔助功能時沒有這筆成本 | `testWidgets(..., semanticsEnabled: false, ...)`；要知道它的影響時，用 `tester.ensureSemantics()` 在同一次執行裡開著再量一次對照 |
| 直接讀一個 Riverpod 的 `autoDispose` provider，而畫面上沒有元件在監聽它 | 讀到的是剛建立就被丟掉的空值，等待它更新會逾時 | 讓監聽它的元件在畫面上（例如捲動之後把清單跳回頂端），或讓量測自己用 `ProviderContainer.listen` 持有它 |
| APP 在背景（模擬 `AppLifecycleState.paused`）時呼叫 `tester.pump()` | 背景時不產生 frame，`pump` 一直等；測試卡住，連「回到前景」那一步都到不了 | 背景期間只用 `Future.delayed` 等真實時間，回前景之後才恢復 `pump` |
| 用 `binding.traceAction` 錄 timeline | APP 連不回自己的 VM service（`Connection refused`，實測）；推論是 `flutter drive` 預設啟動的 DDS 接手了 VM service 的連線，沒有查證 | `flutter drive --no-dds` |
| 錄 timeline 的那一次 | 錄的本身讓程式變慢 | 錄 timeline 的那一次只拿來拆比例，驗收的數字用沒錄的那一次 |
| 用 `binding.watchPerformance` 算超過 frame 預算的比例 | 它的 `FrameTimingSummarizer` 固定用 `kBuildBudget`（預設 16 ms），不看手機的刷新率；120 Hz 的手機上報出來的仍是 16 ms 預算下的比例 | 刷新率從 `View.of(context).display.refreshRate` 讀，連同值寫進紀錄；先把 `kBuildBudget` 設成 `1 / 刷新率` 再量，或自己用 `FrameTiming` 算，寫明比的是 build 還是整段時間 |

**每一個動作後面接一條斷言，確認它改變了狀態**：打字之後斷言搜尋條件等於打的字，換頁之後斷言路由，寫入之後斷言筆數。斷言失敗就讓量測失敗。**等待逾時時，失敗訊息裡帶出當下的狀態**（條件、輸入框內容、清單長度、頁面資料有沒有讀到），一次就分得出是被量的程式慢還是量測沒做到。

## 寫量測時：量對成本模型

- **資料庫要用正式的資料庫執行器**（drift 的 `NativeDatabase.createInBackground`：背景 isolate、檔案資料庫）：單元測試常用同一個 isolate 的記憶體資料庫，每條 SQL 沒有跨 isolate 的往返；手機上的背景 isolate 每條 `await` 都是一次往返。Mac 上用同樣的背景 isolate 量，重現的是往返的次數，不是每一次往返的成本（實測一批 500 本：Mac 上 0.3 秒，手機上 28 秒）。所以 Mac 上的量測用來確認修法減少了往返，批次寫入的驗收數字在實機上量（實測實機 1 萬本約 9.5 分鐘，改成一次送出之後約 4 秒）。
- **主執行緒卡頓另外用計時器量**：長工作期間畫面不一定一直重畫，只收 `FrameTiming` 會漏掉沒有 frame 時的卡頓。加一個每 50 ms 觸發的計時器，量它最晚遲到多少；50 ms 約是 60 Hz 下 3 個 frame，要抓更短的卡頓時把間隔縮短，計時器本身的成本會跟著變多。
- **同一項數字的起伏先量出來**：實測（檔頭的配置）同一個樣式的文字排版時間在兩次執行之間差約 ±30%。比較兩種設定時不拿另一次執行的數字當對照，在同一次執行裡交錯量幾次，差別超出對照組自己的分布範圍才算數。

## 跑完之後：還原

先跑 `"${ADB:-adb}" devices`，確認 `$ANDROID_SERIAL` 的狀態仍是 `device`。手機不在時（被拔掉、沒電），下面每一條都會回 `device not found`，`exec-out … >` 還會把錯誤訊息寫進檔案：等使用者接回再做；接不回來時，把還沒還原的項目（資料、螢幕常亮的設定、`/data/local/tmp/` 裡的副本、手機上的量測版）與要跑的指令寫進給使用者的最後一則總結。

1. **裝回使用者原本的版本**：不論 APP 還在不在都重裝。APP 被解除安裝時要裝；APP 還在時，手機上留著的是 `flutter drive` 裝的量測版（Dart 入口是量測檔、profile 版），使用者打開它跑的是量測本身（推論）。照 `app-version.txt` 建出同一版：用 `git worktree add <暫存目錄>/orig <commit>` 另建一份工作樹再建置，不在使用者的工作樹裡切 commit（切過去會帶著使用者沒提交的改動，或被擋下）。debug 版是在那份工作樹裡 `flutter build apk --debug` 再 `flutter install --debug -d "$ANDROID_SERIAL"`（只安裝、不啟動；這兩條沒有在本檔的配置實測，`flutter install` 可能先解除安裝舊版，所以重裝排在放回資料之前）。用 `adb shell pm path "$APP_ID"` 確認裝上了（`pm list packages | grep` 是部分比對，會命中名字相近的其他套件）。重裝之後先不要開 APP，做完下一步再開：APP 一開就會建一個新的空資料庫。回報裡寫出實際裝回的是哪一版。
2. **把還原檔放回去**：先 `adb shell am force-stop "$APP_ID"`。一次執行列出 `$APP_DIR` 底下現有的全部檔案，跟 `app-files.txt` 比對；下一次執行，用列出的絕對路徑刪掉兩種檔：資料庫目錄裡檔名以主檔名開頭、卻不在 `db-files.txt` 裡的檔（量測留下的 `-wal`、`-shm`、`-journal`，SQLite 會把它們當成這個資料庫的 WAL 或待回滾的 journal 讀進去），以及量測新建、不在 `app-files.txt` 裡的檔（列給使用者看過再刪）。目錄不存在時沒有檔案要刪，跳過。再用 `adb shell "run-as $APP_ID mkdir -p <資料目錄>"`，把 `/data/local/tmp/"$APP_ID"-measure/` 的還原檔照相對路徑 `cp` 回 `$APP_DIR`，權限照 `backup-perms.txt` 改回（實測的 APP 是目錄 `771`、資料庫檔 `600`，只是那支 APP 的值）。
3. **逐行比對內容**：把還原後的資料拉回電腦，存到 `backup/` 以外的目錄（`adb exec-out run-as "$APP_ID" cat "$APP_DIR/<相對路徑>" > <量測目錄>/restored/<相對路徑>`，備份集的每個檔各跑一次；寫進 `backup/` 會用可能有問題的還原結果蓋掉唯一一份好的備份）。APP 還沒開過，所以 `restored/` 的雜湊要逐檔等於 `backup.sha256`；再複製一份，用 `sqlite3 -readonly` 對副本跑 `content-queries.sql`，跟 `content-list.txt` 逐行比對。兩項都相同才算還原完成，在給使用者的回報裡寫出比對結果。不同時，先確認 `backup/` 的雜湊仍然等於 `backup.sha256`，從 `backup/` 重新 `adb push` 到 `/data/local/tmp/"$APP_ID"-measure/`，重做〈把還原檔放回去〉，再比對一次；仍然不同就停下來，請使用者先不要打開 APP，把不同的檔與兩份清單的 diff 給使用者。
4. **改回螢幕常亮的設定**：照 `device-original.txt` 的原值改回，回報裡寫出原值與改回之後讀到的值。檔裡沒有原值時停下來問使用者，不猜（跟 SKILL.md 的還原設備設定那一步相同）。
5. **清掉手機上的副本**：一次執行列出 `/data/local/tmp/"$APP_ID"-measure/` 裡的檔（使用者資料的還原檔、合成資料、匯入檔），問過使用者之後，下一次執行用列出的字面路徑刪。這些檔留在手機上，任何能用 adb 的人都讀得到使用者的資料。
