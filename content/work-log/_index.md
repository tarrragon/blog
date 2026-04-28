---
title: "工作筆記"
slug: "work-log"
---

這個資料夾收錄**工作中遇到的工具 / 技術問題的事件紀錄** — 寫法是「我用某工具做某事、踩到某個具體坑、解法是 X」。

內容大致分三類：

**版控操作** — git rebase / fixup / 移除歷史內容等具體事件。例：

- [Git：把後面 commit 的部分檔案變更搬到前面的 commit](git_move_partial_change_to_earlier_commit/)
- [Git：修復後面的 commit 意外覆蓋前面 commit 的變更](git_fixup_rebase/)

**Build 工具與框架陷阱** — Gradle / Flutter / Dart 的具體錯誤與解法。例：

- `gradle_jvm_target_asymmetry` — Kotlin/Java target 不一致導致 build 失敗
- `gradle_evaluation_order_traps` — Gradle configuration phase 時序陷阱
- `flutter_hit_test_behavior` — Flutter widget hit test 行為

**環境與設定** — 開發環境的一次性設定問題（ssh key、本機環境）。

---

## 跟其他資料夾的邊界

| 議題                                      | 該放                                            |
| ----------------------------------------- | ----------------------------------------------- |
| blog 本身設定（Hugo / mdtools / Mermaid） | `posts/`（不是 work-log）                       |
| 從多個事件抽象的方法論                    | `record/`（中性）或 `report/`（從 case 抽原則） |
| 純 OS / 工具小技巧（不涉及開發專案）      | `other/`                                        |
| 工作中用某工具遇到的事件                  | **本資料夾**                                    |

判斷流程：是「我做某事踩到坑」？→ work-log。是「blog 內部問題」？→ posts。是「方法論抽象」？→ record / report。

---

底下自動列出本資料夾的所有文章、依日期排序。
