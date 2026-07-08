---
title: "手機終端 client 選型：連遠端 agent 工作機該用哪個"
date: 2026-07-08
description: "要從手機連一台遠端 agent 工作機、在 Blink / Termius / 自製通道之間挑一個能撐住 mosh 漫遊與擴充鍵列的終端 client 時回來讀"
weight: 4
tags: ["linux", "remote", "mosh", "tailscale", "mobile", "terminal", "agent"]
---

手機終端 client 是遠端 agent 工作機「行動端輸入可用」這個成立條件的落點。[遠端 agent 工作機選型](../agent-workstation-home-vs-vps/) 列的四個成立條件裡，行動端輸入最容易被漏掉也最容易用不下去：手機軟體鍵盤預設沒有 Esc / Ctrl / 方向鍵，而終端 UI（zellij、Claude Code 這類 TUI）重度依賴這些按鍵。client 選對，手機端是「可操作」；選錯，手機端「只能看」。這篇把 client 的選型判準立在使用形態上、而不是功能總數，並比較兩個現成 client（Blink Shell、Termius）與一條自製路徑（ttyd）。

本篇的工具能力宣稱多數標「需實測」：終端 client 的 mosh 支援、擴充鍵列完整度、定價分層在版本間反覆變動，隔著版本差異用舊資訊斷言會誤導。標「需實測」的項目要在你當前裝置的當前版本上跑過才下結論——這對齊本站工具文章的驗證導向原則。

## 選型判準回到使用形態，不是功能總數

client 的功能表很長，但對「單一遠端 agent 工作機」這個場景，真正決定去留的維度只有三個，其餘多是邊際效益低的加分項。先把判準收斂：

| 判準      | 為何對這個場景是核心                           | 判讀訊號                                   |
| --------- | ---------------------------------------------- | ------------------------------------------ |
| mosh 漫遊 | 手機切網路（Wi-Fi↔行動網路）、app 進背景不斷線 | 切網後 session 存活、免重連                |
| 擴充鍵列  | TUI 依賴 Esc / Ctrl / 方向 / Tab、軟體鍵盤沒有 | 中斷得了 agent、翻得了歷史、切得了模式     |
| TUI 相容  | zellij / Claude Code 的畫面不能錯位亂碼        | 終端模擬正確（xterm-256color）、CJK 不斷行 |

mosh 漫遊是這三個裡的第一順位，因為它是 [連線層選型](../connection-and-sync-tools/) 把 mosh 放進技術棧的唯一理由。手機的網路狀態本來就在漂移——走出 Wi-Fi 範圍、app 被系統凍結、地鐵進出隧道——mosh 的 UDP 漫遊（TCP 為何一換 IP 就斷、見 [TCP 連線漫遊](/linux/dotfile/knowledge-cards/tcp-connection-roaming/)）與本地回顯預測（[mosh 本地回顯預測](/linux/dotfile/knowledge-cards/mosh-local-echo-prediction/)）就是為這個設計。client 若不支援 mosh、只能退回純 SSH，斷線復原（[實作記錄](../agent-workstation-vm-handson/) 的 Step 10 情境二）就從「無感漫遊」降級成「重連再 attach」，體感差一個等級。

相對地，一組常被拿來比較的維度對這個場景邊際效益低：**多 host 圖形化管理、金鑰雲端同步**。這些在你要管理幾十台伺服器時很有用，但 agent 工作機的形態是「連一台常駐 VM」——host 只有一個、金鑰配一次，圖形化管理省下的工趨近於零。選型被這類維度帶走，就會挑到「管理很多台很方便、但漫遊撐不住」的錯位工具。

## 平台先卡掉一半候選

比較功能之前，手機的作業系統先劃掉一部分選項：**Blink Shell 是 iOS / iPadOS 專屬、Android 上裝不了**。所以這組比較只在 iOS 上是「Blink vs Termius」的雙選；Android 上 Blink 直接出局、現成 client 收斂到 Termius（Android 上有 mosh 支援的成熟終端本來就少）。平台可用性是選型的第一刀、排在功能多寡之前——在 Android 手機上，「Blink 的 mosh 比較好」這個結論兌現不了，因為根本裝不上。本篇的實測就發生在一台 Android（Galaxy A70）上，因此候選實質只有 Termius。

## Blink Shell vs Termius（iOS 上的雙選）

兩個 client 的定位差異可以一句話抓：Blink Shell 是 mosh-first 的終端、Termius 是多 host 管理優先的 SSH client。這個定位差異直接投射到上一段的判準上（前提是在 iOS 上、兩者都能裝）。

| 維度               | Blink Shell                                            | Termius                                                                            |
| ------------------ | ------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| mosh 支援          | 原生內建、設計核心（需實測當前版本）                   | 本輪 Android 實測可用、未見 Pro 提示（單次結果、版本間曾變動、仍需以你的版本為準） |
| 漫遊 / 斷線重連    | mosh 原生、切網無感（需實測）                          | mosh 生效時實測切網無感（見下）；未生效退純 SSH 則是重連非漫遊                     |
| 擴充鍵列           | 鍵盤導向、擴充鍵列完整、對實體鍵盤友善（需實測完整度） | 有可自訂鍵列、UI 直覺（需實測完整度）                                              |
| 多 host / 金鑰管理 | 偏設定檔式（host 檔、config）                          | 圖形化多 host + 金鑰雲端同步                                                       |
| TUI 相容           | xterm-256color、TUI 表現佳（需實測）                   | 一般情況可用（需實測）                                                             |
| 定價               | 付費（訂閱制、需實測當前方案）                         | Freemium：基礎免費、進階功能在 Termius Pro（需實測 mosh 落在哪層）                 |

**mosh 支援是決定性差異、也是最需要實測的一格。** Blink Shell 歷來把 mosh 當一等公民，漫遊是它的招牌能力；Termius 的 mosh 支援則在不同版本間出現、下架、綁進 Pro 訂閱，狀態不穩定。本輪在一台 Android（Galaxy A70）上實測：Termius 開 mosh、未見任何 Pro 或付費提示、切 Wi-Fi 到行動網路後畫面凍約 3 秒、恢復後輸出一格不少（tailscale 重建路徑加 mosh 重新同步的時間）——這一版可用。它的價值是「不丟狀態、自動接回」、不是「零延遲」，描述時別把它說成感覺不到切換。這是單次結果、不保證跨版本跨平台成立，仍要在你的裝置上自驗。

驗證有個容易被 client 端顯示誤導的地方：client 說「已連線」不等於「用了 mosh」，要從 server 側查。mosh 生效時 VM 上有 `mosh-server` 程序、SSH 連線在 spawn 完就關閉（`ss -tnp` 看不到該 client 的 TCP:22）；只看到 SSH 連線、沒有 `mosh-server`，就是退回了純 SSH。而且狀態會變——本輪第一條連線的快照是純 SSH、重連後 mosh 才接管，所以不能只查一次。若 mosh 在你的版本上真的不可用或要付費而你不想付，這個 client 對這個場景的核心價值就少了一塊。

**擴充鍵列兩者都有、差在完整度與手感。** Blink 從設計上就服務重度鍵盤使用者，擴充鍵列與實體鍵盤映射完整；Termius 的鍵列可自訂、圖形化調整直覺。這一格的判讀落在「夠不夠用」、不在「有沒有」：實測時走一遍 agent 操作——`Esc` 中斷一次生成、方向鍵翻 zellij 歷史、`Ctrl-C` 送中斷、`Tab` 補全——四個動作都順才算過關。

Termius Android 的實測結果印證了「夠不夠用」要逐鍵走過、而且不能只看第一眼：Tab、Ctrl、方向鍵鍵列都有、可用；Esc 一度以為沒有、實際是**擴充鍵列可以水平捲動、Esc 被推到可見範圍外遮住了**，橫向拖動鍵列就露出來。行動端鍵列常是可捲動的、可見那幾顆不等於全部——判「按鍵缺失」前要先把鍵列拖過一遍。就算真的找不到，終端層還有等價組合鍵：`Ctrl+[` 送出與 Esc 相同的 `0x1b` 控制碼、任何終端等價（實測在 zellij 進 PANE 模式後 `Ctrl+[` 能退回 NORMAL）。判讀原則是：以為缺某個核心鍵時，先捲動鍵列、再用等價組合鍵、再看鍵列能不能自訂，這三條都先於「換 client」。

擴充鍵列之外還有一格常被忽略的輸入限制：**CJK 即時輸入、且它跟 mosh 有顯示衝突**。本輪 Termius Android 實測釐清三層（終端為何預設擋 IME 組字、雙寬字寬度怎麼算，見 [終端 CJK 即時輸入](/linux/dotfile/knowledge-cards/terminal-cjk-input/)）：預設終端不接受 CJK 即時輸入（但中文貼上能送、編碼沒問題）；開了 Termius 的 `Experimental Keyboard Support（CJK layout support）`後能即時打中文；但**開 CJK 後、mosh 連線下中文輸入行會顯示錯位、純 SSH 則正常**。根因是 mosh 的本地回顯預測撞上 CJK 雙寬字元（寬度算錯、游標與重繪錯位），純 SSH 沒預測所以乾淨。這帶出一個選型層的權衡：**要打中文對話用純 SSH（顯示對）、要移動漫遊用 mosh（別打 CJK）**，存兩個 profile 分別服務兩種形態。對要用中文下長指令的使用者、這格權重不低——「能不能打中文」要拆成「能不能貼上」「能不能即時組字」「即時組字跟 mosh 併用會不會亂」三問、各 client 各自實測。

**多 host 管理是 Termius 的長處、但對這個場景用不上。** Termius 的圖形化 host 管理與金鑰同步在管理機群時省事，但 agent 工作機只連一台 VM，這個長處在此場景兌現不出價值。選型判準是「這個場景會不會用到」、不是「功能總數」。

## 測試階段的免費工具約束

工作流本身還在驗證階段時，client 端優先選免費工具、把付費決策延後。這是控制變數的延伸：[實作記錄](../agent-workstation-vm-handson/) 的 Step 9 已經把「本輪用成熟現成 client 歸零變數」定為順序原則，而在成熟工具之內、免費又能滿足核心判準的優先——工作流沒驗通之前，不知道 client 的付費功能是不是真的需要，先付費是把未驗證的假設變成沉沒成本。

實務判讀：先用免費層能跑到多遠。若 Termius 免費層的 SSH + 擴充鍵列已經能完成 attach、下指令、中斷、翻歷史（Step 9 的驗收動作），漫遊那塊暫時用純 SSH 重連頂著、把工作流其他層驗通，再回頭決定 mosh 值不值得付費或換 Blink。反過來，若核心判準（mosh 漫遊）在免費層完全拿不到、而它又是你這個使用形態的硬需求，那付費或換工具就成了這個場景的入場條件、而非可延後的決策——這時要算的是「一年訂閱 vs 漫遊斷線的實際痛感」。

## 候選 B：自製 ttyd 通道

要客製認證與稽核時，路徑從現成 client 換成自建 ttyd 通道。ttyd 把終端包成 WebSocket、走 tailnet、由自製或瀏覽器端收，適合的情境是：連線要過自己的認證層、每個 session 要留稽核記錄、或要嵌進自有的 app。代價是擴充鍵列、斷線重連、TUI 相容這些現成 client 免費附送的能力，全部要自己補齊。

順序上，自製通道的功能對齊（擴充鍵列、斷線重連、多 endpoint、TUI 相容）應該以現成 client 跑通後凍結的判準當驗收規格，而不是一邊開發通道一邊定義「可用」。工作流本身未驗證時、client 端用成熟工具歸零變數；等現成 client 把整套跑通、有了明確的驗收清單，自製通道才有對照基準。這條順序原則的完整推導見 [實作記錄](../agent-workstation-vm-handson/) 的 Step 9。

## 判讀與下一步路由

- client 選型的上游是機器與連線層選型：[遠端 agent 工作機選型](../agent-workstation-home-vs-vps/)、[遠端連線與同步工具選型](../connection-and-sync-tools/)。
- client 跑通後的手機端驗收動作（attach、中斷、翻歷史、漫遊、三情境端到端）：[遠端 agent 工作機實作記錄](../agent-workstation-vm-handson/) 的 Step 9 與 Step 10。
- 手機連線噴亂碼、斷行錯位這類問題是診斷而非選型：[SSH 與終端機問題排查](../../../debug/ssh-and-terminal-troubleshooting/)。
- 本篇工具能力宣稱標「需實測」的項目，結論以本輪實測的裝置（Android / Termius）與版本為準；換裝置、換版本、驗 iOS / Blink 要重新在自己的環境上跑過。
