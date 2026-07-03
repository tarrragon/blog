---
title: "Linux 安裝與機器初始化"
date: 2026-07-01
description: "在 VM 或新機器從零裝好 Linux、判讀安裝程式選項、驗證最小系統、或要從外部連入跑 bootstrap 時回來讀"
weight: 1
tags: ["linux", "install", "bootstrap"]
---

這個系列處理一件編號模組預設你已經完成的事：把一台機器從「空的」變成「能接收 dotfile 的」。模組零到九教你怎麼用 code 管理工作環境，但它們都假設你手上已經有一台裝好 Linux、裝了基本工具、能從外部連入的機器。這個系列補的就是那段地基——OS 怎麼裝、裝完缺什麼、怎麼連進去跑 bootstrap。

這段地基平常被跳過，是因為多數人是在一台早就裝好的機器上開始管理 dotfile。但只要你換到全新環境——開一台 VM、租一台雲端主機、拿到一台空機器——就會直接撞上這層：安裝程式問你十幾個選項該怎麼選、裝完發現連 `sudo` 都沒有、想從本機連進去卻還沒有 SSH key。這些都不在編號模組的範圍，卻是跑 [模組八的 bootstrap script](/linux/dotfile/08-sync-bootstrap/bootstrap-script-packages/) 之前必須先過的關。

本系列的內容來自一次完整的 VM 實測：在 Apple Silicon 的 UTM 上從 archboot（Arch 的獨立網路安裝環境 ISO）裝 Arch Linux ARM、跑 dotfile 的 `install.sh`、一路把 Hyprland 桌面拉起來。實測中每個卡關點都被記錄下來，這裡把它們蒸餾成可重用的判讀與決策，不綁特定發行版或虛擬化軟體。

## 在學習路徑中的位置

| 階段               | 對應內容                                                      |
| ------------------ | ------------------------------------------------------------- |
| 地基（本系列）     | OS 安裝決策、工具驗證、外部連入與 bootstrap 前置              |
| 為什麼管理 dotfile | [模組零：心智模型](/linux/dotfile/00-dotfile-mindset/)        |
| 怎麼管理           | [模組一到七](/linux/dotfile/01-dotfile-management/)           |
| 怎麼一鍵還原       | [模組八：同步與 Bootstrap](/linux/dotfile/08-sync-bootstrap/) |

[模組零的操作順序指引](/linux/dotfile/00-dotfile-mindset/setup-order-guide/) 列出從 OS 安裝到桌面就緒的完整依賴鏈，但只把「安裝作業系統」標成一步。本系列是那一步的展開：安裝程式每個選項背後的取捨、裝完之後的驗證、以及連入機器的幾種路徑。

## 文章

| 文章                                                                   | 主題                                                                                         | 回答什麼問題                                        |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| [安裝過程用到的基礎操作](basic-operations/)                            | 系列用到的基礎操作：`su -`、nano 編輯、檔名/指令大小寫、shell 符號（已熟可跳過）             | 照做時撞到沒見過的基礎指令怎麼辦                    |
| [Linux 安裝選項判讀](install-option-decisions/)                        | 安裝程式各選項的決策方針：locale、網路、鏡像、磁碟分割、檔案系統、bootloader                 | 安裝程式問我這個選項，我該根據什麼選                |
| [最小安裝後的工具驗證與補足](minimal-install-verify/)                  | 最小系統缺哪些必要工具、怎麼驗證、怎麼補                                                     | 為什麼裝完連 sudo 都沒有、bootstrap 跑不起來        |
| [安裝期套件與網路故障排除](package-and-network-troubleshooting/)       | 第一次抓套件就失敗：分「連不到（DNS/mirror）」vs「連得到但被拒（db lock/簽章/partial/404）」 | 剛裝好跑 pacman 就報錯，是網路還是套件管理器的問題  |
| [外部連入、SSH key 與無 key 的 bootstrap 路徑](ssh-keyless-bootstrap/) | 啟用 sshd、從本機連入、設 SSH key，以及還沒有 key 時怎麼把 dotfile 弄進去                    | 怎麼從舒適的本機終端機操作新機器、沒有 key 時怎麼辦 |
| [可除錯的 bootstrap：把可觀測性內建進安裝腳本](observable-bootstrap/)  | bootstrap 失敗時怎麼留下可診斷的痕跡：log 落地、錯誤定位、狀態 dump                          | 安裝腳本失敗時，為什麼我只能瞎找                    |
| [讓機器跑無人值守的長任務](unattended-remote-work/)                    | 無人值守執行的三個障礙與解：NOPASSWD sudo、終端機多工器、推送認證，以及 agent 權限放行的取捨 | 怎麼讓機器在我離開後自己跑完任務、把成果送回來      |
| [平台與發行版差異的判讀地圖](platform-divergence-map/)                 | 差異的四層（套件管理器 / 套件名 / 存在性 / 版本節奏）、除錯前先定平台、bootstrap 分歧判準    | 跨平台的清單與腳本該怎麼切、除錯時先確認什麼        |
| [GUI 應用的安裝驗證](gui-apps-install-verify/)                         | 拆包生態（本體與功能模組分離）、首跑同意對話框、播放驗證鏈、VM 硬體解碼回退                  | GUI 應用裝了打不開 / 無聲 / 不能播該查哪一層        |
| [接手陌生機器的盤點](inventory-unknown-machine/)                       | 只讀不改的八層盤點：服務與自啟、排程、開放 port、套件、設定與 secret 落點、監控現況          | 接手一台別人裝好、已在跑的機器，怎麼盤清楚再動手    |

機器裝好、能連入之後若出問題（連不上、終端機亂、程式行為怪），除錯與診斷自成一組，見同層的 [Linux 除錯與診斷](../debug/)。

## 依情境的讀法

主線那幾篇照「安裝 → 驗證 → 連入 → 可除錯 → 無人值守」的順序，是「從零開一台新機器、到讓它自己跑活」的完整路線，但不是每個讀者都從零開始：

- **接手一台別人已裝好的機器**：OS 已經在、上面還跑著前人留下的服務，先讀 [接手陌生機器的盤點](inventory-unknown-machine/) 用只讀不改的方式盤清楚它在跑什麼；機器乾淨、只是別人裝的，直接從 [最小安裝後的工具驗證與補足](minimal-install-verify/) 切入，確認它缺不缺你流程要的工具。
- **雲端主機初始化**：雲端主機多半已附 OS image、已有 sudo 與注入的 key，適用的是 [外部連入、SSH key 與無 key 的 bootstrap 路徑](ssh-keyless-bootstrap/) 跟 [可除錯的 bootstrap](observable-bootstrap/)，前兩篇的 ISO 安裝可略過。
- **bootstrap 失敗來 debug**：直接讀 [可除錯的 bootstrap](observable-bootstrap/)，它也涵蓋「腳本不是你寫的、只想 debug 一次失敗」的情況。
- **讓機器無人值守跑活**：機器已能連入操作，只想設好讓它在你離開後自己跑長任務或 agent，直接讀 [讓機器跑無人值守的長任務](unattended-remote-work/)。
- **遇到問題要除錯**：機器已在跑但出狀況（連不上、終端機亂、程式行為怪），進 [Linux 除錯與診斷](../debug/)，從 [診斷心法](../debug/diagnosis-read-authoritative-state/) 建立判讀紀律，再依症狀分流。
- **裝好後想讓它自己顧**：服務跑起來後，主動確認這台有沒有在監控自己的服務死活（`systemctl show sshd -p OnFailure`），沒有就從最簡單的 OnFailure + ntfy 建起——遠端機器至少把 sshd 掛上，掛了就失聯。見 [服務掛了怎麼自動知道](../debug/service-failure-monitoring/)。

## 跟其他模組的交叉引用

- [模組八：Bootstrap script 設計](/linux/dotfile/08-sync-bootstrap/bootstrap-script-packages/)——本系列是它的前置；bootstrap 假設套件清單完整、機器可連入，本系列補「在那之前」。
- [模組五：Hyprland VM 測試](/linux/dotfile/05-hyprland-config/hyprland-vm-setup/)——本系列的 VM 安裝是它的下游前置；裝好機器才能測 Hyprland。
- [模組七：日誌判讀與診斷工具](/linux/dotfile/07-desktop-maintenance/log-reading-diagnostic-tools/)——「可除錯的 bootstrap」與它呼應：前者談怎麼產生可診斷的 log，後者談怎麼讀。
- [Linux 除錯與診斷](../debug/)——本系列裝好、連入之後的下游；出問題時的判讀紀律與情境分流。
- [Linux 工具選單](../tools/)——安裝與除錯要用的工具（CLI / 圖形桌面 / 遠端）有哪些選擇、推薦用哪些。
- [Infra 心智模型：拿到雲端帳號的第一天](/infra/00-infra-mindset/first-day-with-cloud-account/)——雲端主機的機器初始化是本系列的上游情境；被指派 infra 工作、拿到一台雲端主機後，先過本系列的 OS 連入與 bootstrap 前置，再進 infra 的資源管理。
