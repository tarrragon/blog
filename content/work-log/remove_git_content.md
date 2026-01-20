---
title: "Git Filter-Repo 使用說明"
date: 2026-01-20
draft: false
tags: ["git"]
---

# Git Filter-Repo 使用說明教學

`git filter-repo` 是一個強大的工具，用於重寫 Git 歷史記錄。它比 `git filter-branch` 更快、更安全，是官方推薦的替代方案。

## 目錄

- [安裝](#安裝)
- [基本概念](#基本概念)
- [常用操作](#常用操作)
  - [移除檔案或資料夾](#移除檔案或資料夾)
  - [只保留特定路徑](#只保留特定路徑)
  - [重新命名檔案或資料夾](#重新命名檔案或資料夾)
  - [修改 commit 訊息](#修改-commit-訊息)
  - [修改作者資訊](#修改作者資訊)
- [進階操作](#進階操作)
- [注意事項](#注意事項)
- [常見問題](#常見問題)

---

## 安裝

### macOS

```bash
# 使用 Homebrew
brew install git-filter-repo

# 或使用 pip
pip3 install git-filter-repo
```

### Linux

```bash
# Ubuntu/Debian
sudo apt install git-filter-repo

# 或使用 pip
pip3 install git-filter-repo
```

### Windows

```bash
# 使用 pip
pip install git-filter-repo
```

---

## 基本概念

### 什麼時候使用 git filter-repo？

- 從歷史記錄中移除敏感資訊（密碼、API 金鑰等）
- 移除不小心 commit 的大型檔案
- 將子目錄拆分成獨立的 repository
- 合併多個 repository
- 批量修改 commit 作者資訊

### 重要提醒

⚠️ `git filter-repo` 會**重寫 Git 歷史**，這意味著：

1. 所有 commit hash 都會改變
2. 需要 force push 到遠端
3. 其他協作者需要重新 clone 或 reset

---

## 常用操作

### 移除檔案或資料夾

#### 移除單一檔案

```bash
git filter-repo --invert-paths --path path/to/file.txt --force
```

#### 移除資料夾

```bash
git filter-repo --invert-paths --path path/to/folder --force
```

#### 移除多個路徑

```bash
git filter-repo --invert-paths --path .env --path secrets/ --path config/credentials.json --force
```

#### 使用 glob 模式移除

```bash
# 移除所有 .log 檔案
git filter-repo --invert-paths --path-glob '*.log' --force

# 移除所有 node_modules 資料夾
git filter-repo --invert-paths --path-glob '**/node_modules/*' --force
```

#### 使用正規表達式移除

```bash
# 移除所有 .env 開頭的檔案
git filter-repo --invert-paths --path-regex '^\.env.*' --force
```

### 只保留特定路徑

將 repository 縮減為只包含特定資料夾（適用於拆分專案）：

```bash
# 只保留 src 資料夾
git filter-repo --path src --force

# 保留多個路徑
git filter-repo --path src --path docs --path README.md --force
```

### 重新命名檔案或資料夾

```bash
# 將 old-name 重新命名為 new-name
git filter-repo --path-rename old-name:new-name --force

# 將資料夾移動到子目錄
git filter-repo --path-rename src:app/src --force

# 將所有檔案移到子目錄
git filter-repo --to-subdirectory-filter my-subdir --force
```

### 修改 commit 訊息

建立一個 Python 腳本 `message-callback.py`：

```python
# message-callback.py
import re

def message_callback(message):
    # 將 "bug" 替換為 "fix"
    return re.sub(b'bug', b'fix', message)
```

執行：

```bash
git filter-repo --message-callback '
    return message.replace(b"bug", b"fix")
' --force
```

或使用外部檔案：

```bash
git filter-repo --message-callback "$(cat message-callback.py)" --force
```

### 修改作者資訊

#### 使用 mailmap 檔案

建立 `.mailmap` 檔案：

```text
New Name <new@email.com> Old Name <old@email.com>
```

執行：

```bash
git filter-repo --mailmap .mailmap --force
```

#### 使用 callback 函數

```bash
git filter-repo --name-callback '
    return name.replace(b"OldName", b"NewName")
' --email-callback '
    return email.replace(b"old@email.com", b"new@email.com")
' --force
```

---

## 進階操作

### 移除大型檔案

找出大型檔案：

```bash
git filter-repo --analyze
cat .git/filter-repo/analysis/blob-shas-and-paths.txt | head -20
```

移除超過特定大小的檔案：

```bash
git filter-repo --strip-blobs-bigger-than 10M --force
```

### 替換敏感內容

建立替換規則檔案 `replacements.txt`：

```javascript
regex:password=.*==>password=REDACTED
literal:my-secret-api-key==>API_KEY_REMOVED
```

執行：

```bash
git filter-repo --replace-text replacements.txt --force
```

### 只處理部分歷史

```bash
# 只處理最近的 commit
git filter-repo --refs HEAD~10..HEAD --path sensitive-file --invert-paths --force

# 處理特定分支
git filter-repo --refs main --path old-folder --invert-paths --force
```

### 保留備份

```bash
# 在操作前建立備份分支
git branch backup-before-filter

# 或 clone 一份完整備份
git clone --mirror original-repo backup-repo
```

---

## 注意事項

### 操作前檢查清單

- [ ] 確保工作目錄是乾淨的（`git status` 無未 commit 的變更）
- [ ] 建立備份（branch 或完整 clone）
- [ ] 確認沒有其他人正在使用這個 repository
- [ ] 了解 force push 的影響

### Remote 會被移除


`git filter-repo` 執行後會**自動移除 `origin` remote**。執行時你會看到以下提示：

```
NOTICE: Removing 'origin' remote; see 'Why is my origin removed?'
        in the manual if you want to push back there.
```

#### 為什麼要移除 Remote？

這是 `git filter-repo` 的**安全機制設計**，目的是保護你和你的團隊：

1. **防止意外推送**：重寫歷史後，所有 commit hash 都會改變。如果你不小心直接執行 `git push`，會把重寫後的歷史推送到遠端，可能覆蓋其他人的工作，造成嚴重問題。

2. **強迫你停下來思考**：移除 remote 後，你必須：
   - 確認是否真的要推送重寫後的歷史
   - 手動重新加入 remote
   - 明確使用 `--force` 參數推送

3. **給你機會通知團隊**：在重新加入 remote 和 force push 之前，你有機會先通知其他協作者，讓他們做好準備。

#### 如何處理

執行完 `git filter-repo` 後，依序執行：

```bash
# 1. 重新加入 remote
git remote add origin <repository-url>

# 2. 確認 remote 已加入
git remote -v

# 3. Force push（確認團隊已知情後再執行）
git push origin --force --all
```


### Force Push

重寫歷史後需要 force push：

```bash
# Push 所有分支
git push origin --force --all

# Push 所有 tags
git push origin --force --tags
```

### 通知協作者

其他協作者需要執行以下操作來同步：

```bash
# 方法一：重新 clone（推薦）
git clone <repository-url>

# 方法二：強制重設（注意：會丟失本地未 push 的變更）
git fetch --all
git reset --hard origin/<branch-name>
```

---

## 常見問題

### Q: 執行時出現 "Refusing to run without fresh clone" 錯誤

這是安全機制，使用 `--force` 參數來覆蓋：

```bash
git filter-repo --invert-paths --path file.txt --force
```

### Q: 如何還原操作？

如果有備份分支：

```bash
git checkout backup-before-filter
git branch -D main
git checkout -b main
```

如果有備份 repository：

```bash
git remote add backup /path/to/backup-repo
git fetch backup
git reset --hard backup/main
```

### Q: 為什麼我的 repository 大小沒有變小？

執行以下命令來清理：

```bash
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### Q: 可以只影響特定分支嗎？

可以，使用 `--refs` 參數：

```bash
git filter-repo --invert-paths --path file.txt --refs main --force
```

### Q: 如何預覽變更而不實際執行？

使用 `--dry-run` 參數：

```bash
git filter-repo --invert-paths --path file.txt --dry-run
```

---

## 參考資源

- [官方文件](https://github.com/newren/git-filter-repo)
- [官方手冊](https://htmlpreview.github.io/?https://github.com/newren/git-filter-repo/blob/docs/html/git-filter-repo.html)
- [常見使用案例](https://github.com/newren/git-filter-repo/blob/main/Documentation/converting-from-filter-branch.md)
