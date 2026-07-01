---
title: "遠端連線與終端機問題"
date: 2026-07-02
description: "SSH 連線斷掉後本機終端機卡住噴亂碼、遠端打字變亂碼、或想從 SSH 操控遠端圖形桌面卻起不來時，判斷是哪一層出問題並修復"
weight: 8
tags: ["dotfile", "linux", "ssh", "terminal", "debugging"]
---

遠端操作 Linux 時，很多問題出在「你的終端機」與「遠端 session」之間那條連線的狀態，而不在遠端那台機器本身。終端機被上一個程式留在奇怪的模式、字元編碼與終端機能力沒對上、或你想從一條純文字的 SSH 連線去驅動一個需要實體螢幕的圖形桌面——這些問題的共同點是：現象發生在連線的某一層，判斷對是哪一層，修復就很直接。

SSH「連不上」本身（`Permission denied`、`Host key verification failed`、`Connection refused`）的判讀與修復，見 [外部連入與無 key 的 bootstrap 路徑](../ssh-keyless-bootstrap/) 的重連段落。這篇處理的是「連上了、但終端機或 session 的狀態不對」的那些情況。

## SSH 斷線後本機終端機噴亂碼、狂跳字元

一個嚇人但無害的情況：SSH 連線被中斷後，你本機的終端機開始瘋狂輸出像 `<35;80;24M` 這樣的序列，尤其在你移動滑鼠時狂跳。這不是遠端機器在打字，是**你本機的終端機被卡在滑鼠回報模式**。

判讀關鍵在「什麼時候噴」：如果那串亂碼只在你移動滑鼠時出現、而且形如 `數字;數字M`，那就是滑鼠座標回報。成因是遠端跑的某個全螢幕程式（TUI、編輯器、終端機多工器）啟動時對終端機開了滑鼠追蹤模式，SSH 被硬斷時它來不及送出「關閉滑鼠模式」的序列就死了，於是你本機終端機還停在回報模式，滑鼠一動就把游標座標當輸入送進來。

修復是重置終端機的模式，跟遠端機器無關：

- 最快：開一個新的終端機分頁 / 視窗。模式是「那個終端機 session」的狀態，新視窗是乾淨的。
- 救現有視窗：先把滑鼠移開別動（洪流會停），盲打 `reset` 再 Enter，送出終端機重置。
- 若 `reset` 沒清掉，補送關閉滑鼠回報的序列：`printf '\033[?1000l\033[?1002l\033[?1003l\033[?1006l'`。

同一類的還有「alternate screen 沒還原」——遠端的全螢幕程式異常結束時，本機終端機可能卡在替代畫面緩衝區，看起來像畫面清空或凍結。`reset` 同樣能救。判讀通則：**SSH 被硬斷後本機終端機行為異常，先懷疑「對端程式來不及還原終端機模式」，用 `reset` 或開新視窗，而不是去重連遠端。**

## 遠端打字變亂碼、重複、位置錯亂

連上遠端後，如果互動式輸入變得不對——打一個字出現好幾個、游標位置錯亂、畫面重繪殘影——通常是兩層問題之一，判讀方式是分開排除。

第一層是**字元編碼（locale）**。從某些本機（例如 macOS）SSH 進 Linux 時，本機會把 `LC_CTYPE` 之類的變數帶過去；如果遠端沒有對應的 locale、就會退回 POSIX/C locale，讓終端機的行編輯（ZLE、readline）對多位元組字元的寬度判斷出錯，表現為輸入重複或錯位。判斷方式是在遠端 `locale` 看目前值、`locale -a` 看有沒有裝對應的 UTF-8 locale。修法是在遠端明確設好 `LANG` / `LC_CTYPE` 到一個實際存在的 UTF-8 locale，而不是讓它繼承一個遠端不認得的值。

第二層是**終端機能力資料庫（terminfo）**。你本機終端機的 `TERM` 值（例如某些新終端機用 `xterm-ghostty` 之類的自訂值）如果在遠端沒有對應的 terminfo 條目，遠端程式就不知道怎麼正確地清行、移動游標、重繪，畫面就會亂。判斷方式是在遠端 `echo $TERM` 看值、`infocmp $TERM` 看遠端認不認得。修法是把本機的 terminfo 條目送過去讓遠端安裝：`infocmp -x $TERM | ssh <遠端> 'tic -x -'`。

先分清是 locale 還是 terminfo，兩者症狀相似但修法不同：locale 是編碼寬度、terminfo 是繪製指令。查 `locale` 跟查 `$TERM` + `infocmp` 就能分開。

## 從 SSH 操控遠端的圖形桌面

想從一條純文字的 SSH 連線去操作遠端的 Wayland 圖形桌面（例如啟動應用、截圖、送 IPC 指令）時，會撞到兩類界線，判斷對是哪一類就知道怎麼繞。

第一類是**圖形程式需要知道連到哪個顯示**。SSH 進來的 shell 預設沒有圖形環境的環境變數，直接跑圖形程式會找不到 display。要對著遠端那個已經在跑的 Wayland session 操作，得補上它的環境變數：`XDG_RUNTIME_DIR`（通常 `/run/user/<uid>`）、`WAYLAND_DISPLAY`（socket 名，如 `wayland-1`）、必要時還有該 compositor 的 instance 變數與 `DBUS_SESSION_BUS_ADDRESS`。這些值可以從那個 session 的 runtime 目錄或既有行程的環境撈出來。補齊後，SSH 這條連線就能對遠端的圖形 session 下指令、截圖。

第二類是**有些東西必須從實體圖形終端機（VT）啟動，SSH 的 pty 起不來**。Wayland compositor（如 Hyprland）需要一個真正的圖形 VT 上的登入 session、拿到 DRM master 與 logind seat 才能啟動；從 SSH 的 pty 起它會直接失敗（例如報 backend 建立失敗）。這不是設定問題，是它需要的資源在 SSH 這條連線上根本不存在。判讀訊號：compositor 一啟動就報 seat / DRM / backend 相關的錯，而你是從 SSH 起的——那就是這個界線。

繞法是回到那台機器的實體圖形終端機去啟動 compositor，但「回到 VT」這件事也可以從 SSH 遠端做：

- `sudo chvt <N>` 從 SSH 切換那台機器目前顯示的虛擬終端機到第 N 個，比在虛擬機視窗裡跟宿主的 `Ctrl+Alt+Fn` 快捷鍵搏鬥穩定。
- 切過去卻是空白、沒有登入提示，通常是那個 VT 上沒有 getty 在跑：`sudo systemctl start getty@tty<N>`（開機時 `enabled` 但 `inactive` 是常見狀態，logind 的 autovt 沒觸發）。
- `sudo fgconsole` 確認目前是哪個 VT 在前景。

還有一個容易混淆的點：一台虛擬機可能同時有「序列主控台」跟「圖形顯示」兩個獨立輸出。在 guest 內 `chvt` 只切圖形那側，序列主控台看到的畫面不會變。如果你在虛擬機軟體裡看的是序列主控台，圖形桌面得切到顯示輸出那個 view 才看得到。判讀：切了 VT 但畫面沒反應，先確認你正在看的是哪個輸出。

## 判讀路由

遠端 / 終端機問題的分流：

- 本機終端機噴亂碼、只在動滑鼠時噴 → 滑鼠回報模式沒關（本機終端機狀態），`reset` 或開新視窗。
- 遠端打字重複 / 錯位 → 分 locale（查 `locale`）與 terminfo（查 `$TERM` + `infocmp`）。
- 圖形程式在 SSH 下找不到 display → 補 `WAYLAND_DISPLAY` / `XDG_RUNTIME_DIR` 等環境變數。
- compositor 從 SSH 起不來、報 seat/DRM 錯 → 它需要實體 VT，用 `chvt` + `getty@tty<N>` 回到圖形 VT 啟動。
- SSH 連不上（拒絕 / host key / refused）→ 見 [外部連入與無 key 的 bootstrap 路徑](../ssh-keyless-bootstrap/)。

判斷不出是哪一層時，回到 [診斷心法](../diagnosis-read-authoritative-state/)：先讀權威狀態（`locale`、`$TERM`、runtime 目錄、`loginctl`、`fgconsole`），不要從畫面現象猜。
