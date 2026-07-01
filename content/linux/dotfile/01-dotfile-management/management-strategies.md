---
title: "管理策略與選型"
date: 2026-06-29
description: "要選 dotfile 管理工具時回來讀 — bare repo、stow、chezmoi 的適用場景與選型判讀"
weight: 1
tags: ["dotfile", "git", "stow", "chezmoi"]
---

Dotfile 管理的核心動作是把散落在家目錄各處的配置檔集中到一個 Git repo 裡版控。工具只是幫你處理「repo 裡的檔案怎麼對應到家目錄正確位置」這一層映射，選型看的是你的機器數量、OS 組合和 secret 需求。

## Git bare repo：直接把家目錄當 work tree

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

## GNU Stow：symlink 農場管理器

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

stow 適合中等複雜度的配置管理。它的優勢是模組化（每個工具獨立一個 package、可選擇性安裝）和概念直覺（目錄結構就是安裝後的樣子）。它的限制是只管 symlink 映射，不管套件安裝；跨 OS 的路徑差異（macOS 和 Linux 某些工具的配置路徑不同）需要自己處理；stow 也不管 file permission——需要 0600 權限的 secret 檔（SSH private key、API token config）靠 symlink 繼承來源檔案權限，不能在部署過程中自動設定。

## yadm：bare repo 的升級版

yadm 包裝了 Git bare repo 的操作，加上三個 bare repo 缺少的能力：alternate files（依 OS、hostname、甚至 user 條件選擇安裝不同版本的配置檔）、encrypt（用 GPG 或 OpenSSL 加密敏感檔案、不依賴外部密碼管理器）、bootstrap script（clone 後自動跑初始化）。

```bash
# 安裝
brew install yadm          # macOS
sudo pacman -S yadm        # Arch

# 初始化（等同 git init --bare + 自動設定 alias）
yadm init
yadm remote add origin git@github.com:you/dotfiles.git

# 操作方式跟 Git 完全一樣
yadm add ~/.zshrc
yadm commit -m "add zshrc"
yadm push
```

Alternate files 的概念是在同一個 repo 裡放多個版本的同一個檔案，yadm 依條件決定用哪一個：

```text
~/.config/alacritty/alacritty.toml##os.Darwin
~/.config/alacritty/alacritty.toml##os.Linux
```

macOS 上 yadm 自動 checkout Darwin 版本、Linux 上 checkout Linux 版本。比 stow 的 shell if-else 判斷更乾淨，比 chezmoi 的 Go template 學習曲線低。

yadm 適合想要 bare repo 的簡單性、但需要條件安裝或 secret 加密的人。它的限制是沒有 stow 的模組化概念（無法選擇性只安裝某些工具的配置）、沒有 chezmoi 的 template 細粒度（alternate files 是整個檔案切換，不是檔案內的段落條件）。

## Chezmoi：多機器 dotfile 管理工具

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

多台異質機器（macOS + Linux）但 secret 需求不高 — stow 加上 OS 分流仍然可行，[跨平台共用一個 Repo](/linux/dotfile/01-dotfile-management/cross-platform-one-repo/) 會完整說明做法。

多台異質機器、需要條件安裝但不想學 template 語法 — yadm。alternate files 讓你依 OS/hostname 切換整個配置檔，內建 encrypt 處理 secret，Git 操作方式跟 bare repo 相同。

多台異質機器（macOS + Linux）、有細粒度 template 或密碼管理器整合需求 — chezmoi。檔案內的段落條件、跟 1Password/Bitwarden 的整合、`private_` 前綴的 permission 管理是它存在的理由。

不確定 — 從 stow 開始。它的概念最直覺（目錄結構 = 安裝後位置）、遷移成本最低（要換到 yadm 是加一層 wrapper、要換到 chezmoi 時目錄結構的概念是相通的）。
