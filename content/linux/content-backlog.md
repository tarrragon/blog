---
title: "Linux 分類：內容缺口待辦"
date: 2026-07-02
description: "linux 分類經三輪審查後盤點出、還沒寫的內容缺口與該補的反向連結，寫新內容前先看這張清單避免遺漏"
draft: true
tags: ["linux", "backlog", "meta"]
---

這是 `content/linux/` 分類經三輪多輪審查（2026-07-02）盤點出的內容缺口。`draft: true` 不對外發佈，只做版本控管的待辦清單。補內容前先看這裡，避免漏掉。缺口用 planned slug 表示（還沒建，不放連結以免觸發 broken-link）。

## 優先一：缺文章造成的「入口幻覺」（審查標為 SEVERE）

`tools/_index` 與 `tools/gui/_index` 的描述承諾了某些主題，但對應文章不存在——讀者看到指路牌、點進去沒有目的地。這兩篇是最高優先。

### 1. 桌面環境選型

- **planned slug**：`linux/tools/gui/desktop-environment-selection`（或放 `linux/tools/` 層）
- **要回答**：從 Windows/macOS 轉來、或要挑第一個桌面時，GNOME / KDE Plasma / Hyprland / XFCE / Cinnamon 怎麼選、各自的定位與代價（資源、客製自由度、穩定性、學習曲線、Wayland/X11 支援）。
- **為什麼**：`tools/_index` 明文「桌面環境本身也有 GNOME/KDE/Hyprland 等多種版本…這些選項的判讀正是這個系列要補的」，但目前只有檔案管理員一篇；`dotfile/06-rice-design` 是「已選 Hyprland 之後怎麼美化」，不是選型。搜尋 `hyprland vs gnome`、`linux 桌面環境 選哪個` 全 dead-end。
- **接應**：寫好後當 `dotfile/06-rice-design`（Hyprland 深入）的上游「為什麼選它」入口。使用者原話：「桌面環境有多種版本、各自對應擴充的 MOD」——選型 + 擴充生態都該涵蓋。

### 2. 遠端連線與同步工具選型

- **planned slug**：`linux/tools/remote/connection-and-sync-tools`
- **要回答**：`ssh` vs `mosh`（斷線漫遊）、`autossh`（自動重連）；遠端檔案同步 `rsync`（單向）vs `sshfs`（掛載）vs `mutagen`（雙向即時）；`tailscale`/`wireguard`、VS Code Remote 的定位。
- **為什麼**：`tools/_index` 把 remote 定義成「多工器、**連線與同步**、把長任務留在遠端」，但 `tools/remote/` 目前 0 自有文章（只有導向 _index）。「連線與同步」這塊完全沒文章。搜尋 `sshfs 還是 rsync`、`mosh 斷線` 落空。

## 優先二：安裝期故障排除（blog 缺、skill 已補）

### 3. 安裝期 pacman / DNS / mirror / keyring 故障排除

- **planned slug**：`linux/install/` 補一段或一篇（如 `package-and-network-troubleshooting`）
- **要回答**：安裝當下 `pacman` 解析失敗 / mirror 逾時 / DNS 沒設 / keyring 簽章過期 / db lock 殘留 / partial upgrade。
- **為什麼**：裝機最常撞的牆之一，blog 目前無聚焦落點（`install-option-decisions` 只教「選」鏡像，不教故障）。**skill 側已在 `install-and-verify` 補了套件管理器失敗段**，blog 可對照補齊。

## 優先三：DRY 與生態完整性（審查建議層）

### 4. compositor / 合成器 知識卡

- **planned slug**：`linux/dotfile/knowledge-cards/compositor`（或 `wayland-compositor`）
- **要做**：compositor 的定義目前被逐檔內嵌重寫（`06-rice-design/_index`、`05-hyprland-config`、`04-window-management/wayland-explainer`、`debug/process-service-state-diagnosis`、`debug/diagnosis` 等 5+ 處）。建一張 atomic 卡當 SSoT，讓這些內嵌括號定義塌縮成連結。
- **註**：Round 2 已在各 debug 篇加了 inline gloss（讀者能懂），這張卡是 DRY / 維護改善，非讀者面缺陷。

### 5. modern-cli 補漏的替代品

- **要做**：`modern-cli-replacements` 的清單補 `delta` / `difftastic`（git diff pager，文中有 bat 無 delta）、`procs`（ps 替代）、`ncdu`（du 互動正典，文中直接跳 dust）、`htop`（top 替代的輕量安全預設，文中直接推 btop）。`jq` / `hyperfine` 屬新類別可略。
- **為什麼**：R3-B steelman 指清單不窮盡。

### 6. gui 檔案管理員補對照

- **要做**：`gui-file-manager-dependencies` 補「TUI 檔案管理員（`yazi` / `lf` / `nnn` / `ranger`）是同 context 零相依對照」、說明為何拿 Nemo 當「重」代表而非 Nautilus（GNOME，更 canonical 的「裝半個桌面」）或 Dolphin（KDE）。
- **為什麼**：R3-B「這麼在乎相依，為何不提 yazi」。

## 優先四：還沒補的反向連結（outbound）

- `dotfile/03-terminal-ecosystem/multiplexer-tmux-zellij`（概覽）→ `tools/cli` 的 tmux/zellij 深度頁：概覽該下引深度頁。
- `infra`（雲端主機初始化、`00-infra-mindset`、「拿到雲端帳號的第一天」）↔ `linux/install`（ssh-keyless-bootstrap、unattended-remote-work）+ `linux/debug/machine-unreachable`：主題高度重疊、目前零互引，該建跨頂層分類的橋。
- `record/systematic-debugging-methodology` → `linux/debug/diagnosis-read-authoritative-state`：通用除錯方法論可引 Linux 具體實例。

## 補完後要回頭做的

- 補完 1、2 後，`tools/_index` 與 `tools/gui/_index` 對桌面環境選型 / 連線同步的承諾就兌現了，「入口幻覺」自動消除。
- 補完 4（compositor 卡）後，把 5+ 處內嵌 gloss 改連卡片。
- 每補一篇跑 `mdtools cards` 確認新連結不 broken，並更新對應 _index 的文章表格。
