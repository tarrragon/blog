---
title: "先建 report 卡再進 skill、不是先改 skill 再補 report"
date: 2026-06-26
weight: 197
description: "report 卡是原則的 SSoT（有情境、根因、理想做法），skill 是 report 的操作化引用。先有 report 才有 skill 引用的依據。反過來做會讓 skill 裡的規則缺乏可追溯的根據，且 report 容易被跳過。"
tags: ["report", "事後檢討", "工程方法論", "原則", "流程"]
---

## 論述基礎與限制

本卡抽自 infra 教學模組的完整生產週期。期間多次出現「先改了 skill、事後才補 report」的操作順序，導致 skill 裡的新規則在一段時間內沒有 report 卡的根據可追溯。限制：evidence 來自單一專案的 skill 演進過程。

## 核心原則

report 卡是原則的 SSoT——它記錄了這個原則是從什麼情境抽出來的、根因是什麼、理想做法是什麼、不這樣做的麻煩是什麼。skill 是 report 的操作化引用——它把 report 裡的原則轉成 reviewer prompt 的審查維度、生成端的檢查清單、keyword bank 的 grep pattern。

兩者的關係是 report → skill，不是 skill → report：

| 方向           | 意義                           | 風險                              |
| -------------- | ------------------------------ | --------------------------------- |
| report → skill | 從情境抽出原則、再操作化進工具 | 低：原則有根據、可追溯            |
| skill → report | 先在工具裡加規則、事後補根據   | 高：規則缺根據、report 容易被跳過 |

## 情境

infra 模組生產期間的操作順序：

- 使用者指出「寫作語氣要調整」→ 直接改 compositional-writing skill 加 keyword bank → 兩天後才補 report 卡
- 使用者指出「管理層資訊缺失」→ 直接補文章 → 之後才建 report 卡 → 再之後才進 skill
- 使用者指出「鏡像連結 mapping 不完整」→ 修了腳本 → 之後才建 report 卡 → 還沒進 skill 就又出下一個問題

每次都能運作，但 report 卡的建立被擠到「有空再做」的位置，而非流程的第一步。

## 理想做法

標準操作流程從 report 卡開始：

1. 發現問題或收到使用者反饋
2. 建 report 卡（情境 → 根因 → 理想做法 → 判讀徵兆）
3. 評估是否進 skill（哪個 skill、哪個段落）
4. 修改 skill、引用 report 卡路徑
5. 推送 skill 庫 + 同步鏡像

report 卡先於 skill 修改，確保每條 skill 規則都有可追溯的根據。

## 沒這樣做的麻煩

- **規則缺根據**：skill 裡加了一條 grep pattern 但沒有 report 卡解釋為什麼要加，三個月後某人問「這條規則的由來是什麼」時答不出來
- **report 被跳過**：「先改 skill 再補 report」的順序讓 report 變成事後文件，容易被「下次再補」拖延到永遠不補
- **skill 的 Version 歷史缺引用**：Version 條目寫「加了 X 規則」但沒有 `per [report 卡名](/report/slug/)` 的引用，讀者無法回溯規則的來源情境

## 判讀徵兆

如果 skill 的 Version 歷史裡有一條更新沒有附 report 卡的引用，代表流程順序反了。每條 skill 更新都應該能回溯到一張 report 卡——即使那張卡是同一個 commit 建的。

## 跟其他抽象層原則的關係

- → [跨 surface 鏡像的連結轉換 mapping 要窮盡](/report/mirror-link-mapping-must-be-exhaustive/)：鏡像同步是 skill 更新流程的最後一步，report 建卡是第一步
- → [多輪審查缺 outside-in 讀者 frame](/report/review-lacks-outside-in-reader-frames/)：六個盲點的修法都是「先建 report → 再進 skill」的順序
