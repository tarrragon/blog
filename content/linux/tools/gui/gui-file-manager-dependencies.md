---
title: "在 Hyprland 加圖形檔案管理員：依賴足跡與桌面環境耦合"
date: 2026-07-01
description: "在最小化 Hyprland 環境要裝圖形檔案管理員（或任何桌面 app）、需要判斷它會拖進多少相依、以及輕量與功能完整之間怎麼取捨時回來讀"
weight: 2
tags: ["linux", "tools", "gui", "hyprland", "package-management", "file-manager"]
---

在一個最小化的 Hyprland 環境加一個圖形應用，真正的成本不是那個 app 本身，是它拖進來的相依樹。Hyprland 這類 window manager 刻意不預設桌面環境，所以你手上是一台「只有合成器、沒有 GNOME/KDE/Cinnamon 那層服務」的機器。這時候裝一個看似單純的圖形檔案管理員，不同實作拖進來的東西可以差一個數量級——因為有些檔案管理員假設某個桌面環境的服務就在旁邊，有些則刻意做成桌面無關的獨立程式。

這篇用「圖形檔案管理員」當具體案例，但判讀方式適用於任何你想加進最小環境的桌面 app：先看它的相依樹拖進什麼，再決定值不值得。

## 三種實作的實測相依

同樣是「有側欄、有選單、能瀏覽掛載裝置」的圖形檔案管理員，三個主流實作在一台已有 GTK3 的 Arch ARM 機器上，各自會**新裝**的套件數量如下（`pacman -S --needed --print` 實測）：

| 檔案管理員 | 出身     | 新裝套件數 | 會拖進的關鍵相依                                                             |
| ---------- | -------- | ---------- | ---------------------------------------------------------------------------- |
| Thunar     | XFCE     | 8          | xfce4 基礎庫（exo、libxfce4util/ui、xfconf、startup-notification、libgtop）  |
| PCManFM-Qt | LXQt     | 7          | libfm-qt、layer-shell-qt、menu-cache、lxqt-menu-data                         |
| Nemo       | Cinnamon | 38         | cinnamon-desktop、xapp、整套 gvfs + udisks2（libblockdev×8、mdadm、parted…） |

差異的來源不是「檔案管理員本身多大」，Thunar 跟 Nemo 的主程式都在 7–10 MB 量級。差的是後面那條相依鏈。

### Thunar 與 PCManFM-Qt：桌面無關的獨立程式

Thunar 與 PCManFM-Qt 都是刻意做成「不依賴完整桌面環境」的檔案管理員。Thunar 雖然出身 XFCE，但它拖進的 8 個套件是 XFCE 的**基礎函式庫**（設定系統 xfconf、工具庫 libxfce4util、UI 庫 libxfce4ui），不是 XFCE 桌面本身——你不會因此裝到 XFCE 的面板、視窗管理器或 session。PCManFM-Qt 走 Qt 棧，帶的 `layer-shell-qt` 反而是 Wayland 原生整合的加分項。這兩個裝下去，機器還是那台只有 Hyprland 的機器，只是多了一個能開的檔案管理員。

### Nemo：為 Cinnamon 而生，假設 Cinnamon 在旁邊

Nemo 是 Cinnamon 桌面的檔案管理員，它的相依反映了這個出身：`cinnamon-desktop` 提供背景與顯示設定的整合、`xapp` 是 Cinnamon 系列跨桌面的整合層。即使你只想要「開一個視窗看檔案」，這些桌面元件也會一起裝上，因為 Nemo 在程式碼層面就假設它們存在。這不是 Nemo 寫得差，是它本來就不是設計給「裸 window manager」用的——它預期自己跑在 Cinnamon session 裡。

Nemo 那 38 個套件裡，還有一大塊來自它把 `gvfs` 列成硬相依（下一節說明 gvfs 是什麼），而 gvfs 又拖進整套磁碟管理棧（udisks2、libblockdev 的 8 個子模組、mdadm、parted、volume_key）。所以 Nemo 的相依樹是「Cinnamon 桌面元件」加「完整磁碟/檔案系統管理」兩層疊起來的結果。

## gvfs：側欄那些功能不是檔案管理員自己做的

截圖裡檔案管理員側欄常見的「Devices（掛載裝置）」「Network（瀏覽網路芳鄰）」「Trash（垃圾桶）」，多半不是檔案管理員自己實作的，是 **gvfs（GNOME Virtual File System）** 這個後端提供的。gvfs 用一層虛擬檔案系統把「掛載 USB 隨身碟」「連 SMB 網路分享」「把檔案丟垃圾桶」這些操作抽象成統一介面，讓檔案管理員不必自己處理每一種裝置與協定。

這帶出一個重要判讀：**輕量不是免費的，當功能對等時，相依會靠攏。** Thunar 與 PCManFM-Qt 把 gvfs 列成 optional dependency——不裝也能開檔案管理員，但側欄就沒有掛載、垃圾桶、網路那些功能。要讓輕量檔案管理員有截圖裡那種完整側欄，你得自己補 gvfs，而補上 gvfs 就會連帶拖進它的相依（udisks2、polkit、fuse3、libsecret 等）。Nemo 把 gvfs 設成硬相依，只是把這個選擇替你做了。

所以公平的比較不是「Thunar 8 個 vs Nemo 38 個」，而是「Thunar + gvfs + 縮圖 vs Nemo」。補齊功能後，Thunar 這條路線仍然省下的是 Nemo 獨有的那層——`cinnamon-desktop`、`xapp`、`xapp-symbolic-icons` 這些桌面環境耦合元件。那層，才是「為了一個檔案管理員裝半個 Cinnamon」真正可以省掉的部分。

## tumbler：縮圖也是一個額外套件

檔案管理員顯示圖片/影片縮圖，同樣不是內建的，靠的是縮圖服務。Thunar 家族用 `tumbler`，影片縮圖再另外需要 `ffmpegthumbnailer`。這是「一個功能對應一個額外套件」的又一個例子——最小環境裡，縮圖、掛載、網路瀏覽每一項都是你明確選擇要不要付相依成本的功能，而不是預設就有。

## Wayland / Hyprland 下的注意事項

這些檔案管理員多數是 X11 時代的 GTK/Qt 程式，在 Wayland 下會透過 XWayland 或原生 Wayland 後端執行。PCManFM-Qt 帶的 `layer-shell-qt` 是 Wayland 的 layer-shell 整合；GTK 的 Thunar/Nemo 在 Wayland 下一般走 GTK 自己的 Wayland 後端。開啟/儲存檔案對話框、拖放、縮圖預覽在裸 Hyprland（沒有完整 portal 服務）下的實際行為，取決於有沒有裝 `xdg-desktop-portal` 與對應的後端。

> **[待實機驗證]** 以下行為尚未在本系列的 Hyprland 實機環境確認，先標記待驗證：(1) Thunar 補上 gvfs 後，側欄的 Devices/Network/Trash 是否如預期出現並可用；(2) tumbler + ffmpegthumbnailer 的縮圖在 Wayland 下是否正常產生；(3) 三者在裸 Hyprland（無完整桌面 portal）下的檔案對話框與拖放行為；(4) Nemo 在沒有 Cinnamon session 的情況下，桌面圖示、設定整合等功能是否失效或報錯。這些是「相依裝了之後實際好不好用」的問題，相依數量本身（上表）已是實測確定值。

## 風險與注意事項

**移除後的孤兒套件**：裝了 Nemo 再反悔移除時，`cinnamon-desktop`、`xapp` 那一票被拖進來的相依會變成沒人依賴的孤兒（`pacman -Qtd` 可列出）。用 `pacman -Rns nemo` 移除時帶走遞迴相依，或定期清孤兒，否則那半個 Cinnamon 會留在系統裡。輕量檔案管理員因為拖進的東西少，這個問題也小。

**桌面環境服務未跑的副作用**：把為某個桌面環境寫的 app 裝進裸 window manager，它預期的那些服務不在時，部分功能可能靜默失效或在啟動時報錯。這類問題不會在相依解析階段出現——套件裝得起來，是執行時才發現某個整合功能沒作用。（Nemo 在無 Cinnamon 下的具體表現，見上方待驗證項。）

**選型判準**：最小化的 Hyprland 想要一個圖形檔案管理員，優先考慮桌面無關的 Thunar 或 PCManFM-Qt；需要截圖那種完整側欄功能時，明確補上 `gvfs`（掛載/垃圾桶/網路）與 `tumbler`（縮圖），把相依成本花在你真的要用的功能上。以 Thunar 為例，完整一套是 `pacman -S thunar gvfs tumbler ffmpegthumbnailer`（`gvfs` 給掛載/垃圾桶/網路、`tumbler` + `ffmpegthumbnailer` 給圖片與影片縮圖）。除非你本來就跑 Cinnamon，否則不建議為了單一檔案管理員把 Nemo 的整套桌面元件裝進來——那是付了桌面環境耦合的代價，卻沒用到那個桌面環境。

## 待實機驗證清單

這篇的相依數量與相依樹是實測確定的；以下「裝了之後實際體驗」的部分待在 Hyprland 實機補驗證：

- Thunar + gvfs + tumbler + ffmpegthumbnailer 的完整側欄與縮圖行為
- 三種檔案管理員在裸 Hyprland（XWayland vs 原生 Wayland、portal 有無）下的差異
- Nemo 脫離 Cinnamon session 的功能缺損範圍
- 加進 `packages-arch.txt` 後，bootstrap 一鍵安裝這條路線的實際落地結果

## 下一步

- 這篇談的是「加桌面 app 時怎麼判讀相依成本」，套件清單本身怎麼設計、怎麼被 bootstrap 一鍵安裝，見 [模組八：Bootstrap script 與套件清單](/linux/dotfile/08-sync-bootstrap/bootstrap-script-packages/)。
- Hyprland 本體與配套工具的安裝，見 [模組五：安裝與環境建置](/linux/dotfile/05-hyprland-config/hyprland-installation/)。
- 這台 Hyprland 是在 VM 上建起來測的，VM 能測什麼、什麼要留到實機，見 [VM 環境設定與測試矩陣](/linux/dotfile/05-hyprland-config/hyprland-vm-setup/)。
