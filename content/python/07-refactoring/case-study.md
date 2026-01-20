---
title: "重構案例研究"
date: 2026-01-20
description: "透過 v0.28.0 Hook 系統重構，說明重構時的思考過程"
weight: 75
---

# 重構案例研究：v0.28.0 Hook 系統重構

本章透過 v0.28.0 重構案例，說明重構時的思考過程。

## 問題：認知負擔過高

重構前的 task-dispatch 有 858 行，閱讀時需要同時追蹤：

- 代理人清單的硬編碼
- Git 操作的底層細節
- 重複出現的 worktree 解析邏輯

根據[序章的認知負擔理論](../../00-philosophy/cognitive-load/)，讀者的工作記憶一次只能處理 5-9 個項目。這個檔案遠遠超過了這個限制。

## 識別問題：用 Error Patterns 的方法

我們用 grep 找出重複的函式定義：

```bash
grep -rh "^def " .claude/hooks/*.py | sort | uniq -c | sort -rn
```

發現 `run_git_command` 在 4 個檔案中重複定義。這就是 IMP-001（重複程式碼）的症狀。

同樣的方法，我們識別出：

- **ARCH-001**：配置硬編碼在 task-dispatch 中
- **IMP-002**：`line[9:]` 這類魔法數字

詳細的識別方法參考[程式碼壞味道識別](../code-smells/)。

## 執行順序：為什麼是 Wave 1-4？

我們把重構分成四個階段，每個階段都有明確的目標和驗證點：

### Wave 1：建立共用程式庫

先建立模組框架，寫測試定義預期行為。這樣後續重構時，每次修改都有測試保護。

建立的模組：

| 職責 | 模組 |
|------|------|
| 讀取配置 | config_loader |
| 執行 Git 命令 | git_utils |
| 處理 Hook I/O | hook_io |
| 設定日誌 | hook_logging |

詳細的抽取技巧參考 [DRY 原則與共用程式庫](../dry-principle/)。

### Wave 2：配置分離

把 task-dispatch 中的硬編碼清單抽到 YAML：

- agents.yaml：代理人配置
- quality_rules.yaml：品質規則

這是行數最多的部分。詳細說明參考[配置與程式碼分離](../config-separation/)。

### Wave 3：逐檔重構

有了共用程式庫，逐一修改 Hook 檔案。每改完一個檔案就跑測試，確保沒改壞東西。

### Wave 4：驗證

28 個單元測試全部通過，確認重構沒有改變行為。

## 思考：為什麼先建程式庫再重構檔案？

如果直接改 Hook 檔案，會遇到「雞生蛋」問題：

- Hook A 需要共用函式
- 但共用函式還沒建立
- 先改 Hook A？還是先建共用函式？

我們的順序是：

1. 先建立共用模組（定義介面）
2. 寫測試確保介面正確
3. 再逐一重構 Hook 檔案

這樣每一步都有測試保護。

## 重構前後對比

```python
# 重構前：直接使用 subprocess
result = subprocess.run(
    ["git", "branch", "--show-current"],
    capture_output=True, text=True
)
branch = result.stdout.strip()
if branch in ["main", "master", "develop"]:
    ...

# 重構後：使用共用模組
from lib.git_utils import get_current_branch, is_protected_branch

branch = get_current_branch()
if is_protected_branch(branch):
    ...
```

這段程式碼的認知負擔從「需要理解 subprocess 細節」降到「只需要知道函式名稱」。

## 結果驗證

重構後的主要檔案變化：

| 檔案 | 重構前 | 重構後 | 縮減 |
|------|--------|--------|------|
| task-dispatch-readiness-check.py | 858 行 | 296 行 | -65% |
| branch-verify-hook.py | 238 行 | 109 行 | -54% |
| branch-status-reminder.py | 167 行 | 103 行 | -38% |

行數減少不是因為刪除了功能，而是因為：

- 配置移到 agents.yaml（不用讀配置的細節）
- Git 操作移到 git_utils（不用讀 subprocess 細節）

閱讀重構後的程式碼時，認知負擔明顯降低。

## 小結

重構的核心問題是：**這段程式碼讓讀者需要同時記住多少東西？**

- 識別問題：用 [Error Patterns 的檢測方法](../code-smells/)
- 解決問題：用職責分離的思考方式
- 驗證結果：看認知負擔是否降低

---

*上一章：[消除魔法數字](../magic-numbers/)*
