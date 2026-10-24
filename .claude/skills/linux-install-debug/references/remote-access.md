# 遠端連線與終端機問題

SSH 連線本身、以及「你的終端機 ↔ 遠端 session」之間那條連線的狀態問題。判斷對是哪一層，修復很直接。

## SSH 連不上

先分「網路層 vs 服務層」，用症狀分流：

- **TCP timeout（連 port 22 卡住無回應）** → 網路層或機器沒跑。查 `ip neigh`（目標 IP 若 `INCOMPLETE` = 鏈路層沒回應；`arp` 常沒裝）→ 見 [machine-unreachable](machine-unreachable.md)。
- **`Connection refused`** → 網路通、但沒服務在聽 22。去機器上 `systemctl status sshd`；沒裝 / 沒起就 `pacman -S openssh && systemctl enable --now sshd`。
- **`Permission denied (publickey)`** → key 沒對上。換帳號 + IP 直連走密碼繞過鎖死金鑰的別名：`ssh user@<IP>`；再重新佈 key。
- **`Host key verification failed` / `REMOTE HOST IDENTIFICATION HAS CHANGED!`** → 目標送來的主機金鑰跟 `known_hosts` 記的不同。成因可能是重裝、換機、IP 重用、雲端 VM 重建了開機磁碟，也可能是連線被中間人攔截，所以清舊紀錄之前先核對新指紋：
  1. 從警告裡 `The fingerprint for the <type> key sent by the remote host is` 下一行抄下 `SHA256:` 的值；`<type>`（ED25519、ECDSA、RSA）決定下一步讀哪一把金鑰。
  2. 用一條**不經過這條 SSH 連線**的管道讀出主機自己的指紋：實體或雲端主控台的 console 上執行 `ssh-keygen -lf /etc/ssh/ssh_host_<type>_key.pub`（`<type>` 寫成小寫的 `ed25519`、`ecdsa`、`rsa`）；GCP 的 VM 在 metadata 設了 `enable-guest-attributes=TRUE` 時，用 `gcloud compute instances get-guest-attributes <vm> --zone=<zone> --query-path=hostkeys/<key-type> --format="value(value)" | awk '{print "<key-type> " $1}' | ssh-keygen -lf -`，`<key-type>` 是 `ssh-ed25519`、`ecdsa-sha2-nistp256` 或 `ssh-rsa`。
  3. 兩個指紋相同才 `ssh-keygen -R <IP 或別名>` 清掉舊紀錄再連；核對不了、或指紋不同時，不要清除舊紀錄；先確認連到的 IP 仍屬於那台主機（DNS 紀錄、IP 是否被重新分配），以及中途有沒有代理或跳板主機。也不要用 `-o StrictHostKeyChecking=no`、`UserKnownHostsFile=/dev/null` 或 `gcloud compute ssh --strict-host-key-checking=no` 繞過，效果等於不核對就清除。
  - `gcloud compute ssh` 的紀錄不在 `~/.ssh/known_hosts`，在 `~/.ssh/google_compute_known_hosts`，鍵是 `compute.<instance-id>`。MIG 的 `recreate-instances` 重建時換掉開機磁碟，實測一次時 ID 沒變（gcloud 說明寫 ID 可能改變），ID 沒變時重建之後就會撞到這個警告；預期中的警告與中間人攔截送出的警告長得一樣，仍然照步驟 2 核對；清除要寫成 `ssh-keygen -R compute.<instance-id> -f ~/.ssh/google_compute_known_hosts`（ID 用 `gcloud compute instances describe <vm> --zone=<zone> --format="value(id)"` 查）。啟用 guest attributes 不會讓 gcloud 自動更新已存在的紀錄，比對與清除要自己做。

根因通則：SSH 的別名 / 金鑰 / `known_hosts` 都綁「特定機器身分」，換機 / 重裝 / DHCP 重配後別名會連錯或被擋 → 用帳號 + IP 直連確認，再更新別名。

### 經 IAP 這類身分感知代理連線：錯誤停在哪一層

連線經過代理（GCP 的 `gcloud compute ssh --tunnel-through-iap`、`gcloud compute start-iap-tunnel`）時，在 TCP 與 sshd 之間多了代理的授權與代理到 VM 的那一段，每個錯誤碼各自對應到其中一層。判讀要看完整輸出（`2>&1`），錯誤碼印在中段，只看最後一行只會看到 ssh 的 `return code [255]`。

- **`4033: 'not authorized'`** → 停在代理的授權：帳號沒有 `roles/iap.tunnelResourceAccessor`，或綁定的 IAM Condition（port、`destination.ip`、`request.time` 期限）不允許這次連線。IAM 綁定的變更通常兩分鐘內生效，有時要七分鐘以上；改完權限之後隔幾分鐘重試再判。
- **`4003: 'failed to connect to backend'`** → 代理已經放行，連不到 VM 的那個 port：VM 少了防火牆規則用的 network tag、規則的來源不含代理的位址段、組織層級的防火牆政策先擋下，VM 上的 sshd 沒在聽，或 VM 內的作業系統防火牆擋下。防火牆這一段用（先啟用 `networkmanagement.googleapis.com`）`gcloud network-management connectivity-tests create <name> --source-ip-address=35.235.240.1 --destination-instance=projects/<project>/zones/<zone>/instances/<vm> --destination-port=22 --protocol=TCP`（`35.235.240.1` 是 IAP 位址段 `35.235.240.0/20` 裡的任一位址），結果會指出擋下的規則名稱；這條指令會留下一個測試資源，看完用 `gcloud network-management connectivity-tests delete <name>` 刪掉。
- **通道開了、`Permission denied (publickey)`** → 停在主機登入：VM 啟用 OS Login 時，查帳號有沒有 `roles/compute.osLogin`（可登入、不能 sudo）或 `roles/compute.osAdminLogin`（可 sudo）；VM 掛著服務帳號時另外要那個服務帳號的 `roles/iam.serviceAccountUser`，缺它同樣只回 publickey 被拒。啟用 OS Login 之後，metadata 裡的 SSH 金鑰對那台 VM 失效。
- **要用一般 `ssh` 測（指定金鑰或使用者）**：在同一次 shell 呼叫裡執行 `gcloud compute start-iap-tunnel <vm> 22 --local-host-port=localhost:2222 --zone=<zone> & TUNNEL=$!; sleep 3; ssh -p 2222 -o HostKeyAlias=<vm> <user>@localhost; kill $TUNNEL`。2222 換成任一個沒被占用的本機 port，兩處要相同；`sleep` 等通道開始監聽；`HostKeyAlias` 讓 known_hosts 依 VM 名稱記錄，換一台 VM 用同一個 port 時不會撞到 `[localhost]:2222` 的舊紀錄；`$!` 記下通道的 PID，每次 shell 呼叫各自獨立時 `kill %1` 找不到它。這條路不需要在 ssh 設定裡寫 `ProxyCommand`。

驗證「新規則放行了 IAP 連線」時，規則剛開 logging 的最初幾分鐘寫入的紀錄 `rule_details` 是空的，所以用規則名稱查（`jsonPayload.rule_details.reference:"<rule>"`）會查到零筆；改用來源位址段查：`gcloud logging read 'logName:"compute.googleapis.com%2Ffirewall" AND ip_in_net(jsonPayload.connection.src_ip, "35.235.240.0/20")' --freshness=1h`。

## SSH 斷線後本機終端機噴亂碼 / 狂跳字元

症狀：本機終端機瘋狂輸出 `<數字;數字M` 之類序列，尤其動滑鼠時。**這是本機終端機被卡在滑鼠回報模式，不是遠端在打字。**

判讀：亂碼只在動滑鼠時出現、形如 `數字;數字M` → 滑鼠座標回報。成因：遠端全螢幕程式（TUI / 多工器）開了滑鼠追蹤，SSH 硬斷時來不及關閉，本機終端機停在回報模式。

修（跟遠端無關）：

- 最快：開新終端機分頁 / 視窗（模式是該 session 狀態，新視窗乾淨）。
- 救現有：滑鼠移開別動 → 盲打 `reset` + Enter。
- 還沒清：`printf '\033[?1000l\033[?1002l\033[?1003l\033[?1006l'`。

同類：alternate screen 沒還原（畫面凍結 / 清空）→ `reset`。通則：SSH 硬斷後本機終端機異常，先懷疑「對端來不及還原終端機模式」，`reset` 或開新視窗，別去重連遠端。

## 遠端打字亂碼 / 重複 / 位置錯亂

分兩層排除（症狀相似、修法不同）：

- **locale（編碼寬度）**：本機把 `LC_CTYPE` 帶進遠端、遠端沒對應 locale → 退回 POSIX，行編輯對多位元組寬度判斷錯 → 輸入重複 / 錯位。查 `locale` + `locale -a`。修：遠端明確設 `LANG` / `LC_CTYPE` 到實際存在的 UTF-8 locale。
- **terminfo（繪製指令）**：本機 `TERM`（如 `xterm-ghostty`）遠端無對應條目 → 清行 / 移游標 / 重繪錯亂。查 `echo $TERM` + `infocmp $TERM`。修：`infocmp -x $TERM | ssh <遠端> 'tic -x -'`。

分法：查 `locale` vs 查 `$TERM`+`infocmp`。

## 從 SSH 操控遠端圖形桌面

兩類界線：

- **圖形程式找不到 display**：SSH shell 無圖形環境變數。對著遠端在跑的 Wayland session 操作要補：`XDG_RUNTIME_DIR=/run/user/<uid>`、`WAYLAND_DISPLAY=<socket 名，如 wayland-1>`、必要時 compositor 的 instance 變數（如 `HYPRLAND_INSTANCE_SIGNATURE`）與 `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/<uid>/bus`。值從 `/run/user/<uid>/` 或既有行程環境撈。補齊後可下 IPC、`grim` 截圖。
- **compositor 必須從實體圖形 VT 起、SSH pty 起不來**：Wayland compositor（Hyprland）需要圖形 VT 上的 logind seat + DRM master；從 SSH pty 起會 backend 建立失敗（如 `CBackend::create() failed`）。判讀訊號：從 SSH 起 compositor 報 seat / DRM / backend 錯。這不是設定問題，是資源在 SSH 這條連線不存在。

從 SSH 遠端回到圖形 VT（比在 VM 視窗跟 `Ctrl+Alt+Fn` 搏鬥穩定），**順序是先查再切**——沒查就 `chvt`，切過去只會看到黑畫面，又回到肉眼判讀（黑畫面這個表象可以是「沒 getty」「顯示輸出沒接」「compositor 掛了」三種不同根因）：

1. **切之前先查目標 VT 有沒有 getty**：`systemctl is-active getty@tty<N>`。inactive 就先拉起來：`sudo systemctl start getty@tty<N>`。
2. **查 enable 狀態決定要不要治本**：`systemctl is-enabled getty@tty<N>`。有些安裝器（實測：archboot）裝出來的系統 `getty@tty1` 是 `disabled`——不是「autovt 沒觸發」的暫時態，而是每次開機都黑畫面；`sudo systemctl enable getty@tty<N>` 治本。
3. **登入後 `tty` 回 `/dev/pts/N` = VT 被 userspace console 接管**（實測：archboot 預設用 kmscon 取代 VT getty——這也是上一條 getty disabled 的真正原因）。kmscon 直接在 DRM 上畫、login 跑在 pts、`chvt` 救不了；compositor 要 DRM master、跟 kmscon 衝突。換手：`pgrep -af kmscon` 確認佔用者 → `sudo systemctl disable --now kmsconvt@tty<N>` → `sudo systemctl start getty@tty<N>`，畫面變真 VT 的 login（`tty` 回 `/dev/tty<N>`）後才起 compositor。
4. `sudo chvt <N>` 切目前顯示的 VT，`sudo fgconsole` 確認前景 VT。
5. 注意：VM 可能同時有序列主控台 + 圖形顯示兩個獨立輸出，`chvt` 只動圖形側；在 VM 軟體裡要切到 Display view 才看得到圖形桌面。判讀自己在哪一側：`who` 顯示登入在 `pts/N` 或 `ttyS*`/`ttyAMA*` = 序列側、`tty<N>` = 圖形側的 VT；圖形裝置本身有沒有掛上讀 `ls /dev/dri/`（有 `card0` = 裝置在、只是視窗停在序列視圖）。使用者停在序列 console 時，畫面上的提示可能寫 `tty0`（現行 VT 的別名）——判斷實際前景 VT 讀 `cat /sys/class/tty/tty0/active`，不讀提示字樣。

## 快速路由

| 症狀                                     | 檢查                                            | 動作                                                                         |
| ---------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------- |
| 本機終端機噴 `數字;數字M`、動滑鼠時      | 只在動滑鼠時 → 滑鼠回報模式                     | `reset` / 開新視窗                                                           |
| 遠端打字重複 / 錯位                      | `locale` vs `$TERM`+infocmp                     | 設 locale / `tic` 裝 terminfo                                                |
| 圖形程式 SSH 下找不到 display            | 有無 `WAYLAND_DISPLAY`                          | 補圖形 env 變數                                                              |
| compositor SSH 起不來報 seat/DRM         | 是否從 SSH pty 起                               | `chvt` + `getty@tty<N>` 回圖形 VT                                            |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | 不經 SSH 的管道讀主機指紋                       | 指紋相同才 `ssh-keygen -R`；gcloud 用 `-f ~/.ssh/google_compute_known_hosts` |
| IAP 連線 `4033`                          | IAM 角色與 Condition、等 2–7 分鐘再判           | 補角色或改 Condition                                                         |
| IAP 連線 `4003`                          | tag、防火牆規則、Connectivity Tests             | 補 tag 或修規則                                                              |
| IAP 通道開了而 publickey 被拒            | OS Login 角色、VM 服務帳號的 serviceAccountUser | 補角色                                                                       |
