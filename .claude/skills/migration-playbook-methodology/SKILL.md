---
name: migration-playbook-methodology
description: "跨 vendor migration playbook 寫作方法論：6 維 diff dimension audit (schema / operational / paradigm / components / application change / data topology) + 6 type 結構模板 (Type A phased translation / Type B drop-in / Type C operational hybrid / Type D parallel streams / Type E paradigm shift / Type F topology re-layout) + Stage 0 variant 規劃 + 4-reviewer audit pattern + Self-aware limitation。觸發詞：migration playbook、cross-vendor migration、Type A B C D E F、diff dimension audit、data topology audit、stage 0 variant、migration 結構、cross-vendor process、Type F re-layout、major version upgrade、re-sharding、partition redesign、policy-driven migration。Trigger when writing migration playbook / cross-vendor process content."
license: MIT
metadata:
  version: 1.0.0
  category: writing-methodology
---

# Migration Playbook Methodology

Cross-vendor migration playbook 寫作方法論 — 從 20 篇 migration / process content 抽出的 audit / structure / discipline 框架。

跟 [single feature deep article methodology](../compositional-writing/) 對照、migration playbook 是 *不同 content category*：

- Single feature deep article：6-section（problem → concept → config → failure → capacity → integration）、200-400 行、focused on *how to implement / debug feature X*
- **Migration playbook**：6 種結構模板（依 diff dimension）、200-400 行 / 篇、focused on *how to move from A to B*

## 適用情境

- **跨 vendor process content**：A vendor → B vendor、A version → B version、cluster topology re-layout、compliance-driven migration
- **6+ 種 type 任一**：高 schema 差 / drop-in compatible / operational redesign / multi-tool 拆分 / paradigm shift / topology re-layout
- **品質高於速度**：完整 audit + structure + 5-case 故障演練、約 2-3 小時 / 篇

不適用：

- **Pure vendor doc 翻譯**：寫在 vendor docs / posts、不寫 migration playbook
- **同 vendor major version upgrade**（PostgreSQL 14 → 17）：結構接近 deep article + upgrade audit、不是 5 type — 例外見 [漏類](#漏類補充)
- **臨時 PoC / spike**：簡短決策文件即可
- **容量重新規劃 / re-sharding**：已涵蓋於 Type F、見「6 type 結構模板」段
- **Acquisition / merger consolidation**：source / target 同產品、要處理 identity / RBAC / 歷史資料合併、6 type 不覆蓋

## 三大支柱

| 支柱                          | 意義                                                                                          |
| ----------------------------- | --------------------------------------------------------------------------------------------- |
| **6 維 diff dimension audit** | 寫前判主導維度、選對應 type 結構；不靠直覺套既有模板                                          |
| **6 type 結構模板**           | Type A-F 對應不同 source/target 差異組合、結構模板隨 type 變動                               |
| **Stage 0 variant 規劃 + 4-reviewer audit** | 寫批量內容前主動準備 framing variant 避免 cadence collapse、寫後跑 multi-axis review |

## 6 維 diff dimension audit

寫 migration playbook 前先跑：

```text
Step 1: 列 6 維度
  - Schema / API
  - Operational model
  - Abstraction / paradigm
  - Number of components (1 vs N)
  - Application change
  - Data topology（sharding / partition / replication / region / co-location）

Step 2: 對每維度評 High / Medium / Low

Step 3: 找主導差異維度（不是「最大」、是「讀者最關心」、audience-dependent heuristic）

Step 4: 對映常見 type
  - Schema = High（其他 Low）      → Type A phased rule translation
  - 全 Low / 全 Medium              → Type B drop-in
  - Operational = High（其他 Low）  → Type C operational hybrid
  - Components = High               → Type D parallel streams
  - Paradigm = High                 → Type E paradigm shift
  - Topology = High（其他 Low）     → Type F topology re-layout

Step 5: 處理多重歸類（多軸 High）
  - 主結構選讀者最關心的維度
  - 多數情境優先序: Schema > Paradigm > Operational > Topology > Components
  - 其他高維度抽出獨立段補充、不強迫單一 type 標籤

Step 6: 確認不在已知漏類內
  - 同 vendor major version upgrade / 政策合規驅動 / acquisition consolidation 不適用 6 type
  - 漏類處理見 [漏類補充](#漏類補充)

Step 7: 評估候選軸（current open question）
  - Identity / Consistency / Residency 是否獨立軸？
  - 累積 3-5 case / 軸後才 commit 升 7-9 維 audit
  - 詳見 [principles/axis-candidate-evaluation](references/principles/axis-candidate-evaluation.md)
```

詳細 6 type 對映 + 漏類處理見 [principles/six-dimension-audit-framework](references/principles/six-dimension-audit-framework.md)。

## 6 type 結構模板

每 type 對應不同 anatomy、200-400 行：

| Type | 主導維度        | Anatomy（章節骨架）                                                              | 行數 | 週期         |
| ---- | --------------- | -------------------------------------------------------------------------------- | ---- | ------------ |
| A    | Schema / API    | 6-phase phased translation                                                       | 11-12 | 4-9 個月    |
| B    | 無顯著差異      | 6-section + compatibility audit prefix                                           | 7-8  | 1-4 週       |
| C    | Operational     | Hybrid (4-phase 含 audit + drop-in cutover)                                      | 11-12 | 6-12 週     |
| D    | Components 拆分 | Parallel migration streams                                                       | 10-11 | 2-4 個月    |
| E    | Paradigm        | Partial + 混合架構                                                               | 10-11 | 不收斂       |
| F    | Data topology   | 機制 + execution flow per-step（可拆 sub-type：F-cluster / F-multi-region）       | 7-9  | 1 天-2 週   |

詳細 anatomy + 寫作範例見 [anatomies/](references/anatomies/) 各 type 個別檔。

## Stage 0 variant 規劃

寫批量 migration playbook（≥ 5 同類檔）必須做 Stage 0 variant 規劃、避免 cadence collapse：

```text
寫前先列 N 種 entry framing variant、對映 N 篇主題分配：

Variant 範例（從 dogfood 收集）：
- Variant A: 標準 6-section「問題情境」開頭
- Variant B: 痛點宣告 case-led「為什麼 X 越跑越慢」
- Variant C: 概念反向定義「X 不是 Y、是 Z」
- Variant D: 對照表 / 矩陣 / 決策表開頭
- Variant E: lifecycle-driven 結構標題
- Variant F: meta-reflection「為什麼這篇不套 N 種 type」
- Variant G: paradox「字面 migration 不成立」/「same protocol, different contract」
- Variant H: cost / bill 拆解開頭

對 N 篇主題、選 N 種不同 variant、寫前完成設計
```

詳細 cadence dogfood evidence + variant 準備見 [principles/stage-0-variant-discipline](references/principles/stage-0-variant-discipline.md)。

## 4-reviewer audit pattern

寫完批量後、跑 4 reviewer 平行 background 審查、各覆蓋不同軸：

- **Reviewer A**：寫作規範 + 字句層（AGENTS.md 八原則 / emoji / 裸 URL / MD036 / MD026）
- **Reviewer B**：概念邊界 + 跨檔一致性（術語 / 數字 / cross-link / hierarchy）
- **Reviewer C**：案例引用準確性 + 數據準確性（行數 / 章節數 / 工作量 % / 死鏈）
- **Reviewer D**：自一致性 + 邏輯漏洞 + 反例搜尋（結構性質疑、最深的批判）

詳細 reviewer prompt 模板見 [reviewer-prompts](references/reviewer-prompts/)。

## Self-aware limitation 模式

第二輪 / 第三輪 audit 後、reviewer D 通常揭露 *結構性質疑*；採 **Phase 3a meta-acknowledgment** 而非 **Phase 3b substantive restructure**：

- Phase 3a：在卡內承認 limitation、列 trigger 給未來累積樣本後重評估
- Phase 3b：跑既有內容 retroactive audit、重審 type / axis（樣本不足時延後）

詳見 [principles/self-aware-limitation-pattern](references/principles/self-aware-limitation-pattern.md)。

## 漏類補充

6 type 是 current best understanding、不是窮盡分類。已知漏類（不適用 6 type）：

- **同 vendor major version upgrade**（PG 14 → 17 / Kafka 3 → 4）：結構走 deep article + upgrade audit
- **政策 / 合規驅動**：driver 在外部、資料層仍走 Type A-F；audit 重點是 evidence collection
- **Acquisition / merger consolidation**：source / target 同產品、處理 identity / RBAC / 歷史資料合併

未來累積更多 case 後可能浮現第 7-9 type（identity / consistency / residency 候選）、或對 6 type 重構。Type 集合是 *open*、不是 *closed*。

## 模組執行的觸發路由

當使用者要寫 migration playbook：

1. **判主題形狀**：cross-vendor 切換 / 同 vendor upgrade / topology re-layout / compliance-driven
2. **跑 6 維 diff dimension audit**（不能跳）
3. **找主導差異維度** + 對映 type
4. **批量寫 ≥ 3 篇** 時做 Stage 0 variant 規劃
5. **按 type anatomy 寫**、補真實 config / 5 case / capacity / integration
6. **跨檔 cadence audit**（每篇前 + 整批後）
7. **批量完成後跑 4-reviewer audit**
8. **Reviewer D 揭露結構性質疑時走 Phase 3a meta-acknowledgment**

## 跟其他 skill 的關係

- [compositional-writing](../compositional-writing/SKILL.md)：寫作 atomic 原則、適用所有寫作
- [case-first-module-workflow](../case-first-module-workflow/SKILL.md)：跨多章節教學模組批次（5+ 章）、本 skill 適用 *cross-vendor process 系列*
- [requirement-protocol](../requirement-protocol/SKILL.md)：寫前澄清需求、本 skill 在 Step 1 audit 前可用 requirement-protocol 確認 scope

## 反覆陷阱（必須主動防範）

20 篇 migration / process content 跑出來的陷阱：

1. **直覺套 6 phase 模板**：drop-in / paradigm shift 套 phased 結構失真；先跑 audit 才選 type
2. **「為什麼遷：X / Y / Z driver」cadence collapse**：被動寫作下相似主題自然 collapse；Stage 0 variant 規劃必須主動
3. **多軸 High 強塞單一 type 標籤**：用「Type X/Y 混合」標示是維度組合、按主導維度選主結構 + 高維度獨立段
4. **「最大維度」沒處理 tie**：兩維度 High 用優先序判讀、非 tie-breaking
5. **工作量 % 包裝成 measured value**：用 hedge 詞（「主要工作量塊」「明顯多於其他維度」）、不亂寫 %
6. **N=1 sample 互引強化「N=多」假象**：3 篇 axis 候選驗證互引強化、實際 evidence weight 仍是 N=1
7. **「擴張不是重構」修辭**：擴 audit 維度時實質 retroactively 暴露既有分類不完整、是 silent grandfathering、不該假裝清白
