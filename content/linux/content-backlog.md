---
title: "Linux 分類：內容缺口待辦"
date: 2026-07-02
description: "linux 分類經多輪審查後盤點出的內容缺口清單，寫新內容前先看這張清單避免重工或遺漏"
draft: true
tags: ["linux", "backlog", "meta"]
---

這是 `content/linux/` 分類經多輪審查盤點出的內容缺口。`draft: true` 不對外發佈，只做版本控管的待辦清單。已完成項目直接從清單移除（完成紀錄看 git history）；本檔只留未完成項，後續有新缺口往下追加。

目前狀態：第一輪（2026-07-02）六項與第二輪（2026-07-03）第 7-9 項均已補完並移除。現存三項：一個依賴 devops 產出的暫記項（#10）、一個等 VM session 的驗證債（#11）、一個等實作需求的候選篇（#12）。

## 待辦

### 10. systemd drop-in / OnFailure 卡 — 已完成（2026-07-03）

- **產出**：建 [systemd OnFailure](/linux/dotfile/knowledge-cards/systemd-onfailure/) 與 [systemd drop-in](/linux/dotfile/knowledge-cards/systemd-drop-in/) 兩張卡（依原子卡判準拆兩張：OnFailure 是失敗觸發鉤子、drop-in 是設定疊加機制）。已加進 knowledge-cards `_index` 系統概念表、並在 debug 服務失效篇與 devops/04 systemd-watchdog-restart 的術語首現處雙向連結。
- **觸發回收**：devops/04（服務探活）已完成，`OnFailure` 成跨模組共用術語，本項一併回收。

### 11. gui 檔案管理員的實機驗證債（待驗證、需 VM session）

- **缺口**：[gui-file-manager-dependencies](/linux/tools/gui/gui-file-manager-dependencies/) 的「待實機驗證清單」段有四項行為驗證未做：Thunar + gvfs + tumbler 的側欄與縮圖行為、三種檔案管理員在裸 Hyprland（XWayland vs 原生 / portal 有無）的差異、Nemo 脫離 Cinnamon 的功能缺損範圍、加進 `packages-arch.txt` 後 bootstrap 一鍵安裝的落地結果。文內已依規範標 caveat（相依數量是實測值、行為未驗）。
- **補法**：下次開 VM session 時逐項驗證、把清單段換成實測結果；驗證結果若推翻文內推測要同步修正文。

### 12. 真實機器儲存規劃（LVM / LUKS / btrfs 快照）候選篇（低優先、暫記）

- **缺口**：[Linux 安裝選項判讀](/linux/install/install-option-decisions/) 兩處明寫手動分割（LVM / LUKS）與 btrfs 快照「是真實機器的儲存規劃主題、值得另外深入」；vm-handson record 的分割關卡段同一判斷。目前 install 系列只覆蓋「演練 VM 該怎麼選」、真實主力機與伺服器的儲存規劃（加密、快照回滾、分區佈局演進）沒有落點。
- **補法候選**：install 系列加一篇「真實機器的儲存規劃」或獨立小模組；需要實機或 VM 演練支撐（LUKS / btrfs 快照都要實測），成本高、等有對應實作需求時再開。

### 13. 遠端 agent 工作機：手機工作流的實機驗證債（進行中、VM 側已驗完、剩手機端）

- **缺口**：[遠端 agent 工作機選型](/linux/tools/remote/agent-workstation-home-vs-vps/) 的決策文已寫，實作記錄 `content/linux/tools/remote/agent-workstation-vm-handson.md`（`draft: true`）在 2026-07-08 VM session 已把 **Step 1-8（VM / 伺服器側全部）實機跑通並回填**：盤點、SSH、mosh 安裝、zellij 斷線重連（18 ticks 連續）、docker image（990MB、掛載隔離、OOM exit 137）、Claude Code 憑證（setup-token）、ntfy hook 觸發手機收訊。**剩 Step 4 漫遊 / Step 9 手機 client / Step 10 三情境**未驗、都需手機端 + 手機上 tailnet。
- **補法**：手機端 session 跑通後回填 Step 9/10 的「待實測補」（`rg "待實測補" content/linux/tools/remote/agent-workstation-vm-handson.md` 掃殘留）；全部回填 + 三情境通過後移除 draft、加進 tools/remote/_index 與決策文路由。
- **實測推翻選型文的 retrospective 候選**：`claude setup-token` 產生的是**長效 token（env-var 注入模型）**、不是「持久化 OAuth session 到 `~/.claude` volume」——原骨架與選型文隱含的持久化模型被推翻、已改寫 Step 7。這個「認證走 env-var secret 注入、設定走 volume 持久化」的分離，值得評估是否回寫選型文的隔離段（目前隔離段講「狀態要顯式持久化」時把憑證跟設定混在一起講）。
- **連帶工具專文缺口進度**：
  - 手機終端 client 選型：**已起草** `content/linux/tools/remote/mobile-terminal-client-selection.md`（`draft: true`、Blink vs Termius vs ttyd、工具能力宣稱標「需實測」）。待手機實測 Termius/Blink 的 mosh 支援後回填結論、移除 draft、加進 _index。
  - Claude Code 安裝與 hooks 配置：仍缺專文，但實作記錄 Step 6-8 已累積具體素材（npm 全域安裝、`setup-token` env-var 模型、Stop hook + ntfy、`--dangerously-skip-permissions` 在 container 邊界即權限邊界下的定位、`.claude.json` 不在 volume 的持久化邊界）。
  - Tailscale 專文：仍只有 connection-and-sync-tools 段落級；實作記錄 Step 3 新增「UTM NAT 下退 DERP 中繼」實例。
- **新發現的 work-log 候選**（跨工具 gotcha 鏈、非 agent 工作機專屬）：`pacman -S` 對相依套件回 404（本地 DB 過時 / partial upgrade 陷阱）→ 修法 `-Syu` 順帶升 kernel → 未重開機導致 docker daemon 因 `nf_tables` 模組載入失敗而起不來（症狀在 iptables、根因在執行中 kernel 與磁碟 module 版本錯配）。這條「一個修法埋下三步後才引爆的伏筆」是 work-log 的好素材、判讀用「讀權威狀態 `uname -r` vs `ls /usr/lib/modules`」。目前只寫進實作記錄的除錯判讀段、可評估抽成獨立 work-log。

## 維護提醒

- 每補一篇都跑 `./bin/mdtools cards content/`（0 broken）、`fmt --fix`、emoji 掃描。
- 新增文章時注意：`content/` 下 leaf 頁的 sibling 連結要加 `../` 前綴、跨 section 再多一層（bundle 式解析），這是前兩輪反覆踩到的陷阱。
- 知識卡建卡後記得三件套：`knowledge-cards/_index.md` 表格加入、K4 鄰卡雙向連結、各篇術語首現處連回卡。
