---
title: "模組一：管理工具與目錄結構"
date: 2026-06-29
description: "要把散落在家目錄的配置檔集中版控時，選 bare repo、stow 還是 chezmoi、目錄該怎麼組織"
tags: ["dotfile", "git", "stow", "chezmoi"]
---

Dotfile 管理的核心動作是把散落在家目錄各處的配置檔集中到一個 Git repo 裡版控。工具只是幫你處理「repo 裡的檔案怎麼對應到家目錄正確位置」這一層映射，選型看的是你的機器數量、OS 組合和 secret 需求。

## 三種主流策略

### Git bare repo：直接把家目錄當 work tree

bare repo 的概念是在家目錄建一個沒有工作目錄的 Git 倉庫，然後用 alias 指定 `--work-tree=$HOME`，讓 Git 直接追蹤家目錄下的檔案，不需要 symlink、不需要額外工具。

初始化：

```bash
git init --bare "$HOME/.dotfiles"
```

在 shell 配置裡加一行 alias：

```bash
alias dotfiles='git --git-dir="$HOME/.dotfiles" --work-tree="$HOME"'
```

之後所有 dotfile 操作都透過這個 alias：

```bash
dotfiles add ~/.zshrc
dotfiles commit -m "add zshrc"
dotfiles remote add origin git@github.com:you/dotfiles.git
dotfiles push -u origin main
```

第一件要做的事是隱藏未追蹤檔案。家目錄底下有成千上萬個檔案，如果不設定這一行，`dotfiles status` 會列出所有未追蹤的東西：

```bash
dotfiles config --local status.showUntrackedFiles no
```

新機器還原的流程：

```bash
git clone --bare git@github.com:you/dotfiles.git "$HOME/.dotfiles"
alias dotfiles='git --git-dir="$HOME/.dotfiles" --work-tree="$HOME"'
dotfiles config --local status.showUntrackedFiles no
dotfiles checkout
```

`checkout` 這步會把 repo 裡的檔案寫到家目錄。如果家目錄已經有同名檔案（例如系統預設的 `.bashrc`），checkout 會失敗並列出衝突檔案，需要先手動備份或刪除。

bare repo 適合配置量少、只管一台機器、不想安裝任何額外工具的人。它的限制是：概念對 Git 初學者不直覺（bare repo + work-tree 的組合不常見）、沒有模組化的概念（無法選擇性安裝某些配置）、多 profile 支援弱（不同機器要不同配置時只能靠 branch，長期維護困難）。

### GNU Stow：symlink 農場管理器

Stow 的概念是把 dotfile 集中放在一個普通目錄（如 `~/dotfiles`），然後用 stow 指令在家目錄建立 symlink。stow 的核心規則是：package 目錄內的路徑結構，就是安裝後相對於目標目錄的路徑結構。

```bash
# 安裝 stow
# macOS
brew install stow
# Arch Linux
sudo pacman -S stow
# Ubuntu/Debian
sudo apt install stow
```

以 zsh 配置為例，目錄結構長這樣：

```text
~/dotfiles/zsh/.zshrc
```

執行 `stow zsh` 後，stow 會在 `$HOME` 建一個 symlink：

```text
~/.zshrc -> ~/dotfiles/zsh/.zshrc
```

對於放在 `~/.config/` 底下的工具（XDG 規範），目錄結構映射同樣的邏輯：

```text
~/dotfiles/nvim/.config/nvim/init.lua
~/dotfiles/nvim/.config/nvim/lua/plugins.lua
```

執行 `stow nvim` 後：

```text
~/.config/nvim -> ~/dotfiles/nvim/.config/nvim
```

stow 會自動判斷該 symlink 整個目錄還是個別檔案——如果目標目錄不存在或目錄內所有檔案都由同一個 package 管理，stow 會 symlink 整個目錄（folding）；如果目標目錄已有其他檔案，stow 會展開（unfolding）成逐檔 symlink。

初始化和日常操作：

```bash
# 初始化
mkdir ~/dotfiles && cd ~/dotfiles
git init
git remote add origin git@github.com:you/dotfiles.git

# 把現有 .zshrc 搬進 dotfiles
mkdir -p ~/dotfiles/zsh
mv ~/.zshrc ~/dotfiles/zsh/.zshrc
cd ~/dotfiles && stow zsh
# 現在 ~/.zshrc 是一個 symlink，指向 ~/dotfiles/zsh/.zshrc

# 日常修改：直接編輯，symlink 透通
vim ~/.zshrc  # 實際編輯的是 ~/dotfiles/zsh/.zshrc
cd ~/dotfiles && git add -A && git commit -m "update zshrc"

# 新機器還原
git clone git@github.com:you/dotfiles.git ~/dotfiles
cd ~/dotfiles && stow zsh git nvim tmux
```

批次安裝所有 package：

```bash
cd ~/dotfiles
# stow 會把每個頂層目錄當成一個 package
stow */
```

移除某個 package 的 symlink：

```bash
cd ~/dotfiles && stow -D nvim
```

stow 適合中等複雜度的配置管理。它的優勢是模組化（每個工具獨立一個 package、可選擇性安裝）和概念直覺（目錄結構就是安裝後的樣子）。它的限制是只管 symlink 映射，不管套件安裝；跨 OS 的路徑差異（macOS 和 Linux 某些工具的配置路徑不同）需要自己處理。

### Chezmoi：多機器 dotfile 管理工具

Chezmoi 是專為 dotfile 管理設計的工具，原生處理 template、secret 管理和多機器差異。它把 dotfile 存在自己的 source directory（`~/.local/share/chezmoi`），用 `chezmoi apply` 把檔案實際寫入目標位置（不是 symlink，是複製）。

```bash
# 安裝
brew install chezmoi        # macOS
pacman -S chezmoi           # Arch
sh -c "$(curl -fsLS get.chezmoi.io)"  # 通用
```

基本操作：

```bash
# 初始化（會建立 source directory 和 Git repo）
chezmoi init

# 加入現有配置
chezmoi add ~/.zshrc
chezmoi add ~/.config/nvim

# 編輯（在 source directory 裡編輯，不是直接改家目錄的檔案）
chezmoi edit ~/.zshrc

# 預覽差異
chezmoi diff

# 套用到家目錄
chezmoi apply

# 推上遠端
chezmoi cd  # 進入 source directory
git add -A && git commit -m "update" && git push
```

chezmoi 的核心優勢是 template。同一份配置檔在不同機器可以產生不同內容：

```bash
# chezmoi 的 source directory 裡，檔案名稱加 .tmpl 後綴
# dot_zshrc.tmpl

export EDITOR="nvim"

{{- if eq .chezmoi.os "darwin" }}
export HOMEBREW_PREFIX="/opt/homebrew"
eval "$($HOMEBREW_PREFIX/bin/brew shellenv)"
{{- end }}

{{- if eq .chezmoi.os "linux" }}
export PATH="$HOME/.local/bin:$PATH"
{{- end }}
```

`chezmoi apply` 會根據當前機器的 OS 展開 template，macOS 上產生的 `.zshrc` 會包含 Homebrew 設定，Linux 上不會。

Secret 管理是另一個殺手功能。chezmoi 整合了 1Password、Bitwarden、pass、gopass、LastPass 等密碼管理器：

```text
# dot_gitconfig.tmpl
[user]
    name = Your Name
    email = {{ (onepasswordRead "op://Personal/Git Config/email").value }}
```

`chezmoi apply` 時會即時從 1Password 拉值填入，secret 不會存在 Git repo 裡。

chezmoi 適合管理多台異質機器（macOS 工作機 + Linux 伺服器 + Linux 桌面 VM）且有 secret 需求的人。它的代價是學習曲線最陡——要理解 chezmoi 自己的目錄命名慣例（`dot_` 前綴代表 `.` 開頭、`private_` 前綴代表權限 0600）、template 語法（Go template）、以及「source directory 和目標位置是兩份獨立的檔案」這個心智模型。

## 選型判讀

選工具看三個維度：機器數量、OS 組合、secret 需求。

只有一台機器、配置簡單 — bare repo 或 stow 都夠用，差別在於你喜不喜歡 symlink 的管理方式。bare repo 最輕量，stow 多一層模組化。

多台同質機器（都是 macOS 或都是 Linux）— stow。配置檔在同 OS 間差異小，不需要 template，stow 的模組化讓你可以只在桌面機安裝 hyprland package、伺服器只裝 zsh + git + tmux。

多台異質機器（macOS + Linux）但 secret 需求不高 — stow 加上 OS 分流仍然可行，下一節會完整說明做法。

多台異質機器（macOS + Linux）、有 secret 需求 — chezmoi。template 和 secret 管理是它存在的理由。

不確定 — 從 stow 開始。它的概念最直覺（目錄結構 = 安裝後位置）、遷移成本最低（要換到 chezmoi 時，目錄結構的概念是相通的；要換到 bare repo 則是刪掉 symlink、直接追蹤）。

## 目錄結構設計

不管用哪個工具，dotfile repo 的目錄結構都遵循同一個原則：每個工具（或 package）是一個頂層目錄，內部路徑反映安裝後在家目錄的相對位置。

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

## 跨平台共用一個 Repo（macOS + Linux）

macOS 跟 Linux 可以用同一個 dotfile repo。不需要 fork 成兩個 repo——兩個 repo 的同步成本會隨時間膨脹，改了 git config 或 neovim 設定要在兩邊各 commit 一次，忘了同步就漂移。

一個 repo 跨平台的做法是三層分離，每層處理不同粒度的差異：

### 第一層：stow 選擇性安裝

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

### 第二層：配置檔內的 OS 分流

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

### 第三層：local.zsh 放機器專屬設定

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

### 套件清單也分 OS

```text
~/dotfiles/
├── Brewfile              # macOS: brew bundle dump 產生
├── packages-arch.txt     # Arch Linux: pacman -Qqe > packages-arch.txt
└── ...
```

Bootstrap script 依 OS 讀對應的清單安裝套件。

### Stow 跨平台的邊界

這個三層模型適合「配置檔本身大部分通用、差異只在 PATH 和少數工具路徑」的狀況——也就是多數開發者的實際情境。判斷是否需要遷移到 chezmoi 的訊號：

- 同一份配置檔裡超過一半的行數是 OS 分流 → chezmoi template 更乾淨
- 需要在配置檔裡注入 secret（API key、token） → chezmoi 的 secret 管理是必要功能
- 管理的機器超過三種 OS/角色組合 → template 的條件判斷比 shell if-else 更可維護

多數情況下 stow + uname + local.zsh 就足夠。

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
