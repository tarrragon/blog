---
title: "安裝期套件與網路故障排除：pacman / DNS / mirror / keyring"
date: 2026-07-02
description: "剛裝好系統第一次抓套件就失敗（pacman 報錯、DNS 解不出、mirror 逾時、簽章過期、db lock）、要判斷是網路層還是套件管理器狀態時回來讀"
weight: 4
tags: ["linux", "install", "pacman", "dns", "troubleshooting", "package-management"]
---

裝好 OS、第一次跑套件管理器抓 bootstrap 要的套件時，最常撞的一類故障是「套件裝不下來」。這類故障的第一步判讀，是把它拆成兩層完全不同的問題：**連不到（網路 / DNS / mirror）**，還是**連得到但被拒（套件管理器自己的狀態）**。這兩層的檢查工具、根因、修法都不一樣，先分對層再往下查，才不會拿修 DNS 的方法去治簽章過期。這篇以 Arch 的 `pacman` 為主要案例，其他發行版的套件管理器概念對應相同。其中 **stale mirror db 的 404** 與 **非互動環境缺 `--noconfirm` 導致 exit 1** 兩條是這批 VM 實測真的踩到的；db lock、簽章 / 校時、DNS 解析這幾類屬通用分層判讀，一併收進來是為了讓「連不到 vs 被拒」這張檢查表完整，不代表每條都在實測中命中過。

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

**第 2 步通、第 3 步不通 = DNS 問題**，這是最小安裝最典型的落點：IP 層明明通（`ping 8.8.8.8` 有回應），但域名解不出來，因為 `/etc/resolv.conf` 還沒設 nameserver。這時 pacman 會卡在解析 mirror 主機名。修法是給系統一個 resolver——臨時可直接寫 `/etc/resolv.conf`（`nameserver 1.1.1.1`）。先看它是什麼（`ls -l /etc/resolv.conf`）：啟用了 `systemd-resolved` 或 NetworkManager 的系統上它是那些服務管理的 symlink，手寫會被覆蓋，治本要透過該網路管理服務設定 DNS；裸 Arch 最小安裝若沒啟用這些服務，它通常就是一個普通檔案，手寫即持久生效。

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
sudo timedatectl set-ntp true     # 開 NTP 自動校時（SSH 進最小系統無 polkit 互動代理、裸跑會被拒，要 sudo）
```

時間對了還失敗，才是 keyring 本身的問題（archlinux-keyring 太舊）：`sudo pacman -Sy archlinux-keyring` 更新 keyring，必要時 `sudo pacman-key --refresh-keys`。順序是先校時再動 keyring，因為時間不對時連 keyring 都更新不了。

### partial upgrade：只同步不升級造成的相依斷裂

`conflicting dependencies` 或裝完某個套件後系統行為異常。根因是在 rolling 發行版上只做了 `pacman -Sy`（同步資料庫）就裝新套件，卻沒 `-u`（升級既有套件）——新套件依賴新版函式庫，但系統還是舊的，相依對不上。Arch 只支援 full upgrade：**一律 `pacman -Syu`，永遠不要單獨 `-Sy` 之後裝東西**。這條規則救掉這一整類故障。

partial upgrade 還有另一張臉：安裝單一套件時撞 `<lib> exists in filesystem (owned by <pkg>)`，例如 `pacman -Sy git` 回 `libstdc++ ... exists in filesystem (owned by gcc-libs)`。這是新套件要帶進較新版的共享庫、它要落地的檔跟系統上舊版留下的同名檔撞在一起——一樣是「只 `-Sy` 沒 `-u`」的徵兆，只是報成「檔案已存在」而非「相依衝突」。修法同上：`-Syu` 把系統一起升上去，舊檔被正常換掉、衝突就消。裸容器 base image 特別容易踩，因為它的內建 db 跟已裝套件版本落差往往更大。（若確認不是只 `-Sy`、`-Syu` 也沒解，那個檔可能是套件外的 untracked 檔佔了路徑，是另一類真正的檔案衝突、要手動處理那個檔。）

### stale db 404：裝機當下的資料庫已經過期

`error: failed retrieving file '...' 404`，而且換好幾個 mirror 都一樣。這是 rolling 發行版特有的時序陷阱：Arch 的 mirror 不保留舊版檔案，你裝機時 ISO 內建的套件資料庫指向的檔名，可能幾天內就被輪替掉了——資料庫說有這個檔、mirror 上已經沒有。修法跟上一條同源：`pacman -Syu` 先把資料庫同步到最新，檔名對上了就抓得到。這也是為什麼「一律 `-Syu`」是 Arch 的鐵律，而不只是建議。

### pacman 7 的 sandbox 在容器內套不起來（container 專屬）

`error: restricting filesystem access failed because the Landlock ruleset could not be applied: Operation not permitted`，接著 `error: switching to sandbox user 'alpm' failed`、`failed to synchronize all databases`。pacman 7 起在下載階段預設用一個受限使用者 `alpm` 加 Landlock（Linux 的檔案系統存取控制 LSM）把自己能碰的路徑縮到最小，這是安全強化。問題是在受限的 container 裡——預設 seccomp profile 擋掉 `landlock_*` 系統呼叫、或核心沒開放該權限——這層 sandbox 套不起來，pacman 就直接放棄同步、而不是降級略過。

這條的判準很明確：**pacman 7 起才有、且只在容器裡出現**。真實 Arch 主機的核心允許 Landlock，同一份設定不會撞；把 image 跑在會走模擬（qemu）的架構上時也可能因 sandbox 相關的 syscall 被擋而出現類似症狀。修法是在 `/etc/pacman.conf` 的 `[options]` 段加 `DisableSandbox`（或單次 `pacman --disable-sandbox ...`）關掉這層。但要劃清邊界：這是**容器的**逃生閥、不是通用修法——別把 `DisableSandbox` 寫進會部署到真機的 `pacman.conf`，只在容器 fixture 裡加，真機保留 sandbox。更保守的替代是給容器一個放行 `landlock_*` syscall 的自訂 seccomp profile（`--security-opt seccomp=…`），保留 pacman 的 sandbox 而非整個關掉；但容器本身通常已是拋棄式、多這層 sandbox 的邊際安全收益低，所以 `DisableSandbox` 多半是夠用的務實解。

## 判讀總表

| 症狀                                | 層     | 權威檢查                      | 修法                                        |
| ----------------------------------- | ------ | ----------------------------- | ------------------------------------------- |
| 主機名解不出                        | 網路   | `getent hosts <域名>`         | 設 resolver（注意 symlink）                 |
| ping IP 通、域名不通                | DNS    | `ping 8.8.8.8` vs `getent`    | 設 `/etc/resolv.conf` 或網管服務            |
| mirror 慢 / 逾時                    | 網路   | 換 mirror 測速                | 改 mirrorlist                               |
| unable to lock database             | pacman | `pgrep -x pacman`             | 確認無後刪 db.lck                           |
| PGP signature / unknown trust       | pacman | `timedatectl`（先校時）       | 校時 →（仍失敗）更新 keyring                |
| conflicting / partial               | pacman | 是否只跑了 `-Sy`              | `pacman -Syu`（永遠 full）                  |
| `exists in filesystem (owned by X)` | pacman | 是否只跑了 `-Sy` 就裝單一套件 | `pacman -Syu`（partial upgrade 的另一張臉） |
| retrieving file 404（多 mirror）    | pacman | rolling stale db              | `pacman -Syu` 同步再裝                      |
| `alpm sandbox failed` / Landlock    | pacman | 是否在容器內（pacman 7 起）   | `pacman.conf` 加 `DisableSandbox`（僅容器） |

## 下一步

- 這幾步用到的網路驗證，完整版在[最小安裝後的工具驗證與補足](../minimal-install-verify/)。
- 裝機時選 mirror / locale / 時區的決策，見[Linux 安裝選項判讀](../install-option-decisions/)。
- 跨發行版時「這個套件名 / 這個旗標在別的發行版叫什麼」的差異判讀，見[平台與發行版差異的判讀地圖](../platform-divergence-map/)。
- 套件抓下來了、但 bootstrap 腳本本身失敗要 debug，見[可除錯的 bootstrap](../observable-bootstrap/)。
- 系統跑起來後才出的套件問題（AUR 建置失敗、`-bin` 包 soname 斷裂等），屬除錯範疇，見[Linux 除錯與診斷](../../debug/)。
