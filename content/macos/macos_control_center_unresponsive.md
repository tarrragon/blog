---
title: "選單列的控制中心沒有回應：ControlCenter 程序的判讀與重啟"
date: 2026-11-17
slug: "macos_control_center_unresponsive"
description: "點選單列右上角的控制中心，或 Wi-Fi、藍牙、音量、時鐘這些系統圖示沒有反應、游標停在上面一直轉圈時回來看：怎麼查出卡住的是哪一個程序、從 ps 的欄位分辨它在空轉還是在等待、為什麼結束它之後系統會自己把它開回來，以及什麼情形下要改成重新開機。"
tags: ["macos", "menu-bar", "control-center", "launchd", "process", "troubleshooting"]
---

**事件說明**：2026-11-17，一台 Apple Silicon Mac，macOS 15.3.1（build 24D70），接了兩個螢幕，距離上次開機 11 天。當時在終端機與瀏覽器之間切換工作，點了選單列右上角的控制中心圖示。

這篇整理選單列右上角的控制中心沒有回應時的判讀與處置：選單列上每個圖示由哪一個程序畫出，以及怎麼從失靈圖示的位置查出它的程序；等待游標（俗稱彩色轉圈的游標）代表 App 處在什麼狀態；用 `ps` 的 `STAT` 與 `%CPU` 分辨程序是在空轉還是在等待，用 `ELAPSED` 與 `%MEM` 看它連續執行了多久、佔了多少記憶體；`launchd` 用什麼設定管理 `ControlCenter`，所以結束這個程序之後它會被自動開回來，以及同一套方法適用的 Dock、Finder、`SystemUIServer`；重啟之後怎麼確認恢復；系統自動留下的診斷報告與重啟之前用 `sample` 取得的呼叫堆疊怎麼讀；以及空轉與等待兩種形態對重啟的效果有什麼不同、什麼情形下要改成登出再登入或重新開機。指令與輸出都在 macOS 15.3.1 上實跑，選單列圖示分給哪些程序依版本而變，以自己機器上的查詢結果為準。程序表格位耗盡造成的「開不了新程序」是另一類故障，寫在 [殭屍程序與使用者程序上限：程序表格位的配置與回收](../macos_process_limit_zombie_reaping/)。

## 選單列圖示的擁有程序

macOS 選單列右側的每個圖示，是某一個程序在選單列那一層開出來的小視窗；開出視窗的程序負責畫這個圖示，也負責處理使用者對它的點擊。所以「右上角沒有反應」可能只有其中一個程序卡住，其他程序的圖示照常運作；要判讀的對象是失靈的那個圖示所屬的程序。

macOS 11 起，Wi-Fi、藍牙、聲音這類系統狀態圖示與控制中心本身，由 `ControlCenter` 程序（`/System/Library/CoreServices/ControlCenter.app`）畫出，在那之前大多由 `SystemUIServer` 畫出（依第三方的整理：Howard Oakley〈What's right at the end of the menu bar, and how it's changing〉，eclecticlight.co，2020-09-25；這次沒有找到 Apple 說明這份分配的文件）。第三方 App 的圖示由那個 App 自己的程序畫出。

要查出自己機器上每個圖示屬於誰，可以列出主螢幕選單列那一層的全部視窗，依水平位置由右到左排列。下面這段程式要先存成 `menubar.swift`，執行它需要 Xcode 或 Xcode Command Line Tools（沒有的話，`xcode-select --install` 安裝）：

```swift
// menubar.swift：列出主螢幕選單列上每個圖示視窗的位置、擁有者的 PID 與名稱
import CoreGraphics
let level = Int(CGWindowLevelForKey(.statusWindow))
let main = CGDisplayBounds(CGMainDisplayID())
let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as! [[String: Any]]
var rows: [(Double, Int, String)] = []
for w in list where (w[kCGWindowLayer as String] as? Int) == level {
  guard let b = w[kCGWindowBounds as String] as? [String: Double],
        let x = b["X"], let y = b["Y"], let h = b["Height"], h <= 40,
        main.contains(CGPoint(x: x, y: y)) else { continue }
  rows.append((x, w[kCGWindowOwnerPID as String] as? Int ?? 0,
               w[kCGWindowOwnerName as String] as? String ?? "?"))
}
for (x, pid, owner) in rows.sorted(by: { $0.0 > $1.0 }) { print(Int(x), pid, owner) }
```

```bash
swift menubar.swift
```

程式裡的 `CGWindowLevelForKey(.statusWindow)` 取得狀態列視窗所在的層級（這台機器上是 25），選單列右側的圖示都開在這一層。`CGMainDisplayID()` 是主螢幕；接了好幾個螢幕時，每個螢幕的選單列各有一份同樣的圖示，所以程式只留下左上角落在主螢幕範圍內的視窗，否則同一個圖示會列出好幾次。同一層裡偶爾也有不是圖示的視窗：這台機器上的視窗管理工具 Magnet 在這一層開了一個跟螢幕一樣大的透明視窗，所以程式另外只留高度不超過 40 點的視窗（選單列的高度在這個範圍內）。這次實跑的輸出（節錄）：

```text
3651 58426 控制中心
3621 496 SystemUIServer
3587 58426 控制中心
3556 550 Spotlight
3518 58426 控制中心
3429 796 TextInputMenuAgent
3396 58426 控制中心
...
3121 16463 iStat Menus Menubar
...
2908 477 Tailscale
```

三欄依序是圖示視窗左緣的水平座標（單位是螢幕的點，數字越大越靠右）、擁有者的 PID 與擁有者的名稱。第一列就是選單列最右邊的那個圖示，往下一列往左一個圖示，所以從右邊數過來，失靈的圖示是第幾個，就讀第幾列。名稱欄印的是 App 的顯示名稱，跟著系統語言：中文介面下 `ControlCenter` 印成「控制中心」，英文介面印成 Control Center。PID 欄是不受語言影響的對照：「控制中心」那幾列的 PID 58426，就是 `ps` 裡 `ControlCenter` 那一列的 PID。

這次的輸出裡，「控制中心」的圖示散在 `SystemUIServer`、Spotlight、輸入法（`TextInputMenuAgent`）的圖示之間，最右邊的時鐘也是它的。失靈的是控制中心的圖示，所以要判讀的程序是 `ControlCenter`。失靈的圖示若對到第三方 App 的列，要查的是那個 App 的程序，下面 `ps` 的判讀方法照樣適用，換成那個 PID 即可；處置則照那個 App 自己的結束方式（App 選單裡的「結束」，或 `kill <PID>`；用 `killall` 時，名稱有空白要加引號，例如 `killall "iStat Menus Menubar"`），再從「應用程式」資料夾打開它。接了好幾個螢幕時，其他螢幕選單列上的圖示是同一個程序畫的複本，所以只有某個螢幕上的圖示失靈時，查的仍是同一個 PID。

## 等待游標與主執行緒的事件處理

滑鼠移到某個 App 的視窗上、游標變成彩色轉圈的等待游標，代表那個 App 一段時間沒有回應使用者的操作。Apple 的開發者文件〈Understanding hangs in your app〉把 App 對一次使用者操作的處理延遲到使用者察覺得到的情形稱為 hang，並寫出 App 沒有回應時 macOS 會顯示這個轉圈的等待游標（文件稱它 spinning wait cursor）。App 處理使用者操作的位置是主執行緒：滑鼠與鍵盤事件由系統程序 `WindowServer` 分送給各 App，App 的主執行緒從自己的事件佇列取出事件來處理，主執行緒沒有回去取事件時，點擊就一直排在佇列裡。由誰在什麼時候換上等待游標，那份文件沒有寫；從機制推論，換游標的是負責畫出游標的 `WindowServer`，因為卡住的 App 自己沒有空做這件事。

所以等待游標只出現在卡住的那個程序的視窗上。這次游標只在控制中心的圖示上轉圈，移到別的 App 的視窗上就恢復正常；從這兩個觀察，卡住的範圍可以先縮小到一個程序。整台機器的 CPU 或記憶體耗盡時，所有 App 一起變慢，等待游標會出現在很多 App 的視窗上。

主執行緒沒有回去取事件，常見的成因有兩種，兩種在 `ps` 上看起來不同：

- **空轉**：主執行緒一直在跑某段運算（例如一個條件永遠不成立的迴圈），沒有時間回去取事件。這時程序的 CPU 用量接近一顆核心的 100%。
- **等待**：主執行緒停在一個要等的操作上（等一把鎖、等另一個程序的回覆、等磁碟或網路的 I/O），等不到就一直停著。這時程序幾乎不用 CPU。

這兩種是讀 `ps` 時分得出來的兩類，不是全部的可能；`ps` 分不進這兩類時（例如 `%CPU` 在 50 上下、介面時好時壞），用〈卡住時的呼叫堆疊：系統的診斷報告與 sample〉的方法看主執行緒停在哪裡。

## 用 ps 的 STAT、%CPU、ELAPSED、%MEM 判讀卡住的程序

`ps` 一次印得出程序的狀態、CPU 用量、記憶體用量與已執行的時間。這次用的指令與輸出：

```bash
ps -Ao pid,ppid,stat,%cpu,%mem,etime,comm | egrep -i 'ControlCenter|SystemUIServer|WindowServer|PID'
```

```text
  PID  PPID STAT  %CPU %MEM     ELAPSED COMM
  155     1 Rs    42.3  0.5 11-00:58:18 /System/Library/PrivateFrameworks/SkyLight.framework/Resources/WindowServer
  495     1 R     97.1  4.4 11-00:58:11 /System/Library/CoreServices/ControlCenter.app/Contents/MacOS/ControlCenter
  496     1 S      0.0  0.1 11-00:58:11 /System/Library/CoreServices/SystemUIServer.app/Contents/MacOS/SystemUIServer
```

`-o` 指定要印的欄位。`-A` 列出所有程序：不加的話，`ps` 只列自己的、而且有控制終端機的程序，`ControlCenter` 沒有控制終端機，`WindowServer` 屬於另一個使用者（`_windowserver`），兩個都列不出來。`egrep` 的 pattern 是要找的程序名，加上 `PID` 是為了留下表頭那一行；查第三方 App 時，把程序名換成它的名字。四個欄位的讀法：

- **`STAT`**：第一個字母是程序的狀態（`man ps`）。`R` 是正在執行或排隊等 CPU；`S` 是睡眠不到約 20 秒，`I` 是睡眠超過約 20 秒；`U` 是不可中斷的等待。第二個字母起是附加旗標，例如 `s` 代表這個程序是 session leader，跟卡不卡住無關，所以 `Rs` 讀作 `R`。
- **`%CPU`**：100 代表佔滿一顆核心。

  這兩欄合起來分辨空轉與等待：`STAT` 是 `R`、`%CPU` 接近 100，是空轉；`STAT` 是 `S`、`I` 或 `U`、`%CPU` 接近 0，介面卻沒有反應，是等待。`ControlCenter` 的 `R` 與 97.1 屬於空轉。`ps` 印的是執行當下的一張快照，空轉或等待要持續才算卡住，所以隔幾秒再跑一次，`STAT` 兩次都一樣才下判斷；`%CPU` 是最長一分鐘的衰減平均，隔幾秒的兩次讀數不是兩次獨立的量測，要看當下的用量用 `top`（見〈重啟 ControlCenter 與確認恢復〉）。這次處理時只跑了一次 `ps` 就重啟；事後從系統的診斷報告查到，同一個程序在兩天前就有過一段三分鐘平均 51% 的高 CPU（見〈卡住時的呼叫堆疊：系統的診斷報告與 sample〉）。`STAT` 是整個程序的狀態：主執行緒卡在等待、而別的執行緒照常醒來時，程序仍可能顯示 `S`，這時要靠 `sample` 看主執行緒本身。
- **`ELAPSED`**：程序從啟動到現在的時間，格式是 `天-時:分:秒`，不滿一天時省略天，不滿一小時時再省略時（`00:02` 是兩秒）。`11-00:58:11` 是十一天；`sysctl kern.boottime` 印出這次開機的時間（這台是 11 月 6 日），兩者對得上，代表 `ControlCenter` 從登入起就沒有重啟過。
- **`%MEM`**：佔實體記憶體的百分比。同一份輸出裡同樣執行了十一天的 `SystemUIServer` 是 0.1，`ControlCenter` 是 4.4。重啟之後新的 `ControlCenter` 是 0.3（見〈重啟 ControlCenter 與確認恢復〉的輸出）。這兩個時間點分不出 4.4 是十一天慢慢長出來的，還是卡住期間才長出來的，這次沒有在卡住之前量過。

同一份輸出裡 `WindowServer` 的 `%CPU` 也偏高（42.3）；`ControlCenter` 重啟之後它的用量是否跟著下降，是判斷它與這次卡住是否有關的依據。這次重啟之後幾秒，用同一條 `ps` 指令讀到的 `WindowServer` 是 41.6，之後用 `top` 讀當下的用量是 45.6，都沒有跟著降，所以 `WindowServer` 的用量不是 `ControlCenter` 造成的；它是其他 App 的繪製、還是 `WindowServer` 自己的畫面合成造成的，這次沒有追查。同一張快照裡兩個程序的數字都偏高，看不出誰是源頭；重啟其中一個之後看另一個有沒有跟著降，才分得出來。處置的對象因此只有 `ControlCenter`。`WindowServer` 結束會讓整個登入工作階段一起結束，所有 App 都會被關掉。

要確認卡住的程序只有這一個，`ps -Ao %cpu,%mem,pid,comm -r | head -8` 依 CPU 用量由高到低列出前七名（`-r` 是依 CPU 排序，`head -8` 多留一行給表頭）。這次 `ControlCenter` 排第一、`WindowServer` 第二，其餘程序都在 35% 以下：CPU 用量異常的系統程序只有 `ControlCenter`，跟等待游標只出現在控制中心圖示上的觀察一致。

## launchd 用 KeepAlive 把 ControlCenter 開回來

`ControlCenter` 由 `launchd` 啟動與看管。`launchd` 是 macOS 的第一個程序（PID 1），開機與登入時依各個 plist 設定檔啟動服務，並依設定決定服務結束之後要不要重新啟動（plist 的基本結構見 [launchd Service](/llm/knowledge-cards/launchd-service/)）。`ControlCenter` 的設定檔在 `/System/Library/LaunchAgents/com.apple.controlcenter.plist`，用 `plutil -p` 可以印成讀得懂的格式：

```bash
plutil -p /System/Library/LaunchAgents/com.apple.controlcenter.plist
```

```text
  ...
  "KeepAlive" => {
    "SuccessfulExit" => 0
  }
  "Label" => "com.apple.controlcenter"
  ...
  "LimitLoadToSessionType" => [
    0 => "Aqua"
  ]
  ...
  "Program" => "/System/Library/CoreServices/ControlCenter.app/Contents/MacOS/ControlCenter"
  "ThrottleInterval" => 1
```

（節錄。`plutil -p` 依鍵名的字母順序印出，每一處 `...` 都省略了幾個鍵，包括 `EnablePressuredExit`、`EnableTransactions`、`LaunchEvents`、`MachServices`。）跟重啟有關的是兩個鍵：

- **`KeepAlive` 底下的 `SuccessfulExit`**：這個鍵的值是 0，也就是 false。`launchd.plist(5)` 的 man page 定義它的意思：值為 true 時，程序以結束碼 0 結束才重新啟動；值為 false 時反過來，程序以非 0 的結束碼結束才重新啟動。man page 沒有寫被信號終止的程序怎麼算；這次 `killall` 送出 `SIGTERM` 結束 `ControlCenter` 之後，`launchd` 把它重新啟動了（〈重啟 ControlCenter 與確認恢復〉的 `runs = 2`），而 `launchctl list | grep -i controlcenter` 印出的 `58426  -15  com.apple.controlcenter`（欄與欄之間是 tab）第二欄 `-15` 是上一次結束的原因：負數代表被那個編號的信號終止，15 是 `SIGTERM`。所以至少在這台機器上，被信號終止算進要重新啟動的那一邊。
- **`ThrottleInterval`**：兩次啟動之間至少要隔幾秒。man page 寫的預設是 10 秒，用來避免一個一啟動就結束的服務被反覆快速重啟；這個 plist 把它設成 1 秒，所以 `ControlCenter` 結束之後約 1 秒就回來，不必等 10 秒。`launchctl print` 的 `properties` 欄另外列出 `exponential throttling`；從欄位名推論，連續結束好幾次時重啟的間隔可能逐次拉長，1 秒是單次結束時的間隔（這次只結束過一次，沒有驗證）。

`LimitLoadToSessionType` 是 `Aqua`，代表這個服務屬於圖形介面的登入工作階段，每個登入的使用者各有一份；重啟它只影響目前登入的使用者自己的選單列。`SystemUIServer` 的設定檔（`/System/Library/LaunchAgents/com.apple.SystemUIServer.plist`，Label 是 `com.apple.SystemUIServer.agent`）同樣設了 `SuccessfulExit => 0`。

「結束程序之後它會自己回來」成立的前提就是這組設定。一個程序沒有交給 `launchd` 用 `KeepAlive` 看管時，結束它就只是結束，要自己再開一次，而它若是登入工作階段要用的元件，結束之後那一項功能就一直不在。所以結束一個系統程序之前，先確認它會不會被開回來。手上只有程序名時，用 `launchctl list | grep -i <程序名>` 找出它的 Label（第三欄），再用〈重啟 ControlCenter 與確認恢復〉裡的 `launchctl print gui/$(id -u)/<Label>` 查它；輸出裡 `path =` 那一行是它的 plist 位置，用 `plutil -p` 讀那個檔，看有沒有 `KeepAlive`。`path =` 印的是 `(submitted by smd.88)` 這類「由某個程序登記」的字樣時（這台機器上的 iStat Menus 就是），這個服務是 App 執行時登記進 `launchd` 的，沒有 plist 可以查；它結束之後會不會被開回來，這兩行看不出來，處置時當成不會自動回來，結束之後自己再打開一次。

Apple 自己的介面程序多數用同一組設定：`com.apple.Dock.plist`、`com.apple.Finder.plist` 與 `SystemUIServer` 的 plist 都設了 `KeepAlive` 底下的 `SuccessfulExit => 0` 與 `ThrottleInterval => 1`（另外多一個 `AfterInitialDemand`），所以 Dock、Finder 或 `SystemUIServer` 的圖示沒有反應時，這篇的判讀與重啟方法照樣適用，換成它們的程序名與 Label。`WindowServer` 不在這個範圍：它結束時整個登入工作階段一起結束，等於登出。

## 重啟 ControlCenter 與確認恢復

確認卡住的是 `ControlCenter`、而且它會被 `launchd` 開回來之後，結束它：

```bash
killall ControlCenter
```

`killall` 依程序名結束程序，預設送出 `SIGTERM`，讓程序有機會自己收尾再結束。引數 `ControlCenter` 是可執行檔的名字，也就是 `ps` 的 `COMM` 欄位路徑最後一段；中文介面上顯示的「控制中心」是 App 的顯示名稱，`killall` 用它比對不到任何程序。隔幾秒用 `ps` 看，PID 沒有變、`ELAPSED` 沒有從頭算起，代表 `SIGTERM` 沒有結束它，這時 `killall -9 ControlCenter` 送出程序無法攔截的 `SIGKILL`。不要加 `sudo`：以 root 執行的 `killall ControlCenter` 會比對到每一個登入使用者的 `ControlCenter`，連別人的選單列一起重啟。`launchd` 本身也提供重啟服務的指令 `launchctl kickstart -k gui/$(id -u)/com.apple.controlcenter`（`-k` 先結束正在執行的那一份再啟動），這次沒有實跑。

不想用終端機時，用「活動監視器」：搜尋 `ControlCenter`，`%CPU` 欄看得到同樣的用量；選取之後的「取樣程序」（這次沒有在卡住時用過）做的事跟〈卡住時的呼叫堆疊：系統的診斷報告與 sample〉的 `sample` 相同，工具列的停止按鈕則結束它，對話框的「結束」相當於 `killall`，「強制結束」相當於 `killall -9`，兩種結束之後它都會被 `launchd` 開回來。活動監視器少了 `STAT` 欄，也沒有可以貼進紀錄的文字輸出，這是用 `ps` 的理由。按 ⌘⌥Esc 打開的「強制結束應用程式」視窗列不出 `ControlCenter`：它的 `Info.plist` 設了 `LSUIElement => 1`，代表它不在 Dock 上顯示，那個視窗只列 Dock 上的 App。

這次 `killall` 之後隔幾秒，用前一節的同一條指令再跑一次 `ps`（下面只節錄兩列，`PPID` 兩列都是 1）：

```text
  PID  PPID STAT  %CPU %MEM     ELAPSED COMM
  155     1 Ss    41.6  0.7 11-00:58:27 /System/Library/PrivateFrameworks/SkyLight.framework/Resources/WindowServer
58426     1 S      1.8  0.3       00:02 /System/Library/CoreServices/ControlCenter.app/Contents/MacOS/ControlCenter
```

`ControlCenter` 換了一個新的 PID（58426），`ELAPSED` 是兩秒，`STAT` 是 `S`、`%CPU` 是 1.8、`%MEM` 是 0.3，空轉的形態消失了。`ps` 確認的是程序的狀態，使用者操作恢復了沒有，要再點一次控制中心的圖示，看面板打不打得開、等待游標還出不出現。`launchd` 對這個服務的紀錄用 `launchctl print` 讀：

```bash
launchctl print gui/$(id -u)/com.apple.controlcenter | egrep '^\s*(runs|pid|state) ='
```

`gui/<uid>` 指目前登入使用者的圖形介面工作階段，指令裡的 `$(id -u)` 由 shell 換成自己的 uid，照抄即可；最後一段是 plist 裡的 `Label`。完整輸出有一百多行，`egrep` 只留下這三行：

```text
state = running
runs = 2
pid = 58426
```

`runs = 2` 代表 `launchd` 在這次登入之後啟動過這個服務兩次（登入時一次、`killall` 之後一次），`pid = 58426` 對得上 `ps` 裡新的程序。

`ps` 的 `%CPU` 是最長一分鐘的衰減平均（`man ps`）：一直在執行的程序（例如 `WindowServer`），它的源頭停下之後的頭幾十秒，讀到的數字仍混著先前的用量。要讀當下的用量，用 `top`：

```bash
top -l 2 -s 3 -n 10 -stats pid,command,cpu -o cpu
```

`-l 2` 取樣兩次後結束，`-s 3` 是兩次之間隔 3 秒，`-n 10` 每次只列前 10 個程序，`-stats` 指定要印的欄位，`-o cpu` 依 CPU 排序。`top` 的 `%CPU` 是拿前後兩次取樣相減算出來的，第一次取樣沒有前一次可以減，那一份表的 `%CPU` 全是 0.0；所以讀第二份表，也就是第二個以 `PID` 開頭的表頭底下那一段。`COMMAND` 欄超過 16 個字元會被截斷。這次重啟之後的第二份表裡，`WindowServer` 是 45.6，`ControlCenter` 不在前 10 名。

## 卡住時的呼叫堆疊：系統的診斷報告與 sample

主執行緒卡在哪段程式，要看它的呼叫堆疊。想回報給 Apple、或想知道同一個程序是不是一再卡在同一處時，有兩個來源：系統自己留下的診斷報告，以及在重啟之前用 `sample` 取樣。

macOS 在程序一段時間內的 CPU 用量超過系統訂的上限時，會自動寫一份診斷報告到 `/Library/Logs/DiagnosticReports/`，檔名是 `<程序名>_<日期時間>_<電腦名稱>.cpu_resource.diag`；「主控台」App 左側的「診斷報告」列出同一批檔案。報告在程序重啟之後仍然留著，所以事後才想到要查也來得及：

```bash
ls -l /Library/Logs/DiagnosticReports/ | grep -i ControlCenter
```

這次的事件之後查到一份 11 月 15 日的報告（兩天前），開頭幾行：

```text
Command:          ControlCenter
PID:              495
Event:            cpu usage
CPU:              90 seconds cpu time over 177 seconds (51% cpu average), exceeding limit of 50% cpu over 180 seconds
```

`PID` 是 495，跟 11 月 17 日卡住的是同一個程序，代表它兩天前就有過一段三分鐘平均 51% 的 CPU 用量，超過系統訂的上限（180 秒內 50%）。報告裡的 `Heaviest stack` 是取樣次數最多的那一串呼叫，讀法跟下面 `sample` 的報告相同。

系統沒有留下報告，或想要卡住當下的完整呼叫堆疊時，在 `killall` 之前先取樣一次：

```bash
sample ControlCenter 5 -file ~/Desktop/controlcenter-sample.txt
```

`sample` 每隔 1 毫秒記錄一次目標程序每個執行緒的呼叫堆疊，第二個引數是取樣的秒數（不給時取樣 10 秒），`-file` 指定報告寫到哪裡（路徑換成自己要放的位置）。報告依執行緒分段，主執行緒那一段的標頭帶著 `com.apple.main-thread`；每一行開頭的數字是落在那一層呼叫的取樣次數。系統 App 的符號被移除，`ControlCenter` 自己的函式在報告裡印成 `???  (in ControlCenter)` 加上位址。

這次處理時沒有先取樣，卡住狀態下的報告沒有取得。下面這段是重啟之後、程序正常時實跑 1 秒的主執行緒（節錄，866 次取樣）：

```text
866 Thread_60877305   DispatchQueue_1: com.apple.main-thread  (serial)
+ 866 start  (in dyld) + 2840
+   866 ???  (in ControlCenter)  load address 0x10486c000 + 0x6faf0
+     866 NSApplicationMain  (in AppKit) + 888
+       866 -[NSApplication run]  (in AppKit) + 480
+         866 -[NSApplication(NSEventRouting) _nextEventMatchingEventMask:untilDate:inMode:dequeue:]  (in AppKit) + 688
+           866 _DPSNextEvent  (in AppKit) + 660
...
+                       866 __CFRunLoopServiceMachPort  (in CoreFoundation) + 160
+                         866 mach_msg  (in libsystem_kernel.dylib) + 24
```

正常而閒著的主執行緒，取樣全部停在 `mach_msg`，而緊接在它上面的是 `__CFRunLoopServiceMachPort`：主執行緒的事件迴圈在等下一個事件，有事件進來就會處理。所以「停在 `mach_msg`」本身不代表卡住，判讀看的是呼叫鏈最底下停在哪裡、以及緊接在上面的是誰。

11 月 15 日那份診斷報告的 `Heaviest stack`（節錄，18 次取樣）是空轉的實例：

```text
18  _DPSNextEvent + 660 (AppKit)
...
11  __CFRunLoopDoTimers + 356 (CoreFoundation)
...
11  __NSFireDelayedPerform + 372 (Foundation)
11  -[NSStatusItem _updateReplicantsUnlessMenuIsTracking:] + 96 (AppKit)
11  -[NSStatusItem _updateReplicants] + 172 (AppKit)
4   -[NSStatusItem _updateReplicant:] + 1360 (AppKit)
4   -[NSView layoutSubtreeIfNeeded] + 96 (AppKit)
```

它跟閒著的主執行緒一樣經過 `_DPSNextEvent`，差別在事件迴圈接著做的是 `__CFRunLoopDoTimers`（執行到期的計時器），計時器呼叫的是更新選單列圖示複本（`_updateReplicants`）與版面配置（`layoutSubtreeIfNeeded`），最底下是計算，沒有停在等待的系統呼叫上。三種形態的讀法因此是：

- **閒著**：最底下是 `mach_msg`，緊接在上面的是 `__CFRunLoopServiceMachPort`。
- **空轉**：最底下是計算的函式（版面配置、繪圖、`???  (in ControlCenter)`），取樣次數集中在同一棵子樹；上面經過 `_DPSNextEvent` 與計時器也一樣是空轉，因為事件迴圈正忙著執行計時器的工作，沒有回去取下一個事件。
- **等待**：最底下是 `mach_msg`、`__psynch_mutexwait` 這類等待的系統呼叫，而緊接在上面的是 App 或框架自己的呼叫（例如同步等另一個程序回覆的 `xpc_connection_send_message_with_reply_sync`），不是 `__CFRunLoopServiceMachPort`。這一種的讀法從前兩種的對照推論，這次沒有看到等待的實例。

`man sample` 寫明它每次取樣時暫停目標程序、記錄完再讓它繼續。從機制推論，暫停的時間只有記錄一次堆疊那麼短，程序已經沒有回應時，使用者感受不到差別。

## 重啟單一程序、登出與重新開機的取捨

結束單一程序的影響範圍是那個程序本身：重啟 `ControlCenter` 只影響選單列上它畫的那些圖示與控制中心面板，其他 App、未存檔的文件、終端機裡跑著的工作都不受影響。重新開機也能讓 `ControlCenter` 恢復，因為它會在登入時重新啟動；代價是所有程序一起結束，要重開每一個 App、重建每一個工作階段。在已經從 `ps` 指認出卡住的程序、而且確認它由 `launchd` 用 `KeepAlive` 看管的情況下，重開機對這個程序的效果是讓它從頭啟動一次，而重啟這個程序已經得到同樣的效果，多付出的只有其他程序一起結束的代價。這跟殭屍程序那一篇的判斷是同一個形狀：已經指認出要處理的程序時，重新開機是〈回收格位的手段〉裡「終止父程序」的高成本超集（[殭屍程序與使用者程序上限：程序表格位的配置與回收](../macos_process_limit_zombie_reaping/)）。

重啟一個程序有沒有用，跟 `ps` 與呼叫堆疊判出的形態有關。空轉時，讓主執行緒停不下來的狀態在這個程序自己的記憶體裡，重啟之後新的程序從頭開始，那份狀態跟著消失，所以重啟多半有效，除非觸發它的條件（例如某個選單列項目）在外面持續成立。等待時，主執行緒等的是另一個程序或資源，重啟只換掉等待的一方；被等的那一方還沒恢復時，新的程序很快又會等在同一處。`sample` 看得出主執行緒在等哪一類呼叫，看不出對方是哪一個程序，所以等待形態重啟之後很快又卡住時，歸到下面「重啟之後很快又卡住」那一種情形。

重啟一個程序與重新開機之間還有登出再登入：它結束整個圖形介面的登入工作階段（包括 `WindowServer` 與全部的 LaunchAgent，`ControlCenter`、Dock、Finder 都在內），再重新啟動它們，不重新啟動核心與系統層的服務。代價是這個使用者的所有 App 都要重開，但不必等整台機器重開。

下列情形要考慮登出再登入或重新開機：

- **重啟之後很快又卡住**：同一個程序在幾分鐘到幾小時內又回到高 CPU 或沒有回應，代表讓它卡住的條件在重啟之後仍然成立（這次沒有遇到）。這次那份診斷報告的熱點在更新選單列圖示的複本（`_updateReplicants`），複本是畫在其他螢幕選單列上的那一份，所以這台接了兩個螢幕的環境可能跟它有關；只有一份報告，這是推論。遇到重複卡住時，拔掉第二個螢幕再觀察一段時間，是驗證這個推論的對照。登出再登入重置了整個工作階段裡程序之間的狀態，重新開機另外重置了系統層的服務，兩者都比重啟一個程序完整。重開機之後仍然重現時，比對幾次 `sample` 的報告，主執行緒是否每次都停在同一串呼叫；同一串就是一個可以回報給 Apple 的穩定現象，系統更新之後再觀察一次是否還重現。
- **異常的不只一個程序**：`ps` 依 CPU 排序時有好幾個系統程序同時異常，或等待游標出現在很多 App 上，成因可能在它們共用的資源（記憶體不足、磁碟、`WindowServer` 本身）；結束其中一個程序之後，其他 App 仍然沒有回應。`WindowServer` 本身異常時先試登出再登入，它是這個工作階段的一部分。
- **要結束的系統元件沒有被看管**：Apple 的系統元件在 `launchctl list` 找不到、或它的 plist 沒有 `KeepAlive`，結束之後不會自動回來，而它又是登入工作階段要用的元件時，登出再登入或重新開機讓它照正常順序啟動。第三方 App 不在此列，照〈選單列圖示的擁有程序〉寫的方式自己再打開就好。

這次不屬於上面任何一種情形：`ps` 裡異常的只有 `ControlCenter` 一個程序，它由 `KeepAlive` 看管，重啟之後 `ps` 上的空轉形態消失，寫完這篇之前也沒有再出現。重啟之前它連續執行了十一天、`%MEM` 是 4.4，重啟之後是 0.3，而兩天前它已經有過一段高 CPU；只有這一個程序的這幾個數字，不足以推出開機越久越容易卡住，所以這篇不把定期重新開機寫成預防的做法。
