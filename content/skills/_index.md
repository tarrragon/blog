---
title: "Skills — Claude skill 的文章版本"
date: 2026-04-24
description: "收錄 .claude/skills/ 底下的 Claude runtime skill 轉為 blog 文章的版本，以及把 skill 搬進來的標準流程。"
tags: ["skills", "Claude", "寫作方法論", "工具設計"]
---

## 這個資料夾是什麼

`content/skills/` 收錄**從 `.claude/skills/` 轉成文章**的 skill 版本。

同一份 skill 有兩種存在形式，各自負責不同角色：

| 位置                             | 角色                            | 讀者     |
| -------------------------------- | ------------------------------- | -------- |
| `.claude/skills/<name>/`         | 實際 skill，Claude runtime 呼叫 | Claude   |
| `content/skills/<name>/`（本處） | 文章版本，Hugo 渲染成 blog 頁   | 人類讀者 |

兩處內容相同、結構略有差異：`.claude/` 版本保留原始 `SKILL.md + references/` 巢狀結構以配合 Claude 的路徑解析；`content/` 版本扁平化（references 內容升級到同層），以契合 blog 的單層文章呈現。

## 目前收錄的 skill

| Skill                    | 主題                                                                                                                         | 入口                                                                   |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| compositional-writing    | Zettelkasten 式組合寫作方法論                                                                                                | [/skills/compositional-writing/](/skills/compositional-writing/)       |
| requirement-protocol     | 需求確認到實作的對話協議（模糊指令、失敗轉折、漸進驗證等）                                                                   | [/skills/requirement-protocol/](/skills/requirement-protocol/)         |
| frontend-with-playwright | 框架無關的前端開發 + Playwright 驗證 + Filter × Source 跨領域 stream 操作（DOM / CSS / JS / framework 共處 / a11y / 資料流） | [/skills/frontend-with-playwright/](/skills/frontend-with-playwright/) |
| wrap-decision            | WRAP 決策框架（錨點確認、資料充足度、擴增選項、實境檢驗、機會成本、行前預想與絆腳索）                                        | [/skills/wrap-decision/](/skills/wrap-decision/)                       |

---

## 把新 skill 轉成文章的標準流程

以下步驟假設新 skill 已經放在 `.claude/skills/<name>/`，包含 `SKILL.md` 和（可能的）`references/` 子資料夾。

### Step 1：複製一份到 content/skills/

```bash
cp -R .claude/skills/<name> content/skills/<name>
```

Claude 版保持原樣、不再動它；所有後續修改都只改文章版。

### Step 2：扁平化 references/

Blog 的文章層級為**單層**，不保留 references 子資料夾。把所有 reference 移到跟 SKILL.md 同一層：

```bash
cd content/skills/<name>
git mv references/*.md .
git rm references/.gitkeep       # 如果有
rmdir references
```

### Step 3：把 `SKILL.md` 改成小寫 `skill.md`

Hugo pretty URL 會把檔名小寫輸出（`SKILL.md` → `/skills/<name>/skill/`），但 `mdtools cards` 連結檢查以**檔名大小寫敏感**的方式解析 URL 回檔案位置。若檔案是 `SKILL.md`，cards 嘗試開啟 `skill.md` 找不到，就會報 `L1-broken-link`。

避免這個陷阱，把 content 版本的檔名直接改成小寫：

```bash
git mv content/skills/<name>/SKILL.md content/skills/<name>/skill.md
```

`.claude/` 版保留原本的 `SKILL.md`（符合 Claude skill 慣例）。兩邊檔名不同是刻意的：runtime 讀 `.claude/SKILL.md`、Hugo 渲染 `content/skill.md`、cards check 能解析。

### Step 4：修改 skill.md 的內部連結

skill.md 裡原本的 `references/X.md` 引用要改。有兩種合法寫法擇一：

- **Markdown 相對路徑**：`./X.md` — 最無痛，Hugo render hook 會自動解析到對應頁面
- **Hugo content-root 絕對路徑**：`/skills/<name>/<slug>/` — 最穩，跟 blog 其他文章遷移後的寫法一致

批次替換範例（將 `references/` 前綴整串刪除）：

```bash
sed -i '' 's|references/|./|g' content/skills/<name>/skill.md
```

記得同時更新 `## Directory Index` 區塊那張 ASCII tree — 刪掉 `└── references/` 那一層、所有 reference 檔案縮排提到 skill.md 同層。

### Step 5：建立 `_index.md`（section 索引）

`content/skills/<name>/_index.md` 是 Hugo section 的 landing page，URL 是 `/skills/<name>/`。

必備欄位（Hugo + mdtools 要求）：

```yaml
---
title: "<Skill 名稱中英對照>"
date: <YYYY-MM-DD>
description: "<一句話描述 skill 做什麼>"
tags: [...]
---
```

內容建議包含：

1. **簡述**：這個 skill 是什麼、解決什麼問題
2. **閱讀順序**：場景 1（第一次接觸）與場景 2（已熟悉、直接解決任務）兩個切入點
3. **觸發路由表**：複製 SKILL.md 的「When to Consult This Skill」表，但把檔案路徑替換成 Hugo 絕對 URL（`/skills/<name>/<slug>/`）
4. **與 blog 其他資料的關係**：對照表（`.claude/skills/<name>/`、相關 `content/posts/...`）
5. **Last Updated**：同步日期與 `.claude/` 版 SKILL.md 的 version

可參考 [compositional-writing 的 `_index.md`](https://github.com/tarrragon/blog/blob/main/content/skills/compositional-writing/_index.md) 當範本。

### Step 6：補 Hugo frontmatter 到 skill.md 與每份 reference

原始 skill.md 與 reference 的 frontmatter 是為 Claude runtime 設計的（欄位多為 `name`/`license`/`metadata`），Hugo 與 mdtools 需要的是 `title` + `date`。每份檔案：

1. 把原 frontmatter 保留或替換成 Hugo 規格（`title`、`date`、`description`、`tags`）
2. 刪掉 body 開頭的 `# H1`（Hugo 會從 `title` 自動生成 H1，保留會觸發 `MD025-no-body-h1`）

### Step 7：跑 `make check` 與 `hugo` 驗收

```bash
make check    # fmt + lint + cards，三個閘門全綠
hugo          # 確認無 WARN/ERROR，page count 多了對應檔數
```

幾個常見訊號與對應的修補點：

| 訊號                                                      | 原因                                   | 回頭修 |
| --------------------------------------------------------- | -------------------------------------- | ------ |
| lint `front-matter-required` / `MD025`                    | 有檔案漏掉 frontmatter 或 body H1 沒刪 | Step 6 |
| cards `L1-broken-link target not found` 且路徑是 `skill/` | SKILL.md 沒改成 skill.md（檔名大小寫） | Step 3 |
| hugo `REF_NOT_FOUND`                                      | 連結還指向 `references/`               | Step 4 |

### Step 8：更新本 `content/skills/_index.md` 的「目前收錄」表

把新 skill 加入上方的表格，含主題一句話與 Hugo URL。

### Step 9：commit

單一 commit 收尾：

```bash
git add .claude/skills/<name> content/skills/<name> content/skills/_index.md
git commit -m "docs(skills): import <name> skill"
```

---

## 設計決策備忘

**為什麼 `.claude/` 保留 references/、`content/` 扁平？**

`.claude/` 是 Claude runtime 的 SKILL 執行環境，SKILL.md 的路徑解析（`references/X.md`）是 skill 原生協議的一部分 — 改了會破壞 Claude 讀取行為。

`content/` 是 blog 文章，Hugo 的 pretty URL 傾向單層結構（`/skills/name/page/` 比 `/skills/name/references/page/` 乾淨）。扁平化也讓 render hook 的 tooltip 與 mdtools 的 card graph 不必穿一層目錄。

兩種結構並行、各自最佳化、用 step 1 的複製動作維持同步。

**為什麼不直接 symlink `content/skills/` → `.claude/skills/`？**

Symlink 會讓兩邊共用 frontmatter 與路徑規範。`.claude/` 版的 frontmatter 是 skill protocol（`name`/`license`/`metadata`），與 Hugo 要的（`title`/`date`）相衝；body 開頭的 `# H1` 是 Claude 讀者的 context signpost，但在 Hugo 會跟 `title` 生的 H1 重複。結構上看似省事，語意上兩邊是不同受眾的產出，應該允許各自演化。

---

## Last Updated

2026-04-24 — 初版：compositional-writing 轉文章完成，記錄標準流程。
