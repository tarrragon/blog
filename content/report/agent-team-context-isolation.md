---
title: "Agent team context 隔離設計：用不同 instance 換 frame、平行 background 保護主 context"
date: 2026-05-13
weight: 121
description: "Multi-pass review 跨輪 frame（#83）跟跨 reviewer instance 隔離（本卡）是兩個 axis：#83 是同一 reviewer 換輪次 frame、本卡是不同 reviewer instance 各自獨立 background 跑；context 隔離設計讓主 context 只接精煉摘要、節省 ~80% token、跟同 reviewer 多輪 catch 同類錯（#114）形成互補解法"
tags: ["report", "事後檢討", "工程方法論", "Writing", "Agent-team", "Case-first-workflow"]
---

## 結論

Agent team context 隔離是 LLM-era review 工具設計的核心模式 — 用 N 個獨立 reviewer instance 各自跑 background、各自寫 output file、主 context 只接精煉摘要、不被 reviewer 細節污染。

| 設計面              | 紀律                                           | 效果                                                 |
| ------------------- | ---------------------------------------------- | ---------------------------------------------------- |
| Instance 隔離       | N 個專責 reviewer 各自獨立 context             | 維度盲點分開處理、不互相干擾                         |
| Background 平行     | 不阻塞主 context、可同時跑 3-5 個 reviewer     | 時間從序列 30 分鐘縮到平行 10 分鐘                   |
| 輸出檔案隔離        | Reviewer 寫 output file、不污染主 conversation | 主 context 增量 ~3K token、節省 ~80% context         |
| 主 context 只接摘要 | Reviewer 完成後回傳精煉彙整                    | 修正循環時 context 留給判讀、不被 raw issue 列表佔滿 |

跟 multi-pass review（#83）的差別：#83 是 *同一 reviewer 換輪次 frame*（生成 / 對意圖 / 機會成本 / grep / 反例）；本卡是 *不同 reviewer instance 各自獨立*（規範 / 案例準確 / 跨章一致 / compositional-writing 等）。兩者正交、可疊加。

---

## 跟 multi-pass review 的差別

| 維度     | #83 Multi-pass review                        | #121 Agent team context 隔離（本卡）                    |
| -------- | -------------------------------------------- | ------------------------------------------------------- |
| 軸定位   | Frame 軸（一個 reviewer N 輪不同 frame）     | Instance 軸（N 個 reviewer 各自獨立）                   |
| 解決問題 | Working memory 限制（一輪 catch 不到所有層） | Context 污染（單一 reviewer context 被 raw input 佔滿） |
| 適用對象 | Author / 單一 reviewer 跑多輪                | Agent team / 自動化平行 review                          |
| 失敗模式 | 跳輪 → 某維度永遠做一半                      | Instance 數量不足 → 維度覆蓋不全                        |

兩軸正交、可疊加 — 同一 reviewer instance 內跑 multi-pass（#83）、跨 reviewer instance 各自獨立（本卡）。Case-first stage 3 設計同時用兩軸：3 個 reviewer instance 各自獨立 + 每個 reviewer 內部跑多輪 frame check。

---

## 為什麼這層設計重要

單一 reviewer 同時處理多維度有兩個限制：

1. **維度盲點**：一個 reviewer 同時看寫作規範 + 案例準確性 + 跨章一致性、容易維度互相干擾、最後每個維度都看不深
2. **Context 污染**：reviewer 讀完整 commit + 所有案例 + 所有章節後、自身 context 被佔滿、給的建議也對應主 context 跟著沉重

Context 隔離解這兩個問題：

- 用 N 個專責 reviewer、各自只處理一個維度 → 維度深度提升
- Reviewer 各自 background、不污染主 context → 主 context 保留判讀空間
- Reviewer 寫 output file、不傳 raw 內容到主 context → 主 context 增量極少

---

## 設計紀律：何時用幾個 reviewer

Reviewer 數量決定取決於審查對象的維度複雜度：

| 審查對象                           | Reviewer 數 | 維度分配                                                                  |
| ---------------------------------- | ----------- | ------------------------------------------------------------------------- |
| Case-driven 章節擴章               | 3 個        | A 寫作規範 / B 案例引用準確性 / C 跨章一致性                              |
| 方法論 / 自我審查                  | 4 個        | A 寫作規範 / B 三方自一致性 / C 概念邊界 / D compositional-writing 6 原則 |
| 一般 PR review                     | 1-2 個      | 規範 + correctness、不需要 case fidelity 維度                             |
| 高 stakes 內容（資安 / financial） | 4-5 個      | 加 epistemic rigor reviewer（claim / evidence / threats）                 |

維度設計要對審查對象客製、不要固定一套維度套所有任務。

---

## 平行 background 的具體實作

Case-first stage 3 的實作 pattern：

```python
# Agent tool spawn 平行 background
for reviewer_id in ['A', 'B', 'C']:
    Agent({
        description: f"Reviewer {reviewer_id}: {dimension}",
        subagent_type: "general-purpose",
        run_in_background: True,
        prompt: get_reviewer_prompt(reviewer_id)
    })

# 主 context 不阻塞、繼續其他工作
# Reviewer 完成時主 context 接通知（task-notification）
# Reviewer 各自寫 output 到 /tmp/reviewer-{id}-report.md
# 主 context 讀 output 彙整、不讀 raw conversation transcript
```

關鍵設計選擇：

1. **`run_in_background: true`**：平行跑、不阻塞
2. **Reviewer 寫 output file**：報告寫 `/tmp/...` 不污染主 conversation
3. **主 context 不讀 reviewer transcript**：只讀 task-notification 的 summary + 最後讀 output file
4. **Reviewer prompt 含「不要佔我主 context、報告寫進檔即可」明示**：避免 reviewer 把 raw issue 都吐回主 conversation

---

## Reviewer 維度設計：跟著任務客製化

Reviewer 維度不該固定 — backend/07 batch 1 案例驅動章節用「規範 / 案例 / 跨章一致」三維度、方法論審查用「規範 / 三方自一致 / 概念邊界 / compositional-writing」四維度。

設計原則：

- **拆 axis 不重疊**：每個 reviewer 的維度跟其他 reviewer 互斥（如「規範」vs「案例準確性」是不同 axis）
- **覆蓋審查對象的關鍵風險**：審查 case-driven 章節要 case fidelity reviewer、審查方法論要三方自一致性 reviewer
- **預期 issue baseline 設好**：每 reviewer 給 prompt 預期數量、reviewer 不要過度抓 / 漏抓
- **prompt 含主 context 保護指令**：「報告寫到 /tmp/X-report.md、不要在主 conversation 吐 raw issue」

---

## 反模式

| 反模式                                                      | 後果                                             |
| ----------------------------------------------------------- | ------------------------------------------------ |
| 單一 reviewer 處理所有維度                                  | 維度盲點 + context 污染、品質下降                |
| Reviewer 不寫 output file、直接在 conversation 吐 raw issue | 主 context 被 issue 列表佔滿、修正循環沒空間     |
| Reviewer 維度固定不變、套所有任務                           | 維度跟審查對象不對齊、漏抓關鍵風險               |
| Reviewer 不平行、序列跑                                     | 時間成本高、序列 30 分鐘 vs 平行 10 分鐘         |
| Reviewer prompt 沒明示 baseline                             | Reviewer 抓 5 個或 50 個都「完成」、無法判讀品質 |
| 主 context 直接 Read reviewer transcript                    | 把 raw conversation 拉進主 context、context 污染 |

---

## 跟其他抽象層原則的關係

| 原則                                                                                            | 關係                                                                                                                            |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| [#83 Writing multi-pass review](../writing-multi-pass-review/)                                  | 互補 — #83 是 frame 軸（一個 reviewer N 輪）、本卡是 instance 軸（N 個 reviewer 各自獨立）、兩軸正交可疊加                      |
| [#114 Multi-pass review 的 frame 顆粒度盲點](../multi-pass-review-frame-granularity-blindspot/) | 解同類問題的不同手法 — #114 用「keyword bank / reader simulation / self-criticism」三機制擴大覆蓋、本卡用 instance 隔離擴大覆蓋 |
| [#67 寫作便利度跟意圖對齊反相關](../ease-of-writing-vs-intent-alignment/)                       | 同骨 pattern — 單一 reviewer 處理多維度最便利（不用 spawn / coordinate）、但意圖（深度 review）失準                             |
| [#42 兩次門檻](../two-occurrence-threshold/)                                                    | 跨機制 — 同 reviewer 多輪 catch 同類錯（#114）跟跨 reviewer instance（本卡）都是「換工具」的具體實作                            |

---

## 判讀徵兆

| 訊號                                           | 該做的事                                                  |
| ---------------------------------------------- | --------------------------------------------------------- |
| Reviewer 給的建議「對應主 context 也沉重」     | Reviewer context 被污染、改 background instance 隔離      |
| 主 context 修正循環時、不知道從哪個 issue 開始 | Reviewer 報告沒精煉、補 reviewer prompt 要求 summary 開頭 |
| 多個 reviewer 抓到同類 issue                   | 維度設計重疊、調整 reviewer 維度分配                      |
| Reviewer 序列跑、單次 review 30 分鐘以上       | 改平行 background、預期縮到 10 分鐘                       |
| 主 context tokens 在 review 階段增長過快       | Reviewer 沒用 output file、改 prompt 明示「報告寫進檔」   |
| 想複用 reviewer prompt 到不同任務              | 維度該重新設計、不是固定一套                              |

**核心**：Agent team context 隔離是 LLM-era review 工具的設計模式 — 用 instance 隔離換維度深度跟 context 保護。維度設計要對任務客製化、不要固定不變。
