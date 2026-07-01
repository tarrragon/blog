---
title: "日誌判讀與診斷工具"
date: 2026-06-30
description: "知道桌面出了問題但不確定原因時回來讀 — journalctl、dmesg、hyprctl、systemctl 的使用方式和常見 log pattern"
weight: 3
tags: ["dotfile", "linux", "hyprland", "troubleshooting", "journalctl"]
---

恢復操作解決的是「怎麼讓桌面回來」，日誌判讀解決的是「為什麼會壞掉」。前者是急救，後者是找病因。如果同一個問題反覆出現，只做急救不找根因會一直繞圈。

## journalctl：系統日誌的主要入口

systemd 的日誌系統（journal）集中收錄所有 service、kernel、user session 的 log。`journalctl` 是查詢這些日誌的指令。

### 基本用法

```bash
# 本次開機的所有日誌
journalctl -b

# 本次開機的錯誤以上等級（err + crit + alert + emerg）
journalctl -b -p err

# 本次開機，只看最後 50 行
journalctl -b -n 50

# 上一次開機的日誌（如果問題發生在上次開機、這次重開後想查）
journalctl -b -1

# 即時跟蹤新 log（類似 tail -f）
journalctl -f
```

### 過濾特定來源

```bash
# 只看 Hyprland 相關
journalctl -b | grep -i hypr

# 只看特定 systemd user unit
journalctl --user -u waybar -b

# 只看 kernel 訊息（等同 dmesg）
journalctl -b -k

# 只看某個 process 的 log（用 PID）
journalctl _PID=12345
```

### 時間範圍過濾

```bash
# 最近 10 分鐘的 log
journalctl --since "10 min ago"

# 指定時間區間
journalctl --since "2026-06-30 14:00" --until "2026-06-30 14:30"
```

## dmesg：Kernel 層訊息

`dmesg` 顯示 kernel ring buffer 的內容——硬體偵測、driver 載入、硬體錯誤這些 kernel 層面的事件。排查 GPU driver 問題、USB 裝置問題、磁碟錯誤時需要看這裡。

```bash
# 所有 kernel 訊息（帶時間戳記）
dmesg -T

# 只看錯誤和警告
dmesg -T --level=err,warn

# GPU 相關（NVIDIA）
dmesg -T | grep -i nvidia

# GPU 相關（AMD）
dmesg -T | grep -i amdgpu

# USB 相關（鍵盤滑鼠突然不回應時看這裡）
dmesg -T | grep -i usb
```

GPU driver 問題在 dmesg 裡的嚴重度差異很大：

一般 GPU hang（driver 嘗試自動恢復）：

```text
[  123.456] nvidia-modeset: ERROR: ...
[  123.789] NVRM: Xid (PCI:0000:01:00): 79, pid=1234, ...
[  124.000] amdgpu: GPU reset begin!
[  124.500] amdgpu: GPU reset succeeded
```

NVIDIA 的 `Xid` 錯誤代碼表示不同類型的 GPU 錯誤。常見的 `Xid 79` 是 GPU fallback，`Xid 31` 是 GPU setup failure。完整代碼表可在 NVIDIA 官方文件搜尋「Xid Errors」。

硬體層級故障（嚴重，可能需要檢查硬體）：

```text
[  123.789] NVRM: Xid (PCI:0000:01:00): 79, pid=1234, GPU has fallen off the bus
```

`GPU has fallen off the bus` 表示 GPU 跟主機板的 PCIe 連線完全中斷。偶發一次可能是 driver 問題，反覆出現通常是硬體故障（PCIe 供電不足、顯卡接觸不良、過熱）。

## hyprctl：Hyprland 的 Runtime 狀態查詢

`hyprctl` 是 Hyprland 提供的命令列控制工具，可以在 compositor 運行中查詢狀態和執行操作。只有在 Hyprland 正在跑的時候才能使用。

```bash
# 目前所有視窗的資訊
hyprctl clients

# 目前的 monitor 設定
hyprctl monitors

# 目前的 workspace 資訊
hyprctl workspaces

# Hyprland 版本和 build 資訊
hyprctl version

# 重新載入 config（不重啟 compositor）
hyprctl reload

# 查看上一次 config reload 是否有錯誤
hyprctl systeminfo
```

`hyprctl reload` 是測試 config 變更的安全方式。如果 config 有語法錯誤，reload 會報錯但 compositor 繼續用舊 config 跑，不會崩潰。

## systemctl：Service 狀態管理

桌面環境的工具（waybar、mako 等）如果用 systemd user unit 管理，可以用 `systemctl --user` 查看狀態和重啟。

```bash
# 查看某個 user service 的狀態
systemctl --user status waybar

# 輸出範例：
# waybar.service - Highly customizable Wayland bar
#    Loaded: loaded (/usr/lib/systemd/user/waybar.service; enabled)
#    Active: active (running) since Mon 2026-06-30 10:00:00 CST
#    Main PID: 1234 (waybar)

# 重啟
systemctl --user restart waybar

# 看最近的 log
systemctl --user status waybar -n 20
```

如果這些工具不是 systemd unit（在 Hyprland config 裡用 `exec-once` 啟動的），就不能用 `systemctl` 管理。改用 `pgrep` 和 `kill`：

```bash
pgrep waybar      # 查看是否在跑
killall waybar    # 停止
waybar &          # 背景啟動
```

## 即時資源監控

排查效能問題和記憶體耗盡時，需要看即時的系統資源使用情況。

**htop**：互動式 process 監控。按 `M` 可以按記憶體用量排序，按 `P` 按 CPU 排序。找到佔用異常的 process 後按 `F9` 可以直接 kill。

**btop**：功能更豐富的替代品，顯示 CPU、記憶體、磁碟、網路的即時使用情況，圖形化介面比 htop 直觀。

```bash
# 安裝
sudo pacman -S btop    # Arch
sudo apt install btop  # Debian/Ubuntu

# 執行
btop
```

**nvidia-smi**：NVIDIA GPU 的專屬監控工具。顯示 GPU 使用率、記憶體、溫度、跑在上面的 process。

```bash
# 一次性查看
nvidia-smi

# 持續監控（每 2 秒更新）
nvidia-smi -l 2
```

## 常見 Log Pattern 速查

| Pattern                         | 出處               | 代表什麼                                      | 下一步                                             |
| ------------------------------- | ------------------ | --------------------------------------------- | -------------------------------------------------- |
| `Out of memory: Killed process` | journalctl / dmesg | OOM Killer 殺了某個 process                   | 檢查被殺的 process 名稱、設定 swap 或 systemd-oomd |
| `GPU has fallen off the bus`    | dmesg              | NVIDIA GPU 完全失聯                           | 檢查 PCIe 供電、更新 driver、檢查硬體              |
| `Xid ... pid=`                  | dmesg              | NVIDIA GPU 錯誤（Xid 編號對應不同類型的錯誤） | 查 NVIDIA 的 Xid 錯誤代碼表                        |
| `GPU reset begin`               | dmesg              | AMD GPU driver 嘗試 reset GPU                 | 通常會自動恢復，頻繁出現代表 driver 或硬體問題     |
| `segfault at`                   | journalctl         | 某個 process segfault（記憶體存取違規）       | 記下 process 名稱，搜尋該軟體的已知 bug            |
| `Failed to start`               | systemctl status   | systemd unit 啟動失敗                         | 看完整的 status 輸出和 journalctl log 找原因       |
| `config error` / `parse error`  | 各工具自身的 log   | Config 檔語法錯誤                             | 檢查最近改過的 config 檔                           |

## 排查流程

遇到桌面環境問題時的判讀順序：

1. **判斷影響範圍**：只有一個視窗壞了、某個工具壞了、整個桌面壞了、還是系統完全不回應？影響範圍決定要看哪一層的 log。

2. **看 journalctl**：`journalctl -b -p err` 先看本次開機有沒有錯誤等級的訊息。大部分 userspace 的問題（compositor crash、工具 crash）會出現在這裡。

3. **看 dmesg**：如果 journalctl 沒有明顯線索、或症狀跟硬體有關（畫面凍結、USB 不回應），`dmesg -T --level=err,warn` 看 kernel 層有沒有硬體或 driver 錯誤。

4. **查特定工具的狀態**：`systemctl --user status <tool>` 或 `pgrep <tool>` 確認工具是否還活著。如果死了，看它最後的 log 訊息。

5. **即時監控**：如果問題是漸進式的（越來越慢、偶爾卡頓），開 `btop` 或 `htop` 觀察 CPU 和記憶體的即時趨勢，找出佔用異常的 process。

## 找到問題後的下一步

判讀完 log 確認問題類型後，行動路徑依問題性質分流：

- **Config 錯誤**：直接修 config，用 `hyprctl reload` 或重啟工具驗證。操作步驟見[常見故障場景與恢復操作](/linux/dotfile/07-desktop-maintenance/common-failures-recovery/)。
- **軟體 bug**（segfault、特定操作觸發 crash）：到該軟體的 issue tracker（通常在 GitHub）搜尋錯誤訊息。Hyprland 的 issue tracker 在 `github.com/hyprwm/Hyprland`。回報 bug 時附上 `hyprctl systeminfo` 的輸出和相關的 journalctl log。
- **GPU driver 問題**：NVIDIA 用戶檢查是否有更新的 driver 版本（`pacman -Syu nvidia`）。AMD 用戶的 driver 跟 kernel 綁定，更新 kernel 就更新 driver（`pacman -Syu linux`）。
- **硬體故障**（`GPU has fallen off the bus` 反覆出現）：軟體層面無法解決，需要檢查硬體（PCIe 插槽接觸、供電、溫度）。
