---
title: "程序、服務與狀態怎麼判"
date: 2026-07-02
description: "要判斷一個程式活著沒、某個系統服務現在由誰提供、桌面 session 有沒有被鎖、或終端機多工器的 session 還在不在時，用對的權威來源而不是靠畫面或猜的名字"
weight: 4
tags: ["linux", "process", "systemd", "debugging"]
---

判斷「某個東西現在是什麼狀態」——程式活著沒、服務由誰提供、螢幕鎖了沒、session 還在不在——是除錯裡最常做、也最常判錯的一步。判錯多半不是工具不對，是問錯了來源：用一個猜的名字去掃行程、用畫面有沒有反應去推服務狀態、用畫面上有沒有某個元素去斷定 session 狀態。這篇把幾個常見的狀態判斷，對到它們各自的權威來源與正確工具。

底層的心法（讀權威狀態、不靠肉眼）見 [診斷心法](../diagnosis-read-authoritative-state/)，這篇是它在「程序 / 服務 / 狀態」這一類的具體招式。

## 程式活著沒：比對正確的行程名

判斷一個程式在不在，行程表是權威來源，`pgrep` / `ps` 是對的工具，但成敗在於**比對正確的行程名**（comm，行程表裡記的執行檔短名，可從 `/proc/<pid>/comm` 看）。一個實際的坑：某個桌面 shell（畫桌面 UI 的圖形程式，不是 bash/zsh 那種命令列 shell）的可執行檔叫 `quickshell`，但透過名為 `qs` 的 symlink 啟動時，它在行程表裡的 comm 是 `qs`。這時 `pgrep quickshell` 找不到，很容易誤判成程式掛了、甚至誤觸「重啟」而引發更大的問題，實際上它以 `qs` 這個名字好好跑著。

可靠的做法：

- 先確認實際的 comm 名：`ps -eo pid,comm | grep -i <關鍵字>`，或看你啟動它的實際指令。
- 用精確比對：`pgrep -x <comm>`（`-x` 要求完全相符），或 `pgrep -af <pattern>` 連完整命令列一起比對，避免被 symlink 名 / 縮寫名騙。
- 另一個 comm 的坑：kernel 把 comm 截在 15 字元（`TASK_COMM_LEN`），名字超過 15 字的程式用 `pgrep -x <完整長名>` 反而 miss——這時改用 `pgrep -af <pattern>` 比對完整命令列。
- 別用一個「你以為的名字」掃過去就下生死結論——行程表沒騙你，是查詢條件寫錯。

## 服務由誰提供：問註冊表

「某個系統服務現在由哪個程式在提供」，權威來源是服務註冊，不是畫面。桌面服務多半註冊在 **D-Bus**（Linux 桌面的行程間訊息匯流排）上：一個服務用一個名字掛在上面，而**同一個名字同一時間只能被一個行程擁有**。以桌面通知為例，`org.freedesktop.Notifications` 這個 D-Bus 名同一時間只有一個擁有者——兩個通知 daemon（例如 mako 跟某個桌面 shell 內建的通知服務）不能共存，誰先註冊誰佔著，後者只能等前者退出。

想知道現在是誰接管，查註冊表而不是送一則通知看畫面：

```bash
# 查 org.freedesktop.Notifications 目前被哪個連線擁有
owner=$(busctl --user call org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus GetNameOwner s org.freedesktop.Notifications | awk '{print $2}' | tr -d '"')
# 把那個連線換算成 PID，再看行程名
pid=$(busctl --user call org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus GetConnectionUnixProcessID s "$owner" | awk '{print $2}')
ps -o comm= -p "$pid"
```

停掉舊 daemon 前擁有者是舊的、停掉後換成新的，就確認接管成功。這比「送通知看畫面有沒有跳」可靠——畫面沒跳可能是勿擾模式吃掉、可能根本沒送出，畫面反應不等於服務歸屬。切換兩個搶同一服務名的 daemon 時，這也解釋了為什麼「新的裝了卻沒作用」：舊的還佔著名字，新的靜默註冊失敗（通常只在它的 log 留一行 warning），得先停掉舊的。

## 桌面 session 有沒有被鎖：認清是哪一層的鎖

判斷一個圖形 session 有沒有被鎖，最容易被畫面帶偏，因為「畫面上有密碼框」很有說服力、卻不等於 session 真的被鎖（現代桌面 shell 的儀表板常內嵌鎖屏樣式的 widget）。而且鎖有不同層，查錯層會得到誤導的答案。

關鍵是分清兩種鎖：

- **logind 層的鎖**：systemd 登入管理的 session 鎖，權威狀態是 `loginctl show-session <id> -p LockedHint`。
- **Wayland 合成器層的鎖**：走 `ext-session-lock` 協議、由**合成器**（compositor，Wayland 下負責把各視窗合成到螢幕、管輸入輸出的核心程式，約當 X11 時代的視窗管理器加顯示伺服器；Hyprland、Sway 等都是）管的鎖，跟 logind 是獨立機制。這種鎖 `loginctl` 的 `LockedHint` **查不到**——不是沒鎖，是查錯層。（用 GNOME / KDE 的鎖屏走的機制不同，以下的 `ext-session-lock` 判法與復原針對 wlroots 系的 Wayland 合成器。）

所以「`loginctl` 沒有 `LockedHint`、`pgrep` 找不到獨立鎖屏程式」不足以斷定「沒鎖」：合成器層的鎖不歸 logind、而鎖屏畫面可能由 shell 主程式在自己行程內畫（沒有獨立可執行檔可抓）。這種情況真正的權威來源是那個 shell 自己的 log（有沒有載入鎖屏模組、idle 計時器有沒有觸發鎖定），或直接看 compositor 的 session-lock 狀態。判鎖看合成器 / shell 的 log，不是 `loginctl`、更不是畫面有沒有密碼框。

### 鎖屏程式死掉造成的死局與復原

`ext-session-lock` 有一個安全設計：持鎖的鎖屏程式若在鎖定狀態下崩潰 / 被中止，compositor **會保持鎖定**、不會因為鎖屏程式沒了就解鎖（否則殺掉鎖屏程式就成了繞過鎖的漏洞）。表現是畫面卡在「鎖屏程式已死」的安全提示。復原要從另一個 VT 或 SSH 用 `hyprctl keyword misc:allow_session_lock_restore 1` 允許新鎖屏 client 接管、再 `hyprctl dispatch exec hyprlock` 起一個接管後輸密碼解鎖。完整機制、兩層鎖的關係、各 compositor 的差異，見 [Wayland Session Lock 卡](/linux/dotfile/knowledge-cards/session-lock/)。

診斷紀律：**測鎖屏、或 `pkill` 一個持鎖的鎖屏程式時，要預期它把 session 卡在鎖定——這是協議的安全設計，不是 bug。** 自動化 / 無人值守流程尤其要避免在持鎖狀態下殺鎖屏程式。

## 終端機多工器的 session 還在不在

用 zellij / tmux 這類多工器跑遠端長任務時，判斷「重連後那個 session 還在不在」的權威來源是多工器自己的 session 列表，不是「我 SSH 斷了所以應該還在吧」的假設。`zellij ls`（或 `tmux ls`）會列出 session 與狀態：多工器是常駐在遠端的程序，SSH 斷不影響它，所以只要那台機器沒重開，`attach` 就能接回去；但如果機器重開過、或那個 session 因為資源不足（例如磁碟滿觸發的連鎖）被殺，列表會顯示它已 `EXITED` / 不存在，這種接不回去。

這裡有個順序上的紀律：**當一個 session 可能已經死掉、而它裡面跑的任務有你在意的產出時，先確認產出有沒有被安全保存，再處理 session。** 例如任務是在改 git repo，先 `git -C <repo> status` 跟 `git log @{u}..`（本地有、遠端沒有的 commit）確認有沒有沒推送的東西、把該推的推掉，再去 `zellij delete` 清死 session。搞反順序、先清了 session，可能連帶失去唯一還記得那些改動的地方。權威狀態（git 的推送狀態、多工器的 session 列表）先讀清楚，再動手。

## 判讀路由

- 判程式活著 → `pgrep -x <正確 comm>` / `pgrep -af <pattern>`，先確認實際 comm 名，別用猜的名字。
- 判服務歸誰 → `busctl` 查 D-Bus name 擁有者 → 換算 PID → comm，不看畫面反應。
- 判 session 鎖沒鎖 → 分清 logind 層（`loginctl LockedHint`）vs 合成器層（`ext-session-lock`，看 compositor / shell log），不看畫面有沒有密碼框。
- 鎖屏程式死掉卡住 → `allow_session_lock_restore` + 重起鎖屏程式接管解鎖。
- 判多工器 session 存活 → `zellij ls` / `tmux ls`；可能已死且有在意的產出時，先確認產出已保存 / 已推送再清 session。

判不準時，[診斷心法](../diagnosis-read-authoritative-state/) 的四步（描述症狀、定位權威來源、用對工具讀、矛盾時信權威）是通用的回退。
