---
title: "Git：git stash 的 -u 參數（連未追蹤檔案一起暫存）"
date: 2026-06-05
draft: false
description: "`git stash` 後切分支或 rebase，發現新建的檔案沒被收走、還散在工作目錄裡害你出狀況時回來看。原因是 stash 預設不收 untracked 檔案，附 -u 用法、正確流程與 commit-rebase 替代做法。"
tags: ["git"]
---

## 問題情境

開新功能時，工作目錄常常同時有「改過的舊檔案」和「全新建立的檔案」。
想用 `git stash` 暫時收起來去拉主線變更，卻發現新檔案沒被收進去，
還散在工作目錄裡，導致 rebase / 切分支時出狀況。

原因是預設的 `git stash` **不會收 untracked 檔案**。

---

## `-u` 是什麼

`-u` 是 `--include-untracked` 的縮寫，`u` 就是 **untracked**（未追蹤檔案）。

Git 把工作目錄的檔案分成幾種狀態，跟 stash 有關的是這三種：

| 狀態               | 意思                        | 預設 `git stash` 會收嗎？ |
| ------------------ | --------------------------- | ------------------------- |
| tracked + modified | Git 已追蹤、改過的檔案      | 會                        |
| untracked          | 全新檔案，從未 `git add` 過 | 不會（要 `-u`）           |
| ignored            | 被 `.gitignore` 忽略的檔案  | 不會（要 `-a` / `--all`） |

「untracked」就是 `git status` 裡出現在 `Untracked files:` 區塊的新檔案。

Git 預設不收 untracked，是因為這類檔案常是編譯產物、log、暫存檔，全收進 stash 反而把雜物一起搬動；要求用 `-u` 明確表態，是把「要不要連新檔一起暫存」的決定權留給操作者。`-a`（`--all`）範圍更大，連 `.gitignore` 忽略的也一起收，日常少用。

---

## 正確流程（拉主線變更）

```bash
git stash push -u -m "暫存"    # -u 連 untracked 新檔案一起收
git pull --rebase origin main  # 或 git fetch + git rebase
git stash pop                  # 把修改倒回工作目錄
```

---

## 替代做法

也可以「先 commit 再 rebase，事後再 `git reset --mixed HEAD~1` 把 commit 拆回未提交狀態」。
這個做法會把 untracked 新檔一起收進 commit，省去記得加 `-u` 的步驟，適合改動較大、想先有一個完整快照的情況。

兩者取捨：commit 法會在分支歷史暫時多一顆 commit，rebase 完要記得 `reset` 拆回；stash 法把改動收在 `refs/stash`、不進分支 log，但 untracked 檔要記得 `-u`。日常小改動用 stash 心智負擔較低，改動大或想保留完整快照時用 commit 法。
