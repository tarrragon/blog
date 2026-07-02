---
title: "安裝期套件與網路故障排除：pacman / DNS / mirror / keyring"
date: 2026-07-02
description: "剛裝好系統第一次抓套件就失敗（pacman 報錯、DNS 解不出、mirror 逾時、簽章過期、db lock）、要判斷是網路層還是套件管理器狀態時回來讀"
weight: 4
tags: ["linux", "install", "pacman", "dns", "troubleshooting", "package-management"]
---

裝好 OS、第一次跑套件管理器抓 bootstrap 要的東西時，最常撞的一類故障是「套件裝不下來」。這類故障的第一步判讀，是把它拆成兩層完全不同的問題：**連不到（網路 / DNS / mirror）**，還是**連得到但被拒（套件管理器自己的狀態）**。這兩層的檢查工具、根因、修法都不一樣，先分對層再往下查，才不會拿修 DNS 的方法去治簽章過期。這篇以 Arch 的 `pacman` 為主要案例（本系列 VM 實測踩過的坑），其他發行版的套件管理器概念對應相同。

## 第一步：分「連不到」還是「連得到但被拒」

錯誤訊息本身就能分層，不用猜：

- **訊息提到主機名解不出、連線逾時、retrieving file 失敗** → 連不到，往網路 / DNS / mirror 查。
- **訊息提到 database lock、signature、trust、conflicting、partial** → 連得到、封包也拿到了，是套件管理器的狀態問題。

判準是問一句：「它到底有沒有成功連上 mirror？」有連上才談得到簽章、相依、db 狀態；連都沒連上，那些都還輪不到。剛裝好的最小系統最常見的是前者——網路設定還沒到位。

## 連不到那層：從實體介面往上查到域名

網路不通有好幾層，從最底層往上逐層確認，哪一層斷了一目了然。這條鏈跟[最小安裝後的驗證](../minimal-install-verify/)裡的網路檢查同源，這裡聚焦在「抓套件失敗」這個症狀上：

```bash
ip -brief a              # 1. 有沒有拿到 IP？介面 UP 且有位址
ping -c1 8.8.8.8         # 2. IP 層對外通不通？（直接打 IP、跳過 DNS）
getent hosts archlinux.org   # 3. 域名解得出來嗎？
timedatectl              # 4. 時間對嗎？（影響下一層的簽章驗證）
```

**第 2 步通、第 3 步不通 = DNS 問題**，這是最小安裝最典型的落點：IP 層明明通（`ping 8.8.8.8` 有回應），但域名解不出來，因為 `/etc/resolv.conf` 還沒設 nameserver。這時 pacman 會卡在解析 mirror 主機名。修法是給系統一個 resolver——臨時可直接寫 `/etc/resolv.conf`（`nameserver 1.1.1.1`），但要注意這個檔在很多系統上是 `systemd-resolved` 或 NetworkManager 管理的 symlink，手寫會被覆蓋；治本是透過該系統的網路管理服務設定 DNS。

**mirror 逾時 / 抓不到**：DNS 通了、但某個 mirror 慢或掛了。換 `/etc/pacman.d/mirrorlist` 到地理近且快的鏡像（實測不同 mirror 速度可差數倍）。這也接回[安裝選項判讀](../install-option-decisions/)裡選 mirror 的決策——裝機當下選錯 mirror，這裡就會慢。

## 連得到但被拒那層：pacman 自己的狀態

連上 mirror、封包也拿到了卻失敗，問題在 pacman 的本地狀態或簽章驗證。這幾種各有明確徵兆與修法：

### database lock：上次沒清乾淨的殘留

`error: failed to init transaction (unable to lock database)`。pacman 用 `/var/lib/pacman/db.lck` 這個鎖檔保證同時只有一個 pacman 在動資料庫；上次 pacman 被中斷（斷電、Ctrl+C、當掉）沒清掉鎖檔就會殘留。**先確認真的沒有 pacman 在跑**（`pgrep -x pacman`），確認沒有再刪鎖檔：

```bash
pgrep -x pacman && echo "有 pacman 在跑、別刪" || sudo rm /var/lib/pacman/db.lck
```

先查再刪這個順序重要——盲刪鎖檔時如果真的有另一個 pacman 在跑，兩個同時寫資料庫會弄壞它。

### 簽章 / keyring 過期：十之八九是時間不對

`invalid or corrupted package (PGP signature)` 或 `signature is unknown trust`。pacman 驗證每個套件的 GPG 簽章，驗證失敗最常見的根因是**系統時間不對**——這正是第一步要 `timedatectl` 的原因。時間差太多（新裝的 VM、主機板電池沒電的老機器）會讓「簽章的有效期」判斷錯誤，明明有效的簽章被判過期。先校時：

```bash
timedatectl set-ntp true     # 開 NTP 自動校時
```

時間對了還失敗，才是 keyring 本身的問題（archlinux-keyring 太舊）：`sudo pacman -Sy archlinux-keyring` 更新 keyring，必要時 `sudo pacman-key --refresh-keys`。順序是先校時再動 keyring，因為時間不對時連 keyring 都更新不了。

### partial upgrade：只同步不升級造成的相依斷裂

`conflicting dependencies` 或裝完某個套件後系統行為異常。根因是在 rolling 發行版上只做了 `pacman -Sy`（同步資料庫）就裝新套件，卻沒 `-u`（升級既有套件）——新套件依賴新版函式庫，但系統還是舊的，相依對不上。Arch 只支援 full upgrade：**一律 `pacman -Syu`，永遠不要單獨 `-Sy` 之後裝東西**。這條規則救掉這一整類故障。

### stale db 404：裝機當下的資料庫已經過期

`error: failed retrieving file '...' 404`，而且換好幾個 mirror 都一樣。這是 rolling 發行版特有的時序陷阱：Arch 的 mirror 不保留舊版檔案，你裝機時 ISO 內建的套件資料庫指向的檔名，可能幾天內就被輪替掉了——資料庫說有這個檔、mirror 上已經沒有。修法跟上一條同源：`pacman -Syu` 先把資料庫同步到最新，檔名對上了就抓得到。這也是為什麼「一律 `-Syu`」是 Arch 的鐵律，而不只是建議。

## 判讀總表

| 症狀                             | 層     | 權威檢查                   | 修法                             |
| -------------------------------- | ------ | -------------------------- | -------------------------------- |
| 主機名解不出                     | 網路   | `getent hosts <域名>`      | 設 resolver（注意 symlink）      |
| ping IP 通、域名不通             | DNS    | `ping 8.8.8.8` vs `getent` | 設 `/etc/resolv.conf` 或網管服務 |
| mirror 慢 / 逾時                 | 網路   | 換 mirror 測速             | 改 mirrorlist                    |
| unable to lock database          | pacman | `pgrep -x pacman`          | 確認無後刪 db.lck                |
| PGP signature / unknown trust    | pacman | `timedatectl`（先校時）    | 校時 →（仍失敗）更新 keyring     |
| conflicting / partial            | pacman | 是否只跑了 `-Sy`           | `pacman -Syu`（永遠 full）       |
| retrieving file 404（多 mirror） | pacman | rolling stale db           | `pacman -Syu` 同步再裝           |

## 下一步

- 這幾步用到的網路驗證，完整版在[最小安裝後的工具驗證與補足](../minimal-install-verify/)。
- 裝機時選 mirror / locale / 時區的決策，見[Linux 安裝選項判讀](../install-option-decisions/)。
- 跨發行版時「這個套件名 / 這個旗標在別的發行版叫什麼」的差異判讀，見[平台與發行版差異的判讀地圖](../platform-divergence-map/)。
- 套件抓下來了、但 bootstrap 腳本本身失敗要 debug，見[可除錯的 bootstrap](../observable-bootstrap/)。
- 系統跑起來後才出的套件問題（AUR 建置失敗、`-bin` 包 soname 斷裂等），屬除錯範疇，見[Linux 除錯與診斷](../../debug/)。
