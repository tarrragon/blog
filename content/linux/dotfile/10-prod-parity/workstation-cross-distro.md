---
title: "工作站 dotfile 跨發行版落地"
date: 2026-07-06
description: "手上 dotfile 是照 Arch 寫的、要在 client 常見的 Debian/Ubuntu 機器上還原工作環境時回來讀 — 哪些綁 pacman、哪些能直接共用"
weight: 1
tags: ["dotfile", "prod-parity", "debian"]
---

這篇的目的是讓一份照 Arch 寫的工作站 dotfile，能在 client 常見的 Debian/Ubuntu 機器上還原出同樣的環境。要改的部分比想像少：綁發行版的只有「用哪個 package manager 裝套件」這一層，config 檔內容、symlink 部署、shell 框架安裝全部可攜。原理見 [Package Manager 抽象層](/linux/dotfile/knowledge-cards/package-manager-abstraction/)，這裡只講怎麼判斷跟怎麼落地。

## 哪些綁 distro、哪些共用

拿到一份 dotfile 要跨 distro 時，先把內容分成兩堆，判準是「換 distro 會不會變」：

- **會變、要下沉到平台層**：套件安裝指令（`pacman` vs `apt-get`）、套件清單、以及套件名分歧的工具。
- **不會變、留共通層**：`.zshrc` 內容、`stow` 建 symlink 的邏輯、oh-my-zsh 的 `git clone`、所有 config 檔本身。

判斷錯的代價是把套件名寫死在共通層——換 distro 就壞。正確形態是共通層只呼叫「裝套件」這個抽象動作，具體套件名交給各平台清單。

## 落地：入口 detection + 平台清單

工作站的套件集在不同 distro 差異大，適合用入口 detection：安裝腳本開頭偵測 package manager，dispatch 到對應的平台腳本。dotfiles repo 的形態是 `install.sh` 判斷 OS 後委派給 `install-arch.sh` / `install-macos.sh` / `install-debian.sh`，套件清單各一份（`packages/arch-*.txt`、`packages/debian-*.txt`），共通的環境組裝（stow、框架 clone）留在 `install.sh`。

跨到 Debian 只需要補一支 `install-debian.sh` 跟對應清單，共通層一行都不用動——這正是抽象層有效的證據。

## 套件名分歧：裝好不等於叫得動

同一個工具在不同 distro 的名字有好幾種分歧（有哪些形態、為什麼，見 [Package Manager 抽象層](/linux/dotfile/knowledge-cards/package-manager-abstraction/)）。落地時按形態各自處理：

- **套件名不同**（`fd` → `fd-find`、`github-cli` → `gh`）：靠各平台清單逐項對照，不假設同名。
- **binary 被改名**（`fd-find` 的 binary 是 `fdfind`、`bat` 是 `batcat`）：`.zshrc` 按平台補 alias（`alias fd=fdfind`）——「套件裝好了」不等於「指令叫得動」。
- **名字撞到別的工具**（`apt install delta` 裝到的不是 `.gitconfig` 要的 git-delta）：別照抄，確認同名同物。

`ripgrep` 兩邊同名（binary 都是 `rg`）不用處理，`fd` / `bat` 就要按上面吸收。

## 實作會遇到的狀況與排除

跨到 Debian 實跑時，除了名字分歧，還有幾個操作面的狀況會擋住 bootstrap。先知道怎麼排除：

- **全新映像連 sudo/git 都沒有**。乾淨的 Debian 映像預裝極簡，`install.sh` 要用到的 `sudo`、`git` 本身都缺。排除：bootstrap 第一步先 `apt-get install -y sudo git`，才有辦法 clone repo、跑後續。這是最小映像的預期形態，不是壞掉。

- **清單裡一個沒打包的名字讓整批全滅**。`apt-get install` 是一筆全有或全無的交易，清單塞一個 Debian 沒有的名字（實測 broot、zellij 在 bookworm 沒打包），apt 直接中止，同批存在的工具也一個都沒裝。排除：清單逐項對齊該 distro 實際有的套件，動手前用 `apt-get install -s <pkg>` 逐一 dry-run 篩掉解不開的。原理見 [apt 安裝的交易原子性](/linux/dotfile/knowledge-cards/apt-transaction-atomicity/)。

- **某些工具 Debian 根本沒打包**。broot、zellij、git-delta、lazygit、yazi 在 bookworm 預設 repo 都不存在（Arch 都有）。排除：把它們移出 apt 清單，改從 GitHub releases 裝——抓對應架構的預編譯檔（`curl -L -O <release-url>`）、解壓、`chmod +x`、`mv` 到 `~/.local/bin`（確認它在 `PATH`）；若走 `cargo install`，cargo 本身要先用 rustup 裝（裸 Debian 沒有）。原理見 [發行版打包粒度](/linux/dotfile/knowledge-cards/distro-package-granularity/)。

- **裝個 node 拉進幾百個系統套件**。`apt install nodejs npm` 在 Debian 會連帶 300 多個 `node-*` 套件（實測 bookworm 一次裝進 402 個新套件、其中 336 個是 node-*）。要避免的是拿系統套件管理器裝語言執行環境。排除：node / python / ruby 這類語言生態走 version manager（fnm / pyenv）在家目錄管，別放進 apt 清單。原理見 [發行版打包粒度](/linux/dotfile/knowledge-cards/distro-package-granularity/)。

## 邊界與下一步

桌面層（Hyprland 的 [rice](/linux/dotfile/knowledge-cards/rice/)，即桌面視覺客製化）的跨 distro 成本遠高於 CLI 層：Hyprland 在 Debian 要較新版才有打包，套件名與可用性都要重驗，所以工作站跨 distro 通常只做到 terminal 層，桌面留在實測過的 Arch。

工作站跨好之後，開發還缺一個對齊 client 線上的 runtime——那是下一篇 [對齊 prod 的 runtime container](/linux/dotfile/10-prod-parity/prod-parity-runtime/)。工作站是你的機器、可以最新；runtime 要退回線上那個凍結的舊形狀，兩者對齊的目標相反。
