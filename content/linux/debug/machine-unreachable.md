---
title: "機器連不到或起不來"
date: 2026-07-02
description: "遠端機器突然 SSH 連不上、虛擬機開不了機、或懷疑磁碟滿引發連鎖故障時，從主機側與網路層的權威狀態往下定位是哪一環斷了"
weight: 3
tags: ["linux", "vm", "networking", "debugging"]
---

一台原本能連的機器突然連不上，或一台虛擬機根本開不起來，判讀的方向是「從你這端往那台機器，一層一層確認哪裡斷了」，而不是反覆重試同一個連線動作。連線失敗是最終症狀，真正斷掉的可能是網路、可能是那台機器的某個服務沒起來、可能是虛擬機的宿主側出問題、也可能是一個把上面全部拖下水的共同根因：磁碟滿。這篇從網路層與宿主側的權威狀態切入，把「連不上」拆成可定位的環節。

## 遠端機器突然連不上：先分清是哪一段斷

一台昨天還能 SSH 的機器今天連不上，第一步是確認「網路層通不通」，跟「SSH 服務在不在」分開。連線在 TCP 就 timeout（連 port 22 卡住沒回應），多半是網路層或機器沒在跑；連線有回應但被拒（`Connection refused`），是網路通、但那台機器上沒有服務在聽 port 22。

對虛擬機或同網段的機器，一個很有用的權威來源是**鄰居表**（IP 對 MAC 的對應）。要填起來需要對方在鏈路層有回應，所以它直接反映「對方在不在」。用 `ip neigh` 看目標 IP 的條目——優先用 `ip neigh` 而不是 `arp -a`，因為 `ip`（iproute2）在現代最小系統一定有，`arp`（net-tools）常常沒裝、跑了會 command not found 反而誤導。如果狀態是 `INCOMPLETE`（`arp -a` 顯示的是 `incomplete`），代表這個 IP 在鏈路層上根本沒有機器回應——不是 SSH 的問題，是那台機器的網路沒起來、或根本沒在跑。一個實際案例：一台虛擬機 SSH timeout，鄰居表顯示整個網段的 guest 位址全是 incomplete、只有閘道（宿主那側的橋接介面）是好的——這就定位到「宿主的橋沒問題，但橋的另一頭沒有 VM 在講話」，方向立刻從「調 SSH」轉到「去看 VM 的網路或開機狀態」。

定位到「機器在跑但網路沒起來」後，去那台機器的主控台（不是 SSH，SSH 正是連不上的那條路）確認——實體機是接鍵盤螢幕，VM 則是打開 hypervisor 的 guest console（UTM / virt-manager 的視窗，或序列 console），必要時用 `chvt` 切到別的 VT，這部分見[遠端連線與終端機問題](../ssh-and-terminal-troubleshooting/)：`ip -brief a` 看有沒有拿到 IP、`systemctl status <網路服務>`（`dhcpcd` / `systemd-networkd`）看網路服務起了沒，需要時 `sudo systemctl restart <網路服務>` 重拉。IP 回來、鄰居表的條目從 incomplete 變成有 MAC，就通了。

連不上的還有一類根因在**你這端的發起程式**，判讀關鍵是交叉驗證「同一個目標、不同的發起 process」：某個終端機 app 裡 SSH 回 `No route to host`，但同一時刻換一個 app（或系統內建終端機）對同一個 IP 的 ping / ssh 都通——網路層跟目標機器都沒事，是作業系統對那個 app 的網路權限。實測案例在 macOS：終端機 app 缺「本機網路」（Local Network）隱私權限時，對區網位址（包括本機上的 VM）的連線一律被擋、錯誤訊息卻長得跟路由故障一模一樣；系統設定裡把權限打開即解。錯誤訊息把你指向網路層、而交叉驗證能在一分鐘內把方向修正回發起端。

還有一個常見誤區是 IP 變了。SSH 的別名、金鑰、`known_hosts` 都綁在特定機器身分上；換機器 / 重裝 / DHCP 重配後 IP 或 host key 變了，用舊別名會連錯或被 host key 檢查擋。這條的判讀與修法（`ssh user@新IP` 直連、`ssh-keygen -R`）見 [外部連入與無 key 的 bootstrap 路徑](../../install/ssh-keyless-bootstrap/)。

## 網路通、但域名解析不了

有一種故障看起來像「網路壞了」，其實是 DNS 解析斷了：能連 IP、卻連不上任何用域名的東西——`ping 8.8.8.8` 通、但 `ping google.com`、`pacman -Sy`、`curl https://...` 全失敗。判讀要跟前面「網路沒起來」分開，因為網路層是通的，斷的是「域名 → IP」這一步。權威檢查：`ping <IP>` 通而 `ping <域名>` 不通、或 `getent hosts <域名>`（`resolvectl query <域名>` 若有 systemd-resolved）解不出位址，就定位到 DNS。常見成因是 `/etc/resolv.conf` 沒有可用的 nameserver（新裝或網路重設後沒填），或負責 DNS 的服務沒起來。修：確認 `/etc/resolv.conf` 有一行 `nameserver`（如 `nameserver 1.1.1.1`）、`systemctl status systemd-resolved`（若用它）。這一層在剛裝好的最小系統特別常撞到——`ip -brief a` 明明有 IP，`pacman` 或 bootstrap 卻抓不到套件，看起來像「網路好好的卻裝不了東西」，根因是 DNS 沒設。

## 虛擬機開不起來：分清 guest 內部還是宿主側

虛擬機開機失敗時，關鍵判斷是「錯誤來自 guest 內部（作業系統層）還是宿主側（虛擬化軟體 / QEMU 層）」。宿主側的錯誤訊息通常來自虛擬機軟體本身、在 guest 還沒開始開機前就跳出來，跟 guest 裡裝了什麼無關。

一個實例是 QEMU 報「找不到某個 ROM 檔」（例如 `efi-virtio.rom`）而拒絕啟動。第一反應可能是「檔案不見了要重裝」，但正確的第一步是**去確認那個檔在不在**——實際去虛擬機軟體的安裝目錄裡找（`find <安裝目錄> -name '<rom名>'`），會發現 ROM 檔明明就在。既然檔案在，「找不到」就不是缺檔，是 QEMU 執行時**在它預期的路徑下找不到**——成因隨宿主 OS 不同。**在 macOS + UTM 宿主上**，最常見的是 Gatekeeper app translocation：帶隔離屬性的 app 被搬到一個隨機唯讀路徑跑，讓 QEMU 解析資源的相對路徑失效，明明存在的檔案在那個執行路徑下就找不到。**在 Linux 宿主上**（沒有 translocation 這回事），同樣的「找不到 ROM」通常是缺對應套件（`ovmf` / `ipxe-roms` / `edk2-ovmf`）、libvirt XML 指的 ROM 路徑錯、或檔案權限不對——一樣先確認檔在哪、QEMU 是用哪個路徑去找。

另外兩個常見的「VM 起不來」故障也順手一起排除，它們不會特定產生「找不到 ROM」但常伴隨出現：上一次崩潰殘留的 helper 行程卡著（`pgrep -af 'qemu|<虛擬機軟體名>'` 找，沒清乾淨會佔住資源），以及宿主磁碟滿（`df -h`，啟動要寫暫存 / 狀態檔）。多數情況下，完全退出虛擬機軟體（連殘留 helper 一起清）+ 清出宿主磁碟空間 + 重新啟動，就恢復了。

宿主側的虛擬化軟體本身也可能被 guest 的行為弄崩。實測案例：guest 在 console 上大量捲動輸出（`pacman` 全量安裝的滾屏）時，UTM 的渲染層 segfault、整個 app 帶著跑到一半的 VM 一起消失。這類崩潰的訊號是宿主的 crash report 指向虛擬化軟體的顯示 / 渲染元件（而非 QEMU 核心），對應的預防是讓 console 安靜：長輸出導檔（`> /tmp/x.log 2>&1`）、日常操作走 SSH，guest console 留給開機救援這類非它不可的場合。

判讀通則：**虛擬機開不起來，先讀錯誤訊息判斷是 guest 還是宿主側；宿主側報「找不到某資源」而資源其實存在時，往「QEMU 是用哪個路徑找、那條路徑對不對」查（macOS 是 translocation、Linux 是缺套件 / 路徑 / 權限），再順手排除殘留行程與磁碟滿，而不是急著重裝。**

## 磁碟滿是連鎖故障的共同根因

很多看起來各自獨立的故障，共同根因是磁碟滿。磁碟一滿，寫入就會失敗，而系統裡太多東西依賴寫入：SSH session 可能因為寫不了而被斷、正在跑的編譯 / 安裝會中途失敗、log 寫不進去、虛擬機狀態檔存不下導致連不上或開不起來。所以當你在短時間內撞到「連線斷了 + 某個任務失敗 + 服務怪怪的」這種一串症狀時，`df -h` 應該是很早就要做的檢查——一個廉價的檢查就可能一次解釋掉全部。

這裡有一個容易搞錯的點：**清錯了地方**。宿主跟 guest 是兩個獨立的檔案系統；虛擬機的宿主磁碟滿，跟 guest 內部磁碟滿，是兩件事。如果你 SSH 進 guest 裡 `df` 看到還有空間就以為沒事，但真正滿的是宿主的磁碟，那問題不會解決。判讀時要分清這串故障是「哪一台機器的哪個檔案系統」滿了——在宿主上 `df -h` 看宿主、在 guest 裡 `df -h` 看 guest，兩邊都要確認。清空間也要清在對的那一側。

## 判讀路由

- SSH timeout（TCP 卡住）→ 網路層或機器沒跑，查 `ip neigh`（`INCOMPLETE` = 對方沒回應）→ 去主控台看 `ip -brief a` / 網路服務。
- `Connection refused` → 網路通、但沒有服務在聽 → 去機器上確認 sshd 起了沒；若是自己剛改過 `sshd_config` 後 sshd 起不來，`sshd -t` 一條指令印出壞在哪行（改 sshd_config 的紀律：先 `sshd -t` 驗證、通過再 restart，避免把自己鎖在外面）。
- 只有某個 app 連不到、其他 process 對同一目標都通 → 發起端 app 的網路權限（macOS 查「本機網路」隱私設定），跟網路層無關。
- 能 ping IP、不能用域名（`pacman` / `curl` 失敗）→ DNS 解析問題，查 `/etc/resolv.conf` 有沒有 nameserver、`systemd-resolved` 起了沒，不是網路層斷。
- 連錯 / host key 被擋 → IP 或身分變了，見 [外部連入與無 key 的 bootstrap 路徑](../../install/ssh-keyless-bootstrap/)。
- 虛擬機開不起來、宿主側報「找不到資源」但資源在 → 主因查路徑隔離，再排除殘留行程（`pgrep -af 'qemu\|...'`）/ 磁碟。
- 一串症狀同時發生 → 早點 `df -h`，宿主與 guest 兩側都查，磁碟滿常是共同根因。

連不上只是最終症狀，真正的定位靠網路表、服務狀態、資源用量這些權威來源一層層往回推——完整的判讀紀律見 [診斷心法](../diagnosis-read-authoritative-state/)。
