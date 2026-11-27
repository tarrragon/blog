# 在實機上以 profile mode 量效能：資料保全與量測本身的陷阱

用 `integration_test` 寫量測、以 `flutter drive --profile` 在 Android 實機上跑時讀這一份。截圖驗證畫面的流程在本 skill 的 SKILL.md；這一份管量測跑之前、跑之中、跑之後要守的事。實測的配置是 Samsung SM-S9010（Android 16）、Flutter 3.41、drift（SQLite 在背景 isolate）；其他配置照同樣的檢查自己量。

## 跑之前：資料保全

`flutter drive` 跑完時會把 APP 解除安裝，APP 的資料跟著刪掉；測試通過或失敗都一樣（實測中途停掉 `flutter drive` 的那一次，APP 還在，但不要依賴這一點）。使用者的手機上有真實資料時，下面每一步都要做，做錯的代價是使用者的資料沒了。

1. **備份全部資料庫檔**：`adb shell am force-stop <applicationId>`，再用 `adb exec-out run-as <applicationId> cat databases/<檔名>` 逐一拉回主檔與 `-wal`、`-shm`（WAL 模式時最近的寫入可能還在 `-wal` 裡）。記下每個檔的雜湊。
2. **備份當下產生一份內容清單**：把備份複製一份，用 `sqlite3 -readonly <副本>` 跑一組固定的查詢（主要資料表的主鍵與關鍵欄位、關聯表），存成清單。不要用一般模式的 `sqlite3` 開備份本身：它關檔時會做 checkpoint，把 WAL 併回主檔，備份的雜湊從此對不上。
3. **在手機上也放一份還原檔**：`adb push` 到 `/data/local/tmp/`。之後還原時不必再從電腦傳，電腦上的暫存目錄被清掉時也還有一份。
4. **量測會寫入資料時，先清掉 APP 的資料庫**：不能用使用者的資料庫跑會寫入的量測。刪之前列出要刪的檔，確認還原檔在。
5. **APP 要讀的檔案**（合成資料庫、匯入檔）先 `adb push` 到 `/data/local/tmp/`，再用 `adb shell run-as <applicationId> cp` 複製進 APP 的 `databases/` 或 `files/`。

## 跑之前：手機與主機的狀態

- **螢幕要全程亮著**：螢幕關掉時 APP 進背景；做了「進背景就暫停」的 APP 會照設計停下來，量測就停住、等到逾時。先讀原本的設定 `adb shell settings get global stay_on_while_plugged_in` 並記下，量測期間 `adb shell svc power stayon usb`，量完改回原值（`adb shell settings put global stay_on_while_plugged_in <原值>`）。
- **量測期間不要碰手機**：integration test 會把觸控當成測試輸入（log 印出 `Some possible finders for the widgets at Offset`），點按與捲動可能改變畫面，量到的就不是腳本的操作。開始前請使用者放著手機。
- **主機磁碟**：增量建置 profile 版約再用 1 GB。不要清 Gradle 快取（`~/.gradle/caches`）或專案的 `build/` 來騰空間：它們是每次建置都要用的工作區，清掉之後下一次建置會整個建回來（實測清掉轉換快取騰出 4.2 GB，下一次建置用掉約 4 GB）。空間不夠時請使用者清專案以外的東西。

## 寫量測時：量測本身的陷阱

每一個都讓量測照樣跑完、照樣產出數字，數字卻不是宣稱的那件事。

| 陷阱 | 後果 | 寫法 |
|------|------|------|
| `integration_test` 的 binding 預設不攔截文字輸入 | `tester.enterText` 的字送進手機的輸入法，沒有進 TextField；「打字時的效能」量到的只有其他動作 | 進要打字的頁面之後呼叫 `tester.testTextInput.register()` |
| `testWidgets` 的 `semanticsEnabled` 預設是 true | 每個 frame 多建一次無障礙樹；使用者沒開輔助功能時沒有這筆成本 | `testWidgets(..., semanticsEnabled: false, ...)`；要知道它的影響時，用 `tester.ensureSemantics()` 在同一次執行裡開著再量一次對照 |
| 直接讀一個 `autoDispose` provider，而畫面上沒有元件在監聽它 | 讀到的是剛建立就被丟掉的空值，等待它更新會逾時 | 讓監聽它的元件在畫面上（例如捲動之後把清單跳回頂端），或讓量測自己 `container.listen` 持有它 |
| APP 在背景（模擬 `AppLifecycleState.paused`）時呼叫 `tester.pump()` | 背景時不產生 frame，`pump` 一直等；測試卡住，連「回到前景」那一步都到不了 | 背景期間只用 `Future.delayed` 等真實時間，回前景之後才恢復 `pump` |
| 用 `binding.traceAction` 錄 timeline | 預設的 `flutter drive` 有 DDS 轉接 VM service，APP 連不回自己（`Connection refused`） | `flutter drive --no-dds` |
| 錄 timeline 的那一次 | 錄的本身讓程式變慢 | 錄 timeline 的那一次只拿來拆比例，驗收的數字用沒錄的那一次 |

**每一個動作後面接一條斷言，確認它真的改變了狀態**：打字之後斷言搜尋條件等於打的字，換頁之後斷言路由，寫入之後斷言筆數。斷言失敗就讓量測失敗。**等待逾時的失敗訊息寫出當下的狀態**（條件、輸入框內容、清單長度、頁面資料有沒有讀到），一次就分得出是被量的程式慢還是量測沒做到。

## 寫量測時：量對成本模型

- **資料庫要用正式的執行器**：單元測試常用同一個 isolate 的記憶體資料庫，每條 SQL 沒有跨 isolate 的往返；手機上的背景 isolate 每條 `await` 都是一次往返。批次寫入的效能只在實機或「同樣是背景 isolate 的檔案資料庫」上量才算數（實測：同一段匯入在記憶體資料庫 1,000 本約 1 秒，實機 1 萬本約 9.5 分鐘，改成一次送出之後約 4 秒）。
- **主執行緒卡頓不只看 frame**：長工作期間畫面不一定一直重畫，只收 `FrameTiming` 會漏掉沒有 frame 時的卡頓。加一個每 50 ms 觸發的計時器，量它最晚遲到多少。
- **兩次執行之間同一項數字可以差 30% 左右**：要比較兩種設定時，在同一次執行裡跑對照組，不拿兩次執行的數字直接比。

## 跑完之後：還原

1. 確認 APP 還在不在（`adb shell pm list packages | grep <applicationId>`）；被解除安裝時重裝 debug 版。
2. `adb shell run-as <applicationId>` 底下 `mkdir -p databases`，把還原檔複製回 `databases/`，`chmod 771 databases`、資料庫檔 `chmod 600`。
3. 把還原後的資料庫拉回電腦，用 `sqlite3 -readonly` 跑同一組查詢，跟備份當下的清單逐行比對；相同才算還原完成，在給使用者的回報裡寫出比對結果。
4. 改回螢幕常亮的設定，回報裡寫出原值與改回後讀到的值。
