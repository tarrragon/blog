---
title: "新增頂層 content 資料夾要同步首頁 _index.md 入口"
date: 2026-05-20
weight: 139
description: "Hugo 不會 auto-list 頂層資料夾、首頁的模組清單是 content/_index.md 的手動 curated markdown。新增 content/<module>/ 後若沒同步加入口、模組在首頁完全不可發現；讀者只能靠搜尋或直接打 URL 才進得去。本卡把『新增頂層資料夾 + 首頁入口』綁成同 commit 的雙生動作、避免下次再漏。是 #44 SSoT 在『首頁清單』維度 + #97 metadata surface 在『上層索引』維度的具體案例。"
tags: ["report", "事後檢討", "工程方法論", "原則", "Hugo", "教材結構"]
---

## 核心原則

新增頂層 content 資料夾的同個 commit、必須同步把該模組入口加進首頁 `content/_index.md` 的對應分類段。Hugo 不會自動把 content/ 下的頂層目錄列在首頁、首頁完全靠 `content/_index.md` 的 markdown 內容渲染。模組內部建得再完整、首頁沒入口 = 該模組對新讀者不可發現。

| 動作                                              | 是否會在首頁顯示                 |
| ------------------------------------------------- | -------------------------------- |
| 建立 `content/<module>/_index.md`                 | 不會、Hugo 不 auto-list 頂層目錄 |
| 在 `hugo.toml` 加 `[[menu.main]]` entry           | 顯示在頂部選單、跟首頁清單無關   |
| 在 `content/_index.md` 對應分類段加 markdown link | 顯示在首頁                       |

判別問題：「**新讀者從首頁進來、能不能 1-2 個 click 走到該模組？**」答案是「不能」就是入口斷裂。

---

## 情境

建立新教學模組（例：`content/business/`）走 case-first 完整流程：寫 `_index.md`、批次建 knowledge-cards、補 reading-frameworks、寫 case-analyses 文章、跑 mdtools 三項檢查、commit + push。模組內部 50 個檔案全綠、卡片網路雙向連結完整、case-first + agent team review 跑完。

問題是首頁 `content/_index.md` 的「教學系列」段沒同步更新、business 模組從首頁進入的入口完全缺席。讀者反饋「我在 blog 首頁沒看到商業這個分類」之前、新模組對 organic traffic 是隱形的。

具體 case：c2c01bf 建立 `content/business/` 50 個檔案、但 `content/_index.md` 的 `## 教學系列` 段沒加 `[商業概念與策略分析](/business/)` 入口；f665e6d 才補上。這個 gap 在過去 backend / llm / ci 等模組可能也遇過、但當時由建立者順手補上、沒成為被紀錄的 retrospective、所以 pattern 沒浮現。

---

## 理想做法

### 第一步：把「新增頂層資料夾」跟「首頁入口」綁成同一個 commit

寫新模組的 PR / commit 時、把 `content/_index.md` 的修改一起放進去。Commit message 明確點出兩件事：

```text
business: 新增商業教材模組 + 首頁入口

- content/business/ 50 檔
- content/_index.md 教學系列段加入口
```

避免拆兩個 commit、避免「下個 PR 再補」。

### 第二步：完稿檢查清單加一條

AGENTS.md §6 完稿檢查清單明列：

```text
- [ ] 新增頂層 content/<module>/ 資料夾時、已同步更新 content/_index.md 對應分類段
```

寫完模組準備 commit 前、過 checklist 時會被 catch。

### 第三步：考慮工具化（可選、不強制）

長期可寫 mdtools check：列出 `content/` 頂層資料夾、跟 `content/_index.md` 的 markdown link 比對、缺的警告。但這個 check 有 false positive 風險（不是所有資料夾都該上首頁、例如 `record` / `report` / `work-log` 是已存在但獨立的 surface、`tags` 是 Hugo 自動產生），實作前先設計 whitelist 機制。建議優先靠 checklist、不急著工具化。

---

## 沒這樣做的麻煩

### 新模組對首頁讀者完全不可發現

讀者從 blog 首頁進來、看到的是 `content/_index.md` 渲染的內容。新模組沒在那個 markdown 裡 = 該模組對 organic traffic 完全消失。內部結構建得再好、卡片再多、case 寫得再深、新讀者進不來 = 等於沒上線。Search 跟 sitemap 是備援、不是主要入口。

### 補救拆成第二個 commit、歷史變零碎

漏掉的入口要事後補、commit 歷史會變成「建模組」+「補首頁入口」兩個 commit。如果在多個 PR 之間，補入口 commit 容易被誤判為瑣碎的 typo fix、reviewer 不會深究、變成 silent fix。

### Pattern 不紀錄、每個新模組都重蹈覆轍

backend / llm / ci 等過去新模組可能也遇過相同 gap、但當時被建立者順手補了、沒成為被紀錄的 retrospective。Pattern 不浮現 = 下個建模組者重蹈覆轍。本卡的責任就是把這個 pattern 紀錄下來、進完稿檢查清單後變成結構性保證。

---

## 跟其他抽象層原則的關係

- **[#44 Single Source of Truth](../single-source-of-truth/)**：本卡是 #44 在「首頁清單」維度的具體案例。`content/_index.md` 的「教學系列」段是讀者入口的 SSoT、不是 auto-derived from filesystem。建立模組時這個 SSoT 沒同步 = SSoT 違反。
- **[#97 Metadata surface 要納入寫作 review 範圍](../metadata-surface-in-writing-review/)**：本卡是 #97 在「上一層 surface」的具體形態。一個模組的 metadata surface 不只是它自己的 title / description / heading、還包括「上一層索引怎麼提它」— 首頁清單就是 module 的上層 metadata surface、跟模組內 metadata 一樣值得納入 review。
- **[#131 教材完整性要用讀者旅程驗證](../teaching-completeness-by-learner-journey/)**：本卡是 #131 在「讀者旅程起點」的具體 gotcha。讀者旅程的入口是首頁、首頁沒 link 等於旅程斷在 step 0。模組內部教學完整性再高、入口斷裂就是 0-completion。
- **[#95 Multi-pass scope 要蓋同類風險區](../multi-pass-scope-must-cover-risk-zone/)**：本卡跟 #95 的關係是「同類風險區包括上游引用點」。寫新模組時 scope 不只限模組內部、要涵蓋上游引用該模組的所有位置（首頁 / sibling 模組 _index.md cross-link / `AGENTS.md` / `CLAUDE.md`）。

---

## 判讀徵兆

| 徵兆                                                             | 該做的事                                                       |
| ---------------------------------------------------------------- | -------------------------------------------------------------- |
| Commit 建了新頂層 `content/<module>/` 但沒動 `content/_index.md` | check 首頁入口、補同 commit 或下個 commit 立刻補 + 寫 retro 卡 |
| 讀者反饋「我在首頁沒看到 X」                                     | too late、應在建模組同 commit 修；同步紀錄 retro 確認 pattern  |
| 不確定首頁清單是否自動產生                                       | 不是、`content/_index.md` 是手動 markdown、Hugo 不 auto-list   |
| 完稿檢查清單沒列「同步首頁入口」                                 | 補進 `AGENTS.md` §6                                            |
| Sibling 模組 `_index.md` 提到新模組時沒 cross-link               | 同類風險、scope 要蓋所有上游引用點、不只首頁                   |

---

## 適用範圍與邊界

- **適用範圍**：
  - 新增 `content/<module>/` 頂層教學資料夾（Backend / LLM / CI / Business / 未來新模組）
  - 把既有頂層資料夾「升格」成正式教學系列（例如從草稿區抽出獨立 surface）
- **不適用**：
  - 新增現有模組的子章節（例如 `content/backend/01-database/` 下新檔）— 這由模組自己的 `_index.md` 路由、不涉及首頁
  - 新增 `content/posts/` 下單篇文章 — posts 是 chronological feed、首頁分類段不負責列每篇文章
  - 新增 `content/work-log/` 或 `content/report/` 下單張卡片 — 同上、這些是已建立的 surface、清單在各自 `_index.md`
- **邊界**：本卡只處理「首頁入口」一個 surface；其他上游引用點（例如 sibling 模組 `_index.md` 提及本模組、`AGENTS.md` 提及本模組、`CLAUDE.md` 提及本模組）是同 pattern 的延伸、但個別 cross-link 要靠該位置自己的 review 維護
