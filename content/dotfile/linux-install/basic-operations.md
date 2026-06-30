---
title: "安裝過程用到的基礎操作"
date: 2026-07-01
description: "照這個系列操作時撞到 su -、nano 的 Ctrl 鍵、檔名與指令的大小寫、或 > | && $() 這些沒見過的基礎操作、需要先弄懂才不被擋住時讀"
weight: 0
tags: ["dotfile", "linux", "shell"]
---

這個系列在安裝、補工具、設定 SSH 的過程中，用到一小撮基礎操作——成為 root、用 nano 改設定檔、shell 的幾個符號。Linux 的指令入門教學網路上已經很豐富，這篇不重複那些，只挑「這個系列實際用到、而且沒太多 Linux 實作經驗的人容易卡住」的那幾個介紹清楚，讓你照著操作時不會被一個沒見過的指令擋在半路。已經熟的，直接跳到 [安裝選項判讀](../install-option-decisions/)。

## 成為 root：su -

`su -` 讓你從一般使用者切換成 root（系統管理員），整個 session 都以 root 身分操作。這個系列用到它，是因為在還沒有 `sudo` 的最小系統上，要裝 sudo、改系統設定，得先成為 root——而成為 root 的方式就是 `su -`，輸入 root 密碼後進入 root 的 shell。

那個 `-` 不是可有可無的。`su`（不加 `-`）只切換身分、但保留你原本的環境（包括 `PATH`）；`su -` 則啟動一個 login shell，載入 root 自己的環境——把 `PATH` 換成 root 的（會包含 `/usr/sbin` 這類放管理工具的目錄）、工作目錄切到 root 的家。少了 `-`，有些管理指令會因為不在 `PATH` 裡而「找不到」，明明你已經是 root。所以要做系統管理，習慣用 `su -`。

`su -` 跟 `sudo` 解決的是不同情境。`sudo` 是「以 root 身分跑單一一條指令」，跑完就回到你自己；`su -` 是「整段都當 root」。這個系列先用 `su -` 是因為 sudo 還沒裝——一旦 sudo 裝好、wheel 群組授權設好，後面就改用 `sudo <指令>`，不再整段切 root。做完 root 的事，打 `exit` 回到原本的使用者。

## 用 nano 改設定檔

nano 是一個對照 vi 更直覺的文字編輯器，安裝過程改 `locale.gen`、`hostname`、`sudoers` 這些設定檔時會用到它。它的好處是所有快捷鍵都列在畫面最下面兩行，不必背。

那兩行裡的 `^` 符號代表 Ctrl 鍵。`^O` 就是 Ctrl+O、`^X` 就是 Ctrl+X。這個系列用到的幾個：

| 按鍵   | 畫面標示       | 作用                            |
| ------ | -------------- | ------------------------------- |
| Ctrl+O | `^O Write Out` | 存檔（會問檔名，按 Enter 確認） |
| Ctrl+X | `^X Exit`      | 離開（有未存變更會問要不要存）  |
| Ctrl+W | `^W Where Is`  | 搜尋——在長檔案裡跳到某個字串    |
| Ctrl+K | `^K Cut`       | 剪掉游標所在的整行              |
| Ctrl+U | `^U Paste`     | 把剪掉的內容貼回來              |

把這幾個串起來就是一次典型的設定檔編輯。以這個系列裡「解開 `locale.gen` 某一行的註解」為例：按 Ctrl+W 搜 `en_US.UTF-8 UTF-8` 跳到那行、用 Backspace 刪掉行首的 `#`、按 Ctrl+O 再 Enter 存檔、按 Ctrl+X 離開。改 `hostname` 則是 Ctrl+K 剪掉預設那行、打上新主機名、Ctrl+O、Ctrl+X。Ctrl+K 加 Ctrl+U 合起來就是「剪下再貼上」，搬移整行很順手。

## 檔名與指令的大小寫

Linux 把大小寫當成不同的字元，這對檔名跟指令都成立。`Setup` 跟 `setup` 是兩個不同的東西、`Documents` 跟 `documents` 是兩個不同的資料夾、打 `Sudo` 不會執行到 `sudo`。這條規則貫穿整個系列：執行 archboot 的安裝程式是 `setup`（全小寫），啟動 Hyprland 桌面的指令是 `Hyprland`（首字母大寫），兩者差一個字母的大小寫就是不同的目標。

這特別容易絆倒從 macOS 或 Windows 過來的人，因為那兩個系統的預設檔案系統不分大小寫——在 Mac 上 `File.txt` 跟 `file.txt` 指向同一個檔，到了 Linux 就是兩個檔。同一個專案在 Mac 上跑得好好的，搬到 Linux 卻出現「檔案找不到」，常常就是某處大小寫對不上、而 Mac 的不分大小寫把問題藏了起來。

判讀方式很簡單：在 Linux 上，指令、檔名、路徑一律照原樣的大小寫打。錯誤訊息 `command not found` 或 `No such file or directory` 在你確定東西明明就在時，先懷疑大小寫。

## shell 的幾個符號

這個系列的指令裡出現了幾個 shell 符號，它們是 shell 本身的語法、不是某個程式的參數，認得它們才讀得懂那些指令在做什麼。

`>` 跟 `>>` 是重導向，把本來會印到畫面的輸出改寫進檔案。`>` 覆蓋、`>>` 追加。系列裡 `echo '%wheel ALL=(ALL:ALL) ALL' > /etc/sudoers.d/10-wheel` 就是把那行文字寫進一個新檔，而設 `authorized_keys` 時用 `>>` 是為了追加、不洗掉既有的 key。

`|`（管線）把左邊指令的輸出，直接餵給右邊指令當輸入。傳 dotfile 進 VM 的 `tar czf - . | ssh host 'tar xzf -'` 就是把 tar 打包的資料流，不落地直接透過 ssh 送到對面解開。

`&&` 串接兩條指令，而且只有左邊成功才跑右邊。`cd ~/dotfiles && ./scripts/install.sh` 的意思是「先切到目錄，切成功了才跑腳本」——如果目錄不存在、`cd` 失敗，後面的腳本就不會在錯的地方亂跑。

`$(...)` 是命令替換，把括號裡指令的輸出，當成值填進當下這條指令。`chsh -s "$(command -v zsh)"` 會先跑 `command -v zsh` 得到 `/usr/bin/zsh`，再把這個路徑填給 `chsh`。理解這個語法，也才看得懂 [工具驗證篇](../minimal-install-verify/) 講的 `which` 地雷：當 `which` 不存在、`$(which zsh)` 算出空字串，整條指令就拿到一個空值。

順帶一提權限。`chmod` 改檔案權限，系列裡的 `chmod 440`（sudoers 檔）、`chmod 600`（私鑰）、`chmod 700`（`.ssh` 目錄）那串數字是八進位的權限碼，分別代表擁有者/群組/其他人能不能讀寫執行。這些檔對權限有要求——sudoers 必須是 440、私鑰必須只有自己讀得到，否則對應的工具會拒絕使用它們，所以那幾個 `chmod` 不是裝飾、是讓 sudo 跟 ssh 願意接受那些檔的條件。

## 下一步

認得這些基礎操作之後，就可以從 [安裝選項判讀](../install-option-decisions/) 開始走完整的安裝流程，過程中再遇到這幾個操作就不會卡。
