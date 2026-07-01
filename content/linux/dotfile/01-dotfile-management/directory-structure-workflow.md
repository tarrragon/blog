---
title: "目錄結構、Git 工作流與常見陷阱"
date: 2026-06-29
description: "設計 dotfile repo 的目錄結構、或遇到 symlink 衝突和私鑰外洩等問題時回來讀"
weight: 3
tags: ["dotfile", "git", "stow"]
---

不管用哪個工具，dotfile repo 的目錄結構都遵循同一個原則：每個工具（或 package）是一個頂層目錄，內部路徑反映安裝後在家目錄的相對位置。

## 目錄結構設計

以 stow 為例的標準結構：

```text
~/dotfiles/
├── zsh/
│   └── .zshrc
├── git/
│   ├── .gitconfig
│   └── .gitignore_global
├── ssh/
│   └── .ssh/
│       └── config
├── nvim/
│   └── .config/
│       └── nvim/
│           ├── init.lua
│           └── lua/
├── tmux/
│   └── .config/
│       └── tmux/
│           └── tmux.conf
├── hyprland/
│   └── .config/
│       └── hypr/
│           └── hyprland.conf
├── waybar/
│   └── .config/
│       └── waybar/
│           ├── config.jsonc
│           └── style.css
├── scripts/
│   └── install.sh
├── Brewfile
├── packages.txt
├── .gitignore
└── README.md
```

這些設計選擇的理由：

**每個工具一個頂層目錄**。stow 的 package 概念讓你可以選擇性安裝——伺服器不需要 hyprland 和 waybar，只 stow 需要的 package。即使不用 stow，這個分法也讓 repo 結構清晰：看頂層目錄就知道管了哪些工具。

**目錄內路徑映射安裝位置**。`nvim/.config/nvim/init.lua` 安裝後變成 `~/.config/nvim/init.lua`。這個映射是 stow 的核心假設，但即使用 chezmoi 或 bare repo，維持同樣的思維讓目錄結構自解釋。

**scripts/ 不是 stow package**。`scripts/install.sh` 是 bootstrap 用的安裝腳本，不應該被 stow 到家目錄。它放在 repo 裡是為了讓新機器還原時有一個入口點可以跑。

**Brewfile / packages.txt 記錄套件清單**。配置檔只告訴工具「怎麼用」，但前提是工具已安裝。`Brewfile`（macOS 用 `brew bundle`）和 `packages.txt`（Linux 用套件管理器批次安裝）把「裝了什麼」也納入版控，讓新機器還原時不用靠記憶。

**ssh/ 只放 config，不放私鑰**。`~/.ssh/config` 記錄 SSH 連線設定（Host alias、ProxyJump 等），是有版控價值的配置。私鑰（`id_ed25519`、`id_rsa`）和公鑰不應進 dotfile repo，即使 repo 是 private。私鑰用密碼管理器或機器本地生成。

## Git 工作流

dotfile repo 的 Git 工作流比一般程式碼專案簡單，因為通常只有一個人在用，branch 和 PR 的需求低。

**日常修改**。直接編輯配置（symlink 透通到 repo 裡的實體檔案），然後 commit：

```bash
cd ~/dotfiles
git add zsh/.zshrc
git commit -m "zsh: add fzf integration"
git push
```

**新增一個工具的配置**。先在 dotfiles 建好目錄結構，把現有配置搬進去，建 symlink，然後 commit：

```bash
mkdir -p ~/dotfiles/alacritty/.config/alacritty
mv ~/.config/alacritty/alacritty.toml ~/dotfiles/alacritty/.config/alacritty/
cd ~/dotfiles && stow alacritty
git add alacritty/ && git commit -m "add alacritty config"
```

**新機器還原**。整個流程應該能在幾分鐘內完成：

```bash
# 1. 裝 Git 和 stow（通常是最先裝的兩個東西）
# 2. clone
git clone git@github.com:you/dotfiles.git ~/dotfiles
# 3. 安裝套件
cd ~/dotfiles
brew bundle          # macOS
# 或
xargs sudo pacman -S < packages.txt  # Arch
# 4. 建 symlink
stow zsh git nvim tmux ssh
# 5. 重開 shell，配置生效
```

## 常見陷阱

**私鑰進 repo**。把 `~/.ssh/` 整個目錄（含 `id_ed25519`）推上 GitHub 是最危險的錯誤。即使事後刪除，Git 歷史裡仍然留有私鑰。做法是只追蹤 `~/.ssh/config`，在 `.gitignore` 明確排除 `*.pem`、`id_*`。

**缺少 .gitignore**。很多工具會在配置目錄產生 cache、compiled 檔案、session 狀態。nvim 的 `plugin/packer_compiled.lua`、zsh 的 `.zcompdump`、tmux 的 `resurrect/` 都不該進 repo。建 repo 時第一件事就是寫 `.gitignore`。

**symlink 衝突**。`stow zsh` 時如果 `~/.zshrc` 已經存在且不是 symlink，stow 會拒絕操作。解法是先備份再安裝：

```bash
mv ~/.zshrc ~/.zshrc.bak
cd ~/dotfiles && stow zsh
```

**路徑寫死**。`.zshrc` 裡寫 `source /Users/mac-eric/.nvm/nvm.sh` 搬到 Linux 就壞了。改用 `$HOME`：`source "$HOME/.nvm/nvm.sh"`。配置檔裡每一處絕對路徑都是可攜性的隱患。

**整包 .config 放一個 package**。把 `~/.config` 整個目錄當成一個 stow package 會喪失模組化的好處，而且衝突風險大幅增加。正確做法是每個工具拆開：nvim 一個、tmux 一個、hyprland 一個。
