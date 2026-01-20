---
title: "DRY 原則與共用程式庫"
description: "學習識別重複程式碼並建立共用模組"
weight: 73
---

# DRY 原則與共用程式庫

DRY (Don't Repeat Yourself) 是軟體開發的核心原則之一。本章基於 Error Pattern IMP-001，學習如何識別重複程式碼並建立共用模組。

## 問題背景

### 症狀

相同功能在多個檔案中重複實作：

```python
# hooks/pre_commit.py
def run_git_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

# hooks/post_merge.py
def run_git_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

# hooks/branch_check.py
def run_git_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

# hooks/worktree_guardian.py
def run_git_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()
```

四個檔案中完全相同的函式定義！

### 5 Why 分析

1. Why 1: 相同的 run_git_command 函式在 4 個檔案中重複
2. Why 2: 每個 Hook 獨立開發，沒有共用模組
3. Why 3: 缺乏 Hook 系統的架構設計和共用程式庫規劃
4. Why 4: 快速開發時複製貼上最快
5. Why 5: **缺乏 DRY 原則的強制檢查機制**

## DRY 原則核心

### 為什麼重複程式碼是壞味道

1. **修改需要改多處**：發現 bug 時要改 4 個地方
2. **容易不一致**：某處修改了，其他地方忘記改
3. **增加維護成本**：新人需要理解多個版本
4. **測試困難**：需要測試每個副本

### DRY 不只是「不要複製貼上」

DRY 的完整含義是：

> Every piece of knowledge must have a single, unambiguous, authoritative representation within a system.
>
> — Andy Hunt & Dave Thomas, *The Pragmatic Programmer*

這意味著不只是程式碼，還包括：
- 業務邏輯
- 資料定義
- 配置資訊

## 識別重複程式碼

### 檢測方法

```bash
# 找出重複的函式定義
grep -rh "^def " .claude/hooks/*.py | sort | uniq -c | sort -rn | head -20

# 範例輸出：
#    4 def run_git_command(cmd):
#    3 def get_current_branch():
#    2 def parse_worktree_line(line):
```

### 重複類型

| 類型 | 範例 | 處理方式 |
|------|------|----------|
| 完全相同 | 複製貼上的程式碼 | 抽取到共用模組 |
| 結構相同 | 相似但參數不同 | 抽取並參數化 |
| 概念相同 | 做同樣的事但實作不同 | 統一介面 |

## 建立共用程式庫

### 步驟 1：規劃模組結構

```
.claude/lib/
├── __init__.py           # 模組初始化
├── git_utils.py          # Git 操作
├── file_utils.py         # 檔案處理
├── config_loader.py      # 配置載入
├── hook_io.py            # 輸入輸出
├── hook_logging.py       # 日誌系統
└── tests/                # 測試檔案
```

### 步驟 2：抽取共用函式

從重複程式碼中抽取出來，加上完整的型別標註和文件：

```python
# lib/git_utils.py
"""Git 操作工具模組。

提供常用的 Git 命令執行和結果解析功能。
"""

import subprocess
from pathlib import Path
from typing import List, Optional

def run_git_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    check: bool = False
) -> str:
    """執行 Git 命令並返回輸出。

    Args:
        cmd: Git 命令列表，例如 ["git", "status"]
        cwd: 工作目錄，預設為當前目錄
        check: 是否在命令失敗時拋出異常

    Returns:
        命令的標準輸出（已去除首尾空白）

    Raises:
        subprocess.CalledProcessError: 當 check=True 且命令失敗時

    Example:
        >>> run_git_command(["git", "branch", "--show-current"])
        'main'
    """
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        check=check
    )
    return result.stdout.strip()

def get_current_branch(cwd: Optional[Path] = None) -> str:
    """取得當前分支名稱。

    Args:
        cwd: 工作目錄

    Returns:
        當前分支名稱
    """
    return run_git_command(
        ["git", "branch", "--show-current"],
        cwd=cwd
    )

def get_repo_root(cwd: Optional[Path] = None) -> Path:
    """取得 Git 儲存庫根目錄。

    Args:
        cwd: 起始目錄

    Returns:
        儲存庫根目錄路徑
    """
    root = run_git_command(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd
    )
    return Path(root)
```

### 步驟 3：更新使用處

將所有使用處改為引用共用模組：

```python
# hooks/pre_commit.py（重構後）
from lib.git_utils import run_git_command, get_current_branch

def check_branch():
    """檢查當前分支。"""
    current_branch = get_current_branch()
    # 使用共用函式，不再重複定義
```

## 抽取技巧

### 處理微小差異

當重複程式碼有微小差異時，使用參數化：

```python
# 重構前：三個版本的 parse_worktree_line
# version 1
def parse_worktree_line(line):
    if line.startswith("worktree "):
        return line[9:]

# version 2
def parse_worktree_line(line):
    if line.startswith("worktree "):
        return line[9:].strip()

# version 3
def parse_worktree_line(line):
    return line.removeprefix("worktree ")
```

```python
# 重構後：統一實作，支援選項
WORKTREE_PREFIX = "worktree "

def parse_worktree_line(line: str, strip: bool = True) -> str:
    """解析 worktree 輸出行。

    Args:
        line: worktree 輸出行
        strip: 是否去除首尾空白

    Returns:
        解析後的路徑
    """
    result = line.removeprefix(WORKTREE_PREFIX)
    return result.strip() if strip else result
```

### 使用高階函式

當邏輯結構相同但操作不同時：

```python
# 重構前：重複的迴圈結構
def check_all_python_files():
    for file in Path(".").glob("**/*.py"):
        if validate_python(file):
            print(f"OK: {file}")

def check_all_yaml_files():
    for file in Path(".").glob("**/*.yaml"):
        if validate_yaml(file):
            print(f"OK: {file}")
```

```python
# 重構後：抽取共用邏輯
from typing import Callable

def check_files(
    pattern: str,
    validator: Callable[[Path], bool]
) -> None:
    """檢查符合模式的所有檔案。

    Args:
        pattern: glob 模式
        validator: 驗證函式
    """
    for file in Path(".").glob(pattern):
        if validator(file):
            print(f"OK: {file}")

# 使用
check_files("**/*.py", validate_python)
check_files("**/*.yaml", validate_yaml)
```

## 共用模組設計原則

### 1. 單一職責

每個模組只負責一類功能：

```python
# 好：職責明確
git_utils.py      # Git 操作
file_utils.py     # 檔案操作
config_loader.py  # 配置載入

# 壞：職責不明
utils.py          # 什麼都放
helpers.py        # 更模糊
```

### 2. 穩定的介面

公開介面要穩定，內部實作可以改變：

```python
# __init__.py - 定義公開介面
from .git_utils import (
    run_git_command,
    get_current_branch,
    get_repo_root,
)

# 使用者透過介面使用
from lib import run_git_command
```

### 3. 完整的文件

每個公開函式都要有文件字串：

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """簡短描述（一行）。

    更詳細的說明（可選）。

    Args:
        param1: 參數 1 的說明
        param2: 參數 2 的說明

    Returns:
        返回值的說明

    Raises:
        ExceptionType: 何時會拋出

    Example:
        >>> function_name("a", "b")
        "ab"
    """
```

### 4. 充分的測試

每個共用函式都要有測試：

```python
# tests/test_git_utils.py
import unittest
from unittest.mock import patch
from lib.git_utils import get_current_branch

class TestGetCurrentBranch(unittest.TestCase):
    @patch("lib.git_utils.run_git_command")
    def test_returns_branch_name(self, mock_run):
        mock_run.return_value = "main"

        result = get_current_branch()

        self.assertEqual(result, "main")
        mock_run.assert_called_once_with(
            ["git", "branch", "--show-current"],
            cwd=None
        )
```

## 重構步驟

完整的重複程式碼重構流程：

```
1. 識別重複
   ↓
2. 確定共用邏輯
   ↓
3. 設計介面
   ↓
4. 撰寫共用模組
   ↓
5. 撰寫測試
   ↓
6. 替換使用處
   ↓
7. 驗證功能
```

### 實際案例

v0.28.0 重構的統計：

| 函式 | 重複次數 | 重構後 |
|------|----------|--------|
| run_git_command | 4 | 1 (git_utils.py) |
| get_current_branch | 3 | 1 (git_utils.py) |
| parse_worktree_line | 2 | 1 (git_utils.py) |
| load_json | 2 | 1 (hook_io.py) |

總計消除約 415 行重複程式碼。

## 常見錯誤

### 錯誤 1：過早抽象

```python
# 錯誤：只用一次就抽出去
def add_two_numbers(a, b):
    return a + b

result = add_two_numbers(1, 2)  # 過度抽象
```

**原則**：至少重複兩次再抽取（Rule of Three）。

### 錯誤 2：強行統一

```python
# 錯誤：強行統一不同的概念
def process(data, mode):
    if mode == "validate":
        # 驗證邏輯
    elif mode == "transform":
        # 轉換邏輯
    elif mode == "export":
        # 匯出邏輯
```

**解決**：不同概念應該是不同的函式。

### 錯誤 3：忽略測試

重構時沒有先寫測試，導致引入新 bug。

**原則**：先寫測試，確保重構不改變行為。

## 實作練習

### 練習 1：識別重複

檢視以下程式碼，找出可以抽取的重複：

```python
# file1.py
def process_user_data(user):
    if not user.get("name"):
        return {"error": "缺少姓名"}
    if not user.get("email"):
        return {"error": "缺少信箱"}
    return {"success": True, "data": user}

# file2.py
def process_order_data(order):
    if not order.get("product"):
        return {"error": "缺少商品"}
    if not order.get("quantity"):
        return {"error": "缺少數量"}
    return {"success": True, "data": order}
```

<details>
<summary>參考答案</summary>

重複的模式：驗證必填欄位並返回統一格式。

```python
# lib/validation.py
from typing import Any, Dict, List

def validate_required_fields(
    data: Dict[str, Any],
    required_fields: List[str]
) -> Dict[str, Any]:
    """驗證必填欄位。

    Args:
        data: 要驗證的資料
        required_fields: 必填欄位清單

    Returns:
        包含 success/error 的結果字典
    """
    for field in required_fields:
        if not data.get(field):
            return {"error": f"缺少{field}"}
    return {"success": True, "data": data}

# 使用
def process_user_data(user):
    return validate_required_fields(user, ["name", "email"])

def process_order_data(order):
    return validate_required_fields(order, ["product", "quantity"])
```

</details>

### 練習 2：設計共用模組

為以下重複的日誌邏輯設計共用模組：

```python
# 多個檔案都有類似的程式碼
print(f"[INFO] {datetime.now()} - 開始處理")
print(f"[ERROR] {datetime.now()} - 處理失敗: {error}")
print(f"[SUCCESS] {datetime.now()} - 完成")
```

<details>
<summary>參考答案</summary>

```python
# lib/hook_logging.py
from datetime import datetime
from typing import Optional

def _log(level: str, message: str) -> None:
    """輸出日誌訊息。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{level}] {timestamp} - {message}")

def info(message: str) -> None:
    """輸出資訊日誌。"""
    _log("INFO", message)

def error(message: str, exception: Optional[Exception] = None) -> None:
    """輸出錯誤日誌。"""
    if exception:
        message = f"{message}: {exception}"
    _log("ERROR", message)

def success(message: str) -> None:
    """輸出成功日誌。"""
    _log("SUCCESS", message)

# 使用
from lib.hook_logging import info, error, success

info("開始處理")
error("處理失敗", e)
success("完成")
```

</details>

## 小結

- DRY 原則要求每個知識只有單一權威來源
- 使用 grep 識別重複的函式定義
- 建立結構清晰的共用程式庫
- 重構時要先寫測試，確保行為不變
- 不要過早抽象，至少重複兩次再抽取

## 下一步

- [消除魔法數字](../magic-numbers/) - 另一種程式碼品質問題
- [重構案例研究](../case-study/) - 看完整的重構流程

---

*文件版本：v0.30.0*
*建立日期：2026-01-20*
