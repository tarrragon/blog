---
title: "VM 實測流程記錄：從零建 Hyprland 桌面"
date: 2026-06-30
draft: true
description: "在 UTM VM 從零建 Linux + Hyprland 桌面的逐步實作流程、需要回查實際下了什麼指令 / 遇到什麼錯 / 怎麼排除時讀"
weight: 100
tags: ["dotfile", "hyprland", "vm", "utm", "handson", "record"]
---

這份是 dotfile 教材模組四到八的 VM hands-on 實測記錄。教材（`content/dotfile/`）負責概念與配置邏輯，這份記錄負責「實際在 VM 裡跑的時候發生了什麼」——下的指令、回饋的情況、除錯的過程、遇到的瓶頸。記錄是時間序的，按 [環境建置的操作順序](/dotfile/00-dotfile-mindset/setup-order-guide/) 的階段分節，供之後教學回顧與回寫教材 `[待實測驗證]` 標記使用。

## 實測環境

| 項目         | 值                                             |
| ------------ | ---------------------------------------------- |
| 宿主機       | Apple Silicon Mac（macOS Darwin 24.3.0）       |
| 虛擬化       | UTM GitHub release 版（免費 + Venus/MoltenVK） |
| Guest OS     | Arch Linux ARM（archboot aarch64 ISO 安裝）    |
| 桌面         | Hyprland（Wayland compositor）                 |
| dotfile repo | 下終端機的實作專案（從零開始）                 |

## 階段零：VM 建置

### 為什麼是 UTM 而不是其他虛擬化軟體

選型用「這次任務的硬限制」篩，不是泛泛比較——換個任務（例如 headless server 測試）答案會不一樣。三個硬限制：

1. 宿主是 Apple Silicon（ARM64）——候選必須原生支援 ARM Mac。
2. 要跑完整圖形桌面 + GPU 加速——Hyprland 是 Wayland compositor，沒有 GPU 3D 加速（VirGL/Venus）就起不來或卡到不可用。這條最關鍵。
3. 免費 + 可重現——教材讀者照著做不該被付費牆擋住。

候選逐一被刷掉的原因：

| 軟體                      | 為什麼這次不選                                                                                                  |
| ------------------------- | --------------------------------------------------------------------------------------------------------------- |
| VirtualBox                | Apple Silicon 上的 ARM 支援長期是實驗性、不穩，出局。                                                           |
| Lima / colima / multipass | 都是 headless server VM 工具，沒有圖形桌面通道，Hyprland 無從談起——限制 2 擋掉。                                |
| Parallels Desktop         | ARM Linux 跑得最順、GPU 也好，但要付費授權，違反限制 3。                                                        |
| VMware Fusion             | 個人免費，但對 ARM Linux guest 的 Wayland + GPU 加速支援比 UTM 弱、VirGL 路徑不完整，易踩坑。                   |
| 裸 QEMU CLI               | UTM 底層就是包 QEMU。手寫能做到一樣的事，但 device tree、virtio-gpu、display 參數要自己拼，門檻太高、不可重現。 |

UTM 是這三個限制交集裡唯一全中的：QEMU 的 GUI 封裝、Apple Silicon 原生、免費開源，而且把 `virtio-gpu-gl-pci`（Venus/VirGL 加速顯卡）做成下拉選單就能選——用 GUI 拿到裸 QEMU 的 GPU 加速能力，卻不用手拼參數。收斂：QEMU 給能力、Apple Silicon 給原生、GUI 給可重現性、開源給免費，四個一起滿足的只有 UTM。

### ISO 選型：archboot 而非 archlinuxarm.org

教材 `hyprland-vm-setup.md` 寫「Arch Linux ARM（archlinuxarm.org）」，但 archlinuxarm.org 提供的是 SBC（樹莓派那類）用的 rootfs tarball，沒有給 UTM/QEMU 用的安裝 ISO。Apple Silicon UTM 上裝 Arch ARM 的可行路徑是 **archboot** 的 aarch64 ISO——archboot 是 Arch 的網路安裝 / 救援環境，開機後跑互動式 `setup` 從網路安裝最新 Arch ARM，所以 VM 必須能上網。

取得點（鏡像三選一，2026-06-30 build）：

```text
https://release.archboot.com/aarch64/latest/iso/
```

當天目錄下有三個 aarch64 ISO：

| 檔名後綴                  | 大小    | 用途                                   |
| ------------------------- | ------- | -------------------------------------- |
| `ARCH-aarch64.iso`        | ~469 MB | 標準版，開機後從網路裝最新套件（建議） |
| `ARCH-latest-aarch64.iso` | ~296 MB | 較小，latest kernel                    |
| `ARCH-local-aarch64.iso`  | ~1 GB   | 內含 local package repo，可離線安裝    |

本次用標準版 `archboot-2026.06.30-02.27-7.1.1-1-aarch64-ARCH-aarch64.iso`。

### 前置步驟（UTM + ISO，可並行）

兩件事並行做（都在宿主機 macOS）：

裝 UTM（GitHub release 版，brew cask 來源就是 GitHub release 的 UTM.dmg）：

```bash
brew install --cask utm
```

結果：`utm was successfully installed!`、版本 4.7.5。

下載 archboot ISO：

```bash
cd ~/Downloads
curl -L -O "https://release.archboot.com/aarch64/latest/iso/archboot-2026.06.30-02.27-7.1.1-1-aarch64-ARCH-aarch64.iso"
```

下載完驗證檔案完整（怕下到半截）：

```bash
ls -lh ~/Downloads/archboot-*.iso
# .rw-r--r--@ 481M ... archboot-2026.06.30-02.27-7.1.1-1-aarch64-ARCH-aarch64.iso
shasum -a 256 ~/Downloads/archboot-*.iso
# 41b382e7a462ca642a81f18a41c7c08198e4afd9b0816192764d247da7f11040
```

481 MB（= 458 MiB，跟 curl 進度條一致），檔案完整。

**gotcha（archboot 對網路的硬依賴）**：archboot 不是「ISO 內含完整系統、裝完即用」的離線安裝器，而是 Arch 的網路安裝環境——開機進去跑互動式 `setup`，從網路抓最新 Arch ARM 套件。所以這台 VM 從第一次開機就必須能上網（UTM 預設 NAT 即可）。這點教材原本沒講，要回寫。

### VM 參數定案

| 項目        | 值                                                                 |
| ----------- | ------------------------------------------------------------------ |
| 引擎        | QEMU（虛擬化技術，非 Apple Virtualization）                        |
| 系統架構    | ARM64 (aarch64)，QEMU 10.0 virt-10.0                               |
| 記憶體      | 4 GB                                                               |
| CPU         | 4 核                                                               |
| 儲存        | 20 GB（qcow2 稀疏配置，實際只吃寫入量；base + Hyprland 約 6–8 GB） |
| 網路        | 共享網路 virtio-net-pci（NAT，archboot 連網靠它）                  |
| 顯示卡      | virtio-gpu-gl-pci（GPU Supported，VirGL/Venus 加速）               |
| OpenGL 加速 | 啟用                                                               |

**顯示卡選型**：UTM 勾「啟用 OpenGL 硬體加速」後會自動把模擬顯示卡設成 `virtio-gpu-gl-pci`。下拉清單裡的對照——`virtio-gpu-pci`（無 gl）沒 3D 加速、Hyprland 會 fallback 軟體渲染或起不來；`virtio-ramfb-gl` 也有加速但 ramfb 偏向開機早期 framebuffer；`apple-gfx-pci` 是 Apple Virtualization 後端用的、走 QEMU 不適用。主顯示卡用 `virtio-gpu-gl-pci` 最穩。

**待驗證（回寫教材重點）**：UTM 硬體頁對「啟用 OpenGL 硬體加速」標了警告——「部分新版 Linux 驅動有已知問題：黑畫面、合成畫面破碎、應用程式無法渲染」。這正對應教材 `hyprland-vm-setup.md` 的 `[待實測驗證]`：VirGL/Venus 加速在這組 kernel + UTM 版本上會不會讓 Hyprland 中黑畫面。先勾起來往「能跑」方向走，中了就記錄並回這頁取消重試。結果待開機後填。

## 階段一：基礎設施（OS / SSH key / Git / clone）

### archboot 安裝流程（launcher → setup）

開機 `Hit ENTER for login routine` 後，archboot 自動帶起 launcher，先過一串前置：Locale → Network Interface → Timezone → Date/Time → Package Mirror，再進 Launcher Menu 選 `1 Launch Archboot Setup`，進入四階段 Setup Menu（Prepare Storage / Install Packages / Configure System / Install Bootloader）。

前置各關的選擇與理由：

| 關卡              | 選擇                       | 理由                                                              |
| ----------------- | -------------------------- | ----------------------------------------------------------------- |
| Locale            | en_US English              | 系統語系留英文，錯誤訊息 / log / 社群文件對得上；繁中在桌面層處理 |
| Network Interface | enp0s1（virtio-net-pci）   | 唯一介面，就是 UTM NAT 網卡                                       |
| IP 取得           | DHCP（archboot 自動選）    | UTM NAT 自動發 IP，不手動設 static                                |
| Proxy             | 留空                       | 走 NAT 直接出網                                                   |
| Timezone          | Asia/Taipei                | 當地時區                                                          |
| Package Mirror    | tw.mirror.archlinuxarm.org | 在台灣選台灣鏡像，1 GB+ 套件下載最快；清單還有 tw2                |

**證實 archboot aarch64 裝的是 Arch Linux ARM**：Package Mirror 清單全是 `archlinuxarm.org` 鏡像（ARM 移植版），跟 ISO 選型那段對得上——這條安裝路徑產出的是 Arch Linux ARM、不是 x86 Arch。

### 磁碟分割（Prepare Storage Device）

| 關卡               | 選擇                    | 理由                                                                                    |
| ------------------ | ----------------------- | --------------------------------------------------------------------------------------- |
| 分割方式           | Quick Setup（清空整碟） | VM 專屬空碟、清掉零代價；任務目標是測 dotfile/Hyprland 不是學分割，手動分割是雜訊       |
| Device Name Scheme | PARTUUID                | GPT 標準；綁分區、跨重開機穩定、重格檔案系統也不變（FSUUID 重格就變）                   |
| ESP 掛載點         | /boot（SINGLEBOOT）     | 單一 OS、不雙開；kernel 跟開機檔同分區、維護單純。MULTIBOOT 是多系統共用 ESP 才需要     |
| ESP 大小           | 512 MiB                 | SINGLEBOOT 下 kernel+initramfs 也住這；單 kernel 約 100–200 MB，512 夠用                |
| Swap               | 2048 MiB                | 4 GB RAM VM 編譯 AUR 套件易 OOM，2 GB swap 當安全墊；mkswap 只寫 header、稀疏不佔宿主碟 |
| 檔案系統           | ext4                    | 簡單穩、ARM 零驚喜；btrfs 的 snapshot/subvolume 對演練是雜訊                            |
| /home 分區         | 0（不獨立、全給 /）     | 用完即丟 VM 不需要「重灌保資料」；17.9 GB 切兩半易一邊爆一邊空，單池最不出事            |

最終分割佈局：512 MiB ESP（/boot）+ 2048 MiB swap + ~17.9 GB ext4 root（/，含 /home）。

**待驗證 / 教材回寫候選**：以上每關（Quick Setup vs 手動、SINGLEBOOT vs MULTIBOOT、ext4 vs btrfs、獨立 /home vs 單池、swap 大小）都是教材該補的決策卡——教材原本沒展開這些 trade-off。手動分割、LVM、LUKS、btrfs 快照、獨立 /home 各自是真實機器的儲存主題，值得另開、別混進 dotfile 演練。

### Configure System 與首次開機

System Configuration 清單裡 archboot 多數項已預填好（locale.conf / vconsole / mirrorlist / fstab），只需手動處理三項：

| 項目            | 操作                                                               | 理由                                                                    |
| --------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| User Management | 建 user `tar`，回答「Enable as Administrator / wheel group」選 Yes | Hyprland 不該用 root 跑、dotfile 部署到一般 user 的 $HOME；wheel = sudo |
| /etc/locale.gen | nano Ctrl+W 搜 `en_US.UTF-8 UTF-8`、Backspace 刪行首 `#`           | 沒解開 locale 系統會一堆 warning                                        |
| /etc/hostname   | 改成 `arch-hyprland`                                               | 預設是佔位字 myhostname                                                 |

其餘決策卡：

- **編輯器**：選 nano（底部顯快捷鍵 `^O` 存 / `^X` 離，比 neovim 直覺）。
- **mkinitcpio early userspace**：選 BUSYBOX（純 ext4、無加密無 LVM，systemd initramfs 的功能用不到）。
- **Set Default Shell**：跳過。最小 base 只有 bash、zsh 還沒裝；shell 留 bash、階段二再用 dotfile bootstrap 裝 zsh 切換。
- **Bootloader**：選 GRUB_UEFI 而非 EFISTUB。理由是 VM 風險——EFISTUB 全靠 UEFI NVRAM 開機項，QEMU/UTM 的 EFI 變數儲存有時不穩、NVRAM 項一掉就開不了機；GRUB 另在 ESP fallback 路徑 `\EFI\BOOT\BOOTAA64.EFI` 放一份、NVRAM 丟了仍能開機，又有救援選單。GRUB config（/etc/default/grub）不用改、VM 預設值即可。

**退 ISO 的坑**：裝完選 Poweroff（不是 Reboot，Reboot 會繞回 archboot ISO）。關機後 UTM 資訊面板的 CD/DVD 顯示「(無)」= ISO 已退，再開機就從硬碟 GRUB 進新系統。GRUB 選單出現 `Arch Linux` 項 = ISO 退乾淨、bootloader 裝對。

**正面發現（回寫教材）**：原本擔心 archboot 裝機時設的 DHCP 不會帶進新系統（VM 裝 Arch 常見斷網點）。實測結果是**會帶進去**——首次開機 `ip -brief a` 顯示 `enp0s1` UP、拿到 `192.168.64.5/24`（UTM 共享網路 vmnet 網段），`ping archlinux.org` DNS 解析到 209.126.35.79，對外網路 + DNS 都通。archboot 的 setup 會把 `/etc/systemd/network/enp0s1-ethernet.network` 複製到目標系統並啟用 systemd-networkd，網路免再手動設。

**輸入掉字觀察**：`ip -brief a; echo ---; ping -c 3 archlinux.org` 一次貼進去時 `---; ping` 段被吃掉、變成 `echo -c 3 archlinux.org`。複合指令在這個 console 一次貼多段有掉字風險，分段下比較穩。

## 階段二：Shell 與終端機

### 工作流基建：SSH key + host↔VM 傳輸

**痛點**：UTM console（TTY）不能貼上，手打長指令會掉字。**解法**：讓 VM 跑 sshd，從 host 的真終端機 SSH 進去操作——SSH session 在真終端機裡、貼上正常。這同時是 dotfile 模組階段一的 SSH 主題。

VM 端起 sshd（在 UTM console 手打這兩條短指令）：

```bash
pacman -S openssh            # 剛裝好的系統 db 是新的，-S 不必 -Sy
systemctl enable --now sshd
```

從 host 連：`ssh tar@192.168.64.5`（IP 來自 `ip -brief a`）。**用 tar 不用 root**——Arch sshd 預設 `PermitRootLogin prohibit-password`、擋 root 密碼登入。

**SSH key 免密碼**（讓 rsync / 自動化免密碼）：host 沒有任何 key，建一把專用 key 不佔預設槽，加 SSH config 別名：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/vm_arch -N "" -C "vm_arch host->utm"
# ~/.ssh/config 加:
#   Host arch-vm
#       HostName 192.168.64.5
#       User tar
#       IdentityFile ~/.ssh/vm_arch
#       IdentitiesOnly yes
```

public key 裝進 VM：因為 SSH session 在真終端機、可貼上，直接在 VM session 貼 `echo "ssh-ed25519 ..." >> ~/.ssh/authorized_keys`（比 ssh-copy-id 少一次離開 session）。之後 `ssh arch-vm` 免密碼。

**dotfiles 進 VM 的傳輸坑**：

- VM 最小安裝**沒有 rsync**（`rsync: command not found`）；host 的是 Apple 老版 rsync 2.6.9。第一次傳輸改用 **tar over SSH**（只需 ssh + tar）：`tar czf - --exclude .git . | ssh arch-vm 'mkdir -p ~/dotfiles && tar xzf - -C ~/dotfiles'`。
- **macOS tar 會夾帶 AppleDouble metadata 檔**（`._.gitignore` `._Brewfile` `._broot` …），在 Linux 是垃圾、會讓 stow 產生垃圾 symlink。要加 `COPYFILE_DISABLE=1` 關掉：`COPYFILE_DISABLE=1 tar czf - ...`。重傳後 `._*` 消失。
- VM 端 GNU tar 解 macOS 包會噴 `Ignoring unknown extended header keyword 'LIBARCHIVE.xattr.com.apple.provenance'`——無害，檔案正常解出。

**sudo 需密碼**：archboot 的「Enable as Administrator」設的是 `%wheel ALL=(ALL) ALL`（需密碼），不是 NOPASSWD。所以 `sudo pacman` 不能從 host 非互動 SSH 跑，install.sh 由使用者在 VM session 跑（互動輸密碼）。分工：host 負責編輯 dotfiles + 傳輸 + 唯讀檢查，VM session 負責跑 install.sh + 看結果。

### Baseline：現有 install.sh 在 Arch 上跑

第一次在 VM 跑 `./scripts/install.sh`，把缺口全炸出來。四個發現：

**發現一：base 沒有 sudo（前置缺口）**。最小 archboot `base` 安裝不含 sudo，裝機時選「Enable as Administrator / wheel」只把 tar 加進 wheel 群組、沒裝 sudo 也沒啟用 sudoers wheel 行。install.sh 第一行 `sudo pacman` 直接 `sudo: command not found`。這是 chicken-and-egg：install.sh 用 sudo 裝套件、但 sudo 自己得先在，所以 sudo 不能放進 `packages-arch.txt`（那是靠 sudo 裝的）、只能當「跑 bootstrap 前的前置」。修法（root 身分）：

```bash
su -
pacman -S --needed sudo
echo '%wheel ALL=(ALL:ALL) ALL' > /etc/sudoers.d/10-wheel
chmod 440 /etc/sudoers.d/10-wheel
visudo -c           # 印 parsed OK 才安全
exit
```

**發現二：install.sh 的 `which` bug**。最後換 zsh 那段 `chsh -s "$(which zsh)"` 報 `which: command not found`——最小 Arch 不含 `which`（獨立套件）。`$(which zsh)` 變空 → `chsh -s ""` → `chsh: shell must be a full path name`。而 `set -euo pipefail` 讓腳本在此中斷、後面 "Done" 沒印、**預設 shell 沒換成 zsh**。修法：`which zsh` → `command -v zsh`（POSIX builtin、一定在）。已修。註：`/usr/bin/zsh` 本來就在 `/etc/shells`、非 root chsh 不會被擋，唯一問題就是空路徑。

**發現三：packages-arch.txt 不存在**。install.sh 的 Arch 分支會讀 `$DOTFILES_DIR/packages-arch.txt` 補裝套件，但 repo 沒這檔、所以只裝了 `stow git zsh`，沒有任何桌面套件。

**發現四：Hyprland stow package 不存在**。install.sh 想 stow `hyprland waybar wofi mako hyprlock`，但這五個目錄都不在 repo、全跳過。Hyprland 完全沒被部署。

**正常運作的部分**：sudo 修好後，pacman 裝 `stow git zsh` 成功；stow 五個既有 package（zsh/git/zellij/btop/broot）全部正確建 symlink——`~/.zshrc` `~/.zshenv` `~/.gitconfig` 與 `~/.config/{broot,btop,git,zellij,zsh}` 都指回 `dotfiles/`。install.sh 的 stow 機制本身在 Arch 上沒問題，缺的是 Arch/Hyprland 的內容與兩個前置修正。

**回寫教材**：setup-order-guide 要補「跑 dotfiles bootstrap 前的前置：裝 sudo + 啟用 wheel」這一步——它不能由 bootstrap 自身完成。

## 階段三：桌面環境（Hyprland + Rice）

### 第一步：最小可跑 + 驗 virtio-gpu（成功）

建最小集：`packages-arch.txt`（`hyprland` + `foot`）+ `hyprland/.config/hypr/hyprland.conf`（monitor、`cursor { no_hardware_cursors = true }`、開終端機 keybind、`exec-once = foot`、動畫關閉）。install.sh 端到端跑通：裝 hyprland 0.55.4 + foot 1.27.0 + 80 依賴、stow 含 hyprland、chsh 換 zsh、印出 `Done`。

但 `Hyprland` 啟動反覆 `CBackend::create() failed!`。排查鏈很長、根因很有教材價值：

**根因：Wayland compositor 必須在真實圖形 VT（tty1）啟動，UTM 預設給的是序列 console。**

- UTM 的 ARM VM 預設用**序列 console（ttyAMA0）**當主互動介面。`getty@tty1`（圖形 VT 的登入）**預設 disabled/inactive**、只有 `serial-getty@ttyAMA0` 在跑。從第一個 archboot 畫面就是 `Login on pts/0`——整個安裝都在文字 console，沒碰過圖形 framebuffer。
- 在 SSH（`tty` = `/dev/pts/N`）或序列 console 跑 Hyprland，`libseat` 走 logind 開 seat 時，session 不在真實 VT 上、拿不到 DRM master → Aquamarine backend 建立失敗。loginctl 甚至會把 seat0 怪異地掛在某個 pts session 上、看似持有 card0 master，但 pts 不在 active VT、KMS 仍然失敗——這個假象很容易誤導。
- 判讀指令：`tty`（要 `/dev/tty1` 不是 pts/ttyAMA0）、`loginctl seat-status seat0`（active session 的 tty）、`cat /sys/class/tty/tty0/active`（實體 active VT）、`systemctl is-active getty@tty1`。

**修法（三件一起）：**

```bash
# 1. 開圖形 VT 的登入
sudo systemctl enable --now getty@tty1
# 2. tar 補 DRM/input 群組（也可靠 active VT 的 logind ACL，但補群組最穩）
sudo usermod -aG video,input tar     # 需重新登入生效
# 3. UTM 視窗切到「圖形顯示器」（非序列 console），在 tty1 用 tar 登入
```

另外 `~/.cache` 在最小安裝不存在，Hyprland crash handler 會 `failed to mkdir() crash report directory / No such file or directory`（次要、但會干擾判讀）——先 `mkdir -p ~/.cache`。

**成功確認**：tty1 登入後 `tty` = `/dev/tty1`、跑 `Hyprland` → 畫面進桌面、`exec-once = foot` 自動跳出終端機、2px 邊框（`border_size`）、青色軟體游標（`no_hardware_cursors` 生效）。log 關鍵行：

```text
[libseat] Backend 'seatd' failed ... skipping
[libseat] Seat opened with backend 'logind'
drm: card0 supports kms ... driver virtio_gpu
drm: Atomic supported, using atomic for modesetting
drm: Connector "Virtual-1" connected
```

**回寫教材的核心發現**：

1. **UTM 警告的黑畫面沒發生**。`virtio-gpu-gl` + OpenGL 加速 + `no_hardware_cursors = true`，Hyprland 在 Aquamarine 用 atomic modesetting render 正常。那行警告是 caveat、不是 blocker。
2. **seat 走 logind、不是 seatd**。logind 要真實 VT session——這是「為何不能從 SSH 跑桌面」的根因，要進 setup-order-guide / hyprland-vm-setup。
3. **UTM 序列 console vs 圖形顯示器**是 ARM VM 的隱形分岔。教材要明寫：裝完要 `enable getty@tty1` + 切 UTM 圖形顯示器，否則永遠在序列 console、跑不了桌面。
4. **`WLR_NO_HARDWARE_CURSORS` env → `cursor{}` 區塊**的 Aquamarine migration 確認：用 config 區塊設定有效。
5. virtio-gpu 的 `supportsAsyncCommit: false`、`supportsAddFb2Modifiers: false`——是限制但不擋 Hyprland。

### gotcha：SUPER = Cmd 被 macOS 攔截

UTM-on-Mac 上，Hyprland 的 `$mainMod = SUPER` 對應 Mac 的 Cmd 鍵，但 Cmd 組合鍵被 macOS 系統層攔截（Cmd+Q 退 app、Cmd+M 最小化、Cmd+Tab 切換），送不進 guest。所以 SUPER keybind 在 Mac host 上難以測試。

判讀：鍵盤輸入本身正常（tty1 登入、foot 內輸入都通），只有 Cmd 組合被攔。這不是 dotfiles bug——SUPER 在實體 Linux 機是正確慣例，Cmd 攔截純是 Mac host 限制。

對策：(1) 測 keybind 功能改用 `hyprctl dispatch ...` 從終端機觸發；(2) 退出 Hyprland 用 `hyprctl dispatch exit`（不靠 Cmd+M）；(3) 若要 keybind 可測，在 VM 上用 machine-specific override 把 `$mainMod` 改 ALT。回寫教材：hyprland-vm-setup 要標這個 Mac host 限制。

### 第二步：rice（waybar / wofi / mako / hyprlock）

_待填。_

### 待修的 shell 缺口（step 2 一起處理）

- `~/.zshenv` 無條件 `source ~/.cargo/env`（rust 沒裝）→ 每次開 zsh 噴錯。該加 `[[ -f ]]` 守衛。
- `~/.zshrc` `source $ZSH/oh-my-zsh.sh`（oh-my-zsh 沒裝）→ 噴錯、無主題無外掛。install.sh 沒裝 oh-my-zsh / powerlevel10k / 外掛（README Dependencies 列了但腳本沒實作）。

## 階段三：桌面環境（Hyprland + Rice）

_待填。_

## 階段四：同步與 Bootstrap script

_待填。_

## 回寫教材的實測發現

_待填。把實機跑出來、跟教材 `[待實測驗證]` 標記對得上的 gotcha 收斂在這裡，再回頭改對應教材檔案。_
