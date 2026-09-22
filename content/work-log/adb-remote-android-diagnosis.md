---
title: "用 adb 遠端診斷 Android 實機"
slug: "adb-remote-android-diagnosis"
date: 2026-09-21
description: "機器不在手邊而要判斷畫面上是誰在擋、擷圖抓回來打不開、或 logcat 撈不到按下去那一刻時回來讀"
tags: ["adb", "android", "debugging", "logcat", "pos"]
---

這篇整理透過 Wi-Fi 連上 adb 之後，用來做遠端排查的指令與注意事項。範圍從 adb 已經接上那一刻開始——無線連線本身的配對與連接流程在[Android 無線調試連接指南](/other/android_wireless_debug/)。

## 指定裝置

adb 的參數分成兩段：`adb` 自己要讀的部分，以及要送去遠端執行的字串。分界是子命令本身，選擇裝置的參數要寫在 `shell` 之前。

```bash
adb devices -l                          # -l 多印 product / model / transport_id
adb -s <serial> shell <command>
adb -t <transport_id> shell <command>   # transport_id 較短、同一次連線內有效
```

寫成 `adb shell -s <serial> <command>` 時，`-s` 落在遠端那一側，`adb shell` 自己的解析器回 `adb shell: illegal option -- s`，指令沒有被送到遠端執行。沒有指定 transport 而多台在線時，adb 在更前面一步失敗、回 `adb: more than one device/emulator`，shell 的選項解析沒有被執行。同一個寫錯的指令因此有兩種回報，指向選項位置的那一則只在單機在線時看得到。

同一台無線機器可能同時以 IP 位址與 mDNS 名稱兩個 transport 在線，`adb devices` 因此列出兩列而背後是同一台。`adb devices -l` 印的 product / model 欄位在同一批機器上完全相同，靠它們分辨不了；硬體序號可以分辨，逐個 transport 問一次 `getprop ro.serialno`，回同一個值的是同一台。

```bash
for serial in $(adb devices | awk 'NR>1 && $2=="device" {print $1}'); do
  model=$(adb -s "$serial" shell getprop ro.product.model | tr -d '\r')
  brand=$(adb -s "$serial" shell getprop ro.product.brand | tr -d '\r')
  sdk=$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')
  hw=$(adb -s "$serial" shell getprop ro.serialno | tr -d '\r')
  echo "$serial | $brand $model (API $sdk) | $hw"
done
```

腳本裡每一行 `getprop` 的結尾都接了 `tr -d '\r'`，作用是去掉輸出裡的歸位字元（`\r`）。adb 在某些條件下會配置 [pty](/linux/dotfile/knowledge-cards/pty/)（pseudo-terminal，虛擬終端機），而作業系統核心的 pty 行規則會把每個 `0x0A`（換行）補成 `0x0D 0x0A`（歸位加換行）。補進來的 `0x0D` 肉眼看不見，但它會讓 shell 的字串比對失敗——`"$model" = "<型號字串>"` 這種比較永遠回假，因為 `$model` 的值尾端多了一個 `\r`。`tr -d '\r'` 在沒有 pty 的情況下是空操作，加上去沒有副作用。

## 遠端擷圖

```bash
adb -s <serial> exec-out screencap -p > screen.png
```

`screencap -p` 在裝置上把當前畫面編碼成 PNG 寫到標準輸出。`exec-out` 不對位元組做行尾轉換；`shell` 在配置了 pty 的時候會把 `0x0A` 換成 `0x0D 0x0A`，PNG 裡的 `0x0A` 是資料不是行尾，被換過之後整個檔案壞掉。

`adb shell` 配不配置 pty 取決於 adb 版本、裝置端有沒有 shell protocol v2（`adb features` 裡有沒有 `shell_v2`）、以及有沒有帶命令參數——帶命令的不配置，不帶命令的互動模式才配。這條規則在裝置有 shell_v2 且沒帶 `-t` / `-tt` 時成立，沒有 v2 的舊組合不適用。`exec-out` 把結果從這組版本組合裡拿出來。

可以用一段已知的位元組確認手上這條通道有沒有配 pty：

```bash
adb -s <serial> exec-out "printf 'a\nb\n'" | xxd
# 610a 620a        — 沒有轉換

adb -s <serial> shell -tt "printf 'a\nb\n'" < /dev/null | xxd
# 610d 0a62 0d0a   — 轉換了
```

`exec-out` 有一個代價：它把遠端的 stderr 併進 stdout。遠端吐一行警告，它就排在 PNG 前面進了檔案。`file` 與本機 stderr 分不出這種壞檔跟行尾被改寫的壞檔——兩種都是 `file` 回 `data`、stderr 零行；分得出的是檔案開頭的位元組（`xxd -l 16`）。

```bash
adb -s <serial> exec-out "printf 'OUT\n'; printf 'ERR\n' >&2" | xxd
# 4f55 540a 4552 520a        — stderr 混進來了

adb -s <serial> shell "printf 'OUT\n'; printf 'ERR\n' >&2" | xxd
# 4f55 540a                  — shell（有 v2 時）分開處理
```

### 驗證檔案

```bash
file screen.png
# 完好：PNG image data, <寬> x <高>, 8-bit/color RGBA, non-interlaced
# 開頭被塞了別的內容（行尾改寫或 stderr 混入）：data
# 零位元組（顯示器編號錯）：empty
```

`data` 有兩種來歷，分辨看檔案開頭：`xxd -l 16 screen.png`。完好 PNG 以 `8950 4e47 0d0a 1a0a` 起頭；行尾被改寫的簽章變成 `8950 4e47 0d0d 0a1a`；stderr 混入的開頭是讀得懂的文字。

### 舊環境的兩段式做法

`exec-out` 不可用時，讓裝置端先寫檔再 `pull` 回來。`pull` 是檔案傳輸、不做行尾處理、也不併 stderr。`pull` 與 `shell` 的可讀範圍不一樣，`/sdcard` 底下兩者都讀得到，系統分割區 `shell` 讀得到而 `pull` 可能回 `Permission denied`。

```bash
adb -s <serial> shell screencap -p /sdcard/screen.png
adb -s <serial> pull /sdcard/screen.png ./device-screen.png
adb -s <serial> shell rm /sdcard/screen.png
```

### 錄影

```bash
adb -s <serial> shell screenrecord --time-limit <秒數> /sdcard/demo.mp4
adb -s <serial> pull /sdcard/demo.mp4 ./
```

時間上限由 `screenrecord` 自己定，`adb -s <serial> shell screenrecord --help` 會印出來。

### 多螢幕機器的顯示器選擇

`screencap` 預設抓主顯示器。POS 機的客顯是對話框可能出現的地方之一，要加 `-d` 指定顯示器。

**編號要取自 SurfaceFlinger，不是 `dumpsys window` 的 `mDisplayId`。** 兩套編號不相容，把 `mDisplayId` 餵給 `screencap -d` 的結果是成功退出、stderr 零行、檔案零位元組。`screencap --help` 自己就寫著要去 SurfaceFlinger 查。

```bash
adb -s <serial> shell dumpsys display | grep mViewports     # 同一行印出兩套編號的對應
adb -s <serial> exec-out screencap -p -d <SurfaceFlinger 的編號> > screen.png
```

`dumpsys display` 的 `mViewports` 行裡 `displayId=` 是 `dumpsys window` 那一套，`uniqueId='local:<數字>'` 裡的數字是 `screencap -d` 要的那一套。

## 前景元件查詢

`screencap` 的擷圖看到畫面上寫了什麼，查畫面由哪個元件繪製要用 `dumpsys window`：

```bash
adb -s <serial> shell dumpsys window | grep -iE "mCurrentFocus|mFocusedApp"
```

輸出帶套件名與 Activity 名。多螢幕機器每個顯示器各印一組，沒有焦點的顯示器兩個欄位都是 `null`。讀輸出時跳過兩欄都是 `null` 的組，找到欄位有值的那一組——它對應的就是有焦點的顯示器。

一個視窗可以畫在有焦點的視窗之上而不取得焦點——`APPLICATION_OVERLAY` 且 `NOT_FOCUSABLE` 的視窗就是這樣，`mCurrentFocus` 不會動。任何持有 `SYSTEM_ALERT_WINDOW` 的第三方套件都畫得出來。排除 overlay 的方法：

```bash
adb -s <serial> shell appops query-op SYSTEM_ALERT_WINDOW allow     # 誰有這個權限
adb -s <serial> shell dumpsys window windows \
  | grep -E "Window #|package=|ty=|mViewVisibility="                # 當下的視窗堆疊
```

第一條列的是能力不是行為，有權限不代表當下有畫東西。第二條按 z-order 由上而下列出視窗，要同時看三個條件：排在目標之上、`ty=APPLICATION_OVERLAY`、且 `mViewVisibility=0x0`。第三個條件用來排除隱形視窗：`0x4` 是存在但不可見，系統自己就常駐幾個這樣的視窗（拖放目標、螢幕裝飾）。三個條件同時成立才代表有第三方視窗正在疊圖。截圖分不出 overlay 與被改寫的元件，兩種在畫面上長得一樣，只有 z-order 的輸出分得開。

## logcat

logcat 讀的是裝置上的[環狀緩衝區](/linux/dotfile/knowledge-cards/ring-buffer-log/)，寫滿之後從頭覆蓋。時間窗由清空與倒出界定，中間那一段是重現問題時裝置寫進去的。

macOS 上常見的替代做法是用 `timeout` 控制收集時間，但 `timeout` 屬於 GNU coreutils，macOS 預設沒有（裝了 coreutils 之後叫 `gtimeout`）。`timeout 300 adb logcat > install.log` 在 macOS 上留下的是 0 bytes 的 `install.log`——`command not found: timeout` 走 stderr、沒進重導檔。清空與倒出已經界定了時間窗，收集時間由操作本身決定，本機的計時程序沒有需要做的事。

```bash
adb -s <serial> logcat -G 16M                          # 放大緩衝區
adb -s <serial> logcat -c                              # 清空，時間窗起點
# （在機器上重現問題）
adb -s <serial> logcat -d -v threadtime > install.log    # 倒出，時間窗終點
adb -s <serial> logcat -g                              # 確認各緩衝區大小
```

| 參數            | 用途                                                                                                                                                     |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `-G 16M`        | 放大緩衝區。POS 機、車機這類常駐服務多的機器，緩衝區在重現過程中就可能把最早的行覆蓋掉——關鍵行往往正是操作之前的那幾行。`16M` 是起點，對著 `-g` 的現況調 |
| `-c`            | 清空                                                                                                                                                     |
| `-v threadtime` | 每行帶 PID / TID 與精確時間戳                                                                                                                            |
| `-d`            | 一次倒出後結束，不停在前景等                                                                                                                             |
| `-g`            | 每個緩衝區各印一行，設完跑一次看 `-G` 涵蓋了哪幾個                                                                                                       |

### PID 與 tag

`-v threadtime` 的欄位順序是日期、時間、PID、TID、層級、tag。PID 直接指出發出這一行的 process；tag 由各元件自行填寫、跨元件會重複，只憑 tag 做對應是推測。

### 篩選

時間排在第二欄，零填補定寬（`HH:MM:SS.mmm`），可以直接用字串比較篩。兩側都要寫——logcat 會插入 `--------- beginning of main` 這類分隔行，第二欄是 `beginning`，字串序大於任何時間值，只寫下界會把它放進來。

```bash
grep -vE "<佔多數的服務 tag>" install.log | tail -<行數>
awk '$2 >= "16:26:00.000" && $2 <= "16:27:00.000"' install.log \
  | grep -viE "adbd|<該機常駐服務的 tag>"
```

找出佔多數的 tag：

```bash
awk '{print $6}' install.log | sort | uniq -c | sort -rn | head
```

logcat 把 tag 欄補寬到八個字元。短於八個字元的 tag 後面冒號被推成獨立一欄，所以長 tag 在第六欄帶冒號（`WifiVendorHal:`）、短 tag 不帶（`adbd`）。統計結果貼回 `awk` 做精確比對前，先確認有沒有尾冒號。

### 找特定元件的啟動紀錄

安裝器有沒有被啟動，看 `ActivityTaskManager` 的視窗切換紀錄：

```bash
grep -E 'ActivityTaskManager.*(START|Displayed)' install.log | grep -i <安裝器套件名>
```

撈得到 `cmp=<套件>/.InstallStart`，代表安裝意圖已經送出去；撈不到，代表 App 根本沒把它發出去。

## 狀態查詢

`dumpsys <服務>` 把問題轉給那個服務自己的 dump 實作，`dumpsys window` 和 `dumpsys user` 的回答由不同的元件產生，格式各自決定。服務不存在時回一行 `Can't find service: <名字>` 並成功退出，`grep` 的結果是零行——先用 `dumpsys -l | grep <服務>` 確認服務在不在。

```bash
adb -s <serial> shell pm list packages | grep -i <keyword>
adb -s <serial> shell appops get <package> REQUEST_INSTALL_PACKAGES
adb -s <serial> shell dumpsys device_policy | grep -iE "owner|admin|restriction" -A<行數>
adb -s <serial> shell dumpsys user | grep -i restriction -A<行數>
adb -s <serial> shell settings list secure | grep -i <key>
adb -s <serial> shell settings get secure <key>
adb -s <serial> shell pm resolve-activity -a android.settings.MANAGE_UNKNOWN_APP_SOURCES
adb -s <serial> shell dumpsys package <package> | grep -iE "versionCode|versionName|codePath|^Packages:|Hidden system packages:"
adb -s <serial> shell ls -l /storage/emulated/0/Android/data/<package>/
```

### appops

`appops` 的 mode 是一組固定值（`allow` / `ignore` / `deny` / `default`，位置類另有 `foreground`）。`ignore` 與 `deny` 都讓呼叫拿不到值，差別在 `deny` 回報失敗、`ignore` 靜默回空。從沒設定過的印 `No operations.` 加一行 `Default mode: default`。

### dumpsys user

要讀的是目標使用者底下的 `Effective restrictions`。`grep -i restriction` 還會撈到 `Guest restrictions`（guest 使用者型別的預設清單）、`mDefaultRestrictions`、`Device policy global restrictions`，它們都不是當前使用者的有效值。判別看它落在哪個標題底下：`UserInfo` 區塊裡的屬於那個使用者，`Device properties` 或使用者型別定義裡的是型別預設。`Guest restrictions` 裡面本來就列著 `no_install_unknown_sources`——乾淨機器上 grep 照樣撈到這一行，跟現象無關。

### dumpsys device_policy

device owner 管整台機器，profile owner 只管工作資料夾，兩者都能下安裝限制。排除管控層要兩個都是空的。

### settings

分成 global / secure / system 三個 namespace，一個鍵通常只在其中一個裡面有值。跨版本搬過家的鍵會在舊 namespace 留下值為 `null` 的殘餘，`null` 因此蓋住三種情形：查錯 namespace、這台機器沒有這個設定、以及殘餘。`settings list <ns> | grep <key>` 命中不等於值在這裡——三個 namespace 都 `get` 過一輪，確認只有一個回非 `null`，才能確定值在哪。

### dumpsys package

更新過的系統 App 有兩組值：出廠版在 `/system/app`、更新版在 `/data/app`。分辨靠 dumpsys 印的段標——`Packages:` 底下是活的、`Hidden system packages:` 底下是被蓋掉的出廠版。grep 要把段標一起收進來。

### pm resolve-activity

輸出的 `ActivityInfo` 區塊帶 `name=` 與 `packageName=`，指出 action 落在誰身上。下方巢狀的 `ApplicationInfo` 另有一組同名欄位，那是套件的 Application 類別，直接 `grep name=` 會拿到兩個不同的值。

## 放寬安裝管控（修改型指令）

`REQUEST_INSTALL_PACKAGES` 是「這個套件可以觸發安裝其他套件」的授權。正常由使用者在設定頁逐一開啟，用指令設成 `allow` 等於跳過確認，改變的是安全設定，只適用自己擁有、可以重置的開發測試機。

```bash
# 放寬（僅限自有開發測試機）
adb -s <serial> shell appops set <package> REQUEST_INSTALL_PACKAGES allow

# 還原
adb -s <serial> shell appops set <package> REQUEST_INSTALL_PACKAGES default
```

還原寫 `default` 而不是 `deny`：`default` 把判斷交還系統預設規則，`deny` 是主動拒絕，後續行為不同。驗證完還原，記錄改過哪一台——沒還原的機器在後續測試裡不再代表出廠狀態。

## 相關指引

同一批 POS 排查的其餘指引：

- [USB 類別代碼記在裝置層與介面層兩處](../usb-class-code-lives-in-two-layers/)
- [claim 一個 USB 介面等於接管它](../usb-claim-takes-the-hardware-away/)
- [兩種錯法的代價不對稱時，過濾策略要讓失敗倒向可補救的那一邊](../filter-strategy-follows-asymmetric-failure-cost/)
- [陌生機器的硬體盤點比從應用端反推便宜](../inventory-hardware-before-inferring-from-the-app/)
