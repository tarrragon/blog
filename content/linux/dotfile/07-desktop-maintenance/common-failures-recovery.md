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

## 場景二點五：鎖屏卡死（hyprlock 異常結束）

**症狀**：鎖屏畫面消失但桌面沒回來，螢幕顯示 Hyprland 的失效保護訊息（「it looks like you locked your screen but the lockscreen app died」），或畫面全黑但系統有回應（SSH 能連、TTY 可能切得到也可能切不到）。

**原因**：鎖屏工具（Hyprlock、Swaylock）透過 Wayland 的 ext-session-lock 協議向 compositor 請求鎖定。鎖定狀態由 compositor 持有，唯一正常解鎖動作是鎖屏 client 通過認證後呼叫 unlock_and_destroy。如果鎖屏 client 在持鎖狀態下被殺（`pkill`、crash），compositor 沒收到認證信號，會維持鎖定並顯示失效保護畫面。這跟殺 waybar/mako 不同——那些是普通 process，殺了重啟就好；鎖屏 client 持有安全狀態，殺了反而卡住。

**恢復步驟**：

1. 嘗試切到另一個 TTY（`Ctrl+Alt+F2`）。注意：ext-session-lock 的安全語意允許 compositor 攔截 VT 切換快捷鍵，此時 TTY 切不過去，改用 SSH 從另一台機器連入
2. 允許新的鎖屏 client 接管既有的鎖：

```bash
hyprctl --instance 0 'keyword misc:allow_session_lock_restore 1'
```

3. 重新拉一個鎖屏 client：

```bash
hyprctl --instance 0 'dispatch exec hyprlock'
```

4. 回到鎖屏畫面，用密碼正常解鎖

**判讀**：`loginctl show-session <id> -p LockedHint` 可能顯示 `LockedHint=no`（logind 層認為沒鎖），但畫面仍進不去——因為擋住畫面的是 compositor 的 ext-session-lock，跟 logind 的提示是獨立的兩層。判斷畫面鎖定狀態看 compositor 層，不看 logind。

**預防**：測試鎖屏時備好恢復路徑（知道密碼、或預先開 SSH）。不要用殺 process 的方式結束鎖屏——要結束就走認證解鎖。自動化流程若會啟動鎖屏，把「需要人工解鎖」算進代價。鎖屏安全模型的完整說明見 [Session Lock](/linux/dotfile/knowledge-cards/session-lock/)。

## 場景二點六：桌面 shell 畫得出來但互動死掉（進程活著卻 wedged）

**症狀**：bar / 狀態列還在螢幕上、看起來一切正常，但點它的按鈕（工作區切換、系統匣圖示）沒反應，keybind 叫不出啟動器（wofi / 內建 launcher）。同時焦點視窗（例如終端機）打字完全正常——鍵盤到得了應用程式，只是桌面 shell 的互動死了。

**原因**：這是跟場景二（工具掛了）不同的一類故障，關鍵差別在**進程還活著**。場景二是 process 崩潰退出（`pgrep` 沒輸出），殺了重啟就好；這裡的桌面 shell（如 caelestia / Quickshell）進程還在跑（`pgrep` 找得到、STAT 是正常的 `S`、在 `poll` 等事件、CPU 不高），但它內部的某個子系統初始化失敗了——常見是 QML scene 的某個物件因為上游錯誤沒建起來、變成 null，於是負責「keybind → 開抽屜」「bar 按鈕互動」的模組對 null 讀屬性、整條互動接線死掉。bar 之所以還畫得出來，是它還停在初始化失敗前那一幀的畫面：**畫得出來不等於還活著**，跟鎖屏那課（畫面有密碼框不等於真的在鎖）是同一個陷阱。

上游觸發常是渲染層。實測案例：VM 的 GPU 只提供到 GLSL 1.20，而 shell 的 shader 需要 GLES 100/300/330，pipeline 建不起來（log 狂噴 `Failed to build graphics pipeline state`），這次渲染失敗把 scene 初始化打斷，drawers 狀態物件變 null。

**診斷（別看 pgrep，讀 shell 自己的 log）**：

`pgrep` 在這裡會騙你——它回報「在跑」，但那不等於「在運作」。權威來源是 shell 自己的 log，而且這種 log 常常**不在 journalctl、也不在你猜的路徑**，要用該 shell 專屬的 log 指令：

```bash
# caelestia 的例子：用它自己的 CLI 印 shell log
caelestia shell -l 2>&1 | tail -40
# 看的是 QML 的 TypeError：對 null 讀屬性 = 那個子系統死了
#   scene: @modules/Shortcuts.qml: TypeError: Cannot read property 'launcher' of null
```

另一個活性探針是 shell 的 **IPC 回不回真實狀態**：正常時查抽屜列表會回傳名字，子系統死掉時回空——這比「進程在不在」精準得多：

```bash
# 子系統活著 → 列出 bar/launcher/session…；死掉 → 回空
caelestia shell ipc call drawers list
```

**恢復步驟**：重啟 shell 讓 scene 重建。以 caelestia 為例：

```bash
caelestia shell -k     # 殺掉卡住的 shell
caelestia shell -d     # 重新啟動（detached）
```

**驗證修好了，看子系統回來、不是看 pgrep**：重啟後 process 一定在（`pgrep` 本來就會有），要確認的是接線恢復——`caelestia shell ipc call drawers list` 從「回空」變成列出真實抽屜名、log 不再噴 null 的 TypeError。這對應「重啟成功要驗子系統狀態、不是驗 process 存在」的通用紀律。

**判讀與其他場景的界線**：`pgrep` 有輸出 + bar 畫得出來 → 別急著判「正常」；點不動 / keybind 死掉就是 wedged 的訊號，往 shell 自己的 log 查。這跟場景二（process 真的沒了、`pgrep` 空）、場景三（compositor 整個凍結、連終端機打字都不行）都不同——這裡 compositor 正常、焦點視窗鍵盤正常，只有 shell 的互動接線死。判「進程活著到底有沒有在運作」的通用招式，見 [程序、服務與狀態怎麼判](/linux/debug/process-service-state-diagnosis/)。

**預防**：留意 shell log 裡持續出現的 shader / 渲染 pipeline 錯誤——在 VM 或 GL 支援不足的環境，這類錯誤可能非致命地存在（shell 大致能用），但一次渲染失敗就可能打斷 scene 初始化、把互動接線弄死。VM 環境要確認 GPU 提供的 GL / GLSL 版本足夠（virtio-gpu 走 mesa/zink 提供 GL 3.3+），或在 shell 設定關掉需要高階 shader 的效果。

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

方法 C — 如果完全無回應，先嘗試 Magic SysRq：

Magic SysRq 是 kernel 層級的緊急操作介面，即使 userspace 完全卡死也能回應。按住 `Alt+SysRq`（筆電通常是 `Alt+Fn+SysRq`），然後依序按 `R E I S U B`（每個鍵間隔幾秒）：

- `R` — 把鍵盤從 raw mode 搶回來
- `E` — 對所有 process 送 SIGTERM
- `I` — 對所有 process 送 SIGKILL
- `S` — sync 所有檔案系統
- `U` — remount 所有檔案系統為 read-only
- `B` — 立即 reboot

這比直接斷電安全——sync + unmount 步驟會盡量保護磁碟上的資料。Arch Linux 預設可能停用 SysRq，需在 `/etc/sysctl.d/` 設定 `kernel.sysrq=1` 啟用。

方法 D — 如果 SysRq 也無效，按住電源鍵強制關機：

這是最後手段。Linux 的 ext4/btrfs 檔案系統有 journal 保護，強制關機通常不會損壞**檔案系統結構**。但 journal 保護的是 metadata 一致性，正在寫入的使用者資料（未存檔的文件、正在下載的檔案）仍然可能遺失或損壞。重開機後正常登入 TTY、啟動 Hyprland 即可。如果開機過程有異常，用 `journalctl -b -1 -p err` 查看上次開機的錯誤訊息，確認是否有檔案系統修復紀錄。

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
