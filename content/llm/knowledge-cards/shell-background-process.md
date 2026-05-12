---
title: "Shell 背景 Process"
date: 2026-05-12
description: "終端機 process 的前景 / 背景生命週期、訊號控制、找出佔用 port 的 process"
weight: 1
tags: ["llm", "knowledge-cards", "macos", "shell"]
---

Shell 背景 Process 的核心概念是「terminal 啟動的程式何時跟 shell 綁定、何時可以脫離、被 shell 用什麼方式管理」。本地 LLM 場景中、`ollama serve` 這類常駐 server 需要持續跑、放前景會把 terminal 卡住、放背景才能繼續打其他指令、或關掉 terminal 後讓服務改交給 [launchd service](/llm/knowledge-cards/launchd-service/) 接手。

## 概念位置

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

對 macOS 新手最常踩的兩個坑：一個是「前景跑 server 後不知道怎麼脫身」、解法是 `Ctrl+Z` 暫停 + `bg` 改背景、或下次改用 `&` 啟動；另一個是「pkill 沒指定夠精確的 pattern、誤殺其他 process」、解法是先用 `ps aux` 加 `grep` 確認 PID 再 kill。

## 設計責任

選前景 vs 背景的判讀：debug 場景前景跑、能直接看到 log；日常使用改 [launchd service](/llm/knowledge-cards/launchd-service/) 跑、跟 shell session 完全脫鉤。`&` 適合「terminal 開著就讓它跑、關掉也沒關係」的臨時場景、不適合需要長期穩定的服務。排錯時養成「先 `lsof` 找誰佔資源、再 `ps` 確認身分、最後才 kill」的順序、避免誤殺。
