# 機器連不到或起不來

從你這端往那台機器一層層確認哪裡斷，不要反覆重試同一個連線動作。連線失敗是最終症狀。

## 遠端機器突然連不上

鄰居表（IP→MAC）是同網段 / VM 的好權威來源，要對方鏈路層有回應才填得起。**用 `ip neigh` 而非 `arp -a`**：`ip`（iproute2）在現代最小系統一定有，`arp`（net-tools）常沒裝、跑了 command not found 反而誤導。

- 目標 IP 條目 `INCOMPLETE`（`arp -a` 顯示 `incomplete`）→ 鏈路層沒機器回應 = 網路沒起來或機器沒跑（不是 SSH 問題）。
- 一個實測：VM SSH timeout、鄰居表整個網段 guest 全 incomplete、只有閘道（宿主橋接介面）好 → 定位「宿主橋沒事、橋另一頭沒 VM 在講話」→ 去看 VM 網路 / 開機。

定位到「機器在跑但網路沒起」後，去主控台（不是 SSH）：

- `ip -brief a` 看有沒有拿到 IP。
- `systemctl status dhcpcd`（或 `systemd-networkd`）看網路服務。
- `sudo systemctl restart <網路服務>` 重拉。IP 回來 + 鄰居表條目變有 MAC = 通了。

IP / host key 變了（別名連錯、host key 被擋）→ 見 [remote-access](remote-access.md) 的 SSH 連不上段。

## 網路通、但域名解析不了（DNS）

能連 IP、連不上任何用域名的東西（`ping 8.8.8.8` 通、`ping google.com` / `pacman -Sy` / `curl https://` 失敗）→ DNS 斷了，不是網路層斷，判讀要分開。

- 權威檢查：`ping <IP>` 通而 `ping <域名>` 不通、或 `getent hosts <域名>`（`resolvectl query <域名>` 若有 systemd-resolved）解不出。
- 成因：`/etc/resolv.conf` 沒有可用 nameserver（新裝 / 網路重設後沒填）、或 DNS 服務沒起。
- 修：先看 `/etc/resolv.conf` 是不是 symlink（`ls -l /etc/resolv.conf`）——若指向 `systemd-resolved`（`../run/systemd/resolve/stub-resolv.conf`），手改會被覆寫，要走 `resolvectl` / `systemd-resolved` 設定；若是普通檔，補一行 `nameserver 1.1.1.1`。
- **剛裝好的最小系統特別常撞**：`ip -brief a` 有 IP 但 `pacman` / bootstrap 抓不到套件，看起來像「網路好好卻裝不了」，根因是 DNS 沒設。

## 虛擬機開不起來

先判「guest 內部（OS 層）vs 宿主側（虛擬化 / QEMU 層）」。宿主側錯誤在 guest 還沒開機前就跳出、跟 guest 裝什麼無關。

實測案例：QEMU 報「找不到 ROM 檔」（如 `efi-virtio.rom`）拒絕啟動。**不要直接跳「缺檔要重裝」**：

1. 先確認檔在不在 —— `find <虛擬機軟體安裝目錄> -name '<rom>'`。檔明明在 → 不是缺檔，是執行時路徑問題。
2. **主因：app 因隔離屬性被搬到唯讀 / 隨機路徑執行**（macOS Gatekeeper app translocation、`xattr` quarantine），讓 QEMU 解析資源的相對路徑失效——「檔在卻找不到」多半是這個。
3. 順手排除兩個伴隨故障（不會特定產生 romfile 錯、但常同時出現）：殘留 helper 行程（`pgrep -af 'qemu|<虛擬機軟體>'`，上次崩潰沒清乾淨佔資源）、宿主磁碟滿（`df -h`）。

多數情況：完全退出虛擬機軟體（清殘留 helper）+ 清宿主磁碟 + 重啟即恢復。

## 隱形的共同根因：磁碟滿 / 檔案系統唯讀

一串看似獨立的故障常有一個隱形共同根因，寫入失敗是關鍵——太多東西依賴寫入。

- **磁碟滿**：`df -h`。SSH 被斷、編譯 / 安裝中途失敗、log 寫不進、VM 狀態檔存不下 → 連不上 / 開不起來。短時間撞到「連線斷 + 任務失敗 + 服務怪」一串症狀時，`df -h` 要很早做。
- **檔案系統被 remount 成唯讀**（ext4 偵測到錯誤會自保 remount-ro）：一切寫入失敗、症狀像磁碟滿但 `df` 有空間。`mount | grep -w ro`、`dmesg | grep -iE 'read-only|remount|EXT4-fs error'` 抓。
- **清錯地方的陷阱**：宿主 vs guest 是兩個獨立檔案系統。VM 宿主磁碟滿 ≠ guest 內磁碟滿。兩側都 `df -h` 確認，清空間也要清對側。

## 快速路由

| 症狀                    | 檢查                                | 定位                           |
| ----------------------- | ----------------------------------- | ------------------------------ |
| SSH TCP timeout         | `ip neigh`（`INCOMPLETE`？）        | 網路沒起 / 機器沒跑 → 去主控台 |
| `Connection refused`    | `systemctl status sshd`             | 服務沒聽 → 起 sshd             |
| ping IP 通、域名不通    | `getent hosts <域名>` / resolv.conf | DNS 沒設，非網路層斷           |
| VM 開不起來、宿主側報錯 | 資源在不在 → 主因路徑隔離           | 宿主狀態問題，別急著重裝       |
| 一串症狀同時發生        | `df -h` + `mount \| grep -w ro`     | 磁碟滿 / fs 唯讀常是共同根因   |
