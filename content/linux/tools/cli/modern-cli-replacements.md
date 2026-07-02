---
title: "現代 CLI 替代工具：grep、find、cat 之外的選擇"
date: 2026-07-02
description: "覺得 grep/find/cat/ls 這些預設指令夠用、但想知道多數開發者為什麼改用 ripgrep/fd/bat/eza，以及什麼情境值得換、換了要注意什麼時回來讀"
weight: 1
tags: ["linux", "tools", "cli", "ripgrep", "fzf"]
---

Linux 的預設指令（`grep`、`find`、`cat`、`ls`）能用，但它們是幾十年前為當時的環境設計的。過去十年出現一批用現代語言（多為 Rust）重寫的替代品，在同樣的工作上更快、預設行為更貼近日常開發、輸出更好讀。認識這些替代品的價值不在「預設的錯了」，而在你能在對的情境用更省力的工具——尤其是每天重複幾十次的搜尋與瀏覽。

這篇按「你原本用什麼」對照現代替代品，講清楚每個替代品解掉原工具的什麼痛點、什麼情境值得換、以及換了要注意的地方。核心的搜尋三件套（`ripgrep` / `fd` / `fzf`）值得優先掌握，其餘按需採用。

## 搜尋文字內容：grep → ripgrep（rg）

`ripgrep`（指令是 `rg`）是 `grep` 的現代替代品，最大差別在它預設就做了開發者幾乎每次都要的事：遞迴搜尋當前目錄、尊重 `.gitignore`（不會翻進 `node_modules`、`.git`、build 產物）、自動跳過二進位檔、輸出帶顏色與行號。用 `grep` 搜整個專案常要寫 `grep -rn --exclude-dir=node_modules pattern .`，用 `rg pattern` 一句就到位且更快（Rust 實作 + 平行搜尋）。

什麼情境值得換：在專案目錄裡找程式碼、找字串出現在哪些檔案——這是 `rg` 最省力的地方。什麼時候還是用 `grep`：處理 pipe 進來的串流（`command | grep x`）兩者差不多；寫要在任何機器都能跑的腳本時 `grep` 是保證存在的（`rg` 要另外裝）。注意點：`rg` 預設跳過 `.gitignore` 忽略的檔，要搜被忽略的檔案得加 `-u`（或 `-uu` 連隱藏檔一起）。

## 找檔案：find → fd

`fd` 是 `find` 的現代替代品，把 `find` 那套冗長語法換成直覺的用法。`find . -name '*.md' -type f` 用 `fd` 是 `fd -e md`；`fd pattern` 直接對檔名做模糊比對，一樣預設遞迴、尊重 `.gitignore`、跳過隱藏檔、輸出帶色。速度也快得多。

什麼情境值得換：日常找檔案（「這個 config 檔在哪」「有哪些 .test.ts」）。什麼時候還是用 `find`：`find` 的 `-exec`、複雜的時間 / 權限 / 大小條件組合仍然更全面，寫可攜腳本時 `find` 保證存在。注意點：`fd` 的正則 / glob 預設是 smart case（有大寫才區分大小寫），跟 `find` 的精確比對行為不同。

## 互動式模糊搜尋：fzf（不是替代，是加一層）

`fzf` 不替代任何工具，它是一層**互動式模糊選擇器**，把「一堆候選 → 你挑一個」這件事變得極快。它從 stdin 吃候選清單、開一個可即時模糊過濾的介面、把你選的印到 stdout，所以能跟任何產生清單的指令組合：`fd -e md | fzf` 挑一個 markdown 檔、`git branch | fzf` 挑分支、`rg --files | fzf` 挑檔案開。

最高價值的兩個內建整合：`Ctrl+R` 覆寫 shell 的歷史搜尋（模糊搜尋整個命令歷史，比預設的反向搜尋強太多）、`Ctrl+T` 把檔案路徑插進當前命令列。這兩個 key binding **不是裝完自動生效的**，要在 shell 設定裡啟用——新版 `fzf` 直接在 `.zshrc` / `.bashrc` 加一行 `eval "$(fzf --zsh)"`（bash 用 `--bash`）；舊版則 source 套件附的整合檔（Arch 在 `/usr/share/fzf/key-bindings.zsh` 與 `completion.zsh`，路徑隨發行版不同）。沒加這行，`Ctrl+R` 不會有反應。`fd` 跟 `rg` 可以當 `fzf` 的預設來源，三者是一組。

## 看檔案內容：cat → bat

`bat` 是 `cat` 加上語法高亮、行號、Git 修改標記、自動分頁。看程式碼 / 設定檔時比 `cat` 好讀很多。`bat file.py` 直接帶高亮顯示。

什麼情境值得換：人在終端機讀檔案內容。什麼時候還是用 `cat`：把檔案內容 pipe 給其他程式、或在腳本裡——這時要純內容，用 `cat`（`bat` 在偵測到輸出不是終端機時會自動退化成類 `cat` 行為，但明確用 `cat` 更穩）。注意點：`bat` 預設會分頁（走 `less`），在腳本 / pipe 情境要加 `--paging=never` 或 `-pp`。

## 列目錄：ls → eza

`eza`（`exa` 的維護接棒者）是 `ls` 的現代替代品，預設輸出帶顏色與圖示、更好的欄位對齊、內建 Git 狀態欄、`--tree` 直接畫樹狀。`eza -la --git` 一眼看到權限、大小、修改時間、Git 狀態。

什麼情境值得換：人在終端機瀏覽目錄。什麼時候還是用 `ls`：腳本裡解析輸出用 `ls` 更穩定（現代替代品的欄位格式可能隨版本變），可攜腳本 `ls` 保證存在。

## 其他常見替代

按需採用，痛點對上了再裝：

| 原工具            | 替代品                 | 解的痛點                                                                                    |
| ----------------- | ---------------------- | ------------------------------------------------------------------------------------------- |
| `cd`              | `zoxide`               | 記住常去的目錄，`z proj` 跳到最常用的（需 `eval "$(zoxide init zsh)"` 進 shell 才攔截 `z`） |
| `ps`              | `procs`                | 帶色、預設欄位更實用、支援樹狀與關鍵字過濾                                                  |
| `du`              | `ncdu` / `dust`        | 找誰佔空間：`ncdu` 互動逐層鑽 + 就地刪，`dust` 一次性樹狀視覺（見下）                       |
| `df`              | `duf`                  | 表格化、帶色、好讀的磁碟用量                                                                |
| `top`             | `htop` / `btop`        | 互動式監控：`htop` 輕量近乎必備，`btop` 更完整的全螢幕儀表（見下）                          |
| `git diff`        | `delta` / `difftastic` | diff pager：`delta` 語法高亮 + 並排，`difftastic` 語法感知（比 AST 不比行）                 |
| `man`             | `tldr`                 | 只給常用範例，不用讀完整 man page                                                           |
| `sed`（簡單替換） | `sd`                   | 直覺的 `sd 舊 新`，不用記 `sed` 的跳脫規則                                                  |

有兩個替代品的那幾格，差別不是「新舊」而是不同的使用模型，值得分清楚：

- **`du` 的 `ncdu` vs `dust`**：兩者解的動作不同。`ncdu` 是互動式的——它掃一次目錄，開一個能逐層往下鑽、當場按鍵刪檔的介面，是「磁碟滿了、要找出並清掉大檔」這個任務的正典（清空間邊找邊刪）。`dust` 是一次性的——跑完印一張樹狀 + 長條的靜態報告，適合「快速看一眼誰佔空間」而不打算就地刪。要清理用 `ncdu`，要瞄一眼用 `dust`。
- **`top` 的 `htop` vs `btop`**：`htop` 是輕量、幾乎每台機器都該有的安全預設——彩色、可捲動、能直接對 process 送訊號，資源佔用極低，SSH 進一台陌生機器臨時看負載首選它。`btop` 是更完整的全螢幕儀表（CPU / 記憶體 / 網路 / 磁碟的圖形化面板），好看資訊多，但相對重、依賴多；當常駐監控台用很讚，臨時排查用 `htop` 更快到位。TUI 監控工具的完整比較見 [TUI 監控工具](../tui-monitoring-tools/)。

## 採用策略與注意事項

**優先順序**：搜尋三件套（`rg` / `fd` / `fzf`）投報率最高，每天用幾十次、學習成本低，先裝這三個。`bat` / `eza` 是體驗提升，其餘按痛點採用。

**跨機器 / CI 的腳本別依賴它們**：要在別台機器或 CI 跑的腳本，用保證存在的 `grep` / `find` / `cat`，因為現代替代品不一定裝了。專案內部、已宣告了 dev 依賴的腳本（devcontainer、Makefile）另當別論——那裡明確裝了 `rg` / `fd`，用它們（甚至還因為 `rg` 尊重 `.gitignore` 的語意才選它）很合理。分界是「這段腳本會在沒裝這些工具的環境跑嗎」，不是「腳本一律不能用」。

**安裝**：多數在各發行版套件庫直接有。Arch：`pacman -S ripgrep fd fzf bat eza zoxide`，按需再加 `procs ncdu htop git-delta`（`delta` 的套件名是 `git-delta`）。Debian / Ubuntu 有兩個要注意的改名坑——`fd` 的執行檔在 apt 上叫 `fdfind`、`bat` 叫 `batcat`（都是為了避免跟既有套件撞名），要自己 alias 回 `fd` / `bat`；`eza` 較舊的 apt 源可能還沒有，用 cargo 或官方 repo 裝。macOS 用 `brew install ripgrep fd fzf bat eza zoxide`。裝好後它們該進你的 [dotfile 套件清單](/linux/dotfile/08-sync-bootstrap/bootstrap-script-packages/)，新機器 bootstrap 時一次裝齊。

## 相關

- 這篇是「日常指令替代」；全螢幕 TUI 工具（監控、Git、檔案瀏覽、資料庫）見 [CLI 環境工具](../) 的其他文章。
- 為什麼把工具當成「有取捨的選項」而非唯一答案，見 [工具選單總覽](../)。
- 這些工具進 dotfile 套件清單、一鍵安裝的做法，見 [模組八：Bootstrap script 與套件清單](/linux/dotfile/08-sync-bootstrap/bootstrap-script-packages/)。
