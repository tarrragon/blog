---
title: "tmux 基礎：遠端 session 持久化與基本操作"
date: 2026-06-15
draft: false
description: "tmux 終端機多工器的遠端使用核心：detach/reattach 讓 session 脫離連線生命週期、prefix key 與 window/pane 操作、手機友善的快捷鍵調校，以及 tmux 與 zellij 的選型對照。"
tags: ["cli", "tmux", "zellij", "terminal", "remote", "multiplexer"]
---

tmux 是終端機多工器，核心責任是把終端機 session 的生命週期與連線本身脫鉤，並在單一連線裡分割出多個工作區。在遠端 SSH 開發下，它解決最痛的一個問題：連線斷了，伺服器上跑的東西不會跟著消失。把工作放進 tmux，連線中斷後 session 仍在伺服器上運作，重連 attach 回去就接續原狀。

遠端伺服器優先選 tmux 的理由是可用性。它幾乎是事實標準，多數 Linux 發行版的套件庫都有、很多伺服器甚至預裝。`zellij` 功能新、畫面提示友善，但通常要自行安裝；在不能隨意裝套件的機器上，tmux 處處可用就是決定性優勢。兩者的取捨在最後一節展開。

本文承接 [終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/) 的多工器分類，聚焦 tmux 在遠端情境的實際操作。

## 持久化工作流：detach 與 reattach

tmux 對遠端最重要的能力是 session 持久化：session 跑在伺服器上，跟當前這條 SSH 連線無關，所以主動離開或被動斷線後它都還在。這條工作流由四個指令構成。

| 動作             | 指令                  | 說明                                                  |
| ---------------- | --------------------- | ----------------------------------------------------- |
| 開新具名 session | `tmux new -s work`    | 用名字開，之後好辨識                                  |
| 主動離開         | `prefix` 後按 `d`     | detach，session 留在背景繼續跑                        |
| 列出現有 session | `tmux ls`             | 看伺服器上有哪些 session                              |
| 接回             | `tmux attach -t work` | reattach，回到離開時的狀態（可簡寫 `tmux a -t work`） |

關鍵在於被動斷線與主動 detach 的結果相同：手機從 Wi-Fi 切到行動網路、SSH 連線逾時、筆電闔上，這些情況下 tmux session 都留在伺服器上，重連後 `tmux a` 就接回去。判讀訊號很單純：任何超過幾秒、不想因斷線重來的工作（build、資料遷移、`tail -f` 追 log、跑測試），開始前先進 tmux。

## prefix key：tmux 操作的入口

tmux 的所有指令都以 prefix key 起手，預設是 `Ctrl-b`。操作方式是按下 `Ctrl-b` 放開、再按功能鍵，而不是同時按住。理解這個「兩段式」是上手 tmux 的第一道門檻；若按住不放或間隔太久而沒反應，多半是兩段式沒按對，重來一次即可。

| 操作                        | 按鍵                    |
| --------------------------- | ----------------------- |
| 開新 window                 | `prefix` 後按 `c`       |
| 切換上一個 / 下一個 window  | `prefix` 後按 `p` / `n` |
| 跳到第 N 個 window          | `prefix` 後按數字       |
| 垂直分割（左右兩個 pane）   | `prefix` 後按 `%`       |
| 水平分割（上下兩個 pane）   | `prefix` 後按 `"`       |
| 在 pane 間移動              | `prefix` 後按方向鍵     |
| 關閉當前 pane               | `prefix` 後按 `x`       |
| 單一 pane 全螢幕放大 / 還原 | `prefix` 後按 `z`       |
| 進 copy mode（往回捲歷史）  | `prefix` 後按 `[`       |

window 與 pane 是兩個層級：window 是整頁工作區（類似分頁），pane 是一個 window 內切出的子區塊。遠端開發常見的佈局是一個 window 切成數個 pane，一個跑編輯器、一個跑 `tail -f`、一個留著敲指令。捲動歷史要先進 copy mode（`prefix` 後按 `[`），用方向鍵或 `PageUp` 往回看，按 `q` 離開 — 這是初學最容易卡住的點，因為進了 tmux 後終端機原本的捲動行為改由 tmux 接管。

## 遠端與手機的調校

tmux 預設設定對手機與慢速連線不夠順，幾項調整能明顯改善體感，全部寫在 `~/.tmux.conf`。

prefix key `Ctrl-b` 在手機虛擬鍵盤上難按，常見的調整是改綁成 `Ctrl-a`（更靠近鍵盤左側）：

```bash
# ~/.tmux.conf
unbind C-b
set -g prefix C-a
bind C-a send-prefix
```

滑鼠支援讓觸控裝置能直接點選 pane 與捲動，在手機與平板特別有用：

```bash
# ~/.tmux.conf
set -g mouse on
```

頻寬層面，tmux 本身傳輸的是純文字、量很低，斷線重連的成本也小。真正吃頻寬的是跑在 tmux 裡的全螢幕 TUI（例如 `btop`）的高頻重畫 — 這要調的是那個工具自己的刷新率，而非 tmux。改完設定檔後，在既有 session 內用 `prefix` 後按 `:` 輸入 `source-file ~/.tmux.conf` 重新載入。

## tmux 與 zellij 的選型對照

tmux 與 zellij 解決同一類問題，session 持久化是兩者共有的基本能力（zellij 甚至內建 resurrection），真正的選擇依據是可用性與上手成本。

| 面向           | tmux                         | zellij                                         |
| -------------- | ---------------------------- | ---------------------------------------------- |
| 預設可用性     | 多數伺服器預裝或套件庫直接有 | 通常需要自行安裝                               |
| 上手成本       | 需記快捷鍵                   | 畫面有提示列，操作邊看邊學                     |
| session 持久化 | 有（detach / reattach）      | 有，另內建 resurrection（結束後重建）          |
| 設定生態       | 成熟、範例與設定檔分享多     | 內建 layout、設定較直覺                        |
| 資源佔用       | 低                           | 略高但仍輕量（差在閒置記憶體、與傳輸頻寬無關） |

選型分界很清楚：受限或陌生的伺服器、要求處處可用，選 tmux；自己掌控的機器、想要友善的上手體驗與內建 layout，選 zellij。對 prefix 快捷鍵還不熟的人，這條分界仍成立：在別人的伺服器上工作優先學 tmux，因為無法保證對方裝了 zellij，可用性約束高於上手體驗；zellij 的友善體驗留給自己能掌控安裝的機器。兩者的指令心智模型相近（都靠一個 prefix/modifier 起手），學會一個再換另一個成本不高。zellij 路線的實際操作在本資料夾另有兩篇：pane 的 CLI 操作見 [Zellij 多終端機操作指南](/linux/tools/cli/zellij-pane/)、瀏覽器遠端連線見 [Zellij Web Client 外網連線教學](/linux/tools/cli/zellij-remote-web-client/)。

## 下一步路由

- 在多工器的 pane 裡擺即時監控：見 [TUI 監控工具](/linux/tools/cli/tui-monitoring-tools/)。
- zellij 的進階用法：[Zellij 多終端機操作指南](/linux/tools/cli/zellij-pane/) 與 [Zellij Web Client 外網連線教學](/linux/tools/cli/zellij-remote-web-client/)。
- 多工器在三類遠端工具中的定位：[終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/)。
