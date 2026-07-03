---
title: "終端機檔案管理器：broot、yazi、ranger 的遠端瀏覽與選型"
date: 2026-06-15
draft: false
description: "想在終端機像 IDE 側邊欄那樣瀏覽目錄與預覽檔案、在樹狀（broot）與欄狀（yazi/ranger）介面之間選、或處理遠端 SSH 下檔案管理器的依賴問題時回來讀"
tags: ["cli", "tui", "file-manager", "broot", "yazi", "ranger", "remote"]
---

終端機檔案管理器把資料夾結構與檔案內容做成全螢幕互動介面，讓遠端只有終端機時也能像 IDE 側邊欄那樣瀏覽目錄、預覽檔案、搬移與改名，取代反覆 `ls`、`cd`、`cat` 的來回。在純 SSH 情境下，它補上 git 線圖與系統監控之外的另一塊日常需求：檔案層級的導覽與操作。

本文承接 [終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/) 的檔案瀏覽分類。

## 兩種介面範式：樹狀與 Miller 欄狀

檔案管理器的版面分兩種範式，直接決定操作手感，也是「我記得的是哪一個」最快的辨認點。

樹狀（tree）範式像 IDE 的左側邊欄：一棵可展開、收合的目錄樹，深層結構的層級關係一眼看到。`broot` 是代表，它的官方定位就是「tree-like view」，配上模糊輸入過濾能直接跳到深層目錄，`--max-depth` 還能控制樹要展開幾層。

Miller 欄狀（Miller columns）範式像 macOS Finder 的欄狀檢視：並列數欄（父目錄、當前目錄、預覽），游標右移進入子目錄、左移回上層，最右欄即時預覽當前檔案內容。`yazi` 與 `ranger` 走這條，預覽窗大、適合邊瀏覽邊讀內容。

辨認方式很單純：記得的是「可展開／收合的樹」就是 broot 這類；記得的是「左邊瀏覽、右邊一大塊預覽」就是 yazi／ranger 這類。

## 工具對照

| 工具     | 語言   | 介面範式    | 特色                                     |
| -------- | ------ | ----------- | ---------------------------------------- |
| `broot`  | Rust   | 可展開樹    | 樹狀 + 模糊跳轉 + 退出時 cd 整合（`br`） |
| `yazi`   | Rust   | Miller 欄狀 | 非同步預覽（圖片／程式碼）、反應最快     |
| `ranger` | Python | Miller 欄狀 | 老牌、外掛與設定分享生態最大             |
| `nnn`    | C      | 細節／預覽  | 極簡超快、資源佔用低                     |
| `lf`     | Go     | Miller 欄狀 | ranger 風、單一 binary                   |

`broot` 把目錄做成可展開的樹，輸入幾個字就模糊過濾並跳轉到符合的路徑，是深層 monorepo 裡找檔最快的範式。它的 `br` shell function 讓退出時把工作目錄切到所在位置，等於用它當互動式 `cd` — 純 `broot` 指令做不到這件事，因為子行程改不了父 shell 的目錄。`br` 不會自動就位：首次執行 `broot` 會跳出提示問是否安裝（答 `Y`，或手動跑 `broot --install`），它把函式寫進 shell rc，重新載入 rc 後改用 `br` 啟動。如果還沒安裝 `br`，在 broot 裡按 `Alt + Enter`（`:cd`）跳轉會看到 `This verb needs broot to be launched as br` 的提示 — 這就是還沒透過 `br` 啟動的訊號，裝好 `br` 並改用 `br` 啟動就能跳轉。

操作上記幾個鍵就夠：直接打字會即時模糊過濾目錄樹，方向鍵移動游標；目錄上 `Enter` 進入該層、`Alt + Enter`（verb `:cd`）離開 broot 並把 shell 切到該目錄、檔案上 `Enter` 用預設程式開啟；`Ctrl + q` 離開，`Esc` 退回上一層狀態。完整快捷鍵與 verb 清單按 `?` 叫出。深層結構需要綜觀層級時，樹狀比欄狀直觀。要注意 broot 是導覽與啟動器、不內建文字編輯：改檔得在檔案上開外部編輯器（叫出 `$EDITOR`），它的強項在樹狀導覽與跳轉，不在看內容或改內容。

`yazi` 是 Miller 欄狀的現代實作，Rust 寫、預覽走非同步，大目錄或檔案很多時捲動不卡。它的程式碼預覽**內建語法高亮**（用內建 highlighter、開箱就有彩色，不必另裝相依，實測程式碼確實彩色渲染）；圖片預覽則看終端機支援度（見最後一節）。要的是「邊瀏覽邊看大塊內容」且在意速度時，yazi 最順。

`ranger` 是 Miller 欄狀的老牌，外掛、設定檔分享與教學資源最多。它的取捨在依賴：ranger 是 Python，遠端機器要有 Python runtime，而且較新的 Python 版本會在啟動時印 deprecation 警告（實測 ranger 1.9.4 配 Python 3.14 會噴 `SyntaxWarning: 'return' in a 'finally' block`，功能不受影響但訊息惱人）。預覽渲染同樣靠外部相依：ranger 預設的程式碼預覽是**純文字、無語法高亮**，要彩色得另裝 `highlight`、`bat` 或 `pygments` 並啟用 previewer（實測沒裝這些時就只有純文字，與 yazi 開箱即有高亮形成對比）。生態與依賴是它的一體兩面。

`nnn`（C）與 `lf`（Go）走輕量路線，啟動極快、資源佔用低，適合老舊或資源吃緊的機器；`lf` 是單一 binary，搬檔即用。

## 遠端情境的選型

選型回到「要哪種瀏覽範式」加上「目標機器能裝什麼」兩條軸：

- 想要 IDE 式可展開樹、常跳深層目錄：選 `broot`，樹狀加模糊跳轉在深層結構找檔最快。
- 想要欄狀導覽加強預覽（看圖、讀程式碼）、在意速度：選 `yazi`。
- 已有 ranger 習慣或需要特定外掛：選 `ranger`，但先確認遠端有 Python、並接受啟動時的警告訊息。
- 受限或老舊機器、要單一 binary 搬過去就用：`lf`（Go）或 `nnn`（C）。

安裝依賴是遠端的隱性分界。編譯型工具（broot、yazi、lf、nnn）搬一個 binary 就近可用；`ranger` 的 Python 依賴在不給裝套件或 Python 版本尷尬的機器上較麻煩。編譯型的單一 binary 仍要留意 glibc／musl 對得上目標系統，這點與 git 工具相同，見 [git 線圖工具選型](/linux/tools/cli/git-line-graph-tools-for-remote-cli/) 的單一 binary 注意事項。

預覽能力有一條邊界要先知道：程式碼與純文字檔的預覽在任何終端機都穩定，但圖片預覽需要終端機支援影像協定（sixel／kitty）。純文字遠端通道下，沒有影像協定時圖片會退回檔名與中繼資訊，這與 [總覽](/linux/tools/cli/cli-graphical-tools-overview/) 對影像協定的取捨一致。

## 下一步路由

- 把檔案管理器擺進可持久化的多工器 pane：[tmux 基礎](/linux/tools/cli/tmux-persistence-and-basics/)。
- 編譯型工具搬到遠端的單一 binary 注意事項：[git 線圖工具選型](/linux/tools/cli/git-line-graph-tools-for-remote-cli/)。
- 檔案管理在遠端工具分類中的定位：[終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/)。
