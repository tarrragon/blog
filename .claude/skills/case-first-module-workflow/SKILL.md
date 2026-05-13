---
name: case-first-module-workflow
description: "Case-first + Agent team review 五階段流程、寫跨多章節教學模組（5+ 章、有 case 庫）時用。觸發詞：教學模組、case-first、case-driven、stage 1/2/3/4/5、agent team review、polish pass、fact vs derive、reviewer prompt、SSoT 對應、frame 重複、skeleton case vs rich case、case fidelity、自掃描 regex、模組擴章。Trigger when writing teaching modules across multiple chapters with an existing case library."
license: MIT
metadata:
  version: 1.0.0
  category: writing-methodology
---

# Case-First Module Workflow

跨多章節教學模組（5+ 章）撰寫的五階段流程。用真實案例驅動 scope 擴展、用 agent team 平行多輪審查補 LLM 自盲點、用 polish pass 處理系統性殘留。已在 6 個模組驗證、334 個 review issue / case fidelity 70-93% 區間。

## 適用情境

- **長期累積的教學模組**：5+ 章、跨章引用密集、規範遵循重要
- **有現成 case 庫**：案例庫含 rich case（具體數字 / 設計細節）跟 / 或 skeleton case（方向骨架）
- **品質高於速度**：完整五階段約 4-6 小時 / 模組、適合長期累積的內容、不適合 one-off 文章
- **主 context 容量敏感**：reviewer 平行 background 是節省 context 的關鍵設計

不適用：新主題沒案例庫、單篇短文、快速迭代原型。

## 三大支柱

| 支柱                     | 意義                                                               |
| ------------------------ | ------------------------------------------------------------------ |
| **Case-driven scope**    | 用真實案例 findings 驅動「該寫什麼」、不是 LLM 從訓練資料自生      |
| **Agent team review**    | 3 個專責 reviewer 平行 background 跑、各維度獨立、不污染主 context |
| **Pattern-aware polish** | 系統性 pattern（負向骨架、模板化）跨檔批次處理、不一個個改         |

## 五階段流程

### Stage 1：案例庫 audit + findings 抽取

完整讀 case（不只 title + description）、邊際遞減判斷停止點、findings 帶 *case 來源* + *對應章節* + *case 類型* 標明。

關鍵紀律：**Skeleton / Medium / Rich case 三類分類** + **Fact vs Derive 分層**。詳見 [stage-1-case-audit](./references/stage-1-case-audit.md) 跟 [principles/case-type-discrimination](./references/principles/case-type-discrimination.md) + [principles/fact-vs-derive-layering](./references/principles/fact-vs-derive-layering.md)。

### Stage 2：基於 findings 建立內容

**寫作前 30 分鐘做 SSoT 對應**（這步不做必踩 frame 重複坑）：列出 cross-chapter findings、每個 frame 指定唯一主寫章節、其他章節只 link。跨模組層級概念 → 模組索引（module index、本 blog Hugo 結構下為 `_index.md`、其他靜態網站可能是 `README.md` 或 `index.md`）。

寫作時主動防範四大反覆陷阱：

1. **負向陳述骨架**：避免「不是 X、是 Y」推進論證、避免「核心責任不是 X、而是 Y」變體段首
2. **模板化**：L1/L2/L3 三層、三選一表格、四步驟流程出現前先問「真的對等嗎？」
3. **首句結構**：每段首句先寫「這個概念是什麼、承擔什麼責任」、不是「對應 [case] 揭露 X」
4. **Case 引用三段式**（06 模組強化）：每處 case 引用要走「概念定義 → case 引用 → 通用展開」三段、case 引用不能取代段首概念定義。詳見 [principles/case-citation-three-part](./references/principles/case-citation-three-part.md)

寫完每章後 commit 一次或合併 commit。

### Stage 3：Agent team 平行多輪審查

Stage 2 commit 後、平行 spawn 3 個 reviewer（`subagent_type: general-purpose`、`run_in_background: true`）：

- **Reviewer A**：寫作規範（AGENTS.md 八原則）— prompt 見 [reviewer-prompts/reviewer-a-standards](./references/reviewer-prompts/reviewer-a-standards.md)
- **Reviewer B**：案例引用準確性（對照原始 case、含 fact vs derive 分層）— prompt 見 [reviewer-prompts/reviewer-b-case-fidelity](./references/reviewer-prompts/reviewer-b-case-fidelity.md)
- **Reviewer C**：跨章一致性（重複 frame / cross-link / 邊界）— prompt 見 [reviewer-prompts/reviewer-c-consistency](./references/reviewer-prompts/reviewer-c-consistency.md)

**為什麼 background**：reviewer 要讀完整 commit + 案例 + 章節、自身 context 會被佔滿；用 background 把 reviewer context 跟主 context 分開、主 context 只接收精煉摘要、節省 ~80% context。

預期 issue baseline：

| Reviewer 維度          | 範圍            | 備註                                                                                                                |
| ---------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------- |
| Standards reviewer     | 20-45 issue     | 規範八原則、含「不是 X 而是 Y」變體段首、06 揭露「case 引用段首」新 pattern                                         |
| Case fidelity reviewer | 6-20 issue      | 準確率 70-93%、skeleton case 多會擴 over-extrapolation、medium case 多會擴實作層、rich case 多會混淆 fact vs derive |
| Consistency reviewer   | 13-18 issue     | 跟章節數 / 跨模組密度成正比                                                                                         |
| **總計**               | **47-71 issue** | 6 模組範圍（baseline 隨 standards reviewer 抓的 pattern 變多而擴大）                                                |

### Stage 4：修正循環

按嚴重度修：critical 編造 → high frame 重複 / fact-derive 錯位 → medium 規範 / 路由 → low polish。

按 *檔案批次* 修、不是按 issue 編號順序。每個檔案修完跑一次 `mdtools fmt --fix` + `mdtools cards` + `mdtools lint`、確認該檔內部一致、再進下一檔。最後跑跨檔驗證、確認 cross-link 全部對齊。

預期成本 1.5-2.5 小時 / 模組。

### Stage 5：Polish pass

Stage 4 後仍會殘留 ~30-40% low / medium issue（負向骨架、編號漂移、cross-link 缺漏、模板化）— 屬系統性 pattern、跨檔批次處理。

詳細工序見 [stage-5-polish-pass](./references/stage-5-polish-pass.md) 跟自掃描 regex 集合 [self-scan-regex](./references/self-scan-regex.md)。

關鍵限制：

- **不重寫章節結構**：polish pass 是修得更貼合規範、不是重新組織
- **不擴大 scope**：polish pass 邊界 = stage 4 修改過的章節集合
- **不追求 0 issue**：保留 ~15 個 low 為下次擴章節時自然處理

預期成本 30-45 分鐘 / 模組。

## 模組執行的觸發路由

當使用者要寫跨章節教學模組時：

1. 確認有 case 庫（rich + skeleton 案例 5+ 篇）— 沒有的話本流程不適用、要先建 case 庫
2. 確認模組規模 5+ 章節 — 單篇文章用 [compositional-writing](../compositional-writing/SKILL.md) 即可
3. 按 stage 1-5 順序執行、不跳階段
4. 每個 stage 完成 commit 一次、保留可追溯歷史
5. 模組完成後做 retrospective、把新浮現 pattern 寫回方法論

## 反覆陷阱（必須主動防範）

6 個模組驗證後、以下陷阱在 *多數模組重複出現*、要在 stage 1-2 就防範、不能依賴 stage 3 reviewer 補救：

1. **Skeleton case 擴寫成 case 事實** — 詳見 [principles/case-type-discrimination](./references/principles/case-type-discrimination.md)
2. **Frame 重複展開（SSoT 不清）** — 詳見 [principles/ssot-correspondence](./references/principles/ssot-correspondence.md)
3. **負向陳述 + 模板化** — 詳見 [self-scan-regex](./references/self-scan-regex.md)
4. **Rich case 判讀層被當 case fact 引用** — 詳見 [principles/fact-vs-derive-layering](./references/principles/fact-vs-derive-layering.md)
5. **自掃描盲點累積** — 每個模組 reviewer 抓出新 pattern 後、回頭更新 self-scan regex
6. **Case 引用段首取代核心概念句**（06 模組新發現）— 詳見 [principles/case-citation-three-part](./references/principles/case-citation-three-part.md)
7. **Medium case 實作層擴寫過頭**（06 模組新發現）— 用 mechanism 名稱精準引用、不擴寫到 case 沒提的具體實作細節、詳見 [principles/case-type-discrimination](./references/principles/case-type-discrimination.md)

## 跟其他 skill 的關係

本 skill 跟 [compositional-writing](../compositional-writing/SKILL.md) skill 互補：

- compositional-writing 管 *單篇* 寫作的原子化跟意圖
- case-first-module-workflow 管 *跨章模組* 的 scope 跟一致性

跟 [requirement-protocol](../requirement-protocol/SKILL.md) skill 互補：

- requirement-protocol 管 *對話協議*（澄清需求、確認方向）
- case-first-module-workflow 管 *內容生產*（5 階段執行）
