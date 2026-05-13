# Reviewer C：跨章一致性 Prompt Template

> **角色**：本卡是 `case-first-module-workflow` 的 prompt template、被 [stage-3 主流程](../../SKILL.md) 引用。
>
> **何時讀**：Stage 3 啟動 Reviewer C 時、複製本 template 並填入模組 / commit / SSoT map / 跨模組對照。

## Prompt Template

```text
你是 backend/<MODULE_ID> <MODULE_TITLE> 模組的跨章一致性 reviewer（Reviewer C）。

## 任務範圍

跨章審查 commit <COMMIT_SHA> 中 N 個新章 + 模組整體 M 章 + 跟其他模組的跨模組一致性。

主要修改章節：

- <CHAPTER_FILE_1>
- <CHAPTER_FILE_2>
- ...

完整模組章節在 content/backend/<MODULE_ID>/*.md。

## SSoT 設計（stage 2 寫作前定的 map）

- <FRAME_1> → <CHAPTER_A> SSoT、其他章 link
- <FRAME_2> → <CHAPTER_B> SSoT、_index 不展開
- ...

## 跨模組對照（如有）

- 引用 09 模組 case：<CASE_LIST>
- 引用 07 模組 case：<CASE_LIST>
- 跟 04 / 06 / 08 章節的 cross-link 路由：<ROUTING_LIST>

## 審查維度

1. **Frame 重複展開**：同一概念是否在多章各自展開？例如：sampling 在 X / Y / Z 章都有 → 應該 SSoT 一處展開、其他 link
2. **Cross-link 缺漏**：應有 link 但缺、或 link 對到錯誤章節
3. **矛盾說法**：兩章對同概念說法不一致
4. **章節邊界錯位**：該寫在 A 章的內容寫在 B 章
5. **失效 cross-link**：link 對到不存在的 anchor 或路徑大小寫錯誤、或 link text 跟 URL 不一致（例：「5.3 LB Contract」link 卻指向 `/knowledge-cards/`）
6. **與模組索引 / case 索引對齊**：章節描述、回寫指引是否跟索引檔一致（本 blog Hugo 結構下為 `_index.md`）
7. **跨模組一致性**：引用其他模組 case 的數字是否跟原 case 一致、跨模組 cross-link 是否正確
8. **編號漂移**：`04.X` vs `4.X` 等編號風格是否模組內統一

## 重點關注

- SSoT map 中的 frame 是否真的只在主寫章展開？
- 兩個 lens 對同 case 引用（例：遷移節奏 vs 常態 ownership）是否有 lens 區分宣告？
- 跨模組對應段（例：05 引用 09 case）的數字 / 細節是否跟原 case 一致？
- 同章節內同一術語的 link target 是否一致（knowledge card vs section URL）？

## 輸出格式

按嚴重度分組：

- **High 重複展開 / 嚴重邊界錯位**：frame 在多章重複定義 / 展開
- **Medium 邊界 / 矛盾 / 失效 link / _index 對齊**
- **Low cross-link 缺漏 / 用語不一 / 編號漂移**

每 issue 含：

- **位置**：A 章 line N、B 章 line M
- **問題類型**：重複 / 矛盾 / 失效 / 邊界 / 跨模組
- **具體內容**：兩處對照
- **建議**：哪章保留 SSoT、哪章改 link

最後彙整：總 issue 數、各類型數量、SSoT 設計總體評估（哪些做得好、哪些需修正）。

## 重要規則

- **不修檔案**、只 report
- 預期 issue baseline：13-18 個
- 報告儲存到 /tmp/<MODULE_ID>-reviewer-c-report.md
- 不要佔我主 context、報告寫進檔即可
```

## 使用方式

```javascript
Agent({
  description: "<MODULE_ID> Reviewer C: 跨章一致性",
  subagent_type: "general-purpose",
  run_in_background: true,
  prompt: "<把上面 template 填入具體值後的內容>"
})
```

## 預期輸出

- ~13-18 個 issue
- 跟章節數 / 跨模組密度成正比
- 主要類型：frame 重複（3-5 個）、cross-link 缺漏（5-7 個）、失效 link / 邊界（2-4 個）、用語不一 / 編號漂移（3-6 個）
- 跨模組對照（如 05 → 09 rich case）會推高 issue 數量
