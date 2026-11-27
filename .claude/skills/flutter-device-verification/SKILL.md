---
name: flutter-device-verification
description: "在 Android 實機與 iOS 模擬器上操作 Flutter APP 並截圖驗證畫面：取得 VM service 位址、用腳本換頁點按捲動、截圖當下記版本、改程式碼後熱重啟並確認、拼圖裁切看圖、逐狀態回填交付紀錄、亮暗字級與導覽方式切換後還原、避免誤點寫入資料、模擬器驗不到的狀態；在實機上以 profile mode 量效能時的資料保全、量測陷阱與還原。觸發：Flutter 截圖、實機驗證、模擬器截圖、熱重啟、重拍、adb、simctl、flutter drive、實機效能量測、integration_test 效能量測。"
license: MIT
metadata:
  portable: true
  version: 1.3.0
  category: testing
---

# Flutter Device Verification

改了 Flutter APP 的畫面之後，在 Android 實機與 iOS 模擬器上把要驗的狀態一個一個開出來、截圖、看圖。`scripts/drive.dart` 經由 VM service 在執行中的 APP 裡求值，完成換頁、點按、返回與輸入，不改 APP 的程式碼，也不靠人手點。

適用：審查的人或使用者要截圖證據；同一組畫面要拍亮暗兩版或多台設備；改了共用元件之後要整組重拍。
在 Android 實機上以 profile mode 量效能（`integration_test` 加 `flutter drive --profile`）時，資料保全（`flutter drive` 結束時會解除安裝 APP 連同資料）、手機與主機的狀態、量測本身的陷阱與還原，讀 `references/profile-measurement.md`。這條路不走下面的〈前置〉與流程（那些是截圖驗證用的，例如只能用 debug 模式啟動），只沿用〈前置〉裡 `adb devices` 列出手機狀態是 `device` 那一項檢查。

不適用：版面與狀態能用 widget 測試或 golden 測試驗的（那是自動測試的範圍，寫測試）；相機掃描、震動、輸入法選字與自動校正這類要人實際操作設備才看得到的行為（請使用者在實機上做，在紀錄寫明是使用者驗的）。螢幕鍵盤打開時的畫面可以拍，做法見 `references/device-pitfalls.md`〈症狀與處置〉。

## 前置

開始流程之前逐項確認：

- `flutter`、`dart` 在 PATH 上；Android 要 `adb`，`adb devices` 列出的手機狀態是 `device`（`unauthorized` 時請使用者在手機上允許 USB 偵錯）（`drive.sh` 先讀環境變數 `ADB`，再找 PATH，再找 `$ANDROID_HOME/platform-tools`；`ANDROID_HOME` 沒設時用 macOS 的預設位置 `~/Library/Android/sdk`，找不到時用 `ADB` 指定），iOS 要 Xcode 的 `xcrun simctl`；拼圖與裁切要 `ffmpeg`；`SHOT_LOG` 要 `shasum`。本 skill 只在 macOS 主機上實測過。
- APP 專案在 git 底下：`SHOT_LOG` 記的版本取自 APP 專案的 git（commit 與工作樹雜湊）。不在 git 底下時，`drive.sh` 把版本記成 `no-git` 並印警告，截圖分不出版本；開拍前先跟使用者確認版本怎麼記。
- `drive.dart` 用 APP 專案的 `.dart_tool/package_config.json` 取得 `vm_service` 套件（Flutter 專案經由 `flutter_test` 的依賴通常已經有）。`grep -c '"vm_service"' <APP 專案根目錄>/.dart_tool/package_config.json` 印出「No such file or directory」時，APP 還沒跑過 `flutter pub get`，先在 APP 專案根目錄跑它再查一次。印出 0 時，先問使用者能不能在 APP 專案加這個開發依賴：`flutter pub add --dev vm_service` 會改 APP 的 `pubspec.yaml` 與 `pubspec.lock`，之後每張截圖的工作樹雜湊都含這個改動。使用者同意才跑，交付紀錄寫出加了這個依賴，收尾時問使用者要不要還原這兩個檔。
- 用 debug 模式啟動（`flutter run` 不加 `--profile`、`--release`）：其他模式沒有求值功能，`drive.dart` 的指令全部失效。
- `drive.dart` 在 APP 的根函式庫（root library：`flutter run` 啟動的那一個，通常是 `lib/main.dart`）裡對 `push`、`back`、`type`、`dpr` 的運算式求值；根函式庫沒有 import Flutter widgets 時，在 `env.sh` 用 `FLUTTER_DRIVE_LIB` 指定一個有 import 的函式庫 uri（例如 `export FLUTTER_DRIVE_LIB=package:<APP 套件名>/app.dart`，套件名是 APP 的 `pubspec.yaml` 的 `name`）。
- `push` 用的是具名路由（`Navigator.pushNamed`）。APP 用宣告式路由（go_router 這類）時，改成點按入口換頁，或在 `drive.dart` 加一個呼叫該路由套件的指令。
- `drive.dart` 從根元素往下前序走訪 element 樹，`push`、`back` 用最後找到的那一個 Navigator。APP 只有一層 Navigator 時，它就是畫面上那一個，`back` 關得掉面板與對話框。APP 有巢狀 Navigator（分頁殼、`CupertinoTabScaffold`、go_router 的 ShellRoute）時，取到的可能是沒有顯示的分頁、或被蓋住的頁面底下那一個 Navigator，`push` 與 `back` 會改到看不見的狀態，截圖跟預期不同，拍攝的人卻看不出原因。這類 APP 不用 `push` 與 `back`，一律 `tap` 畫面上的入口與返回鍵，每一步截圖確認。
- APP 有自己的主題設定（存在 APP 裡的淺色、深色、跟隨系統）時，先確認它設在跟隨系統，切換設備的深色模式才會改變畫面；不是的話，在 APP 裡切換屬於會寫入資料的操作，照 `references/device-pitfalls.md`〈會寫入資料的點按〉做。
- 換頁動畫比 0.8 秒長的 APP（自訂轉場），在 `env.sh`（見「啟動 APP，取得 VM service 位址，寫好 `env.sh`」那一步）加 `export WAIT=<秒數>`。

## 流程

下面的 `<skill 目錄>` 是這份 SKILL.md 所在的目錄；`<APP 專案根目錄>` 是要驗的 Flutter APP 的專案根目錄（有 `pubspec.yaml` 的那一層），使用者沒指定時先問；`<暫存目錄>` 是這次工作專用、APP 專案以外的目錄（agent 的 scratchpad，或用 `mktemp -d` 建一個），pid、log、設備設定的原值與截圖都放在這裡。

同一批要拍兩台設備（Android 實機與 iOS 模擬器）時，每台各開一個子目錄 `<暫存目錄>/<設備名>/`（例如 `android/`、`ios/`），放那台的 `flutter.pid`、`flutter.log`、`env.sh`、`device-original.txt`：下面指令裡這四個檔所在的 `<暫存目錄>`，換成那台的子目錄，每次操作哪一台就 `source` 哪一台的 `env.sh`。`states.md`、`shots.log` 與截圖目錄放在 `<暫存目錄>` 本身，兩台共用。

**1. 啟動 APP，取得 VM service 位址，寫好 `env.sh`。** `flutter run` 不會自己結束，要在背景執行，留下 pid 給之後的熱重啟用：

```bash
cd <APP 專案根目錄> && flutter run -d <設備 ID> --pid-file <暫存目錄>/flutter.pid > <暫存目錄>/flutter.log 2>&1
cd <APP 專案根目錄> && flutter run -d <設備 ID> --dart-define-from-file=<設定檔> --pid-file <暫存目錄>/flutter.pid > <暫存目錄>/flutter.log 2>&1   # APP 平常帶建置設定檔啟動時
```

用 agent 的 shell 工具的背景執行選項跑其中一行；沒有這個選項時，才在行尾加 ` &`。

`<設備 ID>` 是 `flutter devices` 列出的 ID（Android 是 adb 序號，iOS 模擬器是 UDID）。`flutter devices` 只列出已經開機的模擬器：iOS 模擬器先用 `xcrun simctl list devices` 查 UDID，`xcrun simctl boot <UDID>` 開機，`open -a Simulator` 顯示畫面。APP 平常怎麼啟動（要不要帶設定檔、帶哪一個），看 APP 的 README、`Makefile` 或 `.vscode/launch.json` 的啟動參數；都沒有時問使用者。第一次建置可能要幾分鐘，等 log 出現 VM service 那一行或出現錯誤。下面的迴圈每 5 秒查一次、最多 18 次（90 秒），停下時印出停下的原因；agent 的 shell 工具有逾時限制時，把逾時設得比 90 秒長：

```bash
L=<暫存目錄>/flutter.log
for i in $(seq 18); do grep -q 'is available at' $L && echo ready && break; grep -qE 'FAILURE|Lost connection|No supported devices|^Error' $L && echo error && break; [ "$i" = 18 ] && echo waiting; sleep 5; done
grep -m1 -o 'http://127.0.0.1:[0-9]*/[^ ]*=/' $L | sed 's#^http#ws#; s#$#ws#'   # 印出 ws://127.0.0.1:<port>/<token>=/ws
```

印出 `ready` 時往下寫 `env.sh`；印出 `error` 時，讀 `flutter.log` 最後幾行，再查 `references/device-pitfalls.md`〈症狀與處置〉；印出 `waiting` 時建置還沒完成，再跑一次這一段。拿到 ws 位址之後寫 `env.sh`：agent 的 shell 工具每次呼叫是新的 shell，變數留不到下一次，所以之後的每一步都先 `source` 這個檔。`SHOT` 不寫進去（見「操作與截圖」那一步）：

```bash
cat > <暫存目錄>/env.sh <<'EOF'
export FLUTTER_APP_DIR=<APP 專案根目錄>
export FLUTTER_VM_WS=<上面印出的 ws 位址>
export ANDROID_SERIAL=<adb 序號>          # iOS 模擬器改寫 export IOS_UDID=<UDID>，不要兩個都設（都設時截 Android）
# export ADB=<adb 的完整路徑>             # adb 不在 PATH、也不在 macOS 預設位置時才寫
export SHOT_LOG=<暫存目錄>/shots.log
# export FLUTTER_DRIVE_LIB=package:<APP 套件名>/app.dart   # 根函式庫沒有 import Flutter widgets 時才寫（見〈前置〉）
D=<skill 目錄>/scripts/drive.sh           # drive.sh 的完整路徑，它不在 PATH 上
S=<暫存目錄>/shots                        # 放截圖的目錄
EOF
source <暫存目錄>/env.sh; mkdir -p "$S"
```

每次重新 `flutter run`，位址都會變，要改寫 `env.sh` 裡 `FLUTTER_VM_WS` 那一行，否則之後每次 `source` 都載回舊位址。

**2. 列出要拍的狀態，記下要還原的設備設定。** 開拍之前，把要拍的狀態寫進 `<暫存目錄>/states.md`，一行一個狀態（從 `ux-design-evaluation` 的畫面狀態矩陣每一列取，或照使用者指定；契約要求在最大字級驗收的狀態，另列一行最大字級）。表頭與一行的例子：

```text
| 設備 | 畫面 | 狀態 | 亮暗 | 字級 | 導覽 | 截圖路徑 | 結果 |
| android | 書庫 | 多選模式未選定 | 暗 | 1.0 | 三鍵 | shots/android-書庫-多選未選定-暗-1.0-三鍵.png | 待拍 |
```

截圖路徑照 `<設備>-<畫面>-<狀態>-<亮暗>-<字級>-<導覽>.png` 取名，一行一個路徑，iOS 的導覽欄填「—」：同一個路徑只屬於一行，`SHOT` 覆寫時蓋掉的只是這一行自己的舊圖。結果欄在「交付與收尾」那一步回填。貼著螢幕下緣的畫面在三鍵導覽與手勢導覽下各列一行（`component-contract-design` 的 `references/mobile-platform-notes.md`〈驗收的證據〉）。這份清單是「交付與收尾」那一步回填的分母。這一批要切換深色模式、字級或 Android 導覽方式時，先 `source` `env.sh`，再讀原值，寫進 `<暫存目錄>/device-original.txt`（指令在 `references/device-pitfalls.md`〈設備設定的還原〉）。每一批開拍前都截一張顯示資料筆數的畫面（`$D shot $S/count-before.png`），把計數寫在 `states.md` 下方，「還原設備設定並確認」那一步拿它比對：誤點寫入鍵多半發生在以為自己沒點寫入鍵的時候，所以不看這一批打不打算點。契約裡有寫「未量」的欄位時（例如下方面板的返回鍵行為），每一個欄位在 `states.md` 列一行，拍的時候量。

**3. 操作與截圖。** `scripts/drive.sh` 讀 `env.sh` 裡的 `FLUTTER_APP_DIR`、`FLUTTER_VM_WS`、`ANDROID_SERIAL` 或 `IOS_UDID`、`ADB`。`SHOT` 不寫進 `env.sh`，只寫在單一指令的前面：export 之後每個動作都會截圖、覆寫同一張圖。`SHOT_LOG` 寫在 `env.sh` 裡：`drive.sh` 每截成功一張，就在這個檔附加一行拍攝的日期與時間、截圖路徑，以及拍攝當下 APP 的 commit 和工作樹雜湊（未提交的改動與未追蹤檔的內容）；做「交付與收尾」那一步時，從這裡抄版本與時間。`drive.sh` 算雜湊時讀的是磁碟上的程式，不是 APP 已經載入的程式：存了檔還沒熱重啟（hot restart）就拍，雜湊是新值而畫面是舊的，所以改了程式碼之後照「改程式碼之後熱重啟」那一步確認熱重啟成功，再拍。`D` 代表這支腳本的完整路徑，它不在 PATH 上；`S` 是放截圖的目錄。第一次點按之前，先讀 `references/device-pitfalls.md`〈會寫入資料的點按〉：

```bash
source <暫存目錄>/env.sh            # 每次呼叫都先 source
$D dpr                              # 印出裝置像素比（例如 3.0），換算座標用
$D shot $S/pre-tap.png              # 點會寫入資料的鍵之前，先截一張確認那個座標現在是哪一顆鍵
$D push /browse                     # 換到具名路由；/browse 換成 APP 註冊的路由名（MaterialApp 的 routes 或 onGenerateRoute 裡的名字）
$D push /detail 42                  # 第二個引數當成 arguments 傳給路由，型別是 String；路由要的不是 String 時，改從入口 tap 進去
SHOT=$S/browse.png $D tap 72 213    # 在邏輯座標 (72, 213) 點一下；動作後等 0.8 秒，截圖前再等 1.2 秒
$D longpress 72 213                 # 按住 700ms；放開之後再等 0.8 秒
$D drag 200 700 200 250             # 從 (200, 700) 拖到 (200, 250)：往上拖，清單往下捲；重複拖到相鄰兩張截圖的清單內容相同，就是捲到底
$D shot $S/sheet.png                # 只截圖：面板或對話框開著時用這個
$D back                             # 關掉最上層的頁面、面板或對話框（maybePop）；這不是系統返回鍵，驗系統返回鍵的行為時改送 "${ADB:-adb}" -s "$ANDROID_SERIAL" shell input keyevent KEYCODE_BACK
$D type '<文字>'                    # 取代目前有焦點的輸入框的內容；先 tap 輸入框讓它取得焦點；文字含空白時加引號
$D wake                             # 只送喚醒鍵（Android）
```

座標是邏輯座標：截圖的像素座標除以 `$D dpr` 印出的裝置像素比。座標從截圖上量，不用猜：看圖的工具可能已經把圖縮小，讀到的位置不是原圖像素，所以先在原圖上畫格線再讀，例如 `ffmpeg -i $S/a.png -vf "drawgrid=w=100:h=100:t=2:c=red@0.6" $S/a-grid.png`（每格 100 像素），或用「看圖」那一步的裁切指令把候選位置周圍裁出來確認。換算之後再點。版面一變（多了一列、字級改了），座標就要重量。

**4. 改程式碼之後熱重啟。** 對 `flutter run` 的程序送 USR2 訊號，它收到之後熱重啟（USR1 是熱重載）。熱重啟要一點時間才完成（iPhone 16 模擬器、Flutter 3.41 實測約 3 秒），所以送之前記下 `Restarted application` 與編譯錯誤（`<檔案>:<行>:<欄>: Error:`）的行數，送之後每秒查一次、最多查 10 秒（實測值的三倍多，較大的 APP 熱重啟要比較久），`Restarted application` 的行數增加才算成功：

```bash
L=<暫存目錄>/flutter.log; n=$(grep -c 'Restarted application' $L); e=$(grep -c ': Error:' $L); kill -USR2 $(cat <暫存目錄>/flutter.pid)
for i in $(seq 10); do [ "$(grep -c 'Restarted application' $L)" -gt "$n" ] && echo restarted && break; [ "$(grep -c ': Error:' $L)" -gt "$e" ] && echo compile-error && break; sleep 1; done
```

印出 `compile-error` 時，讀 `flutter.log` 最後的 `Error:` 那幾行，修好程式再送一次；兩個都沒印出時，查 `references/device-pitfalls.md`〈症狀與處置〉「改了程式碼、熱重啟之後畫面沒變」那一列。下面這幾種改動熱重啟不會反映到畫面上：改了原生碼或 `android/`、`ios/` 底下的設定；`pubspec.yaml` 加或拿掉含原生端的套件；改了 `--dart-define` 的值或建置設定檔；拿掉了系統列樣式的欄位或整個宣告（改值會反映，拿掉的欄位不會被重設）。前兩種改的是工作樹裡的檔，雜湊會變；`--dart-define` 的值不在工作樹裡，被 gitignore 的設定檔也不算進雜湊，這兩種雜湊不會變，只能靠下面那一行改動紀錄分出前後。這幾種改完結束 `flutter run`（`kill $(cat <暫存目錄>/flutter.pid)`），從「啟動 APP」那一步重來，改寫 `env.sh` 的位址。熱重啟後 APP 回到首頁，從首頁重新操作到要拍的狀態。

每次改完程式碼、熱重啟或重新執行成功之後，照 `component-contract-design` 的 `references/mobile-platform-notes.md`〈驗收的證據〉決定要重拍哪些行：改到系統列宣告或共用層時是全部的行，只改了單一畫面內部的版面或文字時是那一個畫面的行。然後在 `states.md` 下方記一行，格式是：

```text
<date '+%F %T' 的輸出> | <改了哪些檔或哪一項設定> | 受影響的行：<全部，或截圖路徑…>
```

並把受影響的那幾行的結果欄標成待重拍。

**5. 看圖。** 一組截圖（至少兩張）用 `<skill 目錄>/scripts/montage.sh <輸出> <截圖...>` 拼成總覽（預設每列 7 張、每張縮成 270×585；平板或橫式截圖改環境變數 `COLS`、`W`、`H`，`W:H` 照截圖的寬高比，例如 `COLS=4 W=585 H=270 <skill 目錄>/scripts/montage.sh <輸出> <截圖...>`），先看整體有沒有跑版、狀態對不對：把每張圖對照 `states.md` 那一行要的狀態，以及設計稿或元件契約（有的話）寫的樣子。總覽縮得很小，導覽列、1px 線、按鍵下緣這類細節，回原圖用 `ffmpeg -i <原圖> -vf crop=<寬>:<高>:<x>:<y> <輸出>` 裁出那一塊放大看。貼著螢幕下緣的狀態，每一張都裁出導覽列那一塊，看圖示看不看得清楚、有沒有半透明底、按鍵有沒有蓋住文字：白底面板上的淺色導覽列圖示，在總覽圖上看不出來。

**6. 還原設備設定並確認。** 這一批改過的每一項設定都還原：改回 `device-original.txt` 裡的原值，再用讀原值的同一條指令讀一次，結果要等於原值。改了而檔裡沒有原值的，停下來問使用者原值，不猜。這一批沒改的設定不動。再截一次「列出要拍的狀態」那一步拍過的計數畫面（`$D shot $S/count-after.png`），計數跟開拍前不同時，照 `references/device-pitfalls.md`〈會寫入資料的點按〉的誤寫處置做。

**7. 交付與收尾。** 把 `states.md` 逐行回填，交給審查的人（使用者，或派來審畫面的 agent），寫在回覆或審查的人要讀的工作紀錄裡。每一行標成下面一種：
- **已拍**：截圖路徑、`shots.log` 裡那張圖的 commit 與工作樹雜湊（同一路徑重拍過時取最後一行）、看圖結果（符合，或不符的位置；裁切放大看過的位置也寫）。`shots.log` 那一行的時間早於 `states.md` 下方最後一筆列了這個截圖路徑的改動時，不算已拍，標成「未拍（待重拍：<改了什麼>）」。
- **未驗（模擬器：<成因>）**：只用在 iOS 模擬器沒有相機、或接著實體鍵盤而關不掉的時候。
- **未拍（<原因>）**：其餘沒拍的，寫出原因。
- **使用者驗（實機）**：由使用者在實機上操作確認的。

另外寫出設備、Android 或 iOS 的系統版本、APP 的 targetSdk、系統的亮暗、字級與 Android 導覽方式，「還原設備設定並確認」那一步每一項設定的原值與還原後讀到的值，開拍前與收尾時那兩張計數畫面的路徑與計數，以及前置加過 `vm_service` 依賴時寫出加了它。版本的讀法：Android 系統版本 `"${ADB:-adb}" -s "$ANDROID_SERIAL" shell getprop ro.build.version.release`，APP 的 targetSdk `"${ADB:-adb}" -s "$ANDROID_SERIAL" shell dumpsys package <applicationId> | grep -o 'targetSdk=[0-9]*'`（`applicationId` 在 APP 的 `android/app/build.gradle` 或 `build.gradle.kts`），iOS 模擬器的系統版本看 `xcrun simctl list devices booted` 的 `-- iOS x.y --` 那一行。

交付的紀錄寫完、這一批不再拍之後，結束 APP：`kill $(cat <暫存目錄>/flutter.pid)`。前置加過 `vm_service` 依賴時，把 `git -C <APP 專案根目錄> diff -- pubspec.yaml pubspec.lock` 給使用者，問要不要還原這兩個檔。

## 不照做會出的錯

| 規則 | 不照做的後果 |
|------|------------|
| 每個動作之後等換頁動畫跑完（`drive.sh` 等 0.8 秒；Flutter 3.41 預設換頁 Material 450ms、Cupertino 500ms，自訂轉場較長時設 `WAIT`） | 實測（Android 16 實機、iPhone 16 模擬器，Flutter 3.41）動作送得太密時，之後的 push 與 back 不再換頁；已經這樣時熱重啟，從首頁重新操作 |
| 截圖用 `drive.sh shot`，不用「點一下畫面角落」觸發 | 面板或對話框開著時，那一下點按落在暗幕（modal barrier）上，APP 把要拍的面板關掉 |
| 點會寫入資料的鍵之前，先截圖確認那個座標是哪一顆鍵 | 同一個座標在不同狀態是不同的鍵，關面板時點的座標上可能是「加入」或「刪除」鍵；誤寫之後的截圖全部要重拍 |
| 改到系統列宣告或共用層之後，照「改程式碼之後熱重啟」那一步在 `states.md` 標出待重拍的行再重拍（重拍範圍以 `component-contract-design` 的 `references/mobile-platform-notes.md`〈驗收的證據〉為準） | 改動前拍的截圖裡是已經不存在的狀態；審查的人拿它們判定，結論不成立 |
| 每張截圖在拍攝當下記下程式版本（`SHOT_LOG`），交給審查的人時寫明哪些是哪一版拍的 | 審查的人分不出哪些截圖還有效，只能要求全部重拍；等到交付時才一次查版本的話，每張圖拿到的都是交付當下的同一個值，熱重啟前與熱重啟後拍的圖分不出來 |
| `states.md` 的每一行都回填成已拍、未驗（模擬器：成因）、未拍（原因）或使用者驗 | 審查的人把沒拍到的狀態讀成沒問題；拍攝的人把漏拍的狀態標成平台限制 |
| Android 拍攝期間每一步送喚醒鍵（`drive.sh` 已經做），螢幕鎖上時請使用者解鎖 | 腳本操作不算系統觸控，螢幕照樣逾時關閉；之後的截圖全黑，實測（Samsung SM-S9010、Android 16）debug 連線也跟著中斷 |

症狀對處置的完整表（截圖全黑、連線中斷、type 求值失敗或寫錯輸入框、熱重啟之後畫面沒變、建置失敗等）在 `references/device-pitfalls.md`〈症狀與處置〉。

## 相關 skill

這兩支 skill 跟本 skill 放在同一個 skills 目錄底下（`<skill 目錄>/../<skill 名>/`）。

- `component-contract-design` skill 的 `references/mobile-platform-notes.md`：系統列樣式、命中區、行高這類在截圖上才看得出的問題，契約裡該怎麼寫。
- `ux-design-evaluation` skill 的 `references/screen-state-matrix.md`：要拍哪些狀態，從畫面狀態矩陣的每一列取。

版本紀錄在同目錄的 `CHANGELOG.md`。
