---
title: "GNU Stow"
date: 2026-06-29
description: "dotfile 管理文章裡提到 stow、symlink、package 看不懂時回來讀 — stow 的核心概念和常用指令"
weight: 2
tags: ["dotfile", "stow", "knowledge-cards"]
---

GNU Stow 是一個 symlink farm manager，原本設計給軟體安裝用（把 `/usr/local/stow/program/` 下的檔案 symlink 到 `/usr/local/`），在 dotfile 管理場景被借來做「把 repo 裡的配置檔 symlink 到家目錄」。

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

## 限制

- 只管 symlink 映射，不管套件安裝（套件由 Brewfile 或 packages.txt 處理）
- 不管 file permission——需要 0600 的 secret 檔靠 symlink 繼承來源權限，無法在部署時自動 chmod
- 沒有 template 機制——同一份配置在不同機器要不同內容時，需要在配置檔內用 shell 的 OS 判斷處理

完整選型比較見[管理策略與選型](/linux/dotfile/01-dotfile-management/management-strategies/)。
