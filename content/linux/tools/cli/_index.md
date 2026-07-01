---
title: "CLI 環境工具"
slug: "cli"
description: "在純文字終端機下做事時要挑工具——日常指令的現代替代品（rg/fd/fzf），以及用文字字元做出圖形化操作介面的 TUI（監控、圖表、多工器、資料庫）——想知道各情境有哪些選擇時回來讀。"
weight: 1
tags: ["linux", "tools", "cli", "tui", "remote"]
---

在純文字終端機下做事的工具分兩個家族。第一個是**日常指令的現代替代品**：`grep` / `find` / `cat` / `ls` 這些預設指令的現代版（`ripgrep` / `fd` / `bat` / `eza` + 互動式的 `fzf`），在每天重複幾十次的搜尋與瀏覽上更快更省力。第二個是**終端機圖形化介面（TUI）**：用 ASCII 與 Unicode 製圖字元做出的監控、圖表、多視窗、資料庫操作介面，只傳純文字、不依賴影像協定，在 SSH、手機平板、低頻寬連線下最穩。

## 日常指令的現代替代品

- **[現代 CLI 替代工具](modern-cli-replacements/)** — `grep` → `ripgrep`、`find` → `fd`、`cat` → `bat`、`ls` → `eza`，加上互動式模糊搜尋 `fzf`。什麼情境值得換、換了要注意什麼、為什麼別在腳本裡依賴它們。

## 終端機圖形化介面（TUI）

這一類「圖形化」是用製圖字元畫出來的介面，而不是把 PNG／JPG 渲染進終端機，所以傳輸量小、在低頻寬與手機連線下最穩。大致分六類：

- **TUI 監控與儀表板** — `btop` / `htop` / `k9s` / `ncdu` 等系統監控的全螢幕互動介面；版控專用的 git 線圖工具（`tig` / `lazygit` / `gitui`）是同類 TUI 但獨立的子題。
- **ASCII 與文字圖表** — `gnuplot` / `termgraph` / `plotext` 等把資料畫成終端機圖表的工具。
- **終端機多工器** — `tmux` / `zellij`，分割畫面、連線斷了 session 還在。
- **檔案管理器** — `broot`（樹狀）/ `yazi` / `ranger`（Miller 欄狀），像 IDE 側邊欄那樣瀏覽目錄與預覽檔案。
- **SQL 客戶端** — `harlequin`（IDE 風）/ `lazysql`（瀏覽器風）/ `pgcli`、`litecli`（增強 REPL），在終端機連資料庫跑查詢。
- **訊息佇列客戶端** — Kafka 的 `kaskade` / `yozefu` / `ktea`（全螢幕 TUI）、Redis 的 `iredis`（增強 REPL），在終端機連 broker 瀏覽 topic 與訊息。

這個系列的每篇文章都用實機驗證導向的流程生產（裝起來實跑、TUI 交人互動驗、驗不了的標 caveat）。要擴展新類別時，照 [驗證導向的 CLI 工具文章生產流程](/posts/verification-driven-cli-tool-articles/) 走。

---

## 跟其他系列的關係

| 系列                       | 交集                                                                                                                                         |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| [Dotfile](/linux/dotfile/) | CLI 工具（tmux/zellij/btop/broot）的配置檔版控與跨機器同步見 Dotfile 系列，特別是[終端機與編輯器](/linux/dotfile/03-terminal-ecosystem/)模組 |

## 跟其他資料夾的邊界

| 議題                                      | 該放                   |
| ----------------------------------------- | ---------------------- |
| blog 本身設定（Hugo / mdtools / Mermaid） | `posts/`               |
| 工作場景觸發、想記下來的單一事件          | `work-log/`            |
| 從多個事件抽象的工程方法論                | `record/` 或 `report/` |
| 在終端機做圖形化操作介面的工具與選型      | **本資料夾**           |

---

底下自動列出本資料夾的所有文章、依日期排序。
