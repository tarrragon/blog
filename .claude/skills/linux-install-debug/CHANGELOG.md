# linux-install-debug 版本紀錄

新到舊。版號規則與兩個住址（本檔與 `SKILL.md` frontmatter 的 `metadata.version`）見專案的 skill 同步規範。

**Version**: 1.20.4 — 多輪審查 Round 4 修正：共用帳號改成輪替憑證後結束該帳號全部互動工作階段（逐個辨認離職者的 sshd 行程做不到）；撤銷與結束的順序改成最後一次結束排在撤銷生效之後、正在造成損害時先結束一次；刪掉登記失敗時跳過步驟的規則；remote-access 的「重建後必定撞到警告」改成依 ID 是否改變。

**Version**: 1.20.3 — 多輪審查 Round 3 修正：主機金鑰不得用 StrictHostKeyChecking=no 這類旗標繞過、預期中的警告仍要核對；離職結束工作階段排除共用帳號（改輪替憑證、逐個 kill 那個人的 sshd 行程）；快速路由表的 4033 等待時間改成 2–7 分鐘；觸發詞改成 GCP IAP、IAP 4033 這類限定寫法，避免 In-App Purchase 與 WebSocket 4003 誤觸發。

**Version**: 1.20.2 — 多輪審查 Round 2 修正：remote-access 的一般 ssh 測試改成同一次 shell 呼叫內記下通道 PID、等通道監聽、用 HostKeyAlias 避開 localhost port 的 known_hosts 衝突；connectivity test 補 API 啟用與刪除；4003 的 VM 端成因拆成 sshd 沒在聽與作業系統防火牆。process-service-state 的登記失敗段寫明它與三個步驟的關係：只在出現徵兆的機器上省略 terminate-user，pgrep 確認一律不省。

**Version**: 1.20.1 — remote-access 依多輪審查修正：主機金鑰核對不寫死 ED25519，改成依警告寫的金鑰類型讀對應的那一把；指紋不同時寫出要確認的對象（IP 是否仍屬那台主機、中途有沒有代理或跳板）；IAM 綁定生效時間改成通常兩分鐘、有時七分鐘以上；connectivity test 的來源位址、本機 port 與結束通道的方式補上說明；OS Login 兩個角色寫明各自能不能 sudo；防火牆紀錄 rule_details 為空的因果順序改正。process-service-state 的撤銷權限句改成「只會擋住之後的新登入」，離職的處置寫成 pkill 結束、pgrep 輸出為空確認。

**Version**: 1.20.0 — remote-access 的主機金鑰那一條改寫：原本直接 `ssh-keygen -R` 清除，改成先從警告抄下指紋、再用不經過這條 SSH 連線的管道（console 上的 `ssh-keygen -lf`、GCP guest attributes）核對，相同才清除；補 `gcloud compute ssh` 的紀錄在 `~/.ssh/google_compute_known_hosts`、鍵是 `compute.<instance-id>`，MIG 重建沿用同一個 ID 所以必定撞到警告，以及啟用 guest attributes 不會自動更新既有紀錄。remote-access 新增「經 IAP 這類身分感知代理連線：錯誤停在哪一層」段（`4033` 停在代理授權、`4003` 停在代理到 VM、通道開了而 publickey 被拒停在 OS Login 角色與 VM 服務帳號的 serviceAccountUser；IAM 綁定一到兩分鐘才生效；不用 `ProxyCommand` 的本機 port 轉送；防火牆紀錄初期 `rule_details` 為空時改用 `ip_in_net` 查），快速路由表補四列。process-service-state 新增「結束某個使用者的所有工作階段」段：先撤銷再結束、以 `pgrep -u` 判斷而不信 `loginctl` 的回傳值、`pam_systemd` 登記失敗時 `terminate-user` 回 exit 1 而行程仍在、用 `pkill -KILL -u` 補，快速路由補一列。SKILL.md 補兩條路由與觸發詞。來源是一次 GCP 測試專案上的管理通道實機驗證（Debian 12、IAP、OS Login、MIG 重建）。

**Version**: 1.19.0 — machine-unreachable 新增「有外部觀察者時：先比對它們，再登入主機」段：心跳監看、外部探測與內部探測三者並排的判讀表（五種組合各自先查哪裡），心跳中斷時內部探測不可信，心跳與外部探測都正常而主機有說不出原因的異常時把監控主機被入侵列進候選；三個觀察者的結果各從哪裡讀（監看服務頁面、探測服務、Prometheus 的 `probe_success`）、只有兩個時怎麼用、同一列多個地方從最近改過的查起；快速路由表補一列。SKILL.md 的監控路由拆開：「怕整台機器當掉沒人知道」改導向體外心跳（OnFailure 靠 systemd、機器當掉時跟著停），並寫明監看服務的通知管道不能經過這台機器。來源是一組單機監控盲區與跨網路連線文章的判讀表與審查。

**Version**: 1.18.0 — process-service-state 新增「主機很慢、load 很高：先分 CPU、記憶體還是 I/O」段：三種資源在 macOS 與 Linux 的權威指令與判讀、load 高而 CPU 不高先看記憶體、虛擬機內叢集的連鎖症狀（etcd 逾時、控制平面重啟、CrashLoopBackOff、探針逾時、port-forward 斷線）先查宿主機、停東西前先確定瓶頸、恢復時間。SKILL.md 補權威來源速查表一列、症狀路由一條、反模式一條、三個觸發詞（load 很高、swap 滿、etcd 逾時）。來源是一次本機 kind 叢集在宿主機 swap 用滿時的實測。

**Version**: 1.17.2 — 版本紀錄搬到同目錄的 `CHANGELOG.md`。skill 是 runtime 整份載入的檔案，而沒有任何規則要求任何人讀版本紀錄，留在 SKILL.md 等於每次叫用都付一次無效讀取。SKILL.md 末尾留一行指過去，版號的兩個住址改成「CHANGELOG.md 最上面那一條 + frontmatter 的 metadata.version」。skill 的指令內容一個字都沒改。

**Version**: 1.17.1 — 術語校正：判準全數改為判斷標準（動作修飾語縮為「X 標準」、狀態義改為「X 條件」）。判準的語域在哲學與教育評量、工程讀者解析不了——五份低階模型探針一致回報非通用

**Version**: 1.17.0 — 補 frontmatter（並補一條症狀路由：自己寫的 shell script 壞了 → 可攜陷阱段。那幾條歸檔在安裝流程底下，因為它們是寫 bootstrap 腳本時踩出來的，而症狀出現時多半不在裝機情境——只憑主題歸屬分類，症狀查不到它）。補的是 frontmatter（`name` / `description` / `metadata.version`）。這份 skill 先前整份沒有 frontmatter，所以它從來不會被自動觸發——只有明確指名才叫得動。代價在補這一版的當天具體發生過一次：另一個工作流程踩到 `$var` 緊跟多位元組字被吞 byte 的 bug（實測環境正是 macOS bash 3.2），現場重新推導一次，並寫下了 v1.15.3 這條 fact-check 早就修正掉的錯誤歸因。**知識在庫裡而觸發器不存在，等於沒有這份 skill。**

同批修版本記錄的重號：2026-07-09 的三個變更在本 skill 已到 1.15.0 時從 1.3.0 重新編號，且插在舊序列中間，造成 1.4.0 與 1.3.0 各出現兩次、1.4.1 排在 1.2.1 之後。依 commit 時序重編為 1.15.1 / 1.15.2 / 1.15.3。重號會讓「這條規則是哪一版加的」查不出答案，而版本記錄的用途正是回答這個問題。

**Version**: 1.16.0 — install-and-verify 補「`command not found` 分診」段（macOS dotfiles bootstrap 冷測抽出）：三個不同根因（真沒裝 / 裝了但不在 PATH / 互動 shell 能用但 script 不能）分開修，不一律 install——`find` 決定沒裝 vs 裝了、`$PATH` 對照決定哪個目錄漏、互動 vs script 決定哪個作用域沒拿到；涵蓋安裝器把 PATH 寫進非-repo profile / 系統 drop-in、子行程改的 PATH 回不到父行程兩個機制
**Version**: 1.15.3 — fact-check 修正：`$var` 緊跟多位元組字的 unbound 歸因寫反了，實測是 UTF-8 locale 下舊 bash（macOS 3.2）的多位元組解析 bug、不是「非 UTF-8 locale」；`${var}` 免疫跟版本/locale 無關
**Version**: 1.15.2 — install-and-verify 的 SUDO shim 段補兩個「別硬編你這台剛好有的東西」可攜陷阱：GNU coreutils 工具在 macOS 缺席（timeout → gtimeout / 偵測擇一）、`$var` 緊跟多位元組字被吞 byte 報 unbound（改 `${var}`；locale 歸因見 1.4.1 修正）；都是實跑驗證器（validate.sh）自己爆出來的
**Version**: 1.15.1 — install-and-verify 補三條容器實測缺口：root 容器無 sudo 的偵測 shim（`SUDO=sudo; [ root ] && SUDO=""`）、partial upgrade 的 `exists in filesystem` 臉、pacman 7 Landlock sandbox 容器內失敗（DisableSandbox）；read-authoritative-state 原則卡補「你的 verify 腳本也是會讀錯層的眼睛」（stow 摺疊假陰性、`-ef` vs `-L`）
**Version**: 1.15.0 — 第零步 + install-and-verify 補 apt/dpkg 失敗判讀（實測 Debian bookworm 容器裝 dotfile）：`Unable to locate` 三種可能（名字不同 / 沒打包退 GitHub releases / 打錯）、批次交易一個爛名字全滅（`-s` 模擬定位）、dpkg lock + 半裝復原（`dpkg --configure -a` + `--fix-broken`）、EOL 的 archive.debian.org 404、node/python 拉進整個語言生態該走 version manager；SKILL 第零步加 apt 解析階段判讀 + 路由
**Version**: 1.14.0 — 監控段補「本地訂閱」：ntfy 訂閱也是 HTTP GET（curl -sN /json 零安裝 / 瀏覽器 / ntfy subscribe），桌面通知常駐 = user systemd 服務跑 curl /json | jq | notify-send；放盯著的工作機訂遠端、別放被監控機自己（循環）
**Version**: 1.13.0 — 監控升為「主動建議」：裝新系統 / 反覆除服務失敗時先確認有無服務監控（`systemctl show sshd -p OnFailure`），沒有就分層推薦——預設最簡單（OnFailure + ntfy 公共站零 daemon、遠端至少掛 sshd），要更高安全 / 正式再自架 ntfy + 完整堆疊；install-and-verify 加「裝好後確認監控」段
**Version**: 1.12.0 — 監控段補 hung 偵測（外部探針 curl /health 抓進程活著但不回應、補 OnFailure 抓不到的）、canary（可控假服務驗告警管線、不拿真服務冒險）、ntfy topic 安全（公共站無認證、topic 名就是密碼、用長隨機或自架）
**Version**: 1.11.1 — 修正「先重啟才告警」：實測發現 OnFailure 每次失敗都觸發（含 auto-restart 中途、一個重試3次的 crash 觸發4次告警），不是只在放棄時；要只在終局告警需送出腳本 gate `ActiveState != failed` 就 exit（實測加 gate 後 crash 從 4 次降到 1 次）
**Version**: 1.11.0 — process-service-state 補「不想肉眼盯：把失敗變成推播（OnFailure）」（實測驗證告警鏈）：systemd OnFailure 鉤子（alert@ template + 送出腳本 + drop-in）、遞迴陷阱與 `uname -n`（hostname 回空）、`Restart=` 先重啟才告警、體外心跳補「機器當掉 systemd 自己沒了發不出告警」盲點、指標堆疊選型；速查表 + 症狀路由加「服務自動告警」
**Version**: 1.10.0 — process-service-state 補「進程活著 ≠ 內部子系統活著」（實測 Quickshell/caelestia）：GUI shell 進程活著、STAT S 在 poll、CPU 不高，但 QML scene 物件變 null → bar 畫得出來卻點不動、keybind 死、焦點視窗打字正常；`pgrep` 會騙人，權威是程式專屬 log 指令（`<shell> -l`、非 journalctl）+ IPC 回真實狀態（回空=子系統死），修法重啟 shell 重建 scene、驗證看 IPC 不看 pgrep；上游常是 shader/GL pipeline 建失敗
**Version**: 1.9.0 — 音訊無聲判讀（實測 pipewire 缺 wireplumber）：無聲多半不報錯、權威是 `wpctl status` 的 graph——Sinks 空 = session manager 缺件、stream `[active]` = 真在播；「管線通不通」（pw-play 本機音檔）與「應用會不會播」拆開驗證
**Version**: 1.8.0 — process-service-state 補「重啟有沒有真的發生」判讀：kill 指令沒報錯 + 程式在跑 ≠ 重啟成功（app 自帶 kill 子指令可能靜默失敗、新實例偵測舊實例後自行退出）；權威驗證 = 重啟前後比對 `ps -o pid,lstart` 的 pid 與起始時間
**Version**: 1.7.0 — remote-access 補「VT 被 userspace console 接管」case（實測 archboot 預設 kmscon）：登入後 `tty` 回 pts/N 即中、chvt 救不了、compositor 與 kmscon 搶 DRM master；換手 = disable kmsconvt@ + start getty@；同時修正 1.5.0「getty disabled」的不完整理解（真因是 kmscon 取代 VT getty）
**Version**: 1.6.1 — remote-access 的 VM 雙輸出注意事項補「判讀自己在哪一側」：`who` 的 pts/ttyS/ttyAMA vs tty<N>、`ls /dev/dri/` 分辨「裝置沒掛」vs「視窗停在序列視圖」
**Version**: 1.6.0 — install-and-verify 套件管理器段補 AUR / 第三方建置失敗判讀（實測 ALARM）：`-bin` 包 libalpm soname skew（改原始碼建置免疫）、python sysconfig 烤入 distcc 路徑（CXX 環境覆寫）、PKGBUILD arch 漏列（--ignorearch）、optdepends 不自動拉的陷阱；pacman 段補 stale db 404
**Version**: 1.5.0 — VT / getty 判讀補「先查再切」順序：chvt 前先 `systemctl is-active/is-enabled getty@tty<N>`（黑畫面表象有三種根因、切過去看只是回到肉眼判讀）；實測 archboot 裝的系統 getty@tty1 是 disabled 需 enable 治本；`tty0` 是現行 VT 別名、實際前景讀 /sys/class/tty/tty0/active
**Version**: 1.4.0 — 新增「第零步：先定平台」：診斷前先以 os-release / uname -m / command -v 建立平台座標；套件名與執行檔名分歧（fd-find/fdfind、batcat、github-cli vs gh）、非互動旗標不對稱（-y vs --noconfirm）、rolling stale-db 404 需 -Syu、ARM 生態縮水——從新 VM 復現驗證的三個非互動 bootstrap finding 萃取
**Version**: 1.3.0 — Round-3 審查修正：補兩類 AI 最高頻情境——權限被拒(EACCES、namei -l 逐層 / MAC / capability)、套件管理器失敗(pacman db lock / keyring 簽章 / partial upgrade)；被 kill/OOM/exit137 判讀；速查表加 kernel(dmesg)/權限/strace 三列；read-logs 加 strace 回退；DNS resolv.conf symlink caveat、sudoers chmod 0440
**Version**: 1.2.1 — Round-2 審查修正：systemd-failed 情境接上入口（速查表 + 症狀路由補「服務 failed / restart loop」，原本加了 section 卻路由不到）
**Version**: 1.2.0 — Round-1 審查修正：`arp -a` 全面改主推 `ip neigh`（現代最小系統無 net-tools）；新增 DNS 解析、systemd failed 判讀、檔案系統唯讀 remount 三個情境；路由標明 remote→machine 分流；反模式加 scrollback 殘影
**Version**: 1.1.0 — 新增 tool-options reference（依環境 CLI/GUI/遠端挑對工具、現代替代品 vs POSIX 可攜的判斷標準）
**Version**: 1.0.0 — 初版：四步診斷流程 + 權威來源速查 + 5 情境 reference + 2 原則卡，從一次 Arch/Hyprland VM 實機安裝與除錯（含肉眼猜錯兩次的鎖屏案例）萃取
