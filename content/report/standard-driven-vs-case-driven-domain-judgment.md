---
title: "Standard-driven 取代 Case-driven 適用 standard framework 比 case 庫成熟的領域"
date: 2026-05-13
weight: 118
description: "並非所有領域都該走 case-driven。判斷該用哪種策略看四維度：議題穩定度 / case 公開度 / standard 成熟度 / 維護半衰期。LLM 安全屬 standard-driven 領域（OWASP LLM Top 10 + NIST AI RMF 已成型、case 半衰期 6 個月）；分散式系統 / 安全控制面屬 case-driven 領域（case 公開充分、半衰期 5+ 年）。誤套會導致 case 庫過早建構或 case 過時"
tags: ["report", "事後檢討", "工程方法論", "Writing", "Methodology-selection"]
---

## 結論

寫教學內容前要先判讀領域該走 case-driven 還是 standard-driven、看四維度：

| 維度            | Case-driven 適用              | Standard-driven 適用                     |
| --------------- | ----------------------------- | ---------------------------------------- |
| 議題穩定度      | 高（5+ 年穩定）               | 低（< 1 年快速演進）                     |
| Case 公開度     | 高（充分的事故公告）          | 中或低（vendor disclosure 偏 marketing） |
| Standard 成熟度 | 中（多用 case 而非 standard） | 高（standard framework 已成型）          |
| 維護半衰期      | 長                            | 短（6 個月過時）                         |

**典型對照**：

- *Case-driven 領域*：分散式系統 / 安全控制面 / 可靠性 / 訊息佇列（案例公開充分、半衰期 5+ 年）
- *Standard-driven 領域*：LLM 安全（OWASP LLM Top 10 / MITRE ATLAS 已成型、案例 6 個月過時）、新興 compliance（NIST AI RMF）、cloud-native 標準（CNCF baseline）

Standard-driven *不是* case-first 的退化版、是該領域的 *正確策略*。

---

## 為什麼這個 axis 重要

之前的 case-first workflow 預設「沒 case 庫的新主題、要先建 case 庫」— 這暗示缺 case 庫一定要先補。LLM 安全章節驗證了 *第三條路*：

當該領域的 *標準框架*（如 OWASP LLM Top 10 2025 / NIST AI RMF 1.0 / MITRE ATLAS）已涵蓋 threat 分類、且 case 維護半衰期短於 standard、章節應 *用 standard-driven 取代 case-driven*。

誤套的代價：

- **誤套 case-driven 到 standard-driven 領域**：建 case 庫 8-12 小時、6 個月後 case 過時、變成維護負擔
- **誤套 standard-driven 到 case-driven 領域**：章節停留在標準引用、漏掉真實事故才會浮現的議題、scope 盲點

---

## Standard-driven 章節的寫作策略

當判讀領域屬 standard-driven、章節採以下策略：

### 1. 章節對齊 standard framework 分類

用 framework 章節 ID 標明（如 OWASP LLM01 / NIST AI-1.1）取代「對應 [case] —」斷言。

```text
本章的 threat scope 對應 OWASP LLM Top 10 LLM01（Prompt Injection）+
LLM02（Insecure Output Handling）、NIST AI RMF 1.0 MEASURE-2.7。
```

### 2. 加 Last reviewed cadence

每 quarter 重評估 standard 版本跟章節對應、寫進 frontmatter：

```yaml
---
title: "..."
date: 2026-05-12
description: "..."
tags: ["backend", "security", "llm"]
---

> Last reviewed: 2026-05-12（對齊 OWASP LLM Top 10 2025）
```

### 3.「案例觸發參考」段標明「公開案例累積中、值得追蹤的方向」

不寫「對應 [case] 揭露」斷言、避免引用源不穩定：

```markdown
## 案例觸發參考

LLM agent prompt injection 的公開案例累積中、值得追蹤的方向：

- email assistant 場景：閱讀含 injection 的郵件、誘導 agent 觸發外送或洩漏
- coding agent 場景：讀含 injection 的 PR / issue、誘導 agent 修改非預期檔案
- 跨 agent chain：injection 在 sub-agent 累積、影響 parent agent 決策

> **事實查核註**：LLM agent prompt injection 是 2024-2025 快速演進的研究領域、
> 攻擊形態、防禦模式、公開案例都在累積中。建議引用前以 OWASP LLM Top 10、
> 近期論文跟主流 vendor 的 incident 公告為準。
```

### 4. 引用標準時用版本號

OWASP LLM Top 10 **2025** / NIST AI RMF **1.0** / MITRE ATLAS **continuous** — framework 改版要 trigger 章節重審。

引用源規範見 [#104 security citation 時效精確](../security-citation-currency-and-precision/)。

---

## 何時要從 standard-driven 轉回 case-driven

下列 tripwire 出現時、重新評估：

| Tripwire                                                            | 行動                                     |
| ------------------------------------------------------------------- | ---------------------------------------- |
| 該領域累積 5+ 個高可信度 case（vendor + academic + CVE 三來源交叉） | 補完整 case 庫、走 case-first workflow   |
| 跨章 frame 重複出現、SSoT 衝突明顯                                  | case-driven mechanism 深化能解 SSoT 衝突 |
| 出現「等級類似 SolarWinds」的 incident                              | 補單個 case、視為 high-impact reference  |
| 讀者反饋章節太抽象、需要具體 case 才能理解 mechanism                | 補 single high-impact case、不全建庫     |

不滿足任一條件時、繼續走 standard-driven、不勉強建 case 庫。

---

## 07 LLM 章節實證

backend/07 batch 2（LLM 安全 5 章）驗證 standard-driven 策略：

- 章節 113-137 行、含完整 threat scope + 問題節點表 + 風險邊界
- 引用 OWASP LLM Top 10 + NIST AI RMF + MITRE ATLAS 取代個別 case 引用
- 加 `Last reviewed: 2026-05-12` cadence
- 「案例觸發參考」段寫「公開案例累積中、值得追蹤的方向」+「事實查核註」
- 完全不寫「對應 [case] —」斷言、不存在 case fidelity reviewer 該抓的準確性問題

對照 backend/01-07 batch 1 的 case-driven 章節、LLM 章節是 *用不同方法達到同樣品質* — scope 涵蓋真實 production 議題（KV cache 跨租戶、shared prefix optimization、batch 推論順序敏感）、不停在教科書級內容。

---

## 反模式

| 反模式                                         | 後果                                                                 |
| ---------------------------------------------- | -------------------------------------------------------------------- |
| 假設「沒 case 庫一定要先建」                   | 在 standard-driven 領域過早投入建 case 庫、6 個月後過時              |
| Standard-driven 章節沒加 Last reviewed cadence | Standard 改版時章節未更新、引用變過時                                |
| Standard-driven 章節寫「對應 [case] —」斷言    | 引用源不穩定（vendor disclosure 偏 marketing）、case fidelity 風險高 |
| Case-driven 領域只用 framework 引用、不用案例  | 漏掉真實事故議題、章節停在教科書級                                   |
| 沒判讀領域類型、直接套 case-first workflow     | 浪費 8-12 小時建 case 庫、得不到對應 ROI                             |

---

## 跟其他抽象層原則的關係

| 原則                                                                                | 關係                                                                 |
| ----------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| [#115 案例引用深度跟著 case 類型走](../case-type-graded-citation-depth/)            | Case-driven 適用時的 prerequisite — 先判 case 類型再決定承接深度     |
| [#119 章節已有 routing skeleton 走補強段](../routing-layer-chapter-recognition/)    | 互補 — 一個是領域判讀、一個是章節結構判讀                            |
| [#104 security citation 時效精確](../security-citation-currency-and-precision/)     | Standard-driven 章節的 citation 紀律核心                             |
| [#99 security teaching 嚴格度對應風險不對稱](../security-teaching-rigor-asymmetry/) | 高 stakes 內容（含 LLM 安全）的審查標準                              |
| [#83 Writing multi-pass review](../writing-multi-pass-review/)                      | Standard-driven 章節跑輪 E（高 stakes）+ standard 版本對齊（輪 E.5） |

---

## 判讀徵兆

| 訊號                                               | 該做的事                                                       |
| -------------------------------------------------- | -------------------------------------------------------------- |
| 想寫某領域章節、找不到合適 case 庫                 | 先判四維度、可能該走 standard-driven、不是先建 case 庫         |
| Case 引用 6 個月後發現過時、要重寫                 | 領域屬 standard-driven、改用 framework + Last reviewed cadence |
| Standard framework 改版（OWASP 出新版）            | 章節 Last reviewed 重審、補對應 framework ID                   |
| 該領域累積 5+ 個高可信度 case                      | Tripwire 觸發、考慮從 standard-driven 轉回 case-driven         |
| Vendor disclosure 多偏 marketing、case fidelity 低 | 該領域 case 可信度不足、走 standard-driven 更穩定              |
| 想引用 case 但找不到 academic / CVE 三來源交叉     | Case 公開度不足、改用 standard framework                       |

**核心**：寫教學內容的策略選擇要看領域性質、不是預設「先建 case 庫」。Case-driven 跟 standard-driven 各有適用情境、誤套會浪費資源（建過早 case 庫）或降低品質（章節停在教科書級）。
