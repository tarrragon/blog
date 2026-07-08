---
title: "一個修法埋下三步後的雷：pacman 404 → -Syu 升 kernel → docker 起不來"
date: 2026-07-08
slug: "pacman_syu_kernel_reboot_docker"
draft: false
description: "Arch 上裝套件 404、修完之後 docker daemon 突然起不來、iptables 報 nf_tables 錯誤時回來讀 — 症狀與根因差三步的因果鏈與判讀法。"
tags: ["arch", "pacman", "kernel", "docker", "nftables", "systemd", "debug", "root-cause"]
---

> **核心議題**：一個看似無關、且當下成功的修法，可能埋下三步之後才引爆的雷。症狀出現的層（docker / iptables）跟根因所在的層（執行中 kernel 與磁碟 module 版本錯配）可以隔很遠，照症狀直覺除錯會走錯方向。判讀的解法是讀權威狀態、把症狀層與根因層對開。
> **案例骨幹**：在一台 Arch Linux ARM VM 上要裝 mosh、`pacman -S` 回 404，修法牽出 `-Syu` 升級了 kernel，之後裝 docker、daemon 起不來、`iptables` 報 `nf_tables` 錯誤——三個步驟串成一條因果鏈。

## 問題情境：三步串成的因果鏈

事情從一個單純的安裝開始，最後停在一個看起來毫不相關的 docker 故障。三步：

第一步，`pacman -S mosh` 中途對某個相依套件回 HTTP 404、`failed to retrieve some files`。這不是網路問題——是本地套件資料庫過時，記錄的版本在 mirror 上已被新版取代（Arch 的 partial upgrade 陷阱：只裝新套件、沒同步整個系統）。

第二步，修法是 `sudo pacman -Syu` 把整個系統同步升級、對齊資料庫與 mirror。這步成功、mosh 也裝好了。但 `-Syu` 順帶把 kernel 從一個版本升到了下一版——這個副作用當下沒有任何徵兆。

第三步，繼續裝 docker、`systemctl start docker`，daemon 起不來。journal 顯示：

```text
iptables (nf_tables): Could not fetch rule set generation id: Invalid argument
failed to register "bridge" driver: ... iptables ... (exit status 4)
```

照這個症狀，直覺會往「docker 網路設定 / 防火牆規則 / iptables 版本」除錯——全部是錯的方向。

## 根因：執行中 kernel 與磁碟上的 module 錯配

真正的根因在第二步埋下：`-Syu` 升級了 kernel，把新版的 kernel modules 裝到磁碟上，但**機器沒有重開機**。於是系統處在一個錯配狀態——執行中的還是舊 kernel，而磁碟上舊 kernel 的 module 目錄已經被換成新版了（`/usr/lib/modules/` 只剩新版）。執行中的 kernel 找不到自己對應版本的 modules，`nf_tables` 這個 netfilter 模組載入失敗，docker 建 NAT chain 時透過 iptables 操作 nftables 就報了那個 `Invalid argument`。

症狀在 iptables / docker 這一層冒出來，根因卻在「kernel 與 module 版本錯配」這一層。兩層隔了三個操作步驟，這是為什麼照症狀查會鑽進 docker 網路設定的死巷。

## 解法：讀權威狀態、重開機

判讀的關鍵是讀權威狀態、把「執行中的」跟「磁碟上的」對開：

```bash
uname -r                                 # 執行中的 kernel 版本
ls -d /usr/lib/modules/*/                # 磁碟上已裝的 kernel module 目錄
```

兩者不一致，就是 kernel 升級後未重開機。這一秒就定位了——不需要碰任何 docker 或 iptables 設定。解法是重開機進新 kernel，執行中版本與磁碟 module 對齊、`nf_tables` 載得進來、docker daemon 正常啟動。

```bash
sudo systemctl reboot
# 重開後
uname -r                                 # 對上磁碟版本
systemctl start docker && systemctl is-active docker   # active
```

## 判讀徵兆：什麼時候該懷疑這條鏈

- **一個服務突然起不來、而你剛跑過 `-Syu` 或系統更新、且沒重開機** → 先懷疑 kernel / module 錯配，`uname -r` vs `ls /usr/lib/modules` 一秒驗。這不限 docker——任何依賴 kernel module（netfilter、檔案系統、虛擬化）的服務都可能中招。
- **錯誤訊息指向一個「底層設施」（iptables、nftables、module load）而不是應用本身** → 症狀層可能不是根因層，往「這個底層設施依賴的東西（kernel module）狀態對不對」查，而不是去調應用的設定。
- **一個修法「當下成功」不代表沒有副作用** → `-Syu` 修好了 404、也升了 kernel。修完一個問題後、下一個看似無關的故障要把最近的變更列進嫌疑名單，即使它們表面上不相干。

讀權威狀態、以機器實際狀態為準而非症狀表象，是這類「症狀與根因差好幾層」問題的通用解法。
