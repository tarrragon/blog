---
title: "Linux 桌面的故障隔離模型"
date: 2026-06-30
description: "從 Windows 轉過來想知道 Linux 桌面掛了會不會整台崩潰時讀 — kernel vs userspace 隔離、compositor 是 userspace process、TTY 救生通道與其限制"
weight: 1
tags: ["dotfile", "linux", "hyprland", "troubleshooting"]
---

Linux 桌面環境的故障隔離建立在一個結構性的設計決策上：**顯示合成器（compositor）是 userspace process，不是 kernel 的一部分**。這意味著 Hyprland 掛了只是桌面消失，作業系統核心還在正常運作。

本文用「桌面環境」泛指使用者看到的圖形介面整體。技術上，Hyprland 是 Wayland compositor——負責視窗合成和輸入管理，不含完整桌面環境（DE）的套件管理、設定面板等元件。GNOME、KDE Plasma 才是完整的 DE。但在故障隔離的討論中，關鍵區分是 kernel space vs userspace，compositor 和 DE 都在 userspace 這一側。

## Kernel 與 Userspace 的隔離邊界

作業系統分成兩個執行空間。Kernel space 負責硬體驅動、記憶體管理、process 排程這些基礎設施。Userspace 跑所有應用程式，包括桌面環境本身。

兩個空間之間有硬體層級的隔離——CPU 的保護環機制（ring 0 是核心層級、ring 3 是應用程式層級，硬體強制限制 ring 3 的程式碼存取 ring 0 的記憶體）。Userspace 的 process 不管怎麼崩潰，都不會直接影響 kernel。Kernel 會清理掉崩潰的 process、回收它佔用的記憶體，然後繼續運作。

這個隔離機制解釋了一個關鍵差異：為什麼 Linux 上一個 app crash 通常只是那個視窗消失，而不會拖垮整台機器。

## 為什麼 Windows 會藍屏

Windows 的藍屏（Blue Screen of Death, BSOD）是 kernel panic 的表現——作業系統核心本身遇到無法恢復的錯誤，只能停機。

Windows 藍屏頻率較高的結構性原因在於**顯示驅動的執行位置**。Windows 把 GPU 驅動放在 kernel mode（WDDM 架構），NVIDIA 或 AMD 的驅動程式碼直接跑在核心空間。驅動有 bug 時，錯誤發生在 kernel space，清理掉再繼續的選項不存在——繼續執行可能造成資料損壞，只能停機。

藍屏頻率高是架構選擇的代價。把驅動放在 kernel mode 可以減少 context switch 的效能開銷，GPU 效能更好。代價是驅動 bug 的爆炸半徑從「app crash」升級成「整台停機」。Windows 10/11 已加入 TDR（Timeout Detection and Recovery）機制——GPU driver hang 時系統嘗試 reset driver 而非直接藍屏，大幅降低了 GPU 導致的 BSOD 頻率。但架構上 driver 仍在 kernel mode，藍屏的可能性仍然存在。

## Linux 桌面的架構差異

Linux 桌面環境的顯示合成器（Hyprland、Sway、KDE Plasma 的 KWin）跑在 userspace。它們透過 DRM/KMS（Direct Rendering Manager / Kernel Mode Setting，Linux 的顯示子系統介面）跟 kernel 的 GPU 驅動溝通，但合成器本身的程式碼不在 kernel space 裡。

這個架構選擇的效果：

**Compositor crash**。Hyprland 如果遇到 segfault 或其他 fatal error，kernel 終止這個 userspace process。所有由它管理的視窗消失，螢幕回到 TTY 登入畫面或黑屏。但 kernel 還在跑——其他 TTY 可以登入，SSH 可以連線，背景的 service 繼續運作。

**GPU driver bug**。Linux 的 GPU 驅動分兩層：kernel module（可動態載入的核心擴充模組，如 `nvidia.ko`、`amdgpu.ko`）負責硬體操作，userspace 的 Mesa / NVIDIA userspace driver 負責 OpenGL/Vulkan 實作。Kernel module 出問題理論上可以 kernel panic，但實際行為取決於驅動。AMD 的開源 `amdgpu` 通常會嘗試 reset GPU 而非直接 panic，常見的表現是畫面凍結幾秒後恢復。NVIDIA 的閉源 `nvidia.ko` 是隔離模型的主要例外——kernel 社群無法審查或修復其程式碼，hang 時恢復能力遠弱於 amdgpu，經常拖垮整個 session 且 TTY 切換也受影響。這是後續[故障場景](/linux/dotfile/07-desktop-maintenance/common-failures-recovery/)中 NVIDIA 相關 caveat 的根源。

**應用程式 crash**。Firefox、VS Code、任何 GUI 程式崩潰，只有那個視窗消失。Compositor 繼續管理剩下的視窗，桌面環境不受影響。

## TTY：kernel 存活時的首選救生通道

TTY（TeleTYpewriter）是 Linux 核心直接提供的純文字終端機介面，獨立於任何桌面環境。systemd 預設配置下有 6 個 virtual console（TTY1-TTY6）。Wayland compositor（如 Hyprland）通常佔用 TTY1，其餘可用。

切換方式：`Ctrl+Alt+F2`（切到 TTY2）到 `Ctrl+Alt+F6`（切到 TTY6）。

TTY 的重要性在於它**不依賴 compositor**。Hyprland 掛了、compositor crash 導致桌面消失——只要 kernel 還活著、GPU driver 仍能處理 VT switch，TTY 就能切過去登入操作：

- 用 `htop` 或 `ps` 查看哪個 process 出問題
- `kill` 有問題的 process
- 用 `vim` 或 `nano` 修改配置檔
- 重新啟動 Hyprland（`Hyprland` 指令）
- 如果需要，正常 `reboot`

TTY 切換失效的情境有兩種：kernel panic（極罕見）和 GPU 完全 hang 導致 VT switch 本身卡住（NVIDIA 閉源驅動在 Wayland 上較常見，需確保 `nvidia_drm.modeset=1`）。後者的替代手段是 SSH 遠端登入或 Magic SysRq 鍵（見[常見故障場景](/linux/dotfile/07-desktop-maintenance/common-failures-recovery/)的場景三）。

## 記憶體耗盡（OOM）的處理機制

Linux kernel 有 OOM Killer（Out of Memory Killer）機制——當記憶體和 swap 都用完、kernel 無法再分配新頁面時，自動挑選佔用記憶體最多、重要性最低的 process 強制終止，釋放記憶體讓系統繼續運作。

OOM Killer 的行為有時超出使用者的預期——它可能直接終止 Hyprland（因為 compositor 通常佔用不少記憶體），導致桌面突然消失。但關鍵是：**系統沒有崩潰**。Kernel 還在、TTY 還在、SSH 還在。

預防 OOM 的常見做法：

- 設定 swap（即使用 SSD，2-4GB 的 swap 也能在記憶體壓力大時提供緩衝）
- 啟用 `systemd-oomd`（userspace 的 OOM 管理，比 kernel OOM Killer 更早介入、更可控）
- 監控記憶體用量（`btop` 或 `htop` 可以看即時狀態）

## 故障層級速查

| 故障層級                | 症狀                       | 系統影響            | 恢復手段                    |
| ----------------------- | -------------------------- | ------------------- | --------------------------- |
| 應用程式 crash          | 單一視窗消失               | 無                  | 重開該程式                  |
| 工具 crash（waybar 等） | 狀態列 / 通知 / 啟動器消失 | 無                  | 重啟該工具                  |
| Compositor crash        | 所有視窗消失、黑屏         | 桌面環境不可用      | TTY 登入、重啟 compositor   |
| GPU driver hang         | 畫面凍結                   | 桌面環境不可用      | TTY 或 SSH、kill compositor |
| OOM                     | 系統極慢或桌面被殺         | 部分 process 被終止 | TTY 登入、清理 process      |
| Kernel panic            | 完全停機                   | 全機不可用          | 只能重開機                  |

前五個層級都有恢復手段，只有 kernel panic 需要重開機。日常使用中遇到的故障多數落在前三層。
