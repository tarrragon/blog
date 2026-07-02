---
title: "VM 實測流程記錄：從零建 Hyprland 桌面"
date: 2026-06-30
draft: true
description: "在 UTM VM 從零建 Linux + Hyprland 桌面的逐步實作流程、需要回查實際下了什麼指令 / 遇到什麼錯 / 怎麼排除時讀"
weight: 100
tags: ["dotfile", "hyprland", "vm", "utm", "handson", "record"]
---

這份是 dotfile 教材模組四到八的 VM hands-on 實測記錄。教材（`content/dotfile/`）負責概念與配置邏輯，這份記錄負責「實際在 VM 裡跑的時候發生了什麼」——下的指令、回饋的情況、除錯的過程、遇到的瓶頸。記錄是時間序的，按 [環境建置的操作順序](/linux/dotfile/00-dotfile-mindset/setup-order-guide/) 的階段分節，供之後教學回顧與回寫教材 `[待實測驗證]` 標記使用。

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

**gotcha（archboot 鏡像速度差異極大）**：archboot 有三個官方鏡像，預設的 `release.archboot.com`（美國麻州）在台灣下載極慢（~47 KB/s，458 MB 要 2+ 小時）。實測三個鏡像：

| 鏡像                   | 地區         | 從台灣的實測速度         |
| ---------------------- | ------------ | ------------------------ |
| `release.archboot.com` | 美國（麻州） | ~47 KB/s                 |
| `release.archboot.net` | 亞洲（印尼） | ~47 KB/s（跟美國差不多） |
| `release.archboot.eu`  | 歐洲（法國） | ~390 KB/s（快 8 倍）     |

從台灣下最快的是歐洲鏡像（`.eu`），亞洲鏡像（`.net`，印尼）反而沒比美國快。下載指令改用 `.eu`：

```bash
curl -L -O "https://release.archboot.eu/aarch64/latest/iso/archboot-2026.07.01-02.09-7.1.2-2-aarch64-ARCH-aarch64.iso"
```

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

**引擎選型（Virtualize，不是 Emulate——第二次重建踩過的坑）**：UTM 建立精靈第一頁的 Virtualize / Emulate 二選一，同架構（Apple Silicon 跑 ARM64 guest）一律選 **Virtualize**。兩條都是 QEMU，差在 CPU 執行方式：Virtualize 走 hvf 硬體虛擬化（CPU 直通、guest 的 `lscpu` Model name 顯示 `-`）；Emulate 走 TCG 純軟體模擬（Model name 顯示模擬的 Cortex-A72、BogoMIPS 125）。「要用 QEMU 引擎所以選 Emulate」是錯誤推理——Virtualize 也是 QEMU。代價實測：TCG 下 1321 步的 C++ 編譯一小時只跑 37%，網路型作業（裝套件）感覺不出差異、CPU 密集作業慢一個數量級才現形。Emulate 只在跨架構（如 ARM Mac 跑 x86_64 guest）才需要。判別現有 VM 跑哪種：`lscpu` 的 Model name（`-` = 直通、具體型號 = 模擬）比 `systemd-detect-virt` 可靠（hvf 下它也回 `qemu`）。

**顯示卡選型**：Display Output 需要是 `virtio-gpu-gl-pci (GPU Supported)`。Virtualize 精靈通常直接給對；Emulate 精靈預設是無加速的 `virtio-gpu-pci`、要手動改。清單裡的選項對照：

- `virtio-gpu-pci`——無 3D 加速、Hyprland 會 fallback 軟體渲染或起不來
- `virtio-gpu-gl-pci`（要選這個）——VirGL/Venus 3D 加速、Hyprland + Quickshell 需要
- `virtio-ramfb-gl`——也有加速但 ramfb 偏向開機早期 framebuffer
- `apple-gfx-pci`——Apple Virtualization 後端用的、走 QEMU 不適用

建完 VM 後在設定頁的 Display 區還有一個「啟用 OpenGL 硬體加速」checkbox，效果相同——勾了會自動切成 `virtio-gpu-gl-pci`。

**沿用既有磁碟重建 VM 殼**：Virtualize 精靈的「開機映像檔類型」選 **Import existing drive**（先切 radio 再瀏覽——radio 停在 ISO / 核心映像那格就瀏覽，qcow2 會被塞進 `-kernel` 參數、開機報 `could not load kernel '<路徑>.qcow2'`），選舊 VM bundle 裡的 `.qcow2`（右鍵 Show in Finder → 顯示套件內容 → `Data/`）。UTM 會複製一份進新 bundle，舊 VM 不受影響。磁碟內容（系統、config、build cache）全部原封沿用，開機後 DHCP 依 hostname 常拿到同一個 IP。

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

### 第三步：Caelestia + Quickshell 進階桌面 shell（執行中：階段 A go/no-go 已通過）

第二步用手動拼裝（waybar / wofi / mako / hyprlock）證明了各元件在 VM 上能獨立 render。第三步的目標是測試預組裝桌面 shell——用 Caelestia（基於 Quickshell 框架）取代手動拼裝的元件，驗證教材三篇（overview / installation / configuration）的準確性，並挖出 VM 環境特有的坑。

#### 核心風險：Qt6 QML 在 VirGL 上能不能跑

Step 2 證明 Hyprland 的 wlroots/Aquamarine 渲染在 virtio-gpu-gl-pci 上正常。Quickshell 是額外的 Qt6 QML 渲染層——它用 Qt 的 scene graph 畫 UI 元件，走的是另一條 OpenGL/Vulkan pipeline。這條 pipeline 跟 VirGL 的相容性未知，是 step 3 的 go/no-go gate：

- **能跑**：完整走 Caelestia 安裝 → 配置 → 客製化流程，驗證教材
- **不能跑**（QML crash / 全黑 / 嚴重破碎）：只能測安裝流程和 config 結構，視覺效果留實機。記錄失敗模式本身也有教材價值

判定方式：裝完 quickshell 後先跑一個最小 QML（`qs -c` 載入空 shell 或 quickshell-overview），看是否 render。不用等 Caelestia 全裝完才知道。

#### 實測執行記錄：階段 A（go/no-go gate）——通過

前置確認結果：磁碟 13 GB 可用（Qt6 全家桶足夠）、`quickshell` 在 Arch ARM `extra` repo 有 **0.3.0-2 穩定版**（可直接 pacman、不必先上 AUR）、VM **沒有** AUR helper（paru/yay 都缺，階段 B 要先補）。

go/no-go 測法：`sudo pacman -S quickshell`（拉進 qt6-declarative / qt6-wayland / qt6-svg），寫一個最小 QML（一個 `PanelWindow` + 純色矩形 + 文字），用 `qs -p <file>` 在活的 Hyprland instance 上載入：

```qml
import Quickshell
import QtQuick
ShellRoot {
    PanelWindow {
        anchors { top: true; left: true }
        implicitWidth: 460; implicitHeight: 180
        color: "transparent"
        Rectangle { anchors.fill: parent; color: "#89b4fa"; radius: 12
            /* ... 置中文字 ... */ }
    }
}
```

**結果：render 成功**（`shotA-quickshell-qml.png`）——藍色圓角面板 + 「Quickshell 0.3.0 QML render OK」文字正常畫出。**核心風險解除：Qt6 QML 的 scene graph 在 virtio-gpu-gl-pci 上能跑**，step 3 可以往完整 Caelestia 流程走，不必縮減成「只測安裝 + config 結構」。

兩個實測要點：

- **`qs` 的 process 名不是 `quickshell`**：`/usr/bin/qs` 是 `/usr/bin/quickshell` 的 symlink，用 `qs` 啟動時 process 的 comm 是 `qs`。`pgrep quickshell` 會找不到、誤判成 crash——要用 `pgrep -f "qs "` 或 `pgrep -x qs`。這是判讀 quickshell 是否活著的坑。
- **`PanelWindow` 從 `import Quickshell` 就有**：它實作在 `Quickshell/_Window` 內部模組、由主模組自動帶入，不必額外 `import Quickshell.Wayland`。
- **`qs -p file &` 在非互動 shell 會被殺**：背景 job 隨父 shell 結束被清掉。要讓它常駐得走 `hyprctl dispatch exec`（交給 compositor 托管），跟 step 2 拉 waybar/mako 同一招。

**gotcha（自己踩的、跟 stow + git 分支有關）**：這次 step 2 → step 3 中間，dotfiles 的 `main` 在 Mac 端被 force-push 重寫過，`themes/` package（`colors.conf`）當時還沒進 main。VM 端 `git reset --hard origin/main` 對齊 main 時，working tree 的 `dotfiles/themes/.config/hypr/colors.conf` 被刪掉——而 `~/.config/hypr/colors.conf` 是 stow 指過去的 symlink，target 一沒就變**懸空 symlink**。Hyprland 會監看 config 檔、偵測到變動自動 reload，於是跳出 config error 橫幅：`source= file ~/.config/hypr/colors.conf is inaccessible` + `$blue`/`$surface0` 未定義導致邊框色解析失敗。把 `themes/` merge 回來、target 檔恢復後 `hyprctl reload` 即清掉錯誤橫幅、邊框色（`col.active_border = ff89b4fa`）正常套用。教訓：**stow symlink 指向的是 git working tree 裡的檔案，切分支 / reset 會讓 symlink 懸空**——動到被 stow 管理的 package 時，要記得部署端的 symlink 跟 working tree 是綁在一起的。

#### 實測執行記錄：階段 B（Caelestia 完整安裝）——通過

透過 `paru` 從 AUR 編譯 `caelestia-shell`（2.1.0），227 步 C++ 編譯在 aarch64 VM 上完整跑完、產物正常安裝。**先前一次 build 停在 `[120/227]` 不是編譯失敗，是主機磁碟寫滿把 build 中途打斷**——清出空間後同一份 source 接著編就過。這修正了一個容易誤判的方向：build 卡住先查磁碟／資源，不是先懷疑 aarch64 相容性。

`caelestia shell -d` 啟動後 log 收在 `Configuration Loaded`，Material-3 風格的介面（左側直立 dock + 頂列 status bar）在 virtio-gpu 上完整 render（`shotB-caelestia-render.png`）。**階段 A 只證明 Quickshell 能畫一個測試面板，階段 B 證明整套 Caelestia shell 的實際 UI 都能繪製**——go/no-go 的風險到這裡才真正解除。

兩個非致命 warning，都是 VM 環境特性、不是 Caelestia 的 bug：

- **`pw.loop ... can't make support.system handle`（pipewire event loop 建立失敗）**：guest 沒跑 pipewire，Caelestia 的音訊 service 起不來。shell 照常 render，只是音量／音訊 widget 失效。實機或補上 pipewire 即無此問題。
- **`Could not register notification server at org.freedesktop.Notifications`**：step 2 留下的 mako 還在跑、先佔了 D-Bus 的通知服務名，Caelestia 自帶的通知 service 註冊不上。兩個通知 daemon 不能共存——要讓 Caelestia 接管通知，得先停掉 mako。

**啟動路徑實測（無人值守／遠端的真實障礙）**：重開機後要把 Hyprland 拉起來測，卡在兩件事。其一，`getty@tty1` 是 `enabled` 但開機後沒 active（logind 的 autovt 沒觸發），tty1 沒有登入提示。其二，UTM 顯示停在 serial console（`ttyAMA0`），它跟圖形 VT 是兩個獨立輸出，在 guest 內 `chvt` 只切圖形那側、serial console 不受影響。解法是 SSH 進去 `sudo systemctl start getty@tty1` 補出登入提示、`sudo chvt 1` 切到圖形 VT，再從 UTM 的 Display 輸出登入跑 `Hyprland`。**從 SSH 用 `sudo chvt` 與 `systemctl start getty@tty1` 遠端操控 VM 的 VT，比在 Mac + UTM 下跟 `Ctrl+Alt+Fn` 快捷鍵搏鬥穩定**——這是把桌面 session 從遠端拉起來的一條可靠路徑。

#### 實測執行記錄：階段 C 之一（通知服務接管）——通過

Caelestia 自帶通知 service，取代 step 2 rice 用的 mako。實測把 mako 停掉後，Caelestia 的 quickshell 行程自動接手通知，`notify-send` 的訊息由 Caelestia 的面板 render（`shotC-caelestia-notification.png`，右側 `1 notification` 面板顯示測試通知，CJK 標題正常）。

**通知 daemon 是獨佔 D-Bus 服務名的**——這是切換時最容易靜默失效的地方。`org.freedesktop.Notifications` 這個 bus name 同一時間只能有一個擁有者，mako 跟 Caelestia 誰先起誰佔著，後者搶不到。step 3 剛起 Caelestia shell 時 log 就有一行 warning：`Could not register notification server ... presumably because one is already registered`，但畫面上毫無異狀，Caelestia 的通知只是靜靜地不會出現。要讓 Caelestia 接管，得先 `pkill -x mako`；它 log 也說了「若現有 service 取消註冊會再試」，mako 一退出、Caelestia 隔幾秒就自動註冊上。

**驗證「通知到底被誰接管」的可靠手段**是查 D-Bus 服務名的擁有者、不是看畫面有沒有跳通知：

```bash
# 查 org.freedesktop.Notifications 現在被哪個連線擁有
owner=$(busctl --user call org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus GetNameOwner s org.freedesktop.Notifications | awk '{print $2}' | tr -d '"')
# 再把那個連線換算成 PID → 行程名
pid=$(busctl --user call org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus GetConnectionUnixProcessID s "$owner" | awk '{print $2}')
ps -o comm= -p "$pid"
```

停 mako 前擁有者是 mako 的連線、停掉後換成 `qs`（Caelestia 的 quickshell），就確認接管成功。畫面有沒有跳通知會受 idle／專注模式影響，D-Bus 擁有者才是 ground truth。

**附帶觀察（session lock——一段被更正兩次的判斷）**：shotC 畫面中央的 `Enter your password` 覆蓋層，初判為 caelestia 鎖屏；接著我一度「更正」成「不是鎖、是 session/dashboard drawer」，依據是無 lock 行程、`loginctl` 無 `LockedHint`、`caelestia` 無 lock 子指令。這個更正本身是錯的——後來讀 quickshell log、又意外實際觸發了鎖屏 client 死亡事故，才確認初判才對：它是走 Wayland `ext-session-lock` 協議的真鎖屏。完整機制、兩次誤判的根因、以及鎖屏 client 死亡的復原流程，見下方階段 C-2。

#### 實測執行記錄：階段 C 之二（配色切換 + 鎖屏機制 + lock-died 事故）——通過，含兩次誤判更正

##### 配色切換（scheme）

caelestia 內建 15 套配色（onedark／nord／dracula／gruvbox／catppuccin… 加 `dynamic` 從桌布取色）乘上 dark／light，用 `caelestia scheme set -n gruvbox -m light` 切。切完 `caelestia scheme get` 回報已是 gruvbox light，但跑著的 shell UI 沒跟著變色。讀 quickshell log 找到根因：shell 的 `services/Colours.qml` 從 `~/.local/state/caelestia/scheme.json` 讀配色，而 shell 啟動當下這個檔還不存在（log：`Read of .../scheme.json failed: File does not exist`）——第一次 `scheme set` 才建出這個檔。所以行為是「開機讀不到配色檔 → 用 fallback 色；之後 CLI 改了狀態、跑著的 shell 這一輪沒重讀套用」。要讓配色確定生效，最穩的順序是先 `scheme set` 建好 state 檔、再（重）啟 shell 讓它開機就讀。（後續補確認：解鎖後趕在鎖屏重新觸發前搶到一張乾淨桌面截圖 `shotG-desktop-scheme-check.png`——整個 UI 確實換成 gruvbox light 的暖奶油色，bar／dock／foot 終端機底色全變淺、文字轉為 gruvbox 的橄欖／黃／紅，配色確定生效。所以「scheme set 後沒變色」的根因收斂成啟動時機問題：在 scheme.json 存在之前啟動的 shell 實例讀不到、也不會為一次 CLI 變更熱重繪；在 state 檔就緒後啟動的 shell 實例開機讀取就正確上色。進一步驗證（換 tokyonight dark，`shotH-tokyonight-dark-hot-reload.png`）發現這個開機就載入 scheme.json 的實例，對檔案有 file watcher，之後 `scheme set` 會**即時熱套用、不必重啟**——UI 一秒內就變色。所以精確結論是：熱重繪能不能生效，取決於 shell 啟動時 scheme.json 在不在。啟動時檔已存在 → watcher 建成 → 之後改配色即時生效；啟動時檔不存在（首次安裝、沒 set 過）→ 那個實例讀不到、watcher 沒建，得先 `scheme set` 建檔再重啟 shell 一次，之後同一實例才會熱套用。）

##### 鎖屏機制：一個判斷被更正兩次

shotC 那個帶 `Enter your password` 的覆蓋層，判讀走了三步：初判是 caelestia 鎖屏（idle 觸發）；一度「更正」成「不是鎖、是 drawer」；最後靠 log 加實際觸發定案——它是**真的 session lock**，走 Wayland `ext-session-lock` 協議、idle 觸發。第二步的更正錯了。

quickshell log 給了關鍵證據：`@modules/lock/center/ProfilePic.qml`（lock 模組）、三個 `idle_notify` 計時器 timeout `180000／300000／600000` ms（3／5／10 分鐘，`respects inhibitors: true`）。對照行為就是 3 分鐘 idle 鎖屏、10 分鐘 `dispatch dpms off` 關螢幕。

前一次為什麼會誤判成「不是鎖」，根因值得記，因為三個訊號都在騙人：

- **`loginctl` 無 `LockedHint`**：`ext-session-lock` 是 **Wayland 合成器層**的鎖，跟 **logind 的 session 鎖**是兩套獨立機制。查 `LockedHint` 查的是 logind 那套，對 Wayland 協議鎖天生查不到——是查錯層，不是沒鎖。
- **`pgrep` 找不到 lock 行程**：鎖屏由 quickshell **行程內**畫，沒有獨立的 lock 可執行檔可抓。
- **看起來時有時無**：不是鎖時有時無，是我剛好在 3 分鐘 idle 邊界附近截圖、加上截圖前的 IPC 活動偶爾把 idle resume 掉。

教訓：判斷 Wayland session 有沒有被鎖，看的是**合成器的 session-lock 狀態**（有鎖時 Hyprland 的特定行為、或直接看 lock client 在不在），不是 `loginctl LockedHint`，也不是畫面上有沒有密碼框——現代 shell 這兩個訊號都靠不住。用肉眼判 UI 狀態誤判了兩次，是讀 shell 自己的 log 才定案，呼應可除錯 bootstrap 的原則：找程式自己的 log，別盯著畫面猜。

##### lock-died 事故 + 復原（正是無人值守踩過的雷）

為了測配色，我 `caelestia shell -k` 殺掉 shell 重啟——當下 shell 正握著那個 idle 觸發的 session lock。持鎖 client 一死，Hyprland 跳出安全畫面：`Oopsie daisy, it looks like you locked your screen but the lockscreen app died`。這是 `ext-session-lock` 的**故意設計**：持鎖 client 崩潰時，合成器**保持鎖定**而不解鎖——否則「殺掉鎖屏程式就能解鎖」會變成繞過鎖的漏洞。這正是無人值守那晚撞到的畫面，根因就是「鎖屏 client 在持鎖狀態下死亡」。

復原流程（從另一個 tty 或 SSH 用 hyprctl 做，Hyprland 的 died screen 本身也把指令寫在畫面上）：

1. `hyprctl keyword misc:allow_session_lock_restore 1`——允許新的 lock client 接管這個孤兒鎖（預設不允許，同樣是安全設計）。
2. 起一個 lock client 接管：`hyprctl dispatch exec hyprlock`。caelestia 的鎖只在 idle 觸發、沒有「立刻鎖」的指令可以隨手叫出來接管，所以改用 step 2 已裝的 hyprlock（`shotF-hyprlock.png`：hyprlock 的鎖屏蓋上，died screen 模糊在後）。
3. 在鎖屏輸入密碼解鎖，回到桌面。

對無人值守的啟示：跑長任務的圖形 session 若會 idle 鎖屏，鎖屏 client（quickshell／hyprlock）一旦崩潰就會把整個 session 卡在 died screen，SSH 進去用 hyprctl 復原是唯一活路——這也是為什麼無人值守一定要留 SSH 這條帶外通道，不能只靠圖形 session 自救。更根本的做法是無人值守的 session 直接關掉 idle 鎖（改 `hypridle`／shell 的 idle config 或設 inhibitor），從源頭避免長任務跑到一半被鎖。

#### 實測執行記錄：階段 C 之三（動態桌布 + Material-You 動態取色）——通過

caelestia 的招牌功能是 `dynamic` 配色：不是套一組預設色，而是**從當前桌布圖片即時抽出一整組 Material-3 tonal palette**。實測這條在 virtio-gpu VM 上完整運作。

**先看抽色本身（dry-run，不改任何東西）**：`caelestia wallpaper -p <圖片>` 會印出「這張圖會生成的配色」JSON 但不套用。預設桌布抽出的是偏藍調的暗色（primary `b4c7ed`、tertiary `eaddff`、background `0c0e12`），mode 自動判成 dark。這個 dry-run 很適合先確認一張圖會抽出什麼色，再決定要不要換上去。

**換桌布 → 動態重抽 → UI 連動**：VM 上沒有現成的彩色桌布，用 Python PIL 生了一張暖色對角漸層（深橘紅 → 洋紅紫），`caelestia wallpaper -f <圖>` 設上去、`caelestia scheme set -n dynamic` 重抽。抽出的主色從藍調翻成暖調（primary `f9b6ac` 鮭魚粉、tertiary `ffe1ba` 暖奶油、background `130d0b` 暗棕），整個 shell UI——bar、dock、terminal 的文字與 prompt——即時換成暖色系（`shotI-dynamic-from-default-wp.png` 藍灰 vs `shotJ-dynamic-warm-wp.png` 暖粉橘）。同一個 dynamic 設定，換張桌布就換一整套 UI 配色，這是它跟固定配色（catppuccin/gruvbox 那種）的本質差別。

實測要點：

- **抽色跟著桌布走，不是隨機**：暖桌布抽暖色、藍桌布抽藍色，`wallpaper -p` 的 dry-run 數據跟實際套用後的 UI 顏色一致。
- **smart mode 自動判 dark/light**：`wallpaper -f` 預設會依桌布亮度自動選 dark 或 light 模式（`-N` / `--no-smart` 可關掉）。兩張測試桌布都自動判成 dark。
- **換桌布後要不要手動重抽**：這次是明確 `scheme set -n dynamic` 重抽的。`wallpaper -f` 的 smart mode 會調 dark/light，但要讓 dynamic 從新桌布重新抽整組色，走一次 `scheme set -n dynamic` 最保險。
- **熱套用**：dynamic 跟前面 tokyonight 一樣即時生效、不必重啟 shell（呼應階段 C-2 的「shell 啟動時 scheme 檔在不在」結論——這個 shell 實例啟動時檔已存在、watcher 有效）。

#### 實測執行記錄：階段 D（生態對照：caelestia vs 手動拼裝）——完成，已蒸餾成教學文章

因為 step 2 手動拼裝（waybar+wofi+mako+hyprlock）跟 step 3 caelestia 都在同一台 VM 上跑過，這階段不需要新的操作，是把兩者的實測數據拉出來對照。原始量測：

| 軸         | caelestia                                                        | 手動拼裝                                                                        |
| ---------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 安裝大小   | ~230 MB（quickshell 佔 213 MB）                                  | ~4.5 MB（waybar 3MB + KB 級其餘）                                               |
| 記憶體 RSS | `qs` 單行程 ~400 MB                                              | waybar ~53 MB（+ 小型通知/啟動器）                                              |
| config     | 集中一個 `shell.json`（~24 行）                                  | 散在 waybar/wofi/mako/hypr 多檔多格式                                           |
| 配色一致   | 原生 dynamic 一套 scheme 全套用                                  | GTK CSS 讀不到 Hyprland `$` 變數、step 2 得手抄 hex；要一致得外掛 matugen/pywal |
| 失敗半徑   | quickshell 崩 → bar+通知+鎖屏一起沒（+ 實測到的 lock-died 死局） | 各元件獨立、mako 崩 ≠ bar 倒                                                    |

關鍵洞察是配色一致性那軸：手動拼裝的痛點（step 2 的 waybar `style.css` 註解白紙黑字寫「GTK CSS 吃不到 Hyprland `$` 變數、色碼得手抄」）正是 matugen/pywal 這類 template 工具、或 caelestia 內建 dynamic 要解的問題——影片裡看到的 `matugen/templates/rofi-colors.rasi` 就是手動棧自己搭 templating pipeline 的樣子。

這階段的產出蒸餾成一篇證據化決策文章（模組六 rice 設計「整合式 Shell vs 手動拼裝：實測取捨」），含足跡數字、失敗半徑、配色一致性機制、選型判準表與 tripwire。record 這裡保留原始量測，文章做 WARP 決策論述。

#### 前置確認（VM 開機後先做）

1. **quickshell 可用性**：Arch ARM `extra` repo 已有 quickshell 0.3.0 穩定版（aarch64），先試 `sudo pacman -S quickshell`。教材寫「quickshell-git 是硬性需求、穩定版缺 API」——需驗證 0.3.0 穩定版是否已滿足 Caelestia 需求。若不夠再裝 AUR 的 `quickshell-git`
2. **AUR helper**：step 2 用 pacman 原生套件，Caelestia 的 shell 和 CLI 都在 AUR。確認 VM 有 `paru` 或 `yay`，沒有就先裝
3. **磁碟空間**：Caelestia 完整安裝拉的依賴多（Qt6 全家桶 + fish + material-symbols 字型 + 各種 lib）。`df -h /` 確認剩餘空間，20GB VM 裝完 step 2 約用 6-8GB，應該夠
4. **step 2 的手動拼裝備份**：Caelestia `install` 會覆寫 Hyprland config。先 `git stash` 或在 dotfiles 分支保留 step 2 成果，確保能回退

#### 執行計畫

**階段 A：Quickshell 能力驗證（go/no-go gate）**

```text
目標：確認 Qt6 QML 渲染在 VM 的 virtio-gpu 上可用
做法：
  1. sudo pacman -S quickshell（穩定版 0.3.0）
  2. 寫一個最小 QML 測試（純色矩形 + 文字）用 qs 載入
  3. 若 render 成功 → 進階段 B
  4. 若 crash / 黑屏 → 記錄錯誤訊息、嘗試環境變數調整
     （QT_QPA_PLATFORM=wayland、QT_QUICK_BACKEND=software 等）
  5. 軟體 fallback 也不行 → step 3 縮減為「安裝流程 + config 結構驗證」
回寫教材：caelestia-installation.md 的 VM 測試段需補 Qt6/QML 前提
```

**階段 B：Caelestia 安裝流程驗證**

```text
目標：端到端走一次 caelestia install，驗證教材安裝段
做法：
  1. 安裝 AUR helper（paru）
  2. paru -S caelestia-cli（會拉 caelestia-shell → quickshell-git）
     觀察：穩定版 quickshell 0.3.0 跟 AUR quickshell-git 會不會衝突
  3. caelestia install（完整 dotfiles 部署）
     記錄：manifest.toml 實際部署了哪些 component
     觀察：覆寫了哪些既有 config、有沒有備份機制
  4. 重啟 Hyprland，觀察 Caelestia shell 是否載入
  5. 截圖佐證各元件 render 狀態
驗證教材：
  - caelestia-installation.md 的安裝步驟是否逐步對得上
  - runtime 依賴表是否完整（教材漏 libqalculate、swappy）
  - 「quickshell-git 是硬性需求」的說法是否仍然成立
  - uwsm component 教材未提
```

**階段 C：配置與客製化驗證**

```text
目標：驗證 shell.json / token / hypr-user.lua 的配置流程
做法：
  1. 建 shell.json 覆寫幾個 section（bar persistent、clock format、notifs expiration）
  2. 觀察 auto-reload 是否生效（不重啟 Hyprland）
  3. 測 CLI 指令（caelestia wallpaper / scheme / screenshot）
  4. 測 hypr-user.lua 自訂 keybind 和 window rules
  5. 測動態取色（Material Design 3）——VM 可能降級但流程可驗
驗證教材：
  - caelestia-configuration.md 的 section 結構是否跟實際一致
  - token 系統的文件說法是否成立
  - 「修改後自動 reload」是否真的不需要重啟
```

**階段 D：Quickshell 生態對照（若時間充裕）**

```text
目標：測試獨立 Quickshell 模組，理解框架能力邊界
做法：
  1. quickshell-overview（Shanu-Kumawat）：裝上看工作區預覽是否在 VM 可用
  2. vast-shell 架構閱讀（不安裝）：對照 Caelestia 的設計選擇
     - Services 層模組化 vs Caelestia 的 component 結構
     - matugen 取色 vs Caelestia 內建 MD3 取色
回寫教材：
  - caelestia-overview.md 的框架比較表是否需要更新
  - 是否值得加一段「Quickshell 生態的其他 shell」
```

#### 預期回寫教材的方向

| 教材檔案                      | 預期驗證 / 補充                                                    |
| ----------------------------- | ------------------------------------------------------------------ |
| `caelestia-overview.md`       | 框架比較表更新、Quickshell 生態提及                                |
| `caelestia-installation.md`   | 依賴表補齊、quickshell 穩定版 vs git 版判斷更新、VM 前提補 Qt6/QML |
| `caelestia-configuration.md`  | manifest.toml 結構、uwsm component、auto-reload 實測結果           |
| `desktop-shell-components.md` | 手動拼裝 vs Caelestia 的切換路徑（step 2 → step 3 的銜接）         |
| `knowledge-cards/`            | 可能新建：quickshell（框架概念卡）                                 |

#### 著作權紀律

同 step 2：參考 repo（caelestia-dots/shell、caelestia-dots/caelestia、quickshell/quickshell、quickshell-overview、vast-shell）只用於理解架構與配置邏輯。config 自己寫、教材描述基於實測觀察、不複製原始碼或在教學中直接引用重現。Caelestia 的 shell.json 範例可引用（公開配置格式），但要標明來源。

#### 風險與回退

| 風險                                     | 機率 | 回退                                               |
| ---------------------------------------- | ---- | -------------------------------------------------- |
| Qt6 QML 在 VirGL 完全不能 render         | 中   | 縮減為安裝 + config 驗證，視覺留實機               |
| quickshell-git AUR build 在 ARM 失敗     | 低   | 先試穩定版 0.3.0、或手動 build                     |
| caelestia install 覆寫 config 後回不去   | 低   | step 2 成果已在 dotfiles 分支，git checkout 即回退 |
| VM 磁碟空間不足（Qt6 全家桶 + 依賴太多） | 低   | qcow2 擴容或清理不需要的套件快取（`pacman -Sc`）   |
| Caelestia 版本跟教材描述不一致           | 中   | 記錄差異、更新教材——差異本身就是 step 3 的價值     |

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

決定讓 VM 裡的 CC 在無人盯著時自己跑 step 2，目的是用 hands-on 完善教學內容（不是把桌面做完美）。為了讓 CC 能無人值守跑完並把成果送回來，準備了三件事，各對應一個會中斷無人值守執行的障礙——這組 pattern 已抽成教材 [讓機器跑無人值守的長任務](/linux/install/unattended-remote-work/)。

- **NOPASSWD sudo**：無人值守程序沒人打 sudo 密碼，跑到 `sudo` 會卡死。寫 `/etc/sudoers.d/20-nopasswd` 放免密碼。取捨：放棄一道安全防線換自動執行，只因這是用完即丟的測試 VM 才划算。
- **終端機多工器（zellij）**：直接在 SSH session 跑的任務隨斷線而死。放進 zellij、detach，任務在 VM 上續跑、關 SSH 不影響。
- **推送認證（gh auth login）**：成果留在 VM 看不到；使用者從 GitHub 看推上去的分支，所以要先設好 git push 認證，否則 commit 了也推不出去、隔天撲空。
- **宿主防睡**：VM 跑在 Mac 上，Mac 一睡 UTM 的 VM 就暫停、CC 跟著停。離開前 `caffeinate -i` 讓 Mac 不睡。
- **agent 權限放行**：CC 預設每個有風險動作會停下來問，無人值守時沒人答。用 `--dangerously-skip-permissions` 放行。跟 NOPASSWD 同類取捨，靠清楚的 brief 限定範圍（只動哪些目錄、分支上做、產出交 review）降低風險。

另外把任務拆成兩個 repo：dotfiles（建配置=做）+ blog（續寫 record + 蒸餾教學草稿=學），各在自己分支（vm-step2-rice / vm-step2-record），blog commit 用 `--no-verify`（VM 沒 Go、mdtools hook 跑不動）。著作權紀律寫進 brief：參考 repo 只能理解架構、不可複製 config 或在教學引用重現，產出必須原創。

### 參考來源

本次 VM 實測全程使用的外部參考 repo，用於理解架構與配置邏輯，不複製 config 或在教學中直接引用重現：

| Repo                                                                                      | 用途                                                                     |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| [caelestia-dots/shell](https://github.com/caelestia-dots/shell)                           | Caelestia 的 Quickshell UI 元件原始碼，理解 shell 架構與 QML 元件設計    |
| [caelestia-dots/caelestia](https://github.com/caelestia-dots/caelestia)                   | Caelestia 的 CLI 工具與 dotfiles 部署邏輯，理解安裝流程與配置結構        |
| [fish-shell/fish-shell](https://github.com/fish-shell/fish-shell)                         | Fish shell 原始碼，理解 shell 的自動補全與語法高亮實作（終端機模組參考） |
| [quickshell/quickshell](https://git.outfoxxed.me/quickshell/quickshell)                   | Quickshell 框架原始碼（Caelestia 的 UI 底層），理解 QML 元件模型與 IPC   |
| [Shanu-Kumawat/quickshell-overview](https://github.com/Shanu-Kumawat/quickshell-overview) | Quickshell 的社群概覽與範例，理解 Quickshell 的使用模式與元件組合方式    |
| [myamusashi/vast-shell](https://github.com/myamusashi/vast-shell)                         | 另一套 Quickshell 桌面 shell 實作，對照 Caelestia 的設計選擇             |

Step 2 rice 實測中未 clone 這些 repo——手動拼裝的 waybar / wofi / mako / hyprlock 不依賴 Caelestia。Step 3 嘗試 Caelestia 進階設定時會用到 Caelestia、Quickshell 與 vast-shell 相關的五個。

## 階段六：第二次復現——新宿主機 + 分層 bootstrap 驗證

換到另一台 Mac（第一台的 VM 留在原宿主機），從零重走一次「裝 UTM → archboot 裝 Arch ARM → clone dotfiles → install.sh」，目的是驗證整套 dotfiles 能不能在全新環境一鍵復現。第一輪（step 1-3）全程互動式操作，這輪改成 SSH 非互動驅動——同一份腳本換一種執行情境，坑就換一批浮出來。

### 重裝過程的坑（宿主機側）

- **archboot 鏡像速度**：`.eu`（法國）從台灣 ~390 KB/s、`.com`（美國）與 `.net`（印尼）都只有 ~47 KB/s，差 8 倍（已記在階段零）。
- **UTM Emulate 路徑的顯示卡要手動選**：建立精靈預設 `virtio-gpu-pci`（無 3D 加速），要改選 `virtio-gpu-gl-pci`（已更新階段零的顯示卡選型段）。
- **UTM 本體 crash**：pacman 大量捲動 console 輸出時 UTM segfault（`CocoaSpice Renderer Queue`、EXC_BAD_ACCESS）。避法：長輸出導檔（`> /tmp/x.log 2>&1`）讓 console 安靜、操作全走 SSH。
- **macOS 終端機 SSH 到 VM 回 `No route to host`**：終端機 app 缺「本機網路」（Local Network）隱私權限，跟網路無關——同一時刻別的 process ping/ssh 都通。系統設定開權限即解。

### Guest 側的坑

- **sshd config 手滑事故**：`sed 's/^#PasswordAuthentication;*/.../'` 把 `;*` 當 `.*`，行尾殘留 ` no` 產生 `PasswordAuthentication yes no`，sshd 拒起。`sshd -t` 一條指令印出壞行定案（line 58 extra arguments）。教訓：改 sshd_config 後先 `sshd -t` 再 restart。
- **getty@tty1 預設 disabled**：archboot 裝出來的系統圖形 VT 沒有登入提示（黑畫面），`systemctl is-enabled getty@tty1` 回 `disabled`。`enable` + `start` 治本。判讀順序是 chvt 前先查 getty 狀態——黑畫面表象有「沒 getty / 顯示輸出沒接 / compositor 掛」三種根因。

### 非互動 bootstrap 的三個 finding（互動式跑永遠不會遇到）

| #   | Finding                                                                             | 修法                                                                    |
| --- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| 1   | pacman 缺 `--noconfirm`，非 TTY 卡在 `[Y/n]` 直接 exit 1（apt 分支有 `-y`、不對稱） | 兩處 pacman 補旗標                                                      |
| 2   | stale db → 鏡像 404：Arch 鏡像不留舊版檔案，裝機隔天 db 就指向被輪替的檔名          | 裝前先 `pacman -Syu`（只 `-Sy` 會 partial upgrade）                     |
| 3   | `chsh` 非 TTY 要密碼、失敗會被 `set -e` 中斷整個腳本                                | 改 `\|\|` 記 log 不中斷；事後 `sudo chsh -s /usr/bin/zsh <user>` 免密碼 |

### install.sh 分層重構（討論後定案）

單一 install.sh 拆成三層 stage + 平台分歧層：

- `install.sh [base|terminal|desktop]`——入口 + 共通層（stow / OMZ+p10k / Claude Code，跨平台同一套邏輯）
- `install-arch.sh` / `install-macos.sh`——平台套件層，各自維護
- `packages/arch-{base,terminal,desktop}.txt`——分層清單

分歧判準三條：安裝手段跨平台一致→共通層；只是套件名/管理器不同→平台清單；概念只存在某平台→該平台的 desktop 層。細節與跨發行版差異（套件名、rolling vs stable、brew on Linux 的邊界）抽成教材 [平台與發行版差異的判讀地圖](/linux/install/platform-divergence-map/)。

### 復現結果

**通過**。全新最小 Arch + 三行手打前置（root 裝 sudo/git + NOPASSWD），`git clone` + `./scripts/install.sh` 一鍵跑完：216 套件、全部 stow 部署正確（含 `.config/hypr` 的 unfold 多 package 共用）、OMZ/p10k/plugins、Claude Code、zsh 預設 shell，console 登入打 `Hyprland` 桌面直接起來。附帶一個自我提醒：驗證 stow 時 `ls -la ~/.config/waybar/`（帶斜線）穿透目錄 symlink 列出普通檔案、差點誤判部署失敗——`ls -ld`（不帶斜線）+ `stow --simulate` 才是權威讀法，正是 folding 錯覺的再現。

### Caelestia 復現（AUR 鏈、含 hvf 換裝後續編）

Hyprland 復現通過後接著把 step 3 的 Caelestia 在新 VM 重走一次。AUR 這條鏈比 pacman 套件多三種失敗型態，全部踩到並定案：

- **AUR helper 的 `-bin` 包版本半衰期**：paru-bin 的 aarch64 二進位對 `libalpm.so.15` 連結、`-Syu` 後系統已是 `.so.16`、載入直接斷。改用從原始碼 makepkg 的 yay（Go、編譯快、對系統當下 libalpm 編）免疫這類 skew。
- **ALARM 的 python sysconfig 烤入 distcc 路徑**：`python-materialyoucolor`（caelestia-cli 依賴）編 C++ extension 時叫 `/usr/lib/distcc/bin/g++`（不存在）——`/etc/makepkg.conf` 的 `!distcc` 管不到它，因為路徑烤在 ALARM 官方 python 套件的 sysconfig 裡（`python -c "import sysconfig; print(sysconfig.get_config_var('CXX'))"` 定案）。修法：`CXX=g++` 環境覆寫。同包還缺 aarch64 架構宣告、`--mflags "-A"` 繞過。
- **quickshell-git 是 PKGBUILD 層的硬依賴**：caelestia-shell 的 depends 指名 quickshell-git、會跟先裝的 repo 版 quickshell 0.3.0 衝突（`--noconfirm` 下 yay 不自動移除、要手動 `-R` 舊版再 `-U` 裝建好的包）。教材「穩定版是否已夠」的疑問定案：0.3.0 夠跑裸 QML、裝 caelestia-shell 必被 git 版取代。
- **caelestia-cli 對 shell 是 optdepends**：`yay -S caelestia-cli` 不會拉 shell、要各自明講（教材已修正）。

結果：caelestia-shell 2.1.0 在 virtio-gpu 完整 render（頂列 + Material-3 dock + foot 邊框），從 SSH 以 `hyprctl dispatch exec "caelestia shell -d"` 拉起。兩個 config 層 finding：

- **shell 啟動時會改寫 shell.json**：丟掉 schema 不認得的 key（`bar.clock.format` / `notifs.expiration` / `services.*` 在 2.1.0 都不存在）、只留有效子集。教材的 shell.json 範例 key 要對著實際版本驗。
- **runtime 寫入穿透 folded stow symlink 弄髒 repo**：`~/.config/caelestia` 是目錄層 symlink、shell 寫的 `monitors/` 直接落進 dotfiles repo（btop 的 `themes/` 同理）。修法：repo `.gitignore` 把「app 會自己寫的路徑」列入——自寫型 app 的 config 目錄跟 stow folding 共存時，這條是必要配套。

### Caelestia 配色三功能復現 + 假重啟事件

step 3 的配色切換 / 桌布 / 動態取色在新 VM 全部重現，包括「scheme 熱套用取決於啟動時 scheme.json 在不在」那條精確結論：第一個 shell 實例（啟動時無 scheme.json）對 `scheme set -n gruvbox -m light` 無反應、state 檔已寫入但 UI 不變；真重啟後 gruvbox light 完整上色；之後同一實例 `scheme set -n tokyonight -m dark` 秒切（同 pid 驗證）；暖色漸層桌布 + `dynamic` 抽色讓整套 UI 換成鮭魚粉暖色盤。

過程中踩到一個值得獨立記的**假重啟事件**：`caelestia shell -k` 靜默失敗（沒殺掉 shell、錯誤又被 `2>/dev/null` 吃掉），接著 `hyprctl dispatch exec` 起的新實例偵測到舊實例存在就自行退出——兩次「重啟」都沒發生，pid 從頭到尾是同一個。這造成兩次誤判（把 idle 鎖屏當成重啟後的行為、把 config watcher 的改寫當成重啟後的載入），直到 `ps -o pid,lstart` 比對 process 起始時間才拆穿。教訓進 skill：**驗證重啟看 pid + start time，不是看指令沒報錯**；殺 caelestia shell 的可靠做法是 `pkill -x qs`。

假重啟拆穿後反而分離出一個乾淨的發現：**config 熱重載與 scheme 熱套用是兩個獨立的 watcher**——shell.json 的 file watcher 永遠有效（跑著的實例吃到 git pull 進來的 `general.idle.timeouts`、驗證接受後重排序列化回檔案），scheme.json 的 watcher 只在啟動時檔案存在才建。

**Idle 鎖屏 2 小時設定進 repo**：前一天在舊 VM 把鎖定延長到 2 小時的改動是機器本機改的、沒回寫 dotfiles，新 VM 復現不出來——dotfile 漂移的教科書案例。已把 `general.idle.timeouts: [{timeout: 7200, idleAction: "lock"}]` 寫進 repo 的 shell.json（key 名從安裝的 `caelestia-config.qmltypes` schema 讀出、由 shell 改寫行為驗證接受）。

### VT 的三層判讀（kmscon 事件）

新 VM 開機後 UTM 圖形視窗顯示的 login 是 `pts/0`（`tty` 指令定案）——archboot 預設用 **kmscon**（userspace console、直接畫在 DRM 上、login 跑在 pts）取代 VT getty，這也回頭修正了稍早「getty@tty1 被 disabled」的理解：不是漏開、是被 kmscon 取代。kmscon 持有 DRM master、跟 compositor 衝突，`chvt` 也救不了（它不是 VT）。換手：`sudo systemctl disable --now kmsconvt@tty1` + `sudo systemctl start getty@tty1`，畫面變真 tty1 login（`tty` 回 `/dev/tty1`）後 Hyprland 正常啟動。判讀鏈已進 linux-install-debug skill v1.7.0。

### GUI 三類工具安裝驗證（檔案管理 / 瀏覽器 / 串流）

desktop 層的 GUI backlog 這輪放開三類：檔案管理器、瀏覽器、音樂串流。前兩類走 repo 直裝順利，第三類（Spotify）踩出這輪最有教學價值的兩層平台差異。

**Thunar 檔案管理**：`thunar + gvfs + tumbler + thunar-volman + thunar-archive-plugin + file-roller` 全在 ALARM repo。視窗驗證用 `hyprctl clients` 讀 compositor 的視窗表（`class: thunar` 出現即定案）、不靠肉眼。

**音訊棧缺件 finding**：裝串流前檢查發現 **pipewire 在、wireplumber 不在**——pipewire 被依賴鏈拉進來、但 session manager 是獨立套件不會自動跟進。這個組合的症狀是「daemon 在跑、`wpctl status` 的 Sinks 段是空的、應用無聲且不報錯」。補 `wireplumber + pipewire-pulse + pipewire-alsa` 後 UTM 模擬的 Intel HDA 立即出現為 `Built-in Audio Analog Stereo` sink。「有沒有在播」的權威判讀也在同一個地方：`wpctl status` 的 Streams 段有該應用的 stream 且 `[active]`。先用 python 生一段 440Hz 純音 `pw-play` 打通管線、把「音訊路徑」跟「網頁播放」拆成兩個獨立驗證點。

**瀏覽器**：firefox 152 + chromium 149 都有 ALARM aarch64 官方建置、pacman 直裝。YouTube 串流播放成功（Firefox stream 掛上 sink）——確立「無 DRM 串流」這條基線後，Spotify 的失敗就能歸因到 DRM 層。

**Spotify 的兩層平台牆**：

1. **官方 client 不存在**：repo 的 `spotify-launcher` 是去 Spotify 官方 apt repo 抓 deb 的下載器，實跑直接拿到精確錯誤：`There are no packages for your cpu's architecture (cpu="aarch64", supported=["amd64", "i386"])`——存在性層差異的一手案例（工具本身有 aarch64 建置、它要抓的東西沒有）。
2. **Web Player 需要 Widevine DRM**：Google 不對 Linux aarch64 發行 CDM，唯一來源是 [Asahi Linux 的 widevine-installer](https://github.com/AsahiLinux/widevine-installer)（從 ChromeOS recovery 鏡像抽 arm64 CDM、fixup 二進位格式）。腳本預設 Fedora 路徑，Arch 要覆寫 `LIBDIR=/usr/lib CHROME_WIDEVINE_BASE=/usr/lib/chromium`；本 VM kernel page size 4096、CDM 直接相容不需弱化記憶體權限。

**Widevine 的兩段式啟動坑**：裝完 CDM 後第一個 chromium 實例播不了——log（`--enable-logging=stderr --v=1`）顯示第一次啟動只做「發現預裝 component → 寫 hint 檔」，CDM 要**下一次啟動**才以 `Registering hinted Widevine` 真正註冊可用。「裝完 Widevine 要重啟瀏覽器」的機制層原因就是這個 hint 檔時序。CDM 有沒有真的載入的權威判讀：`grep widevinecdm /proc/<pid>/maps`（dlopen 過就有映射）。最終定案三權威齊備：CDM 映射確認 + Chromium stream 雙聲道 `[active]` + Spotify 實際出聲。

安裝結果已回寫 dotfiles `packages/arch-desktop.txt`（音訊三件套、thunar 六件套、雙瀏覽器從 backlog 轉正）；Widevine 屬系統路徑手動步驟、不進 stow、在 packages 檔以註解記程序。

### Caelestia 沒進 autostart（UTM 當機重啟才暴露）

UTM 當機重啟、重新登入 Hyprland 後 Caelestia 沒起來——`grep exec-once hyprland.conf` 定案：autostart 只有 foot / waybar / mako，**shell 從頭到尾沒進過 `exec-once`**，之前每次都是 SSH 手動 `hyprctl dispatch exec` 拉起、又因為沒重開機所以一直活著。「裝了 ≠ 會自動啟動」在 Hyprland 的具體形態就是 `exec-once` 是唯一 autostart 機制。修法連帶處理互斥：Caelestia 自帶 bar / 通知，waybar / mako 跟它搶（通知 D-Bus name 單一擁有者），已改 dotfiles 讓 `caelestia shell -d` 進 `exec-once`、waybar / mako 註解降為 fallback；VM 重開機實測 shell 自動起來、閉環。同輪也把教材 `caelestia-installation.md` 一段虛構的「Lua 格式」`exec-once` 範例（`hl.config({...})`——Hyprland config 是自己的 conf 格式、不是 Lua）修正為實測語法。

**shell.json 序列化順序遷就**：VM 端 `git pull` 被 shell.json 的 dirty 擋住——shell 每次啟動會驗證後重寫 config、key 順序用它自己的序列化（`idleAction` 在 `timeout` 前）。這檔案是被追蹤的 config、不能走 monitors/ 那種 gitignore 路線，治本是把 repo 檔案的 key 順序改成跟 shell 輸出一致、讓改寫變 no-op。

### VLC 影片播放：拆包兩層 + 首跑同意對話框

VLC 的驗證把「裝了本體不等於裝了功能」踩得更完整：`vlc` 開得起來、UI 正常，播 H.264 直接 `Codec 'h264' is not supported`——Arch 把解碼器拆到 `vlc-plugin-ffmpeg`。補上後又暴露第二層：解碼器先嘗試硬體加速（VDPAU/VAAPI），virtio-gpu 沒有視訊解碼能力、`failed to create video output` 閃一次錯誤對話框後回退軟體解碼穩定播放（log 尾端 late-frame 從 136ms 收斂到 19ms 是啟動追幀）。測試素材用 ffmpeg `testsrc2` + 440Hz sine 本機生成、驗證鏈同前（`hyprctl clients` + `wpctl status` stream `[active]`）。

首跑的「Privacy and Network Access Policy」對話框（明示同意 metadata 網路抓取——封面 / 曲名等於把播放內容暴露給第三方服務）值得教學收錄：決策記在 `~/.config/vlc/vlcrc` 的 `qt-privacy-ask` / `metadata-network-access`、但 VLC 退出時整檔重寫 vlcrc、不適合進 stow。整輪 GUI 發現（拆包 / 首跑對話框 / 播放驗證鏈 / 硬體解碼回退）已抽成教學新篇 [gui-apps-install-verify](/linux/install/gui-apps-install-verify/)。

## 回寫教材的實測發現

把實機跑出來、跟教材 `[待實測驗證]` 標記對得上、或值得抽成獨立教學的 gotcha 收斂在這裡。

### 第一步已轉成教材的

- **bootstrap 要交付完整環境**（install.sh 沒裝 `.zshrc` 引用的 oh-my-zsh/p10k/plugins，README 列了沒實作 → shell 壞）→ 寫進 [bootstrap-script-packages](/linux/dotfile/08-sync-bootstrap/bootstrap-script-packages/) 的「交付完整可用的環境」原則。
- **兩個 SSH 終端機坑**（macOS 送非法 LC_CTYPE → locale fallback；Ghostty 的 xterm-ghostty terminfo 新機沒有 → ZLE 重繪亂碼）→ 寫進 [ssh-keyless-bootstrap](/linux/install/ssh-keyless-bootstrap/) 的「連入後的兩個終端機坑」。
- **無人值守長任務的三障礙**（NOPASSWD / 多工器 / 推送認證 + 權限放行取捨）→ 抽成 [unattended-remote-work](/linux/install/unattended-remote-work/) 獨立篇。

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
