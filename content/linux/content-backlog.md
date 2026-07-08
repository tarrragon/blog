---
title: "Linux 分類：內容缺口待辦"
date: 2026-07-02
description: "linux 分類經多輪審查後盤點出的內容缺口清單，寫新內容前先看這張清單避免重工或遺漏"
draft: true
tags: ["linux", "backlog", "meta"]
---

這是 `content/linux/` 分類經多輪審查盤點出的內容缺口。`draft: true` 不對外發佈，只做版本控管的待辦清單。已完成項目直接從清單移除（完成紀錄看 git history）；本檔只留未完成項，後續有新缺口往下追加。

目前狀態：第一輪（2026-07-02）六項、第二輪（2026-07-03）第 7-9 項、#10（systemd 卡）、#13 主體（agent 工作機 handson 實機驗證 + 發佈）均已完成。現存未完成：#11（gui 檔案管理員實機驗證債）、#12（真實機器儲存規劃候選篇）、#13（agent 工作機 session 衍生的**文章**缺口：client 選型文發佈、Tailscale / Claude Code 專文、gotcha work-log、選型文 retrospective）、#14（agent session 揭露的基礎知識**卡**缺口 + article/card 評估）。

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

### 13. 遠端 agent 工作機 session 衍生的文章缺口（handson 已發佈、剩衍生專文）

實作記錄 [agent-workstation-vm-handson](/linux/tools/remote/agent-workstation-vm-handson/) 十步驟 + 三情境已於 2026-07-08 全實機驗證、移除 draft 發佈、加進 _index 與選型文路由。剩下從這個 session 衍生的**文章**缺口（知識**卡**缺口見 #14）：

- **手機終端 client 選型文待發佈**：`mobile-terminal-client-selection.md`（`draft: true`）已寫、Termius/Android 側實測完（mosh 可用、擴充鍵列、CJK 用 SSH 非 mosh），但 Blink/iOS 側仍標「需實測」。待有 iOS 裝置驗 Blink、或決定改寫成只談 Termius/Android 後，移除 draft、加進 _index。
- **Tailscale 專文**：仍只有 connection-and-sync-tools 段落級。handson Step 3 已累積素材：`tailscale up` headless auth URL 流程、DERP 中繼 vs 直連（UTM NAT 穿透失敗退中繼、行動網路轉直連）、`tailscale status` 判讀。含知識卡候選「DERP 中繼 vs 直連」（見 #14）。
- **Claude Code 安裝與 hooks 配置專文**：handson Step 6-8 已累積素材（npm 全域安裝、`setup-token` env-var 模型、Stop hook + ntfy、`--dangerously-skip-permissions` 在 container 邊界即權限邊界下的定位、`.claude.json` 不在 volume 的持久化邊界、認證綁 token 注入非 session）。
- **work-log 候選（跨工具 gotcha 鏈）**：`pacman -S` 回 404（本地 DB 過時 / partial upgrade 陷阱）→ `-Syu` 順帶升 kernel → 未重開機導致 docker daemon 因 `nf_tables` 模組載入失敗起不來（症狀在 iptables、根因在執行中 kernel 與磁碟 module 版本錯配）。「一個修法埋下三步後才引爆的伏筆」、判讀用讀權威狀態 `uname -r` vs `ls /usr/lib/modules`。目前只在 handson Step 6 除錯段、可抽成獨立 work-log。
- **選型文隔離段 retrospective**：`setup-token` 是長效 token 的 env-var 注入模型、非「持久化 OAuth session 到 volume」——選型文隔離段講「狀態要顯式持久化」時把憑證與設定混講、該細化成「設定走 volume 持久化、認證走 runtime 注入的 secret」兩條分開。handson Step 7 與文末「完成與後續」已點出、待回寫選型文。

### 14. 遠端 agent session 揭露的基礎知識卡缺口（article vs card 評估）

handson 的每步除錯判讀把具體操作寫清楚了，但底層的**基礎機制**多數只有選型級（connection-and-sync-tools）或散在各步、沒有原子化的知識卡。知識卡系統目前無任何 networking/connection 卡（現有卡都是 infra/dotfile 概念）。逐項評估要成卡還是成文：

| 知識缺口                                       | 現況                                                           | 建議                             | 理由                                                                                                                            |
| ---------------------------------------------- | -------------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| SSH 為何不能漫遊（TCP 綁 4-tuple、換 IP 即斷） | connection-and-sync-tools 說「網路一換就斷」但沒說機制         | **卡**                           | 原子概念、解釋 SSH 限制與 mosh 為何用 UDP 的共同根                                                                              |
| 連線逾時 vs 連線被拒                           | handson Step 3/9 有判讀、未抽通用卡                            | **卡**                           | 跨情境診斷原則（逾時=可達性層、被拒=服務/認證層）、除錯高頻                                                                     |
| mosh 本地回顯預測（機制與 CJK 代價）           | connection-and-sync-tools 提「預測」一句、CJK 衝突只在 handson | **卡 + 擴充**                    | 卡講預測機制；驗證法（server 側 mosh-server 判是否退回 SSH）補進 connection-and-sync-tools                                      |
| SSH 金鑰儲放與模型                             | ssh-keyless-bootstrap 有 bootstrap flow                        | **卡**                           | key 在哪（`~/.ssh`）、`authorized_keys`、per-device key、password fallback、deploy key vs full key 信任邊界——概念散、值得原子卡 |
| Docker named volume 掛載點 owner               | handson Step 6 有寫                                            | **卡**                           | 「空 named volume 首次掛載沿用 image 內該路徑 owner」是通用 docker 陷阱                                                         |
| 機密 runtime 注入 vs 烤進 image/git            | handson Step 7 + dotfiles runtime README 有寫                  | **卡**                           | 「secret 不進 image layer 也不進 repo（連私有）、runtime 注入」原則                                                             |
| 終端 CJK 雙寬字與即時輸入                      | handson Step 10 + client 選型文有寫                            | **卡（低優先）**                 | 雙寬字寬度、終端 raw 模式擋 IME 組字、貼上繞法                                                                                  |
| DERP 中繼 vs 直連（NAT 穿透）                  | handson Step 3 有寫                                            | **併入 Tailscale 專文**（#13）   | 屬 Tailscale 主題、不獨立成卡                                                                                                   |
| 長效 token vs 互動 session 憑證                | handson Step 7 有寫                                            | **併入 Claude Code 專文**（#13） | 屬 Claude Code 認證主題                                                                                                         |

- **待決策**：networking/connection 卡的落點——現有 `dotfile/knowledge-cards/` 都是 infra/dotfile 概念，remote/network 卡要沿用同一個 knowledge-cards 系統、還是在 tools/remote 或 debug 下開新卡區。寫第一張卡前先定。
- **優先序**：診斷類（逾時 vs 被拒、SSH 金鑰儲放）跨情境高頻、優先；CJK / named volume owner 低頻、backlog 尾。

## 維護提醒

- 每補一篇都跑 `./bin/mdtools cards content/`（0 broken）、`fmt --fix`、emoji 掃描。
- 新增文章時注意：`content/` 下 leaf 頁的 sibling 連結要加 `../` 前綴、跨 section 再多一層（bundle 式解析），這是前兩輪反覆踩到的陷阱。
- 知識卡建卡後記得三件套：`knowledge-cards/_index.md` 表格加入、K4 鄰卡雙向連結、各篇術語首現處連回卡。
