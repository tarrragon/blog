---
title: "Threat model 明確性：「防什麼」與「不防什麼」必須對稱"
slug: "threat-model-explicitness"
date: 2026-05-01
weight: 101
description: "資安 mitigation 的論述要對稱寫「防什麼 threat」+「不防什麼 threat」。只寫前者、讀者會自行 universal 詮釋（防所有相關攻擊）、實際只擋作者腦中 subset、是 false sense of security 的主要產地。對稱論述不是讓文章變負面、是讓 mitigation 的 scope qualifier 顯式化、讓讀者能驗證實作覆蓋邊界。"
tags: ["report", "事後檢討", "工程方法論", "資安", "Audit", "Threat Model", "原則"]
---

## 核心原則

**寫資安 mitigation 必須對稱：每段「防什麼」要配「不防什麼」、不能單邊寫。** 讀者沒拿到「不防 Y」、會用 universal validity 詮釋 mitigation——預設「防 X」涵蓋整個 threat space、實際只是 X 的 subset。Threat model 的 boundary 是 mitigation 論述的一部分、不是補充說明、不能省。

| 寫法                                                | 讀者會形成的結論   | 結論的 scope              | 實作覆蓋率              |
| --------------------------------------------------- | ------------------ | ------------------------- | ----------------------- |
| 「使用 HTTPS 保護傳輸」                             | HTTPS 防傳輸風險   | 全部傳輸風險（universal） | subset（中間人 read）   |
| 「使用 HTTPS 防中間人讀取、不防 endpoint 信任失效」 | HTTPS 防 X、不防 Y | 顯式 scope                | 對應 X、reader 知道補 Y |

差別在於讀者實作時的覆蓋判斷——前者讀完跳過 endpoint 驗證、後者讀完知道要補 Y。

---

## 情境

資安寫作有兩個誘因會讓 threat model boundary 被省略：

1. **正向陳述優先**規範（AGENTS.md §1 原則二）會誤把「不防 Y」歸類為負面句、批量改寫時刪掉、跟 [#94 正向改寫保留對照論據](../positive-rewrite-preserves-contrast/) 同病
2. **章節篇幅控制**會把 threat boundary 當成「進階補充」往後丟、留主章節「乾淨主旨」

兩者都會產出 universal-flavored 的 mitigation 句子。讀者讀「使用 X 即可保護 Y」時、Y 會被腦補成「所有 Y 相關攻擊」、X 跟 Y 之間的 scope 配對被 silent 地放大成 universal。

實際資安章節（`backend/07-security-data-protection/`）會出現的形態：

```text
判讀訊號：登入驗證節奏失衡
前置控制面：authentication / incident-severity
```

這個寫法把 threat 抽象成「節奏失衡」、把 mitigation 抽象成「authentication」——對熟手 OK、對學習者讀完會以為「用 authentication 就擋節奏失衡」、實作時不會去問 authentication 的局部 scope（防 credential 弱、不防 session 重放、不防 supply chain 信任傳導）。

---

## 理想做法

每個 mitigation 句子強制走「對稱論述」結構：

### 對稱論述模板

```text
[Mitigation X] 防 [in-scope threat A]、
不防 [out-of-scope threat B]（[B 的補強路由 / 外部引用]）。
```

三個欄位都要填：

- **In-scope threat**：X 真正擋的攻擊類型（具體、不抽象）
- **Out-of-scope threat**：讀者最容易誤以為 X 也擋的攻擊（讀者直覺會 extrapolate 的方向）
- **補強路由**：Y 該由什麼補（其他章節 / 外部標準 / 已知條件）、不能只丟「自己想辦法」

例（HTTPS 章節）：

```text
HTTPS 防中間人「讀取」傳輸內容（passive eavesdrop）、
不防 endpoint 「身分驗證」失效（compromised CA / cert pinning bypass）、
endpoint 信任靠 cert pinning + CT log monitoring 補（見 7.5）。
```

例（per-IP rate limit）：

```text
per-IP rate limit 擋「單來源」連續嘗試（brute force from single host）、
不擋「分散來源」嘗試（botnet / credential stuffing）、
分散攻擊靠 reputation-based filtering + adaptive challenge 補（見 7.3）。
```

### 對稱不是「補負面」、是「scope 顯式化」

跟 [#94 正向改寫保留對照論據](../positive-rewrite-preserves-contrast/) 同骨：「不防 Y」不是負向陳述、是 mitigation 的 scope qualifier。把 contrast 寫進句子、不是違反「正向陳述優先」、是讓主句的 X claim 站得住。

| 違反「正向陳述優先」              | 符合「正向陳述優先」 + 對稱 boundary    |
| --------------------------------- | --------------------------------------- |
| 「不要忘了 X 不防 Y」（命令）     | 「X 防 A、不防 B（B 由 C 補）」（陳述） |
| 「Y 是 X 的限制」（負面 framing） | 「X 的 scope 是 A」（正面 framing）     |

主句仍然承載 X 的 mitigation claim（正向）、不防 Y 是 scope qualifier、不是論述主體——結構符合「正向陳述優先」、語意保留 boundary。

### Threat model 的層級對應

對稱論述要在三個層級保持一致：

| 層級   | 對稱 threat model 的形態                                      |
| ------ | ------------------------------------------------------------- |
| 章節級 | 章節 lead 段列出整體 threat scope + 不在 scope 的 threat 路由 |
| 段落級 | 每個 mitigation 段配對應 threat 跟 boundary                   |
| 句子級 | 「X 防 A、不防 B」單句承載                                    |

三個層級任一缺、reader 都可能 silent universal 詮釋。實作 audit 時三層分別檢查、不是只看句子。

---

## 沒這樣做的麻煩

### Reader 用 universal 詮釋、實作覆蓋永遠是 worst case

人類讀句子時、預設的 scope 是 universal、不是 minimal——這是語言學跟認知偏差的結合。「使用 X 防 Y」讀者預設 X 防整個 Y space。要讓讀者預設 minimal、必須**顯式給 boundary**——這跟物件的 type narrowing 同骨：沒寫 narrowing predicate、預設 widest type。

跟 [#100 false sense of security](../false-sense-of-security-as-primary-failure/) 主軸對應——universal 詮釋是 false sense 的主要產地。

### Reviewer 跟原作者對 mitigation 的 scope 認知會 silent drift

含糊 threat model 的 mitigation 段、不同 reviewer 讀會 reconstruct 出不同的 in-scope 集合。原作者腦中是 [A, B]、reviewer 讀成 [A, B, C, D]、實作者實作為 [A, B, C, D, E]——三個人對同一段話的覆蓋認知都不同、且都覺得自己對。對稱寫法讓 scope 變成 fact、不是 reconstruction。

### 多 mitigation 疊加時的 gap 永遠看不到

多個 mitigation 各自寫 in-scope、不寫 out-of-scope、疊加時的 gap（哪個 threat 沒人擋）就看不到。對稱寫法讓每個 mitigation 都有顯式 boundary、疊加 audit 時可以做集合運算（聯集 in-scope 應涵蓋 threat space、否則有 gap）。沒對稱寫法、audit 工具只能憑感覺、無法量化覆蓋。

---

## 跟其他抽象層原則的關係

| 原則                                                                                        | 關係                                                                                                                                                  |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| [#100 False sense of security 主要失敗模式](../false-sense-of-security-as-primary-failure/) | **本卡是消滅 #100 的具體 dimension 1** — universal 詮釋是 false sense 的主要產地、對稱論述是直接的 mitigation                                         |
| [#94 正向改寫保留對照論據](../positive-rewrite-preserves-contrast/)                         | **同骨 sibling** — #94 在寫作規範執行層、本卡在資安寫作層、都在說「contrast 是論述完整性的一部分、不能為了正向化而刪」                                |
| [#43 最小必要範圍是 sanity 防線](../minimum-necessary-scope-is-sanity-defense/)             | **scope explicitness 同骨** — #43 在 JS 邊界 / selector / observer scope、本卡在 mitigation 的 threat scope、都在說「scope 不顯式 = 失控的 widening」 |
| [#99 資安教學審查標準對應風險不對稱](../security-teaching-rigor-asymmetry/)                 | 上游動機 — #99 立論「為什麼要 verifiability-first」、本卡是 verifiability 的具體實現之一                                                              |
| [#80 Yes/No 二選 collapse](../yes-no-binary-collapse/)                                      | 「X 防 Y 嗎」的 yes/no 詮釋是 collapse、對稱論述是把多維度（A 防 / B 不防 / 由 C 補）展開回多軸                                                       |

---

## 判讀徵兆

| 徵兆                                                    | 該做的事                                                                      |
| ------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Mitigation 段只寫 in-scope、沒寫 out-of-scope           | 補對稱論述、加 out-of-scope + 補強路由                                        |
| 「使用 X 防 Y」單句、Y 是抽象詞（傳輸風險 / 身分風險）  | Y 太寬、specific 化 Y 的 in-scope subset、列出 out-of-scope 補 boundary       |
| 章節 lead 段沒列整體 threat scope                       | 補章節級 threat model、確立 scope qualifier 的 anchor                         |
| 多個 mitigation 段並列、各自寫 mitigation、沒寫疊加 gap | 補疊加 audit、聯集 in-scope vs 整體 threat space、找 gap                      |
| 把「不防 Y」寫成獨立警告段、跟 mitigation 分開          | 對稱論述應該同句承載、分開寫會被讀者跳過或當成「進階補充」                    |
| Reviewer 讀完問「那 Z 攻擊呢？」                        | Z 在 reader 直覺 in-scope、原文沒對稱寫、補 Z 為 out-of-scope 並標路由        |
| 「之後讀者實作時會自己想到 boundary」                   | 是 [#72](../external-trigger-for-high-roi-work/) 結構性跳過、補 audit trigger |

---

## 適用範圍與邊界

- **適用**：所有資安 mitigation 論述（auth / crypto / 傳輸 / 防護 / 標準引用）；高風險領域的「方法論述」（concurrency primitive 的 ordering 保證、distributed consensus 的 failure mode）
- **不適用**：純歷史 / 概念介紹文章（不教 mitigation、不需 threat model）、研究探討（讀者預期自行 explore boundary）
- **邊界**：「對稱論述」≠「列出所有不防的 threat」——只列讀者直覺會 extrapolate 的方向、不是 enumerate 整個 threat space。判別準則：「讀者讀完 X 防 A 之後、心裡最可能誤以為 X 也防的 B 是什麼？」——B 就是該寫的 out-of-scope
- **過度對稱反例**：每個 mitigation 列十個 out-of-scope threat、文體變 audit-driven（為了 audit checklist 而寫）、不是 reader-driven（為讓讀者建立可驗證 mental model 而寫）；單一 mitigation 的 out-of-scope 通常 1-2 個直覺 extrapolation 方向就夠、列 10 個 = 把 audit 模板當成寫作目標、退化成 #67 寫作便利度反向

本卡是資安 audit 第一個維度（threat model）、配 #102 mitigation 對位、#103 context-dependence、#104 citation 形成完整的 audit dimension 集合。
