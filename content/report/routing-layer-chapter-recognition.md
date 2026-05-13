---
title: "章節已有 routing skeleton 走補強段、不空白擴章"
date: 2026-05-13
weight: 119
description: "章節結構分兩類：空白章節（threat scope / 問題節點表都待補）vs routing layer 章節（已有完整結構、case 庫缺位用 standard 引用承接）。擴章策略要對應結構——空白章節走 case-driven 大幅擴章；routing layer 章節走補強段（在現有結構內補 mechanism 深化）；誤判結構會引發 frame 重複展開或章節失衡"
tags: ["report", "事後檢討", "工程方法論", "Writing", "Chapter-structure"]
---

## 結論

擴章前先判章節結構類型、決定擴章策略：

| 章節類型            | 訊號                                                    | 擴章策略                                             |
| ------------------- | ------------------------------------------------------- | ---------------------------------------------------- |
| 空白章節            | 缺 threat scope / 問題節點表 / 風險邊界、structure 待建 | 走 case-driven 大幅擴章、建完整結構                  |
| Routing layer 章節  | 已有 threat scope + 問題節點表 + 風險邊界 + 案例觸發段  | 走 *補強段* 策略（在現有結構內補 mechanism 深化）    |
| 導讀 / 標準引用章節 | 用 framework（OWASP / NIST）為主、案例為輔              | 走 standard-driven、加 Last reviewed cadence、不擴章 |

擴章策略要對應結構 — 在 routing layer 章節空白擴章會引發 frame 重複展開或章節失衡。

---

## 跟 standard-driven 領域判讀的差別

[#118 standard-driven vs case-driven 領域判讀](../standard-driven-vs-case-driven-domain-judgment/) 看 *領域整體* 該用哪種策略。本卡看 *單一章節* 的結構類型決定擴章策略。

| 維度     | #118 領域判讀（領域級別）                                 | #119 章節辨識（章節級別、本卡）                                   |
| -------- | --------------------------------------------------------- | ----------------------------------------------------------------- |
| 看什麼   | 領域整體性質（議題穩定度 / standard 成熟度）              | 單一章節的結構（routing layer / 空白 / 標準引用）                 |
| 影響範圍 | 整個模組的寫作策略                                        | 單章的擴章方式                                                    |
| 互動關係 | 領域判讀為 standard-driven 時、所有章節走 standard-driven | 領域判讀為 case-driven 時、章節仍可能是 routing layer（走補強段） |

兩者互補：

- 領域 + 章節同 case-driven：走完整 case-first workflow（空白擴章）
- 領域 case-driven + 章節 routing layer：走補強段（在現有結構內補深化）
- 領域 standard-driven：所有章節用 standard 引用 + Last reviewed cadence

---

## 為什麼章節結構決定擴章策略

case-first workflow 之前預設「章節空白、case 庫驅動擴章」— 但實務中常遇到 *章節已有 routing layer skeleton* 的情境（如 backend/07 batch 1 紅隊核心安全 7 章）：

- 章節已有 *threat scope*（In-scope / Out-of-scope 路由）
- 已有 *問題節點表*（4-6 個問題節點 + 判讀訊號 + 風險後果 + 前置控制面）
- 已有 *風險邊界*（4-6 條升級條件）
- 已有 *案例觸發參考*（已 link 3-5 個 case）

這種章節 *不是空白*、是 *routing layer*。空白擴章會：

- 跟既有問題節點表結構衝突
- 把章節擴成厚重 case-driven 章節、失衡 routing 性質
- 引發 frame 重複展開（既有節點 + 新擴章節點都寫一遍）

正確策略：*補強段* — 在現有結構內補 mechanism 深化段、不重建結構。

---

## Routing layer 章節的判讀訊號

掃描章節時、看以下訊號判斷是否為 routing layer：

| 訊號                                                    | 屬 routing layer 章節 |
| ------------------------------------------------------- | --------------------- |
| 含「## 本章寫作邊界」段                                 | ✓                     |
| 含「## 本章 threat scope」段（In-scope / Out-of-scope） | ✓                     |
| 含「## 從本章到實作」段（Mechanism + Delivery chain）   | ✓                     |
| 含「## 問題節點（案例觸發式）」表格                     | ✓                     |
| 含「## 跨章議題交叉引用」段                             | ✓                     |
| 含「## 常見風險邊界」段                                 | ✓                     |
| 含「## 案例觸發參考」段                                 | ✓                     |
| 含「## 下一步路由」段                                   | ✓                     |
| 章節行數 80-120 行（已有完整結構但不厚重）              | ✓                     |

含 4+ 個訊號 → 屬 routing layer 章節、走補強段策略。

---

## 補強段策略

在 routing layer 章節內補 case-driven 深化段、遵守以下紀律：

### 1. 補強段位置

通常放在「問題節點表」後、「常見風險邊界」前：

```markdown
## 問題節點（案例觸發式）

| 問題節點 | ... | ... |

## [新增補強段：對應某問題節點的 mechanism 深化]

[補強內容、case 引用三段式]

## 常見風險邊界
```

### 2. 補強段的範圍紀律

- 每個補強段對應 1-2 個既有問題節點、不擴新議題
- 不重建 threat scope / 問題節點表（保留 routing 性質）
- 補的 mechanism 深化要明示「本節聚焦 X 視角、canonical 在 Y 章」（避免 frame 重複）

### 3. Cross-link 密度上升

補強段要明示「跟其他章節的視角分工」、否則 reviewer C 會抓 frame 重複展開：

```markdown
## 高權限工具的會話收斂節奏

身分被取得後、token 撤銷跟 session kill 的時間窗口直接決定攻擊者可觸及的
資產面積、是初始落點橫向擴散的關鍵節流點。會話收斂節奏的 canonical 在
[7.5 § 會話重放跟全域失效](../transport-trust-and-certificate-lifecycle/#會話重放跟全域失效canonical)、
本節從身分層補 token 撤銷窗口的 specific 訊號。

對應 [Slack 2022 case]：...
```

---

## 07 batch 1 實證

backend/07 batch 1 七章節（identity-access / secrets / entrypoint / transport / credential-rotation / audit / workload-identity）走補強段策略：

- 章節原本 80-100 行、補強後 100-140 行（+20-40 行 / 章）
- 每章補 2-3 個 mechanism 深化段、對應既有問題節點
- 三個 H issue（C-H1/H2/H3）都是 frame 重複展開、補強段紀律失效引起
- 修正後加 cross-link 明示「canonical 在 X 章、本節補 Y 視角」、frame 重複收斂

對照 backend/06 reliability 模組（章節空白擴章）：

- 章節原本 30-50 行、擴章後 80-90 行
- 每章建 mechanism + 訊號 + 反模式完整結構
- 沒有 routing skeleton 衝突問題

兩種策略對應不同章節初始狀態、不互斥。

---

## 反模式

| 反模式                                            | 後果                                |
| ------------------------------------------------- | ----------------------------------- |
| 在 routing layer 章節空白擴章、忽略既有問題節點表 | Frame 重複展開、章節失衡            |
| 補強段沒明示「canonical 在 X 章、本節補 Y 視角」  | Reviewer C 抓 H issue、SSoT 不清    |
| 補強段重建 threat scope / 問題節點表              | 章節結構衝突、原 routing 性質被破壞 |
| 沒先判章節類型、直接套 stage 2 寫作               | 走錯策略、擴章失敗                  |
| Routing layer 章節擴成厚重 case-driven 章節       | 失衡 routing 性質、跨章導讀路徑斷掉 |

---

## 跟其他抽象層原則的關係

| 原則                                                                                               | 關係                                                             |
| -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [#118 Standard-driven vs Case-driven 領域判讀](../standard-driven-vs-case-driven-domain-judgment/) | 互補 — 一個是領域判讀、一個是章節結構判讀                        |
| [#44 Single Source of Truth](../single-source-of-truth/)                                           | 補強段要明示「canonical 在 X 章」是 SSoT 紀律的具體應用          |
| [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)                          | 空白擴章比補強段便利、但便利會偏離意圖（routing 性質）           |
| [#115 案例引用深度跟著 case 類型走](../case-type-graded-citation-depth/)                           | 補強段內 case 引用紀律的 prerequisite                            |
| [#83 Writing multi-pass review](../writing-multi-pass-review/)                                     | 輪 2（對意圖）的具體實作 — 寫補強段時要對齊章節原有 routing 意圖 |

---

## 判讀徵兆

| 訊號                                              | 該做的事                                          |
| ------------------------------------------------- | ------------------------------------------------- |
| 章節已有完整 threat scope / 問題節點表 / 風險邊界 | 走補強段、不空白擴章                              |
| 章節 80-120 行、結構完整但內容不厚重              | Routing layer 章節、補強段策略                    |
| 章節 30-50 行、缺結構                             | 空白章節、走 case-driven 大幅擴章                 |
| Reviewer C 抓 frame 重複展開 H issue              | 補強段紀律失效、補「canonical 在 X 章」cross-link |
| 章節擴章後失衡 routing 性質                       | 退回原章節、補強段重寫、保留 routing layer 結構   |
| 想在 routing layer 章節重建 threat scope          | 紀律失效訊號、改用補強段策略                      |

**核心**：擴章策略要對應章節結構、不是「所有章節都走 case-driven 大幅擴章」。Routing layer 章節走補強段、保留原 routing 性質、補 mechanism 深化即可。
