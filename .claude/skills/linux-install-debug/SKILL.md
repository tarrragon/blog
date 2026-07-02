# Linux Install & Debug

安裝一台新 Linux、或診斷 Linux 系統問題時的標準化診斷協議。核心是一條紀律：**讀權威狀態，不靠肉眼猜表象**。給 AI 快速判斷「出了什麼錯、該做哪些測試」，避免看畫面 / 看症狀就下結論而猜錯。

## 何時啟動

- 安裝新的 Linux 系統（VM 或實機）、需要標準化的安裝 + 首次開機驗證流程
- 遠端（SSH）或本地除錯 Linux：連不上、終端機異常、程式行為不對、服務怪怪的、狀態判不準
- 任何「這現象看起來像 A，但要確認是不是 B」的判斷 — 先讀權威狀態再下結論

## 最高紀律：讀權威狀態，不靠肉眼猜

**表象會騙人。** 畫面上的現象、終端機捲過的輸出、一個視窗長什麼樣，都是表象；能定案的是系統裡記錄這件事的權威來源 — 程式自己的 log、服務註冊表、核心 / systemd 的狀態、資源用量。

實測反例（真實踩過）：一個桌面 shell 的除錯裡，畫面出現密碼框 → 判「鎖了」；接著 `loginctl` 沒 `LockedHint`、`pgrep` 找不到鎖屏程式 → 「更正」成「不是鎖」；兩個判斷都錯。讀那個 shell 自己的 log 才定案：它是走合成器層協議的真鎖，`loginctl`（logind 層）本來就查不到、鎖屏由主程式行程內畫所以沒獨立 process。**肉眼加讀錯層，猜錯兩次；讀對權威來源，一次定案。**

詳見 [讀權威狀態不靠肉眼](references/principles/read-authoritative-state-not-eyeball.md) 與 [讀程式自己的 log](references/principles/read-the-programs-own-log.md)。

## 第零步：先定平台（診斷與修法都是平台相依的）

判讀工具、套件名、修法都因平台 / 發行版 / 架構而異——把 A 平台的經驗直接套到 B 平台，是「工具行為不對」類誤判的常見根因。開始查之前先用三條指令建立座標：

```bash
cat /etc/os-release        # 發行版與版本（Linux）；macOS 用 sw_vers
uname -m                   # CPU 架構：x86_64 / aarch64 — ARM 的套件生態明顯較小
command -v pacman apt-get dnf brew   # 哪個套件管理器在場
```

平台定了之後，這些差異才有判讀基準：

- **套件名與執行檔名分歧**：`fd`（Arch）= `fd-find`（Debian，執行檔 `fdfind`）；`bat` 在 Debian 執行檔叫 `batcat`；`github-cli`（Arch）= `gh`（Debian/Fedora）。「command not found」先確認是沒裝、還是這個發行版叫別的名字。
- **非互動旗標不對稱**：apt 用 `-y`、pacman 用 `--noconfirm`。非 TTY（SSH 一行式、CI、無人值守）下缺對應旗標會卡在 `[Y/n]` 直接失敗。
- **rolling vs stable 的資料庫時序**：Arch 鏡像不保留舊版檔案，stale db 會 404（`failed retrieving file`），修法是先 `pacman -Syu`（只 `-Sy` 不 `-u` 造成 partial upgrade）；Debian stable 無此時序問題、但版本舊，config 語法可能對不上新版文件。
- **工具在不在**：`arp` 常沒裝（用 `ip neigh`）、最小系統連 `sudo` 都沒有；ARM 上 AUR 部分套件不支援、Homebrew on Linux 無 aarch64 bottle。

## 四步診斷流程（每次都跑）

1. **描述症狀**：現象是什麼，別在這步下結論（「畫面出現密碼框」，不是「鎖了」）。
2. **定位權威來源**：這件事的權威狀態記在哪（用下表對照）。
3. **用對工具讀它**：讀權威來源，不是讀畫面 / 終端機殘影。
4. **權威跟表象矛盾時信權威**：矛盾點通常就是原本會猜錯的地方。

## 權威來源速查表

| 症狀類別                              | 權威來源                       | 工具                                                                                        |
| ------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------- |
| 某程式行為不對                        | 程式自己的 log 檔              | log 路徑、`journalctl -u <unit>`                                                            |
| 服務由誰提供                          | D-Bus name / socket 註冊       | `busctl`、`ss -lntp`、`lsof`                                                                |
| 登入 / 鎖定狀態                       | logind                         | `loginctl show-session <id>`                                                                |
| 服務跑了沒 / failed                   | systemd unit                   | `systemctl status` / `is-active` / `is-failed`、`list-units --failed`、`journalctl -u`      |
| 程式活著沒                            | 行程表（比對正確 comm）        | `pgrep -x`、`pgrep -af`、`ps`                                                               |
| 網路通不通                            | 介面 / 路由 / 鄰居表           | `ip -brief a`、`ip neigh`、`ss`（`arp` 常沒裝）                                             |
| 域名解析                              | resolver 設定                  | `getent hosts <域名>`、`/etc/resolv.conf`、`resolvectl`                                     |
| 磁碟 / 記憶體                         | 檔案系統 / 記憶體用量          | `df -h`、`du -sh`、`free`、`mount \| grep -w ro`                                            |
| 核心 / 硬體 / 被殺行程(OOM、exit 137) | kernel ring buffer             | `dmesg`、`journalctl -k -b`                                                                 |
| 權限被拒(EACCES)                      | 檔案 mode/owner、路徑逐層、MAC | `namei -l <path>`、`stat`、`id`、`sudo -l`、`getcap`、`ausearch`(SELinux)                   |
| 程式 log 沉默、不知哪個 syscall 失敗  | syscall 層                     | `strace -f -e trace=file <cmd>`                                                             |
| VT / 主控台（黑畫面 / 沒登入提示）    | getty 狀態（**chvt 前先查**）  | `systemctl is-active/is-enabled getty@tty<N>` → 再 `chvt`；`cat /sys/class/tty/tty0/active` |

## 症狀 → 情境路由

- **安裝新系統 / 首次開機驗證** → [install-and-verify](references/install-and-verify.md)
- **SSH 連不上（先做 timeout vs refused 分流）、終端機噴亂碼 / 亂碼輸入、要從 SSH 操控圖形桌面** → [remote-access](references/remote-access.md)
- **（從 remote-access 分流後）機器沒回應、域名解析不了、虛擬機開不起來、疑似磁碟滿 / 檔案系統唯讀連鎖** → [machine-unreachable](references/machine-unreachable.md)
- **判程式活著沒 / 服務歸誰 / 服務 failed 或一直重啟(restart loop) / 鎖沒鎖 / session 存活 / 卡住是資源還是相容** → [process-service-state](references/process-service-state.md)
- **權限被拒（Permission denied / EACCES / Operation not permitted / sudo 後冒 root-owned 檔）** → [process-service-state](references/process-service-state.md) 的權限段
- **套件管理器失敗（pacman db lock / keyring 簽章過期 / partial upgrade / mirror）** → [install-and-verify](references/install-and-verify.md) 的套件管理器段
- **要讀某程式的 log 定位根因** → [read-logs](references/read-logs.md)
- **要挑 / 推薦工具（同一件事有多個選擇：grep vs ripgrep、哪個檔案管理員、遠端用什麼）** → [tool-options](references/tool-options.md)

## 反模式

- **看畫面就下結論**：畫面有密碼框 ≠ 鎖了；通知沒跳 ≠ 服務沒接管；build 停住 ≠ 不相容。一律回權威來源確認。
- **讀錯層**：Wayland 合成器層的鎖用 logind 的 `LockedHint` 查（查錯層）；用猜的 process 名 `pgrep`（查詢條件錯）。權威來源對、但問錯地方，一樣誤導。
- **急著下昂貴結論**：跳到「不相容 / 要重裝」前，先用最廉價的檢查（`df -h`、資源、資源在不在）排除。
- **一直重試同一個失敗動作**：連不上就一直重連，不去讀網路 / 服務 / 資源的權威狀態。
- **信終端機 scrollback 殘影**：拿捲過的舊輸出當現況。權威狀態是「現在再查一次」的結果，不是畫面上留著的上一次。

---

**Version**: 1.7.0 — remote-access 補「VT 被 userspace console 接管」case（實測 archboot 預設 kmscon）：登入後 `tty` 回 pts/N 即中、chvt 救不了、compositor 與 kmscon 搶 DRM master；換手 = disable kmsconvt@ + start getty@；同時修正 1.5.0「getty disabled」的不完整理解（真因是 kmscon 取代 VT getty）
**Version**: 1.6.1 — remote-access 的 VM 雙輸出注意事項補「判讀自己在哪一側」：`who` 的 pts/ttyS/ttyAMA vs tty<N>、`ls /dev/dri/` 分辨「裝置沒掛」vs「視窗停在序列視圖」
**Version**: 1.6.0 — install-and-verify 套件管理器段補 AUR / 第三方建置失敗判讀（實測 ALARM）：`-bin` 包 libalpm soname skew（改原始碼建置免疫）、python sysconfig 烤入 distcc 路徑（CXX 環境覆寫）、PKGBUILD arch 漏列（--ignorearch）、optdepends 不自動拉的陷阱；pacman 段補 stale db 404
**Version**: 1.5.0 — VT / getty 判讀補「先查再切」順序：chvt 前先 `systemctl is-active/is-enabled getty@tty<N>`（黑畫面表象有三種根因、切過去看只是回到肉眼判讀）；實測 archboot 裝的系統 getty@tty1 是 disabled 需 enable 治本；`tty0` 是現行 VT 別名、實際前景讀 /sys/class/tty/tty0/active
**Version**: 1.4.0 — 新增「第零步：先定平台」：診斷前先以 os-release / uname -m / command -v 建立平台座標；套件名與執行檔名分歧（fd-find/fdfind、batcat、github-cli vs gh）、非互動旗標不對稱（-y vs --noconfirm）、rolling stale-db 404 需 -Syu、ARM 生態縮水——從新 VM 復現驗證的三個非互動 bootstrap finding 萃取
**Version**: 1.3.0 — Round-3 審查修正：補兩類 AI 最高頻情境——權限被拒(EACCES、namei -l 逐層 / MAC / capability)、套件管理器失敗(pacman db lock / keyring 簽章 / partial upgrade)；被 kill/OOM/exit137 判讀；速查表加 kernel(dmesg)/權限/strace 三列；read-logs 加 strace 回退；DNS resolv.conf symlink caveat、sudoers chmod 0440
**Version**: 1.2.1 — Round-2 審查修正：systemd-failed 情境接上入口（速查表 + 症狀路由補「服務 failed / restart loop」，原本加了 section 卻路由不到）
**Version**: 1.2.0 — Round-1 審查修正：`arp -a` 全面改主推 `ip neigh`（現代最小系統無 net-tools）；新增 DNS 解析、systemd failed 判讀、檔案系統唯讀 remount 三個情境；路由標明 remote→machine 分流；反模式加 scrollback 殘影
**Version**: 1.1.0 — 新增 tool-options reference（依環境 CLI/GUI/遠端挑對工具、現代替代品 vs POSIX 可攜的判準）
**Version**: 1.0.0 — 初版：四步診斷流程 + 權威來源速查 + 5 情境 reference + 2 原則卡，從一次 Arch/Hyprland VM 實機安裝與除錯（含肉眼猜錯兩次的鎖屏案例）萃取
