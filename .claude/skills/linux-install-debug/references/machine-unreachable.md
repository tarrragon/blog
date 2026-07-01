# 機器連不到或起不來

從你這端往那台機器一層層確認哪裡斷，不要反覆重試同一個連線動作。連線失敗是最終症狀。

## 遠端機器突然連不上

`arp -a` 是同網段 / VM 的好權威來源（ARP 記錄 IP→MAC，要對方鏈路層有回應才填得起）：

- 目標 IP 條目 `incomplete` → 鏈路層沒機器回應 = 網路沒起來或機器沒跑（不是 SSH 問題）。
- 一個實測：VM SSH timeout、`arp -a` 整個網段 guest 全 `incomplete`、只有閘道（宿主橋接口）好 → 定位「宿主橋沒事、橋另一頭沒 VM 在講話」→ 去看 VM 網路 / 開機。

定位到「機器在跑但網路沒起」後，去主控台（不是 SSH）：

- `ip -brief a` 看有沒有拿到 IP。
- `systemctl status dhcpcd`（或 `systemd-networkd`）看網路服務。
- `sudo systemctl restart <網路服務>` 重拉。IP 回來 + `arp` 條目變有 MAC = 通了。

IP / host key 變了（別名連錯、host key 被擋）→ 見 [remote-access](remote-access.md) 的 SSH 連不上段。

## 虛擬機開不起來

先判「guest 內部（OS 層）vs 宿主側（虛擬化 / QEMU 層）」。宿主側錯誤在 guest 還沒開機前就跳出、跟 guest 裝什麼無關。

實測案例：QEMU 報「找不到 ROM 檔」（如 `efi-virtio.rom`）拒絕啟動。**不要直接跳「缺檔要重裝」**：

1. 先確認檔在不在 —— `find <虛擬機軟體安裝目錄> -name '<rom>'`。若檔明明在 → 不是缺檔，是執行時路徑 / 狀態問題。
2. 查殘留 helper 行程卡著：`ps aux | grep -iE 'qemu|<虛擬機軟體>'`（上次崩潰沒清乾淨會讓下次啟動拿不到正確資源路徑）。
3. 查宿主磁碟：`df -h`（啟動要寫暫存 / 狀態檔，滿了會失敗）。
4. 查 app 是否因隔離屬性被搬到唯讀路徑執行（macOS 的 Gatekeeper translocation、`xattr` quarantine）。

多數情況：完全退出虛擬機軟體（清殘留 helper）+ 清宿主磁碟 + 重啟即恢復。

## 磁碟滿是連鎖故障的共同根因

磁碟滿 → 寫入失敗 → 一串看似獨立的故障：SSH 被斷、編譯 / 安裝中途失敗、log 寫不進、VM 狀態檔存不下導致連不上 / 開不起來。短時間撞到「連線斷 + 任務失敗 + 服務怪」一串症狀時，`df -h` 要很早做，一個廉價檢查可能一次解釋全部。

**清錯地方的陷阱**：宿主 vs guest 是兩個獨立檔案系統。VM 的宿主磁碟滿 ≠ guest 內磁碟滿。SSH 進 guest `df` 看到有空間 ≠ 宿主有空間。兩側都 `df -h` 確認，清空間也要清對側。

## 快速路由

| 症狀                    | 檢查                            | 定位                           |
| ----------------------- | ------------------------------- | ------------------------------ |
| SSH TCP timeout         | `arp -a`（`incomplete`？）      | 網路沒起 / 機器沒跑 → 去主控台 |
| `Connection refused`    | `systemctl status sshd`         | 服務沒聽 → 起 sshd             |
| VM 開不起來、宿主側報錯 | 資源在不在 → 殘留行程 / `df -h` | 宿主狀態問題，別急著重裝       |
| 一串症狀同時發生        | `df -h`（宿主 + guest 兩側）    | 磁碟滿常是共同根因             |
