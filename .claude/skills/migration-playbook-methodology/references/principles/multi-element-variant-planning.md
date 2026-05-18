# Multi-element variant planning

> **角色**：本卡是 `migration-playbook-methodology` 的支撐型原則、被 [SKILL.md](../../SKILL.md) Stage 0 段引用、補 [stage-0-variant-discipline](./stage-0-variant-discipline.md) 只 cover entry layer 的 gap。
>
> **何時讀**：批量寫 migration playbook（≥ 3 篇）+ 已做 entry framing variant 規劃、但發現 section 2+ 結構同骨化時。

## 核心原則

Variant 規劃要 cover *多個結構 element axis*、不只 entry framing。一篇 migration playbook 至少有 5 個結構位置會 collapse、stage 0 規劃要對每個 axis 列 N 種 variant、不重複。

5 個結構 element axis：

| Axis                 | 結構位置                           | Collapse 風險        |
| -------------------- | ---------------------------------- | -------------------- |
| **Entry framing**    | 章節 1 H2 標題 + 開頭段落           | 高（主題語意 attractor）|
| **Driver framing**   | 章節 2「為什麼遷」格式             | **極高（5/5 collapse 在連續兩輪 dogfood）** |
| **Audit presentation** | 6 維 audit 表呈現方式（標準表 vs narrative） | 中 |
| **Case enumeration** | 5 個 production case 編排（按 phase / 按 mechanism / 按 stakeholder）| 中 |
| **Closing CTA**      | 結尾 cross-link / 整合 / 下一步段框架 | 低 |

跟 [stage-0-variant-discipline](./stage-0-variant-discipline.md) 對照、該卡只規範 *Entry framing axis*；本卡擴張到全 5 axis。

## 為什麼必須

第六輪 migration batch dogfood（驗證假設）結果：

| Axis              | 第五輪 (passive) | 第六輪 (validation) |
| ----------------- | ---------------- | ------------------- |
| Entry framing     | **0/5 collapse**（active variant）| **0/5 collapse**（active variant）|
| Driver framing    | **5/5 collapse**（passive）| **5/5 collapse**（passive）|

連續兩輪 N=5 driver framing 都 100% collapse 到「為什麼遷：X / Y / Z 三條 driver」格式 — 是 *systematic gap*、不是偶然。

關鍵 finding：

- **Entry layer 0% collapse 不代表整篇 cadence 健康** — 章節 2+ 結構位置仍 collapse
- **Section 2「driver framing」是最高風險位置**：因為主題語意 attractor「migration 都有 X / Y / Z driver」自然引導；不主動規劃就 collapse
- **Stage 0 規劃要 cover 多 axis、不只 entry**

## Driver framing variant 列表

從前批跟新議題抽出 10 種 variant for *章節 2 driver framing*：

| Driver framing variant | 描述                                                | 適用                                  |
| ---------------------- | --------------------------------------------------- | ------------------------------------- |
| α 標準 driver list     | 「為什麼遷：X / Y / Z 三條 driver」                  | 簡單明確情境（baseline、容易 collapse）|
| β reverse: 為什麼不遷  | 「為什麼大家不切？X / Y 反向 driver」                | 反向決策內容（保留 source 仍合理時）  |
| γ Decision matrix      | Driver × cost benefit 對照表、不是 list             | 多 driver 並重 + cost trade-off       |
| δ Customer voice       | 「3 個 production team 的真實 driver」              | Case-based driver（避開抽象 driver）  |
| ε Cost reality check   | 「$X / month → $Y / month」具體數字                  | Cost-driven migration                 |
| ζ Risk envelope        | 「不遷的風險：A / B / C」reverse view                 | 合規 / EOL / security driver          |
| η Capability gap       | 「Source 撞 X feature ceiling、target 解 Y」         | Feature / scalability driver          |
| θ Org dynamics         | 「Team 變動 / vendor relationship 轉變」             | Politics / vendor consolidation       |
| ι Tech debt narrative  | 「累積 N 年 debt、cutover window 終於 open」          | Long-overdue migration                |
| κ Comparison anchor    | 「業界 X% 已切、我們是 laggard」                     | Competitive driver                    |

**Stage 0 規劃 N 篇要對 N 種 driver framing variant 分配**、跟 entry framing variant 平行規劃。

## Stage 0 規劃擴張流程

```text
Step 1: 列預計寫的批量 N 篇主題

Step 2: 對 5 個 element axis 分配 variant
  - Entry framing (A-J): 每篇選 1 個、N 篇不重複
  - Driver framing (α-κ): 每篇選 1 個、N 篇不重複
  - Audit presentation: 標準表 / narrative / 隱含
  - Case enumeration: phase-based / mechanism-based / stakeholder-based
  - Closing CTA: 對位 list / decision tree / open question

Step 3: 5 axis × N 篇 → 規劃矩陣
  - 每 axis 內 N 種選擇不重複
  - 跨 axis 組合對主題自然 fit

Step 4: 寫前 audit
  - 每篇 stage 0 規劃矩陣 review
  - 確認 5 axis variant 對映主題本質

Step 5: 寫到第 ceil(N/2) 篇後跑跨檔抽樣
  - 5 axis 各 grep 對應結構位置
  - 發現 drift 立即補變體
```

## 反模式

| 反模式                                          | 後果                                                |
| ----------------------------------------------- | --------------------------------------------------- |
| 只規劃 entry framing variant、忽略 section 2+   | Driver framing 5/5 collapse（已連續兩輪 evidence）  |
| 把 multi-element variant 規劃當 nice-to-have    | Section 2 cadence collapse 不可逆、batch 寫完才發現 |
| Variant α-κ 強迫對映 N 篇、不准 invent          | 主題不 fit existing variant 時硬塞、變體扭曲      |
| Audit presentation 全部用標準表                  | 6 維 audit 變儀式、不傳達 type 判讀                |
| Case enumeration 全 phase-based                  | 跨篇 case 編排骨架同質、reader 看到「又是 5 case」  |
| Stage 0 規劃跑半小時、寫作 30 小時              | Investment ratio 1:60、value-add 邊際遞減          |

## 跟其他原則的關係

| 原則                                                                  | 關係                                                                |
| --------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [stage-0-variant-discipline](./stage-0-variant-discipline.md)         | **父卡** — 該卡規範 entry framing variant；本卡擴張到 5 axis 全 element |
| [six-dimension-audit-framework](./six-dimension-audit-framework.md)   | 互補 — audit 決定主結構、multi-element variant 決定 5 axis framing  |
| [self-aware-limitation-pattern](./self-aware-limitation-pattern.md)   | Trigger 來源 — multi-element collapse 是該模式驗證 Phase 3a / 3b 切換條件的具體 case |

## 自查清單

寫批量 migration playbook 前：

1. **5 個 element axis 都規劃 variant 了嗎**？只 entry layer 不夠
2. **Driver framing 是不是 α 標準 list**？多數情境 α 是 anchor、但 N 篇別都 α
3. **Audit presentation N 篇是否變化**？全用標準 6 維 audit 表是 ritualization 風險
4. **Case enumeration 跨篇是否分組**？避免「又是 5 case」骨架
5. **Stage 0 投入時間 vs 寫作時間比例 1:30 內**？超過 1:30 是過度規劃

## Threshold

Multi-element variant planning *值得做* 的 N 閾值：

- **N ≥ 3 篇**：必做 entry + driver framing 兩 axis variant
- **N ≥ 5 篇**：必做 entry + driver + 1 個其他 axis（audit / case / closing）
- **N ≥ 10 篇**：必做 5 axis 全規劃 + stage 0 中段抽樣
- **N = 1-2 篇**：variant 規劃 optional、用 *單篇* 內部變化即可
