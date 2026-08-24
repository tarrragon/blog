---
title: "工作筆記"
slug: "work-log"
description: "工作場景觸發的技術紀錄 — git 操作、build 工具、框架行為、環境設定與架構觀念"
tags: ["work-log", "debug", "工具"]
---

這個資料夾收錄**工作場景中遇到、值得記下來的內容** — 觸發時機是工作（debug、設定、討論、學到某個觀念），不限於事故後的解法，也包含工具設定、技術觀念整理、後端設計分析等。

內容大致分三類：

**版控操作** — git rebase / fixup / 移除歷史內容等。例：

- [Git：把後面 commit 的部分檔案變更搬到前面的 commit](git_move_partial_change_to_earlier_commit/)
- [Git：修復後面的 commit 意外覆蓋前面 commit 的變更](git_fixup_rebase/)
- [commit message 引用外部 issue 會在對方 repo 留下永久事件](github-cross-reference-from-commit-message/)

**Build 工具與框架** — Gradle / Flutter / Dart 的錯誤、行為、設計觀念。例：

- `gradle_jvm_target_asymmetry` — Kotlin/Java target 不一致導致 build 失敗
- `gradle_evaluation_order_traps` — Gradle configuration phase 時序陷阱
- `flutter_hit_test_behavior` — Flutter widget hit test 行為
- `flutter_repaint_heartbeat` — 畫面落後邏輯狀態（重繪訊號沒進 frame 排程）的排查與心跳做法
- `flutter_schedule_frame` — `scheduleFrame()` 的設計意義：按需 render 的最底層「要一個 frame」原語
- `flutter_audio_volume_control` — per-player 音量 vs 系統音量、為何多數不該從 App 改系統音量

**環境、設定與架構觀念** — 開發環境一次性設定、與後端協作時整理出的設計觀念等。例：

- [一行查詢放哪、一個測試留不留：結構改動後的兩次「還需要存在嗎」](flutter_query_ownership_and_structurally_immune_test/) — 查詢的責任歸屬（掛回資料擁有者）與被結構免疫掉的贅測

---

## 寫作模板與語域

work-log 的讀者由搜尋或站內路由帶來、自帶問題；文章的職責是讓他最快拿到判準與脈絡。模板四條（原則見 [#254 寫給帶問題來的讀者](/report/write-for-readers-not-audiences/)）：

- **標題是結論的直述句**：一句話說出這篇確立的判準或結論。標題是檢索錨、錨要承載立場——問句標題把唯一保證被讀到的 surface 用來提問，讀者掃標題列表時拿不到這篇的結論。
- **結構是「情境條件 → 推導與驗證 → 判準」**：開頭把情境講成條件描述——什麼樣的程式、什麼設定、什麼操作會遇到——讓讀者判斷自己在不在射程內；接著讓推導與實測帶著讀者走，判準在推導走完的位置浮現，是讀者已經能自己說出的東西。兩個方向都要避免：把判準壓到文末扣住的三幕劇（第一次失敗、第二次失敗、頓悟）是懸念，要壓平成推導；把結論抽成開頭一段要讀者先記住是灌輸，沒有被推導承接的結論只能硬記。標題承載結論、開頭承載情境、判準由推導交付。
- **視角是客觀條件、不是第一人稱時間線**：檢討的脈絡（做錯了什麼、為什麼錯、為什麼要糾正）用條件語言承載——「reviewer 問了 X、後來才想清楚」寫成「若對這個做法問 X 而答不出來、就該重新檢討」；人物以角色出現（reviewer、修改者）。
- **事件來源一句話帶過、不建結論摘要欄位組**：需要交代「這來自一次實際事件」時，開頭一句話就夠。「觸發場景 / 疑問來源 / 整理目的 / 本文邊界」這類文首欄位組把各段結論先摘出來放在推導之前，是灌輸的另一種形態——讀者拿到的是要硬記的摘要，不是可跟的推導。

範例見 [註解防不了改壞](comment_cannot_guard_invariant/)——直述標題、案例推導帶著讀者走到判準、reviewer 的退件理由呈現為檢視標準。

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
