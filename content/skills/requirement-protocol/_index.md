---
title: "Requirement Protocol — 需求確認到實作的對話協議"
date: 2026-04-26
description: "從需求確認到實作的對話協議：模糊指令澄清、可決定 vs 該確認、失敗 2 次轉折、覆寫成本告知、revert checkpoint、漸進驗證、工具切換時機。六大原則 + 五份情境 reference。"
tags: ["工程方法論", "對話協議", "需求澄清", "Debugging", "skills"]
---

## 這個資料夾是什麼

`requirement-protocol` 是一套對話協議 skill，原生位置在 [`.claude/skills/requirement-protocol/`](https://github.com/tarrragon/blog/tree/main/.claude/skills/requirement-protocol) 供 Claude runtime 呼叫；這份是**同內容的文章版本**，讓人類讀者也能直接在 blog 閱讀。

把「使用者下指令 → 執行者實作」之間的溝通流程結構化、避免反覆失敗、避免做出使用者沒要的東西、避免在錯誤方向上累積沉沒成本。源頭是 [`content/report/`](/report/) 累積的 50+ 篇事後檢討、由本 skill 的五份 reference 萃取對應五個情境的協議步驟。

## 閱讀順序

### 場景 1：第一次接觸

| 順序 | 檔案                                            | 目的                                     |
| ---- | ----------------------------------------------- | ---------------------------------------- |
| 1    | [SKILL.md](/skills/requirement-protocol/skill/) | 三大支柱 + 六大原則速查、觸發路由表      |
| 2    | 依情境挑一份 reference（見下表）                | 把原則翻譯成可套用的協議步驟、模板與範例 |
| 3    | 該 reference 結尾的 self-check checklist        | 自評有沒有按協議走                       |

### 場景 2：已熟悉協議、想直接解決當前任務

直接依觸發情境跳對應 reference：

| 觸發情境                                                       | reference                                                                                            |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| 收到模糊指令（含「對齊」「靠近」「隔離」「不要動」「分開」等） | [clarifying-ambiguous-instructions](/skills/requirement-protocol/clarifying-ambiguous-instructions/) |
| 不確定某個決定該自決還是該先問使用者                           | [clarifying-ambiguous-instructions](/skills/requirement-protocol/clarifying-ambiguous-instructions/) |
| 同方向失敗 ≥ 2 次、想再試一次更小心                            | [failure-pivot-protocol](/skills/requirement-protocol/failure-pivot-protocol/)                       |
| 推理 + 視覺截圖溝通迴圈卡住、不知道該不該換工具                | [tool-switching-timing](/skills/requirement-protocol/tool-switching-timing/)                         |
| 客製需求要對抗多層（vendor CSS、framework、browser default）   | [cost-and-checkpoint](/skills/requirement-protocol/cost-and-checkpoint/)                             |
| 收到「先還原 / 先重來 / 換個方向」類指令                       | [cost-and-checkpoint](/skills/requirement-protocol/cost-and-checkpoint/)                             |
| 開始 UI layout debug、不知道從哪一步起                         | [progressive-verification](/skills/requirement-protocol/progressive-verification/)                   |
| 設計 selector / MutationObserver root / JS 操作範圍            | [progressive-verification](/skills/requirement-protocol/progressive-verification/)                   |

每份 reference 自包含：讀任一份不需要回頭讀其他 reference。

## 與 blog 專案其他資料的關係

| 位置                                           | 角色                                                          |
| ---------------------------------------------- | ------------------------------------------------------------- |
| `.claude/skills/requirement-protocol/`         | 實際 skill — Claude runtime 呼叫的檔案來源                    |
| `content/skills/requirement-protocol/`（本處） | 文章版本 — 人類讀者在 blog 閱讀                               |
| [`content/report/`](/report/)                  | 50+ 篇事後檢討、本 skill 的素材來源；reference 結尾連回對應篇 |
| `.claude/skills/compositional-writing/`        | 寫作方法論 skill — 本 skill 的 references 撰寫品質依此規範    |

## Last Updated

2026-04-26 — 初版：v0.1.0 同步、五份 references 對應「模糊指令 / 失敗轉折 / 成本與 checkpoint / 漸進驗證 / 工具切換」五個情境。
