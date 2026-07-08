---
title: "Linux 分類：內容缺口待辦"
date: 2026-07-02
description: "linux 分類經多輪審查後盤點出的內容缺口清單，寫新內容前先看這張清單避免重工或遺漏"
draft: true
tags: ["linux", "backlog", "meta"]
---

這是 `content/linux/` 分類經多輪審查盤點出的內容缺口。`draft: true` 不對外發佈，只做版本控管的待辦清單。已完成項目直接從清單移除（完成紀錄看 git history）；本檔只留未完成項，後續有新缺口往下追加。

目前狀態：第一輪（2026-07-02）六項、第二輪（2026-07-03）第 7-9 項、#10（systemd 卡）、#13 主體（agent 工作機 handson 實機驗證 + 發佈）、#14（基礎知識卡缺口、7 張卡 2026-07-08 全數建立、落點沿用 `dotfile/knowledge-cards/`）均已完成。現存未完成：#11（gui 檔案管理員實機驗證債）、#12（真實機器儲存規劃候選篇）、#13 剩餘（client 選型文的 Blink / iOS 側實測、選型文隔離段 retrospective）。

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

### 13. 遠端 agent 工作機 session 衍生文章缺口的剩餘項

實作記錄 [agent-workstation-vm-handson](/linux/tools/remote/agent-workstation-vm-handson/) 十步驟 + 三情境已於 2026-07-08 全實機驗證發佈；同 session 衍生的手機 client 選型文、[Tailscale 專文](/linux/tools/remote/tailscale-tailnet-and-relay/)、[Claude Code 專文](/linux/tools/remote/claude-code-container-and-hooks/)、[pacman gotcha work-log](/work-log/pacman_syu_kernel_reboot_docker/) 亦已發佈。剩餘兩項：

- **client 選型文的 Blink / iOS 側實測**：[mobile-terminal-client-selection](/linux/tools/remote/mobile-terminal-client-selection/) 已發佈，Termius / Android 側實測完（mosh 可用、擴充鍵列、CJK 用 SSH 非 mosh），但 Blink / iOS 側仍標「需實測」。待有 iOS 裝置驗 Blink 後回填結論。
- **選型文隔離段 retrospective**：`setup-token` 是長效 token 的 env-var 注入模型、非「持久化 OAuth session 到 volume」——[選型文](/linux/tools/remote/agent-workstation-home-vs-vps/)隔離段講「狀態要顯式持久化」時把憑證與設定混講、該細化成「設定走 volume 持久化、認證走 runtime 注入的 secret」兩條分開。handson Step 7 與 Claude Code 專文已把機制講清、待回寫選型文隔離段對齊。

## 維護提醒

- 每補一篇都跑 `./bin/mdtools cards content/`（0 broken）、`fmt --fix`、emoji 掃描。
- 新增文章時注意：`content/` 下 leaf 頁的 sibling 連結要加 `../` 前綴、跨 section 再多一層（bundle 式解析），這是前兩輪反覆踩到的陷阱。
- 知識卡建卡後記得三件套：`knowledge-cards/_index.md` 表格加入、K4 鄰卡雙向連結、各篇術語首現處連回卡。
