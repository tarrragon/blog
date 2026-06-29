---
title: "macOS 新機基礎建設：套件管理與個人 bin 的設定順序"
date: 2026-06-27
description: "重灌或換機後最底層的三項基礎建設與它們的依賴順序：先裝 Homebrew 當套件管理基礎，再用它把凍在舊版的內建 bash 換成現代版本，最後掛上個人 bin 目錄。之後會持續增補。"
tags: ["macos", "setup", "homebrew", "bash", "tooling"]
---

重灌或換機後要補的設定很多，但有個底層順序不能跳：套件管理工具要先到位，後面的補強才裝得起來。這篇聚焦最底層的三項基礎建設（Homebrew、bash、個人 bin），按依賴順序排列。重點不只是「裝什麼」，而是「為什麼這個順序」；之後遇到的新需求會接在後面繼續增補。

## 先裝 Homebrew，它是後面一切的基礎

macOS 本身沒有內建的第三方套件管理工具，而後面幾乎每一項補強（命令列工具、開發語言、甚至部分 GUI App）都靠它安裝。沒有 Homebrew，這份清單的其他項目全部無從裝起，所以它排第一。

安裝過程會要求輸入登入密碼（sudo），並自動下載 Xcode Command Line Tools，畫面可能停住數分鐘屬正常。

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

裝完還要把 Homebrew 的執行檔目錄加進 PATH，shell 才找得到 `brew` 與之後用它裝的工具。Homebrew 的安裝前綴依晶片而異：Apple Silicon 機器裝在 `/opt/homebrew`、Intel 機器裝在 `/usr/local`。安裝腳本結尾會印出對應這台機器的設定指令，照它印的路徑寫進 `~/.zprofile` 讓每次開 shell 都生效。以下以 Apple Silicon 為例，Intel 機器把前綴換成 `/usr/local` 即可：

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

這一步做完，驗證安裝成功：

```bash
brew --version   # 應印出 Homebrew 4.x.x
```

版本號印出來，[Homebrew](/llm/knowledge-cards/homebrew/) 就能當後面所有項目的安裝來源。

## 把 bash 更新到 5.x

bash 是裝完 Homebrew 後最值得優先換掉的內建工具。macOS 的 `/bin/bash` 長年凍結在 3.2 系列（2006 年釋出，目前是 patchlevel 57），Apple 不再更新它，原因是 bash 4 改用 GPLv3 授權、Apple 不願隨系統散布。對寫腳本的人來說，這代表 associative array、`${var,,}` 大小寫轉換、`mapfile` 等近二十年的語法都用不了。

正確做法是用 Homebrew 另外裝一份新版並排存在，而不是覆寫系統版。`/bin/bash` 在唯讀的系統卷上、受 SIP（System Integrity Protection）保護，覆寫會被擋下：

```bash
brew install bash
```

這會把 bash 5.x 裝到 `/opt/homebrew/bin/bash`，完全不碰 `/bin/bash`。因為前一步已經把 `/opt/homebrew/bin` 排在 PATH 前面，用 `#!/usr/bin/env bash` 起手的腳本就會自動改用新版。裝完驗證一下版本確實切過去：

```bash
env bash --version   # 應顯示 5.x
/bin/bash --version  # 系統版仍是 3.2.57，沒被動
```

要留意的是互動 shell 在現代 macOS 預設是 zsh，這一步不影響它。更新 bash 的目的是給 `#!/usr/bin/env bash` 腳本一個現代執行環境，不是換登入 shell。真要把新版 bash 當登入 shell，才需要額外把它加進 `/etc/shells` 再 `chsh`。

## 把 ~/.local/bin 加進 PATH，放個人腳本

跟專案無關的小工具（例如 [disk-report](../macos_disk_space_diagnosis/) 與 [app-report](../macos_app_footprint_report/) 這類系統診斷腳本）需要一個能在任何地方直接呼叫、又不污染專案 repo 的家。慣例是個人的 `~/.local/bin`，把它建好並掛上 PATH。

```bash
mkdir -p ~/.local/bin
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zprofile
export PATH="$HOME/.local/bin:$PATH"
```

目錄建好、PATH 掛上後，確認它確實生效：

```bash
echo "$PATH" | tr ':' '\n' | grep "$HOME/.local/bin"
```

之後把腳本 symlink 進這個目錄就能直接當指令用。

## 後續項目

基礎建設到位後，第一個掛上去的實用腳本就是系統診斷：[磁碟空間診斷的 disk-report](../macos_disk_space_diagnosis/) 與 [按 App 聚合佔用的 app-report](../macos_app_footprint_report/)，兩支都 symlink 進 `~/.local/bin` 直接當指令用。

這份清單會隨著之後遇到的需求往下增補，新項目接在這裡。原則維持不變：基礎建設排前面，依賴它的補強排後面，每一項都寫清楚「為什麼要做」而不只是貼指令。
