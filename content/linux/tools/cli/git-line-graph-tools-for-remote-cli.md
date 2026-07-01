---
title: "遠端 CLI 開發的 git 線圖工具選型：tig、lazygit、gitui 與管線增強"
date: 2026-06-15
draft: false
description: "純 CLI、遠端開發情境下查看 git 分支線圖的工具地景，從 tig 唯讀瀏覽到 lazygit/gitui 操作中樞的定位差異，含選型判準與 lazygit 上手、delta side-by-side diff 設定。"
tags: ["cli", "git", "tui", "lazygit", "gitui", "tig", "delta"]
---

git 線圖工具，是把 commit 的分支、合併與時間先後關係畫成終端機可讀圖形的一類程式，承擔的責任是讓開發者在沒有桌面圖形環境的遠端機器上，仍能看清楚 repo 的歷史結構並進行版控操作。在純 SSH 連線的開發情境下，它取代了 IDE 內建的 git 圖形面板，而傳輸的全是文字，所以在頻寬低、只有終端機的條件下依然可用。

最基本的線圖能力內建在 git 本身：`git log --oneline --decorate --graph` 就會用 ASCII 畫出分支線。Oh My Zsh 的 git plugin 把它包成 `glog`（當前分支）與 `gloga`（加 `--all` 看全分支）兩個 alias。這條 alias 是任何環境都成立的底線 — 即使在一台陌生、不能安裝任何東西的機器上，`git log --graph` 永遠都在。專用工具要解決的，是這條底線之上的兩個缺口：互動瀏覽的流暢度，以及把「看」與「改」整合在同一畫面。

本文承接 [終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/) 的 TUI 工具脈絡，聚焦 git 線圖這個版控子題（最常被遠端開發者問到）。

## 三類工具的職責分工

git 線圖工具依承擔的責任分三類，遠端 CLI 情境下各自適用的條件不同。

### TUI 互動式瀏覽與操作

TUI 工具負責把 git 歷史開成全螢幕的互動介面，讓游標在 commit、檔案、分支之間移動，並即時在側欄顯示對應的 diff。它跟單純印一次 log 的差別在於「可導航」— 線圖、diff、blame 在同一個畫面裡用鍵盤切換，不必反覆重打指令。

| 工具      | 語言 | 一句話定位                             |
| --------- | ---- | -------------------------------------- |
| `tig`     | C    | 老牌穩定的唯讀瀏覽器（log/diff/blame） |
| `lazygit` | Go   | 功能最全的操作中樞                     |
| `gitui`   | Rust | 精簡高效、大 repo 友善                 |

已經在用 `tig` 的人，可以把後兩者當成「補上操作能力」而非替換：只想瀏覽就停在 `tig`，要用鍵盤完成 stage/commit/rebase 再加 `lazygit`，兩者互補。各工具的責任邊界與選型條件在下面逐一展開。

`tig` 的責任邊界在「看」。它把 git 歷史做成可導航的唯讀視圖，線圖呈現清楚、資源佔用極低，適合只想快速翻歷史與看 diff 的情境。它本身不做版控操作，所以心智負擔小、學習成本低。

`lazygit` 把責任從「看」擴到「改」。互動式 rebase、cherry-pick、stash 管理、衝突解決、stage 到 commit 的完整流程都能用鍵盤完成，等於把終端機 git 操作整碗端進一個畫面。它的代價是功能多帶來的學習曲線與稍高的資源佔用。

`gitui` 與 `lazygit` 定位相近但取捨相反，刻意保持精簡並換取效能。日常的 stage、commit、branch、stash、blame、log 都涵蓋，但進階流程的覆蓋度不追求面面俱到。它跟 `lazygit` 的深入比較放在後面一節。

### 純 log 線圖增強（走管線、零 TUI）

這類工具不開全螢幕介面，而是改善 `git log` 一次性輸出的可讀性，責任是讓線圖更清楚、讓 diff 配色更易讀。它走標準輸出與管線，適合接在腳本裡或當成 alias 隨手用。

`git log --graph` 系列（也就是 `glog` / `gloga`）是這條路線的起點，零安裝、處處可用。`git-graph` 是專門產生比內建更清楚的 ASCII 分支線的工具，當內建線圖在複雜合併歷史下變得難讀時，它把分支著色與排版做得更工整。`delta` 是 diff 的語法高亮 pager，嚴格說不算線圖工具，但它把 `git log -p` 與 `git diff` 的輸出做成帶配色、帶行號、可左右並排的版面，常跟前述工具搭配使用 — 後面 lazygit 的 side-by-side diff 就是靠它。

這類工具的判讀訊號是：需要的是「印一次看一眼」而非持續導航。它對頻寬特別友善，因為是一次性輸出、不像 TUI 會持續重畫畫面。

### 桌面 GUI（遠端通常排除）

`gitk`、`git-gui`、`gitg` 這類桌面圖形工具依賴 X11 或桌面環境，在純終端機的遠端連線下無法直接執行，或需要繁瑣且吃頻寬的 X11 forwarding。這個排除有明確前提：本篇限定「只有終端機、不能在遠端裝 IDE agent」的最小情境。若情境允許 IDE 的 remote 機制（VS Code Remote-SSH、JetBrains Gateway）或可接受 X11 forwarding，桌面 GUI 仍能遠端使用、體驗也不差 — 這條前提放寬時，本篇的結論會跟著變。把 GUI 列在這裡只為說明邊界：它們解決的是「有桌面或 IDE 通道」的需求，與「只有終端機」是不同場景。

## 遠端情境為什麼偏好單一 binary

遠端開發選型有一個容易被忽略的隱性約束：工具的安裝依賴。Go 與 Rust 寫的工具（`lazygit`、`gitui`、`git-graph`、`delta`）通常編譯成單一 binary，相較需要先裝 runtime 的工具，把檔案搬上去就能用，這是它們在 SSH 情境特別受歡迎的原因之一。

但「單一 binary」要打兩個折扣，照字面 `scp` 可能撞牆。其一，binary 自身不含 runtime，不代表沒有執行期依賴：`lazygit` 與 `gitui` 執行時都會呼叫系統的 `git`，遠端機沒裝 git 就跑不動。其二，Rust 工具（`gitui` / `delta`）預設動態連結 glibc，不是真正的 static；跨發行版或搬進 alpine 容器（用 musl）會出現 `GLIBC not found`，這種情境要下載對應的 musl 靜態建置版。判讀的分界是：能用系統套件管理器自由安裝時，依語言寫成什麼影響不大；環境受限時，除了「一個檔案」還要確認目標機有 `git`、且 binary 的 libc 對得上目標系統。這也是為什麼 `git log --graph` alias 是最後的保命符 — 它連 binary 都不必搬。

## lazygit 與 gitui 的定位差異

`lazygit` 與 `gitui` 表面功能重疊度很高，選擇依據主要落在以下幾個面向，而非單純「誰比較快」。

### 技術底色：效能與資源

`gitui` 用 Rust 做了非同步架構，在 monorepo、歷史很長、或機器資源有限（老舊伺服器、容器內）時反應更跟手，啟動極快、記憶體佔用低。`lazygit` 的效能日常夠用，但在 diff 或 log 非常大時偶有卡頓、記憶體佔用較高。這是兩者最常被提到的分水嶺，也直接對應遠端機器的強弱。

### 功能廣度 vs 功能聚焦

這是比效能更根本的定位差異。`lazygit` 賭功能廣度：互動式 rebase、cherry-pick、stash 管理、衝突解決、自訂指令幾乎都包了，目標是讓人完全不打 git 指令。`gitui` 賭功能聚焦：涵蓋 stage、commit、branch、stash、blame、log 這些日常約八成的操作，進階流程（複雜 rebase）的覆蓋度刻意保留，設計上傾向不做太重的事。

### 選型決策邏輯

兩者背後是兩種不同的使用意圖。傾向 `lazygit` 的，是想用一個工具取代 git CLI、把版控操作整碗端進終端機，願意付稍高的資源代價換廣度與便利。傾向 `gitui` 的，是想要一個快速的 git 視窗，主要看狀態、看歷史、做基本提交，要求即開即用、進階操作仍回去打 git 指令。一句話收斂：`lazygit` 押廣度與便利，`gitui` 押速度與輕量。

### 生態與社群

`lazygit` 社群採用度較高、star 數較多、教學與設定檔分享資源豐富，keybinding 與自訂指令的客製空間大。`gitui` 社群較小但穩定，定位清晰。對需要大量客製或想參考他人設定的情境，`lazygit` 的生態是實質優勢。長期依賴前也值得瞄一眼維護活躍度（release 節奏決定 bug 修復速度）— 兩者都在活躍維護，但 star 數高不等於修得快，這跟社群熱度是兩件事。

## 選型判準（遠端 CLI 情境）

把上述收斂成一條判準鏈，對應遠端開發的機器條件：

- 機器資源充足、想要一個工具搞定所有 git 操作：選 `lazygit`，把它當操作中樞。
- 遠端機器較弱、repo 很大、或只想快速看狀態做提交：選 `gitui`，換取即開即用與低資源。粗略 tripwire：repo 歷史上萬筆 / monorepo、機器 RAM 約 1GB 以下、或 `lazygit` 開大 diff 時明顯卡頓，就往 `gitui` 靠。
- 只需要看歷史與 diff、不在工具裡做版控操作：`tig` 的唯讀定位最輕量。
- 環境受限、不能安裝：退回 `gloga`（`git log --graph --all`），它在任何 git 環境都成立。

這四者能共存。常見的搭配是 `tig` 看歷史 + `lazygit` 做操作，兩者互補性高；`gitui` 與 `tig` 的瀏覽定位略有重疊，同時留兩個的理由較弱。風險與邊界在於學習成本：操作中樞型工具按一個鍵就改動 repo，初期適合先在拋棄式分支或測試 repo 練手，熟悉後再用到開發分支。

## lazygit 上手與 side-by-side diff

`lazygit` 的介面遵循一個固定心法：左側面板選「對什麼東西操作」、右側看「內容」、底部提示列顯示「當前能按什麼」。底部提示列會隨游標位置動態變化，所以操作不必背全部快捷鍵，迷路時按 `?` 會叫出當前面板的上下文敏感說明。

入門只需記幾個導航鍵：`Tab` 或數字 `1`~`5` 切換左側面板（Status / Files / Branches / Commits / Stash），方向鍵或 `hjkl` 在面板與清單內移動，`Esc` 返回上一層，`q` 離開。線圖在 `Commits` 面板（按 `4`），全分支關係在 `Branches` 面板（按 `3`）。三個最常用的日常操作：在 `Files` 面板用空白鍵 stage / unstage、stage 完按 `c` 輸入訊息提交、在 `Commits` 面板選 commit 後右側自動顯示 diff（`Enter` 進入檔案層級）。

預設的 diff 是單欄 unified（增刪行逐行上下排列）呈現。要做到像 IDE 那樣左右並排（side-by-side）對齊，`lazygit` 本身沒有內建這個視圖，需要外接 pager。pager 是負責把長輸出分頁、上色顯示的程式（git 預設用 `less`）；這裡讓 `lazygit` 把 diff 文字交給外部 pager 上色並重排成並排版面，最常見的搭配是 `delta`。安裝 `delta` 後，在 `lazygit` 設定檔（`~/Library/Application Support/lazygit/config.yml`，或 `~/.config/lazygit/config.yml`）指定它當 pager 並開啟並排模式：

```yaml
git:
  pagers:
    - colorArg: always
      pager: delta --dark --paging=never --side-by-side
```

`--side-by-side` 是讓 `delta` 左右並排的關鍵旗標，`--paging=never` 讓 `delta` 只負責上色與排版、捲動分頁仍由 `lazygit` 處理。`git.pagers`（list）是現行 lazygit 的設定鍵；舊版的 `git.paging.pager`（單數）仍可用，新版啟動時會自動 migrate 成上面的形式並改寫設定檔。在窄螢幕（手機、平板遠端）下，並排會把每欄壓得很窄，這種情境改回垂直單欄反而好讀 — side-by-side 的適用條件是螢幕夠寬。

## 下一步路由

選型確定後，後續深入的方向：

- 想完全用鍵盤取代 git 指令：深入 `lazygit` 的互動式 rebase、cherry-pick 與自訂指令流程。
- 遠端機器資源吃緊：實測 `gitui` 在大型 repo 的反應，跟 `lazygit` 同一個 repo 跑一次比較體感。
- diff 配色與並排需求延伸到日常 git：把 `delta` 設成 git 全域 pager（`git config --global core.pager delta`），讓 `git diff` 與 `git log -p` 也吃到同一套配色。

git 線圖在整個遠端 CLI 工具選型中的位置，見 [終端機圖形化工具總覽](/linux/tools/cli/cli-graphical-tools-overview/) — 本篇屬其中的版控子題、與系統監控的 TUI 工具脈絡相承。
