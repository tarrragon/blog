---
title: "Audit recommendation 層級：accept / minor / major / 教錯不可保留"
slug: "security-audit-recommendation-tiers"
date: 2026-05-01
weight: 105
description: "資安 audit 的產出不該是「OK / 不 OK」二選、要分層給 ship 決策用：accept（無 weakness）/ minor revise（補 boundary 級小改）/ major revise（結構性 false sense、需重寫）/ withdraw（教錯主動誤導、必須移除或全換）。前三層對應學術 peer review、第四層是資安 audit 特有——當內容會 silent 把 reader 帶向破口時、保留是淨負面、不存在「先 ship 後改」的選項。"
tags: ["report", "事後檢討", "工程方法論", "資安", "Audit", "Decision", "原則"]
---

## 核心原則

**資安 audit 的 recommendation 是 ship 決策、不是評語。** 把每個 weakness trace 到具體 tier、輸出可被 build process / publish gate 引用——不該停在「這裡可改善」的軟性建議。四個 tier 是 monotonic decision shape：

| Tier         | 意涵                             | Ship 決策                       |
| ------------ | -------------------------------- | ------------------------------- |
| Accept       | 無 weakness 或全在容忍範圍       | 直接 ship                       |
| Minor revise | 邊界 / contrast / 版本標記類小改 | 補完即可 ship、不阻擋 timeline  |
| Major revise | 結構性 false sense / 對位失效    | 重寫對應段、ship 前必須修復     |
| **Withdraw** | 內容主動誤導、ship = 增加 risk   | **必須移除或全換、不存在 ship** |

第四層是資安 audit 跟一般學術 peer review 的關鍵差異——學術 reject 會給投稿者改寫機會、本 audit 的 withdraw 是「**保留 = 增加生產系統 risk**」的硬決策。跟 [#76 incremental shipping criteria](../incremental-shipping-criteria/) 反向：可逆內容可分批 ship 改善、不可逆 risk 內容不能。

---

## 情境

audit 報告若只給「找到 N 個問題」的 flat list、團隊收到後無法決策、最後常變成「慢慢改」、article ship 跟 audit 改善的 timeline 完全脫鉤。Tier 化的 recommendation 把 weakness 轉成決策訊號：

```text
Flat list（沒層級）：
- 第 3 段沒寫 threat model boundary
- 第 5 段 mitigation 沒寫 mechanism
- 第 7 段引用 OWASP 沒標版本
- 第 9 段 bcrypt work factor = 10、針對 nation-state 弱

決策結果：「都有問題、找時間改」、實際上幾個月不會動

Tiered（分層）：
- Withdraw: 第 9 段 bcrypt work factor 描述會直接讓 reader 用 weak setting、必須改寫或移除
- Major revise: 第 5 段 defense theater、整段重寫 mechanism + 前提
- Minor revise: 第 3 段補 threat model 對稱、第 7 段補 OWASP 版本

決策結果：第 9 段必須現在改、第 5 段下個 sprint 改、第 3/7 段順手補
```

層級給的是「**先做什麼 / 什麼擋 ship / 什麼可緩**」的明確排序、不是改善優先序的軟建議。

---

## 理想做法

### 四 tier 判準

每個 weakness 套這個決策樹：

```text
Q1：reader 照這段實作會不會主動產生破口？
  是 → Withdraw（不可保留）
  否 → Q2

Q2：weakness 是結構性（多 dimension 同時失效）還是局部（單一 dimension 缺）？
  結構性 → Major revise
  局部 → Q3

Q3：補完 weakness 的 cost 是「補一句 / 一表」還是「重寫一段」？
  一句 / 一表 → Minor revise
  重寫一段 → Major revise

Q4：weakness 在容忍範圍（背景段 / 低 stakes 段、reader 不會直接照做）？
  在 → Accept（可選 minor 但不要求）
  不在 → 走 Q3
```

### 各 tier 的 fix 模式

| Tier         | Fix 模式                                                 | Ship gate              |
| ------------ | -------------------------------------------------------- | ---------------------- |
| Accept       | 無 fix 或自願性 minor                                    | 不阻擋                 |
| Minor revise | 補 boundary / 加 contrast / 標版本 / 補連結              | 不阻擋（可 follow-up） |
| Major revise | 重寫段落 + 補 mechanism / 前提 / context                 | 阻擋直到 fix 完成      |
| Withdraw     | 移除整段 / 加 deprecation banner + redirect / 全換現代版 | 阻擋直到處理           |

### Withdraw 的具體訊號

什麼狀態算 withdraw？四個訊號：

1. **過時 crypto / hashing primitive 沒 deprecation 標記**：教 MD5 / SHA-1 / 弱 PBKDF2 但沒明示「這是過時、不要用」
2. **扭曲 citation 改變原文語意**：把 OWASP conditional 引成 unconditional、或反向違反現行標準（NIST 的 password 定期更換 case）
3. **違反 current best practice 的步驟說明**：教讀者主動關閉 mitigation（disable HSTS / CSP / SameSite）作為 workaround、沒明示「workaround 引入的新 risk」
4. **Defense theater 例子當示範**：用名稱層 mitigation 對位（rate limit「擋」brute force）作為步驟、reader 照做不擋實際 mechanism

四訊號的共通：**reader 照做後實作會主動 worse than not having read**。Withdraw 不是嚴格、是 risk-asymmetric（[#99](../security-teaching-rigor-asymmetry/)）下的必要決策。

### Audit report 輸出格式

學術 peer review 的格式對應到本 audit：

```text
# Audit Report: <章節 / 文章 title>

## Summary
<1-2 句：主要 audit 結論 + 整體 tier>

## Strengths
- <段 / dimension 跟其優點>

## Weaknesses by dimension

### Threat model（[#101](../threat-model-explicitness/)）
- [Tier]: 段 N、[具體 weakness 描述]、[fix 建議]

### Mitigation 對位（[#102](../mitigation-threat-alignment/)）
- ...

### Context-dependence（[#103](../mitigation-context-dependence/)）
- ...

### Citation（[#104](../security-citation-currency-and-precision/)）
- ...

## Blocking conditions
<必須 fix 才能 ship 的 weakness 清單、按 tier 排序>

## Recommendation
<Accept / Minor revise / Major revise / Withdraw + 整體決策說明>
```

格式跟學術 peer review 同骨、欄位對應 audit dimension（#101-104）、輸出可直接餵 ship gate 工具。

---

## 沒這樣做的麻煩

### Audit 變評語、改善 timeline 跟 ship 完全脫鉤

flat list 的 audit 給「找到問題」、team 把問題列入 backlog、backlog 永遠排不到上面（[#72 高 ROI 無外部觸發會被結構性跳過](../external-trigger-for-high-roi-work/)）。tier 化讓 audit 從「評語」變「ship 決策 input」、跟 timeline 強耦合。

### Withdraw-level 內容繼續 ship、生產系統 risk 持續累積

最危險的 case 是 audit 找到 withdraw-level weakness（過時 crypto、扭曲 citation）但用 minor / major 處置——讓內容繼續存在並擴散。教學擴散 = silent gap 集體放大（[#100 false sense of security](../false-sense-of-security-as-primary-failure/)），withdraw 是 cut-off 訊號、不是嚴格、是必要。

### 各 tier 之間的決策邏輯模糊、reviewer 之間判準不一致

沒明確 tier 判準、不同 reviewer 對同一個 weakness 給不同建議——有人覺得「補一行就好」（minor）、有人覺得「整段重寫」（major）、有人覺得「移除」（withdraw）。決策不一致 = audit 失去結構性 value、退化成個人意見集合。tier 判準（決策樹四問題）讓判準可重現、跨 reviewer 收斂。

---

## 跟其他抽象層原則的關係

| 原則                                                                                        | 關係                                                                                                                                                                |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [#74 決策呈現：選項 + 推薦 + 開放修改](../decision-presentation-options-recommendation/)    | **同骨決策呈現** — #74 是給 user 決策的 options + recommendation 模板、本卡是給 ship gate 的 tier + recommendation 模板；都把整理成本攤開、不丟「你想怎麼做」開放問 |
| [#76 分批 ship：低風險可見價值先行](../incremental-shipping-criteria/)                      | **反面對照** — #76 適用可逆內容、本卡的 withdraw 適用不可逆 risk 內容、分批 ship 邏輯不適用；本卡是 #76 在 risk-asymmetric 領域的硬邊界                             |
| [#79 決策對話的五個維度](../decision-dialogue-dimensions/)                                  | **本卡的決策維度** — #79 是 meta、本卡是其中「呈現 + 策略疊加 + 批次」三維在 audit 報告的具體實現                                                                   |
| [#91 升級 trigger 的量化設計](../escalation-trigger-quantification/)                        | **withdraw 是 blocking trigger** — #91 在 capability 升級的 trigger 設計、本卡的 withdraw 是 ship 阻擋的 trigger；都是「沒明確 trigger = 不會 fire」                |
| [#100 False sense of security 主要失敗模式](../false-sense-of-security-as-primary-failure/) | **本卡是消滅 #100 的 ship 決策面** — #101-104 是發現 false sense 的維度、本卡是發現後的處置決策                                                                     |
| [#99 資安教學審查標準對應風險不對稱](../security-teaching-rigor-asymmetry/)                 | 上游動機 — risk-asymmetric 直接驅動 withdraw tier 的存在；一般 audit（一般教學）只需要 accept / minor / major、資安 audit 必須加 withdraw                           |
| [#80 Yes/No 二選 collapse](../yes-no-binary-collapse/)                                      | **避免 collapse** — 「audit 通過嗎」是 yes/no collapse、tier 化是把 1 bit 展開成 4 個 monotonic 層級、保留決策維度                                                  |

---

## 判讀徵兆

| 徵兆                                                       | 該做的事                                                                               |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Audit 結論是「找到 N 個問題」flat list                     | 把每個 weakness 跑 tier 決策樹、輸出 tier-grouped report                               |
| 找到過時 crypto / 扭曲 citation 但給 minor revise          | 升級到 withdraw、ship gate 必須阻擋                                                    |
| 「之後改善」「下個版本補」當 weakness 處置                 | 是 [#72](../external-trigger-for-high-roi-work/) 結構性跳過、補 ship gate 強制 trigger |
| 不同 reviewer 對同 weakness 給不同 tier                    | 補決策樹、跑判準收斂                                                                   |
| Audit pass 但實作後事故、回溯到 audit 沒 catch 的 weakness | 補 weakness 到對應 dimension（#101-104）、檢查 tier 判準是否需調整                     |
| 沒「strengths」段                                          | 補 strengths、reviewer 視角不只 weakness、strengths 是 audit completeness 的訊號       |
| Recommendation 沒明確 ship gate 對應                       | 補 blocking conditions 段、明示哪些 tier 阻擋 ship                                     |

---

## 適用範圍與邊界

- **適用**：資安內容 audit 的產出格式（章節 audit / 文章 audit / 跨章節 review）；任何「reader 照做後錯誤不可逆」的高 stakes 領域 audit（concurrency 正確性、distributed consistency、financial / medical 計算）
- **不適用**：一般技術內容 audit（不需要 withdraw tier、accept / minor / major 三層即可）、研究探討文章的 review（學術 reject 跟 withdraw 語意不同）
- **邊界**：「Withdraw」≠「全文重寫」——可以是「移除有問題的段 + 加 deprecation 標 + redirect 到 current best practice 段」、不必整篇重做；判別準則：「reader 看到這個處置版本後、會不會用過時 / 扭曲版本實作？」——不會 → withdraw 處置 OK、會 → 需要更深的處置（移除整段 / 整篇）
- **過度 tier 化反例**：把每個段都評 tier、文章變評分表、reviewer 投資爆炸；tier 投資量級對應內容對 reader 實作的影響——核心 mitigation 段需 tier、background 段直接 accept 即可

本卡是資安 audit 系列（#99-105）的決策面收尾、把 #101-104 四個 dimension 的 weakness 統合成 ship 決策。後續對應的 skill reference（`auditing-articles.md`）會以本卡的 tier + report 格式為輸出模板。
