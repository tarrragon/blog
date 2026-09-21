---
title: "adb 遠端診斷 Android 實機：狀態查詢讀到的是元件對自己的描述，畫面與 log 是它實際產生的輸出"
slug: "adb-remote-android-diagnosis"
date: 2026-09-21
description: "機器不在手邊而要判斷畫面上是誰在擋、擷圖抓回來打不開、或 logcat 撈不到按下去那一刻時回來讀"
tags: ["adb", "android", "debugging", "logcat", "pos"]
---

本篇的情境來自一次實際排查：同一個 APK 用 `adb install` 裝得起來，換成由 App 自行下載再觸發安裝就被一個對話框擋住，而機器在另一個地點、沒有人看得到它的螢幕。下面每一條指令都是在這個限制下取值用的。範圍從 adb 已經接上那一刻開始——無線連線本身要先在開發者選項的無線偵錯頁面取得位址與埠號，Android 11 之後首次連線還要先 `adb pair`，那一段在[Android 無線調試連接指南](/other/android_wireless_debug/)。

機器交得出來的資料分兩類，而它們的來源不同：某個系統元件對自己狀態的描述，由回答問題的那個元件產生；裝置實際產生的輸出（畫面上的像素、log 裡的行），由做事的那些元件產生。這個差別在最後一節決定一組查詢全部回報「正常」而現象仍在的時候該問誰。

在那之前還有三件事要先決定：指令送到哪一台機器、它是讀還是寫、以及輸出用哪一條通道送回來。前兩件決定指令打不打得中目標、跑完之後那台機器還是不是原來的樣子；第三件決定送回來的那串位元組是不是原來的樣子。

## 指定裝置的參數屬於 adb，不屬於遠端 shell

adb 的一行指令分成兩段責任：`adb` 自己要讀的參數，以及要送去遠端執行的字串。分界就是子命令本身，所以選擇裝置的參數要寫在 `shell` 之前。

```bash
adb devices -l                          # -l 多印 product / model / transport_id
adb -s <serial> shell <command>
adb -t <transport_id> shell <command>   # transport_id 較短、同一次連線內有效
```

`adb shell -s <serial> <command>` 這種寫法裡的 `-s`，落在分界的遠端那一側，而 `adb shell` 自己的選項解析器並不接受它——它回報 `adb shell: illegal option -- s`，遠端一個字都沒有執行。這個訊息指得出問題在選項上。

沒有指定 transport 的時候看到的是另一則訊息：adb 先解析要送到哪一台，在多台在線時當場失敗、回報 `adb: more than one device/emulator`，根本沒走到 `adb shell` 的解析那一步。同一個寫錯的指令因此有兩種回報，而指向參數位置的那一則只在單機在線時看得到。

「多台」這個判斷也比看起來寬鬆。同一台無線機器可能同時以 IP 位址與 mDNS 名稱兩個 transport 在線，`adb devices` 因此列出兩列而背後是同一台實體機器。數量對不上手邊的機器數時，`-l` 印的 product / model 分不出來，同一批機器的那幾個字串本來就一樣；分得出來的是硬體序號，逐個 transport 問一次 `getprop ro.serialno`，回同一個值的那幾列是同一台。

機種身分由幾個 `ro.*` property 合成，而序號與機種是兩件事：同一批機器共用機種字串，各有各的序號。

```bash
for serial in $(adb devices | awk 'NR>1 && $2=="device" {print $1}'); do
  model=$(adb -s "$serial" shell getprop ro.product.model | tr -d '\r')
  brand=$(adb -s "$serial" shell getprop ro.product.brand | tr -d '\r')
  sdk=$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')
  hw=$(adb -s "$serial" shell getprop ro.serialno | tr -d '\r')
  echo "$serial | $brand $model (API $sdk) | $hw"
done
```

`tr -d '\r'` 處理的是行尾。遠端 shell 的輸出會不會帶 `\r`，取決於 adb 送這段輸出回來的時候有沒有配置 **pty**（pseudo-terminal，虛擬終端機）——那是核心提供的一對裝置，一端交給遠端執行的程式、一端交給呼叫它的人，讓程式以為自己接在真實終端機上；於是核心會對經過的位元組做終端機該做的處理，把換行補成歸位加換行是其中一項。配置了的話每個換行都是 CRLF，而字串比對與拼接會在看不見的位置失敗——`"$model" = "<型號字串>"` 這種比較永遠不成立，印出來卻看不出差別。`tr -d '\r'` 在不需要的時候不改變結果，所以它在這個位置的成本是零。同一個行尾處理決定擷圖抓不抓得回完好的檔案。

## 二進位輸出走 exec-out，因為 pty 會改寫換行

把遠端機器的畫面抓回本機是一行：

```bash
adb -s <serial> exec-out screencap -p > screen.png
```

`screencap -p` 在裝置上把當前畫面編碼成 PNG 寫到標準輸出，adb 負責把這串位元組送回本機，而送回來的路徑有兩種處理方式。`exec-out` 不對位元組做行尾轉換；`shell` 在配置了 pty 的時候，pty 的那個終端機處理會把每一個 `0x0A` 換成 `0x0D 0x0A`。PNG 裡的 `0x0A` 是資料、不是行尾，被換掉的每一處都讓檔案的位元組數與內容一起偏移。

這個差別可以用一段已知的位元組當場看出來：

```bash
adb -s <serial> exec-out "printf 'a\nb\n'" | xxd
# 610a 620a

adb -s <serial> shell -tt "printf 'a\nb\n'" < /dev/null | xxd
# 610d 0a62 0d0a
```

`-tt` 的作用是強制配置 pty（單一個 `-t` 在標準輸入不是終端機時會拒絕配置並印出說明）。不帶這兩個旗標的時候，`adb shell` 會不會配置 pty 取決於三件事：adb 版本、裝置端支不支援 shell protocol v2（`adb features` 列不列出 `shell_v2`），以及有沒有帶命令參數——帶了命令的不配置，不帶命令的互動模式才配置。這條規則的成立範圍是「裝置端有 shell protocol v2、而且沒帶 `-t` / `-tt`」，沒有 v2 的舊組合不適用。adb 版本與 shell protocol v2 這兩項都不在指令字面上。所以 `adb shell screencap -p > screen.png` 這個常見的寫法在較新的組合下抓得回完好的檔案、在沒有 shell protocol v2 的舊組合下抓回一個大了幾百個位元組的壞檔，兩種結果都沒有任何錯誤訊息。選 `exec-out` 的理由因此比「shell 會壞」更強一階：它把行尾這件事從版本組合裡拿出來。

代價在另一個軸上。`exec-out` 把遠端的標準錯誤併進同一條流，`shell`（在有 shell protocol v2 時）不併：

```bash
adb -s <serial> exec-out "printf 'OUT\n'; printf 'ERR\n' >&2" | xxd
# 4f55 540a 4552 520a        OUT.ERR.

adb -s <serial> shell "printf 'OUT\n'; printf 'ERR\n' >&2" | xxd
# 4f55 540a                  OUT.
```

所以遠端那一側只要吐出一行警告，它就排在 PNG 的前面進了檔案。這在取二進位輸出時是真實的風險，而它的徵兆與行尾被改寫**完全一樣**：`file` 回 `data`、本機的標準錯誤一個字都沒有、檔案比預期大。

轉換過的檔案不會發出任何錯誤，而檔案類型分得出三種結果：

```bash
file screen.png
# 完好：PNG image data, <寬> x <高>, 8-bit/color RGBA, non-interlaced
# 開頭被塞了別的內容（行尾改寫，或遠端的錯誤訊息併進來）：data
# 一個位元組都沒收到：empty
```

`data` 有兩種來歷而徵兆相同，分辨的方式是把檔案開頭印出來：`xxd -l 16 screen.png`。完好的 PNG 以 `8950 4e47 0d0a 1a0a` 起頭；行尾被改寫的簽章自己就歪了（`8950 4e47 0d0d 0a1a`）；被錯誤訊息塞住的開頭是一段讀得懂的文字。

行尾被改寫的檔案認得出來，理由在 PNG 的八位元組簽章裡本來就含 `0x0A`——轉換過的檔案連簽章都對不上，`file` 於是退回最一般的 `data`。同一批畫面下，它的大小也會比完好的版本大，多出來的位元組數正是被轉換掉的 `0x0A` 個數。`empty` 是另一回事，顯示器編號給錯是它最常見的來歷。

`exec-out` 不可用的舊環境走兩段式。裝置端帶檔名參數時 `screencap` 不寫標準輸出，所以這條路徑上沒有行尾問題；回傳由 `pull` 負責，而 `pull` 傳的是檔案、不做行尾處理，也不會把錯誤訊息併進去。前提是 `pull` 讀得到那個路徑——它與 `adb shell` 的可讀範圍不一樣，`/sdcard` 底下兩者都讀得到，系統分割區底下 `shell` 讀得到而 `pull` 可能回 `Permission denied`。代價是裝置上多一個不會自己消失的檔案，而下一次擷圖看不出它是新的還是舊的：

```bash
adb -s <serial> shell screencap -p /sdcard/screen.png
adb -s <serial> pull /sdcard/screen.png ./device-screen.png
adb -s <serial> shell rm /sdcard/screen.png
```

錄影是同一個形狀，裝置端先寫檔、本機再拉回來：

```bash
adb -s <serial> shell screenrecord --time-limit <秒數> /sdcard/demo.mp4
adb -s <serial> pull /sdcard/demo.mp4 ./
```

錄影的時間上限與 logcat 的緩衝區是相反的形狀：緩衝區的上限要自己調大，錄影的上限是工具寫死的天花板。手上這一版是多少，`adb -s <serial> shell screenrecord --help` 會連同預設值一起印出來。

## 畫面上寫了什麼與畫面由誰畫的是兩個問題

擷圖回答畫面上寫了什麼，畫面由誰畫的要另外問一條：

```bash
adb -s <serial> shell dumpsys window | grep -iE "mCurrentFocus|mFocusedApp"
```

回傳直接帶套件名與 Activity 名，例如安裝確認畫面會顯示系統安裝器的套件與它的 Activity。多螢幕的機器每個顯示器各印一組，而沒有任何視窗取得焦點的那些顯示器，兩個欄位的值都是字面的 `null`。所以不能預設第一行就是有焦點的那一組，兩個欄位都是 `null` 的那幾組要先跳過。

兩條合起來才定位得到一個對話框的歸屬：元件名說出它屬於哪個套件，畫面文字說出它問了什麼。

焦點落在副顯示器上的時候，`exec-out screencap -p` 那一條抓的仍然是主顯示器——它不帶顯示器參數，而 POS 機的客顯正是對話框會出現的地方之一。補上 `-d` 可以指定，但**編號要取自 SurfaceFlinger，不是 `dumpsys window`**：

```bash
adb -s <serial> shell dumpsys display | grep mViewports     # 兩套編號的對應在這一行
adb -s <serial> exec-out screencap -p -d <對應的編號> > screen.png
```

`dumpsys SurfaceFlinger --display-id` 也印得出 `screencap` 要的那組編號，但它不說哪一個對應到 `dumpsys window` 的哪個 `mDisplayId`——兩個顯示器以上的機器只能猜，而猜錯的回報是零位元組加成功退出。`dumpsys display` 的 `mViewports` 那一行把兩邊寫在一起（`displayId=` 與 `uniqueId='local:<編號>'`），對應關係在那裡讀得出來。

兩個編號空間不同而且不相容：`dumpsys window` 的 `mDisplayId` 與 SurfaceFlinger 的顯示器編號取值範圍不一樣，而 `screencap -d` 只收 SurfaceFlinger 那一組。編號一律以 `dumpsys SurfaceFlinger --display-id` 的輸出為準，不靠長相辨識。把 `mDisplayId` 餵給 `screencap -d`，它回傳成功、標準錯誤一個字都沒有、檔案零位元組——這是 `file` 回報 `empty` 的來歷。`screencap --help` 自己就寫著編號要去 SurfaceFlinger 查。

## logcat 的參數決定按下去那一刻留不留得住

logcat 讀的是裝置上的環狀緩衝區，寫滿之後從頭覆蓋。可用的時間窗因此由緩衝區的兩端界定：清空劃下起點、倒出劃下終點，中間那一段是重現問題的時候裝置自己寫進去的。緩衝區本身就是收集器，不需要一個在本機持續執行的程序陪著它。

```bash
adb -s <serial> logcat -G 16M                        # 放大緩衝區
adb -s <serial> logcat -c                            # 清空，時間窗的起點
adb -s <serial> logcat -d -v threadtime > install.log  # 倒出，時間窗的終點
adb -s <serial> logcat -g                            # 查目前各緩衝區的大小
```

這幾個參數各自解一個問題：

| 參數            | 解的問題                                                              |
| --------------- | --------------------------------------------------------------------- |
| `-G 16M`        | 放大緩衝區，而 `16M` 是起點不是答案——實際要多大對著 `-g` 印出的現況調 |
| `-c`            | 清空，讓緩衝區裡只剩這次重現的內容                                    |
| `-v threadtime` | 每行帶 PID / TID 與精確時間戳                                         |
| `-d`            | 把現有內容一次倒出來就結束，不停在前景等                              |
| `-g`            | 每個緩衝區各印一行，設完回頭跑一次看 `-G` 涵蓋了哪幾個                |

放大的理由在於裝置類型：POS 機、車機這類機器的常駐服務多，重現問題的過程還沒結束，緩衝區就可能把最早那幾行覆蓋掉，而判斷是誰擋下一個動作時，關鍵行往往正是按下去之前的那幾行。

`-v threadtime` 的 PID 直接指出發出這一行的 process。tag 由各元件自行填寫、跨元件會重複，所以只憑 tag 做對應得到的是推測。時間戳則讓篩選多一個維度——欄位順序是日期、時間、PID、TID、層級、tag，時間排在第二欄且是 `HH:MM:SS.mmm` 這種零填補的定寬格式，所以時間範圍可以直接用字串比較篩。

下面兩條在本機跑、各自獨立，看 log 被哪個 tag 佔滿就挑一條：

```bash
grep -vE "<佔多數的服務 tag>" install.log | tail -<行數>
awk '$2 >= "16:26:00.000" && $2 <= "16:27:00.000"' install.log \
  | grep -viE "adbd|<該機常駐服務的 tag>"
```

時間值要寫足到毫秒的定寬形式，因為那是字串比較：寫成 `16:26` 不會報錯，只會篩出數量不對的結果。兩側都要寫也有理由——logcat 會插入 `--------- beginning of main` 這類分隔行，它的第二欄是 `beginning`，字串序上大於任何時間值，只寫下界會把它放進來。

行數佔多數的 tag 是哪一個，要先掃一遍未過濾的 log 才知道：

```bash
awk '{print $6}' install.log | sort | uniq -c | sort -rn | head
```

第六欄大多數時候是 tag，而短 tag 會讓這個位置偏掉：logcat 把 tag 欄補寬到八個字元，短於八個字元的 tag 後面那個冒號因此被推成獨立的一欄，於是長 tag 在第六欄讀到的是 `WifiVendorHal:`（帶冒號）而短 tag 讀到的是 `adbd`（不帶）。統計的結果貼回 `awk` 做精確比對之前，先確認手上那個值有沒有尾冒號。

macOS 上另有一個會安靜失敗的做法。`timeout 300 adb logcat > install.log` 在 macOS 留下的是一個 0 bytes 的 `install.log`——`command not found: timeout` 走的是標準錯誤、沒有進那個重導檔，所以事後只看檔案的人看到的是「跑過了但什麼都沒收到」。`timeout` 屬於 GNU coreutils，macOS 預設不帶它（裝了 coreutils 之後名字是 `gtimeout`）。而緩衝區的兩端已經界定了時間窗，本機那個計時程序從一開始就沒有它要做的事。

## 狀態查詢的輸出完整而語法正確，回答的卻常是沒問的那個問題

下面這幾條問的是各子系統對外宣告的狀態，不改變任何設定。`dumpsys <服務>` 並不是一個統一的查詢介面——它把問題轉給那個服務自己的 dump 實作，所以 `dumpsys window`、`dumpsys user`、`dumpsys device_policy` 的回答分別由三個不同的元件產生，格式與詳略各自決定。這件事在最後一節會再出現一次。

服務不存在的時候這條路徑也不報錯：`dumpsys` 對查無此服務回一行 `Can't find service: <名字>` 並以成功退出，而那一行過不了後面任何一條 `grep`，讀者看到的是零行輸出。廠商客製的機器拿掉某個服務是常見的事，所以零行要先用 `dumpsys -l | grep <服務>` 確認服務在不在，再決定它是「沒有管控」還是「沒有人回答」。

`appops`（App Ops）是 Android 在權限之外的另一層閘門，逐項操作計帳——每一組（套件、操作）各自落在一個 mode 上，所以 `appops get` 讀回來的是一個值，不是一個是非。

```bash
adb -s <serial> shell pm list packages | grep -i <keyword>          # 先拿到套件名
adb -s <serial> shell appops get <package> REQUEST_INSTALL_PACKAGES
adb -s <serial> shell dumpsys device_policy | grep -iE "owner|admin|restriction" -A<行數>
adb -s <serial> shell dumpsys user | grep -i restriction -A<行數>
adb -s <serial> shell settings list secure | grep -i <key>
adb -s <serial> shell settings get secure <key>
adb -s <serial> shell pm resolve-activity -a android.settings.MANAGE_UNKNOWN_APP_SOURCES
adb -s <serial> shell dumpsys package <package> | grep -iE "versionCode|versionName|codePath|^Packages:|Hidden system packages:"
adb -s <serial> shell ls -l /storage/emulated/0/Android/data/<package>/
```

| 指令                    | 回答的問題                                                                                      |
| ----------------------- | ----------------------------------------------------------------------------------------------- |
| `pm list packages`      | 某個關鍵字對應到哪些已安裝套件                                                                  |
| `appops get`            | 這個套件的某個操作落在哪個 mode；從沒設定過的印 `No operations.` 加一行 `Default mode: default` |
| `dumpsys device_policy` | 裝置有沒有 device owner 或 profile owner                                                        |
| `dumpsys user`          | 當前使用者的 `Effective restrictions` 是什麼                                                    |
| `settings list/get`     | 某個系統設定在某個 namespace 裡的值                                                             |
| `pm resolve-activity`   | 某個 action 由哪個 Activity 承接、那個設定頁存不存在                                            |
| `dumpsys package`       | 某個套件的版本與安裝路徑                                                                        |
| `ls -l`                 | 這個套件的私有目錄底下有沒有那個 APK、時間戳是不是這一次下載的                                  |

四條的輸出各有一個容易讀反的地方，而它們共用同一個形狀：輸出完整、語法正確，回答的卻是沒問的那個問題。

**`dumpsys user` 的限制分屬不同的使用者。** 要讀的是目標使用者底下的 `Effective restrictions`，而 `Device properties` 那一段的 `Guest restrictions` 是 guest 這個使用者型別被建立時會套上的預設清單，與當前使用者無關。同一條 grep 還會撈到 `mDefaultRestrictions`（使用者型別的定義）與 `Device policy global restrictions`，它們同樣不是當前使用者的有效值。判別的依據是它落在哪個標題底下：落在某個 `UserInfo` 區塊裡的屬於那個使用者，落在 `Device properties` 或使用者型別定義裡的是型別預設值。它裡面本來就列著 `no_install_unknown_sources`——一台完全沒有加過限制的機器，`grep -i restriction` 照樣把這一行撈出來。查安裝被擋的人看到這一行會停下來，而它跟現象無關。

**`appops` 的 mode 是一組固定的值**（`allow` / `ignore` / `deny` / `default`，位置這類權限另有 `foreground`），讀到的字要對回這組值。`ignore` 與 `deny` 都讓呼叫拿不到值，差別在 `deny` 回報失敗而 `ignore` 靜默地回空值。

**`settings` 分成 global / secure / system 三個 namespace**，一個鍵通常只在其中一個裡面有值。跨 Android 版本搬過家的鍵會在舊的 namespace 留下一列值是 `null` 的殘餘，所以 `null` 蓋住的是三種情形：查錯 namespace、這台機器上沒有這個設定、以及這個 namespace 留著一列空的。`settings list <ns> | grep <key>` 命中不等於值在這裡——三個 namespace 都 `get` 過一輪、確認只有一個回非 `null`，才有資格說某個設定查到了或查不到。

**`dumpsys package` 對更新過的系統 App 回兩組值。** 出廠那一版留在 `/system/app` 底下，更新後的那一版在 `/data/app`，兩組各自帶自己的 `versionCode` 與 `versionName`，而版號可能差上好幾個大版本。活著的是 `/data/app` 那一組，而分辨它們靠的是 dumpsys 自己印的段標——`Packages:` 底下是活的，`Hidden system packages:` 底下是被蓋掉的出廠版，所以 grep 要把這兩個段標一起收進來，只看路徑會在不熟悉的機型上判錯。

`pm resolve-activity` 回答的是廠商有沒有把這個 action 接走：輸出的 `ActivityInfo` 區塊帶 `name=` 與 `packageName=`，指出這個 action 最後落在誰身上。它下方巢狀的 `ApplicationInfo` 另有一組同名欄位，那是該套件的 Application 類別、不是承接的 Activity，所以直接 `grep name=` 會拿到兩個不同的值。系統設定頁被換掉的時候，這一條看得到換成了誰。

device owner 與 profile owner 的差別在管轄範圍：device owner 管整台機器，profile owner 只管工作資料夾，而兩者都下得了安裝限制。所以排除管控層要兩個都是空的，只確認其中一個不夠。

## 放寬安裝管控的那一條跨過唯讀的邊界

`appops get` 那組唯讀查詢與這一條走的是同一個介面，差別在這一條會寫。`REQUEST_INSTALL_PACKAGES` 是「這個套件可以觸發安裝其他套件」的授權，正常路徑由使用者在設定頁逐一開啟。用指令直接設成 `allow` 等於跳過那個確認，所以它改變的是裝置的安全設定，適用範圍限於自己擁有、可以重置的開發測試機。

```bash
# 放寬安裝管控：允許該套件安裝其他套件（僅限自有的開發測試機）
adb -s <serial> shell appops set <package> REQUEST_INSTALL_PACKAGES allow

# 還原
adb -s <serial> shell appops set <package> REQUEST_INSTALL_PACKAGES default
```

還原寫 `default` 而不寫 `deny`：`default` 把判斷交還給系統的預設規則，`deny` 是一個主動的拒絕決定，兩者在後續的行為上不同。還原與紀錄是這條指令的一部分——沒還原的機器在後續測試裡不再代表出廠狀態，而它被改過這件事只存在於操作者的記憶裡。

## 狀態 API 的射程止於它自己

把 `appops`、`dumpsys device_policy`、`dumpsys user` 問過一輪之後全部回報正常——授權交還預設、沒有 device owner、當前使用者的 `Effective restrictions` 是 `none`——而對話框仍然擋在那裡。這組回報本身就是一則訊息，而它的理由在前面那一節就給過了：`dumpsys` 把問題轉給各個服務自己的實作，所以這幾條查詢的答案分別由幾個不同的元件產生。擋下安裝的若是被改寫過的安裝器元件，負責回答問題的正是被改寫的那一個。它照實回報了管控層的狀態，擋人的那一道不在那一層。

這裡要判的是「畫面上那一段文字由誰畫的」，而 `dumpsys window` 的 `mCurrentFocus` 只回答了其中一半。**一個視窗可以畫在有焦點的視窗之上而不取得焦點**——宣告成 `APPLICATION_OVERLAY` 且帶 `NOT_FOCUSABLE` 的視窗就是這樣，`mCurrentFocus` 與 `mFocusedApp` 兩欄都不會動。這不是系統專屬的能力，任何持有 `SYSTEM_ALERT_WINDOW` 的第三方套件都畫得出來，而 POS 這類機器上常駐的遠端協助、店務管理類 App 經常持有它。

所以「前景元件是系統安裝器、畫面文字是廠商的」這個組合指向的不只一種成因，排除另一種的成本是兩條唯讀指令：

```bash
adb -s <serial> shell appops query-op SYSTEM_ALERT_WINDOW allow     # 誰有能力疊上來
adb -s <serial> shell dumpsys window windows | grep -E "Window #|package=|ty=|fl="
```

第二條按 z-order 由上而下列出視窗。畫面上那段文字若來自一個排在安裝器之上、帶 `APPLICATION_OVERLAY` 的視窗，成因是那個套件疊上來，安裝器本身沒有被動過。兩條都排除掉之後，剩下的才是系統映像裡那個元件的內容被換過——至於是替換套件還是資源覆蓋，要看該機型的系統映像才判得出來，這一篇不涵蓋。

廠商換過的字串有幾個可以直接看出來的特徵：自己的措辭、品牌名，而且常常附帶一條指示——去某個後台開權限、確保裝置連網。三項齊全時判定明確。三項都沒有、文字讀起來中性的時候，正面的檢查是把畫面上那一句拿去 AOSP 的 `packages/apps/PackageInstaller` 的字串資源裡搜：搜得到逐字對應的，是系統原文。

## 判斷標準

狀態查詢全部回報正常而現象擺在眼前時，下一個要懷疑的對象是產生那些回答的元件本身，而不是再換一個 API 去問。畫面是裝置實際呈現的結果，狀態查詢是某個元件對自己的描述，而一個被換掉的元件仍然會給出語法完整的描述。

這條標準的前半要先讀對欄位。讀到一個非預設的值不等於它不適用——那個值要先確認它屬於當前的對象（`dumpsys user` 的 `Guest restrictions` 就是反面的例子）。而確實有非預設的值、那個值卻解釋不了現象時，這條標準照樣適用，理由是同一個：一則屬於別的使用者的限制同樣是語法完整的描述。零行輸出則要先分清楚是「沒有管控」還是「那個服務不在這台機器上」。

後半的下一步由現象的形態決定，而形態分得出四種：

| 現象                               | 下一步問誰                                                                   |
| ---------------------------------- | ---------------------------------------------------------------------------- |
| 畫面上沒有內容可看（安裝毫無反應） | 先確認抓的是對的顯示器、所有顯示器的 `mCurrentFocus` 都是 `null`，再去問 log |
| 畫面上是廠商的字串                 | 先排除 overlay，再判安裝器的內容被換過                                       |
| 畫面上是 AOSP 的原字串             | 擋下來的是正常的確認流程，往觸發安裝的那一側查                               |
| 畫面上是 App 自己的錯誤提示        | 動作送出去了而被 App 接住，往 App 自己的錯誤處理查                           |

第一種要的落點 logcat 那一節沒有給——那一節教的全是怎麼把噪音減掉，而這裡需要的是一個正向的搜尋目標。安裝器有沒有被啟動，看的是 `ActivityTaskManager` 的視窗切換紀錄：

```bash
grep -E 'ActivityTaskManager.*(START|Displayed)' install.log | grep -i <安裝器套件名>
```

撈得到 `cmp=<安裝器套件>/.InstallStart` 這一行，代表安裝的意圖已經送出去、問題在安裝器那一側；撈不到，代表 App 根本沒把它發出去，往回查的是 App 自己——先用狀態查詢那一節的 `ls -l` 確認 APK 有沒有落到私有目錄、時間戳是不是這一次的。

重現一次動作才有這段 log，而重現需要有人在機器那一端操作。遠端觸發要走寫入類的指令，那條邊界與放寬安裝管控那一節是同一條。

同一條判斷標準換一個層級就換一篇：懷疑的對象從「回答問題的軟體元件」換成「這台機器上實際接了什麼硬體」時，可核對的值要從硬體那一側取得，那條路線在[陌生機器的硬體盤點比從應用端反推便宜](../inventory-hardware-before-inferring-from-the-app/)裡展開，它給的是每一條盤點查詢換掉的是哪一個假設，以及盤點的完整度該用什麼條件檢查。
