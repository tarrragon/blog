---
title: "OpenSSH 內建 CA 的導入：CA 金鑰、sshd 設定、簽發、principal、撤銷與主機憑證"
date: 2026-10-23
description: "用 OpenSSH 自帶的 ssh-keygen 與 sshd 建立 SSH 憑證的完整流程：使用者 CA 與主機 CA 的金鑰怎麼產生與保管、sshd 的 TrustedUserCAKeys 與 AuthorizedPrincipalsFile、簽發時的識別字串與有效期、憑證外洩時用 KRL 撤銷，以及用主機憑證取代逐台確認指紋，以及導入順序與兩個會讓所有人登不進去的設定：AuthorizedPrincipalsFile 的讀取權限、RevokedKeys 指的檔案不存在"
weight: 6
tags: ["infra", "ssh", "security", "access", "certificate"]
---

這篇整理只用 OpenSSH 本身（`ssh-keygen` 與 `sshd`，不加 Vault 或 Teleport 這類簽發服務）導入 [SSH 憑證（SSH certificate）](/infra/knowledge-cards/ssh-certificate/) 的做法。範圍從「主機上的 sshd 已經只收金鑰登入」開始，到每位管理員用短期憑證登入、憑證外洩時能提前作廢、用戶端不必再逐台確認主機指紋為止。文中的指令與紀錄格式在 OpenSSH 9.6 上跑過；本篇用到的 ed25519 金鑰與 KRL 撤銷清單要 OpenSSH 6.5 以上，憑證機制本身從 5.4 起就有。為什麼要把登入權限從靜態 `authorized_keys` 換成會到期的憑證、它跟 OS Login 這類由中央服務決定公鑰的做法怎麼選，見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/#主機登入驗證登入權限的收回靠人工刪除帳號連動或到期)的〈主機登入驗證：登入權限的收回靠人工刪除、帳號連動或到期〉。

## SSH CA 的運作：使用者憑證、主機憑證與兩把 CA

靜態 `authorized_keys`（每個帳號家目錄裡的 `~/.ssh/authorized_keys`，一行一把可以登入這個帳號的公鑰）的做法裡，每台主機各自記著「哪些公鑰可以登入哪個帳號」，所以新增一個人要改每一台，收回一個人也要改每一台。SSH CA 把這份清單換成一個簽名：一把 CA 私鑰對使用者的公鑰簽名，簽出一張憑證，憑證裡寫著一組名稱（principal，主機依它決定這張憑證能登入哪些帳號）、在什麼期間內有效、識別字串是什麼（key ID）。主機的 sshd 只要信任那把 CA 的公鑰，任何帶著有效 CA 簽名、還在有效期內、principal 對得上的憑證都能登入，主機上不必有任何一個人的公鑰。

同一個機制反過來用在主機上，叫主機憑證：CA 對主機的 host key（主機用來向用戶端證明自己身分的金鑰，用戶端第一次連線時確認的指紋就是它的）簽名，用戶端只要信任這把 CA，連到任何一台帶著有效主機憑證的主機都不必再確認指紋。使用者憑證與主機憑證最好用兩把不同的 CA 簽：使用者 CA 的私鑰外洩，攻擊者能簽出登入任何主機的憑證；主機 CA 的私鑰外洩，攻擊者能冒充任何主機。兩把分開，一把外洩只影響一個方向。

這套做法換掉的是收回方式：權限到期自動失效，收回延遲的上限是憑證的有效期。代價是多了要保管的 CA 私鑰（使用者與主機各一把）、一份要派送到每台主機的撤銷清單，以及一個每天替管理員簽發憑證的流程。

## 產生使用者 CA 與主機 CA 的金鑰

```bash
# 在簽發主機（保管 CA 私鑰的機器，位置的選擇見下方）上產生兩把 CA 金鑰：使用者 CA 與主機 CA 分開
ssh-keygen -t ed25519 -f user_ca -C "user-ca"
ssh-keygen -t ed25519 -f host_ca -C "host-ca"
```

- `-t ed25519`：金鑰類型。CA 金鑰與一般金鑰沒有格式上的差別，差別只在用途。
- `-f user_ca`、`-f host_ca`：輸出的檔名，自己取。執行之後產生 `user_ca`（私鑰）與 `user_ca.pub`（公鑰），主機 CA 同理。
- `-C`：註解，只是讓人辨認這把金鑰，不影響驗證。
- 執行時會要求輸入 passphrase，CA 私鑰要設：之後每次簽發都要輸入它，私鑰檔被複製走時攻擊者也還要猜這個 passphrase。

CA 私鑰能簽出登入所有主機的憑證，它外洩的影響等於所有主機的所有金鑰一起外洩，所以它的保管位置決定了這套做法的安全上限：放在一台專用、不對外開放、只有少數人能登入的簽發主機上，或放在[硬體安全模組（HSM）](/backend/knowledge-cards/hsm/)裡（`ssh-keygen` 支援用 `-D` 指定 PKCS#11 函式庫，讓私鑰留在硬體裡簽名；PKCS#11 是程式存取硬體金鑰的標準介面。這時 `-s` 給的是 CA 的公鑰檔，`ssh-keygen` 用它找出硬體裡對應的那把私鑰，簽發指令寫成 `ssh-keygen -D <pkcs11-library-path> -s user_ca.pub -I ... id_ed25519.pub`，函式庫路徑看硬體廠商的文件）。不放在任何人的筆電上，也不放進版本控制。公鑰（`.pub`）不是機密，可以放進設定管理工具派送。

## 設定主機的 sshd：信任使用者 CA

每台要讓管理員登入的主機，把使用者 CA 的公鑰放到 `/etc/ssh/user_ca.pub`，建立放 principals 檔的目錄（`sudo install -d -m 755 /etc/ssh/auth_principals`），並在 `sshd_config` 加入：

```text
# /etc/ssh/sshd_config：信任使用者 CA 簽發的憑證
TrustedUserCAKeys /etc/ssh/user_ca.pub
AuthorizedPrincipalsFile /etc/ssh/auth_principals/%u
RevokedKeys /etc/ssh/revoked.krl
```

- `TrustedUserCAKeys`：指向使用者 CA 的公鑰檔。這一行讓 sshd 接受這把 CA 簽的憑證；檔案裡可以放多把 CA 公鑰，一行一把，換 CA 時新舊兩把並列一段時間。
- `AuthorizedPrincipalsFile`：指定每個帳號接受哪些 principal，`%u` 會代入要登入的帳號名稱，所以 `/etc/ssh/auth_principals/deploy` 這個檔案列出的 principal 能登入 `deploy` 帳號。**不設這一行時，憑證裡的 principal 必須與登入的帳號名稱完全相同**（簽給 `alice` 的憑證只能登入 `alice` 帳號）。
- `RevokedKeys`：撤銷清單的位置，格式與用法見〈憑證外洩時提前作廢：KRL 撤銷清單〉。

principals 檔是一行一個 principal：

```text
# /etc/ssh/auth_principals/deploy：哪些 principal 可以登入 deploy 帳號
alice
ops-oncall
```

principal 的命名有兩種常見做法：一種是用人名（`alice`），principals 檔列出誰能登入哪個帳號；另一種是用角色（`ops-oncall`、`db-admin`），簽發時依這個人的角色把對應的 principal 簽進憑證，主機上的 principals 檔只列角色，人員異動時不必改任何一台主機。人少、人員很少異動時用人名就夠；人員常異動、或主機數量多到改 principals 檔本身就是負擔時，用角色。主機上只有一個共用帳號（雲端映像預設的 `ubuntu`、`ec2-user`）時，用角色當 principal、簽進憑證的 key ID 寫人名，sshd 的紀錄才分得出是誰登入（見〈sshd 紀錄裡的憑證資訊〉）。

改完設定先檢查語法，再重新載入：

```bash
# 檢查設定檔語法，沒有輸出代表語法正確
sudo sshd -t
# 重新載入設定，已經建立的連線不受影響
sudo systemctl reload ssh    # RHEL 系的服務名稱是 sshd
```

設定這一步有兩個在實測中會讓所有人登不進去的陷阱，套用到一台以上的主機之前都要先在一台上確認：

- **`AuthorizedPrincipalsFile` 是用登入帳號本人的權限讀的**：sshd 在驗證時以那個帳號的身分開這個檔，路徑上任何一層目錄那個帳號讀不到，sshd 就當成沒有任何 principal、拒絕登入，紀錄裡寫的是 `Could not open user 'alice' authorized principals ...: Permission denied` 與 `Certificate does not contain an authorized principal`。放在 `/etc/ssh/auth_principals/`、目錄權限 755、檔案權限 644，所有帳號都讀得到。
- **`RevokedKeys` 指的檔案不存在時，sshd 拒絕所有金鑰登入**：不只憑證，連 `authorized_keys` 裡的一般公鑰也一起被拒，紀錄裡是 `Error checking authentication key ... in revoked keys file ...: No such file or directory`。先放一份空的撤銷清單（`sudo ssh-keygen -k -f /etc/ssh/revoked.krl` 產生一份不含任何項目的 KRL；這條沒有 `-u`，只在第一次建立時用，對已有內容的清單執行會把它清空），再加這一行設定。之後的派送用新檔覆蓋舊檔，派送失敗時主機上留著的是上一版清單：sshd 照常運作，只是這次新撤銷的憑證在那台主機上還沒生效。

導入期間 `authorized_keys` 照常生效：sshd 同時接受憑證與 `authorized_keys` 裡的公鑰，所以可以先讓每位管理員用憑證登入過一次，確認之後再清掉 `authorized_keys`。用另一個終端機保留一條已登入的連線再改設定，改錯時還有一條路能改回來；整台都進不去時的備用路徑見[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)的〈救援入口：管理通道斷掉時的備用路徑〉。

## 簽發使用者憑證：識別字串、principal 與有效期

管理員把自己的公鑰交給持有 CA 私鑰的人或簽發主機，簽出一張憑證：

```bash
# 對 alice 的公鑰簽發一張可以登入 alice 與 deploy 帳號、8 小時有效的憑證
ssh-keygen -s user_ca -I "alice@example.com" -n alice,deploy -V +8h -z 1001 id_ed25519.pub
```

- `-s user_ca`：用來簽名的 CA 私鑰。
- `-I "alice@example.com"`：識別字串（key ID），會出現在 sshd 的認證紀錄與撤銷清單裡，填一個能對回人的值，通常是這個人在 IdP 的帳號。
- `-n alice,deploy`：principal，多個用逗號分隔，對應主機 principals 檔裡的名稱（或不設 principals 檔時對應帳號名稱）。不給 `-n` 時簽出的憑證不帶任何 principal：`TrustedUserCAKeys` 會拒絕這種憑證；但 OpenSSH 另有一種逐帳號信任 CA 的寫法，在某個帳號的 `authorized_keys` 裡寫一行 `cert-authority ssh-ed25519 AAAA...`（CA 公鑰），這一行會接受不帶 principal 的憑證登入那個帳號。本篇用的是 `TrustedUserCAKeys`，而主機上若有人在某個帳號的 `authorized_keys` 寫過 `cert-authority` 行，不帶 principal 的憑證就能登入那個帳號，所以每次簽發都寫出 principal。`authorized_keys` 裡的 `cert-authority` 與主機憑證一節用戶端 `known_hosts` 裡的 `@cert-authority` 是兩回事：`authorized_keys` 那一行在主機上信任使用者 CA，`known_hosts` 那一行在用戶端信任主機 CA。
- `-V +8h`：有效期，`+8h` 表示從現在起八小時；也可以寫成 `20261101:20261102` 這種起訖日期。有效期就是收回延遲的上限，手動簽發時常設成一個工作日左右，範例的八小時就是這個長度：每天簽一次，下班時自然失效。
- `-z 1001`：序號，撤銷清單可以用序號指定要作廢的憑證，所以每張憑證給不重複的序號（從某個數字起逐張加一即可），簽發主機要記下每個序號簽給了誰。
- `id_ed25519.pub`：要被簽的使用者公鑰。

執行之後在公鑰旁邊產生 `id_ed25519-cert.pub`。這個檔名是固定的對應關係：`ssh` 用 `id_ed25519` 這把私鑰時，會自動找同目錄的 `id_ed25519-cert.pub` 一起送出，所以管理員把憑證放回 `~/.ssh/` 就能直接登入，不必加任何參數。用 `ssh-keygen -L` 讀得出憑證的內容：

```bash
# 讀出憑證的識別字串、序號、有效期與 principal
ssh-keygen -L -f id_ed25519-cert.pub
```

輸出裡要對的是 `Key ID`、`Serial`、`Valid` 與 `Principals` 四欄；`Extensions` 欄列出這張憑證允許的功能（`permit-pty`、`permit-port-forwarding`、`permit-agent-forwarding` 這類），預設全開，簽發時用 `-O`（指定憑證選項）加上 `no-agent-forwarding`、`no-port-forwarding` 這類值逐項關掉。需要讓 CI 這類機器用憑證時，同樣用 `-O force-command=<指令>` 限定它登入之後只能執行一條指令。

手動簽發時，簽發的人每天要處理每位管理員的申請，每一次都要先確認申請者的身分，否則任何人寄來一把公鑰都能拿到憑證。組織有 [IdP](/backend/knowledge-cards/identity-provider/) 時，常見的做法是讓簽發服務接 IdP 登入，管理員登入 IdP 之後由服務自動簽發，這就是 [HashiCorp Vault](/infra/knowledge-cards/vault/) 的 SSH secrets engine、smallstep 的 `step ssh` 與 Teleport 做的事；本篇的手動流程適合人數少、或要先理解機制再導入簽發服務的團隊。

## 憑證外洩時提前作廢：KRL 撤銷清單

憑證到期之前就要失效時（筆電遺失、私鑰外洩、人員在有效期內離職），把它加進撤銷清單（KRL，Key Revocation List）並派送到每一台主機。撤銷清單的正本放在簽發主機上，以下指令都在簽發主機上對正本執行，改完再把整份檔案派送到每台主機的 `/etc/ssh/revoked.krl`（`RevokedKeys` 指的位置）：

```bash
# 依憑證檔撤銷：把 alice 那張憑證加進既有的撤銷清單
ssh-keygen -k -u -f revoked.krl id_ed25519-cert.pub

# 依序號或識別字串撤銷：手上沒有憑證檔時用規格檔描述要撤銷的憑證
echo "serial: 1001" > krl.spec
ssh-keygen -k -u -f revoked.krl -s user_ca.pub krl.spec

# 確認某張憑證是否已在清單裡（輸出 REVOKED 代表已撤銷）
ssh-keygen -Q -f revoked.krl id_ed25519-cert.pub
```

- `-k`：產生或更新 KRL；`-u` 表示加進既有的清單，不加 `-u` 會用這次的內容覆蓋整份清單。
- `-f revoked.krl`：簽發主機上那份正本的檔名。
- `-s user_ca.pub`：用規格檔撤銷時，指定這些序號或識別字串屬於哪一把 CA。給的是公鑰：撤銷清單只記下「這把 CA 簽的哪些序號作廢」，不需要 CA 私鑰簽名，這與簽發時 `-s user_ca` 給私鑰不同。
- `krl.spec`：規格檔，一行一項，`serial: 1001` 撤銷那個序號，`id: alice@example.com` 撤銷那個識別字串簽出的所有憑證。
- `-Q`：查詢一把金鑰或一張憑證是否在清單裡。

sshd 每次驗證都重新讀這份檔案，換掉檔案之後不必重新載入 sshd。撤銷清單的成本在派送：它要送到每一台主機，送不到的那幾台仍然接受被撤銷的憑證，所以派送要交給設定管理工具或 IaC 這類會回報失敗的機制，派送失敗時有人看得到。撤銷擋下的是下一次登入，已經建立的工作階段要另外在主機上結束，用的是 systemd 管理登入工作階段的 `loginctl`（要 root 權限）：一人一個帳號時用 `sudo loginctl terminate-user <username>`；多人共用一個帳號（`deploy`、`ubuntu`）時 `terminate-user` 會結束所有人的工作階段，改用 `loginctl list-sessions` 列出工作階段、對照 sshd 紀錄裡那一行 `Accepted publickey` 的來源 IP 與時間找出那個人的 `<session-id>`，再用 `sudo loginctl terminate-session <session-id>` 只結束它。

有效期短的時候，撤銷清單能爭取到的時間有限：一張八小時的憑證剩下的有效時間最多八小時，派送清單到每台主機若也要花上幾小時，撤銷只比自然到期早一點生效。撤銷清單是給「等不到到期」的情形用的，而 CA 私鑰本身外洩時撤銷清單也救不了，那時要換掉 CA：產生新的 CA、把新公鑰加進每台主機的 `TrustedUserCAKeys`、同一次就拿掉舊的那一把、重新簽發所有人的憑證。〈設定主機的 sshd〉講的新舊兩把並列一段時間，是有計畫輪替 CA 時的做法；私鑰外洩時舊的那一把每多留一刻，攻擊者就多一刻能簽出有效憑證。

## sshd 紀錄裡的憑證資訊

用憑證登入時，sshd 的認證紀錄會帶著憑證的識別字串、序號與簽發的 CA，這一行才分得出是誰登入。在預設的 `LogLevel INFO` 下，成功登入的那一行是：

```text
Accepted publickey for deploy from 10.0.1.20 port 53080 ssh2: ED25519-CERT SHA256:eLfd... ID alice@example.com (serial 1001) CA ED25519 SHA256:kSP8...
```

`for deploy` 是登入的帳號，`ID alice@example.com (serial 1001)` 是憑證的識別字串與序號，多人共用 `deploy` 帳號時靠這一段分出是誰。`sshd_config` 設 `LogLevel VERBOSE`（比預設 `INFO` 多記驗證細節的紀錄等級）時，上面這一行照樣出現，而且在它之前還會多記一行 `Accepted certificate ID "alice@example.com" (serial 1001) signed by ED25519 CA ...`。

被拒時，紀錄寫出原因：過期是 `Certificate invalid: expired`；principal 對不上時，有設 `AuthorizedPrincipalsFile` 是 `Certificate does not contain an authorized principal`，沒設時是 `Certificate invalid: name is not a listed principal`；在撤銷清單裡是 `Authentication key ED25519-CERT SHA256:... revoked by file /etc/ssh/revoked.krl`。這幾種情形用戶端看到的都只是 `Permission denied (publickey)`，原因只在主機的紀錄裡（Debian 與 Ubuntu 用 `journalctl -u ssh`，RHEL 系用 `journalctl -u sshd`）。

## 主機憑證：簽發流程、HostCertificate 與 @cert-authority

第一次連到一台主機時，`ssh` 會問要不要信任它的指紋；主機重建（autoscaling、重新部署）之後 host key 換了，`ssh` 會警告指紋變更並拒絕連線。主機經常重建的環境裡，管理員會被這個警告訓練成直接刪掉舊指紋、接受新的，而那正是中間人攻擊需要的反應。主機憑證讓用戶端改成信任主機 CA，帶著有效主機憑證的主機直接通過，不再逐台確認指紋。

主機 CA 的私鑰在簽發主機上，所以流程是把目標主機的 host key 公鑰取回簽發主機、在那裡簽、再把簽出的憑證放回目標主機：

```bash
# 在目標主機 web-01 上執行：把 host key 的公鑰從 web-01 推到簽發主機（公鑰不是機密）
scp /etc/ssh/ssh_host_ed25519_key.pub <signing-host>:web-01_host_ed25519_key.pub

# 在簽發主機上執行：對取回的公鑰簽發主機憑證，-h 表示這是主機憑證
ssh-keygen -s host_ca -I "web-01" -h -n web-01.example.com -V +52w web-01_host_ed25519_key.pub

# 回到 web-01 上執行：把簽出的憑證拉回來、放到 host key 旁邊
scp <signing-host>:web-01_host_ed25519_key-cert.pub /tmp/
sudo install -m 644 /tmp/web-01_host_ed25519_key-cert.pub /etc/ssh/ssh_host_ed25519_key-cert.pub
```

- `-h`：簽的是主機憑證而不是使用者憑證。
- `-I "web-01"`：主機的識別字串，填主機名稱。
- `-n web-01.example.com`：用戶端連線時會用到的名稱，逗號分隔可以列多個（用 IP 連線時也列 IP）。用戶端連線時用的名稱不在這份 `-n` 清單裡，用戶端就不接受這張憑證，用戶端的 `ssh -v` 輸出裡是 `Certificate invalid: name is not a listed principal`。
- `-V +52w`：主機憑證的有效期通常比使用者憑證長（主機不會離職），但仍要在到期前重新簽發，否則到期那天所有用戶端都會連不上這台主機。
- `<signing-host>`：簽發主機的位址。`web-01_host_ed25519_key.pub`：取回之後在簽發主機上的檔名，自己取，帶主機名稱以免混淆；來源路徑以目標主機上實際存在的 `/etc/ssh/ssh_host_*_key.pub` 為準。

憑證放到 `/etc/ssh/ssh_host_ed25519_key-cert.pub` 之後，在 web-01 的 `sshd_config` 加一行 `HostCertificate /etc/ssh/ssh_host_ed25519_key-cert.pub`，同樣先 `sudo sshd -t` 檢查語法再重新載入。用戶端在 `~/.ssh/known_hosts`（用戶端記錄已信任主機的檔案；全機共用的是 `/etc/ssh/ssh_known_hosts`）加一行：

```text
# 信任 host_ca 簽給 *.example.com 的主機憑證
@cert-authority *.example.com ssh-ed25519 AAAAC3Nza...（host_ca.pub 的內容）
```

`@cert-authority` 後面的樣式限定這把 CA 只對哪些主機名稱有效，填組織自己的網域；樣式寫成 `*`（符合任何主機名稱）時，拿到這把 CA 私鑰的人簽出的憑證，不論掛著哪個主機名稱（包括別的組織的網域），用戶端都會接受。這個樣式比對的是用戶端連線時用的名稱，所以一次連線要通過兩道比對：那個名稱符合 `@cert-authority` 的樣式，而且列在主機憑證的 `-n` 裡。用 IP 連線時兩處都要涵蓋那個 IP；樣式只寫網域時，用戶端不採信這把 CA、退回逐台確認指紋。主機憑證最適合交給建立主機的流程：映像檔或開機流程產生 host key 之後，由簽發服務自動簽發，主機重建時憑證跟著重簽。

## 導入順序：CA、主機設定、憑證與 authorized_keys 之間的依賴

上面各節的設定有先後依賴，而導入期間管理員仍要天天登入主機，所以順序的原則是新的登入路徑驗證過之前，舊的那一條一直保留。

CA 與主機設定之間的依賴最直接：主機要信任的是 CA 公鑰，所以 CA 先產生、私鑰先放進簽發主機或硬體安全模組，才有公鑰可以派送。主機那一側加 `TrustedUserCAKeys`、`AuthorizedPrincipalsFile`、`RevokedKeys` 三行之前，先把使用者 CA 公鑰、principals 檔與一份空的撤銷清單放到位：三行設定指向的檔案只要有一個不在，〈設定主機的 sshd：信任使用者 CA〉講的兩個陷阱就會在重新載入的那一刻讓所有人登不進去。這時 `authorized_keys` 仍然有效，憑證是多出來的一條路。

憑證與 `authorized_keys` 之間的依賴決定什麼時候能拿掉舊路徑：每位管理員都用憑證登入過每一類主機、並在 sshd 紀錄裡看到自己那一行帶著 `ID <自己的識別字串>` 的 `Accepted publickey` 之後，`authorized_keys` 才可以清掉。撤銷清單的派送也要在清掉之前接上設定管理工具並實際演練一次——撤銷一張測試憑證、確認每台主機都拒絕它——因為清掉 `authorized_keys` 之後，收回一個人的權限只剩兩個手段：不再替他簽發、等手上的憑證到期，以及把他的憑證加進撤銷清單，而撤銷清單要靠演練過的派送才送得到每台主機。救援用的本機帳號（給 Serial Console 這類救援入口用、不經過 sshd 金鑰登入的帳號）不跟著清掉，它的密碼與保管方式另外管理。

主機憑證與使用者憑證之間沒有依賴，可以獨立導入；它的前提是用戶端的 `known_hosts` 已經加了 `@cert-authority` 那一行，否則用戶端仍然逐台確認指紋，主機憑證放上去也不會被用到。

## 延伸閱讀：簽發服務、知識卡與 GCP 上的對應做法

- → [SSH Certificate（SSH 憑證）](/infra/knowledge-cards/ssh-certificate/)：SSH 憑證與靜態金鑰、OS Login 三種金鑰發放方式的對照
- → [HashiCorp Vault](/infra/knowledge-cards/vault/)：接 IdP 登入、自動簽發 SSH 憑證的簽發服務，也是保管 CA 私鑰的位置之一
- → [伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/#主機登入驗證登入權限的收回靠人工刪除帳號連動或到期)：SSH 憑證適合的情境（主機跨多個環境、進不了客戶帳號系統的外包團隊），以及它與跳板機、身分感知代理怎麼組合
- → [GCP VM 的 SSH 與 RDP 管理通道](/infra/03-network-foundation/gcp-iap-ssh-access/)：主機全在 GCP 時改用 OS Login 讓登入權限跟著 Google 帳號走的做法
