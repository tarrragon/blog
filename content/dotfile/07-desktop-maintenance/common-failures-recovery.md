---
title: "常見故障場景與恢復操作"
date: 2026-06-30
description: "Hyprland 黑屏、waybar 消失、畫面凍結、記憶體爆掉或 config 寫錯導致進不了桌面時，按症狀查恢復操作"
weight: 2
tags: ["dotfile", "linux", "hyprland", "troubleshooting"]
---

這篇按故障場景組織，每個場景列出症狀、原因、恢復步驟和預防措施。出問題時按症狀找到對應場景，照步驟操作。

## 場景一：Hyprland compositor crash

**症狀**：所有視窗同時消失，螢幕變黑或回到 TTY 登入畫面。滑鼠鍵盤有反應（可以切 TTY），但沒有桌面。

**原因**：Compositor process 遇到 fatal error 被 kernel 終止。常見觸發條件包括 plugin 相容性問題、特定 Wayland 協議操作觸發的 bug、GPU driver 回傳異常狀態。

**恢復步驟**：

注意：以下步驟中 `killall Hyprland` 或重啟 Hyprland 會終止所有由 compositor 管理的視窗，未存檔的工作會遺失。如果可能，先透過 TTY 或 SSH 嘗試存檔（如 `kill -USR1 <pid>` 對支援的應用程式觸發存檔）。

1. `Ctrl+Alt+F2` 切到 TTY2
2. 用你的帳號登入
3. 檢查 Hyprland 的最後錯誤訊息：

```bash
# 通用方式（不管 Hyprland 怎麼啟動都有效）
journalctl -b | grep -i hypr | tail -30

# 如果 Hyprland 是 systemd user unit，可以更精準地查：
journalctl --user -u hyprland -n 50 --no-pager
```

4. 重新啟動 Hyprland：

```bash
Hyprland
```

5. 如果反覆 crash，檢查最近改過的 config：

```bash
cd ~/.config/hypr
git diff  # 如果 dotfile 有版控
```

**預防**：config 改動後用 `hyprctl reload` 測試，不要直接重啟。啟用 plugin 前確認版本跟 Hyprland 版本相容。

## 場景二：單一桌面工具掛了

**症狀**：狀態列（waybar）消失、啟動器（wofi/rofi）叫不出來、通知（mako/dunst）不跳了。桌面其他功能正常，視窗可以操作。

**原因**：這些工具各自是獨立的 process。掛了只影響自己的功能，不影響 compositor 或其他工具。常見原因是 config 語法錯誤（改完 config 後觸發）、記憶體洩漏（長時間運作後）、或外部服務連線異常（如 waybar 的某個 module 連不到系統匯流排）。

**恢復步驟**：

判斷啟動方式：如果工具是在 Hyprland config 裡用 `exec-once`（Hyprland 的自動啟動指令，compositor 啟動時執行一次）啟動的，用 `killall` + 手動重啟；如果是 systemd user unit，用 `systemctl --user`。

`exec-once` 啟動方式（多數 Hyprland 安裝的預設做法）：

```bash
# waybar 掛了
killall waybar; waybar &

# wofi 掛了
killall wofi
# wofi 只在需要時啟動，不用常駐

# mako 掛了
killall mako; mako &
```

systemd user unit 啟動方式：

```bash
systemctl --user restart waybar
systemctl --user restart mako
```

**確認工具是否在跑**：

```bash
pgrep waybar  # 有輸出 = 在跑
pgrep mako    # 沒輸出 = 沒在跑
```

**預防**：改 config 後重啟對應的工具確認語法正確。Waybar 的 config 是 JSON 格式，語法錯誤會導致它無法啟動——改完後先用 `waybar` 前台跑一次看有沒有錯誤訊息。

## 場景三：GPU driver hang（畫面凍結）

**症狀**：桌面畫面完全凍結——滑鼠不動、鍵盤不回應、`Ctrl+Alt+F2` 切 TTY 也沒反應或延遲很久才回應。但如果從另一台機器 SSH 進來，系統是活的，process 都在跑。

**原因**：GPU driver 進入異常狀態。NVIDIA 閉源驅動在 Linux 上的穩定性不如 AMD 開源驅動（amdgpu），特別是在 Wayland 環境下。常見觸發條件包括 suspend/resume 之後 GPU 沒正確恢復、某些 OpenGL/Vulkan 操作觸發 driver bug、顯示輸出切換（接上或拔掉外接螢幕）。

**恢復步驟**：

方法 A — 如果 TTY 能切過去：

```bash
# 切到 TTY2
Ctrl+Alt+F2

# 殺掉 Hyprland（它會帶走所有視窗）
killall Hyprland

# 重新啟動
Hyprland
```

方法 B — 如果 TTY 也凍結、但 SSH 能連：

```bash
# 從另一台機器 SSH 進來（需事先知道 IP，見下方預防段）
ssh user@machine-ip

# 殺掉 compositor
killall Hyprland

# 如果需要 reset GPU（NVIDIA，且 driver 仍回應）
# 前提：所有使用 GPU 的 process 已停止（compositor 已 kill）
sudo nvidia-smi --gpu-reset

# 切回機器前面重啟 Hyprland
```

方法 C — 如果完全無回應：

按住電源鍵強制關機。這是最後手段。Linux 的 ext4/btrfs 檔案系統有 journal 保護，強制關機通常不會損壞**檔案系統結構**。但 journal 保護的是 metadata 一致性，正在寫入的使用者資料（未存檔的文件、正在下載的檔案）仍然可能遺失或損壞。重開機後正常登入 TTY、啟動 Hyprland 即可。如果開機過程有異常，用 `journalctl -b -1 -p err` 查看上次開機的錯誤訊息，確認是否有檔案系統修復紀錄。

**預防**：

- NVIDIA 用戶：關注 driver 版本的 release notes，已知有 Wayland 問題的版本避開
- 配置 suspend 後的 GPU 恢復：在 Hyprland config 或 systemd sleep hook 裡加入 GPU reset 操作
- 事先記錄機器的 IP 位址（`ip addr show`）或設定固定 hostname（如 mDNS 的 `machine.local`），桌面凍結時才有辦法從另一台機器 SSH 進來
- 考慮開啟 SSH server，出問題時可以遠端救援。開啟後應配置 key-based authentication 並停用密碼登入（`PasswordAuthentication no`），避免在網路上暴露密碼登入通道：

```bash
sudo systemctl enable sshd
sudo systemctl start sshd

# 安全配置：停用密碼登入（確保已設好 SSH key 再改）
# 編輯 /etc/ssh/sshd_config，設定 PasswordAuthentication no
# 然後 sudo systemctl restart sshd
```

## 場景四：記憶體耗盡（OOM）

**症狀**：系統變得極慢，操作有明顯延遲（幾秒到幾十秒）。隨後可能某些 process 突然被殺掉——瀏覽器分頁消失、IDE 視窗關閉，嚴重時 Hyprland 本身被 OOM Killer 終止導致桌面消失。

**原因**：實體記憶體和 swap 都用完了。常見觸發者是瀏覽器（Chrome/Firefox 的分頁越開越多）、IDE（大型專案的 language server）、Docker container、或應用程式的記憶體洩漏。

**恢復步驟**：

如果還能操作：

```bash
# 找出誰在吃記憶體
top -o %MEM
# 或用 htop/btop 的互動介面

# 殺掉佔最多記憶體的 process
kill <PID>
```

如果桌面已經被殺、在 TTY 裡：

```bash
# 看 OOM Killer 殺了誰
journalctl -b | grep -i "out of memory"
journalctl -b | grep -i "oom"

# 清理完後重啟桌面
Hyprland
```

**預防**：

設定 swap（即使 RAM 夠大，swap 提供 OOM 前的緩衝時間讓你有機會手動清理 process）。RAM 16GB 以上的機器，2-4GB swap 作緩衝通常足夠：

```bash
# 查看是否有 swap
swapon --show

# 如果沒有，建立一個 4GB 的 swap file（ext4 檔案系統）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久生效：加入 /etc/fstab
echo '/swapfile none swap defaults 0 0' | sudo tee -a /etc/fstab
```

Btrfs 檔案系統不支援 `fallocate` 建立 swap file。Btrfs 用戶需改用 `btrfs filesystem mkswapfile` 或建立專屬的 swap subvolume，具體做法參考 Arch Wiki 的 Btrfs swap 段落。

啟用 systemd-oomd（比 kernel OOM Killer 更早介入、更可控）。systemd-oomd 在 cgroup 的記憶體壓力達到閾值時就開始清理，預設配置對多數桌面場景足夠。進階調整可透過 `/etc/systemd/oomd.conf` 設定：

```bash
sudo systemctl enable systemd-oomd
sudo systemctl start systemd-oomd
```

## 場景五：Config 寫錯導致 Hyprland 啟動失敗

**症狀**：從 display manager（圖形登入畫面，如 SDDM、GDM）登入後立刻黑屏又回到登入畫面，或直接回到 TTY。如果從 TTY 手動執行 `Hyprland`，看到錯誤訊息後立即退出。

**原因**：Hyprland config 有語法錯誤或引用了不存在的資源。常見錯誤包括 `source` 指定的檔案不存在、keybind 語法寫錯、monitor 設定格式錯誤。

**恢復步驟**：

1. 切到 TTY（`Ctrl+Alt+F2`）
2. 登入後直接跑 Hyprland 看錯誤訊息：

```bash
# 看 Hyprland 的啟動錯誤（也可用 journalctl -b | grep -i hypr）
Hyprland
# Hyprland 如果因 config 錯誤無法啟動，會直接印出錯誤訊息後退出
```

3. 根據錯誤訊息修改 config：

```bash
# Hyprland 的主 config
vim ~/.config/hypr/hyprland.conf

# 如果用了 source 拆分，錯誤訊息會指出是哪個檔案
vim ~/.config/hypr/keybinds.conf
```

4. 修完後重新啟動：

```bash
Hyprland
```

**常見 config 錯誤**：

`source` 路徑錯誤——檔案不存在或路徑拼錯：

```bash
# 確認 source 指定的檔案都存在
grep "^source" ~/.config/hypr/hyprland.conf
# 逐一檢查每個路徑
```

Monitor 設定錯誤——指定了不存在的螢幕名稱：

```bash
# 查看系統實際的螢幕名稱
# 在能進桌面時記下來，或用 wlr-randr
wlr-randr
```

Keybind 語法錯誤——dispatcher 名稱拼錯或參數格式不對。Hyprland 的 keybind 格式是 `bind = MOD, key, dispatcher, params`，少一個欄位或 dispatcher 拼錯就會報錯。

**預防**：config 改動時用 `hyprctl reload` 即時測試，不要改完 config 就直接重啟 Hyprland。如果 dotfile 用 Git 管理，改壞了可以 `git checkout` 回退。

## 場景六：Suspend/resume 後桌面異常

**症狀**：筆電蓋上或手動 suspend 後喚醒，出現以下任一情況——螢幕黑屏但系統有反應（鍵盤背光亮）、解析度跑掉、多螢幕配置丟失（所有視窗擠到一個螢幕）、compositor 直接 crash 回到 TTY。

**原因**：GPU driver 在 suspend/resume 過程中需要保存和恢復 GPU 狀態。NVIDIA 閉源驅動在 Wayland 上的 suspend/resume 支援不如 AMD 開源驅動穩定，特別是多螢幕配置和高刷新率模式下容易出問題。

**恢復步驟**：

如果螢幕黑屏但系統有反應：

```bash
# 切到 TTY
Ctrl+Alt+F2

# 檢查 Hyprland 是否還在跑
pgrep Hyprland

# 如果在跑但沒畫面，kill 再重啟
killall Hyprland
Hyprland
```

如果解析度或螢幕配置跑掉：

```bash
# 在 Hyprland 內重新套用 monitor 設定
hyprctl reload
```

如果 compositor 已經 crash：按場景一的步驟從 TTY 重啟。

**預防**：

- NVIDIA 用戶：在 `/etc/modprobe.d/nvidia.conf` 啟用 preserve video memory allocations：

```bash
# /etc/modprobe.d/nvidia.conf
options nvidia NVreg_PreserveVideoMemoryAllocations=1
```

同時啟用 NVIDIA 的 suspend/resume systemd service：

```bash
sudo systemctl enable nvidia-suspend
sudo systemctl enable nvidia-resume
sudo systemctl enable nvidia-hibernate
```

- AMD 用戶：amdgpu driver 的 suspend/resume 通常開箱即用，遇到問題先更新 kernel（`pacman -Syu linux`）。
