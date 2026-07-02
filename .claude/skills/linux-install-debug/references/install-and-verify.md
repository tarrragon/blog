# 安裝新系統與首次開機驗證

安裝一台新 Linux（VM 或實機）到「能從外部連入跑 bootstrap」的標準化流程。重點是每一步都有可驗證的權威狀態，不是裝完就假設好了。

## 安裝階段的決策錨點

安裝程式問的選項，用途決定選法，不是背預設值：

- **磁碟分割 / 檔案系統**：清楚要不要 UEFI（有沒有 ESP 分割 + EFI bootloader）。分割後記 PARTUUID / FSUUID，bootloader 與 fstab 靠它認分割，不是靠 `/dev/sdaX` 這種會變的名字。
- **bootloader**：UEFI 開機鏈是 NVRAM → ESP → EFI 執行檔。裝完務必確認 bootloader 真的寫進 ESP 且 NVRAM 有開機項（`efibootmgr`），否則裝好卻開不了機。
- **網路**：確認開機後網路服務會自動起（`systemctl enable` 網路服務），否則首次開機拿不到 IP、連不進去。
- **鏡像 / 套件來源**：選地理近 + 快的鏡像（實測鏡像速度可差數倍）。

## 首次開機驗證清單（裝完立刻跑）

最小系統常缺你以為有的東西。逐項驗證，缺就補：

```bash
# 基本身分與權限
id; whoami
command -v sudo || echo "缺 sudo"          # 最小安裝常無 sudo，Enable-as-admin 可能只加 wheel 群組
command -v which curl git openssh || true  # base 常缺 which / curl

# 網路真的通
ip -brief a                                # 有拿到 IP？
ping -c1 8.8.8.8                            # 對外通？（IP 層）
getent hosts archlinux.org                 # DNS 解得出？（域名層，minimal 常沒設 resolv.conf）
timedatectl                                # 時間對嗎？clock skew 會讓 TLS / 套件簽章驗證失敗

# sudo 能不能用（無 sudo 要先 su - 補裝 + 設 sudoers）
sudo -v
```

判讀：`command -v <工具>` 是「這工具在不在」的權威（比「應該有吧」可靠）。最小安裝缺 `sudo` / `which` / `curl` 是常態，不是壞掉。

## 補 sudo（最小安裝常見前置）

base 沒 sudo、而 bootstrap 又要靠 sudo 時：

```bash
su -                                        # 切 root（要 root 密碼）
pacman -S sudo                              # 或該發行版的套件管理器
echo '<user> ALL=(ALL:ALL) ALL' > /etc/sudoers.d/10-<user>
chmod 0440 /etc/sudoers.d/10-<user>         # 必須 0440，world-writable 會被 sudo 靜默忽略（檔在卻不生效）
visudo -c                                   # 驗證 sudoers 語法（別跳過，寫錯會鎖死 sudo）
```

## 讓外部連得進來

- 啟用 sshd：`systemctl enable --now sshd`。
- 驗證在聽：`ss -lntp | grep :22`。
- 佈 key（有 key 時）或先走密碼登入。細節與無 key 路徑見 [remote-access](remote-access.md)。

## 套件管理器失敗（pacman 為例，其他發行版對應概念相同）

裝好 OS、進 bootstrap 抓套件時最常撞的一類，跟「網路 / DNS」分開判：

- **db lock**：`error: failed to init transaction (unable to lock database)`。上次 pacman 崩潰沒清乾淨的 `/var/lib/pacman/db.lck` 殘留。確認沒有 pacman 在跑（`pgrep -x pacman`）後 `rm /var/lib/pacman/db.lck`。
- **簽章 / keyring 過期**：`invalid or corrupted package (PGP signature)` / `signature is unknown trust`。archlinux-keyring 過期或時間不對。先 `timedatectl`（clock skew 會讓簽章驗證失敗——這接上首次開機驗證的時間檢查），再 `pacman -Sy archlinux-keyring` 更新 keyring、必要時 `pacman-key --refresh-keys`。
- **partial upgrade 壞相依**：只 `-Sy` 不 `-Su` 會裝到跟舊系統不相容的新套件。Arch 只支援 full upgrade：`pacman -Syu`，不要單獨 `-Sy` 後裝東西。
- **mirror 逾時 / 抓不到**：換 mirror（`/etc/pacman.d/mirrorlist`）或先確認是 DNS 問題（見 [machine-unreachable](machine-unreachable.md)）。
- **stale db 404**：`failed retrieving file ... 404`（多個 mirror 都一樣）。rolling 發行版鏡像不保留舊版檔案，裝機當下的 db 幾天內就指向被輪替掉的檔名。修法 `pacman -Syu` 同步 db 再裝（接上一條：一律 `-Syu`）。

判讀：先分「連不到（網路/DNS/mirror）」vs「連得到但拒絕（lock/簽章/相依）」——前者查網路層，後者是 pacman 狀態。

### AUR / 第三方建置的失敗判讀（實測 Arch Linux ARM 踩過）

- **`-bin` 預編譯包載入錯誤**：`error while loading shared libraries: libalpm.so.<N>`。二進位對舊版系統函式庫連結、`-Syu` 後 soname 升級就斷。判讀：`ls /usr/lib/libalpm.so*` 比對版本。修法選「從原始碼 makepkg 的版本」（對系統當下的函式庫編、免疫 skew）——如 paru-bin 換 yay（Go、編得快）。
- **編譯器路徑不存在**：`command '/usr/lib/distcc/bin/g++' failed: No such file or directory`，但 `/etc/makepkg.conf` 的 `BUILDENV` 已是 `!distcc`。根因在更深一層：發行版的 python 是在 distcc build farm 編的、`CXX` 路徑烤進 python sysconfig（`python -c "import sysconfig; print(sysconfig.get_config_var('CXX'))"` 定案），所有 setuptools C/C++ extension 都中招。修法：建置時環境覆寫 `CXX=g++`（`CC` 同理）。
- **`not available for the '<arch>' architecture`**：PKGBUILD 的 `arch` 陣列沒列這個架構，常是 metadata 漏列而非真不相容（上游若是純 python + 通用 C extension 就能編）。`makepkg -A` / yay `--mflags "-A"` 繞過；編不過再回頭當真的不相容處理。
- **AUR 相依鏈的 optdepends 陷阱**：A 套件把 B 列 optdepends 時裝 A 不會拉 B——「文件說裝 A 就有 B 功能」失效時，先 `pacman -Qi <A>` 看 B 在 depends 還是 optdepends。

## bootstrap 前的最後確認

跑 dotfile 的 `install.sh` 之前：套件清單完整、機器可連入、sudo 可用。bootstrap 腳本本身要內建可觀測性（`tee` log + `ERR` trap），失敗才可診斷 —— 見 [read-logs](read-logs.md) 末段。

## 圖形桌面（若目標含桌面）

- compositor（Hyprland）要從實體圖形 VT 起，不是 SSH pty —— 見 [remote-access](remote-access.md) 的圖形 session 段。
- VM 特有：確認顯示卡類型（有無 3D 加速）、可能同時有序列主控台 + 圖形顯示兩個輸出。

## 快速路由

| 階段        | 權威驗證                                    |
| ----------- | ------------------------------------------- |
| 分割 / boot | `efibootmgr`、PARTUUID / FSUUID、ESP 有 EFI |
| 首次開機    | `id` / `command -v sudo` / `ip -brief a`    |
| 補 sudo     | `visudo -c` 驗證語法                        |
| 外部連入    | `ss -lntp \| grep :22`                      |
| bootstrap   | 套件清單 + 可連入 + sudo；腳本內建可觀測性  |
