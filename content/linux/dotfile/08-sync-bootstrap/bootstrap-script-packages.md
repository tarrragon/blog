---
title: "Bootstrap Script 與套件清單管理"
date: 2026-06-29
description: "寫 dotfile 的 install script、或整理「這台機器裝了什麼」的套件清單時回來讀"
weight: 2
tags: ["dotfile", "bootstrap", "brewfile", "pacman"]
---

一份 bootstrap script 是重建指令的入口。它做三件事：安裝套件、部署配置檔、執行初始化設定。

## 範例結構

```bash
#!/usr/bin/env bash
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# --- 偵測 OS ---
OS="$(uname -s)"

install_packages() {
    if [[ "$OS" == "Darwin" ]]; then
        command -v brew >/dev/null || {
            echo "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        }
        brew bundle --file="$DOTFILES_DIR/Brewfile"

    elif [[ -f /etc/arch-release ]]; then
        sudo pacman -Syu --noconfirm
        sudo pacman -S --needed - < "$DOTFILES_DIR/packages.txt"
        # AUR 套件需要 AUR helper（假設已安裝 yay）
        if command -v yay >/dev/null && [[ -f "$DOTFILES_DIR/aur-packages.txt" ]]; then
            yay -S --needed - < "$DOTFILES_DIR/aur-packages.txt"
        fi

    elif [[ -f /etc/debian_version ]]; then
        sudo apt update
        xargs -a "$DOTFILES_DIR/apt-packages.txt" sudo apt install -y
    fi
}

deploy_configs() {
    if ! command -v stow >/dev/null; then
        echo "stow not found, skipping config deployment"
        return 1
    fi
    cd "$DOTFILES_DIR"
    for dir in zsh git nvim tmux hypr waybar; do
        [[ -d "$dir" ]] && stow -v --target="$HOME" "$dir"
    done
}

post_setup() {
    # 切換預設 shell
    if [[ "$SHELL" != "$(command -v zsh)" ]] && command -v zsh >/dev/null; then
        chsh -s "$(command -v zsh)"
    fi

    # neovim plugin 安裝（headless 模式）
    if command -v nvim >/dev/null; then
        nvim --headless "+Lazy! sync" +qa 2>/dev/null || true
    fi
}

echo "=== Installing packages ==="
install_packages

echo "=== Deploying configs ==="
deploy_configs

echo "=== Post-setup ==="
post_setup

echo "Done. Log out and back in for shell changes to take effect."
```

## 設計原則

**冪等性**是最重要的性質。跑一次和跑十次結果相同。`pacman -S --needed` 只安裝缺少的套件、`stow` 只建立不存在的 symlink、`command -v` 在工具已存在時跳過安裝（用 `command -v` 不用 `which`——後者在最小系統可能不存在）。冪等的 script 可以放心重跑——改了一個配置後重新 deploy，不會弄壞其他已經正確的部分。

**失敗可診斷**是這支範例為了聚焦結構而省略、但實際該有的性質。bootstrap 在陌生機器上失敗是常態，怎麼讓它在某一步掛掉時留下可定位的痕跡（全輸出 tee 落地 + ERR trap 點名出錯的行與指令），見 [可除錯的 bootstrap](/linux/install/observable-bootstrap/)——那篇是這支腳本的「失敗時看得見」那一層。

**偵測 OS 分流**處理的是跨平台差異。macOS 用 Homebrew、Arch 用 pacman、Debian 系用 apt——套件管理器不同、套件名稱有時也不同（macOS 的 `coreutils` 在 Linux 是預裝的）。分流邏輯集中在 bootstrap script 裡，配置檔本身盡量保持跨平台一致。

**最少依賴**原則：script 本身只依賴 bash 和 curl（幾乎所有系統預裝），其他工具由 script 自己安裝。這確保你可以在一台只有 base system 的機器上直接跑 script。不過「base system 直接跑」有個前提——最小安裝可能連 `sudo` 都沒有，而 script 裝套件正要靠它。跑這支 script 之前該驗證並補齊的前置工具，見 [最小安裝後的工具驗證與補足](/linux/install/minimal-install-verify/)。

**交付完整可用的環境**：script 的職責是讓部署完的配置「能直接用」，所以它必須裝齊配置實際引用的每一樣東西，而不是假設它們已經在。一個常見的破綻是把依賴寫進 README 的「dependencies」清單、卻沒在 script 裡實作安裝——例如 `.zshrc` 引用了 oh-my-zsh、主題、外掛，但 install script 只裝了 zsh 本身，結果 stow 部署完、第一次開 shell 就因為找不到那些東西而報錯。README 列依賴是給人看的、不會被執行；要讓配置真的能用，那些依賴得由 script 自己裝（例如把外掛 git clone 進對應位置）。檢查方式是反過來從配置出發：把每個 config 會 source 或引用的外部東西列出來，逐一確認 script 有沒有負責把它裝上。

**可部分執行**的結構：拆成 function，允許只跑某一段。除錯時只想重新 deploy 配置、不想重裝套件，直接呼叫 `deploy_configs` 就好。進一步可以把每段拆成獨立 script（`scripts/install-packages.sh`、`scripts/deploy-configs.sh`），bootstrap 入口只是依序呼叫它們。

## 套件清單管理

dotfile repo 管的是「配置」，但配置的前提是軟體已安裝。沒有附帶套件清單的 dotfile repo 是不完整的重建指令——你 clone 下來卻不知道該先裝什麼。

### macOS：Brewfile

```ruby
# Brewfile
tap "homebrew/cask-fonts"

# CLI 工具
brew "git"
brew "neovim"
brew "tmux"
brew "stow"
brew "ripgrep"
brew "fd"
brew "fzf"
brew "zsh"

# GUI app
cask "wezterm"
cask "rectangle"
cask "font-jetbrains-mono-nerd-font"
```

`brew bundle dump` 從當前系統產生 Brewfile、`brew bundle` 照 Brewfile 安裝。Brewfile 區分三種來源：`brew`（CLI formula）、`cask`（GUI app）、`tap`（第三方 repo）。把 Brewfile 放在 dotfile repo 根目錄，bootstrap script 用 `brew bundle --file=./Brewfile` 安裝。

### Arch Linux：packages.txt

```bash
# 匯出已安裝的 explicitly installed 套件
pacman -Qqe > packages.txt

# AUR 套件另外記
pacman -Qqem > aur-packages.txt
```

`-Qqe` 只列出使用者主動安裝的套件（不含被依賴自動拉進來的），這是你實際需要管理的範圍。`-Qqem` 進一步篩出外部來源（AUR）。還原時用 `pacman -S --needed - < packages.txt`，`--needed` 跳過已安裝的。

### Ubuntu/Debian

apt 的匯出格式比較雜。務實做法是手動維護一份清單檔（`apt-packages.txt`），每行一個套件名，用 `xargs -a apt-packages.txt sudo apt install -y` 安裝。比起 `apt list --installed` 的完整匯出（包含大量系統依賴），手動維護的清單更乾淨、更容易讀懂。

### 為什麼套件清單要進 repo

一個常見的失敗模式：dotfile repo 裡有完整的 neovim 配置，clone 到新機器後發現 neovim 沒裝、ripgrep 沒裝、字型沒裝，配置跑起來全是 error。套件清單跟配置檔放在同一個 repo，bootstrap script 才能先裝套件再 deploy 配置，形成完整的重建鏈路。
