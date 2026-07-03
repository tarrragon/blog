---
title: "AUR 建置失敗的分層判讀"
date: 2026-07-03
description: "paru / yay 裝 AUR 套件失敗——helper 自己載入不了、編譯叫不存在的編譯器、makepkg 說架構不符、或 build 跑一半停住時，定位是資源、二進位漂移、烤入路徑還是宣告缺失"
weight: 7
tags: ["linux", "arch", "aur", "build", "debugging"]
---

[AUR](/linux/dotfile/knowledge-cards/aur/) 套件的安裝是在本機從原始碼編譯，這讓它的失敗面比官方 repo 套件多出一整層：官方套件的失敗集中在「抓不抓得到」（網路、資料庫、簽章，見 [安裝期套件與網路故障排除](../../install/package-and-network-troubleshooting/)），AUR 套件在抓到之後還要在你的機器上 build 成功——編譯環境、函式庫版本、架構宣告都可能讓它斷在半路。本篇把一輪 ARM VM 實測踩到的建置失敗分層整理成判讀路由：每一層有不同的權威檢查，判對層就能避免「build 失敗就懷疑軟體不支援這平台」這種昂貴的誤判。

## 先排資源層：build 中斷優先查磁碟

一次大型編譯（上百步的 C++ 專案）停在中途，最廉價也最常見的解釋是資源耗盡。實測案例：一次 build 停在第 120/227 步，同一份原始碼在清出磁碟空間後接著編就過——中斷的根因是宿主磁碟寫滿，跟 aarch64 相容性完全無關。`df -h` 加 `free` 是 build 中斷後的第一組檢查，先排除掉廉價解釋再往下懷疑，完整的判讀紀律見 [診斷心法](../diagnosis-read-authoritative-state/)。

## 型態一：預編二進位的版本半衰期（`-bin` 套件）

AUR 的 `-bin` 套件是別人在某個時間點編好的二進位，它對「當時的系統函式庫」連結。rolling 發行版的函式庫 soname 輪替快，一次 `pacman -Syu` 之後，預編二進位依賴的舊版函式庫可能已經被換掉——二進位還在、但載入直接失敗。實測案例：`paru-bin` 的 aarch64 二進位連結 `libalpm.so.15`，系統升級後 libalpm 已是 `.so.16`，helper 自己就起不來。

判讀訊號是 `error while loading shared libraries: libxxx.so.N: cannot open shared object file`——注意這是「工具自己壞了」，跟它要裝的套件無關。兩條修法對應不同取捨：

- **改用原始碼建置的 helper**：`yay` 從 AUR 以 makepkg 建置（Go 專案、編譯快），建置當下就對系統現有的 libalpm 連結，對這類 soname 漂移免疫。長期用 rolling 發行版時這條比較划算。
- **重建 `-bin` 包**：重跑一次該 `-bin` 套件的安裝讓它抓新版二進位。前提是上游已經對新 soname 重新發布，時效上受制於維護者。

這條機制對所有 `-bin` 後綴的 AUR 套件成立：`-bin` 換到的是「省編譯時間」，付出的是「跟系統函式庫版本綁定的半衰期」。系統更新頻繁、或架構冷門（上游重發慢）時，半衰期會明顯縮短。

## 型態二：建置設定烤入發行版套件（`makepkg.conf` 管不到的路徑）

編譯期叫到一個不存在的工具時，直覺是去 `/etc/makepkg.conf` 找設定，但有一類路徑是**烤入發行版套件本身**的：發行版建置自家套件時使用的工具鏈路徑，被序列化進了套件的建置中繼資料，之後所有透過該套件觸發的編譯都會沿用。實測案例：Arch Linux ARM 官方的 python 套件是用 distcc（分散式編譯）建的，`CXX=/usr/lib/distcc/bin/g++` 被烤進 python 的 sysconfig；本機編任何 Python C++ extension（AUR 的 `python-materialyoucolor`）都會去叫這個不存在的路徑，而 `makepkg.conf` 的 `!distcc` 完全管不到它——那個設定管的是 makepkg 自己的行為，管不了 python 轉手發起的編譯。

權威判讀是直接問那個工具鏈自己記了什麼：

```bash
python -c "import sysconfig; print(sysconfig.get_config_var('CXX'))"
# /usr/lib/distcc/bin/g++  ← 烤入的路徑，不是 makepkg.conf 給的
```

修法是在建置指令前用環境變數覆寫：`CXX=g++ paru -S <套件>`。這層的通用判讀：**編譯叫錯工具時，先查路徑是誰給的**——makepkg 設定、環境變數、還是烤入語言 runtime 的建置中繼資料，三個來源的修法各不相同。

## 型態三：PKGBUILD 架構宣告缺失

makepkg 建置前會比對 PKGBUILD 的 `arch` 陣列跟當前機器架構，沒列就拒建。這是 metadata 層的宣告缺失，跟「軟體真的不支援這個架構」是兩件事——很多 AUR 維護者只在 x86_64 測過、就只宣告 x86_64，程式本身可能完全可移植。判讀訊號是錯誤訊息明講架構不在清單（`doesn't support the 'aarch64' architecture`），此時用 `--mflags "-A"`（傳 `--ignorearch` 給 makepkg）繞過宣告、讓它實際嘗試編譯：編得過且跑得動，就是純宣告缺失（值得回報維護者補宣告）；編譯在架構相關的程式碼上真的失敗，才是存在性層的問題——這條跟「工具打包了、依賴的專有二進位沒有這個架構」的判讀合流，見 [平台與發行版差異的判讀地圖](../../install/platform-divergence-map/) 的套件存在性段。

## 建置成功之後：`-git` 版本與既有套件的衝突

AUR 鏈還有一類失敗發生在建置成功、安裝階段：PKGBUILD 把依賴指名到 `-git` 開發版（例如 depends 列 `quickshell-git`），跟系統已裝的官方 repo 穩定版同名衝突。互動模式下 helper 會問你要不要移除舊版；`--noconfirm` 的非互動流程則直接失敗、且已建好的包留在快取裡。修法是手動換裝：`pacman -R <穩定版>` 再 `pacman -U <快取裡建好的包>`。自動化腳本要把「AUR 依賴可能指名 `-git` 版」納入預期，先查 PKGBUILD 的 depends 再決定要不要預先移除穩定版。

## 判讀總表

| 症狀                                             | 層         | 權威檢查                               | 修法                                 |
| ------------------------------------------------ | ---------- | -------------------------------------- | ------------------------------------ |
| build 跑一半停住                                 | 資源       | `df -h`、`free`（宿主與 guest 兩側）   | 清空間後同一份原始碼續編             |
| helper 報 `error while loading shared libraries` | 二進位漂移 | `ldd $(which <helper>)` 看斷的 soname  | 換原始碼建置的 helper 或重建 `-bin`  |
| 編譯叫不存在的編譯器路徑                         | 烤入路徑   | `sysconfig.get_config_var('CXX')` 之類 | 環境變數覆寫（`CXX=g++`）            |
| `doesn't support the '...' architecture`         | 宣告缺失   | `--mflags "-A"` 實編驗證               | 編過即宣告問題、編不過才是存在性問題 |
| 建好了、安裝時跟穩定版衝突                       | 依賴衝突   | PKGBUILD 的 depends 是否指名 `-git`    | 手動 `-R` 舊版再 `-U` 裝建好的包     |

## 下一步路由

- AUR 是什麼、跟官方 repo 的信任模型差異：[AUR 知識卡](/linux/dotfile/knowledge-cards/aur/)。
- 抓套件階段（網路、資料庫、簽章）的失敗：[安裝期套件與網路故障排除](../../install/package-and-network-troubleshooting/)。
- 「這個架構到底有沒有這個套件 / 二進位」的存在性判讀：[平台與發行版差異的判讀地圖](../../install/platform-divergence-map/)。
- build 環境整體的判讀紀律：[診斷心法](../diagnosis-read-authoritative-state/)。
