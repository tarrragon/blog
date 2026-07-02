---
title: "Wayland Session Lock（鎖屏安全狀態）"
date: 2026-07-01
description: "hyprlock / swaylock 畫面卡住、pkill 後進不了桌面、或要在 VM / 自動化環境測試鎖屏時回來讀"
weight: 15
tags: ["dotfile", "hyprland", "wayland", "security", "knowledge-cards"]
---

## 鎖屏是 compositor 持有的安全狀態

Wayland 下的 compositor（如 Hyprland、Sway）同時管理視窗排列與畫面輸出。鎖屏工具（Hyprlock、Swaylock）一旦啟動，桌面的「鎖定」狀態就由 compositor 透過 ext-session-lock-v1（Wayland 生態系的跨 compositor 鎖屏協議）持有。解鎖的正常動作是鎖屏 client 通過認證後呼叫 `unlock_and_destroy`（協議定義的 request），compositor 收到這個信號才釋放鎖定。

這個責任邊界在自動化測試、VM 演練、遠端操作時最容易出事，因為這些情境常用「殺 process」當「關掉一個東西」的通用手段。殺掉鎖屏 client 跳過了認證，compositor 不會釋放鎖——畫面會卡在失效保護狀態而非回到桌面。

## logind 提示與 compositor 鎖的值可以不一致

鎖屏狀態牽涉兩個獨立的層，觸發方向和持有者不同：

| 層            | 持有者             | 查看方式                                   | 語意                                        |
| ------------- | ------------------ | ------------------------------------------ | ------------------------------------------- |
| logind 會話鎖 | systemd-logind     | `loginctl show-session <id> -p LockedHint` | 會話的鎖定提示，給登入管理器 / 螢幕保護程式 |
| compositor 鎖 | Wayland compositor | 畫面是否進得去、鎖屏 surface 是否在最上層  | 實際擋住畫面的那層                          |

`loginctl lock-session` 走 logind 層觸發鎖屏，鎖屏 client 收到信號後啟動、再向 compositor 取得 session lock。觸發方向是 logind → client → compositor；持有與強制執行方向是 compositor → 畫面。兩者方向相反，正好印證兩層是獨立的。

實測會遇到 `LockedHint=no`（logind 層說沒鎖）但畫面仍進不去——因為擋住畫面的是 compositor 的 ext-session-lock，跟 logind 提示是兩回事。判斷畫面進不進得去，看 compositor 層，不看 logind 層。

## 鎖屏 client 非正常結束時的失效保護

鎖屏 client 在持有鎖的狀態下死掉（被 `kill`、crash），compositor 沒有收到認證通過的信號，只能維持鎖定並顯示失效保護畫面。Hyprland 的失效保護畫面會直接給恢復指令：

```text
hyprctl --instance 0 'keyword misc:allow_session_lock_restore 1'
hyprctl --instance 0 'dispatch exec hyprlock'
```

`allow_session_lock_restore` 允許新的鎖屏 client 接管既有的鎖（否則新 client 會因「已經鎖了」被拒）。接管後是乾淨的鎖屏 prompt，用密碼正常解鎖。

備好 restore 路徑時，殺掉無回應的鎖屏 client 是合理操作——問題不在「殺」、在「以為殺完就回桌面」。restore 的前提是有另一個可操作的 session：另一個 TTY 或 SSH 連線。ext-session-lock 的安全語意允許 compositor 攔截 VT 切換快捷鍵（`Ctrl+Alt+Fn`），遇到 TTY 切不過去的情況，SSH 是替代救援通道（事先配好 SSH server，見[常見故障場景與恢復操作](/linux/dotfile/07-desktop-maintenance/common-failures-recovery/)的 GPU hang 段）。

## 判讀與操作

- **判讀鎖定狀態**：`loginctl show-session $(loginctl show-user $USER -p Display --value) -p LockedHint` 查 logind 層；compositor 層看畫面能否操作。兩層不一致時以 compositor 層為準。
- **正常解鎖**：通過鎖屏 client 的認證（密碼 / 指紋），client 呼叫 `unlock_and_destroy`，compositor 釋放鎖。
- **失效保護恢復**：從另一個 TTY 或 SSH 執行 `hyprctl --instance 0 'keyword misc:allow_session_lock_restore 1'` + `hyprctl --instance 0 'dispatch exec hyprlock'`，重新拉起鎖屏 prompt 後認證解鎖。
- **自動化流程的代價**：啟動鎖屏後，畫面會留在鎖定狀態直到有人通過認證。自動化測試若會觸發鎖屏，要把「需人工解鎖」算進代價。
- **診斷路由**：「畫面卡住 / 螢幕鎖了沒」當成一般 Linux 狀態判讀問題（跟判程式活著、判服務歸屬同類）時，見[程序、服務與狀態怎麼判](/linux/debug/process-service-state-diagnosis/)——它把「判 session 有沒有被鎖」放進「讀權威狀態、別看畫面猜」的通用診斷紀律裡。
- **延伸閱讀**：鎖屏的視覺配置（背景、輸入框、時鐘 label）見[配色系統、鎖屏與 GTK 主題](/linux/dotfile/06-rice-design/color-system-theming/)的 Hyprlock 段；桌面故障恢復流程見[常見故障場景與恢復操作](/linux/dotfile/07-desktop-maintenance/common-failures-recovery/)。持鎖的那個 compositor 到底是什麼、還握著哪些系統狀態，見 [Compositor 術語卡](/linux/dotfile/knowledge-cards/compositor/)。

## 邊界條件

正常認證解鎖（走 `unlock_and_destroy`）後鎖屏 client 結束，compositor 已回到非鎖定狀態，不觸發失效保護。失效保護只在「持鎖中非正常結束」時出現。

Sway/swaylock 在 client 死掉時沒有畫面上的恢復提示（不像 Hyprland 會印指令），得預先知道走 TTY 或 SSH 執行 restore。「鎖是 compositor 持有、解鎖要認證」是 ext-session-lock 協議層的共通約束；失效保護的具體呈現方式因 compositor 而異。
