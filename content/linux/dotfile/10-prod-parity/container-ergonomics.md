---
title: "dotfile 跨進 runtime container"
date: 2026-07-06
description: "想在對齊 prod 的 container 裡用自己順手的 shell / vim、又不想把工具裝進 image 破壞 parity 時回來讀 — 在 running container 裝開發工具、跟 runtime 分層"
weight: 3
tags: ["dotfile", "prod-parity", "docker"]
---

有了對齊 prod 的 runtime，你會想在裡面用順手的 shell 跟 vim——但直接把這些裝進 image，它就不再跟線上逐項相同（parity 破功）。這篇把開發 ergonomics（shell、vim、git config）帶進 container、同時保住 parity，做法是把「這個 image 跟線上一不一樣」跟「我用得順不順手」當成兩層分開處理。

## ergonomics 進可寫層，不進 image

最容易犯的錯是把 zsh、vim、個人 config 寫進 runtime 的 Dockerfile。一旦 ergonomics 進了 image，這個 image 就不再等於 prod——線上不會有你的 oh-my-zsh，parity 當場破功。判準很硬：

- **runtime image 只裝 app 需要、prod 也有的套件**（見 [對齊 prod 的 runtime container](/linux/dotfile/10-prod-parity/prod-parity-runtime/)）。
- **ergonomics 裝進「已啟動的 container」**：`docker compose exec <service> bash` 進去後才裝，或 `docker compose cp` 把檔案送進去（已啟動的 container 無法事後 mount，掛載只能在 compose / `docker run` 當下宣告）。它活在容器的可寫層、不進 image。

這條分層讓同一個 runtime image 既是「線上的忠實複製」又能「開發時很好用」，兩個需求不打架。

## ergonomics 層自己也要可攜

runtime 的 base 是 Debian，但你的 dotfile 是照 Arch 或 macOS 寫的。ergonomics 安裝腳本要能在 Debian container 裡跑，靠的是 package manager detection——同一支腳本用 `command -v apt-get / pacman / apk` 分支，適配當下所在的環境。原理見 [Package Manager 抽象層](/linux/dotfile/knowledge-cards/package-manager-abstraction/)。

跟工作站的入口 detection 不同，container 內只裝少數幾個工具、不值得拆多檔，適合行內 detection：一支腳本內分支、共用同一份工具清單。dotfiles repo 的 `runtimes/php72-mysql57/ergonomics/setup.sh` 就是這個形態。

## 落地形態

裝套件那一步分 distro，config 部署完全共通：

- **裝工具**：把 `setup.sh` 送進已啟動的 container 再跑——`docker compose cp ergonomics/setup.sh php:/tmp/setup.sh && docker compose exec php bash /tmp/setup.sh`，它偵測 package manager 裝 zsh/git/vim。
- **部署 config**：dotfiles repo 送進去再 stow——`docker compose cp ~/dotfiles php:/root/dotfiles && docker compose exec php bash -c 'cd /root/dotfiles && stow zsh git vim'`。config 本身可攜、不分 distro（見 [GNU Stow](/linux/dotfile/knowledge-cards/gnu-stow/)）。

這樣 config 只維護一份，跟工作站共用；container 內只多了「裝套件」那一層 distro 分支。

## 邊界

ergonomics 進可寫層的代價是「不持久」：container 重建就沒了，每次 `docker exec` 重來或寫成啟動時自動跑的腳本。這是刻意的取捨——為了保住 image 的 parity，換來 ergonomics 每次重建要重裝。想持久化 ergonomics 又不碰 runtime image，正解是走 devcontainer 那套（見 [模組九：從個人到團隊](/linux/dotfile/09-team-environment/devcontainer-nix/)），它把開發環境跟 runtime image 明確拆成兩個 image。
