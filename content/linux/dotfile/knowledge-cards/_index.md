---
title: "Linux 術語卡"
date: 2026-06-29
description: "dotfile 管理、平鋪式視窗管理、桌面客製化、遠端連線與網路、安裝與除錯相關的術語索引"
weight: 99
tags: ["dotfile", "linux", "knowledge-cards"]
---

Linux 系列（dotfile / 安裝 / 除錯 / 工具）共用的關鍵術語。各卡片會在對應章節深入說明、這裡提供快速查閱入口，install / debug / tools 各篇的術語首現處也會連回這裡。

術語卡會隨教材擴展逐步補充。

## 語言與工具

| 卡片                                                                                         | 主題                                                         |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| [Lua Scripting Language（腳本語言）](/linux/dotfile/knowledge-cards/lua-scripting-language/) | Hyprland / Neovim 配置檔使用的腳本語言，配置檔需要的最小知識 |
| [GNU Stow](/linux/dotfile/knowledge-cards/gnu-stow/)                                         | symlink farm manager，dotfile 管理的核心工具之一             |
| [AUR（Arch User Repository）](/linux/dotfile/knowledge-cards/aur/)                           | Arch 社群自建套件庫，paru/yay 為何用來裝官方 repo 沒有的套件 |
| [Quickshell](/linux/dotfile/knowledge-cards/quickshell/)                                     | Qt6/QML 的桌面 shell runtime，Caelestia 的執行引擎           |

## 系統概念

| 卡片                                                                                                                | 主題                                                               |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [TTY](/linux/dotfile/knowledge-cards/tty/)                                                                          | Linux 核心的純文字終端機介面，桌面故障時的救生通道                 |
| [initramfs](/linux/dotfile/knowledge-cards/initramfs/)                                                              | 開機初期掛真 root 之前的臨時根檔系統，ESP 大小要算進它             |
| [UEFI Boot Chain（開機鏈）](/linux/dotfile/knowledge-cards/uefi-boot-chain/)                                        | 韌體到 kernel 的交棒過程，bootloader 選型與開機故障的依據          |
| [Partition Identification（分區識別，PARTUUID / FSUUID）](/linux/dotfile/knowledge-cards/partition-identification/) | 分區的穩定識別方式，fstab / bootloader 怎麼指涉分區                |
| [字型的可用集合在 process 啟動時決定](/linux/dotfile/knowledge-cards/font-availability-at-startup/)                 | 裝了字型但畫面還是豆腐時的判讀依據                                 |
| [Session Lock](/linux/dotfile/knowledge-cards/session-lock/)                                                        | 鎖屏是 compositor 持有的安全狀態，殺 process 不等於解鎖            |
| [Compositor（合成器）](/linux/dotfile/knowledge-cards/compositor/)                                                  | Wayland 下把畫面合成與視窗管理合一的核心程式，多個系統狀態的持有者 |
| [fontconfig](/linux/dotfile/knowledge-cards/fontconfig/)                                                            | 字型搜尋、匹配與 fallback 的底層服務，fc-* 工具分工                |
| [logind Session 與 Seat](/linux/dotfile/knowledge-cards/logind-session-seat/)                                       | 誰持有 VT 與輸入權，SSH 起不了桌面與 loginctl 假象的根因           |
| [systemd OnFailure](/linux/dotfile/knowledge-cards/systemd-onfailure/)                                              | 服務進 failed 時觸發另一個 unit，每次失敗都觸發的告警洗爆陷阱      |
| [systemd drop-in](/linux/dotfile/knowledge-cards/systemd-drop-in/)                                                  | 不改原檔疊加設定，升級不覆蓋、一次套所有 service、systemctl edit   |

## 容器與 prod 對齊

| 卡片                                                                                                           | 主題                                                                         |
| -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [環境 as code 的三個尺度](/linux/dotfile/knowledge-cards/environment-as-code-scope/)                           | dotfile / Dockerfile / IaC 的分界與 repo 歸屬判準                            |
| [Golden Path / paved road](/linux/dotfile/knowledge-cards/paved-road-golden-path/)                             | 鋪好的預設路徑消除重複決策、org 的 developer portal vs 個人的 repo+腳本+路標 |
| [Prod Parity Principle（生產環境對等原則）](/linux/dotfile/knowledge-cards/prod-parity-principle/)             | 本機 runtime 對齊的是凍結舊環境而非最新版                                    |
| [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)                                         | tag 要釘到 OS 世代才凍結得住，浮動 tag 是不可重現的來源                      |
| [glibc 與 musl](/linux/dotfile/knowledge-cards/glibc-vs-musl/)                                                 | 兩種 libc 的差異，prod 是 Debian 就別用 alpine                               |
| [Package Manager 抽象層](/linux/dotfile/knowledge-cards/package-manager-abstraction/)                          | dotfile 跨 distro 可攜，綁發行版的只有裝套件那一層                           |
| [發行版打包粒度](/linux/dotfile/knowledge-cards/distro-package-granularity/)                                   | 同一指令跨發行版拉的套件數差一量級，node 一裝拉 300+                         |
| [apt 安裝的交易原子性](/linux/dotfile/knowledge-cards/apt-transaction-atomicity/)                              | 批次安裝全有或全無，一個沒打包的名字讓整批都不裝                             |
| [Docker Named Volume Ownership（掛載點擁有者）](/linux/dotfile/knowledge-cards/docker-named-volume-ownership/) | 空 volume 首次掛載沿用 image 內該路徑 owner，非 root 寫不進的根因            |
| [Runtime Secret Injection（機密注入）](/linux/dotfile/knowledge-cards/runtime-secret-injection/)               | token / 金鑰不進 image layer 也不進 repo，runtime 注入才對                   |
| [OOM Killer and Exit Code 137（OOM killer 與退出碼 137）](/linux/dotfile/knowledge-cards/oom-exit-code-137/)   | 137=128+SIGKILL、cgroup 記憶體上限、可用量比設定小的根因                     |

## 遠端連線與網路

| 卡片                                                                                                              | 主題                                                                      |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [TCP Connection Roaming（連線與漫遊）](/linux/dotfile/knowledge-cards/tcp-connection-roaming/)                    | TCP 綁 4-tuple、換 IP 即斷，SSH 為何不能漫遊、mosh 為何用 UDP             |
| [Connection Refused vs. Timeout（連線被拒與逾時）](/linux/dotfile/knowledge-cards/connection-refused-vs-timeout/) | 逾時=可達性層、被拒=服務層，兩種症狀相反的除錯方向                        |
| [Mosh Local Echo Prediction（本地回顯預測）](/linux/dotfile/knowledge-cards/mosh-local-echo-prediction/)          | 高延遲下打字即時的機制、跟 CJK 顯示的衝突、怎麼驗真的走 mosh              |
| [SSH Key Storage（SSH 金鑰儲放與 authorized_keys）](/linux/dotfile/knowledge-cards/ssh-key-storage/)              | 私鑰在客戶端 / 公鑰在伺服器、per-device 金鑰、deploy vs full key          |
| [git credential helper](/linux/dotfile/knowledge-cards/git-credential-helper/)                                    | git 怎麼不手打帳密取得 HTTPS 認證、gh auth login 與手設 !helper 同一機制  |
| [Terminal CJK Input（終端 CJK 雙寬字與即時輸入）](/linux/dotfile/knowledge-cards/terminal-cjk-input/)             | 雙寬字顯示錯位、raw 模式擋 IME 組字、貼上繞法                             |
| [SIGHUP（斷線即死訊號）](/linux/dotfile/knowledge-cards/sighup-hangup-signal/)                                    | 連線掛斷送前景程序的訊號、直接掛 SSH 的任務活不過斷線、session 層為何存在 |

## 文化與術語

| 卡片                                                           | 主題                                           |
| -------------------------------------------------------------- | ---------------------------------------------- |
| [Rice（桌面視覺客製化）](/linux/dotfile/knowledge-cards/rice/) | Linux 桌面社群的視覺客製化文化，詞源和涵蓋範圍 |
