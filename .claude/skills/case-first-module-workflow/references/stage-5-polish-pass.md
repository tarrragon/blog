# Stage 5：Polish Pass

> **角色**：本卡是 `case-first-module-workflow` 的執行型 reference、被 [SKILL.md](../SKILL.md) 引用。
>
> **何時讀**：Stage 4 修正循環完成 commit 後、評估是否需要跨檔系統性 polish。

## 為什麼需要 Polish Pass

Stage 4 按檔案批次修正完 critical + high + 重要 medium 後、仍會殘留 ~30-40% low / medium issue。這些殘留屬於系統性 pattern（負向骨架、編號漂移、用語不一、cross-link 缺漏、模板化）、性質上：

- **跨多個檔案出現** — 不適合按章節批次修
- **單獨修改 ROI 低** — 一個個改散開、容易漏改、容易引入不一致
- **可用 regex / grep 跨檔掃描** — 批次處理效率高 3-5 倍

Polish pass 是處理這類殘留的標準入口。

## 觸發條件

Stage 4 後出現以下任一訊號、就該排 polish pass：

- Standards reviewer 抓出「不是 X、而是 Y」段首結構超過 5 處（屬寫作習慣、單章修改無效率）
- Consistency reviewer 抓出「編號漂移」「失效 link」「用語不一」多處（屬跨檔規範問題）
- 自掃描漏掉的 pattern 出現在 reviewer report（暴露 self-scan regex 不夠寬、要演進）
- 多個檔案有相同類型 issue 殘留（例：4 個檔案都有 cross-link 缺漏）

## Polish Pass 不該做的事

明確邊界、避免 scope creep：

- **不重寫章節結構**：polish pass 是把現有內容修得更貼合規範、不是重新組織。重寫的觸發條件應該回到 stage 2、不是 polish pass。
- **不擴大 scope**：原本不在擴充範圍的章節、polish pass 也不動。Polish pass 邊界 = stage 4 修改過的章節集合。
- **不追求 0 issue**：reviewer 抓的 ~15 個 low 通常可保留為下次擴章節時自然處理。Polish pass 處理「系統性 pattern」、不處理「孤立 issue」。

## 標準工序（7 步）

按系統性 pattern 分批處理、每批跑一次自掃描確認：

### 1. 負向骨架掃描修正

用更寬泛的 regex 掃描、修法「正向陳述 + 後置邊界提醒」：

```bash
rg -n "不是 |而不是|沒有.*[，、]會" <module-paths>
rg -n "^[^|].*責任(不是|並非)" <module-paths>      # 抓「核心責任不是 X」變體
rg -n "^[^|].*[，,]而是|^[^|].*[，,]不是" <module-paths>  # 抓對比骨架開段
```

技術約束敘述例外（「多人共用 IP 無法區分」「單一 timestamp 無法判斷漂移」）保留。

### 2. 編號漂移統一

把 `04.X` 風格 plain text 改成 `[4.X title](url)` markdown link、跟模組索引（Hugo 結構下為 `_index.md`）對齊。

```bash
grep -n "0[0-9]\.[0-9]" <module-paths>  # 找 04.X 風格編號
```

### 3. 表格延伸段補強（關鍵段）

選 2-3 個最高 impact 表格補延伸子段、不全部補（避免擴展超出 scope）：

- 判讀訊號表的爭議列（最常被 reviewer 抓的）
- 選型表（Buffer / Sampling / 策略對照）
- 反模式表（如果前文沒對應 section）

### 4. 模板化拆敘事（代表性段）

選 1-2 個最明顯的「四步驟模板套不同情境」段、拆成情境化敘事、其他保留為下次：

- 三類規模 / 四層 grey zone 套同模板
- 並列點性質異質（時序 + 治理 + 風險）卻用同一個 1-4 編號

### 5. Cross-link 補漏 + ownership 邊界補強

Reviewer C 報告的所有 cross-link 缺漏一次補完、用同一個批次跑 mdtools 驗證。包括：

- 同章節內 link 不一致（knowledge card vs 章節 URL）
- 應有 link 但缺
- ownership 邊界路由（A 章設邊界但 B 章 SSoT 不接）

### 6. 用語不一統一 + 失效 link 修正

- 簡轉繁（例：「生命周期」→「生命週期」）
- 術語層級統一（例：instance vs node vs replica 在 K8s 章節）
- `/knowledge-cards/` vs `/section/` URL 統一
- 失效 link 改規劃中或正確路徑

### 7. 最終驗證 + commit

```bash
./bin/mdtools fmt --fix <module-paths>
./bin/mdtools cards content/
./bin/mdtools lint <module-paths>
```

確認全綠、commit。commit message 結構參考：

```text
backend/XX+YY: polish pass — 負向骨架 / 模板化 / cross-link / 編號漂移

## 1. 「不是 X、而是 Y」結構（N 處）

[列出位置]

## 2. 模板化拆敘事（N 處代表性段）

[列出位置 + 改法]

...

## 自掃描

- rg 掃描剩 N 處屬合法因果敘述、非對比骨架、保留
- mdtools fmt / lint / cards 全綠

剩餘 ~N 個 low 保留下次再處理、本次優先 systemic pattern。
```

## Polish Pass 的實作成本

實作數據（04 / 05 polish pass 合併處理）：

- 處理範圍：11 個檔案、+44 / -29 行
- 修正項目：~35 個 issue（10 個負向骨架、2 個模板化、3 個編號漂移、3 個表格延伸段、3 個 cross-link、1 個 case 引用結構）
- 時間：~30-45 分鐘（不重寫、只 pattern match）
- 剩餘 ~15 個 low 保留下次

ROI 來自「系統性 pattern 一次處理 vs 散在各章一個個改」的效率差異 — 用 grep / rg 跨檔修一輪比每章單獨修快 3-5 倍。

## 自掃描盲點更新（重要）

每個模組 reviewer 抓出新 pattern 後、回頭加進 self-scan regex、避免在下個模組重蹈覆轍。

把 self-scan 視為持續演進的工具、不是固定 checklist。詳細 regex 集合見 [self-scan-regex](./self-scan-regex.md)。
