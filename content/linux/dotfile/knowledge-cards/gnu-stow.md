---
title: "GNU Stow"
date: 2026-06-29
description: "dotfile 管理文章裡提到 stow、symlink、package 看不懂時回來讀 — stow 的核心概念和常用指令"
weight: 2
tags: ["dotfile", "stow", "knowledge-cards"]
---

GNU Stow 是一個 symlink farm manager，原本設計給軟體安裝用（把 `/usr/local/stow/program/` 下的檔案 symlink 到 `/usr/local/`），在 dotfile 管理場景被借來做「把 repo 裡的配置檔 symlink 到家目錄」——這是後續 [Rice](/linux/dotfile/knowledge-cards/rice/) 客製化能跨機器重現的部署基礎。

## 概念位置

GNU Stow 管的是檔案部署，跟 [AUR](/linux/dotfile/knowledge-cards/aur/) 負責的套件安裝是正交的兩件事——Stow 決定 repo 裡的配置檔怎麼連到家目錄，AUR/pacman 決定程式本身怎麼裝。它落地的內容通常是用 [Lua](/linux/dotfile/knowledge-cards/lua-scripting-language/) 或其他格式寫成的配置檔。

## 核心規則

Stow 的核心規則只有一條：**package 目錄內的路徑結構，就是安裝後相對於目標目錄的路徑結構**。

```text
~/dotfiles/zsh/.zshrc          → ~/.zshrc
~/dotfiles/nvim/.config/nvim/  → ~/.config/nvim/
~/dotfiles/git/.gitconfig      → ~/.gitconfig
```

每個頂層目錄（`zsh/`、`nvim/`、`git/`）是一個 stow package，可以獨立安裝或移除。

## 常用指令

```bash
cd ~/dotfiles

# 安裝：在目標目錄（預設 $HOME 的上一層，通常用 --target）建立 symlink
stow zsh                # 安裝 zsh package
stow zsh git nvim tmux  # 批次安裝多個 package
stow */                 # 安裝所有 package

# 移除：刪除該 package 建立的 symlink
stow -D nvim

# 重新安裝（移除 + 安裝）
stow -R zsh

# 收養：如果目標位置已有檔案，--adopt 把它移進 repo 再建 symlink
stow --adopt zsh
```

`--adopt` 是首次把現有配置納入 dotfile 管理時的關鍵操作——它把家目錄的既有檔案「收養」進 repo（移動過去），然後建 symlink。之後 `git diff` 就能看到 repo 版本跟原版的差異。

## Folding 與 Unfolding

Stow 會自動判斷要 symlink 整個目錄還是逐一 symlink 檔案：

- **Folding**：目標目錄不存在、或目錄內所有檔案都由同一個 package 管理 → symlink 整個目錄
- **Unfolding**：目標目錄已有其他來源的檔案 → 展開成逐檔 symlink，保留既有檔案不受影響

這個機制讓多個 package 可以共存於同一個目標目錄（如 `~/.config/`）。

### 實際部署時的形態轉換

同一個目標子目錄被第二個 package 加入時，stow 會自動從折疊形態過渡到展開形態。以三個 package 共用 `.config/hypr/` 為例：只有 `hyprland/` 一個 package 時，`~/.config/hypr` 是一條指向 repo 的**目錄 symlink**（folding）；`themes/` 也要往同一個子目錄放 `colors.conf` 時，stow 先拆掉目錄 symlink、建真實目錄、再把每個檔案各自 symlink 回所屬 package：

```text
$ stow themes
UNLINK: .config/hypr
MKDIR:  .config/hypr
LINK:   .config/hypr/hyprland.conf => ../../dotfiles/hyprland/.config/hypr/hyprland.conf
LINK:   .config/hypr/colors.conf   => ../../dotfiles/themes/.config/hypr/colors.conf
```

最終形態是真目錄 + 逐檔 symlink 各指各家的 package。這解釋了兩個常見的觀察困惑：

- **為什麼有時 `~/.config/X` 是 symlink、有時是真目錄**——取決於該目錄由一個還是多個 package 提供內容，兩種都是 stow 的正常形態。
- **為什麼 `readlink` 個別檔案看起來「不是 symlink」**——folding 形態下 symlink 在目錄那一層，檔案本身是順著目錄 symlink 走到 repo 裡的真實檔；判斷一個配置檔是否由 stow 管理，要從它往上逐層檢查到底哪一層是 symlink。

驗證部署結果時同一個錯覺會再出現一次：`ls -la ~/.config/waybar/`（帶斜線）會穿透目錄 symlink、列出裡面的普通檔案，看起來像 stow 沒建 symlink。權威讀法是 `ls -ld ~/.config/waybar`（不帶斜線，看目錄本身是不是 symlink）加 `stow --simulate`（讓 stow 自己報告會做什麼）。

## Symlink 與 git working tree 綁定

Stow 建立的 symlink 指向 repo 的 working tree，所以 working tree 一變、部署端立即跟著變——這既是它熱更新的來源，也是一個陷阱：`git reset --hard`、切分支、rebase 把某個 package 的檔案從 working tree 拿掉時，指過去的 symlink 當場變懸空，讀取該配置的程式會直接報「檔案不存在」（實測：Hyprland 監看 config 偵測到變動自動 reload，跳出 `source file is inaccessible` 錯誤橫幅）。動被 stow 管理的 repo 分支狀態前，先想一下部署端有哪些 symlink 會受影響；恢復 working tree 後配置即自動復原。

## 限制

- 只管 symlink 映射，不管套件安裝（套件由 Brewfile 或 packages.txt 處理）
- 不管 file permission——需要 0600 的 secret 檔靠 symlink 繼承來源權限，無法在部署時自動 chmod
- 沒有 template 機制——同一份配置在不同機器要不同內容時，需要在配置檔內用 shell 的 OS 判斷處理

完整選型比較見[管理策略與選型](/linux/dotfile/01-dotfile-management/management-strategies/)。
