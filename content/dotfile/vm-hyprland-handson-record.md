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

第一步證明 Hyprland 在 virtio-gpu 上能 render 後，第二步把桌面 shell 拼上去：狀態列、啟動器、通知、鎖屏。做法是照 dotfile 慣例每個元件一個 stow package，配色統一 Catppuccin Mocha，字型對齊「VM 實際裝進來的字族」。產出五個 package：`waybar/` `wofi/` `mako/` `hyprlock/`，外加一個不屬於任何單一工具的 `themes/`（集中配色 `colors.conf`）。

#### 配色與字型的兩個對齊點

配色選 Catppuccin Mocha（公開色票），集中寫進 `themes/.config/hypr/colors.conf` 當 Hyprland 系列的 SSoT。但有個範圍限制要先講清楚：**只有 Hyprland 自家的 `.conf`（`hyprland.conf` / `hyprlock.conf`）能 `source` 這些 `$` 變數**。Waybar 與 Wofi 用的是 GTK CSS、Mako 用的是自己的 ini，三者都引用不到 Hyprland 變數，色碼只能手抄同一組 hex。所以「一份配色檔餵所有工具」在純手寫配置下做不到，得靠 build script / 樣板工具（pywal、flavours）才能從單一來源生成各工具的配色——這次先手動對齊，把限制記下來。

字型踩到第一個實測坑。教材範例（`desktop-shell-components.md`、`color-system-theming.md`）裡 waybar / mako / hyprlock 的字型都寫 `JetBrainsMono Nerd Font`，但 VM 照 `packages-arch.txt` 裝的是 `ttf-meslo-nerd`，實際字族名是 **MesloLGS Nerd Font**：

```bash
fc-list | grep -i meslo | head -1
# MesloLGSNerdFont-Regular.ttf: "MesloLGS Nerd Font":style=Regular
```

字族名對不上的後果不是 fallback 成別的字，而是**狀態列 icon glyph 直接變豆腐方塊**——Nerd Font 的圖示字元落在私有區（PUA），只有那支字有；指定一個沒裝的字族，Pango 找不到 PUA glyph 就畫不出 icon。所以所有 rice config 的字型統一改成 `MesloLGS Nerd Font`（實裝字族）。**回寫教材**：範例字型要嘛改成 `ttf-meslo-nerd` 對應的 `MesloLGS Nerd Font`，要嘛在 `packages-arch.txt` 改裝 `ttf-jetbrains-mono-nerd`，兩邊得對齊，不能教材寫一套、套件清單裝另一套。

#### 部署坑：stow 的 tree folding / unfolding

新 package `stow` 下去時，`themes/` 這步噴出比預期多的動作：

```text
$ stow themes
UNLINK: .config/hypr
MKDIR:  .config/hypr
LINK:   .config/hypr/hyprland.conf => ../../dotfiles/hyprland/.config/hypr/hyprland.conf
LINK:   .config/hypr/colors.conf   => ../../dotfiles/themes/.config/hypr/colors.conf
```

原本 `~/.config/hypr` 是一條**整個目錄的 symlink**（第一步只有 `hyprland/` 這一個 package 提供 `.config/hypr/`，stow 把整個目錄折疊成單一 symlink → `dotfiles/hyprland/.config/hypr`，這叫 tree folding）。這也解釋了第一步一個觀察：`readlink ~/.config/hypr/hyprland.conf` 看起來「不是 symlink、是普通檔」——因為 symlink 在**目錄那一層**，檔案本身是順著目錄 symlink 走到 repo 裡的真實檔。

當 `themes/` 也要往 `.config/hypr/` 放東西時，stow 不能再讓整個目錄指向單一 package，於是 **unfold**：拆掉目錄 symlink、建一個真實的 `.config/hypr/` 目錄、再把每個檔案各自 symlink 回它所屬的 package。`hyprlock/`（提供 `.config/hypr/hyprlock.conf`）接著加進同一個目錄也是同樣機制。最後 `~/.config/hypr/` 是真目錄、底下三條 per-file symlink 各指各家：

```text
colors.conf   -> ../../dotfiles/themes/.config/hypr/colors.conf
hyprland.conf -> ../../dotfiles/hyprland/.config/hypr/hyprland.conf
hyprlock.conf -> ../../dotfiles/hyprlock/.config/hypr/hyprlock.conf
```

**回寫教材**：這是 stow folding/unfolding 的教科書案例，值得補進 `knowledge-cards/gnu-stow.md`——多個 package 共用同一個目標子目錄（這裡 `.config/hypr/`）時，stow 自動從「折疊的目錄 symlink」過渡到「真目錄 + 逐檔 symlink」。理解這個才看得懂為什麼有時 `~/.config/X` 是 symlink、有時是真目錄。

#### 測試方法：在活的 instance 上手動拉元件

測試走第一步建立的套路：先從 `$XDG_RUNTIME_DIR/hypr/` 找出**活的** instance signature（crash 留下的 stale socket 連不上），用該 sig 操作。改了 `hyprland.conf` 後 `hyprctl reload` 套用新設定，但**`reload` 不會重跑 `exec-once`**（那只在 compositor 啟動時跑一次）——所以 waybar / mako 要用 `hyprctl dispatch exec` 手動拉起來測：

```bash
export XDG_RUNTIME_DIR=/run/user/1000
export HYPRLAND_INSTANCE_SIGNATURE=<活的 sig>
hyprctl reload                                    # 套用 source/keybind/邊框色
hyprctl dispatch exec "waybar"                    # exec-once 的元件手動拉
hyprctl configerrors                              # 確認沒解析錯誤
```

截圖用 grim，但 grim 走 `WAYLAND_DISPLAY` 連 compositor，不是 `HYPRLAND_INSTANCE_SIGNATURE`。要從活 instance 的某個 client process 撈出它連的 socket：

```bash
cat /proc/$(pgrep -x waybar)/environ | tr '\0' '\n' | grep WAYLAND_DISPLAY
# WAYLAND_DISPLAY=wayland-1
WAYLAND_DISPLAY=wayland-1 grim ~/step2/shot.png
```

#### Waybar：VM 下的模組自動退化

Waybar 起來就正常 render（截圖 `shot1.png`）：左邊工作區 + 視窗標題、中間時鐘、右邊系統狀態，Catppuccin 配色與 MesloLGS icon 都對。值得記的是**同一份 config 在 VM 與實體機都能用、不必為 VM 改**——靠的是 Waybar 對缺硬體的模組自動隱藏：

```text
[warning] No batteries.
[info] Bar configured (width: 1280, height: 32) for output: Virtual-1
```

`battery` 模組在沒有電池硬體的 VM 直接消失、不報錯也不留空位；`pulseaudio` 在沒有 pipewire/音效裝置時顯示為空；`network` 顯示 VM 唯一的有線介面 `enp0s1`。所以 config 裡 wifi / disconnected / battery 等分支留著給實體機用、在 VM 無害。waybar 起來後 `hyprctl monitors` 的 `reserved: 0 32 0 0` 確認它在頂部保留了 32px。

另一行 log 值得知道但無須處理：`Unable to receive desktop appearance: GDBus.Error...ServiceUnknown`——這是 Waybar 想透過 portal 問系統的 light/dark 偏好，但 VM 沒跑 `xdg-desktop-portal`。無害，只影響自動深淺色切換（我們本來就寫死深色）。

#### Mako：通知的兩個缺口

Mako config 用 `makoctl reload` 驗證能 parse、`[urgency=critical]` criteria 區塊生效——送一則 critical 通知，截圖（`shot2.png`）看到**紅框**（`border-color=#f38ba8`）、圓角、右上錨點都對。但測試過程炸出兩個缺口：

**缺口一：mako 只負責「顯示」、不會自己造通知。** 要產生通知得靠 `libnotify` 的 `notify-send`，而最小安裝沒有它（`notify-send: command not found`）。沒有它連自測都做不到，更重要的是**應用程式也是透過 libnotify 發通知**，缺了等於整條通知鏈斷在源頭。臨時自測可改用 `gdbus` 直接打 `org.freedesktop.Notifications` 介面：

```bash
gdbus call --session --dest org.freedesktop.Notifications \
  --object-path /org/freedesktop/Notifications \
  --method org.freedesktop.Notifications.Notify \
  "test" 0 "" "標題" "內文" "[]" "{}" 5000
```

但正解是把 `libnotify` 加進 `packages-arch.txt`（已加）。

**缺口二：CJK 變豆腐。** critical 通知的中文內文在截圖裡是一排**豆腐方塊**（`shot2.png` 清楚可見）。根因同字型那段的延伸：MesloLGS Nerd Font 只含 Latin + icon glyph、**沒有 CJK**，而 VM 沒裝任何 CJK fallback 字型：

```bash
fc-match ":lang=zh-tw"
# AdwaitaMono-Regular.ttf  ← 不含中文，等於沒有可用的 zh-tw 字
```

任何中文（通知、視窗標題、應用程式名、本地化的鎖屏日期）都會變豆腐。修法是裝 `noto-fonts-cjk` 當 fallback：

```bash
sudo pacman -S --needed noto-fonts-cjk
fc-match ":lang=zh-tw"
# NotoSansCJK-Regular.ttc: "Noto Sans CJK KR"  ← fontconfig 現在有 CJK glyph 可 fallback
```

裝完 `fc-match` 已能解析到 Noto Sans CJK。但這裡踩到一個比「裝字型」更深的坑：**光裝字型不夠，已經在跑的 client 不會自動看到新字。** 裝完 `noto-fonts-cjk` 後 `makoctl reload` 再送中文通知，畫面**還是豆腐**（`shot8.png`，注意這張的邊框已是藍色、順帶確認了 normal urgency 的邊框色）。原因是 mako daemon 在啟動時就把 Pango/fontconfig 的 font map 快取住了，而 `makoctl reload` 只重讀 config 檔、**不會重建 font map**——mako 是在裝 CJK 字型之前啟動的，所以它手上那份字集根本沒有 Noto CJK。

修法是**重啟 daemon**（不是 reload）：

```bash
pkill mako && hyprctl dispatch exec mako
```

重啟後同一則中文通知正常顯示（`shot9.png`：「中文通知測試（重啟 mako 後）」標題與內文的中文都出來了，跟 Latin 的 `MesloLGS` 混排無縫）。這也解釋了為什麼在真實使用情境裡通常不會遇到——正常開機時 `exec-once = mako` 是在字型都裝好之後才啟動，daemon 一開始就看得到 CJK；只有「系統已在跑、中途才補裝字型」這種當下除錯的時序才會現形。**回寫教材要點**：裝 fallback 字型後，已在執行的 client（mako、waybar 等）要重啟才吃得到；`reload` 類指令通常只重讀設定、不重建字型快取。

一個次要觀察：`fc-match :lang=zh-tw` 回的是 Noto Sans CJK **KR**（韓文排序優先），靠 Han 統一多數字能正常顯示，但要精確拿到台灣字形變體得另設 fontconfig 語言優先序——這是後續可細修的點、不擋用。

`libnotify` 與 `noto-fonts-cjk` 都已補進 `packages-arch.txt`。

#### Wofi：啟動器一次到位

Wofi 是這次最順的元件。`hyprctl dispatch exec "wofi --show drun"` 叫起來（綁 `SUPER+D`），截圖（`shot3.png`）：藍框圓角的搜尋框、放大鏡 icon、drun 列出 `.desktop` 應用程式（ranger、zellij、foot、yazi 等），選中項是藍底反白字（`#entry:selected` 的 CSS 生效）。`mode=drun` 列的是 `.desktop` 應用程式；要 `run`（PATH 執行檔）或 `dmenu`（吃 stdin）模式時用 CLI 旗標臨時切，不寫死在 config。

#### Hyprlock：渲染完成、但測試方式有大坑

Hyprlock config 渲染結果確認（`shot4.png`）：`path = screenshot` 截當下畫面 + `blur_passes = 2` 模糊當背景、64px 時鐘、`cmd[update:60000] date` 產生的日期 label（`Wednesday, 01 July`，locale en_US 下是英文所以無豆腐）、藍框 pill 密碼框。VM 軟體渲染下 `blur_passes` 設 2 是兼顧霧化效果與效能的折衷。

但測試 hyprlock 踩到這趟最嚴重的坑，根因很有教材價值：

**`pkill hyprlock` 不是解鎖、而是讓 compositor 掉進鎖屏失效保護畫面。**

測完想解鎖（我沒有密碼），直覺 `pkill hyprlock`。process 是沒了，但畫面變成 Hyprland 的失效保護（`shot6.png`）：

```text
Oopsie daisy, it looks like you locked your screen but the lockscreen app died :(
If you want to unlock your screen, go into another tty ... and run:
  hyprctl --instance 0 'keyword misc:allow_session_lock_restore 1'
  hyprctl --instance 0 'dispatch exec hyprlock'
```

關鍵理解：Wayland 的 `ext-session-lock-v1` 協議下，鎖屏 client（hyprlock）一旦 lock，session 的「安全鎖定」狀態是由 **compositor** 持有的；**只有 lock client 通過認證後呼叫 `unlock_and_destroy` 才能解**。`pkill` 是直接砍掉 client、沒走解鎖流程，compositor 仍保持鎖定、只好顯示這個失效保護畫面。最容易誤判的是**兩層鎖是不同的東西**：

```bash
loginctl show-session ... -p LockedHint
# LockedHint=no          ← logind 那層說沒鎖
pgrep hyprlock
# (空)                    ← client 死了
# ……但 compositor 的 session-lock 還在，畫面進不去
```

`LockedHint=no`（logind 層）會讓人以為已解鎖，但 compositor 層的 `ext-session-lock` 還鎖著——這個假象很坑。

**正確的測試與恢復做法：**

- **別用砍 process 的方式測 hyprlock**。要結束鎖屏就走認證解鎖；自動化測試裡要嘛別碰 hyprlock、要嘛接受它會把畫面鎖住。
- 已經掉進失效保護時，照畫面指示：`hyprctl keyword misc:allow_session_lock_restore 1` 允許新的 hyprlock 接管既有鎖，再 `hyprctl dispatch exec hyprlock` 重新拉一個**乾淨的鎖屏 prompt**（`shot7.png`），使用者用密碼正常解鎖。
- **沒有使用者密碼就無法完整解鎖**——這是設計、不是 bug。所以在這台 VM 上，這個測試的代價是畫面留在鎖定狀態，得由知道密碼的人解。`waybar` / `mako` / `foot` 等 process 都還活著，解鎖後桌面照舊。

**回寫教材**：這是「在 VM / 自動化環境裡測鎖屏」的安全守則，值得獨立成卡或進 `color-system-theming.md` 的 hyprlock 段：鎖屏一旦啟動，唯一的正常出口是認證；測試前先想好怎麼回得來（知道密碼、或準備好走 restore 路徑），別用 `pkill` 當「關掉」。

#### 截圖剪貼簿的型別坑

順手測 `hyprland.conf` 綁的截圖 keybind `grim - | wl-copy`，發現複製進剪貼簿的型別不對：

```bash
grim - | wl-copy
wl-paste --list-types
# text/plain  text/plain;charset=utf-8 ...   ← 被當文字、不是圖
```

`wl-copy` 預設要靠 `xdg-utils`（`xdg-mime`）推斷 stdin 的型別，最小安裝沒裝它，於是把 PNG bytes 誤標成 `text/plain`——貼進影像應用程式就拿不到圖。修法是明確告知型別，不必為此多裝一個 `xdg-utils`：

```bash
grim - | wl-copy --type image/png
wl-paste --list-types
# image/png   ← 正確
```

keybind 已改成帶 `--type image/png`（全螢幕與 slurp 框選兩條都改）。

#### 第二步小結

`waybar` / `wofi` / `mako` / `hyprlock` 四個元件都在 VM 的 live instance 上實際 render 成功、各有截圖佐證。挖到的缺口集中在「最小安裝缺的相依」與「VM／自動化環境特有的測試陷阱」，不是配置本身寫錯：字族名要對齊實裝字型、CJK 與通知產生各缺一個套件、剪貼簿型別要明指、鎖屏不能用砍 process 測。這些都比「桌面好不好看」更該被學起來，收斂在下一節「回寫教材的實測發現」與 `~/step2/REPORT.md` 的待審清單。

### 待修的 shell 缺口（step 2 一起處理）

- `~/.zshenv` 無條件 `source ~/.cargo/env`（rust 沒裝）→ 每次開 zsh 噴錯。該加 `[[ -f ]]` 守衛。
- `~/.zshrc` `source $ZSH/oh-my-zsh.sh`（oh-my-zsh 沒裝）→ 噴錯、無主題無外掛。install.sh 沒裝 oh-my-zsh / powerlevel10k / 外掛（README Dependencies 列了但腳本沒實作）。

## 階段四：完整 dotfiles 安裝 + Claude Code（為 step 2 在 VM 內除錯）

把 dotfiles 補到真的能交付 `.zshrc` 期望的環境，目標是讓 VM 變成能直接跑 CC 除錯的開發環境。

**補完 install.sh 的缺口**（上面「待修的 shell 缺口」的解）：

- install.sh 加 `setup_zsh_framework()`：git clone oh-my-zsh + powerlevel10k + zsh-autosuggestions + zsh-syntax-highlighting 進 `~/.oh-my-zsh/custom`（pacman 裝不出 OMZ 的 custom theme/plugin 佈局，要 clone 對齊 `.zshrc` 的 plugin 機制）。
- `.zshenv` 守衛 `.cargo/env`。
- packages-arch.txt 加 21 個工具（pacman 原生，Brewfile 保持 macOS 專用）：gh（套件名 `github-cli`）、fzf、ripgrep、fd、bat、lazygit、git-delta、yazi、tig、ranger、nodejs/npm、autojump、ttf-meslo-nerd、broot/btop/zellij（stowed config 但 base 沒裝 binary）、ca-certificates、curl。
- Claude Code 用原生 installer（`curl -fsSL https://claude.ai/install.sh | bash`）裝進 `~/.local/bin`、免 sudo、自動更新。認證在有瀏覽器的 Mac 跑 `claude setup-token`，或在 VM 跑 `claude` 走 OAuth（URL 複製到 Mac 瀏覽器、code 貼回）。

**兩個 SSH 終端機坑（回寫教材重點，已寫進 ssh-keyless-bootstrap）**：裝了 p10k + plugins 後，從 Ghostty SSH 進 VM 打字變「一字母重複多次」的累加亂碼。陽春 shell 之前正常、是因為沒 unicode 撐得住壞掉的 locale/terminfo。

1. **locale**：macOS 終端機 SSH 送 `LC_CTYPE=UTF-8`（非合法 Linux locale 名）→ VM fallback 成 POSIX → zsh 行編輯器把輸入當單位元組、p10k unicode 重繪亂碼。`locale` 看到 `LANG` 空、`LC_CTYPE=POSIX` 即中。修法：強制 `LANG=LC_CTYPE=en_US.UTF-8`（已加進 dotfiles `.zshenv` 的 Linux 防護段）。
2. **terminfo**：Ghostty 送 `TERM=xterm-ghostty`，VM 的 terminfo 資料庫沒這條目 → 行編輯器「清行重繪」找不到控制序列、畫面畫壞。修法：`infocmp -x xterm-ghostty | ssh arch-vm 'tic -x -'` 把 terminfo 灌進 VM 的 `~/.terminfo`（保留完整功能），或退而求其次 `TERM=xterm-256color`。

排查教訓：兩個坑都在裝了 unicode 重的 shell 之後才浮現，先懷疑「終端機環境層（locale/terminfo）」而不是「剛裝的 shell 配置壞了」，能省很多時間。

**其他小坑**：

- chsh 在 zsh 已是預設 shell 時報 `Shell not changed`（no-op、無害）。
- CC installer 警告「`~/.local/bin` not in PATH」是它檢查當下 bash 的誤報；zsh 的 path.zsh 已含 `~/.local/bin`。
- 桌面 foot 被關掉後 `SUPER+Q`（= Cmd+Q）開不了新終端機（macOS 攔截）；從 host `hyprctl dispatch exec foot` 可補開，但要先從 `$XDG_RUNTIME_DIR/hypr/` 找出**活的** instance signature（crash 留下的 stale socket 連不上、`Hyprland` process 自己的 environ 也沒帶 signature）。

**結果**：VM 裝齊 zsh rice（oh-my-zsh + p10k + plugins）+ 工具鏈 + Claude Code 2.1.197，CC 認證成功、能對話。step 2 rice 可直接在 VM 內用 CC 除錯。

## 階段五：把 step 2 交給無人值守的 CC（環境準備）

決定讓 VM 裡的 CC 在無人盯著時自己跑 step 2，目的是用 hands-on 完善教學內容（不是把桌面做完美）。為了讓 CC 能無人值守跑完並把成果送回來，準備了三件事，各對應一個會中斷無人值守執行的障礙——這組 pattern 已抽成教材 [讓機器跑無人值守的長任務](/dotfile/linux-install/unattended-remote-work/)。

- **NOPASSWD sudo**：無人值守程序沒人打 sudo 密碼，跑到 `sudo` 會卡死。寫 `/etc/sudoers.d/20-nopasswd` 放免密碼。取捨：放棄一道安全防線換自動執行，只因這是用完即丟的測試 VM 才划算。
- **終端機多工器（zellij）**：直接在 SSH session 跑的任務隨斷線而死。放進 zellij、detach，任務在 VM 上續跑、關 SSH 不影響。
- **推送認證（gh auth login）**：成果留在 VM 看不到；使用者從 GitHub 看推上去的分支，所以要先設好 git push 認證，否則 commit 了也推不出去、隔天撲空。
- **宿主防睡**：VM 跑在 Mac 上，Mac 一睡 UTM 的 VM 就暫停、CC 跟著停。離開前 `caffeinate -i` 讓 Mac 不睡。
- **agent 權限放行**：CC 預設每個有風險動作會停下來問，無人值守時沒人答。用 `--dangerously-skip-permissions` 放行。跟 NOPASSWD 同類取捨，靠清楚的 brief 限定範圍（只動哪些目錄、分支上做、產出交 review）降低風險。

另外把任務拆成兩個 repo：dotfiles（建配置=做）+ blog（續寫 record + 蒸餾教學草稿=學），各在自己分支（vm-step2-rice / vm-step2-record），blog commit 用 `--no-verify`（VM 沒 Go、mdtools hook 跑不動）。著作權紀律寫進 brief：參考 repo 只能理解架構、不可複製 config 或在教學引用重現，產出必須原創。

## 回寫教材的實測發現

把實機跑出來、跟教材 `[待實測驗證]` 標記對得上、或值得抽成獨立教學的 gotcha 收斂在這裡。

### 第一步已轉成教材的

- **bootstrap 要交付完整環境**（install.sh 沒裝 `.zshrc` 引用的 oh-my-zsh/p10k/plugins，README 列了沒實作 → shell 壞）→ 寫進 [bootstrap-script-packages](/dotfile/08-sync-bootstrap/bootstrap-script-packages/) 的「交付完整可用的環境」原則。
- **兩個 SSH 終端機坑**（macOS 送非法 LC_CTYPE → locale fallback；Ghostty 的 xterm-ghostty terminfo 新機沒有 → ZLE 重繪亂碼）→ 寫進 [ssh-keyless-bootstrap](/dotfile/linux-install/ssh-keyless-bootstrap/) 的「連入後的兩個終端機坑」。
- **無人值守長任務的三障礙**（NOPASSWD / 多工器 / 推送認證 + 權限放行取捨）→ 抽成 [unattended-remote-work](/dotfile/linux-install/unattended-remote-work/) 獨立篇。

### 第二步 rice 的發現（已三輪審查、已回寫教材）

第二步 rice 的發現分兩類：**配置層**（教材範例與實裝環境對不上、該直接修教材）與 **環境／測試層**（最小安裝缺相依、VM/自動化特有陷阱、該補成卡或教材新段）。

| 發現                                 | 類別 | 回寫落點                                                                                      | 狀態     |
| ------------------------------------ | ---- | --------------------------------------------------------------------------------------------- | -------- |
| 字族名 MesloLGS ≠ 範例 JetBrainsMono | 配置 | `desktop-shell-components.md`、`color-system-theming.md`、`hyprland-installation.md` 全域對齊 | 已回寫   |
| CJK 無字 → 豆腐，需 noto-fonts-cjk   | 環境 | `desktop-shell-components.md` Mako 段後新增 CJK fallback 段                                   | 已回寫   |
| 字型可用集合在 process 啟動時決定    | 機制 | 新卡 `knowledge-cards/font-availability-at-startup.md`                                        | 已建卡   |
| mako 要 libnotify 才有通知可發       | 環境 | `desktop-shell-components.md` Mako 段新增 libnotify 說明                                      | 已回寫   |
| waybar 模組在 VM 自動退化            | 配置 | `desktop-shell-components.md` Waybar 段新增自動退化說明                                       | 已回寫   |
| stow tree folding/unfolding          | 機制 | `knowledge-cards/gnu-stow.md`                                                                 | backlog  |
| Hyprland 變數 source 範圍限制        | 配置 | `color-system-theming.md` 配色統一段                                                          | 已有覆蓋 |
| hyprlock pkill ≠ 解鎖、掉失效保護    | 機制 | 新卡 `knowledge-cards/session-lock.md` + `common-failures-recovery.md` 新場景                 | 已建卡   |
| grim 截圖需 wl-copy --type image/png | 環境 | `desktop-shell-components.md` 新增 Grim 截圖段                                                | 已回寫   |

另建 `knowledge-cards/fontconfig.md` 傘卡（font-availability 的上游概念）。階段零～二的 `[待驗證]` 標記（virtio-gpu 黑畫面、DHCP 帶進新系統、序列 console vs 圖形 VT）已在階段一、三第一步驗證並記錄。
