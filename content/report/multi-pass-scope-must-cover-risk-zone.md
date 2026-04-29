---
title: "Multi-pass review 的 scope 要蓋『同類風險區』、不是『改動區』"
date: 2026-04-29
weight: 95
description: "做 multi-pass review 時、預設用『我這次改過的檔』當 scope 是便利選擇；但同一原則違反通常分布在整個 corpus、改動區只是冰山一角。Scope 該由『同類風險的內容範圍』決定 — 跑某條原則的 pass、就要掃所有適用該原則的檔、不是只掃我自己改過的。改動區 scope 是 #67 在 review 流程的具體展現、會讓 multi-pass 退化成 self-edit pass。"
tags: ["report", "事後檢討", "工程方法論", "寫作", "原則"]
---

## 核心原則

**Multi-pass review 的 scope 由『同類風險區』決定、不是『我改過的檔』。** 跑某條原則的 pass（例如「結論可驗證性」）、scope 就是「所有可能違反該原則的檔」、不是「我這次改了的檔」。後者是執行便利選擇、不是 review scope 的合法依據 — 同一原則違反通常分布在整個 corpus、改動區只佔小比例。

| Scope 定義方式         | 抓得到的違規                              | 漏掉的違規                            |
| ---------------------- | ----------------------------------------- | ------------------------------------- |
| 「我改過的檔」（便利） | 改動區的新引入違規 + 我順手注意到的舊違規 | 整個 corpus 既有的同類違規（佔多數）  |
| 「同類風險的內容範圍」 | 該原則在整個 corpus 的所有違規            | 無 — 這就是該原則 review 的合法 scope |

判別問題：「**這次 pass 用的 frame、適用範圍是哪些檔？我的 scope 涵蓋了那個範圍嗎？**」答案是「沒有、我只掃了改動區」就需要擴大 scope。

---

## 情境

寫了一條新原則卡片（例：#94 結論可驗證性）後、要套回既有寫作做 multi-pass review。預設行為是「掃我這次改過的檔」、原因：

- 改動區是當下 working memory 裡的內容、便利
- 改動區 diff 短、容易跑完
- 改動區是「我剛動過的、所以可能有違規」的直覺對象

這三個理由都是**執行便利**、不是「review scope 的合法依據」。新原則套回既有 corpus 時、違規通常已經存在於沒被改動的部分（因為原則之前不存在、整個 corpus 都沒按該原則寫過）。只掃改動區會 systematic miss 大部分違規。

具體 case：本 blog `compositional-writing` skill 的負向表述清理：

1. 寫 #94 結論可驗證性原則（contrast 該保留還是該刪的判別）
2. Multi-pass 跑 6 輪、scope 設為「我改過的 SKILL.md / writing-articles.md / #94 卡片本身」
3. 第二天使用者讀 references/writing-prompts.md、發現「Prompt 的『原子單位』不是『一句話』、而是『一個可被驗收的任務』」就是 #94 該抓的 case
4. 該違規分布廣度：scan 整個 references/ 目錄、相同句型違規共 4 處（writing-prompts / writing-logs / designing-fields / managing-article-collections）、僅 0 處在我改動區內

我的 multi-pass 設計把 4 處違規 100% 漏掉、使用者用肉眼讀就抓到。

---

## 理想做法

### 第一步：定義原則的「適用範圍」

寫一條新原則時、明確標註該原則適用於哪些檔 / section。例：

| 原則                      | 適用範圍                                       |
| ------------------------- | ---------------------------------------------- |
| #94 結論可驗證性          | 所有教學 / 知識卡 / 規範文件的論證段落         |
| 規則五 最重要的話優先說   | 所有有「核心命題」「重點」段落的文件           |
| Severity 判準對齊分流目的 | 所有定義 severity 的 logging / monitoring 文件 |

### 第二步：Pass scope = 適用範圍 ∩ 待 review corpus

跑該原則的 pass 時、scope 是「該原則的適用範圍」交集「目前要 review 的 corpus」、跟「我改過哪些檔」完全無關。

對 compositional-writing skill 而言：跑 #94 pass 的合法 scope 是 `.claude/skills/compositional-writing/**/*.md` 全部、不是「我這次 commit 動到的 5 個檔」。

### 第三步：用 grep 把同類風險區找出來

同類風險常有結構性 signature（句型、詞彙、模式）、可用 grep 把適用範圍縮到具體行。例：

- #94：grep `不是.*而是\|不是.*是\|只是表象\|只是次級訊號` → 候選行
- 規則五：grep `^[^*].*。.*它` → 「X。它不是…」後置定義候選
- Severity 判準：grep `severity.*\(嚴重度\|頻率\)` → 替代判準誤用候選

把 grep 命中行當 review 起點、再人工判斷是否真違規。

---

## 沒這樣做的麻煩

### Multi-pass 退化成 self-edit pass

只掃改動區 = 把 multi-pass review 退化成「我剛寫的東西自己再看一次」、這是 [#83](../writing-multi-pass-review/) 「同 frame 重看」的另一種變形 — 表面在跑 N 輪、實際 scope 是同一塊小區。違規率沒下降、只是把改動區內的違規多檢查了 N 次。

### 既有 corpus 的違規永久累積

每次跑 pass 都只掃改動區、整個 corpus 的既有違規會永久不被處理 — 因為新加的原則只回頭掃改動區、舊內容沒被改的就永遠不過 review。corpus 越大、這個問題越嚴重 — 違規被結構性掩蓋、不是因為沒人看、是因為 scope 預設把它們排除。

### 違規由使用者眼睛 catch、而不是流程 catch

最終結果是違規被使用者讀到才發現、而不是 review 流程主動 catch。這違反 [#82](../literal-interception-vs-behavioral-refinement/) 跟 [#72](../external-trigger-for-high-roi-work/) — 把高 ROI 的 review 工作結構性跳過、靠外部 trigger（使用者抱怨）才執行。

---

## 跟其他抽象層原則的關係

- **[#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)**：本卡是 #67 在「review scope 設定」層的具體案例。最便利的 scope（改動區）跟意圖對齊（同類風險區）反向 — 越便利、越漏掉違規。
- **[#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/)**：本卡跟 #82 互補。#82 是「驗證粒度」要對齊、本卡是「驗證範圍」要對齊 — 兩個都是把 review 結構錯位、結果都是 false confidence。
- **[#83 寫作的 multi-pass review](../writing-multi-pass-review/)**：本卡補強 #83 沒覆蓋的 scope 軸。#83 講「每輪換 frame」（horizontal）、本卡講「每輪 scope 由原則適用範圍決定」（範圍）— frame × scope 兩軸都對齊、multi-pass 才有意義。
- **[#72 高 ROI 無外部觸發的工作會被結構性跳過](../external-trigger-for-high-roi-work/)**：「擴大 scope 跑 corpus-wide review」是高 ROI 但無強制 trigger 的工作、本卡指出該動作預設會被「改動區便利 scope」結構性取代。
- **[#94 正向改寫要保留對照論據](../positive-rewrite-preserves-contrast/)**：本卡跟 #94 是同次踩坑串接 — #94 抓到「改寫違規」、本卡抓到「review scope 漏掉的違規」、兩條一起才是完整的「正向改寫流程」。

---

## 判讀徵兆

當你準備 / 正在跑 multi-pass review 時、停下來檢查：

| 徵兆                                                | 說明                                                          |
| --------------------------------------------------- | ------------------------------------------------------------- |
| Pass 的 scope 是「我改過的檔」                      | 便利 scope、跟原則適用範圍對不上                              |
| 沒明確標註「這條原則適用於哪些檔」                  | 沒適用範圍 = scope 沒依據、預設就會回退到改動區               |
| 跑完 pass 沒用 grep 把同類風險區掃過一遍            | 缺結構性掃描、漏掉的違規無法被流程 catch                      |
| Review 報告寫「修了 X 處違規」、沒寫「掃過 Y 個檔」 | 報告只記輸出、沒記 scope、無法事後驗證 review 範圍是否合法    |
| 使用者後續抓到違規、且該違規不在你的改動區          | scope 失誤的 retro signal、表示這條原則的 pass 該 corpus-wide |

---

## 適用範圍與邊界

- **適用**：multi-pass review、新原則套回既有 corpus、批量品質檢查
- **不適用**：純 syntax / lint check（這類由工具固定 scope 跑全 corpus、無便利退化問題）
- **邊界**：「同類風險區」≠「全 repo 全掃」— scope 由原則適用範圍界定、不無限擴大；範圍邊界比較適合寫在原則定義時（一次想清楚、之後直接套用）、勝過 review 時臨時決定（每次都要重判一次、累積成本高）
