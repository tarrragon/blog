---
title: "Cross-Reviewer Convergence：多 Reviewer 收斂的 finding 比單 Reviewer flag 信號強"
date: 2026-05-19
description: "Multi-reviewer audit（4-reviewer / N-reviewer parallel）後、finding priority 不該是 *N 個 reviewer 報告平均合併*、應該按 *跨 reviewer convergence* 加權 — 兩個獨立 reviewer 從不同 axis 各自發現同一 finding 是 *信號收斂*、比單 reviewer flag 信號強 5-10x。Case：MySQL 17 篇 4-reviewer audit、Reviewer A（寫作規範）跟 Reviewer B（跨檔一致性）獨立 flag 同一 finding『4 篇 migration playbook 缺 weight + banner』、是跨軸 convergence、是最 high-priority fix。機制：N 個獨立 axis 隨機 hit 同一 finding 的機率隨 N 增加而 exponential decline、convergence 排除噪音、是 signal-to-noise 的最高比訊號。修法：multi-reviewer audit 後做 *cross-reviewer matrix*、convergence column 自動標 priority bump。"
weight: 138
tags: ["report", "事後檢討", "工程方法論", "review", "audit"]
---

## 核心：跨 reviewer 收斂的 finding 信號強

當跑 multi-reviewer parallel audit（4-reviewer / N-reviewer）、最 high-priority 不是 *單一 reviewer flag 的 most severe finding*、是 *多個 reviewer 從不同軸獨立 flag 的同一 finding*。

直覺：

- 單 reviewer flag P0 finding 是 *該軸的判斷*
- 跨 reviewer convergence flag 是 *多軸共同 hit 同一點*、信號收斂

機制：N 個獨立 axis 隨機 hit 同一 finding 的機率隨 N 指數下降 — 兩個 axis 偶然 hit 同點機率低、三個 axis hit 同點機率更低。所以 convergence 排除 *單 reviewer 主觀 / 偏好 bias*、留 *系統性 issue*。

## Case：MySQL 4-reviewer audit

跑 4-reviewer audit（A 寫作規範 / B 跨檔一致性 / C 技術準確性 / D 結構性質疑）對 MySQL 17 篇：

| Finding                                    | Flagged by              | Convergence |
| ------------------------------------------ | ----------------------- | ----------- |
| 4 篇 migration playbook 缺 weight + banner | Reviewer A + Reviewer B | **2 軸**    |
| Frame uniformity（5 個踩雷 100% 重複）     | Reviewer A + Reviewer D | **2 軸**    |
| PlanetScale FK 過時 claim                  | Reviewer C 單獨         | 1 軸        |
| PG CTE 版本錯（6.4 vs 8.4）                | Reviewer C 單獨         | 1 軸        |
| Connection memory 衝突（3MB vs 8-10MB）    | Reviewer B 單獨         | 1 軸        |
| Framework bias（Type A/C/E 集中）          | Reviewer D 單獨         | 1 軸        |

2 軸 convergence 的 finding（缺 weight + frame uniformity）信號特別強 — 兩個 reviewer 從不同 audit 維度（寫作規範軸 vs 跨檔一致性軸）獨立判斷出同一 issue。

對比：PlanetScale FK 是 *單 reviewer 找到的 highest-severity finding*（invalidates 整段 Phase 1 audit premise）、但是 *單軸 flag*。

兩種都 P0、但 *priority weighting* 應該不同：

- 2 軸 convergence finding：*structurally important*、是 batch level pattern
- 單軸 high-severity finding：*technically critical*、specific issue

## 機制：為什麼 convergence 比 severity 重要

### 1. 單 reviewer flag 有 axis-specific bias

每個 reviewer 用特定 audit 軸（寫作規範 / 一致性 / 技術 / 結構）。單軸 flag 帶該軸的 *judgment preference*：

- Reviewer A 偏好 *寫作風格規範*、可能 flag 過嚴
- Reviewer C 偏好 *technical correctness*、可能 flag 一些 *正確但 niche* 議題

單軸 flag finding 可能是 *該軸 perspective 的 P0、其他軸 perspective 不重要*。

### 2. 跨 axis convergence 排除 axis-specific bias

當兩個 reviewer 從 *不同 axis* 獨立 flag 同 finding、表示這個 issue 對 *多種 judgment perspective* 都 reachable — 是 *系統性 pattern*、不是單一 perspective 的偏好。

舉例：「4 篇 migration playbook 缺 weight」

- Reviewer A 從 *寫作規範* 角度 flag：missing frontmatter required field
- Reviewer B 從 *跨檔一致性* 角度 flag：13 篇 deep article 有 weight、4 篇 migration 沒有、不對齊

兩個獨立 reasoning path 到同一 finding、信號收斂、是 *結構性問題*。

### 3. Convergence finding 修一次解決多 reviewer flag

實作層：

- 單軸 P0：修 → 解決 1 個 reviewer 的 flag
- 雙軸 convergence：修 → 解決 2 個 reviewer 的 flag

ROI 上 convergence finding 修法效率 2x。

### 4. Convergence 揭露 audit framework blindspot 的補集

如果某 finding *所有 reviewer 都沒 flag*、可能：

- 沒問題（true negative）
- 所有 axis 都看不到（structural blindspot）

如果某 finding *只一 reviewer flag*、可能：

- Niche but real（axis-specific catch）
- Axis-specific bias

如果某 finding *多 reviewer flag*、強：

- 多 axis 收斂 → 高度 likely true positive
- 排除 axis-specific bias

## 修法：Cross-reviewer convergence matrix

### 1. Multi-reviewer audit 後做 convergence matrix

收齊 N 個 reviewer report 後、不是 merge findings list、是建 matrix：

```text
Finding          | Reviewer A | Reviewer B | Reviewer C | Reviewer D | Convergence
─────────────────┼────────────┼────────────┼────────────┼────────────┼────────────
Missing weight   |     P0     |     P0     |            |            |    **2**
Frame uniformity |     P1     |            |            |     -      |    **2**
FK claim 過時    |            |            |     P0     |            |    1
CTE version 錯   |            |            |     P0     |            |    1
Conn memory 衝突 |            |     P0     |            |            |    1
```

Convergence column 自動標 priority bump — 2+ 列為 *首要 fix*、1 列為 *依 severity 處理*。

### 2. Priority list 按 convergence 排序、不是純按 severity

修法 priority：

1. **2+ convergence finding**（系統性 pattern）— 必修、高 ROI
2. **單軸 + 高 severity finding**（如 FK claim 過時 invalidates premise）— 必修、specific
3. **單軸 + 中 severity finding**（如 CTE version 錯）— 修、ROI 中等
4. **單軸 + 低 severity finding** — 可選

### 3. Convergence 揭露的 *pattern* 寫進 retro

2+ convergence finding 通常是 *寫作流程 / 模板* 級議題、修了該 case 還要回頭看 *為什麼會系統性發生*：

- Missing weight：寫 migration playbook 模板沒有 weight、是 *template gap*
- Frame uniformity：「5 個踩雷」frame 在所有 article 重複、是 *frame template too rigid*

把這些 pattern 寫進 retro / report card、未來不再踩。

## 跟既有原則的關係

- [Sibling Coverage Asymmetry Blindspot in Priority](../sibling-coverage-asymmetry-blindspot-in-priority/)：本卡是 *audit finding 的 priority weighting*、那卡是 *batch coverage 的 priority weighting*、不同 layer
- [Multi-Pass Review Frame Granularity Blindspot](../multi-pass-review-frame-granularity-blindspot/)：multi-pass 是 *同 reviewer 多輪*、本卡是 *多 reviewer 平行*、不同模式

## 反向驗證

不該誤用：

- *Convergence > severity* 不是絕對 — 單軸高 severity finding（如 invalidates premise）仍是必修、不該因為「只一軸 flag」延後
- N=1 reviewer audit 不適用本卡 — 至少 2 個 reviewer 才有 convergence 概念
- 2 個 reviewer 用 *同樣 axis* 都 flag 不算 convergence — 必須 *不同 axis* 才是真正收斂
- Reviewer 之間 *互相看過彼此 report* 後再 flag 不算 convergence — 必須 *獨立 parallel* 跑

## 觸發再評估

- N-reviewer audit 跑超過 5 輪後、check convergence finding 的 follow-up rate 是否真比單軸 finding 高
- 出現 *3 軸以上 convergence* 的 finding 時、是否 trigger framework-level review（不只是 content fix）
- 累積足夠 reviewer convergence case 後、考慮抽出 *axis design 原則*：哪些 axis 組合的 convergence 最 informative
