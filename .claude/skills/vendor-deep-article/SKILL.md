---
name: vendor-deep-article
description: "Vendor 深度技術文章的寫作方法論：從 vendor overview 往下寫單一功能的深度實作文章。選題判準（3 條 + 反向判準）、6 段結構模板（問題情境 → 概念 → 配置 → 故障演練 → 容量 → 整合）、跟 overview 的職責劃分、寫作流程 7 step、批次 cadence variant 規劃。觸發詞：deep article、vendor 深度文章、實作文章、vendor feature、pgBouncer、Patroni、寫 vendor 文章、sub-tool article、feature deep dive。Trigger when writing vendor-specific deep implementation articles."
license: MIT
metadata:
  version: 1.0.0
  category: writing-methodology
---

# Vendor Deep Article Methodology

Vendor 深度技術文章的寫作方法論 — vendor overview 飽和後、往下寫單一功能的深度實作文章。

跟 vendor overview 是不同產品：overview 回答「該不該選 / 跟同類差在哪」（選型層）、deep article 回答「某功能怎麼設 / 踩哪些坑 / 容量怎麼規劃」（實作層）。

## 適用情境

- Vendor overview 頁尾「預計實作話題」backlog 中的議題
- 跨 vendor 議題、不適合塞單一 vendor overview
- Overview 的「進階主題」段已經點到但 7-15 行說不清楚

不適用：

- **Vendor 文件已經夠好**：自己加一篇只是 paraphrase
- **議題太小**：塞進 vendor overview 某段 200 字解決
- **沒 production 經驗或 case 支撐**：純 spec 復述會變低品質內容
- **News-driven 短文**（CVE / 收購）：寫在 posts/
- **Cross-cutting 概念**（observability vs SRE）：寫在 report/ 或 posts/

## 選題判準

三條判準、至少符合一條：

### 判準一：被讀者問或被自己在 production 踩過

Overview backlog 的 9 項都重要、但寫作 ROI 不一樣。優先寫讀者最常問或自己踩最痛的、不是清單前幾項。

### 判準二：跨 vendor 議題

跨兩個 vendor overview、寫在任一頁都偏。deep article 可以獨立、cross-link 兩個 vendor overview。

### 判準三：overview 進階段落說不清楚

Overview 中 7-15 行的進階主題段、dynamic credential 怎麼 call / lease renewal 怎麼處理 — 不是 overview 該寫的。需要獨立深度文章。

## 6 段結構

| 段落                    | 內容                                                           | 比例 |
| ----------------------- | -------------------------------------------------------------- | ---- |
| 1. 問題情境             | 「為什麼會踩到這個」— 真實場景觸發、不是 textbook intro        | 10%  |
| 2. 核心概念             | 該 vendor 特有的概念（不是通用 concept、是這個 vendor 怎麼解） | 15%  |
| 3. 配置 step-by-step    | 真實可跑的 config + code + command（不是偽 code）              | 30%  |
| 4. 故障演練 / 邊界 case | 「踩到哪些坑、什麼徵兆、怎麼修」— production 經驗最有價值的段  | 25%  |
| 5. 容量 / cost 規劃     | 在什麼規模下這個配置適用、超出後要換什麼                       | 10%  |
| 6. 整合 / 下一步        | 跟其他 vendor 怎麼接、什麼 case 後該 revisit                   | 10%  |

6 段是內容指引、不是章節標題模板。章節名稱可隨主題調整。

跟 overview 的職責劃分：overview 不該出現在 deep article 的段落（服務定位 / 核心取捨表 / 跨 vendor 比較）。如果讀者沒看 overview 就直接讀 deep article、開頭一段引用 overview link 即可。

## 寫作流程

### Step 1：選題 + 經驗驗證

從 vendor overview 頁尾 backlog 挑一個、確認自己在 production 踩過或處理過。沒踩過的議題寫不出有價值的故障演練段。

### Step 2：草稿 outline + 真實 config

先列 6 段結構、把真實能跑的 config / code 放進 step-by-step 段。從 config 寫起、不從文字寫起 — 確保 implementation 段有實質內容。

### Step 3：補敘事文字

回頭補每段敘事 — 為什麼這樣配、跟 default 差異、邊界什麼時候會踩。對著 config 寫、不是憑印象寫。

### Step 4：故障演練段是核心

deep article 的差異化價值在故障演練段。Production 經驗、debug log、metric 徵兆描述、recovery 步驟。沒這段就跟 vendor 官方 docs 沒差。

### Step 5：cross-link 回 overview + case

開頭 link 到 vendor overview、結尾 link 到被引用的 case。

### Step 6：單一 reviewer 即可

deep article 的跨章一致性風險低（焦點窄）、案例引用密度低（1-2 個對照）。單一 reviewer 看「config 對不對 + 敘事流暢」就足夠。

### Step 7：行數檢查

200-400 行 sweet spot。超過 500 行該拆兩篇。低於 200 行通常是 overview 重複、應該塞回 overview。

## 批次 cadence variant 規劃

批次寫 ≥ 4 篇 deep article 時、寫前準備 N 種 framing 變體、每篇對應一種。

已驗證的 5 種 entry framing variant：

```text
- Variant A: 標準 6-section「問題情境」開頭
- Variant B: 痛點宣告 case-led
- Variant C: 概念反向定義
- Variant D: 對照表 / 矩陣驅動
- Variant E: lifecycle-driven 結構標題
```

cadence audit 抽樣位置在進度 60-80%（有 4 樣本對照訊號強、進度 10-20% 只有 1 樣本訊號弱）。

## 反覆陷阱

1. **從文字寫起**：沒有真實 config 的 deep article 是 paraphrase、不是 implementation 指引
2. **重複 overview 內容**：deep article 開頭寫了三段「為什麼選這個 vendor」— 已經在 overview
3. **跳過故障演練段**：deep article 沒有故障演練就跟官方 docs 沒差
4. **被動寫 batch 不做 variant**：同 vendor 多篇 deep article 特別容易 cadence collapse

## 跟其他 skill 的關係

- [compositional-writing](../compositional-writing/SKILL.md)：寫作 atomic 原則、適用所有寫作
- [migration-playbook-methodology](../migration-playbook-methodology/SKILL.md)：sibling、處理 cross-vendor process content
- [case-first-module-workflow](../case-first-module-workflow/SKILL.md)：跨多章節教學模組批次、本 skill 適用單篇或小批次 deep article

---

**Version**: 1.0.0
