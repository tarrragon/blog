---
title: "Zellij session 生命週期：常駐、注入、attach / detach"
date: 2026-07-08
draft: false
description: "要用 CLI 管理 zellij session（建背景常駐 session、從外部注入指令、斷線後 attach 接回、清理），特別是把長任務留在遠端跑時回來讀"
tags: ["zellij", "terminal", "session", "cli", "remote"]
---

Zellij 的 session 是讓工作獨立於連線存活的單位：session 常駐在 zellij server（一個背景 daemon）、你的連線只是 attach 上去看，連線斷了 session 與裡面跑的任務不受影響。本文整理 session 生命週期的 CLI 操作——建立、背景常駐、從外部注入指令、列舉、attach / detach、清理——這些是把長任務交給遠端機器無人值守跑的地基。

本文承接 [終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/) 的多工器分類。範圍上跟兩篇既有的 zellij 文互補：session 內部單一 pane 的佈局 / 讀取 / resize 見 [Zellij 多終端機操作指南](/linux/tools/cli/zellij-pane/)、把 session 分享給瀏覽器連線見 [Zellij Web Client 外網連線教學](/linux/tools/cli/zellij-remote-web-client/)、session 持久化的跨工具通用概念見 [tmux 基礎](/linux/tools/cli/tmux-persistence-and-basics/)。

## session 活在 server、跟連線解耦

session 生命週期的核心性質是它跟連線分離：`zellij` 第一次啟動 session 時會拉起一個常駐的 server 行程，session 的狀態（pane 佈局、跑著的程序、輸出）活在那個 server 裡，不在你的終端連線裡。所以連線斷開（SSH 掉線、手機切網路、關掉 app）只是把「顯示」拿掉，server 端的 session 照常運行。這是後面所有操作的前提：管理 session 等於管理那個 server 裡的一組常駐工作環境，attach 只是接上去看它。

一個直接的推論是「session 存在」跟「你連上去」是兩件可以分開的事——下一段的背景建立就是把這兩件事拆開。

## 建 session：連入即建 vs 背景常駐

建 session 有兩個入口，差別在建完要不要立刻 attach。

| 指令                      | 行為                                          | 適用                                |
| ------------------------- | --------------------------------------------- | ----------------------------------- |
| `zellij attach -c <name>` | session 不存在就建、並立刻 attach 進去        | 互動：連進來就要進工作環境          |
| `zellij attach -b <name>` | session 不存在就在背景建、detached、不 attach | 腳本 / 開機：先把環境備好、之後再連 |

`-c`（`--create`）是日常互動的入口：連進遠端機器打 `zellij attach -c work`，有 `work` 就接回、沒有就建一個並進去。

`-b`（`--create-background`）建一個背景 detached session、不把你拉進去。它的價值是把「session 存在」跟「人連上去」解耦：可以在開機腳本或登入流程裡先把工作 session 備好、裡面甚至已經起好任務，等你（或另一台裝置）之後再 attach 上去看。遠端無人值守的情境常從這裡起手——環境先常駐、連線是後來的事。

## 從外部對 session 注入指令

不必先 attach 就能把指令送進一個已存在的 session，用 `--session` 指定目標：

```bash
# 在指定 session 開一個新 pane、跑一條長任務
zellij --session work run -- bash -c 'while true; do date +%T >> ~/heartbeat.log; sleep 1; done'

# 送一個動作給指定 session（例如新開分頁、切換佈局）
zellij --session work action new-tab
```

`run` 在目標 session 裡開一個新 pane 執行指定命令、回傳該 pane 的 ID；`action` 送一個編輯 / 導航動作。這條路的用途是腳本化：一個部署腳本可以先 `attach -b` 建背景 session、再用 `--session ... run` 把服務、監控、長任務逐一丟進去，全程不需要一個互動終端 attach 在上面。把任務丟進常駐 session（而非直接跑在 SSH shell 裡）也是斷線存活的前提——直接掛在 SSH 前景的程序會隨連線斷掉被 SIGHUP 殺掉、跑在 session 裡的才活得過斷線。

## 列舉、attach、detach

`zellij ls`（`list-sessions`）列出目前所有 session 與狀態（建立多久、是否 exited）：

```bash
$ zellij ls
work [Created 18s ago]
```

`zellij attach <name>` 接上一個已存在的 session。detach（離開但讓 session 繼續跑）有兩條路：互動上進 session 模式後按 detach（預設鍵位是 `Ctrl+o` 再按 `d`、但 zellij 的 keybind 常被自訂、以你的 `config.kdl` 為準）；而**直接關掉連線本身就是一種 detach**——因為 session 活在 server、連線消失不影響它。

斷線 / detach 後任務仍在跑，判讀方法是看輸出的連續性：讓 session 裡的任務每秒寫一筆帶時間戳的紀錄、斷線一段時間再 attach 回去，若時間戳連續無斷檔，就證明任務在沒有連線的期間持續執行。這個「用輸出連續性驗證未中斷」是判斷 session 是否真的獨立於連線存活的可靠訊號。

## 清理與已知邊界

`zellij delete-session <name>` 刪除一個 session；加 `--force` 連還在跑的 session 也一併砍掉：

```bash
$ zellij delete-session work --force
Session: "work" successfully deleted.
```

一個要記成已知邊界、而非除錯項的行為：session 活在記憶體裡的 server 行程，**機器重開機後 session 全部消失**。這是預期的——重開機後要重建 session（或由開機腳本 `attach -b` 自動重建），不是「session 壞了」。把它列為已知邊界，除錯時就不會把「重開機後 session 不見」當成故障去查。

## 連入即 attach 的收斂

日常常把「連進遠端機器」跟「進工作 session」收斂成一步：在登入 shell 尾端（`.zshrc` / `.bashrc`）加 `zellij attach -c work`，SSH 進來就自動落在名為 `work` 的常駐 session、有就接回沒有就建。這讓遠端機器對你永遠呈現同一個持續累積的工作環境、而不是每次連進來一個空 shell。

## 除錯判讀 / tripwire

attach 不到預期的 session、或「任務好像不見了」時，最常見的原因是 session 名稱不一致：`attach -c` 對一個拼錯的名稱會**靜默開一個新的空 session**（因為 `-c` 的語意就是「不存在就建」），看起來像原本的任務消失了、其實任務還活在原本正確名稱的 session 裡。先 `zellij ls` 看實際有哪些 session、確認自己 attach 到的是不是同一個，就能區分。以 `zellij ls` 的輸出為權威狀態、不要靠記憶認定 attach 到了哪個 session。

## 下一步路由

- session 內單一 pane 的佈局 / 讀取 / resize：[Zellij 多終端機操作指南](/linux/tools/cli/zellij-pane/)
- 把 session 分享給瀏覽器連線的協作者：[Zellij Web Client 外網連線教學](/linux/tools/cli/zellij-remote-web-client/)
- session 持久化的跨工具通用概念（含 tmux 對照）：[tmux 基礎](/linux/tools/cli/tmux-persistence-and-basics/)
- 這些 session 操作在遠端 agent 工作機的實作實例（背景 session + 注入任務 + 斷線復原）：[遠端 agent 工作機實作記錄](/linux/tools/remote/agent-workstation-vm-handson/) 的 Step 5
