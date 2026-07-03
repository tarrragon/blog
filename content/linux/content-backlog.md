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

### 10. systemd drop-in / OnFailure 候選卡（中低，暫記）

- **缺口**：`drop-in` 2 檔、`OnFailure` 4 檔，集中在 debug 服務失效篇。devops/04 接上後 `OnFailure` 會變跨模組共用術語，屆時值得建卡；現階段 inline 解釋足夠、暫記。
- **依賴追蹤**：devops/04（服務探活）本身尚未產出，已列入 [devops 分類的內容缺口待辦](/devops/content-backlog/) 順位 1，該模組完成時一併回收本項。

### 11. gui 檔案管理員的實機驗證債（待驗證、需 VM session）

- **缺口**：[gui-file-manager-dependencies](/linux/tools/gui/gui-file-manager-dependencies/) 的「待實機驗證清單」段有四項行為驗證未做：Thunar + gvfs + tumbler 的側欄與縮圖行為、三種檔案管理員在裸 Hyprland（XWayland vs 原生 / portal 有無）的差異、Nemo 脫離 Cinnamon 的功能缺損範圍、加進 `packages-arch.txt` 後 bootstrap 一鍵安裝的落地結果。文內已依規範標 caveat（相依數量是實測值、行為未驗）。
- **補法**：下次開 VM session 時逐項驗證、把清單段換成實測結果；驗證結果若推翻文內推測要同步修正文。

### 12. 真實機器儲存規劃（LVM / LUKS / btrfs 快照）候選篇（低優先、暫記）

- **缺口**：[Linux 安裝選項判讀](/linux/install/install-option-decisions/) 兩處明寫手動分割（LVM / LUKS）與 btrfs 快照「是真實機器的儲存規劃主題、值得另外深入」；vm-handson record 的分割關卡段同一判斷。目前 install 系列只覆蓋「演練 VM 該怎麼選」、真實主力機與伺服器的儲存規劃（加密、快照回滾、分區佈局演進）沒有落點。
- **補法候選**：install 系列加一篇「真實機器的儲存規劃」或獨立小模組；需要實機或 VM 演練支撐（LUKS / btrfs 快照都要實測），成本高、等有對應實作需求時再開。

## 維護提醒

- 每補一篇都跑 `./bin/mdtools cards content/`（0 broken）、`fmt --fix`、emoji 掃描。
- 新增文章時注意：`content/` 下 leaf 頁的 sibling 連結要加 `../` 前綴、跨 section 再多一層（bundle 式解析），這是前兩輪反覆踩到的陷阱。
- 知識卡建卡後記得三件套：`knowledge-cards/_index.md` 表格加入、K4 鄰卡雙向連結、各篇術語首現處連回卡。
