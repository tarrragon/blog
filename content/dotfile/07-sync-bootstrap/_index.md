---
title: "模組七：同步、Bootstrap 與環境重建"
date: 2026-06-29
description: "換機器或重灌時怎麼還原工作環境 — bootstrap script 設計、套件清單管理、跨機器同步策略、secret 排除，以及 VM 快照和 dotfile 重建兩種思路的場景判讀"
tags: ["dotfile", "bootstrap", "sync"]
---

環境重建是 dotfile 管理的最終目的：拿到一台空白機器，能在可預期的時間內還原成你熟悉的工作環境。這件事有兩條根本不同的路線，選哪條決定了你之後所有的管理策略。

## 環境重建的兩種思路：拍照 vs 重建指令

第一種是**拍照**。VM 快照和磁碟映像（Clonezilla、`dd`）做的事是把整台機器某一刻的完整狀態凍結存檔——整個虛擬硬碟的 block-level 複製，有時連記憶體狀態都包含。還原就是把映像寫回去，系統回到那一刻，像時光倒流。Docker 的 `docker commit` 也屬於這個方向：把正在跑的 container 的檔案系統快照成一個 image。

第二種是**重建指令**。Dotfile repo + install script 描述的是「怎麼從一台空白機器組出這個環境」，每次都從零開始執行。Dockerfile 也是重建指令——一份「照著做就能重現」的食譜，描述每一步該安裝什麼、複製什麼、怎麼啟動。

兩條路的差異在本質上：

拍照產出的是**黑盒子**。一個磁碟映像是二進制檔案，沒人能看出裡面到底做了什麼設定、裝了什麼、改過什麼。它大（動輒 GB 級）、跟硬體耦合（換不同架構或不同顯卡可能開不起來）、無法做 diff 或 code review。

重建指令產出的是**白盒子**。每一步都是可讀的文字——這行裝 zsh、那行設定 Hyprland 的 keybind——可以被 review、被 diff、被另一個人讀懂。它小（通常幾十 KB）、跨硬體（同一份 script 加 OS 判斷就能跑在不同機器）、可以進版控走 PR 流程。

dotfile 管理選的是重建指令這條路。代價是你必須把環境建構的過程記錄清楚——每裝一個新工具、每改一個配置都要同步更新 repo。回報是任何一台機器、任何時間點，都能用一份 Git repo 重現你的工作環境。

## Bootstrap Script 設計

一份 bootstrap script 是重建指令的入口。它做三件事：安裝套件、部署配置檔、執行初始化設定。

### 範例結構

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
    if [[ "$SHELL" != "$(which zsh)" ]] && command -v zsh >/dev/null; then
        chsh -s "$(which zsh)"
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

### 設計原則

**冪等性**是最重要的性質。跑一次和跑十次結果相同。`pacman -S --needed` 只安裝缺少的套件、`stow` 只建立不存在的 symlink、`command -v` 在工具已存在時跳過安裝。冪等的 script 可以放心重跑——改了一個配置後重新 deploy，不會弄壞其他已經正確的部分。

**偵測 OS 分流**處理的是跨平台差異。macOS 用 Homebrew、Arch 用 pacman、Debian 系用 apt——套件管理器不同、套件名稱有時也不同（macOS 的 `coreutils` 在 Linux 是預裝的）。分流邏輯集中在 bootstrap script 裡，配置檔本身盡量保持跨平台一致。

**最少依賴**原則：script 本身只依賴 bash 和 curl（幾乎所有系統預裝），其他工具由 script 自己安裝。這確保你可以在一台只有 base system 的機器上直接跑 script。

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

## 跨機器同步策略

多台機器共用 dotfile repo 時，需要一套同步策略來處理「改了配置後怎麼讓其他機器也更新」。

### Git push/pull（手動）

最基本的做法：改了就 commit + push，另一台機器 pull + 重新 apply。優點是簡單、沒有額外依賴。缺點是容易忘記——你在公司機器上改了一個 alias，回家忘記 push，隔天公司又改了一版，兩邊 diverge。

適合只有一兩台機器、改動不頻繁的人。

### 自動同步

chezmoi 內建 `chezmoi update` 指令（pull + apply 一步完成），搭配 cron 或 systemd timer 定期執行：

```ini
# ~/.config/systemd/user/chezmoi-update.timer
[Unit]
Description=Update dotfiles daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# ~/.config/systemd/user/chezmoi-update.service
[Unit]
Description=chezmoi update

[Service]
Type=oneshot
ExecStart=/usr/bin/chezmoi update --no-tty
```

自動同步減少手動操作，但要注意衝突處理——如果兩台機器同時改了同一個檔案且都 push，後面那台的自動 pull 會遇到 merge conflict。實務上 dotfile 很少有真正的衝突（兩台機器同時改同一行的機率低），但偶爾發生時需要手動介入。

### 機器差異的處理

推薦的模式是 main branch 放所有共用配置，機器差異用條件判斷處理。

用 shell 的 OS 判斷：

```bash
# ~/.zshrc
if [[ "$(uname -s)" == "Darwin" ]]; then
    export PATH="/opt/homebrew/bin:$PATH"
    alias ls="ls -G"
else
    alias ls="ls --color=auto"
fi
```

用 chezmoi template（Go template 語法）：

```bash
# chezmoi 管理的 .zshrc.tmpl
{{ if eq .chezmoi.os "darwin" -}}
export PATH="/opt/homebrew/bin:$PATH"
{{ end -}}

{{ if eq .chezmoi.hostname "work-laptop" -}}
export HTTP_PROXY="http://proxy.corp:8080"
{{ end -}}
```

chezmoi template 的優勢是條件判斷發生在 apply 階段，產出的檔案裡看不到 template 語法，乾淨且不依賴 shell 的 runtime 判斷。

不推薦每台機器一個 branch 的做法。短期可行，長期一定 diverge——main 加了新配置，各 branch 要 rebase 或 merge，忘了就漂移。一份 main + template 條件判斷是長期可維護的結構。

## Secret 排除與管理

dotfile repo 通常是 public 或至少多人可見的。以下東西進了 repo 等於把鑰匙掛在門口：

- SSH 私鑰（`~/.ssh/id_*`、`*.pem`）
- API token、password、.env 檔案
- GPG 私鑰
- cloud provider 的 credential 檔案（`~/.aws/credentials`、`~/.config/gcloud/application_default_credentials.json`）
- browser profile 裡的 cookie / session

### .gitignore 是第一道防線

```gitignore
# SSH 私鑰
*.pem
id_*
known_hosts
authorized_keys

# 環境變數
.env
.env.*

# Cloud credentials
credentials
application_default_credentials.json
```

但 .gitignore 只防「不小心 add」，不防「故意 add -f」。更重要的是建立習慣：repo 裡永遠只放「看到了也沒關係」的東西。

### SSH config 的特殊處理

`~/.ssh/config`（host alias、ProxyJump 設定、port forwarding）本身不含 secret，可以進 repo——它記錄的是「連線要怎麼走」而不是「憑證是什麼」。但同一個 `~/.ssh/` 目錄下的私鑰絕對排除。

stow 管理時的目錄結構範例：

```text
dotfiles/
└── ssh/
    └── .ssh/
        └── config        # 進 repo
        # id_rsa 不放這裡
        # known_hosts 不放這裡
```

### 三個層級的 secret 管理

**層級一：手動**。.gitignore 排除 secret 檔案，在 README 記錄「這些東西需要在新機器手動設定」。最低成本、對只有一兩台機器的人足夠。

**層級二：密碼管理器整合**。chezmoi 支援從 1Password、Bitwarden、pass（Unix password manager）等拉取 secret：

```text
# chezmoi template 語法
{{ (onepasswordRead "op://Personal/SSH Key/private key").value }}
```

配置檔的 template 裡引用密碼管理器的條目，apply 時自動填入。secret 不在 repo 裡，但 repo 知道去哪拉。

**層級三：加密存放**。用 age 或 sops 把 secret 加密後直接存在 repo 裡。解密需要對應的 key。chezmoi 原生支援 age 加密：

```bash
# 加密一個檔案
chezmoi add --encrypt ~/.ssh/id_rsa

# repo 裡看到的是加密後的內容
cat ~/.local/share/chezmoi/private_dot_ssh/id_rsa.age
```

加密存放的好處是 secret 跟著 repo 走、不用另外設密碼管理器。風險是加密 key 本身變成唯一的依賴——丟了 key，加密的 secret 就拿不回來。

層級選擇取決於你的安全需求和便利需求的平衡。多數人從層級一開始，覺得手動處理太煩再往上升級。

## VM 快照 vs Dotfile 重建的場景判讀

兩種思路各有守備範圍，選擇取決於你要解什麼問題。

| 需求                             | VM 快照                      | Dotfile 重建                       |
| -------------------------------- | ---------------------------- | ---------------------------------- |
| 保留某一刻的完整系統狀態         | 適合（block-level 完整備份） | 只管配置層，不含系統狀態           |
| 在新機器還原工作環境             | 映像大、跟硬體耦合           | 跨硬體、輕量、一份 repo 多台 apply |
| 讓環境可被他人重現（onboarding） | 黑盒子、難維護、難 review    | 白盒子、可讀、可 PR                |
| 在多台機器維持一致               | 每台都要拍照、同步困難       | 一份 repo、Git push/pull           |
| 實驗後回滾（改壞了想恢復）       | 適合（秒級回滾）             | 靠 git revert + 重新 apply         |
| 讓桌面配置進 review 流程         | 二進制映像無法 diff          | 純文字、可 diff、可 code review    |

兩者不互斥。常見的組合是：用 dotfile 管理配置作為長期可維護的基線（每次變更都有 commit 紀錄），VM 快照用於短期實驗保護（要改一個不確定效果的設定前先拍照，改壞了秒回）。dotfile 是你的「正式版本」，VM 快照是你的「undo 按鈕」。

如果你用的檔案系統支援快照（ZFS、Btrfs），快照的成本極低（秒級、幾乎不佔空間），可以更積極地拍——每次改配置前拍一個、確認沒問題後刪掉。這不取代 dotfile 管理，而是補上 dotfile 管不到的層（系統狀態、套件版本、runtime 狀態）。

## 環境重建的實際流程

假設拿到一台全新的 Arch Linux 機器，要從零重建完整的 Hyprland 桌面環境。以下是 end-to-end 的步驟，對應 bootstrap script 的每個階段。

### 階段一：最小可用環境

```bash
# Arch 安裝完成後，base system 只有 bash 和基本工具
sudo pacman -S git base-devel
```

這是 bootstrap script 的唯一外部前提：有 Git 能 clone repo、有 base-devel 能編譯 AUR 套件。其他一切由 script 處理。

### 階段二：取得 dotfile repo

```bash
git clone https://github.com/you/dotfiles ~/dotfiles
cd ~/dotfiles
```

如果 repo 是 private，這一步需要先設定 SSH key 或用 HTTPS + token。這是前面提到的 secret 雞生蛋問題——你需要 SSH key 才能 clone 含有 SSH config 的 repo。解法通常是：第一次用 HTTPS clone，deploy 完 SSH config 後把 remote 改成 SSH。

### 階段三：執行 bootstrap

```bash
./scripts/install.sh
```

script 依序：安裝套件（Hyprland、waybar、rofi、wezterm、zsh、neovim、stow 等）、用 stow 部署配置到 `$HOME`、執行初始化（換 shell、安裝 neovim plugin）。

### 階段四：手動處理

bootstrap 處理不了（或不該處理）的部分：

- **SSH 私鑰**：從備份或密碼管理器取回，放到 `~/.ssh/`，設定正確權限（`chmod 600`）
- **Git 簽署用的 GPG key**：如果有用 commit signing
- **密碼管理器登入**：如果 secret 管理用了層級二或三

### 階段五：硬體相關調整

Hyprland 的 monitor 設定（解析度、縮放、排列位置）跟實際接的螢幕有關，這部分配置每台機器都不同：

```ini
# ~/.config/hypr/hyprland.conf 的 monitor 段
# 這幾行在每台機器上都要調
monitor=DP-1, 2560x1440@144, 0x0, 1
monitor=HDMI-A-1, 1920x1080@60, 2560x0, 1
```

處理方式有兩種：把 monitor 設定拆成獨立的 `monitor.conf`，主配置用 `source` 引入，`monitor.conf` 不進 repo（加進 .gitignore）、每台機器本地維護；或者用 chezmoi template 按 hostname 判斷。

顯卡驅動（Intel/AMD 通常自動、NVIDIA 需要額外安裝 `nvidia-dkms` 和設定環境變數）也是硬體相關的步驟，可以放在 bootstrap script 的 OS 判斷裡，但通常 Arch 安裝階段就已經處理。

### 階段六：驗證

```bash
# 登出 TTY，重新用 Hyprland 登入
# 或者直接在 TTY 執行
Hyprland
```

登入後確認：視窗管理器正常運作、keybind 正確、狀態列出現、字型正確渲染、終端機配色正常。如果某個元件沒反應，通常是套件沒裝或配置路徑不對——回去檢查 bootstrap 的套件清單和 stow 的 symlink。

### 時間預估

整個流程在網路順暢的情況下，大約 30 分鐘到 1 小時，取決於套件數量和下載速度。主要時間花在套件安裝（pacman 下載 + 編譯 AUR 套件）。配置 deploy 本身是秒級操作（stow 只建 symlink）。

對比沒有 dotfile 管理時的重建：邊想邊裝、裝了忘記某個工具的名稱、配置靠記憶手打、兩天後還在調某個快捷鍵為什麼不對。差距在「可預期 vs 碰運氣」。

## 維護節奏

環境重建能力需要持續維護，不是設定完就一勞永逸。

日常習慣：新裝一個工具時，順手更新套件清單（`brew bundle dump` 或手動加一行到 `packages.txt`）。改了一個配置後，commit + push。這個習慣的建立成本低，但需要刻意練幾週才會變成反射動作。

定期檢查：每隔幾個月在 VM 或 container 裡跑一次完整的 bootstrap，驗證 script 還能從零跑通。配置會演進、套件會改名或被取代、script 裡硬寫的路徑可能失效——定期驗證才能確保「這份重建指令真的能重建」，而不是一份過期的紀錄。
