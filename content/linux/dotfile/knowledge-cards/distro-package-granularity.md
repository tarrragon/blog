---
title: "發行版打包粒度"
date: 2026-07-06
description: "同一個 install 指令在不同發行版拉的套件數差一個量級、或某工具在某發行版根本沒打包時回來讀 — 發行版怎麼切套件顆粒度"
weight: 44
tags: ["dotfile", "prod-parity", "debian", "knowledge-cards"]
---

發行版打包粒度是「一個發行版把軟體切成多細的系統套件」的策略。它決定同一個安裝指令的後果量級：有的發行版把每個 library 都包成獨立系統套件，有的把 library 留給語言自己的套件管理器管。同一個工具在前者可能拉進幾百個系統套件、在後者只拉幾個。

## 概念位置

這條跟 [Package Manager 抽象層](/linux/dotfile/knowledge-cards/package-manager-abstraction/) 互補：抽象層講「同一件事換 backend 怎麼寫」，這張講「同一個指令換 backend 後果量級差多少」。一個爛名字為何拖垮整批安裝，見 [apt 安裝的交易原子性](/linux/dotfile/knowledge-cards/apt-transaction-atomicity/)。實作上怎麼判斷該不該進 apt 清單，見 [工作站 dotfile 跨發行版落地](/linux/dotfile/10-prod-parity/workstation-cross-distro/)。

## 兩種粒度

以 nodejs + npm 為例，同樣一個安裝動作在兩種發行版的展開差一個量級（Debian bookworm 實測）：

```text
Debian   apt install nodejs npm   → 連帶 402 個新套件（其中 336 個 node-*，eslint、node-glob…每個 JS lib 一個 .deb）
Arch     pacman -S npm            → 只拉少數幾個；JS library 交給 npm 在 node_modules 管
```

Debian 的哲學是「所有東西都是系統套件」，所以它把 nodejs / npm 工具鏈本身的相依也拆成上百個 `node-*` deb，一次 `apt install npm` 就全灌進系統。要分清楚：這些 `node-*` 是 Debian 為了打包 node 工具鏈而拉進的**系統層相依**，跟你專案 `npm install` 進 `node_modules` 的依賴無關——後者不論哪個 distro 都走 npm、從不碰 apt。所以「402 套件」講的是系統工具鏈膨脹，不是應用依賴。Arch 不把這層 library 納入系統套件，同一個 npm 只在系統層多幾個檔案。

## 為什麼有的工具乾脆沒打包

粒度策略也決定「哪些工具進得了官方 repo」。移動快速的新工具（多為 Rust 寫的 CLI）在保守、定版凍結的發行版常常還沒被打包：broot、zellij、git-delta、lazygit、yazi 在 Debian bookworm 的預設 repo 都不存在，但在 Arch 都有。發行版愈保守（stable 凍結愈久），這類缺口愈多。

## repo 成員資格會隨時間漂移

「沒打包」不只是「保守發行版從沒收」的靜態狀態，也可能是「曾經收、後來被移出」的時間變化。官方 repo 會把不再維護的套件汰除：autojump（目錄跳轉工具）一度在 Arch 官方 repo，後來被移到 AUR，現在 `pacman -S autojump` 回 `target not found`——同一個發行版、同一個套件名，只是時間軸上的成員資格變了（維護版替代是 zoxide，仍在官方 repo）。這讓一份釘死的套件清單即使不換發行版也會腐化：清單寫的當下該套件在官方 repo、幾年後被移出，清單就在新機器上裝不起來。判讀是：`target not found` 且你確定名字沒打錯、以前明明裝得起來，就往「它被移出官方 repo 了」查（多半移到 AUR，或改由上游自行發佈 binary）。若整批一次裝，一個被移出的名字還會拖垮整批（見 [apt 安裝的交易原子性](/linux/dotfile/knowledge-cards/apt-transaction-atomicity/)）。

## 判讀訊號

安裝一個工具卻拉進幾百個套件時，先問「這些是不是某個語言生態的 library」。是的話，通常代表這東西不該走系統套件管理器——語言生態的執行環境（node、python、ruby）交給 version manager（fnm / pyenv / rbenv）在家目錄管更乾淨：可切版本、不污染系統、不被發行版凍在舊版。系統套件管理器留給「系統層工具」本身。

反過來，某工具 `apt install` 直接 unable to locate 時，多半是它還沒進這個發行版的 repo，不是名字打錯——退回 GitHub releases 的預編譯 binary 或 `cargo install`。

## 邊界

粒度細不是缺點：Debian 把 library 拆成系統套件，換來的是每個 library 都能收到發行版的安全更新與依賴一致性保證，這對伺服器場景有價值。問題只出在「拿它裝語言生態的開發依賴」——那是 version manager 的場域。判斷依用途，不是依發行版好壞。
