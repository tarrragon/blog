---
title: "Shell Background Process（Shell 背景行程）"
date: 2026-05-12
description: "終端機 process 的前景 / 背景生命週期、訊號控制、找出佔用 port 的 process"
weight: 1
tags: ["llm", "knowledge-cards", "macos", "shell"]
---

Shell 背景 Process 的核心概念是「terminal 啟動的程式何時跟 shell 綁定、何時可以脫離、被 shell 用什麼方式管理」。本地 LLM 場景中、`ollama serve` 這類常駐 server 需要持續跑、放前景會把 terminal 卡住、放背景才能繼續打其他指令、或關掉 terminal 後讓服務改交給 [launchd service](/llm/knowledge-cards/launchd-service/) 接手。

## 跟其他概念的關係

Shell（zsh / bash）執行一個程式時、預設讓程式佔住 terminal、stdin / stdout / stderr 直接連到使用者眼前的視窗、稱為**前景 process**。指令尾巴加 `&` 改成**背景 process**、shell 立刻拿回 prompt 控制權、程式繼續跑但不佔住 terminal。背景 process 仍綁在當前 shell session、關掉 terminal 視窗時通常會被 SIGHUP 終止；要完全脫離 shell 生命週期、得改用 [launchd service](/llm/knowledge-cards/launchd-service/) 或 `nohup` / `disown` 等機制。

## 可觀察訊號與例子

shell 控制 process 的關鍵操作：

| 動作                | 指令 / 按鍵      | 效果                                 |
| ------------------- | ---------------- | ------------------------------------ |
| 前景跑              | `ollama serve`   | terminal 被卡住、看到 process stdout |
| 背景跑              | `ollama serve &` | 拿回 prompt、程式仍在跑              |
| 中止前景 process    | `Ctrl+C`         | 送 SIGINT、多數程式收到後優雅退出    |
| 暫停前景 process    | `Ctrl+Z`         | 送 SIGTSTP、process 進 stopped 狀態  |
| 列出當前 shell jobs | `jobs`           | 看 shell 管理的背景 / 暫停 job       |
| 把 job 拉回前景     | `fg %1`          | 1 號 job 變前景                      |
| 把暫停 job 改背景   | `bg %1`          | 1 號 job 改背景繼續跑                |

排錯常用的兩個工具（兩者跟 shell job 不直接相關、是 macOS 系統工具）：

| 指令                      | 用途                                                                         |
| ------------------------- | ---------------------------------------------------------------------------- |
| `lsof -i :11434`          | 找出哪個 process 在聽 11434 [port](/llm/knowledge-cards/port-and-localhost/) |
| `pkill -f "ollama serve"` | 用 pattern 匹配 process 命令列、送 SIGTERM 終止                              |
| `ps aux \| grep ollama`   | 列出所有跟 ollama 有關的 process                                             |

對 macOS 新手最常遇到的兩個事故：一個是「前景跑 server 後不知道怎麼脫身」、解法是 `Ctrl+Z` 暫停 + `bg` 改背景、或下次改用 `&` 啟動；另一個是「pkill 沒指定夠精確的 pattern、誤殺其他 process」、解法是先用 `ps aux` 加 `grep` 確認 PID 再 kill。

## 判斷條件與後果

前景、`&` 背景與 launchd service 的差別在 process 跟 shell session 綁得多緊，選哪一種看這個 server 要跑多久、是否要看到它的輸出：

- **前景跑時**，stdout 直接印在 terminal 上，log 一出來就看得到，適合 debug；代價是 terminal 被佔住。
- **用 `&` 放到背景時**，shell 拿回 prompt，process 仍綁在這個 shell session 上，關掉 terminal 視窗時通常隨 SIGHUP 終止。這適合只在 terminal 開著時才需要它的臨時場景；需要長期穩定的服務放在 `&` 底下，會在某次關視窗時停掉而沒有任何提示。
- **交給 [launchd service](/llm/knowledge-cards/launchd-service/) 時**，process 跟 shell session 完全脫鉤，關掉 terminal 不影響它，適合日常使用的常駐服務。

排錯時，`pkill -f` 用 pattern 比對整條命令列，pattern 不夠精確就會連其他 process 一起送 SIGTERM；所以 kill 之前，先用 `lsof` 查出佔著 port 的 process，再用 `ps aux` 加 `grep` 確認它的命令列與 PID。
