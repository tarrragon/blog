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
ping -c1 <鏡像或 8.8.8.8>                  # 對外通？

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
visudo -c                                   # 驗證 sudoers 語法（別跳過，寫錯會鎖死 sudo）
```

## 讓外部連得進來

- 啟用 sshd：`systemctl enable --now sshd`。
- 驗證在聽：`ss -lntp | grep :22`。
- 佈 key（有 key 時）或先走密碼登入。細節與無 key 路徑見 [remote-access](remote-access.md)。

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
