---
title: "Metadata surface 要納入寫作 review 範圍"
date: 2026-04-30
weight: 97
description: "寫作 review 的 surface 包含正文與 metadata surface：title、description、frontmatter、heading、link label、MOC 索引條。正文通過 positive wording 或 multi-pass review 只代表 body surface 收斂；讀者入口與索引入口也要跑同一套 frame，才能讓文章在第一眼、搜尋與跨篇路由上維持同一個概念錨點。"
tags: ["report", "事後檢討", "工程方法論", "寫作", "review"]
---

## 核心原則

**寫作 review 的 surface 包含正文與 metadata surface。** Title、description、frontmatter、heading、link label、MOC 索引條都是讀者入口與 grep 入口；它們和正文共同建立讀者第一個概念錨點。正文通過 multi-pass review 只代表 body surface 收斂，metadata surface 仍要跑同一套意圖、語氣、grep-ability 與索引一致性檢查。

| Surface            | 典型位置                                 | Review 責任                            |
| ------------------ | ---------------------------------------- | -------------------------------------- |
| Body surface       | 段落、表格、範例、判讀徵兆               | 完整論證、段首核心、案例補足           |
| Metadata surface   | `title`、`description`、`tags`、`weight` | 讀者第一眼、搜尋摘要、排序與分類       |
| Navigation surface | `_index.md` 索引條、MOC hook、link label | 跨篇路由、下一步判斷、概念入口一致性   |
| Identity surface   | 檔名、slug、canonical link               | 可回溯識別、跨工具定位、單次 grep 命中 |

判別問題：「**讀者看到這篇文章之前，會先看到哪些文字？這些文字有沒有跟正文跑同一輪 review？**」

---

## WARP 分析摘要

| 面向 | 內容                                                                                                                                                                                        |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 觀察 | 在建立資安章節大綱時，正文已採用「資安作為風險路由系統」的正向概念，但 frontmatter title 與 `_index.md` 索引條保留 `資安不是 Checklist：它是風險路由系統`。                                 |
| 判讀 | Review frame 套在 body surface，metadata surface 被當成包裝文字；因此「正向陳述優先」實際只覆蓋正文，讀者入口仍使用負向 hook。                                                              |
| 策略 | 把 metadata surface 明列成 review scope：title、description、tags、heading、link label、MOC hook、slug / filename 都要跟正文一起跑 positive wording、focus、grep-ability、cross-link pass。 |
| 結論 | `compositional-writing` 的 multi-pass 規則需要補一個 surface 軸：frame 決定看什麼品質，surface 決定掃哪些文字。Frame × surface 同時完整，review 才能覆蓋文章實際被讀到的位置。              |

反向驗證：有些標題可以保留對照句型，條件是正文需要讀者先排除常見誤解，且標題本身同時給出正向概念錨點。這次的正文已能用「資安作為風險路由系統」直接建立錨點，對照句型放在正文的論證段更穩定。

---

## 情境

建立 `content/backend/07-security-data-protection/security-as-risk-routing-system.md` 時，文章責任已經寫成「把資安從檢查項目轉成工程路由語言」。正文段落也使用了正向定義：資安路由系統先判斷風險落點，再選擇控制面。

問題出現在讀者入口：

- Frontmatter `title` 使用 `資安不是 Checklist：它是風險路由系統`
- `content/backend/07-security-data-protection/_index.md` 的索引條沿用同一個 link label
- Review 討論集中在正文與章節內容，title / MOC hook 沒被列為同一輪檢查對象

這個問題的主因是 review surface enumeration 漏列：執行者知道要跑正向陳述檢查，但心中 scope 等於「正文段落」，沒有把 metadata surface 視為同等重要的文字。

---

## 理想做法

### 第一步：先列出本次產出的所有 surface

寫作前先列出本次會產生或修改的文字位置。例：

```text
content/backend/07-security-data-protection/security-as-risk-routing-system.md
- frontmatter.title
- frontmatter.description
- body headings
- body paragraphs
- link labels

content/backend/07-security-data-protection/_index.md
- table link label
- table topic
- table responsibility
```

這份清單是 review 的 surface enumeration。它補足 [#96 適用範圍要展開成 file enumeration](../applicability-scope-must-be-enumerated/) 的單檔內版本：#96 先列「哪些檔」，本卡再列「檔內哪些文字位置」。

### 第二步：每一輪 frame 都掃所有 surface

Multi-pass review 的每輪 frame 都要套到 surface 清單上：

| Frame                   | Body surface                 | Metadata / navigation surface                |
| ----------------------- | ---------------------------- | -------------------------------------------- |
| 對意圖                  | 段落是否回到核心責任         | Title / description 是否承接同一個核心責任   |
| 正向陳述 / 機會成本語氣 | 段落是否先建立概念，再補對照 | Title / MOC hook 是否先給正向錨點            |
| Grep-ability / 命名     | 段首關鍵字是否可搜尋         | Title、slug、link label 是否能單次 grep 命中 |
| Cross-link 健康度       | 引用是否指向正確卡片         | `_index.md` 索引條是否導向同一個概念入口     |
| 反例 / 邊界             | 對照段是否保留原因與適用範圍 | 標題若使用對照句型，是否有正文立即承接其原因 |

Surface enumeration 讓「我有跑正向陳述 pass」變成可驗證動作，而不只是抽象自我宣告。

### 第三步：用 grep 補字面層掃描

正向陳述是語意判斷，但第一層候選可以用 grep 找出：

```bash
rg -n "不行|不可以|不是|不要|無法|不能" \
  content/backend/07-security-data-protection/security-as-risk-routing-system.md \
  content/backend/07-security-data-protection/_index.md
```

grep 命中代表「需要判讀」，不代表自動違規。合法的對照句型要回到 [#94 正向改寫要保留對照論據](../positive-rewrite-preserves-contrast/) 的判準：有正向錨點、有對照原因、有適用情境。

---

## 沒這樣做的麻煩

### 讀者入口會先傳遞舊 frame

Title 與 MOC hook 是讀者先看到的文字。正文即使已經建立正向概念，入口若仍用負向 hook，讀者第一個 mental model 仍會被帶回「排除某種做法」而非「建立某個責任」。入口 frame 會影響後續閱讀方式。

### Search surface 會保留錯誤概念錨點

Title、description、link label 是搜尋結果與 grep 最容易命中的位置。metadata surface 沒跑 grep-ability 與 positive wording，錯誤概念會比正文更容易被找到，長期變成知識庫中的主要入口。

### Review 報告會產生 coverage illusion

只寫「已跑 positive wording pass」但沒有列 surface，review 報告會暗示整篇文章已覆蓋。實際上只掃 body surface，metadata surface 仍是未驗證區。這是 [#95 Multi-pass scope 要蓋同類風險區](../multi-pass-scope-must-cover-risk-zone/) 在單檔內的同形問題。

---

## 跟其他抽象層原則的關係

- **[#83 Writing 的 multi-pass review](../writing-multi-pass-review/)**：#83 定義 frame 軸，本卡補 surface 軸。Frame 回答「用什麼眼睛看」，surface 回答「哪些文字都要被看」。
- **[#95 Multi-pass review 的 scope 要蓋同類風險區](../multi-pass-scope-must-cover-risk-zone/)**：#95 處理跨檔 scope，本卡處理單檔內 surface scope。兩者組合成完整 coverage：file scope × surface scope。
- **[#96 適用範圍要展開成 file enumeration](../applicability-scope-must-be-enumerated/)**：#96 要求可重現的 file list，本卡要求每個 file 內的 surface list。File enumeration 完成後，還要做 surface enumeration。
- **[#94 正向改寫要保留對照論據](../positive-rewrite-preserves-contrast/)**：#94 保留合法對照的推理，本卡定義對照句型出現在 title / MOC hook 時的檢查位置與承接責任。
- **[#84 Naming 是 iterated artifact](../naming-as-iterated-artifact/)**：Title、slug、link label 都是命名。它們需要多輪迭代，在生成後持續用 grep-ability 與讀者入口角度收斂。
- **[#44 Single Source of Truth](../single-source-of-truth/)**：正文核心概念與 metadata surface 需要共享同一個概念 SSoT。入口文字與正文語意分裂時，讀者會看到兩個 competing source。

---

## 判讀徵兆

當你完成文章或卡片後，看到以下訊號就要補 surface enumeration：

| 徵兆                                            | 判讀                           |
| ----------------------------------------------- | ------------------------------ |
| 正文改成正向概念，title 仍使用排除式 hook       | Metadata surface 漏跑語氣 pass |
| `_index.md` 索引條只是沿用第一版標題            | Navigation surface 漏跑對意圖  |
| Frontmatter description 比正文更像行銷標語      | Search surface 漏跑概念錨點    |
| Review 紀錄只寫「已檢查文章」但沒列 title / MOC | Coverage 欠缺驗證依據          |
| Grep 掃正文通過，搜尋結果仍命中舊句型           | Grep scope 沒包含 metadata     |

---

## 適用範圍與邊界

- **適用**：技術文章、report 卡片、知識卡片、README、規格文件、skill reference、MOC / `_index.md`
- **特別適用**：有 frontmatter、sidebar title、SEO description、index table、link label 的內容系統
- **邊界**：Metadata surface review 是寫作 pass；它需要語意判讀，grep 只負責提出候選
- **例外**：短訊息、一次性草稿、私人 scratch note 可以只保留 title / body 的最小 surface；production 內容與公開知識庫需要全 surface review

---

## 可操作檢查

Production 內容交付前，至少跑這三步：

1. 列出這次新增 / 修改檔案的 surface：`title`、`description`、heading、body、link label、MOC row。
2. 跑負向詞候選 grep，逐一判讀是否有正向錨點與對照原因。
3. 對照 `_index.md` 或 MOC，確認索引條、文章標題與正文第一段都指向同一個核心責任。
