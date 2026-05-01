---
title: "Mitigation 對位：防護對應到具體 threat 的驗證"
slug: "mitigation-threat-alignment"
date: 2026-05-01
weight: 102
description: "資安寫作裡 mitigation 寫得乾淨不代表對到 threat、必須讓「mitigation X → 防 threat Y」的對應鏈可被反向驗證。常見失效模式：mitigation 攔的是 threat 的 surface artifact、不是 mechanism；mitigation 跟 threat 在不同抽象層；mitigation 假設 threat 已被上層擋掉但上層沒擋。對位驗證的 audit 模板：每個 mitigation 列出「設計攔的 threat」+「驗證 mechanism」+「失效訊號」三欄、缺一即 false sense of security 產地。"
tags: ["report", "事後檢討", "工程方法論", "資安", "Audit", "Mitigation", "原則"]
---

## 核心原則

**資安 mitigation 對讀者有意義的不是「mitigation 存在」、是「mitigation 跟 threat 的對應鏈成立」。** 對應鏈拆三段——`設計上 mitigation X 攔 threat Y` + `攔的 mechanism 是 Z` + `Z 失效時的訊號是 W`——任一段空、mitigation 在實作端就會跟 threat 錯位、變成「看似在防、實際只擋表面 artifact」的 defense theater。

| 對應鏈段落                     | 缺失時的後果                                                                 |
| ------------------------------ | ---------------------------------------------------------------------------- |
| 攔什麼 threat（設計 in-scope） | mitigation 變裝飾、讀者實作時不知道測試該擋什麼                              |
| 攔的 mechanism                 | mitigation 對位到 threat 表面 artifact、不是攻擊 mechanism、變體攻擊立刻繞過 |
| 失效訊號                       | mitigation 失效時讀者不知道、靠 silent assumption 撐著                       |

三段都齊、reader 才能反向驗證實作有沒有達到設計強度。

---

## 情境

資安章節常見的論述形態：給 mitigation 名稱（rate limit、CSRF token、prepared statement）+ 對應 threat 名稱（brute force、CSRF、SQLi）。表面對位、底層 mechanism 沒交代。讀者讀「prepared statement 防 SQLi」、實作時用 string concat + escape function、心裡覺得「我擋 SQLi 了」——因為原文只給 mitigation/threat 對應、沒給 mechanism（parameterization 跟 escape 是兩種不同 mechanism、抗的攻擊面不同）。

實際 case 的失效模式有三類：

### 失效模式 1：Mitigation 攔表面 artifact、不是攻擊 mechanism

```text
論述：rate limit 擋 brute force
讀者實作：per-IP rate limit
攻擊 mechanism：分散來源（botnet）每個 IP 低頻率、整體高頻率
結果：mitigation 攔到的是「單 IP 高頻」表面、不是「身分嘗試」mechanism
```

對位該寫的是「rate limit 攔『單來源高頻嘗試』、不攔『身分嘗試』本身」——mechanism level 的對位、不是名稱對位。

### 失效模式 2：Mitigation 跟 threat 在不同抽象層

```text
論述：CSP 擋 XSS
讀者實作：CSP header 設 default-src 'self'
Threat 抽象層：XSS 是 injection class、有 reflected / stored / DOM 三類
Mitigation 抽象層：CSP 是 browser-side execution policy
結果：CSP 擋「未授權 script 執行」、不擋 stored XSS 在 DB 已 persist 的階段
```

對位該寫 mitigation 在抽象層的位置——CSP 在 browser 執行層、不在 input 處理層。讀者光看「CSP 擋 XSS」會以為 input sanitization 不必做。

### 失效模式 3：Mitigation 假設上層 threat 已擋

```text
論述：bcrypt 防 password DB 外洩後 brute force 還原
讀者實作：bcrypt 存 password
被忽略的 threat：DB 外洩前 - phishing / credential stuffing / weak password
結果：bcrypt 是「外洩後」的 last line、不是 password security 的 first line
```

對位該寫 mitigation 在 defense-in-depth 的層次跟前提——bcrypt 在「**假設** DB 外洩」的條件下成立、不擋外洩前的 threat。讀者沒拿到前提、會以為 bcrypt 是 password security 的 sufficient solution。

---

## 理想做法

每個 mitigation 段落補三欄對位：

### 三欄對位模板

```text
[Mitigation X]
- 攔的 threat：[具體攻擊行為、不是攻擊類別名稱]
- 攔的 mechanism：[X 在什麼層擋 / 擋的是 mechanism 的哪一步]
- 失效訊號：[reader 能觀察到 mitigation 有沒有發揮的具體現象]
```

例（per-IP rate limit）：

```text
per-IP rate limit
- 攔的 threat：單來源連續嘗試（同 IP 短時間多次 login）
- 攔的 mechanism：在 single-source 維度限制 attempt rate、攻擊者必須切 IP 才能繞
- 失效訊號：分散來源（多 IP 各自低頻）的 aggregate 嘗試率、per-IP rate limit metric 不會 trigger
```

例（bcrypt password hashing）：

```text
bcrypt
- 攔的 threat：DB 外洩後 password 被離線 brute force 還原
- 攔的 mechanism：work factor 控制 hash 計算成本、攻擊者每次嘗試的成本不可優化
- 失效訊號：weak password / 已知 password 在 dictionary 中、攻擊者不需 brute force 全 space
- 前提：上層擋住 phishing / credential stuffing、bcrypt 是 last line、不是 first line
```

### 對位的層次規則

對位驗證要在三個層次都對齊：

| 層次         | 對位的形態                                                       |
| ------------ | ---------------------------------------------------------------- |
| 名稱層       | mitigation 名稱 → threat 名稱（最弱、容易裝飾）                  |
| Mechanism 層 | mitigation 擋的攻擊 mechanism → threat 的具體 mechanism          |
| 前提層       | mitigation 成立的前提 → 前提失效時的 fallback / upstream control |

只到名稱層 = defense theater；到 mechanism 層 = 可實作驗證；到前提層 = 可疊加 defense-in-depth audit。

### 對位 audit 的工具方法

對 mitigation 群組做集合運算：

```text
1. 列章節所有 mitigation 跟對應 threat
2. 對每對 (mitigation, threat) 補 mechanism + 前提
3. 集合化：聯集所有 mitigation 攔的 mechanism、聯集所有 threat 的 mechanism
4. 找 gap：threat 集合裡沒被 mitigation 集合涵蓋的 mechanism
5. Gap 處理：補 mitigation / 標 out-of-scope（[#101](../threat-model-explicitness/)）/ 升級到 defense-in-depth 上層
```

集合運算讓對位錯誤跟覆蓋 gap 從「靠感覺」升級到「可量化」。

---

## 沒這樣做的麻煩

### Defense theater 在 audit 跟 implementation 都通過、生產系統有破口

只到名稱層對位的 mitigation、audit 工具看到「rate limit 已部署」會 pass、implementation 看到「CSRF token 已加」會 pass、threat 還在——攻擊者用 mechanism 變體（分散來源 / DOM XSS / stored injection）繞過、mitigation 集體 silent 失效。**對位錯誤的 mitigation 跟沒 mitigation 在攻擊者眼中等價、但對 audit / 對讀者不等價**——這個 gap 是 defense theater 的本質。

跟 [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/) 同骨：mitigation 名稱對位是字面層、mechanism 對位是行為層、前提對位是 contextual 行為層。stop at 字面層 = false confidence。

### Mitigation 變體跟 threat 變體無法 trace

新 threat 出現（如 credential stuffing 之於傳統 brute force）、reader 必須重新評估既有 mitigation 是否還對位。對位鏈寫到 mechanism + 前提的 mitigation 可被 trace（per-IP rate limit 的 mechanism 是 single-source 限制、credential stuffing 是分散來源、不對位、需新 mitigation）；只到名稱層的 mitigation 不可 trace（rate limit vs credential stuffing：名稱看起來「應該擋」、實際不擋）。寫作時的 mechanism / 前提投資、是給未來 threat evolution 留的 review 入口。

### Mitigation 疊加時的責任邊界含糊

多個 mitigation 共防一個 threat、若各自不寫 mechanism + 前提、疊加時無法判斷「誰負責什麼層」。修補某個 mitigation 時不知道會不會影響其他 mitigation 的前提、變更冒險成本上升。明示 mechanism + 前提 = 明示 mitigation 之間的 dependency、修補成本可控。

---

## 跟其他抽象層原則的關係

| 原則                                                                                        | 關係                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [#82 字面攔截 vs 行為精煉](../literal-interception-vs-behavioral-refinement/)               | **本卡是 #82 在 mitigation 設計層的具體化** — mitigation 名稱對位 = 字面層、mechanism 對位 = 行為層、前提對位 = contextual 行為層；stop at 名稱層 = false confidence          |
| [#86 Capability gap 三層對策階梯](../capability-gap-three-layer-escalation/)                | **同骨對位邏輯** — #86 是 capability gap 的 L1/L2/L3 對應；本卡是 mitigation 在「名稱 / mechanism / 前提」三層對應；都在說「層次選對才有效」                                  |
| [#75 主策略 + 補強策略](../main-strategy-plus-supplementary/)                               | **疊加 mitigation 的對位** — #75 是多策略疊加判準（解不同層 / 沒副作用衝突 / 增量成本可接受），本卡補「疊加時各 mitigation 的 mechanism 跟前提要明示」、不然 #75 的判準沒法跑 |
| [#100 False sense of security 主要失敗模式](../false-sense-of-security-as-primary-failure/) | **#100 的 dimension 2** — 對位失效是 false sense 的第二大產地（dimension 1 是 threat model 不對稱、見 [#101](../threat-model-explicitness/)）                                 |
| [#101 Threat model 明確性](../threat-model-explicitness/)                                   | **本卡的上游前提** — #101 確立 threat space 的 scope、本卡確立 mitigation 在 scope 內的 mechanism 對位；threat model 不清的話 mitigation 對位無從談起                         |
| [#99 資安教學審查標準對應風險不對稱](../security-teaching-rigor-asymmetry/)                 | 上游動機 — verifiability-first 的具體實現之二（#101 是 dimension 1、本卡是 dimension 2）                                                                                      |

---

## 判讀徵兆

| 徵兆                                                          | 該做的事                                                                                       |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Mitigation 段只寫「X 防 Y」、沒寫 mechanism                   | 補 mechanism 層：X 在什麼抽象層擋、擋的是 Y 的哪一步                                           |
| Mitigation 用 threat 類別名稱（brute force / SQLi / XSS）對位 | 類別名稱太寬、specific 化到具體攻擊行為（單 IP 高頻 / payload boundary / stored vs reflected） |
| Mitigation 段沒寫前提、讀者不知道何時失效                     | 補前提層：mitigation 在什麼條件下成立、條件失效時的 upstream control                           |
| 多個 mitigation 並列、各自寫對應、沒寫疊加 dependency         | 補集合運算 audit、聯集 mechanism 集合 vs 整體 threat space                                     |
| Reviewer 讀完問「這跟 [新 threat 變體] 對到嗎？」             | 對位鏈停在名稱層、補 mechanism 讓變體可被 trace                                                |
| 「業界常用 X 防 Y」當論證                                     | Appeal to convention、補 mechanism 對位驗證、不能用「常用」代替                                |
| 章節開頭列 threat、結尾列 mitigation、中間沒對位鏈            | 補對位段、把兩個列表 link 成 (threat, mitigation, mechanism, 前提) 表                          |

---

## 適用範圍與邊界

- **適用**：資安 mitigation 設計（auth / crypto / 防護 / 標準 control）的論述；任何「方法 → 問題」對應的高 stakes 領域（concurrency primitive 對 race 類別 / consensus 演算法對 failure mode / financial control 對 risk 類別）
- **不適用**：純概念 / 歷史介紹（不教 mitigation）、研究探討（讀者預期自行 explore mechanism）
- **邊界**：「對位驗證」≠「列出每個攻擊變體」——mechanism 層列到攻擊行為的根 mechanism 即可、不必列所有 surface 變體；判別準則是「reader 能不能用這個 mechanism 描述去判斷新變體攻擊是否在 mitigation 覆蓋內」
- **過度對位反例**：每個 mitigation 寫 mechanism + 前提 + 三層 scope qualifier + 五種失效訊號、文章變 audit checklist、不是教學；mitigation 對位的投資量級對應 mitigation 在系統的責任比重——核心 mitigation（auth / crypto primitive）值得三層完整對位、輔助 mitigation（log redaction / banner notice）只到 mechanism 層即可

本卡是資安 audit 第二個維度（mitigation 對位）、配 [#101](../threat-model-explicitness/) threat model 明確性、後續 #103 context-dependence、#104 citation 形成完整 audit dimension 集合。
