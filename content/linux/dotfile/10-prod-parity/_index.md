---
title: "模組十：Prod Parity — 跨發行版與線上環境對齊"
date: 2026-07-06
description: "工作站是 Arch 這種滾動最新版、但要開發的 client 線上跑的是凍結舊環境（PHP 7.2 / MySQL 5.7 / Debian）時回來讀 — dotfile 哲學怎麼跨 distro 落地、怎麼建對齊 prod 的 runtime"
weight: 10
tags: ["dotfile", "container", "prod-parity", "docker"]
---

前面的模組把個人工作環境用 dotfile 管起來，預設工作站跟你天天用的機器是同一套。實際接案 / 商用開發會撞上一個落差：工作站是 Arch 這種滾動更新、永遠最新版的環境，但要開發的 client 線上跑的是幾年前定版後就凍結的舊環境——PHP 7.2、MySQL 5.7、某個特定 Debian 世代。直接拿最新的 Arch 環境開發，寫出來的成品可能在線上根本跑不起來。

這個模組把 dotfile 的「環境可重現」思想延伸到兩個新對象：一是讓工作站 dotfile 跨到 client 常見的非 Arch 發行版，二是建一個跟線上逐項對齊的 runtime container。核心切分是三層，各自可重現、各自對齊不同目標。

## 三層切分

| 層                   | 是什麼                             | 對齊誰                  | 綁 distro 嗎                                  |
| -------------------- | ---------------------------------- | ----------------------- | --------------------------------------------- |
| 工作站               | 你的個人機（shell / wm / editor）  | 對齊你自己的順手        | 綁 pacman/brew/apt，靠抽象層跨 distro         |
| runtime              | 跑 app 的 PHP / MySQL / web server | 逐項對齊 client 的 prod | 不碰主機 package manager，parity 靠 image tag |
| container ergonomics | 你在 container 裡用的 shell / vim  | 純開發舒適              | 靠 detection 分支同時支援多 distro            |

三層的哲學是同一套（環境 as code、可重現），差別只在對齊誰、綁哪個 package manager。把三者混進同一個 artifact 是常見錯誤：ergonomics 混進 runtime image，image 就不再等於 prod、parity 破功。

## 章節文章

| 文章                                                                                   | 主題                                                    | 回答什麼問題                         |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------ |
| [工作站 dotfile 跨發行版落地](/linux/dotfile/10-prod-parity/workstation-cross-distro/) | 同一份 dotfile 從 Arch 跨到 Debian/Ubuntu               | 換 client 環境時哪些要改、哪些能共用 |
| [對齊 prod 的 runtime container](/linux/dotfile/10-prod-parity/prod-parity-runtime/)   | 建跟線上逐項對齊的 PHP 7.2 + MySQL 5.7 runtime          | parity 要對齊到多細、什麼時候值得    |
| [dotfile 跨進 runtime container](/linux/dotfile/10-prod-parity/container-ergonomics/)  | 把開發 ergonomics 帶進 Debian container 又不污染 parity | ergonomics 跟 runtime 怎麼分層       |

## 這個模組的知識點

三篇實作文章都薄，只講目的與判讀；背後的設定原理拆成獨立術語卡：

- [Prod Parity 原則](/linux/dotfile/knowledge-cards/prod-parity-principle/)：對齊凍結舊環境而非最新
- [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)：tag 要釘到 OS 世代才凍結得住
- [glibc 與 musl](/linux/dotfile/knowledge-cards/glibc-vs-musl/)：prod 是 Debian 就別用 alpine
- [Package Manager 抽象層](/linux/dotfile/knowledge-cards/package-manager-abstraction/)：綁 distro 的只有裝套件那一層
- [發行版打包粒度](/linux/dotfile/knowledge-cards/distro-package-granularity/)：同一指令跨發行版後果量級差多少
- [apt 安裝的交易原子性](/linux/dotfile/knowledge-cards/apt-transaction-atomicity/)：批次安裝為何全有或全無

## 實作 artifact

三層的實際檔案放在 dotfiles repo（不在教材裡）：工作站層是 repo 主體加 `scripts/install-debian.sh`，runtime 層是 `runtimes/php72-mysql57/`（Dockerfile + docker-compose），ergonomics 層是同目錄的 `ergonomics/setup.sh`。教材講判讀，repo 放可跑的設定。

## 跨分類引用

- → [模組九：從個人到團隊](/linux/dotfile/09-team-environment/)：devcontainer 是同一個「環境 as code」思想的團隊化形態
- → [模組八：同步、Bootstrap 與環境重建](/linux/dotfile/08-sync-bootstrap/)：跨 distro 安裝腳本是 bootstrap 的延伸
- → [Container 術語卡](/backend/knowledge-cards/container/)：container 作為服務交付單位的服務設計視角
