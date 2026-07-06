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

**Build 工具與框架** — Gradle / Flutter / Dart 的錯誤、行為、設計觀念。例：

- `gradle_jvm_target_asymmetry` — Kotlin/Java target 不一致導致 build 失敗
- `gradle_evaluation_order_traps` — Gradle configuration phase 時序陷阱
- `flutter_hit_test_behavior` — Flutter widget hit test 行為
- `flutter_repaint_heartbeat` — 畫面落後邏輯狀態（重繪訊號沒進 frame 排程）的排查與心跳兜底
- `flutter_audio_volume_control` — per-player 音量 vs 系統音量、為何多數不該從 App 改系統音量

**環境、設定與架構觀念** — 開發環境一次性設定、與後端協作時整理出的設計觀念等。

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
