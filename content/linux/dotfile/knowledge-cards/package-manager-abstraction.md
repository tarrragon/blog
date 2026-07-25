---
title: "Package Manager 抽象層"
date: 2026-07-06
description: "同一份 dotfile 要從 Arch 跨到 Debian/macOS、不確定哪些要改哪些能共用時回來讀 — 綁 distro 的只有 package manager 這一層"
weight: 43
tags: ["dotfile", "prod-parity", "knowledge-cards"]
---

Package manager 抽象層是 dotfile 跨發行版可攜的關鍵切分：一份 dotfile repo 裡，真正綁特定發行版的只有「用哪個 package manager 裝套件」這一層，其餘（config 檔內容、symlink 部署、shell 框架安裝）都是跨 distro 共通的。把這一層隔離出來，同一份 repo 就能同時服務 Arch 工作站、Debian 容器與 macOS。這層抽象是 [發行版打包粒度](/linux/dotfile/knowledge-cards/distro-package-granularity/) 差異的因應之道。

## 概念位置

這個抽象讓 [GNU Stow](/linux/dotfile/knowledge-cards/gnu-stow/) 管的 config 層完全可攜。實作見 [工作站 dotfile 跨發行版落地](/linux/dotfile/10-prod-parity/workstation-cross-distro/) 與 [dotfile 跨進 runtime container](/linux/dotfile/10-prod-parity/container-ergonomics/)。

## 綁 distro 的只有裝套件那一步

各發行版的差異集中在 package manager 的指令與套件名：

```text
Arch          pacman -S --needed --noconfirm <pkg>
Debian/Ubuntu apt-get install -y --no-install-recommends <pkg>
macOS         brew install <pkg>
Alpine        apk add --no-cache <pkg>
```

除了這一步，其餘幾乎都可攜：`.zshrc` 的內容、`stow` 建 symlink 的方式、oh-my-zsh 的 `git clone`、config 檔本身——這些不管在哪個 distro 都一樣。所以跨 distro 的正解不是維護多份 dotfile，是維護一份 config + 一個依 package manager 分支的安裝層。

## Detection 分支的兩種形態

抽象這一層有兩種常見寫法，差別在分支放哪：

- **入口 detection**：安裝腳本開頭偵測 package manager，dispatch 到對應的 `install-<platform>.sh`，套件清單各平台一份（`packages/arch-*.txt`、`packages/debian-*.txt`）。適合工作站，因為各平台的套件集差異大。
- **行內 detection**：一支腳本內用 `command -v apt-get / pacman / apk` 分支，共用同一份套件名。適合容器內的輕量 ergonomics 安裝——只裝少數幾個工具、不值得拆多檔。

## 判讀訊號：什麼進分支、什麼是共通層

判準是「這一項換 distro 會不會變」：會變的（套件名、安裝指令）進 detection 分支；不會變的（config 內容、symlink 邏輯、框架 clone）留共通層。一個常見的誤置是把套件名寫死在共通層，結果換 distro 就壞——正確做法是共通層只呼叫抽象後的安裝函式，具體套件名下沉到各平台清單。

## 套件名分歧的常見形態

「換 package manager」不只是換指令前綴，套件名本身在不同 distro 有好幾種分歧，各要不同處理：

- **同工具不同套件名**：Arch 的 `fd` 在 Debian 叫 `fd-find`、`github-cli` 在 Debian 叫 `gh`。要靠各平台清單逐項對照，不能假設同名。
- **binary 名被改**：Debian 為了讓整個 archive 的 `/usr/bin` 名字全域唯一，會在上游 binary 名跟現有套件撞名時改名——`fd-find` 裝出來的 binary 是 `fdfind`、`bat` 是 `batcat`。所以「套件裝好了」不等於「指令叫得動」，`.zshrc` 的 alias 要按平台補（Debian 上 `alias fd=fdfind`）。
- **名字撞到別的工具**：`apt install delta` 裝到的是一個 heuristic minimizer、不是 `.gitconfig` 指的那個 diff pager（那個叫 git-delta、且 bookworm 沒打包）。同名不同物，照抄會裝錯東西。
- **套件被拆分或合併**：同一個上游工具在 Debian 常被拆成 `foo` + `foo-dev` + `foo-common`（照抄單一名字會漏裝 `-dev`、編不起來），或反過來多個工具併進一個 meta-package（如 `build-essential`）。安裝顆粒度跟 Arch 不對齊，要看該 distro 怎麼切。

除了名字，同名套件的**版本**也常分歧：Debian stable 凍結的版本往往比 Arch 舊一個世代，名字一樣、行為卻不同——這不是名字問題，但一樣影響對齊，見 [發行版打包粒度](/linux/dotfile/knowledge-cards/distro-package-granularity/)。

## 邊界

當某工具在目標 distro 根本沒打包時，抽象層也擋不住——退回手動安裝或換等價工具。哪些工具在保守發行版容易缺席，見 [發行版打包粒度](/linux/dotfile/knowledge-cards/distro-package-granularity/)；為什麼清單裡一個爛名字會拖垮整批安裝，見 [apt 安裝的交易原子性](/linux/dotfile/knowledge-cards/apt-transaction-atomicity/)。
