---
title: "跨平台共用一個 Repo"
date: 2026-06-29
description: "macOS 跟 Linux 要共用同一個 dotfile repo、不想維護兩份時回來讀"
weight: 2
tags: ["dotfile", "stow", "cross-platform"]
---

macOS 跟 Linux 可以用同一個 dotfile repo。不需要 fork 成兩個 repo——兩個 repo 的同步成本會隨時間膨脹，改了 git config 或 neovim 設定要在兩邊各 commit 一次，忘了同步就漂移。

本文的做法基於 GNU Stow——將 dotfile repo 的檔案透過 symlink 對應到家目錄的工具（完整說明見[管理策略與選型](/dotfile/01-dotfile-management/management-strategies/)）。一個 repo 跨平台的做法是三層分離，每層處理不同粒度的差異：

## 第一層：stow 選擇性安裝

Stow 的 package 機制天然支持跨平台。repo 裡同時放 macOS 和 Linux 的配置，安裝時只 stow 該 OS 需要的 package：

```bash
# macOS
stow zsh git zellij btop broot

# Linux desktop
stow zsh git zellij btop broot hyprland waybar wofi mako
```

hyprland、waybar 這些目錄放在 repo 裡但 macOS 不 stow，不會有副作用。bootstrap script 裡用 `uname` 自動決定要 stow 哪些 package：

```bash
PACKAGES=(zsh git zellij btop broot)

if [[ "$(uname -s)" == "Linux" ]]; then
    for pkg in hyprland waybar wofi mako hyprlock; do
        [[ -d "$pkg" ]] && PACKAGES+=("$pkg")
    done
fi
```

## 第二層：配置檔內的 OS 分流

同一份配置檔裡，用 `uname` 區分 macOS 和 Linux 的差異。適合處理 PATH、工具初始化路徑這類「同一個用途、不同 OS 路徑」的狀況：

```bash
# path.zsh
typeset -U PATH
export PATH="$HOME/.local/bin:$PATH"    # 共用

if [[ "$(uname)" == "Darwin" ]]; then
    # Homebrew Ruby、FVM、Android SDK（macOS 路徑）
    [[ -d "/opt/homebrew/opt/ruby/bin" ]] && export PATH="/opt/homebrew/opt/ruby/bin:$PATH"
    export PATH="$HOME/fvm/default/bin:$PATH"
    export PATH="$PATH:$HOME/Library/Android/sdk/emulator"
fi

if [[ "$(uname)" == "Linux" ]]; then
    # Android SDK（Linux 路徑）
    [[ -d "$HOME/Android/Sdk/emulator" ]] && export PATH="$PATH:$HOME/Android/Sdk/emulator"
fi
```

```bash
# tools.zsh — autojump 的 source 路徑在兩個 OS 不同
if [[ "$(uname)" == "Darwin" ]]; then
    [ -f /opt/homebrew/etc/profile.d/autojump.sh ] && . /opt/homebrew/etc/profile.d/autojump.sh
else
    [ -f /usr/share/autojump/autojump.sh ] && . /usr/share/autojump/autojump.sh
fi
```

每個路徑加 `[[ -d ]]` 或 `[ -f ]` 存在性檢查——即使在正確的 OS 上，如果該工具沒裝也不會報錯。

## 第三層：local.zsh 放機器專屬設定

不是「macOS 的設定」而是「這台特定機器的設定」——工作專案 alias、公司 VPN proxy、只有這台機器需要的 PATH——放在 `~/.config/zsh/local.zsh`，不進 Git。

```bash
# .zshrc 裡的載入方式
[[ -f "$HOME/.config/zsh/local.zsh" ]] && source "$HOME/.config/zsh/local.zsh"
```

```bash
# ~/.config/zsh/local.zsh（不在 repo 裡，每台機器自己建）
alias unimall-dev='cd ~/project/unimall_shop && ./scripts/run_commands.sh dev'
alias unipos-dev='cd ~/project/unipos && ./scripts/run_commands.sh dev'
```

Repo 裡放一份 `local.zsh.example` 作為範本，`.gitignore` 裡排除 `local.zsh` 本身。

## 套件清單也分 OS

```text
~/dotfiles/
├── Brewfile              # macOS: brew bundle dump 產生
├── packages-arch.txt     # Arch Linux: pacman -Qqe > packages-arch.txt
└── ...
```

Bootstrap script 依 OS 讀對應的清單安裝套件。

## Stow 跨平台的邊界

這個三層模型適合「配置檔本身大部分通用、差異只在 PATH 和少數工具路徑」的狀況——也就是多數開發者的實際情境。判斷是否需要遷移到 chezmoi 的訊號：

- 同一份配置檔裡超過一半的行數是 OS 分流 → chezmoi template 更乾淨
- 需要在配置檔裡注入 secret（API key、token） → chezmoi 的 secret 管理是必要功能
- 管理的機器超過三種 OS/角色組合 → template 的條件判斷比 shell if-else 更可維護

多數情況下 stow + uname + local.zsh 就足夠。
