# .codex/ — Codex 行為規範與任務 Brief

本資料夾集中管理 Codex 在 blog 專案的行為規範與任務 brief。Codex 進入 blog 專案後，請先讀取本 README，再依任務類型讀取對應檔案。

---

## 目錄結構

```
.codex/
├── README.md                  # 本檔：目錄導航與讀取順序
├── skills -> ../.claude/skills  # symlink：與 Claude Code 共用同一組 skill
├── briefs/
│   ├── knowledge-cards.md           # Task 1：補卡 + 連結回填
│   └── knowledge-web-expansion.md   # Task 2：知識網拓展（Task 1 完成後）
└── outlines/                  # 過去任務的大綱與審查紀錄（歷史資料，不是現行規範）
```

---

## 讀取順序

### 場景 1：一般撰寫任務（新文章 / 改寫既有文章）

| 順序 | 檔案                                                       | 目的                                                                             |
| ---- | ---------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 1    | repo 根目錄的 `AGENTS.md`                                  | 規則入口：優先序、每個 session 都用到的規則，以及指向 `docs/rules/` 分冊的路由表 |
| 2    | 路由表指到的 `docs/rules/` 分冊                            | 依 `AGENTS.md`〈怎麼讀分冊〉的路由表，照這次要改的路徑讀取                       |
| 3    | `compositional-writing` skill 的觸發路由表指到的 reference | 依撰寫情境讀取對應的 reference                                                   |
| 4    | 既有樣本文章                                               | 依系列（go / go-advanced / backend）挑 1-2 篇熟悉風格                            |

### 場景 2：執行指定 brief

| 順序 | 檔案                                         | 目的                            |
| ---- | -------------------------------------------- | ------------------------------- |
| 1    | repo 根目錄的 `AGENTS.md` 與路由表指到的分冊 | 理解規則                        |
| 2    | `briefs/<任務>.md`                           | 讀取本次任務的執行細節          |
| 3    | brief §0 前置閱讀                            | 依 brief 內指定順序讀取相關資料 |

---

## 核心承諾

Codex 在本專案的行為建立在三個核心承諾上：

1. **以 AGENTS.md 為權威**：寫作與工程規則的單一真實來源是 repo 根目錄的 `AGENTS.md` 與它路由到的 `docs/rules/` 分冊；寫作時另外遵循本 repo `.claude/skills/`（經由 `.codex/skills` 這條 symlink 讀到）裡的 `compositional-writing` skill。本資料夾的內容是任務 brief，與規則檔衝突時以規則檔為準。
2. **正面表述優先**：主要敘述用正向句建立概念，規則與掃描方式見 `docs/rules/writing.md`〈主要敘述用正向陳述〉。
3. **生成後檢查**：產出之後照 `docs/rules/writing-process.md`〈文章產出流程〉的字句層掃描與〈完稿檢查清單〉逐項確認，通過後才繼續下一段。

---

## 與 blog 專案其他文件的關係

| 資料        | 位置                               | 用途                                                              |
| ----------- | ---------------------------------- | ----------------------------------------------------------------- |
| 文章內容    | `content/`                         | 教材正文（go / go-advanced / backend / python / python-advanced） |
| 知識卡片    | `content/backend/knowledge-cards/` | 後端通用術語原子化解說                                            |
| Go 專屬術語 | `content/go/glossary.md`           | Go 語言專屬詞彙表                                                 |

本 `.codex/` 資料夾只承載**行為規範**與**任務 brief**，不承載教材內容。

---

**Last Updated**: 2026-10-25
**Version**: 0.2.0 — 讀取順序與核心承諾改指 AGENTS.md 與 `docs/rules/` 分冊（原本指向的 codex.md 已不存在）；目錄結構補上 skills symlink 與 outlines/
