---
title: "Security 標準引用的時效性與精確度"
slug: "security-citation-currency-and-precision"
date: 2026-05-01
weight: 104
description: "資安 citation 跟一般技術引用不同——best practice 時效短（MD5 / SHA-1 / bcrypt 100k / TLS 1.0 都曾是 best practice）、原文常被引用扭曲（conditional → unconditional drift）、版本不標 reader 會套用過時 spec。citation 同時涵蓋外部標準（OWASP / RFC / NIST / CIS）跟內部 citation（knowledge-cards / 跨章引用作為 control-of-record）；後者因無版本號 anchor 反而更易 silent drift / broken。每條 citation 必須附：版本 / 年份、引用句意可回溯、deprecated / superseded 標記、強度參數對應 actor 能力的 review trigger（外部）/ last-checked + sync owner（內部）。"
tags: ["report", "事後檢討", "工程方法論", "資安", "Audit", "Citation", "原則"]
---

## 核心原則

**資安標準引用不是「這條 control 寫在 X 文件」、是「這條 control 在 X 版本 X 年份 X 語境下對 X actor 模型成立」。** 五個變數任一變、引用就過時或扭曲。資安 best practice 衰退快、universal-flavored 引用（「OWASP 建議 X」「RFC 規定 Y」）會 silent 把過時或語境外的內容傳給 reader、產生 [#100 false sense of security](../false-sense-of-security-as-primary-failure/) 的 citation 維度產地。

| 引用形態                                      | reader 套用時的判斷               | 過時 / 扭曲時的後果                |
| --------------------------------------------- | --------------------------------- | ---------------------------------- |
| 「OWASP 建議 X」                              | X 是 universal best practice      | 套用時 OWASP 已改版、reader 不知道 |
| 「OWASP Top 10 (2021) 建議 X、原文：『...』」 | X 在 2021 OWASP Top 10 語境下成立 | 過時時 reader 知道要 check 新版    |

差別在 reader 在實作 review 階段有沒有版本變數可檢查、有沒有原文語境可驗證。

---

## 情境

資安標準群（OWASP / RFC / NIST SP 800 系列 / CIS Benchmark / PCI DSS / ISO 27001）有三個跟一般技術文獻不同的特性：

### 特性 1：Best practice 衰退速度快

加密 / hashing 領域是最典型例子：

```text
1995-2005：MD5 是 password hashing 常見選擇
2005-2010：MD5 deprecated、改 SHA-1
2010-2015：SHA-1 弱、改 bcrypt
2015-2020：bcrypt 仍 OK、PBKDF2 100k iter 仍 OK
2020-2026：建議升 argon2id、PBKDF2 推 600k+、bcrypt work factor 推 12+
```

任何 2020 年寫的「使用 bcrypt 即可」教學在 2026 年仍部分成立、但 work factor 推薦值已 outdated。沒標年份的引用 reader 沒有 review trigger。

### 特性 2：原文常被引用扭曲

引用 chain 中常見的 drift：

```text
原文（OWASP Cheat Sheet）：In contexts where session fixation is a concern, consider regenerating the session ID upon login.
中介轉述：OWASP says regenerate session ID upon login.
進一步引用：OWASP requires session regeneration on every login.
最終讀者：「OWASP 強制要求每次 login 都 regenerate session」
```

語意從「conditional 建議」滑成「universal 強制」、原文的 conditional context（「session fixation is a concern」）被丟。Reader 套用時把 conditional 當 unconditional、可能在不需要的地方加複雜度、或在需要的地方因為「我已經做了」跳過 threat model 重新評估。

### 特性 3：版本之間語意可能反轉

OWASP Top 10 / NIST SP 800 系列、版本之間的 control 重點會大幅調整：

```text
OWASP Top 10:
  2017 → A1 Injection / A7 XSS
  2021 → A03 Injection（含 XSS、合併）/ A08 Software and Data Integrity Failures（新類別）
NIST SP 800-63B:
  2014 版：強制 password 定期更換
  2017 版：明示**不要**強制定期更換、除非有外洩證據
```

引用「NIST 建議定期更換 password」在 2014 對、2017 後是反向違反 NIST。版本不標 = reader 可能引用到反向版本。

### 特性 4：Internal citation 也是 citation

問題節點 / problem-node 框架的章節常用內部連結（`[authentication]` `[session-invalidation]` 等 knowledge-cards）作為「control-of-record」，把實作細節下放到子頁。這些內部連結**等同 citation**——指向「這個 control 由那一頁定義」、章節讀者在這層形成判斷、再決定是否點進去。

Internal citation 同樣有四個失效模式：

| 失效模式           | 外部 citation（OWASP / RFC）        | Internal citation（knowledge-cards / 跨章引用）       |
| ------------------ | ----------------------------------- | ----------------------------------------------------- |
| 時效衰退           | OWASP 改版、引用過時版本            | knowledge-cards 內容更新、章節引用沒同步              |
| 句意 drift         | conditional → unconditional 轉述    | 章節用 control-name 暗示能力、子頁定義跟暗示不一致    |
| 版本反轉           | NIST 2014 vs 2017 password 政策反向 | knowledge-card rewrite、原本 in-scope 變 out-of-scope |
| Broken / dead link | URL 變更、文件下架                  | knowledge-card 改 slug / 移檔、章節連結 silent broken |

外部 citation 至少有版本號當 anchor、internal citation 連版本概念都沒有——更易 silent drift。所以 audit 跟 review trigger 對 internal 反而更嚴格。

---

## 理想做法

每個 security citation 加四個欄位：

### 四欄位引用模板

```text
[Citation X]
- 標準 / 文件：[全名 + 版本 + 年份]
- 原文 / quote：[原文一句、不轉述]
- 引用 scope：[原文適用的 context / actor model / 前提條件]
- Review trigger：[何時要 re-check 標準是否有新版]
```

例（password hashing）：

```text
- 標準：OWASP Password Storage Cheat Sheet（2024 update）
- 原文：「Use Argon2id with a minimum configuration of 19 MiB of memory, an iteration count of 2, and 1 degree of parallelism」
- Scope：Web 應用 password hashing、針對個人 / 組織 actor、不適用 nation-state actor 或 high-throughput verification
- Review trigger：每 12 月 re-check OWASP cheat sheet 是否有新建議；GPU 算力翻倍時提前 re-check
```

例（session 管理）：

```text
- 標準：OWASP Session Management Cheat Sheet（2024 update）
- 原文：「Session ID should be regenerated after any privilege level change (e.g., after a successful authentication or after a session token has elevated privileges)」
- Scope：Web session ID rotation、conditional 在 privilege level change 時、不是「每次 request」也不是「每次 login」（對 already-authenticated session）
- Review trigger：當 application 加入新的 privilege boundary（如 admin elevation）時 re-check
```

### 引用扭曲的 audit 流程

對章節既有引用跑驗證 pass：

```text
1. 列出所有 citation（外部：標準 / RFC / CVE；內部：knowledge-cards 連結 / 跨章引用）
2. 對每條 citation 找一手來源、記錄 URL + 版本 + 年份（外部）/ 最後修改 + slug（內部）
3. 對比文中轉述跟原文 / 子頁定義、check 三類 drift：
   - Conditional → unconditional drift（原文有條件、文中沒條件）
   - Specific → general drift（原文限特定 context、文中講通用）
   - Recommendation → mandate drift（原文是 consider / recommend、文中是 must / required）
4. drift 找到、補回原文 conditional / scope / language strength
5. 標版本跟 review trigger（外部）/ 標 last-checked + sync owner（內部）
6. 內部專屬 check：連結是否 broken（slug 改了 / 檔案移了）、子頁是否仍存在 / 仍 in scope
```

集合運算讓引用扭曲從「靠記憶」升級到「可驗證」。Internal citation 多兩個專屬步驟（broken link + slug drift）、跟 [#93 URL slug 必須顯式定義為 fact](../url-slug-must-be-explicit-fact/) 同骨——identifier 跨工具 / 跨檔案沒 fact 化、就會 silent broken。

### Review trigger 的 cadence 設計

不同類型 citation 的 review cadence 不同：

| Citation 類型                | 建議 review cadence                                           |
| ---------------------------- | ------------------------------------------------------------- |
| Crypto primitive 強度參數    | 每 6-12 月（actor 算力會變）                                  |
| OWASP Top 10 / Cheat Sheet   | 每 12-24 月（major 改版頻率）                                 |
| RFC（已 finalized）          | 每 24-36 月（除非有新 RFC supersede）                         |
| CVE / 特定漏洞               | 即時（一次性事件、不需 cadence、引用後標記「fixed in vX.Y」） |
| **Internal knowledge-cards** | **每 6 月（內部演化快、無版本號當 anchor）**                  |
| **跨章 / 跨模組引用**        | **每次大改子頁時 broadcast；無 broadcast 時每 6 月 sweep**    |
| NIST SP 800 系列             | 每 24 月（NIST 改版頻率）                                     |
| PCI DSS / ISO 27001          | 每 24-36 月（合規標準改版頻率）                               |

跟 [#91 升級 trigger 的量化設計](../escalation-trigger-quantification/) 同骨——「之後再 review」不是 trigger、有 cadence + owner + threshold 才是 trigger。

---

## 沒這樣做的麻煩

### 過時 citation silent 變成過時實作

reader 信任引用、用 citation 內容實作、citation 過時後實作不知道、新 best practice 沒被採用。Crypto 領域最常見：MD5 / SHA-1 / 弱 PBKDF2 iteration / 過時 cipher suite 在生產系統留存幾十年的案例不少、原因常常是「教學 / spec 沒更新、實作跟著沒更新」。

跟 [#100 false sense of security](../false-sense-of-security-as-primary-failure/) 同病、citation 維度的具體展現：reader 以為「我用了標準推薦」就安全、實際標準早改、自己用的是 deprecated 版本。

### 扭曲 citation 把 conditional 變強制 / 把 specific 變通用

引用扭曲的後果有兩面：

- **Conditional → unconditional**：reader 在不需要的地方加複雜度、團隊成本上升、卻不解決真 threat
- **Specific → general**：reader 把特定 context 的 control 套到不同 context、可能 silent 失效

兩面都讓 mitigation 跟 threat 對位錯誤（[#102 mitigation-threat-alignment](../mitigation-threat-alignment/)）。

### 引用 chain 越長、扭曲累積越嚴重

教學 → 教學 → 教學 的 chain 中、每一層轉述都可能 drift。citation 沒回到一手原文、整條 chain 共享同一個扭曲、攻擊者繞過扭曲版的 mitigation 一次、所有採用該 chain 的 implementation 都中。**citation 的時效跟精確不是個別文章問題、是 ecosystem 問題**——一手原文 + 版本 + 原文 quote 是 minimum cost 的修法。

---

## 跟其他抽象層原則的關係

| 原則                                                                                        | 關係                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [#97 Metadata surface 要納入寫作 review](../metadata-surface-in-writing-review/)            | **citation 是 metadata surface 的延伸** — citation 是讀者的「外部 source」入口、跟 title / heading / link label 並列為 metadata；本卡是 #97 在引用維度的展開                                                                                                                              |
| [#93 URL slug 必須顯式定義為 fact](../url-slug-must-be-explicit-fact/)                      | **identifier 同骨 + internal citation 強相關** — slug 是內部 identifier、外部 citation / 內部 citation 都需要 explicit fact（版本 / 年份 / 原文 / slug + last-checked）；internal citation 沒版本號當 anchor、跟 #93 SSoT 違反同類風險、broken-link / drift 是 internal citation 專屬失效 |
| [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/)               | **同骨 ceiling** — 引用標準名稱 = 字面、引用句意對到原文 context = 行為；stop at 字面 = false confidence                                                                                                                                                                                  |
| [#91 升級 trigger 的量化設計](../escalation-trigger-quantification/)                        | **review trigger 同骨** — #91 在 capability 升級的 trigger 設計、本卡在 citation review 的 cadence 設計；都是「沒 trigger = 結構性跳過」                                                                                                                                                  |
| [#100 False sense of security 主要失敗模式](../false-sense-of-security-as-primary-failure/) | **#100 的 dimension 4** — citation 過時 / 扭曲是 false sense 的第四大產地（dimension 1-3 = threat / mitigation / context、本卡 = 引用 source）                                                                                                                                            |
| [#99 資安教學審查標準對應風險不對稱](../security-teaching-rigor-asymmetry/)                 | 上游動機 — verifiability-first 的 dimension 4                                                                                                                                                                                                                                             |

---

## 判讀徵兆

| 徵兆                                                                                                   | 該做的事                                                                               |
| ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| 引用「OWASP / NIST / RFC / CIS」沒標年份 / 版本                                                        | 補版本 + 年份、確認當前是否仍是 current                                                |
| 引用是轉述、沒原文 quote                                                                               | 找一手來源、補原文 quote、check 是否被 drift                                           |
| 「OWASP **建議** X」「RFC **規定** Y」當 universal                                                     | 補 scope（在什麼 context / actor model 下成立）                                        |
| Crypto / hashing 強度參數是固定值（10 / 100k / 32 char）                                               | 補 review trigger（每 6-12 月 re-check actor 算力跟標準）                              |
| Citation 是「最佳實踐」「業界標準」當 anchor、沒列具體文件                                             | 補具體標準名稱 + 版本、不能用 vague reference                                          |
| 章節寫於 N 年前、沒提 last reviewed 日期                                                               | 補 last reviewed 標記、設下次 review trigger                                           |
| Conditional 原文被引成 unconditional（「強制」「必須」「總是」）                                       | 找原文 conditional context、補回 scope qualifier                                       |
| 「之後標準改了再更新」                                                                                 | 是 [#72](../external-trigger-for-high-roi-work/) 結構性跳過、補 review cadence + owner |
| 章節用 internal link（knowledge-cards / 跨章引用）作為 control-of-record、沒 last-checked / sync owner | 等同未驗證的 citation；補 last-checked + sync owner、子頁大改時 broadcast 到引用方     |
| Internal link 連結還在但目標頁 slug / 內容已改、章節原本暗示的 control 跟現在不對應                    | Silent broken / drift；定期跑連結 sweep + 文意對比、跟外部 citation 同流程處理         |

---

## 適用範圍與邊界

- **適用**：資安內容引用標準（auth / crypto / 傳輸 / 防護 / 合規）；**內部 citation**（knowledge-cards 連結、跨章 / 跨模組引用作為 control-of-record）；任何 best practice 衰退快、版本之間語意會反轉的領域（cloud security 配置、container 安全、特定 framework 的安全 idiom）
- **不適用**：純歷史 / 概念介紹（不依賴 current best practice）、學術 retrospective（討論 historical 標準時版本本身是內容）
- **邊界**：「citation 時效跟精確」≠「窮舉所有版本變更」——只列當前文章涵蓋 scope 的 citation、追到一手 + 版本 + scope qualifier 即可；判別準則：「如果這條 citation 過時或語境變、reader 會做錯什麼？」——會做錯 → 補完整四欄位；不會做錯（純歷史 reference）→ 標年份即可
- **過度引用反例**：每段話都附 citation 鏈 + 原文 quote + 三條 review trigger、文章變 footnote-driven、reader 讀不下去；citation 投資量級對應該段對 reader 實作的影響——核心 mitigation 段值得四欄位完整、background 段標版本 + URL 即可

本卡是資安 audit 第四個維度（citation）、配 [#101](../threat-model-explicitness/) / [#102](../mitigation-threat-alignment/) / [#103](../mitigation-context-dependence/) 形成完整 audit dimension 集合（threat / mitigation / context / citation）。後續 [#105 audit recommendation 層級](../security-audit-recommendation-tiers/) 把四維度的 weakness 統合成 recommendation 決策。
