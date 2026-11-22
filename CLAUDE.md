@AGENTS.md

---

# Claude Code 專屬的操作

Claude Code 依上方的 `@` 匯入，在 session 啟動時載入 AGENTS.md（規則的入口）的全文。分冊不用 `@` 匯入，否則每個 session 一啟動就載入全部分冊的全文；要讀哪一份照 `AGENTS.md`〈怎麼讀分冊〉。本檔只寫任何 session 都可能碰到的 Claude Code 操作，其餘的完整規則在 `docs/rules/claude-code.md`。共用的規則不寫在這裡，要改就改 AGENTS.md 或對應的分冊。

## 回覆語言的設定

回覆語言的規則在 `AGENTS.md`〈回覆語言〉。使用者層級的 `~/.claude/settings.json`（`"language": "繁體中文"`）已經把同一條指示注入系統提示；注入之後總結仍然會漂成英文，所以那一條的「送出前確認」照樣要做。

## Skill 的叫用

Claude Code 依 `.claude/skills/<name>/SKILL.md` frontmatter 的 `description` 比對當前任務，自動觸發 skill；系統提示裡會列出每個 skill 的 description。使用者在對話中打 `/<skill-name>` 手動叫用；agent 自己要叫用時用 Skill tool，不在回覆裡打斜線指令。

寫作類 skill 不等自動觸發、由 agent 主動叫用的規則，寫在 `AGENTS.md`〈寫作類 skill 的叫用〉。

## Memory 與規則檔的分工

寫 memory 之前，照 `docs/rules/claude-code.md`〈Memory 只記 repo 與文章以外的事〉判斷這筆內容寫在哪裡。agent 要照做的做法，包括使用者對寫法或工作方式的回饋，即使系統提示把它列為 memory 的一種，也寫進 repo，不寫進 memory。

## 規則分冊的讀取檢查

`.claude/hooks/rule_read_guard.py` 在寫入 repo 內的檔案、`bin/commit-files`、`bin/push-main` 與 `ssh` 之前查這個 agent 的 transcript，對應的分冊有還沒讀的就拒絕這次工具呼叫，拒絕理由列出要讀的檔案。用 Read 整份讀完（不帶 offset 與 limit）之後，照分冊檢查這次的內容或動作，不合規的先改再重送；subagent 要自己讀，context 被壓縮之後要重讀。

## 提交前對照編輯紀錄

`bin/commit-files` 提交前自己跑 `bin/session-edits-check --staged`，拿 transcript 重播的結果比對要提交的內容，確認 diff 都是這個 session 的編輯。工具只重播 Edit 與 Write，所以要提交的檔案的內容用 Edit 或 Write 改；用其他方式改的檔案，工具會印 `[ASK-USER]`。`bin/commit-files` 印出 `[ASK-USER]` 或 `session-edits-check exit` 時，照 `docs/rules/claude-code.md`〈提交前對照編輯紀錄〉處置；其餘的失敗照 `docs/rules/commit-push.md`〈提交〉。
