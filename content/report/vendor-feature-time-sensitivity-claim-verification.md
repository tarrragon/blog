---
title: "Vendor Feature 時間敏感性：Claim Verification 必跑、寫作日期必標"
date: 2026-05-19
description: "寫 vendor article 時、feature limitation claim（『不支援 X』『最多 Y』『預設 Z』）有時間敏感性 — vendor 持續演進、寫作後 N 個月可能 invalidate 整段 audit 邏輯。Case：PlanetScale FK 不支援是 2022 年的事實、2023 末 Vitess 18 加 FK 支援、寫作時若不 verify、Phase 1 audit「FK audit + 全 drop」整段過時。機制：LLM training cutoff vs vendor changelog 速度差、且 LLM 預設不標 claim 的時間性。修法：每篇 vendor article 標 *Last verified* date、limitation claim 必要時加 *as of N* 註、claim 反轉 invalidates 整段 audit 時必須重寫不是修補。"
weight: 137
tags: ["report", "事後檢討", "工程方法論", "寫作", "vendor", "verification"]
---

## 核心：Vendor feature limitation claim 有時間敏感性

寫 vendor article 時、常見以下 claim 形態：

- 「Vendor X 不支援 Y」
- 「Vendor X 最多 Z」
- 「Vendor X 預設 W」

這些 claim 在寫作那刻是真的、但 vendor 持續演進。寫作後 *N 個月* — 6 個月、12 個月、24 個月 — claim 可能反轉、整段 audit 邏輯 invalidates。

問題不只是 *claim 過時*、是 *基於 claim 的整段流程被推翻*。Migration playbook Phase 1 audit 如果以「Vendor 不支援 X」為前提、X 後來變支援、Phase 1 整段重寫。

## Case：PlanetScale FK claim 反轉

寫 migrate-to-planetscale.md 跟 migrate-vitess-to-planetscale.md 時：

- Claim：「PlanetScale 不支援 Foreign Key（Vitess 限制）」
- 基於此 claim：Phase 1 audit 整段「FK audit + 全 drop FK + application enforcement 改寫」
- Phase 1 是 weeks-months 工作量、第一個 phase

實際狀態（4-reviewer C audit catch）：

- Vitess 18（2023 末）加 FK 支援
- PlanetScale 2024 起在合適 plan 內可啟用 FK
- 「不支援」是 2022 年的事實、寫作時已過時

修法：整段 Phase 1 audit 從「FK audit + drop」改寫成「FK 行為驗證 + cross-shard cascade 處理」。

這不是 *微調文字*、是 *整段 framing 重做*。

## 機制：為什麼會發生

### 1. LLM training cutoff vs vendor changelog 速度差

LLM training data 有 cutoff date（通常滯後 12-18 個月）。Vendor major feature release 在 cutoff 後、LLM 不知道。

寫 vendor article 時、LLM 預設用 *training 內的 latest fact* — 那個 fact 可能已過時。

### 2. LLM 預設不標 claim 的時間性

LLM 寫「PlanetScale 不支援 FK」、不會自動標「*as of 2022*」、讀者看到 *永久性 claim*。

LLM 不會主動 verify「我寫的這個 claim 是 N 個月內仍 valid 的嗎」、除非寫作流程強制 verify step。

### 3. 基於 claim 的整段流程是「結構性 anchor」

Migration playbook 的 Phase 1 是 *結構錨點* — 後續 Phase 2-4 都 reference Phase 1 結果。Phase 1 基於過時 claim 時、修法不只是 claim、是 *整個 anchor 重做*。

這比修 isolated fact 工作量大 10x — 是「invalidates premise」、不是「fix typo」。

### 4. Vendor article 多用 *永久性語氣* 而非 *時間性語氣*

寫作習慣寫「PlanetScale 不支援 FK」（永久性）、不寫「PlanetScale 截至 2022 末不支援 FK」（時間性）。

讀者讀到的是 *當前永久狀態*、寫作者其實只能保證 *寫作那刻*。

## 修法

### 1. 每篇 vendor article 標 `Last verified` date

frontmatter 或開頭加：

```yaml
last_verified: 2026-05-19
verified_against:
  - PlanetScale docs（2026-05 access）
  - Vitess 18.0 release notes
```

讓讀者看到 *寫作時 verify 的 source / date*、不假設永久性。

### 2. Feature limitation claim 加時間註

寫「Vendor X 不支援 Y」時、加 *as of N*：

```text
PlanetScale 截至 2024 末有限支援 FK（Vitess 18+、需明確啟用）
```

而非：

```text
PlanetScale 不支援 FK
```

### 3. Claim 反轉 → 整段 audit 重寫、不是 patch

當 verify 發現 claim 已反轉（如 PlanetScale FK 從不支援變支援）、不要 *只改 claim 字句*。回頭看 *基於該 claim 的流程段落* —

- Migration Phase 1 audit
- 「何時不要遷」反向 recommendation
- 「跟 sibling vendor 對比」表

每段都要 *重看是否還成立*、不成立的整段重寫。

### 4. Vendor article 寫作前先 verify 主要 claim

寫作流程加 *verify checkpoint*：

- 列出該 article 的「Vendor X 不支援 Y / 最多 Z / 預設 W」claim
- 對每個 claim、查 vendor official docs（最新 docs）/ recent release note（過去 12 個月）
- 不確定的標 *uncertain*、不要 confidence-fake

### 5. Reviewer C 必查 vendor feature time-sensitive claim

跑 4-reviewer audit 時、Reviewer C（技術準確性）必須：

- 對每個 *feature limitation claim*、verify 是否仍 current
- 對每個 *vendor CLI command*、verify 是否真實存在（hallucinated CLI 是 sibling 問題）
- 對每個 *vendor default value*、verify 是否最新

## Hallucination 鄰近議題

LLM 寫 vendor CLI command 容易 hallucinate（例如 `pscale database promote-shadow`、`vtctldclient PartitionTablet`）— 命令不存在、是 LLM 編造。

跟本卡時間敏感性 *不完全相同* —

- 時間敏感性：*claim 寫作時 valid、現在過時*
- Hallucination：*claim 寫作時也 invalid、是編造*

兩者修法部分重疊：

- 寫前 verify（claim + CLI）
- Reviewer C audit
- 不確定標 uncertain

但 hallucination 是 *更基本的 verify failure*、本卡聚焦時間敏感性。

## 跟既有原則的關係

- [Sibling Coverage Asymmetry Blindspot in Priority](../sibling-coverage-asymmetry-blindspot-in-priority/)：本卡是 *claim 時間敏感性*、那卡是 *coverage 對稱性*、不同 axis
- [Data Topology as Audit Dimension](../data-topology-as-audit-dimension/)：本卡是 *寫作 audit 應加時間維度*、那卡是 *content audit 應加 topology 維度*

## 反向驗證

不該誤用本卡：

- *穩定 fact*（SQL syntax / RFC standard / industry-wide convention）不必標時間性、只有 *vendor-specific evolving feature* 才需要
- 不是每個 claim 都要 verify — 「MySQL replication 用 binlog」是穩定 fact、不必加 *as of N*
- 過度標 *as of N* 會讓 article 變 verbose、只對 *limitation claim* 跟 *vendor-specific behavior* 套用

## 觸發再評估

未來累積到以下情境、本卡應 review：

- 連續 2 個 batch 都踩 hallucinated CLI（trigger 升級到強制 *寫前 CLI verify*）
- Feature claim 反轉 invalidates 整段流程的 case 超過 3 次（trigger 把 vendor article 改成 *每 N 個月 re-verify* 紀律）
- LLM training cutoff 跟 vendor changelog 速度差變更大（trigger 升級 verify cadence）
