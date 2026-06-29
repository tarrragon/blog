---
title: "文章主體要對齊標題承諾、WRAP 內部分析不該喧賓奪主"
date: 2026-05-20
weight: 142
description: "文章標題對讀者做了承諾、文章主體必須對齊這個承諾。WRAP 內部分析（Widen Options + Reality Test 含 prior 引用 + evidence weight）即使方法論做得好、如果不是標題承諾的內容、就不該佔文章主體—屬於 scope mismatch、跟 process metadata 暴露（#141）的議題分開。附帶議題：當 WRAP 內部分析喧賓奪主、為了支撐 prior 容易引入沒實際出處的 source citation；把 WRAP 內部分析從主體移除、hallucination 風險自然降低。是 #141 的姊妹卡—#141 處理章節標題 surface、本卡處理章節內容 scope。"
tags: ["report", "事後檢討", "工程方法論", "原則", "WRAP", "Writing", "Scope"]
---

## 核心原則

文章標題對讀者做了承諾、文章主體必須對齊這個承諾。WRAP 內部分析（Widen Options + Reality Test 含 prior 引用 + evidence weight）即使方法論做得好、若不是標題承諾的內容、就不該佔文章主體。

這跟 [#141 WRAP 是寫作者的內部工具、不是文章章節結構](../wrap-as-internal-tool-not-section-structure/) 是兩個不同層級的議題：

| 議題       | [#141](../wrap-as-internal-tool-not-section-structure/)    | 本卡 (#142)                                                               |
| ---------- | ---------------------------------------------------------- | ------------------------------------------------------------------------- |
| 處理層級   | 章節標題（surface）                                        | 章節內容（scope）                                                         |
| 違規症狀   | Process metadata 標題（「Widen Options」「Reality Test」） | 即使標題改了、內容仍是 WRAP 內部分析、偏離標題承諾                        |
| 修法       | 改章節標題為教學風格                                       | 縮減 WRAP 內部分析篇幅、聚焦標題承諾的內容                                |
| 附帶副作用 | 預設讀者認知、分析報告 meta dialogue、重複預告             | Source citation hallucination 風險、解釋順序錯位（source 在前、解釋在後） |

兩卡互補—改了章節標題還不夠、章節內容也要對齊標題承諾。

---

## 情境

3 篇 case-analyses 經過 [#141](../wrap-as-internal-tool-not-section-structure/) 的 Round 3 重寫、章節標題已從 WRAP process metadata 改成教學風格（「為什麼供應商選擇 enterprise 包裝」取代「Widen Options」）。但讀者再次 feedback 指出更深的問題：

第一、[Claude for Legal 之後](/business/case-analyses/claude-for-legal/) 的標題承諾「應用層、新創、知識工作者的三層擠壓」、但「供應商為什麼選擇 enterprise 包裝」段佔了文章 30%+ 篇幅—讀者拿到的內容跟標題承諾不匹配。

第二、那一段內容引用「a16z、Sequoia 公開報告跟 Anthropic 投資人 deck 都強調 enterprise ARR」這類 source—但這些引用沒具體出處（哪份報告、哪一頁、哪一段）、有 hallucination 風險。為了支撐 WRAP Widen Options 的 prior 而引入沒實際出處的 source、是 fidelity 漏洞。

第三、解釋順序錯位—寫成「a16z / Sequoia 等公開報告強調 ARR、背後邏輯是 X」、把 source 放前面、解釋放後面、違反 AGENTS.md 原則一「核心原則先行」。

更深層問題：即使章節標題改成教學風格、WRAP 內部分析（含 prior 引用）的內容仍然喧賓奪主、偏離標題承諾。3 篇都踩同樣的 pattern：

- claude-for-legal 標題「三層擠壓」、原版「供應商為什麼選擇 enterprise 包裝」段佔大量篇幅、含 hallucinated source
- fde-arms-race 標題「SaaS 三支柱鬆動」、原版「三家為什麼同步押 FDE」段佔了三支柱主體的空間
- bufstream 標題「整併週期 + 基礎設施重組」、原版「Buf 為什麼賣」「CoreWeave 為什麼買」兩段 WRAP 分析佔主體

Round 4 重寫後、3 篇都移除「為什麼 X」獨立段、把核心動機塞進「事件本身」一兩句 + cross-link 到處理該動機的對應文章、文章主體留給標題承諾的內容。

---

## 理想做法

### 第一步：寫稿前明確列出標題承諾什麼

標題是讀者跟文章之間的合約。寫稿前用一句話寫下「這篇標題承諾讀者拿到什麼」：

- 「Claude for Legal 之後：應用層、新創、知識工作者的三層擠壓」→ 承諾三層擠壓的拆解
- 「FDE 軍備競賽：SaaS 三支柱鬆動下的結構性轉變」→ 承諾三支柱怎麼鬆動的機制
- 「CoreWeave 收購 Bufstream：整併週期下的賽道判讀與基礎設施重組」→ 承諾整併週期判讀 + 基礎設施重組分析

承諾寫下後、後續每個章節都對齊問：「這段是不是在履行承諾？」

### 第二步：跑完 WRAP 內部分析、區分「主結論」跟「分析過程」

WRAP 七步驟在寫作者腦中跑完—Anchor Check / Step 0 / Widen Options / Reality Test / Attain Distance / Prepare to be Wrong / Tripwire 都要做。但跑完後、分兩類東西：

- **主結論**：可以放文章主體、是讀者要拿走的判讀
- **分析過程**：（Widen Options 的多個解釋、Reality Test 的逐一驗證、Prior 的 source 引用）留在腦中或寫作筆記、不放進文章

判別線是「這段內容是不是標題承諾的一部分」。承諾「三層擠壓」、文章主體就是三層擠壓；供應商動機是 prelude / context、塞進「事件本身」一兩句帶過、不獨立成段做完整 WRAP 分析。

### 第三步：完稿時跑「標題對齊測試」

寫完後、列出文章各段佔多少篇幅、跟標題承諾比對：

```text
列出每段標題 + 段落篇幅 + 是否對齊標題承諾
```

例：

```text
- 事件本身 (10%) — 提供 context、合理
- 供應商為什麼選擇 enterprise 包裝 (30%) — 不在標題承諾、過度
- 第一層擠壓 (15%) — 對齊承諾
- 第二層擠壓 (15%) — 對齊承諾
- 第三層擠壓 (15%) — 對齊承諾
- 長期影響 (10%) — 對齊承諾
- 預警訊號 + 框架 (5%) — 對齊承諾
```

「不在標題承諾」的段落佔 > 20% 就要重寫—把該段縮成一兩句塞進「事件本身」、cross-link 到處理該議題的對應文章、不獨立展開。

### 第四步：Source citation 必須真實可驗證

引用 source 時遵守三條規則：

1. **能 verify 才寫**：引用「a16z 報告」「Sequoia 分析」前、確認你看過該報告、能給具體標題或連結。不能就改成 hedged claim（「業界普遍觀察」「分析師多次點過」）。
2. **解釋在前、source 在後**：「API 利潤太薄需要長合約對沖（這個論點 a16z 多次公開分析）」、不是「a16z 公開分析 API 利潤太薄、所以需要長合約對沖」。核心原則先行—讀者先吸收解釋、再判斷 source 可信度。
3. **不確定就刪掉 source 引用**：寫到「a16z、Sequoia、Andreessen」這種列舉時要問「我真的能列出三家都講過這個論點嗎？」答案是「不確定」就改成「業界普遍觀察」、不列 specific 名字。

### 第五步：WRAP 內部分析的次要結論的處理

WRAP 內部分析跑完後、會產出「主結論 + 次要結論」。主結論放標題承諾的主體、次要結論的處理：

| 次要結論類型       | 處理方式                                                                             |
| ------------------ | ------------------------------------------------------------------------------------ |
| 跟其他文章主題重疊 | Cross-link 過去、不展開（claude-for-legal 把供應商動機 cross-link 到 fde-arms-race） |
| 提供事件 context   | 塞進「事件本身」段一兩句、不獨立成段                                                 |
| 完全偏離本篇主題   | 留在寫作筆記、可能變成另一篇文章                                                     |

---

## 沒這樣做的麻煩

### 讀者拿到的內容跟標題承諾不匹配

標題承諾「三層擠壓」、文章主體 30% 在講「供應商為什麼選擇 enterprise 包裝」、讀者拿走的判讀工具偏離標題暗示的方向。這比章節標題違規更隱蔽—章節標題違規讀者一眼看穿、內容偏離標題要讀完才發現、傷害更深。

### Hallucinated source citation 的 fidelity 漏洞

WRAP Widen Options 需要 prior 支撐（「誰持這論」）、寫作者為了證明 prior 存在、容易引用「a16z、Sequoia、Andreessen」這類沒具體出處的 source。讀者 trust 在 source citation 上、hallucinated source 一旦被識破、整篇文章的 fidelity 崩。

### 解釋順序錯位、違反核心原則先行

當寫作者重心在「我有 source 支撐」、會把 source 放前面（「a16z 公開報告強調 X」）、解釋放後面。違反 AGENTS.md 原則一「核心原則先行」—讀者要的是解釋本身、source 是 attribution、不是 lead。

### WRAP 內部分析方法論價值反而被稀釋

WRAP 是寫作者的 hypothesis 探索工具、價值在「強制做完整探索、防認知偏誤」。當分析過程被搬上文章主體、讀者把它當成「文章內容」吸收、原本的探索工具退化成「對讀者展示我做了多少 hypothesis 探索」的修辭。

---

## 跟其他抽象層原則的關係

- **[#141 WRAP 是寫作者的內部工具、不是文章章節結構](../wrap-as-internal-tool-not-section-structure/)**：sibling 卡。#141 處理章節標題 surface 違規（process metadata 暴露）、本卡處理章節內容 scope 違規（WRAP 內部分析喧賓奪主）。兩卡互補—改章節標題不夠、還要改章節內容比重。

- **[#140 WRAP Widen Options 容易塌成稻草人 framing](../wrap-widen-options-strawman-risk/)**：cousin 卡。#140 處理 Widen Options 段落內部的稻草人結構、本卡處理 Widen Options 段落「該不該存在」的更上位議題。如果 Widen Options 跟標題承諾不對齊、根本不該獨立成段、稻草人問題自然消失。

- **[#131 教材完整性要用讀者旅程驗證](../teaching-completeness-by-learner-journey/)**：本卡是 #131 在「標題承諾兌現」維度的具體 instance。讀者旅程的起點是標題暗示、終點是讀完文章能做什麼。標題承諾不兌現、讀者旅程斷在中段、完成感跟可遷移工具都失效。

- **[#97 Metadata surface 要納入寫作 review 範圍](../metadata-surface-in-writing-review/)**：本卡擴 #97 的 metadata surface 概念。標題本身是 metadata surface—它對讀者承諾文章主體是什麼。Review 不能只看內文是否正確、要看「內文跟標題承諾是否對齊」。

- **[#126 寫作 review 是多軸完整性](../writing-review-multi-axis-completeness/)**：本卡是 review 設計時要看的「scope 軸 + 標題對齊軸」的具體 instance。Review 不只看 frame / instance / surface、還要看「內容範圍跟標題承諾是否對齊」、是 scope 軸的延伸應用。

---

## 判讀徵兆

| 訊號                                                                    | 該做的事                                                             |
| ----------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 文章某段佔 > 20% 篇幅、但不在標題暗示的主題範圍                         | 縮成一兩句塞進事件本身、cross-link 到處理該議題的對應文章            |
| Widen Options / Reality Test 內容獨立成段                               | 改成內嵌進「事件本身」段一兩句、不展開完整分析                       |
| Source citation 列舉「a16z、Sequoia、Andreessen」這類沒具體出處的 prior | Verify 不到就改 hedged claim（「業界普遍觀察」）、不列 specific 名字 |
| 段落寫成「source 公開 X、所以 X 成立」                                  | 順序錯、改成「解釋本身 + 附加 source attribution」                   |
| 完稿後讀者反饋「文章寫了很多東西、但跟標題主題不一致」                  | 標題對齊測試失敗、要把不在標題承諾範圍的段落瘦身或移除               |
| Reviewer 報告「文章主體 30% 在講次要議題」                              | Scope mismatch、跑標題對齊測試 + 重寫                                |

---

## 適用範圍與邊界

- **適用範圍**：
  - 用 WRAP 框架寫商業 case-analyses、市場事件拆解、產業策略分析
  - 任何「標題承諾 vs 文章主體 scope」可能不對齊的情境（深度教學文章、技術 deep-dive、產業分析）
  - 文章標題明確指涉特定主題、但寫作過程容易被相關但非標題承諾的分析吸引展開
- **不適用**：
  - 探索式 essay（標題本來就模糊、scope 由內文展開）
  - 短篇 commentary（內容篇幅不夠展開 scope mismatch）
  - 純技術 reference（標題承諾的是「查得到」、不是「主題聚焦」）
- **邊界**：本卡禁的是「WRAP 內部分析喧賓奪主」、不是禁所有 WRAP 內部分析出現在文章。標題承諾本身就是「拆解 X 動機」的文章（例如 fde-arms-race 主題就是供應商為什麼押 FDE）、那 WRAP 內部分析才是文章主體、屬於正當對齊。判別線：標題承諾的主題跟 WRAP 分析的對象是否一致。一致就展開、不一致就壓縮成 cross-link。
