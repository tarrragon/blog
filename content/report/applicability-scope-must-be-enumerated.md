---
title: "適用範圍要展開成 file enumeration、口語描述不夠"
date: 2026-04-29
weight: 96
description: "原則的『適用範圍』寫成口語描述（『所有教學文件的論證段落』）時、執行 review 的人要當場推導『具體哪些檔屬於這個範圍』、推導步驟容易漏；改寫成 enumerated file list（具體列出 file paths）就能避免 enumeration 不完整。Enumerate 的合法形式是『可被 grep / find 重現的具體 file 集合』、不是『口語類型描述』。本卡是 #95 的下游具體化、跟 #82 互補：enumerate 是字面層、enumeration completeness 是行為層判準。"
tags: ["report", "事後檢討", "工程方法論", "寫作", "原則"]
---

## 核心原則

**適用範圍要展開成具體 file enumeration、不能只給口語類型描述。** 「所有教學文件」「所有規範文件」這類描述聽起來夠語意化、實際執行 review 時要當場推導「具體哪些檔屬於這個類型」— 推導步驟容易漏。Enumerate 成具體 file list（或可重現該 list 的 grep / find 指令）才是合法的適用範圍形式。

| 適用範圍的形式                                     | 合法性                                      |
| -------------------------------------------------- | ------------------------------------------- |
| 「所有教學 / 知識卡 / 規範文件的論證段落」         | 不夠、執行時要當場推導具體檔、推導步驟易漏  |
| 「`.claude/skills/compositional-writing/**/*.md`」 | 合法、明確檔列表、可重現                    |
| 「`grep -l '## 核心原則' content/report/`」        | 合法、可重現的 grep 規則                    |
| 「同類教學文件、含 mirror / fork / 翻譯版」        | 不夠、mirror / fork / 翻譯版要明列具體 path |

判別問題：「**這個適用範圍能 reproduce 出具體 file list 嗎？兩個人各自展開會得到同一個 list 嗎？**」答案是「不能」就需要 enumerate。

---

## 情境

寫了一條原則卡片（例：#95 multi-pass scope 由適用範圍決定）後、開始套用該原則跑 review。預設行為是讀「適用範圍」描述、心裡推導具體檔、開始掃。推導過程典型踩到的坑：

- 描述用語意層詞彙（「教學文件」「規範文件」）、心裡只想到主檔、忘了 mirror / sibling / 翻譯版
- 描述用 directory 層級（「`.claude/skills/`」）、忘了 `content/skills/` 是同 surface mirror
- 描述用「所有 X」，X 邊界本來就模糊（「所有 Pattern 卡片」— 哪些算 Pattern？）

具體 case：本 blog 跑 #94 + #95 review 時、適用範圍寫「`compositional-writing` skill 的所有 references」、心裡推導 = `.claude/skills/compositional-writing/references/*.md`。漏掉的是：

- `content/skills/compositional-writing/*.md`（同 surface mirror、AGENTS.md §9 規範要求「主體相同」）
- 同名檔在兩個物理路徑都存在、語意上是同一份內容

連續兩輪 review（#94 跟 #95）都漏同 5 個 mirror 檔、共 10 處違規透過 mirror 永久躲過 review。**Root cause 不是「我忘了」、是「適用範圍沒 enumerate、每次 review 都要重新心算一次具體 list」**。

---

## 理想做法

### 第一步：原則定義時 enumerate 適用範圍

寫原則卡片時、適用範圍欄位寫具體 file enumeration（path glob 或 grep / find 指令）、不寫類型描述。例：

```markdown
## 適用範圍

- `.claude/skills/compositional-writing/SKILL.md`
- `.claude/skills/compositional-writing/references/*.md`
- `content/skills/compositional-writing/*.md`（mirror、AGENTS.md §9 規範同步）
- `content/report/*.md`（教學卡）
```

或用可重現的 grep / find 規則：

```bash
# 適用範圍 = 含「## 核心原則」section 的所有教學卡
grep -rl "^## 核心原則" content/report/ content/skills/
```

兩種形式擇一、避免「所有 X 類文件」的口語描述。

### 第二步：Review 開始前先跑 enumeration、確認 list 完整

跑 pass 之前、先 ls / grep 出具體檔列表、貼到 review 紀錄裡、確認沒漏。例：

```bash
$ find .claude/skills/compositional-writing content/skills/compositional-writing -name "*.md"
.claude/skills/compositional-writing/SKILL.md
.claude/skills/compositional-writing/references/writing-articles.md
... (15 files total)
content/skills/compositional-writing/skill.md
content/skills/compositional-writing/writing-articles.md
... (12 files total)
```

把這個 list 當這次 pass 的 ground truth、跟原則的「適用範圍 enumeration」比對、有 discrepancy（list 多 / 少）就停下來重看適用範圍定義。

### 第三步：把 enumeration 規則做成工具化檢查

當 enumeration 規則穩定後（例：「`.claude/skills/<x>/` 跟 `content/skills/<x>/` 永遠是 mirror 關係」）、把它寫成 lint / pre-commit hook：

- mirror 檢查：兩 path 同名檔有 diff → 警告
- enumeration 漂移檢查：原則卡片裡的 path glob 跟實際 ls 結果有差 → 警告

工具化後 enumeration 不再依賴人為紀律、是結構性保證。

---

## 沒這樣做的麻煩

### Review scope 每次都要重新心算、漏判率隨輪次累積

口語描述的適用範圍 = 每次 review 都要當場推導具體 list。推導步驟有錯漏率、每跑一輪 review 就累積一次。本 blog 跑 #94 / #95 連續兩輪都漏同 5 個 mirror = 推導錯漏率 100%、不是偶發。

### Mirror / fork / 副本永遠躲過 review

語意上是同一份內容、物理上不同 path 的檔（mirror / fork / 翻譯版 / SDK 多語言 port），最容易在「所有 X」描述下被漏掉 — 因為心算推導對齊到「主檔」、副本被「以為已包含」漏跳過。連續多輪後副本內容會嚴重 drift、跟主檔失去同步。

### Enumeration 缺失等於沒有原則的 SSoT

適用範圍是原則的「作用域 SSoT」、沒寫清楚就等於每個讀者各自解釋一份 — #44 SSoT 違反在「原則作用域」維度的具體形態。讀者 A 跑 review 涵蓋 mirror、讀者 B 不涵蓋、原則套用結果就會 drift。

---

## 跟其他抽象層原則的關係

- **[#95 Multi-pass scope 要蓋同類風險區](../multi-pass-scope-must-cover-risk-zone/)**：本卡是 #95 的下游具體化。#95 答「scope 從哪來 = 適用範圍 ∩ corpus」、本卡答「適用範圍長什麼樣 = enumerated file list」。兩條串起來才是完整 review 流程。
- **[#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/)**：本卡跟 #82 互補。Enumerate file list 是字面層（具體 path）、enumeration completeness 是行為層的合法性判準（兩個人展開能否得到同一個 list）— 兩層都要對齊、scope 才合法。
- **[#44 Single Source of Truth](../single-source-of-truth/)**：本卡是 #44 在「原則作用域」維度的具體案例。適用範圍口語描述 = 每個讀者各自解釋一次、結果 drift。
- **[#7 量測值缺一不可](../measurement-completeness/)**：本卡是 #7 在「review 範圍」的同形 pattern — enumerate 漏一個 = sanity 防線有缺口、整組 review 結果不可信。
- **[#42 2 次門檻是訊號](../two-occurrence-threshold/)**：本卡的觸發來自「同方向漏判 2 次」訊號 — mirror 漏同步在 #94 / #95 review 連續發生、就是 #42 訊號要求抽象的 case。

---

## 判讀徵兆

當你寫原則卡片或準備跑 review 時、停下來檢查：

| 徵兆                                                | 說明                                       |
| --------------------------------------------------- | ------------------------------------------ |
| 適用範圍寫「所有 X 類文件」（口語類型描述）         | 沒 enumerate、執行時要心算、易漏副本       |
| 適用範圍只寫主目錄、沒列 mirror / fork / 翻譯版     | mirror 系列檔最容易漏、明列                |
| 兩個人讀同一個適用範圍、心裡展開的 file list 不一樣 | 適用範圍模糊、要改寫成 grep / find 規則    |
| Review 跑完、沒有「實際掃過哪些檔」的紀錄           | scope 沒驗證、漏判無 retro signal          |
| 連續多輪 review 都漏同類檔（例 mirror）             | #42 訊號、enumerate 規則該升級成工具化檢查 |

---

## 適用範圍與邊界

- **適用範圍 enumeration**：
  - `content/report/*.md`（所有 report 卡片寫適用範圍時）
  - `.claude/skills/*/SKILL.md`（所有 skill 入口的觸發路由）
  - `.claude/rules/**/*.md`（所有規範文件的作用域）
- **不適用**：純文字創作（散文 / 詩 / 故事）— 這類沒有「原則作用域」議題、enumerate 是 over-engineering
- **邊界**：「Enumerate」≠「全 repo 全列」— 適用範圍仍由原則決定、enumerate 只是把該範圍寫成可重現形式；範圍本身的合理性是另一件事（由原則的 trade-off 決定）
