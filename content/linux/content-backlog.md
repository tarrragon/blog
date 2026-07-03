---
title: "Linux 分類：內容缺口待辦"
date: 2026-07-02
description: "linux 分類經三輪審查後盤點出的內容缺口清單與補完紀錄，寫新內容前先看這張清單避免重工或遺漏"
draft: true
tags: ["linux", "backlog", "meta"]
---

這是 `content/linux/` 分類經三輪多輪審查（2026-07-02）盤點出的內容缺口。`draft: true` 不對外發佈，只做版本控管的待辦清單。下方各項的原始盤點理由保留，狀態標在標題。**清單所列缺口已於 2026-07-02 全部補完**——後續有新缺口往下追加。

## 優先一：缺文章造成的「入口幻覺」（審查標為 SEVERE）— 已補完

`tools/_index` 與 `tools/gui/_index` 的描述承諾了某些主題，但對應文章不存在——讀者看到指路牌、點進去沒有目的地。這兩篇是最高優先。

### 1. 桌面環境選型 — 已補完

- **已建**：`tools/gui/desktop-environment-selection.md`
- **回答**：GNOME / KDE / Hyprland / XFCE / Cinnamon 依「整合度 vs 組裝自由度」軸線選型、各自的資源與客製代價、Wayland/X11 判斷、擴充生態、依情境倒推。已當 `dotfile/06-rice-design` 的上游入口、並在 `gui/_index` 表格與相關段接上。

### 2. 遠端連線與同步工具選型 — 已補完

- **已建**：`tools/remote/connection-and-sync-tools.md`
- **回答**：連線層 `ssh`/`mosh`/`autossh`、網路層 `tailscale`/`wireguard`、同步層 `rsync`/`sshfs`/`mutagen` 三種語義、IDE remote。已在 `remote/_index` 兌現「連線與同步」承諾。

## 優先二：安裝期故障排除（blog 缺、skill 已補）— 已補完

### 3. 安裝期 pacman / DNS / mirror / keyring 故障排除 — 已補完

- **已建**：`install/package-and-network-troubleshooting.md`（主線 weight 4）
- **回答**：第一步分「連不到（DNS/mirror）」vs「連得到但被拒（db lock/簽章/partial/stale 404）」，每種的徵兆、根因、修法。與 skill 側 `install-and-verify` 的套件管理器失敗段對照。

## 優先三：DRY 與生態完整性（審查建議層）— 已補完

### 4. compositor / 合成器 知識卡 — 已補完

- **已建**：`dotfile/knowledge-cards/compositor.md`，_index 系統概念表加入，K4 雙向連結（tty / session-lock / wayland-explainer）。
- **刻意保留**：各 debug 篇的 inline gloss 是 Round 2 為冷讀者刻意加的、**未塌縮成純連結**——冷讀者落單篇仍需一行定義。卡片作為 SSoT 存在、gloss 作為冷讀自足並存，兩者不衝突。

### 5. modern-cli 補漏的替代品 — 已補完

- **已補**：`modern-cli-replacements` 加 `procs`(ps) / `ncdu`(du) / `htop`(top) / `delta`+`difftastic`(git diff)；`ncdu` vs `dust`、`htop` vs `btop` 是不同互動模型、加判讀段分清。`jq` / `hyperfine` 屬新類別、按原計畫略。

### 6. gui 檔案管理員補對照 — 已補完

- **已補**：`gui-file-manager-dependencies` 加「為何拿 Nemo 當重代表」（Nautilus/Dolphin 更 canonical）、加純終端機檔案管理員（`yazi`/`lf`/`nnn`）零相依對照。

## 優先四：反向連結（outbound）— 已補完

- `dotfile/03-terminal-ecosystem/multiplexer-tmux-zellij` → `tools/cli` 多工器深度頁 + `remote` 連線同步選型：已加「深入」段。
- `infra/00-infra-mindset` ↔ `linux/install` + `linux/debug/machine-unreachable`：已建跨頂層雙向橋（infra `_index` 跨分類引用、`first-day` 情境表、`install/_index` 交叉引用各補一向）。
- `record/systematic-debugging-methodology` → `linux/debug/diagnosis-read-authoritative-state`：已加「延伸：套用到 Linux 系統除錯」段。

## 補完後的維護提醒

- 補完 1、2 後 `tools/_index` 與 `tools/gui/_index` 的承諾已兌現、「入口幻覺」消除。
- 每補一篇都跑過 `mdtools cards`（0 broken）、`fmt --fix`、emoji 掃描。
- 未來新增文章：`content/` 下 leaf 頁的 sibling 連結要加 `../` 前綴、跨 section 再多一層（bundle 式解析），這是本輪反覆踩到的陷阱。

## 第二輪多輪審查（2026-07-03）盤出的新缺口 — 已補完（第 10 項暫記除外）

這批是 linux 樹大量新增/重組後、第二次三輪審查（Round 3 steelman / outbound / persona）盤出的缺口，第 7-9 項已於 2026-07-03 補完：

### 7. 「接手一台陌生的、已在跑的機器」缺專屬入口（persona 缺口，SEVERE）— 已補完

- **已建**：`install/inventory-unknown-machine.md`（weight 10）
- **回答**：只讀不改的八層盤點——機器身分、存取面（帳號/sudo/key）、服務與自啟差集、排程落點、開放 port、套件與手放檔案、設定與 secret 落點、監控現況；每層導流既有聚焦篇（process-service-state-diagnosis / service-failure-monitoring / sync-strategy-secret / platform-divergence-map）、收尾以「能否重建」檢驗盤點品質並接 dotfile 收斂與 infra takeover。install/_index 文章表 + 讀法段、debug/_index 讀法段各加路由。

### 8. Quickshell 知識卡（跨 9 檔、達建卡門檻）— 已補完

- **已建**：`knowledge-cards/quickshell.md`（weight 17、_index「語言與工具」表加入）
- **回答**：runtime 與成品的分工（Quickshell 是引擎、Caelestia 是 QML 成品）、quickshell-git 硬需求與只有 Arch 打包、213 MB 足跡來源、兩個除錯陷阱（comm 是 `qs`、畫得出來不等於還活著）、同源架構的連帶故障。K4 雙向：compositor / session-lock 卡加反向連結；六篇術語首現處（caelestia-overview、integrated-shell、desktop-shell-components、process-service-state-diagnosis、platform-divergence-map、common-failures-recovery）連回卡。

### 9. logind / seat 候選卡（中強度）— 已補完（評估結論：新建）

- **評估**：logind 的提及分兩個語意責任——LockedHint 鎖屏層已由 session-lock 卡涵蓋；「session/seat 是誰持有 VT/輸入權」無卡承載。併入 session-lock 會混兩個責任、違反一卡一語意責任，故新建。
- **已建**：`knowledge-cards/logind-session-seat.md`（weight 18、_index 系統概念表加入）
- **回答**：session vs seat 的語意、裝置權發放規則（掛 seat + active VT 才有 DRM/input）、SSH pts 起不了桌面的根因、判讀指令組（tty / seat-status / tty0/active / getty）、loginctl 假象（seat0 掛 pts 看似持有 master）、跟 session-lock 卡的分層銜接。K4 雙向：compositor / session-lock 卡與 debug 三篇首現處接上。

### 10. systemd drop-in / OnFailure 候選卡（中低，暫記）

- **缺口**：`drop-in` 2 檔、`OnFailure` 4 檔，集中在 debug 服務失效篇。devops/04 接上後 `OnFailure` 會變跨模組共用術語，屆時值得建卡；現階段 inline 解釋足夠、暫記。
- **依賴追蹤**：devops/04（服務探活）本身尚未產出，已列入 [devops 分類的內容缺口待辦](/devops/content-backlog/) 順位 1，該模組完成時一併回收本項。
