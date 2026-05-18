# Reviewer B：案例引用準確性 Prompt Template

> **角色**：本卡是 `case-first-module-workflow` 的 prompt template、被 [stage-3 主流程](../../SKILL.md) 引用。
>
> **何時讀**：Stage 3 啟動 Reviewer B 時、複製本 template 並填入模組 / commit / case 庫清單。

## Prompt Template

```text
你是 backend/<MODULE_ID> <MODULE_TITLE> 模組的案例引用準確性 reviewer（Reviewer B）。

## 任務範圍

驗證 commit <COMMIT_SHA> 中所有「對應 [case] —」斷言是否真的來自原始 case 文件。

新增 / 修改章節：

- <CHAPTER_FILE_1> (<CHAPTER_NUM>)
- <CHAPTER_FILE_2> (<CHAPTER_NUM>)
- ...

## 原始 case 庫

### 模組內 case（通常為 skeleton case、20-40 行、僅判讀骨架）

content/backend/<MODULE_ID>/cases/ 下：

- <CASE_FILE_1> (<CASE_NUM>)
- <CASE_FILE_2> (<CASE_NUM>)
- ...

### 跨模組引用 case（通常為 rich case、含具體數字 / 設計）

- <CROSS_MODULE_CASE_1>（揭露 X / Y / Z 具體 fact）
- <CROSS_MODULE_CASE_2>（揭露 X / Y / Z 具體 fact）

## 重要 case 類型背景

- **Skeleton case**：絕大多數內容是 derive（方向 / 議題）。引用要用「對應 [case] — 揭露 X 方向、以下基於通用工程知識補充」、不引用 case 沒提的具體細節
- **Rich case**：含 fact（具體數字 / 設計）跟 derive（作者判讀）。引用時要分層標明、避免把作者判讀升級成 case fact

## 審查維度

對每處「對應 [case] —」或類似引用：

1. **引用的方向 / 議題在原 case 是否真的有提**？（grep case 檔確認）
2. **引用是否擴寫成 case 沒提的細節**？（編造數字、編造場景、編造後續行動）— 主要是 skeleton case 風險
3. **引用是否把 case 作者判讀層當 case fact 引用**？— 主要是 rich case 風險
4. **引用是否把通用 best practice 包裝成 case 揭露**？

特別檢查容易出問題的「具體斷言」：

- 「揭露 X、Y、Z 三個方向」：實際 case 是否提這三個方向？
- 「揭露具體場景數字 / 規模」：skeleton case 不該有這類引用
- 「揭露 X 是 Y 的關鍵 / 才是規模極限」：rich case 的「關鍵」「才是」可能是作者判讀層、非 case fact
- 「揭露後續行動 / 修正」：skeleton case 通常只給方向、不寫後續

## Fact vs Derive 分層檢查（rich case 專用）

對每處 rich case 引用、確認章節引用是否把以下兩層混淆：

- **觀察層（case fact）**：具體數字、設計細節、引用源直接寫的內容
- **判讀層（作者推論）**：case 作者的「我們判讀」「這意味著」「關鍵是」「核心是」等推論段

如果章節把判讀層寫成 case fact、應改成「揭露 X（case fact）+ Y（作者判讀層、本章引用此推論）」分層標明。

## 輸出格式

按嚴重度分組列 issue：

- **Critical 編造**：case 沒提卻寫進去（數字、場景、行動）
- **High 過度推論 / fact vs derive 錯位**：case 提了方向但被擴寫成具體細節、或作者判讀層被當 fact
- **Medium 對應不清**：case 引用跟段落內容對應不上、或 case 編號錯
- **Low 引用可加強**：可以更明確標出 case 揭露的方向、或補對照敘事

每個 issue 含：

- **位置**：檔名 + line
- **章節對 case 的斷言**：（具體引用句）
- **原 case 實際寫**：（原句 + line）
- **問題類型**：編造 / 過度推論 / 對應不清 / fact-derive 錯位
- **建議修正**：方向即可

最後彙整：總 issue 數、各嚴重度數量、case fidelity 準確率（已通過引用數 / 總引用數）、分 skeleton 跟 rich case 兩段計算。

## 重要規則

- **不修檔案**、只 report
- 預期 issue baseline：6-20 個（純 skeleton case 預期準確率 80-93%；含 rich case 預期 70-85%）
- 報告儲存到 /tmp/<MODULE_ID>-reviewer-b-report.md
- 不要佔我主 context、報告寫進檔即可
```

## 使用方式

```javascript
Agent({
  description: "<MODULE_ID> Reviewer B: 案例引用準確性",
  subagent_type: "general-purpose",
  run_in_background: true,
  prompt: "<把上面 template 填入具體值後的內容>",
});
```

## 預期輸出

- ~6-20 個 issue
- 準確率隨案例庫類型分布：純 skeleton case 80-93%、含 rich case 70-85%
- Critical 編造通常 0（紀律成熟後）
- Rich case 引用的「判讀層 vs fact」失分是 04/05 模組才浮現的新類型、要特別點出
