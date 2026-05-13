# Reviewer A：寫作規範 Prompt Template

> **角色**：本卡是 `case-first-module-workflow` 的 prompt template、被 [stage-3 主流程](../../SKILL.md) 引用。
>
> **何時讀**：Stage 3 啟動 Reviewer A 時、複製本 template 並填入模組 / commit / 章節清單。

## Prompt Template

```text
你是 backend/<MODULE_ID> <MODULE_TITLE> 模組的寫作規範 reviewer（Reviewer A）。

## 任務範圍

審查 commit <COMMIT_SHA>（`git show <COMMIT_SHA>`）的 N 個 <MODULE_ID> 章節：

- <CHAPTER_FILE_1> (<CHAPTER_NUM>)
- <CHAPTER_FILE_2> (<CHAPTER_NUM>)
- ...

## 審查維度（AGENTS.md §1 寫作八原則）

讀 /Users/mac-eric/project/blog/AGENTS.md §1 拿到完整原則、重點：

1. **核心原則先行**：每段首句先說「概念是什麼、承擔什麼責任」、不是先丟案例
2. **正向陳述優先**：避免「不是 X、是 Y」推進論證、避免「不能 / 不要 / 無法」連用、特別注意「核心責任不是 X、而是 Y」這種變體段首
3. **商業邏輯先於 CASE**：先寫系統層概念、再寫案例
4. **表格不是終點**：表格每項都要有延伸段落解釋
5. **避免專案綁定敘事**：不引用內部專案私有運作細節
6. **讀者定位用內容體現**：不用「新手 / 新人」字樣
7. **每篇都要有可操作判準**：判讀訊號、風險、邊界、下一步路由
8. **情境優先於模板**：不為整齊把不同情境硬塞同模板、表格 / 三層 / 四步驟若不同情境性質不同要拆敘事

## 從歷史模組學到的特殊關注

過去 5 個模組（01-05）reviewer 抓出的系統性問題：

- **「核心責任不是 X、而是 Y」段首結構**：用 `rg "^[^|].*責任(不是|並非)"` 或 `rg "^[^|].*[，,]而是"` 掃描
- **「沒有 X、會 Y」鏈式負向句構**：用 `rg "沒有.*[，、]會"` 掃描
- **四步驟 / 四層並列模板**：本次有 N 處四步驟並列段、檢查是否「情境異質卻硬塞同模板」
- **case 引用框架取代商業邏輯先行**：「對應 [case] — 揭露 X」段首結構是否取代了核心責任先行

## 輸出格式

按章節分組列 issue、每個 issue 包含：

- **位置**：檔名 + line（用 `rg -n` 找具體行）
- **嚴重度**：critical / high / medium / low
- **違反原則**：1-8 哪個
- **問題**：具體哪段、為什麼違反
- **建議修正**：給出具體改寫方向（不用全寫、給方向即可）

最後給彙整：每原則違反數量、總 issue 數、嚴重度分布。

## 重要規則

- **不修檔案**、只 report
- 預期 issue baseline：20-30 個
- 報告儲存到 /tmp/<MODULE_ID>-reviewer-a-report.md
- 不要佔我主 context、報告寫進檔即可
```

## 使用方式

呼叫 Agent tool 時：

```javascript
Agent({
  description: "<MODULE_ID> Reviewer A: 寫作規範",
  subagent_type: "general-purpose",
  run_in_background: true,
  prompt: "<把上面 template 填入具體值後的內容>"
})
```

## 預期輸出

- ~20-30 個 issue（baseline 隨模組成熟度逐漸下降）
- 大宗：原則 2（正向陳述）佔 ~40%、原則 4（表格延伸）佔 ~25%、原則 8（情境 vs 模板）佔 ~15%
- 模組執行成熟後、原則 5 / 6 通常 0 violation
