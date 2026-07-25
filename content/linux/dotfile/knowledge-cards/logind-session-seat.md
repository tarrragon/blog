---
title: "logind Session 與 Seat（VT 與輸入權的持有者）"
date: 2026-07-03
description: "compositor 從 SSH 起不來報 seat / DRM 錯、想確認哪個 session 在 active VT、或 loginctl 輸出跟畫面狀態對不上時讀"
weight: 18
tags: ["dotfile", "linux", "systemd", "logind", "knowledge-cards"]
---

systemd-logind 是 systemd 的登入管理服務：追蹤每一次登入（session）、把實體輸入輸出裝置組成 seat、並依「哪個 session 在 active VT 上」決定誰拿得到顯示與輸入裝置的存取權——[Compositor](/linux/dotfile/knowledge-cards/compositor/) 就是這個存取權的典型使用者，得透過 logind 才拿得到 seat 與 DRM master。教材裡「為什麼不能從 SSH 跑桌面」「為什麼 loginctl 說沒鎖但畫面進不去」這兩類問題，根因都在這一層的概念。

## 概念位置

相關概念：[TTY](/linux/dotfile/knowledge-cards/tty/)（VT 是 seat 存取權的判定基準）、[Compositor](/linux/dotfile/knowledge-cards/compositor/)（透過 logind 取得 seat 與 DRM master 的程式）、[Session Lock](/linux/dotfile/knowledge-cards/session-lock/)（logind 鎖定提示與 compositor 鎖的分層）。

兩個核心名詞各承擔一個語意：

- **Session**：一次登入。從圖形 [VT](/linux/dotfile/knowledge-cards/tty/) 登入、從 SSH 連入、在另一個 tty 登入，各自是一個獨立 session。`loginctl list-sessions` 列出全部。
- **Seat**：一組綁在一起的實體裝置——螢幕、鍵盤、滑鼠。單人單機只有一個 `seat0`。`loginctl seat-status seat0` 看它掛了哪些裝置、哪個 session 是 active。

裝置存取權的發放規則是這張卡的重點：**只有掛在 seat 上、且位於 active VT 的 session，才拿得到 DRM master（顯示卡獨佔繪圖權）與 input 裝置**。[Compositor](/linux/dotfile/knowledge-cards/compositor/) 啟動時透過 libseat 向 logind 要 seat，SSH 連線的 session 是 pty（`tty` 指令回 `/dev/pts/N`）、不屬於 seat0，於是 compositor 的預設 backend 從 SSH 起會直接失敗、報 seat / DRM / backend 相關的錯——判讀與繞法（headless backend、回實體 VT 啟動）見[遠端連線與終端機問題](/linux/debug/ssh-and-terminal-troubleshooting/)。

判讀 seat 狀態的權威指令組：

```bash
tty                                # 現在這個 session 的終端機：/dev/tty1 是圖形 VT、/dev/pts/N 是 SSH
loginctl seat-status seat0         # seat0 的 active session 掛在哪個 tty
cat /sys/class/tty/tty0/active     # kernel 認定的實體 active VT
systemctl is-active getty@tty1     # 那個 VT 上有沒有 getty 給登入提示
```

實測有一個假象值得警惕：`loginctl` 可能把 seat0 掛在某個 pts session 上、看似持有 DRM master，但 pts 不在 active VT、KMS 照樣失敗——loginctl 的歸屬顯示跟「真的能畫」是兩回事，交叉比對 `tty` 與 `/sys/class/tty/tty0/active` 才定案。另一個常見狀態是 `getty@ttyN` 顯示 `enabled` 但開機後 `inactive`（logind 的 autovt 沒觸發）、VT 切過去一片空白沒登入提示，`sudo systemctl start getty@tty<N>` 補起來、`sudo chvt <N>` 切 active VT。

logind 也持有一個「session 鎖定提示」（`loginctl show-session <id> -p LockedHint`），它跟 Wayland compositor 的 `ext-session-lock` 鎖是獨立兩層——`LockedHint=no` 不代表畫面進得去。兩層的方向、持有者與判讀方式見 [Session Lock](/linux/dotfile/knowledge-cards/session-lock/)。
