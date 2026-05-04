---
title: "WRAP 決策框架 — 認知偏誤防護與決策品質"
date: 2026-05-04
description: "WRAP 決策框架的 blog 好讀版：用錨點確認、資料充足度、選項擴增、實境檢驗、機會成本、行前預想與絆腳索防止自動駕駛式決策。"
tags: ["skills", "wrap-decision", "決策框架", "工程方法論"]
---

## 這個資料夾是什麼

`wrap-decision` 是一套 WRAP 決策框架 skill，原生位置在 [`.claude/skills/wrap-decision/`](https://github.com/tarrragon/blog/tree/main/.claude/skills/wrap-decision) 供 Claude runtime 呼叫；這份是**同內容的文章版本**，讓人類讀者也能直接在 blog 閱讀。

核心是提醒決策者「你是有選擇的」。它把決策拆成錨點確認、Step 0 資料充足度閘門、W 擴增選項、R 實境檢驗、A 拉開距離、P 準備好犯錯，以及 Tripwire 絆腳索監控。

## 閱讀順序

### 場景 1：第一次接觸

| 順序 | 檔案                                                   | 目的                                     |
| ---- | ------------------------------------------------------ | ---------------------------------------- |
| 1    | [SKILL 入口](/skills/wrap-decision/skill/)             | 理解 WRAP 主流程、觸發條件與決策檢查順序 |
| 2    | [PM 快速參考清單](/skills/wrap-decision/pm-checklist/) | 用快速模式或完整模式跑一次決策自檢       |
| 3    | [詳細技巧](/skills/wrap-decision/detailed-techniques/) | 補齊每階段的操作技巧與反偏誤方法         |

### 場景 2：已熟悉原則、想直接解決當前任務

| 觸發情境                                   | reference                                                                                            |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| 要快速跑一輪 WRAP                          | [pm-checklist](/skills/wrap-decision/pm-checklist/)                                                  |
| 需要每階段詳細技巧                         | [detailed-techniques](/skills/wrap-decision/detailed-techniques/)                                    |
| 要設計絆腳索、失敗門檻或重新評估時機       | [tripwire-catalog](/skills/wrap-decision/tripwire-catalog/)                                          |
| 要做深度查詢、反向驗證或多輪研究           | [iterative-research](/skills/wrap-decision/iterative-research/)                                      |
| 要檢查規則設計是否產生 paternalism 悖論    | [anti-paternalism](/skills/wrap-decision/anti-paternalism/)                                          |
| 任務啟動前只想保留最低品質閘門             | [claim-quick-wrap](/skills/wrap-decision/claim-quick-wrap/)                                          |
| 要把 WRAP 接進任務系統、規則庫或自動化提醒 | [integration-patterns](/skills/wrap-decision/integration-patterns/)                                  |
| 要對齊觸發條件清單                         | [triggers-alignment](/skills/wrap-decision/integration-patterns-triggers-alignment/)                 |
| 要把 W/A/P 簡化成任務啟動三問              | [simplified-three-questions](/skills/wrap-decision/integration-patterns-simplified-three-questions/) |
| 要防止偽 Widen 與假選項                    | [pseudo-widen-guard](/skills/wrap-decision/integration-patterns-pseudo-widen-guard/)                 |
| 要做來源逐項核對                           | [source-verification](/skills/wrap-decision/integration-patterns-source-verification/)               |
| 要處理個人化建議的資料充足度               | [personalized-advice](/skills/wrap-decision/integration-patterns-personalized-advice/)               |
| 要整理 WRAP 與專案規則庫分工               | [rules-map](/skills/wrap-decision/integration-patterns-rules-map/)                                   |
| 要把案例抽成可重用決策教訓                 | [case-studies](/skills/wrap-decision/integration-patterns-case-studies/)                             |

每份 reference 自包含：讀任一份不需要回頭讀其他 reference。

## 與 blog 專案其他資料的關係

| 位置                                    | 角色                                       |
| --------------------------------------- | ------------------------------------------ |
| `.claude/skills/wrap-decision/`         | 實際 skill — Claude runtime 呼叫的檔案來源 |
| `content/skills/wrap-decision/`（本處） | 文章版本 — 人類讀者在 blog 閱讀            |
| `content/skills/compositional-writing/` | 寫作方法論 — 用於把 skill 內容整理成文章   |
| `content/skills/requirement-protocol/`  | 對話協議 — 與 WRAP 的決策呈現場景互補      |

## Last Updated

2026-05-04 — 同步到 `.claude/skills/wrap-decision/` @ v2.3.0：

- v2.1.0 — 新增多輪迭代查詢方法論、反向驗證範本、悖論識別檢查清單與自我暴露偏好實踐。
- v2.2.0 — 新增反思深度質疑觸發條件。
- v2.3.0 — 新增 CLI autopilot、既有結論優先、草率改規則與多步驟 perplexity 盲等決策路徑層干擾。
