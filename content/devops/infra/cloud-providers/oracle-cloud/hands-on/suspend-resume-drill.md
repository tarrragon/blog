---
title: "Oracle Cloud 主機的暫停與恢復上線實測紀錄：暫停前的基準、收窄入口、停止主機、停止期間的計費與 Cloudflare 的回應、恢復上線的每一步與耗時，以及收尾時 DNS 紀錄與主機的刪除順序"
date: 2026-10-27
description: "要讓 Oracle Cloud 上一台放在 Cloudflare 後面的主機停機一段時間再恢復上線、想知道停止之後公開 IP 留不留、停止期間 A1 與開機磁碟怎麼計費、Cloudflare 回什麼錯誤、恢復時每一步要多久，或服務要收掉時 DNS 紀錄與主機的刪除順序時，查實際跑過的指令、輸出與量到的時間"
weight: 7
tags: ["infra", "cloud-providers", "oracle-cloud", "oci", "cloudflare", "maintenance", "hands-on"]
---

> **事件說明**：2026-10-27（本篇的時刻都是 UTC），在 Oracle Cloud 的 `ap-batam-1` 區域，從一台 macOS 開發機用 OCI CLI 操作。tenancy（Oracle Cloud 的帳號層級）是付費帳戶。主機是 A1 機型（`VM.Standard.A1.Flex`，1 OCPU、6 GB），Oracle Linux 10.2，放在公開子網路、有臨時公開 IP（ephemeral public IP）。網卡掛著一個 NSG（network security group：套在個別網卡上的一組防火牆規則，跟 AWS 的 [Security Group](/devops/infra/knowledge-cards/security-group/) 是同一類），只放行 Cloudflare IPv4 位址段連 80 與 443；子網路的 security list（套在整個子網路上的防火牆規則）只放行管理者的 IP 連 22。主機上跑 nginx（80 與 443，443 用自簽憑證）與一個接收監控事件的 systemd 服務。網域的根網域與 `www` 兩筆 A 紀錄經過 Cloudflare 代理（Proxied：訪客連到 Cloudflare，再由 Cloudflare 回源到這台主機，見 [CDN](/devops/infra/knowledge-cards/cdn/)）指到這台主機，SSL/TLS 模式實際套用的是完整（Full）。這台主機與它的網路，是在 [Cloudflare 回源的實測紀錄：Oracle Cloud NSG 只放行 Cloudflare 位址與規則數上限、回源的來源位址、Authenticated Origin Pulls、Worker 偽造 CF-Connecting-IP 與 Tunnel 的出站連接埠](/devops/infra/03-network-foundation/hands-on/cloudflare-origin-pull-walkthrough/)（下文稱「回源那篇」）的實測收掉之後，照那篇的步驟另建的，DNS 紀錄改成根網域與 `www`。當時在做的操作是：這台實驗主機要收掉之前，先照 [服務暫停與恢復上線：只停服務、停止主機、終止主機到全部刪除各自保留的資源，暫停期間仍計費與仍被指向的資源，恢復前要查的漂移與恢復的順序](/devops/operations/09-host-lifecycle/suspend-and-resume-service/)（下文稱「暫停那篇」）的「停止主機」那一種範圍演練一次停機與恢復上線。

這篇記錄在 Oracle Cloud 上把一台放在 Cloudflare 後面的主機停機、再恢復上線的每一步，以及演練完把它收掉的順序。各節依序是：

- 暫停前記下的基準：接聽的程式、服務的狀態、待裝的安全更新、憑證效期、公開 IP 與 A1 的用量，以及記這些值的指令。
- 收窄入口：把 NSG 從主機的網卡拿掉，以及 Cloudflare 在這之後回的錯誤與等待時間。
- 停止主機：`SOFTSTOP` 與 `STOP` 的差別、停止花的時間、停止之後公開 IP 的去留，以及停止中的主機是否仍佔 A1 與區塊儲存的用量。
- 停止期間的計費：用 usage API 逐小時讀帳務明細，停止的那一小時 A1 與開機磁碟各記了什麼。
- 恢復上線：啟動與 SSH 連得上的時間、跟基準比對的漂移（暫停期間改變了的狀態）、裝安全更新與重開機的判斷、只對 loopback 的冒煙測試（[smoke test](/testing/knowledge-cards/smoke-test/)：只確認服務起得來、首頁有回應的最小檢查）、重新掛回 NSG 之後從外面的驗證。
- 收尾：服務要收掉時，DNS 紀錄、主機與網路資源的刪除順序、這個順序的理由與實際耗時。

每一步為什麼排在這個位置（入口要在停止之前收窄、更新要在開放入口之前裝），推導在暫停那篇；這裡寫的是在 Oracle Cloud 與 Cloudflare 上跑出來的結果。本篇的 OCID、IP 與網域一律是佔位值，各自的查法寫在第一次用到它的那條指令旁邊。

## 暫停前記下的基準：接聽的程式、服務、待裝的更新、憑證效期與公開 IP

恢復的時候要拿一份暫停當下的值來比，才知道暫停期間變了什麼（暫停那篇〈恢復上線前要重新確認的漂移〉），所以基準在入口收窄之前、主機還在跑的時候記。下面這一條從開發機經 SSH 在主機上執行，輸出存成檔案留著比對：

```bash
# <登入設定> 是連到這台主機的 ssh 參數（-i 私鑰、使用者@公開 IP），這次是 security list 只放行管理者 IP 的直連
ssh <登入設定> '
  sudo ss -lntup                                  # 接聽的程式與連接埠
  systemctl is-enabled nginx monitor-collector     # 開機時會不會自己起來
  systemctl is-active nginx monitor-collector
  curl -s -o /dev/null -w "loopback http %{http_code}\n" http://127.0.0.1/
  curl -sk -o /dev/null -w "loopback https %{http_code}\n" https://127.0.0.1/
  echo sec=$(sudo dnf -q check-update --security | grep -c .)   # 待裝的安全更新（行數）
  sudo needs-restarting -r                         # 現在需不需要重開機
  uname -r
' > pre-suspend.log
```

`monitor-collector` 是這台主機上那個接收監控事件的服務名稱，換成自己主機上要確認的服務。`dnf check-update --security` 每個待裝的套件印一行，`grep -c .` 數的是非空的行數；這次是 18 行，恢復時實際裝了 18 個套件，兩個數字相同。`needs-restarting` 這個指令在 Oracle Linux 10.2 由 `yum-utils` 套件提供（`oraclelinux:10` 容器裡 `rpm -qf $(command -v needs-restarting)` 實跑），Debian 與 Ubuntu 上對應的是 `needrestart -b` 與 `/var/run/reboot-required`（[長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/devops/operations/09-host-lifecycle/long-running-host-maintenance/)〈會老化的軟體：各條更新管道與更新後的重開機〉）。

這次記到的值：nginx 聽 80 與 443、sshd 聽 22、監控事件的服務聽 8765，兩個服務都是 `enabled` 與 `active`；loopback 的 HTTP 與 HTTPS 都回 200；待裝的安全更新 18 行；`needs-restarting -r` 印 `Reboot should not be necessary.`；核心是 `6.12.0-207.111.5.6.el10uek.aarch64`。

憑證效期照 `nginx -T` 列出的 `ssl_certificate` 路徑讀。這台主機在建好之後換過網站，建立腳本裡寫的憑證路徑已經不在，照那個路徑讀會回 `No such file or directory`；`nginx -T` 印的是 nginx 實際載入的設定，所以讀到的是現在用的那一張：

```bash
# 列出 nginx 實際載入的憑證路徑；開頭是 # 的是註解掉的範例，這條 grep 只取沒有註解的那一行
ssh <登入設定> 'sudo nginx -T 2>/dev/null | grep -E "^\s*ssl_certificate\s"'
ssh <登入設定> 'sudo openssl x509 -in <上一條印出的路徑> -noout -enddate'
```

這次讀到 `notAfter` 在 2036 年，是建網站時簽的十年自簽憑證；暫停只有 2 小時，恢復時沒有再讀。暫停期長到可能跨過效期的，恢復時要再讀一次。

公開 IP、私有 IP 與 A1 的用量在開發機上用 CLI 讀。`<tenancy 的 OCID>` 是 `~/.oci/config` 裡 `tenancy=` 那一行的值；`<compartment 的 OCID>` 是主機所在的 compartment（Oracle Cloud 裡把資源分組的單位），用 `oci iam compartment list -c <tenancy 的 OCID> --compartment-id-in-subtree true --all --query 'data[].{name:name,id:id}' --output table` 列出名稱與 OCID，主機建在最上層時就是 tenancy 的 OCID；`<主機的 OCID>` 用 `oci compute instance list -c <compartment 的 OCID> --query 'data[].{name:"display-name",id:id}' --output table` 列出每台主機的名稱與 OCID 再挑；`<可用網域>`（availability domain，區域裡的一個資料中心，跨業者的概念見 [Availability Zone](/devops/infra/knowledge-cards/availability-zone/)）用 `oci compute instance get --instance-id <主機的 OCID> --query 'data."availability-domain"' --raw-output` 查：

```bash
oci compute instance list-vnics --instance-id <主機的 OCID> \
  --query 'data[0].{pub:"public-ip",priv:"private-ip",vnic:id}' --output table
# A1 的核心數用量；記憶體把 limit 名稱換成 standard-a1-memory-count
oci limits resource-availability get -c <tenancy 的 OCID> --service-name compute \
  --limit-name standard-a1-core-count --availability-domain <可用網域> --query 'data.used' --raw-output
```

這次 tenancy 裡有三台各 1 OCPU 的 A1，核心數的 `used` 回 3；記憶體與免費區塊儲存的用量這次在暫停前沒有讀（下面〈停止主機：SOFTSTOP、耗時、公開 IP 的去留與停止中的用量〉在停止中讀了）。暫停前沒有跑 [只讀檢查腳本 host-check.py 的原始碼與逐段說明：選項的切分與各工具的白名單規則、清單的載入與驗證、指令的執行、各項檢查、路徑與時間的量測、結果檔與命令列，以及這一版的已知限制](/devops/operations/09-host-lifecycle/hands-on/host-check-script-source/) 的檢查：這台主機沒有寫過主機清單，上面那幾條指令是手動挑的，涵蓋不到清單會檢查的累積資料與到期設定。

## 收窄入口：把 NSG 從網卡拿掉，以及 Cloudflare 回的 522

收窄入口是暫停那篇〈暫停時先收窄的入口〉的用詞，指收回對外的放行、只留管理者的連線。主機停止期間不回應任何連線，入口開不開沒有差別；入口要收窄，是為了下一次啟動的那一刻：主機一開機，enabled 的服務自己起來、防火牆照舊放行，入口還開著的話，主機在裝好更新之前就在接受外部連線。所以收窄只要在下一次啟動之前做完；暫停那篇把它排在暫停的當下，是因為恢復的人可能隔了很久、或換了一個人，到時不一定記得先收窄。Oracle Cloud 對一張網卡的放行是它的 NSG 與子網路 security list 兩處規則的聯集（[網路：subnet、私有 IP、公開 IP 與防火牆規則](/devops/infra/cloud-providers/vm-options/networking/)〈防火牆規則的位置與合併方式〉），所以先確認 80 與 443 在哪一處放行：這台主機的 security list 只放行 22，對外的 80 與 443 只靠那個 NSG，收窄入口的動作就是把 NSG 從網卡拿掉，規則本身留在 NSG 裡，恢復時再掛回去。security list 也放行 80 與 443 的主機，拿掉 NSG 之後入口照樣開著，下面那條 `curl` 會回 200 而不是 522，要另外收回 security list 那幾條（它管的是整個子網路，同一個子網路的其他主機會一起受影響）。拿掉之前先把網卡現在掛著的 NSG 清單存下來，恢復時要用：

```bash
# <VNIC 的 OCID> 是〈暫停前記下的基準：接聽的程式、服務、待裝的更新、憑證效期與公開 IP〉那條 list-vnics 印的 vnic 欄
oci network vnic get --vnic-id <VNIC 的 OCID> --query 'data."nsg-ids"' > nsg-ids.json
oci network vnic update --vnic-id <VNIC 的 OCID> --nsg-ids '[]' --force
```

`--nsg-ids` 是整份替換（[VNIC](/devops/infra/knowledge-cards/vnic/) 卡寫了這個欄位的整份替換）。網卡上掛著好幾個 NSG、只要拿掉其中一個時，`'[]'` 要換成去掉那一個之後的清單，否則別的 NSG 會一起被拿掉；這次 `nsg-ids.json` 裡只有一個。沒有存下來的話，恢復時用 `oci network nsg list -c <compartment 的 OCID> --query 'data[].{name:"display-name",id:id}' --output table` 列出名稱與 OCID 查回來。網卡上另有一個放行監控探測的 NSG 時，探測在暫停期間不論拿不拿掉它都會失敗，探測要在監控那一端先靜音或停用，恢復時等外部驗證通過之後再啟用（暫停那篇〈恢復的順序：依元件之間的依賴排列〉的流量導回那一段）。04:59:11 送出 `update`，1 秒後回應，`nsg-ids` 變成 `[]`。之後每 40 秒從開發機經 Cloudflare 請求一次首頁：

```bash
# <網域> 換成經過 Cloudflare 代理的網域；印回應碼與總耗時
curl -s -o /dev/null -w '%{http_code} %{time_total}\n' --max-time 40 https://<網域>/
```

三次都回 `522`，耗時 20.3 到 20.7 秒。522 是 Cloudflare 連到源站逾時的錯誤碼：NSG 拿掉之後，security list 只放行管理者 IP 的 22，Cloudflare 送到 443 的封包沒有規則放行，被丟掉而沒有回應，所以 Cloudflare 等到逾時（源站拒絕連線時的 521 與逾時的 522 怎麼分，見暫停那篇〈暫停期間仍指向這台主機的外部設定〉）。約 20 秒是 Cloudflare 那一端等 TCP 連線的時間，源站這一端決定不了；方案或設定會不會改變它，這次沒有查。訪客在這段時間看到的是 Cloudflare 的 522 錯誤頁，每次要等約 20 秒才出現；DNS 紀錄不經 CDN、直接指公開 IP 時，訪客看到的是瀏覽器自己的連線逾時（從機制推論，這次沒有這種紀錄）。放行 22 的規則在 security list，不在這個 NSG，所以收窄之後管理者照樣連得進主機。

這一步的其他做法與換到的結果：

- **刪掉 NSG 裡 80 與 443 的規則**：效果相同，恢復時要把整份 Cloudflare 位址段重新加回去。這個 NSG 有 30 條規則，回源那篇量到每次 API 呼叫最多加 25 條，所以要分兩次加；拿掉整個 NSG 時規則原封不動，恢復只要一條指令。
- **改 security list**：這台主機的 80 與 443 本來就不在 security list 裡，改它收窄不了這兩個連接埠。
- **網卡一定要掛至少一個防火牆群組的業者**：AWS 的網卡至少要有一個 security group，拿成零個的做法換不過去，改成掛一個沒有放行規則的空群組（依業者的規則推論，沒有實跑）。
- **只在 Cloudflare 那一層擋**：zone 上加一條 Worker route 回維護頁，或一條 WAF 自訂規則直接擋，訪客馬上拿到回應，不必等 20 秒的 522，DNS 也不必改。它只在 Cloudflare 這一層生效：NSG 放行的是整份 Cloudflare 位址段，別人在自己的 Cloudflare 帳號裡把一個網域指到這個 IP，回源照樣進得來，所以只能跟拿掉 NSG 並用（從回源那篇量到的 Worker 穿過 NSG 推論，這次沒有做）。
- **改用 Cloudflare Tunnel**：源站完全不開入站，暫停時停掉 `cloudflared` 就收窄了，恢復時也不必比對位址段（回源那篇〈Cloudflare Tunnel：源站不開入站，以及出站要放行的連接埠〉；這台主機沒有用 Tunnel）。
- **DNS 紀錄改指到維護頁**：訪客看到的是說明頁而不是 522，代價是要另外準備一個維護頁（Cloudflare Workers 或另一台主機）、恢復時再改回來（暫停那篇〈暫停期間仍指向這台主機的外部設定〉）。這次沒有做，訪客看到的是 522。
- **不收窄**：停止期間沒有差別，差別在恢復時開機的那一刻，見下面〈恢復上線：啟動、漂移比對、安全更新、冒煙測試與重新開放入口〉的對外入口開放那一段。

## 停止主機：SOFTSTOP、耗時、公開 IP 的去留與停止中的用量

停止之前先確認業者停止主機時收不收回公開 IP：Oracle Cloud 的臨時公開 IP 停止時留著（下面實測），DNS 紀錄可以不動；停止時就收回臨時公開 IP 的業者（暫停那篇寫的 AWS 沒有 Elastic IP 的主機），DNS 紀錄要在送出停止之前改指維護頁或刪除，否則停止那一刻舊 IP 就還給業者，之後被分給別人時就是懸空 DNS（dangling DNS：DNS 紀錄指著已經還給業者、可能分給別人的 IP）。經過 Cloudflare 代理、SSL/TLS 模式是完整（Full，不驗源站憑證）時，Cloudflare 會把訪客的請求送到那個 IP 的下一任主人。

主機上有寫入資料的服務時，先經 SSH 用 `systemctl stop` 停掉它、確認它已經結束，再停止主機；下面的 `SOFTSTOP` 最多等作業系統關機 15 分鐘，服務停不下來時照樣被切斷電源（這次沒有先停服務，69 秒就停好了）。從 API 停止主機。暫停那篇〈暫停期間仍在計費的資源〉引的 Oracle Cloud 官方文件寫明，在作業系統裡下 `shutdown` 關機不會停止計費，要從主控台或 API 停止；這樣關機之後主控台上顯示的狀態，這次沒有查。

```bash
oci compute instance action --instance-id <主機的 OCID> --action SOFTSTOP \
  --wait-for-state STOPPED --max-wait-seconds 1200 --query 'data."lifecycle-state"' --raw-output
```

`--action` 收 `STOP` 與 `SOFTSTOP` 兩種停止。依 `oci compute instance action --help`，`STOP` 直接切斷電源（Powers off the instance）；`SOFTSTOP` 先送關機指令給作業系統，等作業系統關機最多 15 分鐘，之後才切斷電源，所以作業系統上的程式有機會正常結束。這台主機上有寫入 SQLite 的服務，選 `SOFTSTOP`；`STOP` 這次沒有實跑，依說明，它跳過作業系統的關機，正在寫入的資料可能沒有寫完。`--wait-for-state STOPPED` 讓 CLI 等到主機的狀態變成 `STOPPED` 才回傳，`instance action` 收的是主機本身的狀態，跟 `instance terminate` 收 work request（Oracle Cloud 記錄一次非同步操作進度的物件）的狀態不同，下面〈收尾：DNS 紀錄、主機與網路資源的刪除順序〉會用到這個差別。上面那條的 `--max-wait-seconds` 寫 1200，比這次實跑時寫的 900 大：`SOFTSTOP` 最多等作業系統關機 15 分鐘（900 秒），作業系統拖滿 15 分鐘才關機時，等待上限也是 900 秒的話，CLI 會先以逾時結束，主機卻還在停（從這兩個 900 推論）。這次 69 秒就停好了，沒有碰到這個上限。

05:01:31 送出，05:02:40 回 `STOPPED`，共 69 秒。這個時間取決於主機上的服務停下來要多久，上限是上面那 15 分鐘。停止之後讀到的狀態：

| 項目                    | 讀法                                                                                                                                                                                                                                                    | 結果                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 公開 IP                 | `list-vnics` 的 `public-ip`，與 `oci network vnic get` 的 `public-ip`                                                                                                                                                                                   | 跟停止前相同，VNIC 的狀態是 `AVAILABLE`                                          |
| 經 Cloudflare 請求首頁  | 〈收窄入口：把 NSG 從網卡拿掉，以及 Cloudflare 回的 522〉的 `curl`                                                                                                                                                                                      | `522`，20.4 秒                                                                   |
| SSH                     | 同一組登入設定                                                                                                                                                                                                                                          | `Operation timed out`                                                            |
| A1 的核心數與記憶體用量 | 〈暫停前記下的基準：接聽的程式、服務、待裝的更新、憑證效期與公開 IP〉的 `limits resource-availability get`，記憶體把 limit 名稱換成 `standard-a1-memory-count`                                                                                          | 3 與 18；核心數跟停止前相同，記憶體 18 等於三台各 6 GB：停止中的主機仍算在用量裡 |
| 免費區塊儲存的用量      | `oci limits resource-availability get -c <tenancy 的 OCID> --service-name block-storage --limit-name total-free-storage-gb-regional --query 'data.used' --raw-output`（區域層的這一條不帶 `--availability-domain`）                                     | 141，等於三台的開機磁碟各 47                                                     |
| 開機磁碟                | `oci bv boot-volume get --boot-volume-id <開機磁碟的 OCID>`；OCID 用 `oci compute boot-volume-attachment list -c <compartment 的 OCID> --availability-domain <可用網域> --instance-id <主機的 OCID> --query 'data[0]."boot-volume-id"' --raw-output` 查 | 47 GB、`AVAILABLE`                                                               |

公開 IP 留在主機上，跟暫停那篇引的 Oracle Cloud 文件一致：停止時臨時公開 IP 還在，終止時才刪除。所以這台主機停止期間，DNS 紀錄指著的仍是自己的 IP，訪客看到的是 522，不會連到別人的主機；本節開頭那段寫的前提（業者停止時不收回 IP）在這裡成立。

停止中的主機仍算在 A1 的 limits 用量裡，也就是決定還能再建多少 A1 的那個用量，跟計費是兩回事（計費見下面〈停止期間的計費：usage API 逐小時的明細〉）。用量已經到上限時，停機期間這份 A1 的額度不能拿去建另一台主機（上限與剩餘量用同一條指令把 `--query` 換成 `'data.{used:used,available:available}'` 讀），要讓出額度得終止主機，也就是暫停那篇表裡「終止主機、保留磁碟與網路設定」那一種範圍：主機刪掉，磁碟與網路設定留著。limits 用量也不等於實體的主機容量：停止中的 A1 再啟動時會不會遇到容量不足（A1 建立時常見的 `Out of host capacity`），Oracle 停止與啟動主機的[說明頁](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/restartinginstance.htm)（2026-10-27 讀）沒有寫，這次 2 小時後的啟動沒有遇到。暫停期長、而那一區的 A1 常常容量不足時，停止之前先備份開機磁碟，啟動失敗時才有從備份換到別的可用網域或機型重建的路（沒有實跑）。

## 停止期間的計費：usage API 逐小時的明細

停止期間 A1 是否計費，用 usage API 依 SKU（帳務明細上的計費品項）與資源逐小時讀。逐小時的明細大約落後 2 小時，所以這一段在恢復之後才查得到；`usage-api` 各參數的讀法寫在 [Oracle Cloud 私有子網路 Ubuntu 主機的實測紀錄：套件來源的出站（NAT gateway、路由與 NSG）、序列主控台的連線，以及被回收之後的重建](/devops/infra/cloud-providers/oracle-cloud/hands-on/private-ubuntu-egress-console-rebuild/)〈費用與額度：A1、開機磁碟與區塊儲存額度、出站流量與 NAT gateway〉：

```bash
oci usage-api usage-summary request-summarized-usages --tenant-id <tenancy 的 OCID> \
  --time-usage-started 2026-10-27T04:00:00Z --time-usage-ended 2026-10-27T09:00:00Z \
  --granularity HOURLY --query-type USAGE --group-by '["skuName","skuPartNumber","resourceId"]' \
  --query 'data.items[].{hour:"time-usage-started",sku:"sku-name",res:"resource-id",qty:"computed-quantity"}' \
  --output table
```

起訖換成要看的時段（UTC 的整點）。這台主機與它的開機磁碟在各小時記到的項目（`res` 欄對回主機與開機磁碟的 OCID）：

| 小時（UTC） | 主機的狀態                       | `Standard - A1`（OCPU 小時） | `Standard - A1 - Memory`（GB 小時） | 開機磁碟的 `Block Volume - Free` |
| ----------- | -------------------------------- | ---------------------------- | ----------------------------------- | -------------------------------- |
| 04 時       | 整小時 `RUNNING`                 | 1.0                          | 6.0                                 | 0.0632                           |
| 05 時       | 05:01:31 開始停止，05:02:40 停止 | 0.0258                       | 0.1558                              | 0.0632                           |
| 06 時       | 整小時 `STOPPED`                 | 沒有這一項                   | 沒有這一項                          | 0.0632                           |

05 時的 0.0258 OCPU 小時約 93 秒，換算回去是 05:01:33，跟送出 `SOFTSTOP` 的 05:01:31 差 2 秒，所以這一次 A1 的計費大約停在送出停止動作的那一刻，比主機變成 `STOPPED` 的 05:02:40 早約 1 分鐘（從這一小時的數字推算，只量了這一次）。06 時整小時停止，明細裡沒有這台主機的 A1 項目。開機磁碟每小時照樣記 0.0632，等於 47 GB 除以 744 小時（31 天的小時數；10 月正好 31 天，Oracle 換算時是否固定用 744 沒有查），記在 `Block Volume - Free`，金額 0：磁碟在主機停止時繼續存在、繼續佔免費額度。這台主機的 A1 在付費 tenancy 每月的免費量裡，金額是 0，停止省下的是那幾個小時從每月免費量裡扣掉的 OCPU 與記憶體小時數；A1 用量超過免費量的帳戶，停止那幾個小時的費用就省下來了（從這三個小時的明細推論，沒有在超過免費量的帳戶上量）。這是 A1 這類標準機型的結果；Dense I/O、HPC 與多數 GPU 機型停止期間照樣計費，見 [機型與映像檔：CPU 架構、核心與記憶體、計費模式與作業系統](/devops/infra/cloud-providers/vm-options/shape-and-image/)〈停止主機時的計費〉。

## 恢復上線：啟動、漂移比對、安全更新、冒煙測試與重新開放入口

主機停了 1 小時 59 分鐘之後恢復。恢復分成主機與網路就緒、主機內部就緒、對外入口開放三段，每一段的產出是下一段的前提（暫停那篇〈恢復的順序：依元件之間的依賴排列〉）；DNS 紀錄這次一直指著同一個 IP（公開 IP 停止前後沒有變），暫停那篇「流量導回」那一段（把 DNS 紀錄改回這台主機、經 CDN 從外面驗證）只剩經 CDN 的外部驗證，併在對外入口開放之後做。

**主機與網路就緒**：

```bash
oci compute instance action --instance-id <主機的 OCID> --action START \
  --wait-for-state RUNNING --max-wait-seconds 900 --query 'data."lifecycle-state"' --raw-output
# 每 5 秒試一次 SSH，連得上就停
for i in $(seq 1 30); do ssh <登入設定> true && break; sleep 5; done
oci network vnic get --vnic-id <VNIC 的 OCID> --query 'data.{pub:"public-ip",nsg:"nsg-ids"}'
```

07:01:28 送出 `START`，07:02:03 回 `RUNNING`（35 秒），SSH 在 07:02:21 第 4 次嘗試時連上（`RUNNING` 之後 18 秒），從送出到連得上共 53 秒。這幾個時間依機型、映像檔與開機時起來的服務而變（這次是 A1、Oracle Linux 10.2、兩個 enabled 的服務），上面的 `--wait-for-state` 與 SSH 迴圈都是依回應自己等，不依賴這個值。SSH 迴圈這次沒有帶 `-o ConnectTimeout`，主機還沒起來時一次嘗試可能等到連線逾時才換下一次；加上 `-o ConnectTimeout=5`，每次嘗試最多等 5 秒（沒有實跑）。迴圈跑完 30 次都沒連上時，它不會報錯，後面的指令照樣接著跑；這時除了主機還沒起來，也要比對 security list 放行的來源跟自己現在的對外 IP，暫停期間管理者的 IP 換了也是同樣的逾時。`vnic get` 讀到的公開 IP 跟停止前相同，`nsg-ids` 還是 `[]`；經 Cloudflare 請求首頁照樣回 522（20.2 秒），入口還收窄著。

**主機內部就緒**：先跟基準比，再裝更新。

| 項目                   | 暫停前                                                                      | 恢復後（裝更新之前）                                             |
| ---------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| nginx 與監控事件的服務 | `enabled`、`active`                                                         | `active`：enabled 的服務開機時自己起來了                         |
| 接聽的 TCP 連接埠      | 22、80、443、8765，共 7 行（22、80、443 的 IPv4 與 IPv6 各一行，8765 一行） | 只數了這四個連接埠的接聽行數，回 7，行數相同；沒有逐一列出連接埠 |
| 待裝的安全更新         | 18 行                                                                       | 18 行                                                            |
| 核心                   | `6.12.0-207.111.5.6.el10uek`                                                | 相同                                                             |
| 公開 IP                | 停止前的值                                                                  | 相同                                                             |

這張表是手動逐項比的，接聽的連接埠只數了行數，行數相同而連接埠換了的情形看不出來。比較完整的做法是恢復時重跑暫停前那一整段指令、輸出存成 `post-resume.log`，再用 `diff pre-suspend.log post-resume.log` 看差異（這次沒有這樣做）。暫停期間只有 2 小時，待裝的安全更新數量沒有變。暫停幾週時這個數量會變多，裝更新的時間跟著變長（推論，這次沒有量長的暫停）。接著裝安全更新、判斷要不要重開機：

```bash
ssh <登入設定> 'sudo dnf -y -q upgrade --security; sudo needs-restarting -r'
ssh <登入設定> 'echo sec=$(sudo dnf -q check-update --security | grep -c .)'
```

07:03:12 開始、07:03:40 結束（28 秒），裝了 18 個套件：`bind` 的三個套件、`gcc-toolset-15` 的四個、`kernel-headers`、`kernel-tools`、`kernel-tools-libs`、`libbrotli`、`nodejs` 的五個、`perf` 與 `python3-perf`。`kernel-tools` 這幾個是核心相關的工具，核心本身（`kernel-uek-core`）不在這一批裡，`needs-restarting -r` 印 `No core libraries or services have been updated since boot-up.` 與 `Reboot should not be necessary.`，所以沒有重開機。裝完之後待裝的安全更新是 0。核心在一批更新裡的時候，`needs-restarting -r` 會列出要重開機的原因、以 1 結束：2026-10-26 在另一台 Oracle Linux 10.2 主機上裝了 `kernel-uek-core` 的更新之後，它印 `Core libraries or services have been updated since boot-up:`、列出 `kernel-uek-core`，以 1 結束（實跑）。遇到這種情形，重開機（`sudo systemctl reboot`）排在開放入口之前，重開之後重跑上面的 SSH 迴圈與下面的 loopback 冒煙測試。

`-r` 只判斷要不要重開機；更新了服務已經載入的共用函式庫時（常見的是 `openssl-libs`；這一批裡的共用函式庫是 `libbrotli`，有沒有被 nginx 或那個服務載入這次沒有查），已經在跑的程序在重新啟動之前用的仍是記憶體裡的舊版。`needs-restarting -s` 列出受影響的 systemd 服務，重啟它們之後再開放入口（`-s` 在 `oraclelinux:10` 容器的 `--help` 列得出來，這次沒有在主機上跑）。

`--security` 只認套件來源裡帶 updateinfo（安全公告）中繼資料的更新，nginx 官方套件來源這類第三方來源的安全修補不會算進去（依 dnf 的說明推論，這台主機只用 Oracle Linux 的套件來源）。

這一步的其他做法：`dnf upgrade`（不加 `--security`）把非安全性的更新一起裝上，裝的套件更多、時間更長，換到的是恢復之後不必另外安排一般更新；`dnf-automatic` 這類自動更新在主機停止期間不會執行，恢復時照樣要補裝。另一種做法是用最新的映像檔重建主機：省下裝更新與可能的重開機，代價是網路、nginx 與服務都要照回源那篇重建，臨時公開 IP 會換、DNS 紀錄要改（暫停那篇〈恢復的順序：依元件之間的依賴排列〉）。這次只比較了要裝的範圍，三種另外的做法都沒有實跑。

只對 loopback 的冒煙測試：`curl http://127.0.0.1/` 與 `curl -k https://127.0.0.1/` 都回 200。監控事件的服務對 `/` 回 404，它的根路徑本來就沒有內容；要驗證它，要打它實際接收事件的路徑，這次沒有做。

**對外入口開放**：NSG 裡的規則是暫停前 Cloudflare 公布的 IPv4 位址段。暫停期間 Cloudflare 新增了位址段的話，從新位址段回源的請求沒有規則放行、會回 522，而且只有部分請求失敗。反方向也要看：Cloudflare 撤回的位址段，舊規則會繼續放行，而那些位址已經不屬於 Cloudflare。所以掛回之前，先把 Cloudflare 公布的 IPv4 清單與 NSG 規則的來源位址比對，兩個方向的差異都處理，有新增的照回源那篇的寫法補進規則（每次 API 呼叫最多加 25 條）。這次暫停 2 小時，沒有做這一步比對；下面兩條印出兩邊的清單（沒有實跑）：

```bash
curl -s https://www.cloudflare.com/ips-v4 | sort > cf-v4.txt
# <放行 Cloudflare 的 NSG 的 OCID> 是 nsg-ids.json 裡那一個；80 與 443 各一條，所以每個來源出現兩次，sort -u 去重
oci network nsg rules list --nsg-id <放行 Cloudflare 的 NSG 的 OCID> --all \
  --query 'data[?direction==`INGRESS`].source' --raw-output | tr -d '[]", ' | grep . | sort -u > nsg-v4.txt
diff cf-v4.txt nsg-v4.txt    # 「<」是 Cloudflare 新增、NSG 還沒有的；「>」是 NSG 有、Cloudflare 已經撤回的
```

接著把存下來的 NSG 清單掛回網卡，再從外面驗證：

```bash
# <NSG 的 OCID> 是 nsg-ids.json 裡的值；原本掛著好幾個時，清單要寫回 nsg-ids.json 裡的全部，否則其餘的不會掛回去
# （OCI CLI 的清單參數也收 --nsg-ids file://nsg-ids.json，直接讀存下來的檔，這種寫法沒有實跑）
oci network vnic update --vnic-id <VNIC 的 OCID> --nsg-ids '["<NSG 的 OCID>"]' --force
# <公開 IP> 是〈暫停前記下的基準：接聽的程式、服務、待裝的更新、憑證效期與公開 IP〉那條 list-vnics 印的 pub 欄
curl -s -o /dev/null -w 'direct %{http_code}\n' --max-time 8 http://<公開 IP>/      # 繞過 Cloudflare 直連
curl -s -o /dev/null -w 'cf %{http_code} %{time_total}\n' --max-time 40 https://<網域>/
```

07:04:05 掛回，07:04:15 直連回 `000`（8 秒逾時）：NSG 只放行 Cloudflare 的位址段，開發機的 IP 進不來。07:04:16 經 Cloudflare 回 `200`（1.19 秒），`www` 的根路徑 07:04:24 也回 200（07:04:18 對 `www` 打的是網站改版前的舊路徑，回 404，跟入口無關）。第一次經 Cloudflare 的請求是在掛回之後約 10 秒才送出的（前面先跑了逾時 8 秒的直連），所以量到的只是 NSG 在 10 秒之內生效，生效最快要多久沒有量到。

入口要等更新裝完才開，是因為這台主機的服務在開機的那一刻就起來了（上表的 `active`）。恢復時沒有收窄入口的話，從 07:02:03 主機 `RUNNING` 到 07:03:40 更新裝完的 97 秒裡，主機上還有 18 個安全更新沒裝，nginx 與監控事件的服務已經在接受 Cloudflare 送來的連線。這一批的 18 個套件裡沒有 nginx 與那個服務本身的套件；它們載入的共用函式庫有沒有在這一批裡、要不要重啟，這次沒有用 `needs-restarting -s` 查。換一批更新、裡面有接聽的程式或它用的函式庫時，那段時間裡對外接聽的就是缺了修補的程式。暫停期越長、要裝的更新越多、要重開機時，這段時間越長。

從送出 `START` 到經 Cloudflare 回 200，整個恢復花了 2 分 48 秒；其中裝更新 28 秒，其餘是等主機啟動與手動逐步確認的時間。

## 收尾：DNS 紀錄、主機與網路資源的刪除順序

演練完，這台主機與它的網路要收掉。順序是先刪 DNS 紀錄、再終止主機、最後刪網路資源。先刪 DNS 紀錄，是因為終止主機時臨時公開 IP 會還給 Oracle Cloud，DNS 紀錄還指著它就是上面〈停止主機：SOFTSTOP、耗時、公開 IP 的去留與停止中的用量〉寫的懸空 DNS（完整的後果見暫停那篇〈暫停期間仍指向這台主機的外部設定〉）。網路資源排在主機之後，是因為它們被主機的網卡引用著，主機還在時刪不掉。指著這個 IP 的不只 DNS 紀錄：外部監控的探測、別處的 IP 白名單、CDN 的其他回源設定也要在終止之前一起移除（暫停那篇〈暫停期間仍指向這台主機的外部設定〉）；這台主機只有 DNS 紀錄指著它。要讓終止或重建前後 IP 不變，另一種做法是一開始就用保留的公開 IP（reserved public IP），它存在到被刪除為止，DNS 紀錄不必改，懸空 DNS 也不會發生（[網路：subnet、私有 IP、公開 IP 與防火牆規則](/devops/infra/cloud-providers/vm-options/networking/)〈公開 IP：網際網路上的入口〉；保留 IP 的計費這次沒有查）。

1. **刪 DNS 紀錄**：在 Cloudflare 主控台的 DNS → Records 頁，刪掉根網域與 `www` 兩筆指到這台主機的 A 紀錄（每一筆從右側的選單選 Delete record，再按確認），郵件的 MX、SPF、DKIM 紀錄不動。刪完之後直接問網域的權威 nameserver，避開遞迴解析器的快取，刪除當下就讀得到結果；`<權威 nameserver>` 用 `dig NS <網域> +short` 查。經過 Cloudflare 代理的紀錄，訪客解析到的是 Cloudflare 的位址，紀錄一刪，Cloudflare 就不再回源到這台主機，所以這次確認刪除之後 24 秒就終止主機。不經代理、直接指公開 IP 的紀錄，訪客的遞迴解析器在舊紀錄的 TTL（DNS 回應可以被快取多久，見 [DNS](/devops/infra/knowledge-cards/dns/) 卡）到期之前還會回這個 IP，要從刪除那一刻起等過舊紀錄的 TTL 再終止主機；TTL 要在刪除之前讀，刪掉之後就讀不到了，`dig A <網域> @<權威 nameserver>` 的 ANSWER 段第二欄就是它（從 DNS 快取的機制推論，這次的紀錄都經過代理）：

   ```bash
   dig A <網域> @<權威 nameserver>        # 看 status 與有沒有 ANSWER
   dig A www.<網域> @<權威 nameserver>
   dig MX <網域> @<權威 nameserver> +short  # 郵件的紀錄還在
   ```

   07:19:54 查：根網域回 `NOERROR` 而沒有 A 紀錄（根網域上還有 MX 這些紀錄，所以名稱存在），`www` 回 `NXDOMAIN`；`dig MX` 照樣列出三筆。
2. **終止主機並刪掉開機磁碟**：

   ```bash
   oci compute instance terminate --instance-id <主機的 OCID> --preserve-boot-volume false --force \
     --wait-for-state SUCCEEDED --wait-for-state FAILED --max-wait-seconds 900
   ```

   07:20:18 送出，07:21:24 work request `SUCCEEDED`（66 秒）。`--preserve-boot-volume false` 讓開機磁碟一起刪掉，免費區塊儲存的 47 GB 才會釋放；不帶時開機磁碟留下來、繼續佔額度（回源那篇的清理寫了這一點；不帶的情形這次沒有實跑）。`terminate` 的 `--wait-for-state` 只收 work request 的四種狀態（`ACCEPTED`、`IN_PROGRESS`、`FAILED`、`SUCCEEDED`）。寫成主機的 `TERMINATED` 時 CLI 以 2 結束、請求不會送出（同一天對另一台主機實跑；後續網路資源跟著刪不掉的經過在回源那篇〈清理與 Cloudflare 設定的還原〉）。帶 `SUCCEEDED` 與 `FAILED` 兩個值時，CLI 等到其中一個就回傳，回傳的 work request 的 `status` 欄才分得出成功或失敗。
3. **刪網路資源**：照回源那篇〈清理與 Cloudflare 設定的還原〉的順序刪 NSG、公開子網路、security list、route table、internet gateway，每一條都帶 `--wait-for-state TERMINATED`（這幾種資源的刪除收的是資源本身的狀態）。五條在 16 秒內跑完，之後每一個 `get` 都回 `NotAuthorizedOrNotFound`。

終止之後，免費區塊儲存的用量少了這顆開機磁碟的 47（實跑讀到）；A1 的用量照理少 1 OCPU、6 GB，終止之後沒有讀。

## 延伸閱讀：暫停的範圍與恢復的順序、回源的網路、帳務明細的查法

- [服務暫停與恢復上線：只停服務、停止主機、終止主機到全部刪除各自保留的資源，暫停期間仍計費與仍被指向的資源，恢復前要查的漂移與恢復的順序](/devops/operations/09-host-lifecycle/suspend-and-resume-service/)：本篇演練的「停止主機」以外的暫停範圍（只停服務、終止主機但保留磁碟與網路設定、全部刪除再從 repo 重建）、怎麼依保留的月費與重建的成本選擇、恢復時憑證續期的時機
- [Cloudflare 回源的實測紀錄：Oracle Cloud NSG 只放行 Cloudflare 位址與規則數上限、回源的來源位址、Authenticated Origin Pulls、Worker 偽造 CF-Connecting-IP 與 Tunnel 的出站連接埠](/devops/infra/03-network-foundation/hands-on/cloudflare-origin-pull-walkthrough/)：這台主機的公開子網路、NSG 與 nginx 怎麼建的，以及網路資源的刪除順序與各自的錯誤訊息
- [Oracle Cloud 私有子網路 Ubuntu 主機的實測紀錄：套件來源的出站（NAT gateway、路由與 NSG）、序列主控台的連線，以及被回收之後的重建](/devops/infra/cloud-providers/oracle-cloud/hands-on/private-ubuntu-egress-console-rebuild/)：usage API 查帳務明細的每個參數、開機磁碟與免費區塊儲存額度的查法、超過額度的磁碟整顆計費與自動轉成免費
- [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/devops/operations/09-host-lifecycle/long-running-host-maintenance/)：恢復時比對的那幾類狀態平時怎麼量、更新之後的重開機判斷
