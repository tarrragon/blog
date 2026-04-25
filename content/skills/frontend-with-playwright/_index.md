---
title: "Frontend with Playwright — 框架無關的前端開發 + Playwright 驗證"
date: 2026-04-26
description: "框架無關的前端開發協議 + Playwright 驗證：DOM topology 先於 CSS、CSS / JS 邊界辨識、Playwright 三個位置（假設 / 行為 / 互動驗證）、framework 共處、Reactive 效能、A11y。六大原則 + 六份情境 reference。"
tags: ["前端開發", "Playwright", "CSS", "JavaScript", "Accessibility", "Performance", "skills"]
---

## 這個資料夾是什麼

`frontend-with-playwright` 是一套前端開發協議 skill，原生位置在 [`.claude/skills/frontend-with-playwright/`](https://github.com/tarrragon/blog/tree/main/.claude/skills/frontend-with-playwright) 供 Claude runtime 呼叫；這份是**同內容的文章版本**，讓人類讀者也能直接在 blog 閱讀。

原則框架無關 — 適用 vanilla HTML/CSS/JS、Vue、React、jQuery — 因為核心是「DOM / CSS / JS 三者的本質行為」加上「Playwright 用 live DOM 量測驗證」、不依賴特定框架的渲染機制。源頭是 [`content/report/`](/report/) 累積的 50+ 篇事後檢討、由本 skill 的六份 reference 萃取對應六個情境的協議步驟。

## 閱讀順序

### 場景 1：第一次接觸

| 順序 | 檔案                                                | 目的                                     |
| ---- | --------------------------------------------------- | ---------------------------------------- |
| 1    | [SKILL.md](/skills/frontend-with-playwright/skill/) | 三大支柱 + 六大原則速查、觸發路由表      |
| 2    | 依情境挑一份 reference（見下表）                    | 把原則翻譯成可套用的協議步驟、模板與範例 |
| 3    | 該 reference 結尾的 self-check checklist            | 自評有沒有按協議走                       |

### 場景 2：已熟悉協議、想直接解決當前任務

直接依觸發情境跳對應 reference：

| 觸發情境                                                              | reference                                                                            |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 要寫 CSS 規則、需要先確認 DOM 結構 / selector 該怎麼寫                | [dom-topology-first](/skills/frontend-with-playwright/dom-topology-first/)           |
| 不確定 selector 該多寬、命中其他元素                                  | [dom-topology-first](/skills/frontend-with-playwright/dom-topology-first/)           |
| 不確定值該寫進 CSS 還是 JS、CSS layers / variable / class toggle 取捨 | [css-js-boundary](/skills/frontend-with-playwright/css-js-boundary/)                 |
| 用 `!important` / inline style 解 specificity                         | [css-js-boundary](/skills/frontend-with-playwright/css-js-boundary/)                 |
| 要用 playwright 驗證 layout / 假設 / 互動                             | [playwright-in-loop](/skills/frontend-with-playwright/playwright-in-loop/)           |
| Layout bug 第 2 次出現、想寫成測試                                    | [playwright-in-loop](/skills/frontend-with-playwright/playwright-in-loop/)           |
| 客製 UI 被 framework 還原、不知道該注入到哪                           | [framework-coexistence](/skills/frontend-with-playwright/framework-coexistence/)     |
| 要客製外部組件（pagefind / vendor library）                           | [framework-coexistence](/skills/frontend-with-playwright/framework-coexistence/)     |
| 使用者反映卡頓、CPU 100%、scroll lag、resize jank                     | [reactive-performance](/skills/frontend-with-playwright/reactive-performance/)       |
| 要設計 MutationObserver / event listener 範圍                         | [reactive-performance](/skills/frontend-with-playwright/reactive-performance/)       |
| 要驗收鍵盤 / screen reader / motor / 視覺 a11y                        | [accessibility-and-focus](/skills/frontend-with-playwright/accessibility-and-focus/) |
| JS reparent 後 focus 跑掉、aria-live 沒朗讀                           | [accessibility-and-focus](/skills/frontend-with-playwright/accessibility-and-focus/) |

每份 reference 自包含：讀任一份不需要回頭讀其他 reference。

## 跟 requirement-protocol 的關係

[requirement-protocol](/skills/requirement-protocol/) 是上層的「對話協議」（澄清需求、失敗轉折、覆寫成本、工具切換時機）；本 skill 是下層的「前端執行協議」（DOM / CSS / JS / Playwright 的具體做法）。

| 情境                                               | 該讀哪個 skill                       |
| -------------------------------------------------- | ------------------------------------ |
| 不確定該怎麼跟使用者溝通、需求模糊、失敗該怎麼轉折 | requirement-protocol                 |
| 知道要做什麼、不確定前端該怎麼實作驗證             | frontend-with-playwright（本 skill） |

兩個 skill 的 `playwright` 段落互補：requirement-protocol 講「何時切」、本 skill 講「切了之後具體寫什麼 query」。

## 與 blog 專案其他資料的關係

| 位置                                                                    | 角色                                                          |
| ----------------------------------------------------------------------- | ------------------------------------------------------------- |
| `.claude/skills/frontend-with-playwright/`                              | 實際 skill — Claude runtime 呼叫的檔案來源                    |
| `content/skills/frontend-with-playwright/`（本處）                      | 文章版本 — 人類讀者在 blog 閱讀                               |
| [`content/report/`](/report/)                                           | 50+ 篇事後檢討、本 skill 的素材來源；reference 結尾連回對應篇 |
| [`content/skills/requirement-protocol/`](/skills/requirement-protocol/) | 上層對話協議 skill                                            |

## Last Updated

2026-04-26 — 初版：v0.1.0 同步、六份 references 對應「DOM topology / CSS-JS 邊界 / Playwright 三位置 / framework 共處 / Reactive 效能 / A11y」六個情境。
