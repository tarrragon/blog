# linux-install-debug 版本紀錄

新到舊。版號規則與兩個住址（本檔與 `SKILL.md` frontmatter 的 `metadata.version`）見專案的 skill 同步規範。

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
