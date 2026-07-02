---
title: "GUI 應用的安裝驗證：拆包、首跑對話框與播放判讀"
date: 2026-07-02
description: "裝檔案管理器、瀏覽器、媒體播放器後打不開、無聲、不能播，或首跑冒出同意對話框不知道該不該勾時回來讀"
tags: ["linux", "desktop", "gui", "install", "multimedia"]
---

GUI 應用的安裝驗證跟 CLI 工具走不同的判讀鏈：CLI 工具裝完 `command -v` 加一次試跑就能定案，GUI 應用則有三個 CLI 沒有的失敗層——依賴鏈拆包（裝了本體、缺功能模組）、首跑同意對話框（程式要求使用者決策才繼續）、播放輸出鏈（視窗有了、聲音或畫面沒有）。這三層都有各自的權威判讀位置，本篇以一輪 VM 實測（檔案管理器、瀏覽器、媒體播放器、音樂串流）把它們走一遍。

## 拆包生態：裝了本體不等於裝了功能

發行版為了控制依賴體積，會把一個應用的核心跟功能模組拆成多個套件，預設只裝核心。這個設計讓「安裝成功」跟「功能可用」變成兩件事，而缺件的症狀往往是靜默的：

- **VLC 的解碼器是獨立 plugin**：Arch 的 `vlc` 本體開得起來、UI 完整，播 H.264 影片卻回報 `Codec 'h264' is not supported`——解碼能力在 `vlc-plugin-ffmpeg`（或整組 `vlc-plugins-all`）。judgment 訊號是「應用正常啟動、特定格式失敗」，權威來源是應用自己的 log（`vlc --verbose=2`）。
- **pipewire 的 session manager 是獨立套件**：`pipewire` 常被依賴鏈拉進來，但沒有 `wireplumber` 就沒有人建立音訊 graph——daemon 在跑、`wpctl status` 的 Sinks 段是空的、所有應用無聲且不報錯。補 `wireplumber` + `pipewire-pulse`（多數 GUI 應用走 PulseAudio API）後輸出裝置立即出現。
- **optional dependency 不會自動安裝**：套件宣告的 optdepends 是「裝了會多什麼功能」的提示、不是安裝動作。影片縮圖、壓縮格式支援、硬體加速常落在這層，`pacman -Qi <pkg>` 的 Optional Deps 段列出哪些沒裝。

判讀原則：GUI 應用「開得起來但某個功能不動」時，先查發行版有沒有把那個功能拆成獨立套件，再懷疑設定或相容性。

## 首跑同意對話框：程式在等使用者決策

不少 GUI 應用第一次啟動會彈出需要使用者決策的對話框，最典型的是 VLC 的「Privacy and Network Access Policy」：

VLC 聲明自己不蒐集、不傳輸任何個人資料，但它能自動向第三方網路服務抓取播放清單裡媒體的中繼資料（封面圖、曲名、演出者）——這個行為等於把「你在播哪些檔案」暴露給第三方服務，所以 VLC 開發者要求使用者明示同意（Allow metadata network access 勾選框、預設勾選）後才允許自動連網。

這個對話框的判讀是用途導向：拿 VLC 播本機影片、看下載的影片檔，中繼資料抓取沒有用處、取消勾選讓播放器完全離線工作；拿它管理音樂庫、想要自動補封面跟曲目資訊，才需要同意。同意與否都能在偏好設定（Privacy / Network Interaction）事後改。

首跑對話框對自動化流程有一層額外影響：無人值守安裝驗證時，應用會停在對話框等輸入、腳本側只看到「程式起了但沒繼續」。VLC 把這兩個決策記在 `~/.config/vlc/vlcrc` 的 `qt-privacy-ask` 與 `metadata-network-access` 兩個鍵——首跑後檔案才生成，而且 VLC 退出時會整檔重寫（幾千行的完整設定 dump），把它納入 dotfile 版控會持續產生無意義的 diff，比較合理的處理是讓首跑對話框留給人、或在自動化腳本裡預先寫入只含這兩鍵的最小 vlcrc。

同型的首跑決策也出現在瀏覽器（預設瀏覽器詢問、錯誤回報同意）跟大型 GUI 應用（遙測同意）。它們的共通判讀：對話框問的是「要不要讓程式自動連外 / 回傳資料」，答案取決於這台機器的用途與隱私要求，安裝驗證流程要把「首跑會有互動」納入預期、不是當成故障。

## 播放驗證鏈：三個權威位置

「有沒有真的在播」的驗證不靠肉眼跟喇叭，三個權威位置各管一段：

| 驗證對象     | 權威來源            | 工具與判準                                               |
| ------------ | ------------------- | -------------------------------------------------------- |
| 視窗存在     | compositor 的視窗表 | `hyprctl clients` 有該應用的 class 條目                  |
| 音訊真的在出 | 音訊伺服器 graph    | `wpctl status` Streams 段有該應用的 stream 且 `[active]` |
| 失敗的原因   | 程式自己的 log      | `vlc --verbose=2`、瀏覽器 `--enable-logging=stderr`      |

把「管線通不通」跟「應用會不會播」拆開驗證能大幅縮短歸因：先用本機音檔 `pw-play <file>` 打通音訊路徑（stream 出現 `[active]` 代表 guest 側無誤），再測應用層；應用層失敗就跟管線無關，往解碼器、DRM、應用 log 查。串流再多拆一層：先用無 DRM 的串流（一般影音網站）確立網路串流基線，DRM 內容（Spotify、Netflix 類）的失敗才能歸因到 DRM 層——DRM 在非 x86_64 架構的可用性判讀見 [平台與發行版差異的判讀地圖](../platform-divergence-map/) 的套件存在性段。

## VM 特有：硬體解碼回退

在 VM 裡播放影片，第一次開檔常會閃一個錯誤對話框（`failed to create video output`）然後正常播放——這是硬體解碼回退的痕跡：播放器預設先嘗試硬體加速解碼（VDPAU / VAAPI），虛擬 GPU（如 virtio-gpu）沒有視訊解碼能力，嘗試失敗後回退軟體解碼重建輸出。log 上的特徵是一次性的 decoder error 加上之後穩定的 `avcodec decoder` 軟體解碼行；實體機器有 GPU 解碼時不會出現。VM 裡想要乾淨啟動，在播放器偏好設定停用 hardware-accelerated decoding 即可——這是機器特性設定，適合留在該機器本機、不進共用 dotfile。

## 下一步路由

- 套件在這個平台 / 架構存不存在、名字叫什麼：[平台與發行版差異的判讀地圖](../platform-divergence-map/)
- 音訊、行程、服務狀態的權威判讀：[Linux 除錯與診斷](../../debug/)
- GUI 應用清單怎麼進 bootstrap：[模組八：Bootstrap script 設計](/linux/dotfile/08-sync-bootstrap/bootstrap-script-packages/)
