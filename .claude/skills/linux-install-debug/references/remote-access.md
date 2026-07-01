# 遠端連線與終端機問題

SSH 連線本身、以及「你的終端機 ↔ 遠端 session」之間那條連線的狀態問題。判斷對是哪一層，修復很直接。

## SSH 連不上

先分「網路層 vs 服務層」，用症狀分流：

- **TCP timeout（連 port 22 卡住無回應）** → 網路層或機器沒跑。查 `ip neigh`（目標 IP 若 `INCOMPLETE` = 鏈路層沒回應；`arp` 常沒裝）→ 見 [machine-unreachable](machine-unreachable.md)。
- **`Connection refused`** → 網路通、但沒服務在聽 22。去機器上 `systemctl status sshd`；沒裝 / 沒起就 `pacman -S openssh && systemctl enable --now sshd`。
- **`Permission denied (publickey)`** → key 沒對上。換帳號 + IP 直連走密碼繞過鎖死金鑰的別名：`ssh user@<IP>`；再重新佈 key。
- **`Host key verification failed`** → 目標身分變了（重裝 / 換機 / IP 重用）。`ssh-keygen -R <IP>` 清舊 host key 再連。

根因通則：SSH 的別名 / 金鑰 / `known_hosts` 都綁「特定機器身分」，換機 / 重裝 / DHCP 重配後別名會連錯或被擋 → 用帳號 + IP 直連確認，再更新別名。

## SSH 斷線後本機終端機噴亂碼 / 狂跳字元

症狀：本機終端機瘋狂輸出 `<數字;數字M` 之類序列，尤其動滑鼠時。**這是本機終端機被卡在滑鼠回報模式，不是遠端在打字。**

判讀：亂碼只在動滑鼠時出現、形如 `數字;數字M` → 滑鼠座標回報。成因：遠端全螢幕程式（TUI / 多工器）開了滑鼠追蹤，SSH 硬斷時來不及關閉，本機終端機停在回報模式。

修（跟遠端無關）：

- 最快：開新終端機分頁 / 視窗（模式是該 session 狀態，新視窗乾淨）。
- 救現有：滑鼠移開別動 → 盲打 `reset` + Enter。
- 還沒清：`printf '\033[?1000l\033[?1002l\033[?1003l\033[?1006l'`。

同類：alternate screen 沒還原（畫面凍結 / 清空）→ `reset`。通則：SSH 硬斷後本機終端機異常，先懷疑「對端來不及還原終端機模式」，`reset` 或開新視窗，別去重連遠端。

## 遠端打字亂碼 / 重複 / 位置錯亂

分兩層排除（症狀相似、修法不同）：

- **locale（編碼寬度）**：本機把 `LC_CTYPE` 帶進遠端、遠端沒對應 locale → 退回 POSIX，行編輯對多位元組寬度判斷錯 → 輸入重複 / 錯位。查 `locale` + `locale -a`。修：遠端明確設 `LANG` / `LC_CTYPE` 到實際存在的 UTF-8 locale。
- **terminfo（繪製指令）**：本機 `TERM`（如 `xterm-ghostty`）遠端無對應條目 → 清行 / 移游標 / 重繪錯亂。查 `echo $TERM` + `infocmp $TERM`。修：`infocmp -x $TERM | ssh <遠端> 'tic -x -'`。

分法：查 `locale` vs 查 `$TERM`+`infocmp`。

## 從 SSH 操控遠端圖形桌面

兩類界線：

- **圖形程式找不到 display**：SSH shell 無圖形環境變數。對著遠端在跑的 Wayland session 操作要補：`XDG_RUNTIME_DIR=/run/user/<uid>`、`WAYLAND_DISPLAY=<socket 名，如 wayland-1>`、必要時 compositor 的 instance 變數（如 `HYPRLAND_INSTANCE_SIGNATURE`）與 `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/<uid>/bus`。值從 `/run/user/<uid>/` 或既有行程環境撈。補齊後可下 IPC、`grim` 截圖。
- **compositor 必須從實體圖形 VT 起、SSH pty 起不來**：Wayland compositor（Hyprland）需要圖形 VT 上的 logind seat + DRM master；從 SSH pty 起會 backend 建立失敗（如 `CBackend::create() failed`）。判讀訊號：從 SSH 起 compositor 報 seat / DRM / backend 錯。這不是設定問題，是資源在 SSH 這條連線不存在。

從 SSH 遠端回到圖形 VT（比在 VM 視窗跟 `Ctrl+Alt+Fn` 搏鬥穩定）：

- `sudo chvt <N>` 切目前顯示的 VT。
- 切過去空白 / 無登入提示 = 該 VT 沒 getty：`sudo systemctl start getty@tty<N>`（開機時常 `enabled` 但 `inactive`，autovt 沒觸發）。
- `sudo fgconsole` 確認前景 VT。
- 注意：VM 可能同時有序列主控台 + 圖形顯示兩個獨立輸出，`chvt` 只動圖形側；在 VM 軟體裡要切到 Display view 才看得到圖形桌面。

## 快速路由

| 症狀                                | 檢查                        | 動作                              |
| ----------------------------------- | --------------------------- | --------------------------------- |
| 本機終端機噴 `數字;數字M`、動滑鼠時 | 只在動滑鼠時 → 滑鼠回報模式 | `reset` / 開新視窗                |
| 遠端打字重複 / 錯位                 | `locale` vs `$TERM`+infocmp | 設 locale / `tic` 裝 terminfo     |
| 圖形程式 SSH 下找不到 display       | 有無 `WAYLAND_DISPLAY`      | 補圖形 env 變數                   |
| compositor SSH 起不來報 seat/DRM    | 是否從 SSH pty 起           | `chvt` + `getty@tty<N>` 回圖形 VT |
