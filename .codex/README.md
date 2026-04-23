# .codex/ — Codex 行為規範與任務 Brief

本資料夾集中管理 Codex 在 blog 專案的行為規範與任務 brief。Codex 進入 blog 專案後，請先讀取本 README，再依任務類型讀取對應檔案。

---

## 目錄結構

```
.codex/
├── README.md                  # 本檔：目錄導航與讀取順序
├── codex.md                   # 總規範：寫作原則、決策框架、正面表述、檢查循環
└── briefs/
    ├── knowledge-cards.md           # Task 1：補卡 + 連結回填（當前執行）
    └── knowledge-web-expansion.md   # Task 2：知識網拓展（Task 1 完成後）
```

---

## 讀取順序

### 場景 1：一般撰寫任務（新文章 / 改寫既有文章）

| 順序 | 檔案 | 目的 |
|-----|------|------|
| 1 | `../codex.md` | 總規範：§2 寫作原則、§4 正面表述、§5 檢查循環 |
| 2 | `codex.md` §2.4 對應 reference | 依撰寫情境讀取 compositional-writing SKILL reference |
| 3 | 既有樣本文章 | 依系列（go / go-advanced / backend）挑 1-2 篇熟悉風格 |

### 場景 2：執行指定 brief

| 順序 | 檔案 | 目的 |
|-----|------|------|
| 1 | `../codex.md` | 理解總規範 |
| 2 | `briefs/<任務>.md` | 讀取本次任務的執行細節 |
| 3 | brief §0 前置閱讀 | 依 brief 內指定順序讀取相關資料 |

---

## 核心承諾

Codex 在本專案的行為建立在三個核心承諾上：

1. **以 SKILL 為權威**：寫作規範與決策框架的權威來源位於 `book_overview_v1/.claude/skills/`。本資料夾的內容是 blog 專案的應用說明，SKILL 原檔為最終依據。
2. **正面表述優先**：規範性描述採「應該 / 建議 / 以 X 為準」語氣。保留否定詞的情境見 `codex.md §4.3`（物理限制 / 安全警示 / 反模式對照）。
3. **生成後檢查循環**：每段產出後執行 `codex.md §5` C1–C7 檢查，含負向表述專項掃描。通過後才繼續下一段。

---

## 與 blog 專案其他文件的關係

| 資料 | 位置 | 用途 |
|------|------|------|
| 文章內容 | `content/` | 教材正文（go / go-advanced / backend / python / python-advanced） |
| 知識卡片 | `content/backend/knowledge-cards/` | 後端通用術語原子化解說 |
| Go 專屬術語 | `content/go/glossary.md` | Go 語言專屬詞彙表 |

本 `.codex/` 資料夾只承載**行為規範**與**任務 brief**，不承載教材內容。

---

**Last Updated**: 2026-04-23
**Version**: 0.1.0 — 初版：建立 .codex/ 導航索引
