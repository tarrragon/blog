---
title: "Compositional Writing — 組合式寫作方法論"
date: 2026-04-24
description: "以 Zettelkasten 為核心、針對程式碼註解、文件、log、prompt、欄位、長篇技術文章的寫作方法論。五大原則 + 觸發路由 + 9 份情境 reference。"
tags: ["寫作方法論", "Zettelkasten", "技術寫作", "compositional-writing"]
---

## 這個資料夾是什麼

`compositional-writing` 是一套寫作方法論 skill，原生位置在 [`.claude/skills/compositional-writing/`](https://github.com/tarrragon/blog/tree/main/.claude/skills/compositional-writing) 供 Claude runtime 呼叫；這份是**同內容的文章版本**，讓人類讀者也能直接在 blog 閱讀。

核心是把寫作看成「原子卡片組合」：每段文字只承載一個概念、可獨立閱讀、可跨情境重用。適用情境涵蓋程式碼註解、文件、log、prompt、欄位設計、完整長篇技術文章。

## 閱讀順序

### 場景 1：第一次接觸

| 順序 | 檔案                                                           | 目的                              |
| ---- | -------------------------------------------------------------- | --------------------------------- |
| 1    | [SKILL.md](/skills/compositional-writing/skill/)               | 三大支柱 + 五大原則速查、觸發路由 |
| 2    | 依情境挑一份 reference（見下表）                               | 把原則翻譯成可套用的檢查項與範例  |
| 3    | [meta-metrics.md](/skills/compositional-writing/meta-metrics/) | 用 M1–M2 自評寫作成果             |

### 場景 2：已熟悉原則、想直接解決當前任務

直接依觸發情境跳對應 reference：

| 觸發情境                                       | reference                                                                                     |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------- |
| 要寫或改一段程式碼註解 / doc comment           | [writing-code-comments](/skills/compositional-writing/writing-code-comments/)                 |
| 要起草 / 改寫一份文件（worklog、spec、README） | [writing-documents](/skills/compositional-writing/writing-documents/)                         |
| 要設計 log / 錯誤訊息 / 結構化輸出             | [writing-logs](/skills/compositional-writing/writing-logs/)                                   |
| 要撰寫給 AI 的 prompt / instruction            | [writing-prompts](/skills/compositional-writing/writing-prompts/)                             |
| 要撰寫完整長篇技術文章                         | [writing-articles](/skills/compositional-writing/writing-articles/)                           |
| 要設計 ticket 欄位 / schema frontmatter        | [designing-fields](/skills/compositional-writing/designing-fields/)                           |
| 六欄位範例詳查（正確 + 混淆對照）              | [designing-fields-ticket-6w](/skills/compositional-writing/designing-fields-ticket-6w/)       |
| 驗證寫作品質（認知負擔、獨立理解率）           | [meta-metrics](/skills/compositional-writing/meta-metrics/)                                   |
| 新增或修改一份 Skill reference                 | [reference-authoring-standards](/skills/compositional-writing/reference-authoring-standards/) |
| 驗收 Skill 發布品質（dry-run）                 | [dry-run-guide](/skills/compositional-writing/dry-run-guide/)                                 |

每份 reference 自包含：讀任一份不需要回頭讀其他 reference。

## 與 blog 專案其他資料的關係

| 位置                                            | 角色                                                               |
| ----------------------------------------------- | ------------------------------------------------------------------ |
| `.claude/skills/compositional-writing/`         | 實際 skill — Claude runtime 呼叫的檔案來源                         |
| `content/skills/compositional-writing/`（本處） | 文章版本 — 人類讀者在 blog 閱讀                                    |
| `content/posts/markdown-writing-spec.md`        | Blog 自己的 markdown 寫作規範（mdtools 檢查項目、與本 skill 並行） |
| `content/posts/tech_writing_structure.md`       | 長篇技術文章結構（writing-articles 的來源之一）                    |

## Last Updated

2026-04-24 — 初版文章化：`.claude/skills/compositional-writing/` @ v0.3.0 同步。
