---
title: "工作筆記"
slug: "work-log"
description: "工作場景觸發的技術紀錄 — git 操作、build 工具、框架行為、環境設定與架構觀念"
tags: ["work-log", "debug", "工具"]
---

這個資料夾收錄**工作場景中遇到、值得記下來的內容** — 觸發時機是工作（debug、設定、討論、學到某個觀念），不限於事故後的解法，也包含工具設定、技術觀念整理、後端設計分析等。

內容大致分三類：

**版控與協作平台** — git rebase / fixup / 移除歷史內容，以及 GitHub 對 commit 內容的解析行為。例：

- [Git：把後面 commit 的部分檔案變更搬到前面的 commit](git_move_partial_change_to_earlier_commit/)
- [Git：修復後面的 commit 意外覆蓋前面 commit 的變更](git_fixup_rebase/)
- [commit message 引用外部 issue 會在對方 repo 留下事件——檔案內容裡的同一串字不會](github-cross-reference-from-commit-message/)
- [停止開發的專案封存：未提交修改、被忽略檔案、倉庫依賴、分支的收斂與遠端搬遷、還原驗證](project_archive_before_cleanup/)

**Build 工具與框架** — Gradle / Flutter / Dart / Node / CSS / Chrome 擴充功能的錯誤、行為、設計觀念與量測，以及介面配色的對比量測。例：

- `gradle_jvm_target_asymmetry` — Kotlin/Java target 不一致導致 build 失敗
- `gradle_evaluation_order_traps` — Gradle configuration phase 時序陷阱
- `flutter_hit_test_behavior` — Flutter widget hit test 行為
- `flutter_repaint_heartbeat` — 畫面落後邏輯狀態（重繪訊號沒進 frame 排程）的排查與心跳做法
- `flutter_schedule_frame` — `scheduleFrame()` 的設計意義：按需 render 的最底層「要一個 frame」原語
- `flutter_audio_volume_control` — per-player 音量 vs 系統音量、為何多數不該從 App 改系統音量
- [量終端機動畫程式的 CPU](terminal-animation-cpu-measurement/) — 用 pty 執行、認出 tsx 實際執行程式的程序、停掉之後檢查殘留、固定種子比較兩個版本，以及百分比不跟著工作量下降的讀法
- [CSS 規則沒生效時的量測與成因：範圍重設的特定性與宿主樣式、container-type 與 subgrid、捲動陰影的覆蓋漸層](css-silent-override-measurement/) — 用計算後的樣式與 DevTools 的 Styles 面板分出規則是沒套上還是輸了，以及展示頁沒載入宿主樣式時怎麼比較
- [狀態色塊配色的對比量測：文字對色塊、色塊對背景、細標記對底色，以及紅綠色覺差異](state-color-contrast-and-color-vision/) — 三道對比各自怎麼算、各自擋下哪個顏色，以及只靠紅綠區分時色覺差異的讀者看到什麼
- [CSS 改用 token 取值的重構與驗證：逐元素比對計算後的樣式、字級分成尺寸階與功能字級（primitive 與 semantic token）、!important 與提高特定性的 id 選擇器的替代寫法](css-token-refactor-verified-by-computed-style-diff/) — 重構前後逐元素比對計算後的樣式並歸類差異（預期內、字串不同而畫面相同、量測時序），字級的兩層 token，改寫選擇器取代 `!important` 與 id 加權、拿掉加權量出它是否還要贏過哪條規則，用檢查腳本擋新的寫死值，grid 子項 `min-width: auto` 的溢出，以及三個元件與 JavaScript 共用 token
- [Chrome 擴充功能提取書目之後書庫頁停在舊資料的排查：逐段計數、頁首總數的解析、轉送層覆蓋欄位寫錯 storage key、舊識別碼對不上而新增重複、修好之後的殘留資料](chrome-extension-library-stale-after-extraction/) — 沿著資料流在每一段取本數找出第一次對不上的位置，轉送層的附註佔用了下游拿來組 key 的欄位名，舊版程式用書名或封面當識別碼而重新提取時對不上，以及修好之後殘留資料的處理

**環境、設定與架構觀念** — 開發環境一次性設定、規則檔維護、與後端協作時整理出的設計觀念等。例：

- [一行查詢放哪、一個測試留不留：結構改動後的兩次「還需要存在嗎」](flutter_query_ownership_and_structurally_immune_test/) — 查詢的責任歸屬（掛回資料擁有者）與被結構免疫掉的贅測
- [規則檔 AGENTS.md 的瘦身紀錄：逼近讀取上限的成因、分冊的按需載入、agent 失敗歸因與修法擴張](agents-md-slimming-and-failure-attribution/) — 規則檔接近工具的讀取上限、越補越長而 agent 仍然犯錯，或修規則時同一段越改越長時，判斷該從大小、載入、規則文字還是動筆前的對齊處理

**硬體與裝置辨識** — 五篇的共同起點是一句話：**裝置的身分要從硬體那一側判定，不從程式那一側推論**。順著它展開的五個問題各成一篇——身分記在哪、判錯身分之後會發生什麼、判錯的設定存進去之後怎麼恢復、篩錯的代價該由誰承擔、以及怎麼取得身分。一批出自同一次 Android POS 一體機的印表機設定排查：

- [USB 類別代碼記在裝置層與介面層兩處，只讀裝置層的印表機會回報 0](usb-class-code-lives-in-two-layers/)
- [claim 一個 USB 介面等於接管它，原本用它的系統功能會停止回應](usb-claim-takes-the-hardware-away/)
- [會在開機自動生效的設定要在讀取端驗證，寫入端的把關救不了已經寫壞的機器](validate-persisted-settings-on-read/)
- [兩種錯法的代價不對稱時，過濾策略要讓失敗倒向可補救的那一邊](filter-strategy-follows-asymmetric-failure-cost/)
- [陌生機器的硬體盤點比從應用端反推便宜，因為它把假設換成可核對的值](inventory-hardware-before-inferring-from-the-app/)

**遠端 Android 實機診斷** — 機器不在手邊、只有一條指令通道時怎麼取值與判讀。上一組把判定的依據從程式的推論換成硬體的值，而機器不在手邊時，連取值這件事本身都要先決定信哪一種輸入：

- [用 adb 遠端診斷 Android 實機](adb-remote-android-diagnosis/)

連線本身（無線偵錯的配對與連接）在 [Android 無線調試連接指南](/other/android_wireless_debug/)，這一組從連上之後開始。

---

## 寫作模板與語域

work-log 的讀者由搜尋或站內路由帶來、自帶問題；文章的職責是讓他最快拿到判斷標準與脈絡。模板四條（原則見 [#254 寫給帶問題來的讀者](/report/write-for-readers-not-audiences/)）：

- **標題寫主旨**：寫這篇處理的對象與交付的內容種類（排查、判讀、機制、取捨），冒號之後寫涵蓋的成員。「X 決定 Y」「X 才是 Y」這類結論句留在正文推導走完的位置：讀者在乎那句結論的理由要由正文建立，而標題是他還沒讀正文時看到的那一行，被別篇當成連結文字時他連這篇的主題都還不知道。問句標題同樣不用，標題是檢索錨，掃標題列表的讀者要從它知道這篇講什麼。寫法與檢查方法見 `docs/rules/writing.md`〈標題與段標寫主旨〉。
- **結構是「情境條件 → 推導與驗證 → 判斷標準」**：開頭把情境講成條件描述——什麼樣的程式、什麼設定、什麼操作會遇到——讓讀者判斷自己在不在射程內；接著讓推導與實測帶著讀者走，判斷標準在推導走完的位置浮現，是讀者讀完推導已經能自己說出的結論。兩個方向都要避免：把判斷標準壓到文末扣住的三幕劇（第一次失敗、第二次失敗、頓悟）是懸念，要壓平成推導；把結論抽成開頭一段要讀者先記住是灌輸，沒有被推導承接的結論只能硬記。標題承載主旨、開頭承載情境、判斷標準由推導交付。
- **視角是客觀條件、不是第一人稱時間線**：檢討的脈絡（做錯了什麼、為什麼錯、為什麼要糾正）用條件語言承載——「reviewer 問了 X、後來才想清楚」寫成「若對這個做法問 X 而答不出來、就該重新檢討」；人物以角色出現（reviewer、修改者）。
- **事件說明寫在開場之前、不建結論摘要欄位組**：內容來自一次實際事件時，在開場之前寫一段事件說明，寫出事件的日期，以及在什麼環境、做什麼操作時發生。它交代來源，不摘要結論。「觸發場景 / 疑問來源 / 整理目的 / 本文邊界」這類文首欄位組把各段結論先摘出來放在推導之前，是灌輸的另一種形態——讀者拿到的是要硬記的摘要，不是可跟的推導。

範例見 [註解防不了改壞](comment_cannot_guard_invariant/)：案例推導帶著讀者走到判斷標準、reviewer 的退件理由呈現為檢視標準。

---

## 跟其他資料夾的邊界

| 議題                                      | 該放                                            |
| ----------------------------------------- | ----------------------------------------------- |
| blog 本身設定（Hugo / mdtools / Mermaid） | `posts/`（不是 work-log）                       |
| 從多個事件抽象的方法論                    | `record/`（中性）或 `report/`（從 case 抽原則） |
| 純 OS / 工具小技巧（不涉及開發專案）      | `other/`                                        |
| 工作場景觸發、想記下來的內容              | **本資料夾**                                    |

判斷流程：是「工作場景觸發、想記下來的」？→ work-log。是「blog 內部問題」？→ posts。是「跟工作脈絡無關的方法論整理」？→ record / report。

---

底下自動列出本資料夾的所有文章、依日期排序。
