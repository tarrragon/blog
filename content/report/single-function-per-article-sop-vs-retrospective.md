---
title: "一篇文章只承擔一種功能：SOP 跟 retrospective 混寫兩邊都做不好"
date: 2026-06-29
weight: 199
description: "文章同時塞操作步驟（SOP）和批次驗證紀錄（retrospective）時，機器讀者找不到可執行的步驟、人類讀者不知道哪段是給自己看的。"
tags: ["report", "事後檢討", "工程方法論", "原則", "寫作", "內容分類"]
---

## 論述基礎與限制

本卡抽自四篇方法論文章同時塞 SOP 和驗證紀錄、導致兩種讀者都服務不好的分類檢討。limitation：evidence 來自同一個 blog 的四篇文章，都是寫作方法論主題。

## 核心原則

操作步驟（SOP：結構模板、流程 checklist、怎麼做）和演化紀錄（retrospective：批次驗證數據、實際跑出來學到什麼）服務不同讀者。混寫本身不一定失敗（SRE 手冊和 postmortem 模板都成功交織兩者），但在本 repo 的場景下會造成兩個具體問題：

1. **SOP 同時存在於 skill 和文章裡，改 skill 時文章沒同步更新、兩處內容分歧**。這是主要痛點。
2. 沒有清楚的分節標示時，讀者要跳過大量「不是給我看的」段落。

## 情境

四篇 `posts/` 文章的共通症狀：

| 文章                                  | SOP 段內容                                 | Retrospective 段內容                                           | 混合比例            |
| ------------------------------------- | ------------------------------------------ | -------------------------------------------------------------- | ------------------- |
| migration-playbook-methodology        | 6 type 結構模板、diff dimension audit 步驟 | 三輪 batch 驗證、cadence dogfood、self-aware limitation update | SOP 40% / retro 60% |
| vendor-deep-article-methodology       | 選題判準、6 段結構、寫作流程 7 step        | 兩輪 batch 驗證、跨兩輪 cadence 對照                           | SOP 35% / retro 65% |
| verification-driven-cli-tool-articles | 分類 → fixture → 標註 → gotcha 回寫流程    | 「為什麼官方 docs 不夠」+ 實測落差清單                         | SOP 70% / retro 30% |
| ci-silent-hang-diagnosis              | 無明確 SOP（不可重複流程）                 | 完整 case study + 原則提取                                     | 不適用此分類        |

前三篇的共通模式：文章開頭像方法論手冊（SOP 感），中段突然變成「第一輪 demo 驗證」「第二輪 batch 對照」（retrospective 感），讀者在兩種模式之間切換的認知成本高。

第四篇 ci-silent-hang 是不同問題 — 它不是功能混合，是資料夾歸類錯（debugging case study 放在 `posts/` 而非 `work-log/`）。

## 理想做法

功能拆分到對應的 surface：

| 功能                      | Surface                            | 讀者                        | 格式                              |
| ------------------------- | ---------------------------------- | --------------------------- | --------------------------------- |
| SOP（操作步驟）           | `.claude/skills/`                  | Claude runtime + 人類執行者 | Skill 格式（H1 + body、portable） |
| Retrospective（驗證證據） | `posts/` 或 `content/skills/` 鏡像 | 人類讀者                    | 文章格式（Hugo frontmatter）      |
| Debugging case            | `work-log/`                        | 人類讀者                    | 事件紀錄                          |
| 抽象原則                  | `report/`                          | 所有讀者                    | Report 卡片                       |

拆分後的文章只保留 retrospective 段（去掉跟 skill 重複的 SOP 步驟），開頭引用 skill 路徑建立 context。去掉 SOP 後文章若不能獨立成篇（冷讀者讀不懂、或只剩表格沒有判讀），降級成 `content/skills/` 鏡像。

已有先例：`case-first-agent-team-review-workflow` 已經走這條路 — 文章是方法論敘事、skill 是操作步驟、兩者共存互連。

## 沒這樣做的麻煩

- **機器讀者找不到步驟**：Claude runtime 透過 skill 觸發操作流程；SOP 埋在文章的 retrospective 段落裡，觸發路徑不通
- **人類讀者跳著讀**：讀者進來看「migration playbook 怎麼寫」，要跳過三輪 batch 驗證表才找到 6 type 結構模板；或者進來看「為什麼三輪 batch collapse 率不同」，要跳過 diff dimension audit 步驟才到驗證段
- **維護雙份**：SOP 同時存在於 skill 和文章裡（migration-playbook 已發生），改 skill 時文章沒同步更新，兩處內容分歧
- **新文章不知道放哪**：下一篇方法論文章也會自然累積 SOP + retrospective，如果沒有拆分慣例，就會繼續混寫

## 判讀徵兆

寫方法論文章時，如果文章裡同時出現以下兩類段落，就是功能混合的訊號：

1. **步驟型段落**：「Step 1 → Step 2 → Step 3」、結構模板、checklist、「照這個跑」
2. **證據型段落**：「第 N 輪 batch 驗證」、「N/N collapse 率」、「跨兩輪對照」、「self-aware limitation update」

另一個徵兆：文章已有對應的 skill（或適合建 skill），但文章裡仍重複 skill 的 SOP 內容。

本徵兆適用 `posts/` 方法論文章。`report/` 卡片的修法步驟 + case 證據並存是正常形態（report 卡格式本就含情境 + 原則 + 修法）。

## 跟其他抽象層原則的關係

- → [#142 文章主體要對齊標題承諾](/report/article-body-must-align-with-title-commitment/)：#142 處理「章節內容偏離標題」，本卡處理「整篇文章功能定位混合」— #142 是段落層、本卡是文章層，同屬「內容要對齊承諾」家族
- → [#122 cadence 同質化](/report/cadence-homogenization-in-batch-writing/)：本卡四篇文章中的 retrospective 段大量引用 #122 的 cadence 概念；拆分後 retrospective 段落成為 #122 的 evidence 文件，SOP 進 skill 不再重複
- → [#154 教材的重點/總結段是內容發散訊號](/report/summary-section-signals-scattered-prose/)：#154 說「刪掉總結段看正文站不站得住」，本卡的對應操作是「刪掉 SOP 段看 retrospective 站不站得住」— 同類「減法測試」判準
- → AGENTS.md 跨 surface 內容處理原則：本卡的拆分動作跨 `.claude/skills/` 和 `content/` 兩個 surface，各自獨立、不交叉引用
