---
title: "Linux 安裝與機器初始化"
date: 2026-07-01
description: "在 VM 或新機器從零裝好 Linux、判讀安裝程式的各個選項、確認最小系統缺哪些必要工具、或要從外部連入跑 dotfile bootstrap 時回來讀"
weight: -1
tags: ["dotfile", "linux", "install", "bootstrap"]
---

這個系列處理一件編號模組預設你已經完成的事：把一台機器從「空的」變成「能接收 dotfile 的」。模組零到九教你怎麼用 code 管理工作環境，但它們都假設你手上已經有一台裝好 Linux、裝了基本工具、能從外部連入的機器。這個系列補的就是那段地基——OS 怎麼裝、裝完缺什麼、怎麼連進去跑 bootstrap。

這段地基平常被跳過，是因為多數人是在一台早就裝好的機器上開始管理 dotfile。但只要你換到全新環境——開一台 VM、租一台雲端主機、拿到一台空機器——就會直接撞上這層：安裝程式問你十幾個選項該怎麼選、裝完發現連 `sudo` 都沒有、想從本機連進去卻還沒有 SSH key。這些都不在編號模組的範圍，卻是跑 [模組八的 bootstrap script](/dotfile/08-sync-bootstrap/bootstrap-script-packages/) 之前必須先過的關。

本系列的內容來自一次完整的 VM 實測：在 Apple Silicon 的 UTM 上從 archboot（Arch 的獨立網路安裝環境 ISO）裝 Arch Linux ARM、跑 dotfile 的 `install.sh`、一路把 Hyprland 桌面拉起來。實測中每個卡關點都被記錄下來，這裡把它們蒸餾成可重用的判讀與決策，不綁特定發行版或虛擬化軟體。

## 在學習路徑中的位置

| 階段               | 對應內容                                                |
| ------------------ | ------------------------------------------------------- |
| 地基（本系列）     | OS 安裝決策、工具驗證、外部連入與 bootstrap 前置        |
| 為什麼管理 dotfile | [模組零：心智模型](/dotfile/00-dotfile-mindset/)        |
| 怎麼管理           | [模組一到七](/dotfile/01-dotfile-management/)           |
| 怎麼一鍵還原       | [模組八：同步與 Bootstrap](/dotfile/08-sync-bootstrap/) |

[模組零的操作順序指引](/dotfile/00-dotfile-mindset/setup-order-guide/) 列出從 OS 安裝到桌面就緒的完整依賴鏈，但只把「安裝作業系統」標成一步。本系列是那一步的展開：安裝程式每個選項背後的取捨、裝完之後的驗證、以及連入機器的幾種路徑。

## 文章

| 文章                                                                   | 主題                                                                             | 回答什麼問題                                        |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------------- |
| [安裝過程用到的基礎操作](basic-operations/)                            | 系列用到的基礎操作：`su -`、nano 編輯、檔名/指令大小寫、shell 符號（已熟可跳過） | 照做時撞到沒見過的基礎指令怎麼辦                    |
| [Linux 安裝選項判讀](install-option-decisions/)                        | 安裝程式各選項的決策方針：locale、網路、鏡像、磁碟分割、檔案系統、bootloader     | 安裝程式問我這個選項，我該根據什麼選                |
| [最小安裝後的工具驗證與補足](minimal-install-verify/)                  | 最小系統缺哪些必要工具、怎麼驗證、怎麼補                                         | 為什麼裝完連 sudo 都沒有、bootstrap 跑不起來        |
| [外部連入、SSH key 與無 key 的 bootstrap 路徑](ssh-keyless-bootstrap/) | 啟用 sshd、從本機連入、設 SSH key，以及還沒有 key 時怎麼把 dotfile 弄進去        | 怎麼從舒適的本機終端機操作新機器、沒有 key 時怎麼辦 |
| [可除錯的 bootstrap：把可觀測性內建進安裝腳本](observable-bootstrap/)  | bootstrap 失敗時怎麼留下可診斷的痕跡：log 落地、錯誤定位、狀態 dump              | 安裝腳本失敗時，為什麼我只能瞎找                    |

## 依情境的讀法

四篇照「安裝 → 驗證 → 連入 → 可除錯」的順序，是「從零開一台新機器」的完整路線，但不是每個讀者都從零開始：

- **接手一台別人已裝好的機器**：OS 已經在，從 [最小安裝後的工具驗證與補足](minimal-install-verify/) 切入，確認它缺不缺你流程要的工具。
- **雲端主機初始化**：雲端主機多半已附 OS image、已有 sudo 與注入的 key，適用的是 [外部連入、SSH key 與無 key 的 bootstrap 路徑](ssh-keyless-bootstrap/) 跟 [可除錯的 bootstrap](observable-bootstrap/)，前兩篇的 ISO 安裝可略過。
- **bootstrap 失敗來 debug**：直接讀 [可除錯的 bootstrap](observable-bootstrap/)，它也涵蓋「腳本不是你寫的、只想 debug 一次失敗」的情況。

## 跟其他模組的交叉引用

- [模組八：Bootstrap script 設計](/dotfile/08-sync-bootstrap/bootstrap-script-packages/)——本系列是它的前置；bootstrap 假設套件清單完整、機器可連入，本系列補「在那之前」。
- [模組五：Hyprland VM 測試](/dotfile/05-hyprland-config/hyprland-vm-setup/)——本系列的 VM 安裝是它的下游前置；裝好機器才能測 Hyprland。
- [模組七：日誌判讀與診斷工具](/dotfile/07-desktop-maintenance/log-reading-diagnostic-tools/)——「可除錯的 bootstrap」與它呼應：前者談怎麼產生可診斷的 log，後者談怎麼讀。
