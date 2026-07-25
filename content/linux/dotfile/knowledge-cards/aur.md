---
title: "AUR（Arch User Repository）"
date: 2026-07-03
description: "教材裡叫你 paru -S 某個套件、或說某工具「官方 repo 沒有、要走 AUR」、想搞懂 AUR 是什麼、跟官方 repo 差在哪、build-from-source 的代價時讀"
weight: 10
tags: ["dotfile", "linux", "arch", "aur", "package-management"]
---

AUR（Arch User Repository）是 Arch 的社群自建套件庫：官方 repo 沒收的軟體，由使用者上傳一份叫 `PKGBUILD` 的建置腳本，別人抓下來在自己機器上**從原始碼編譯**成套件再安裝。它補的是官方 repo 的覆蓋缺口——冷門工具、專有軟體的封裝、開發版（`-git`）套件，多半只在 AUR。跟 [Package Manager 抽象層](/linux/dotfile/knowledge-cards/package-manager-abstraction/) 抽象掉的官方套件管理員不同，AUR 是 Arch 特有的第三方來源。

## 概念位置

相關概念：[GNU Stow](/linux/dotfile/knowledge-cards/gnu-stow/)（dotfile 部署、與套件管理正交）、[Compositor](/linux/dotfile/knowledge-cards/compositor/)（Hyprland 等常以 `-git` AUR 套件安裝）、[平台差異](/linux/install/platform-divergence-map/)（AUR 是 Arch 特有、其他發行版有各自的第三方套件來源）。

跟官方 repo 的關鍵差別是「誰建置、誰背書」。官方 repo 的套件由 Arch 維護者預先編譯成二進位、簽章、掛在鏡像上，`pacman -S` 直接下載裝好。AUR 只存 `PKGBUILD` 腳本本身，不存編譯好的成品——你裝 AUR 套件是「抓腳本 → 在你機器上 build → 裝」，沒有官方簽章背書。所以 AUR 套件要自己看一眼 `PKGBUILD` 在做什麼（社群審查、不是官方保證），且 build 需要時間與 build 依賴（`base-devel`）。

`pacman` 本身不碰 AUR——它只管官方 repo。裝 AUR 套件靠 **AUR helper**：`paru`、`yay` 是最常見的兩個，它們把「抓 PKGBUILD → 解 AUR 依賴 → build → 交給 pacman 裝」自動化成一句 `paru -S <套件>`。所以教材寫 `paru -S mutagen.io-bin` 而不是 `pacman -S`，就是在說「這個套件在 AUR、要用 helper 裝」。

判讀訊號：`pacman -S <名字>` 找不到、或裝到一個名字像但功能無關的套件（例 `pacman -S mutagen` 會裝到音訊 metadata 函式庫 `python-mutagen`、不是同步工具 mutagen），代表你要的東西在官方 repo 沒有、該去 AUR 查正確的套件名（`paru -Ss <關鍵字>` 搜）。build-from-source 的代價是：慢（大套件編譯要時間）、可能因上游改動或缺 build 依賴而建置失敗——建置失敗的分層判讀（資源 / 二進位漂移 / 烤入路徑 / 架構宣告）見 [AUR 建置失敗的分層判讀](/linux/debug/aur-build-failure-triage/)。
