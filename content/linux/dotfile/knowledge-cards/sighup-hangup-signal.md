---
title: "SIGHUP 與斷線即死"
date: 2026-07-08
description: "遠端跑的程序在 SSH 一斷就消失、想知道為什麼直接掛在連線上的任務活不過斷線、該把工作放哪一層時回來讀"
weight: 53
tags: ["linux", "remote", "process", "signal", "knowledge-cards"]
---

SIGHUP 是控制終端消失時，核心送給該終端前景程序群的掛斷訊號（hangup），預設動作是終止程序。SSH 連線斷掉時，遠端那個 shell 的控制終端跟著消失，掛在它前景的程序就收到 SIGHUP 被殺——這是「直接跑在 SSH shell 裡的長任務，連線一斷就死」的根因，也是為什麼長任務要放進獨立於連線的 session 層。這條連線本身為什麼會斷，見 [TCP 連線與漫遊](/linux/dotfile/knowledge-cards/tcp-connection-roaming/)。

## 概念位置

相鄰概念見 [TCP 連線與漫遊](/linux/dotfile/knowledge-cards/tcp-connection-roaming/)（連線本身怎麼斷）。

## 為什麼斷線會送 SIGHUP

終端程序（pty）有一組掛在它上面的前景程序。SSH 的遠端 shell 就跑在一個 pty 上。連線斷掉時這個 pty 被關閉，核心對還掛在上面的前景程序群發 SIGHUP，通知「你的控制終端沒了」。多數程序沒有自訂 SIGHUP 處理，就走預設——終止。所以 `ssh host 'long-task'` 或在互動 SSH shell 裡前景跑的迴圈，連線一抖就跟著消失。

## 讓程序活過斷線的兩條路

把工作跟連線的生命週期解耦，有兩種做法：

- **放進終端機多工器 session**（`tmux` / `zellij`）：session 常駐在遠端、有自己的 pty，SSH 斷了 session 不受影響，重連 `attach` 回到原狀。這是遠端長任務的標準做法（見 [zellij session 生命週期](/linux/tools/cli/zellij-session-lifecycle/)）。
- **切斷 SIGHUP 傳遞**：`nohup <cmd>`（忽略 SIGHUP）、`disown`（把 job 從 shell 的 job 表移除）、或 `setsid`（開新 session 脫離控制終端）。這些能讓單一程序活下來，但沒有 session 的重連、多 pane、狀態保留能力。

多工器是有狀態的工作環境、`nohup` 家族是單程序的救急，兩者解的是同一個 SIGHUP 問題、能力範圍不同。

## 判讀訊號

- **遠端任務在 SSH 斷線的當下消失、重連後不見** → 十之八九是前景程序吃了 SIGHUP。把任務移進多工器 session 即解。
- **想確認某程序會不會被 SIGHUP 殺** → 看它有沒有自訂 handler（`trap '' HUP` 之類）或用 `nohup` 起；沒有就走預設終止。

## 邊界

SIGHUP 的另一個慣例用途是「請 daemon 重讀設定」——`nginx`、`sshd` 這類長駐服務把 SIGHUP 接管成 reload（重讀設定不重啟）。同一個訊號在前景互動程序與 daemon 上語意不同：前者走預設的終止、後者由程式主動接管成「重載」。這張卡講的是前者（斷線殺前景任務）。系統層「服務怎麼被叫醒 / 重載」另見服務管理主題。
