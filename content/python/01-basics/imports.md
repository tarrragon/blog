---
title: "1.3 導入機制與路徑管理"
date: 2026-01-20
description: "解決模組找不到的問題"
weight: 3
---

# 導入機制與路徑管理

「ModuleNotFoundError」是 Python 開發者最常遇到的錯誤之一。理解導入機制可以幫助你快速解決這類問題。

## 模組搜尋路徑

Python 使用 `sys.path` 列表來搜尋模組。你可以查看當前的搜尋路徑：

```python
import sys
for path in sys.path:
    print(path)
```

典型輸出：

```
/current/script/directory     # 腳本所在目錄
/usr/local/lib/python3.11     # 標準庫
/usr/local/lib/python3.11/site-packages  # 第三方套件
```

## Hook 腳本的導入問題

### 問題情境

Hook 腳本位於 `.claude/hooks/`，共用模組位於 `.claude/lib/`：

```
.claude/
├── hooks/
│   └── branch-verify-hook.py    # 需要導入 lib 的模組
└── lib/
    ├── __init__.py
    └── git_utils.py
```

如果直接在 Hook 腳本中寫 `from git_utils import ...`，會得到 `ModuleNotFoundError`。

### 解決方案

在導入前將 lib 目錄加入搜尋路徑：

```python
#!/usr/bin/env python3
"""Branch Verify Hook"""

import sys
from pathlib import Path

# 計算 lib 目錄的路徑
# __file__ = .claude/hooks/branch-verify-hook.py
# parent = .claude/hooks/
# parent.parent = .claude/
# parent.parent / "lib" = .claude/lib/
lib_path = Path(__file__).parent.parent / "lib"

# 插入到搜尋路徑的最前面
sys.path.insert(0, str(lib_path))

# 現在可以導入了
from git_utils import get_current_branch
from hook_io import read_hook_input
```

### 為什麼用 `insert(0, ...)` 而不是 `append(...)`？

```python
# 優先搜尋我們的模組（推薦）
sys.path.insert(0, str(lib_path))

# 最後才搜尋我們的模組（可能被標準庫覆蓋）
sys.path.append(str(lib_path))
```

如果你的模組名稱與標準庫衝突（例如 `email.py`），使用 `append` 會導致導入標準庫而非你的模組。

## 使用 Path 物件

### Path 的基本操作

```python
from pathlib import Path

# 取得目前檔案的路徑
current_file = Path(__file__)

# 取得父目錄
parent_dir = current_file.parent

# 組合路徑
lib_path = parent_dir / "lib"  # 使用 / 運算子

# 轉換為字串
lib_path_str = str(lib_path)
```

### 路徑解析的陷阱

```python
# __file__ 可能是相對路徑
print(__file__)  # 可能是 "./hooks/my_hook.py"

# 轉換為絕對路徑
absolute_path = Path(__file__).resolve()
print(absolute_path)  # "/home/user/project/.claude/hooks/my_hook.py"
```

## 環境變數方式

另一種方法是使用 `PYTHONPATH` 環境變數：

```bash
# 在 shell 中設定
export PYTHONPATH="${PYTHONPATH}:/path/to/.claude/lib"

# 然後執行腳本
python .claude/hooks/my_hook.py
```

## 專案根目錄的取得

Hook 系統中經常需要取得專案根目錄：

```python
def get_project_root() -> str:
    """
    獲取專案根目錄（git 倉庫根目錄）

    Returns:
        str: 專案根目錄路徑
    """
    success, output = run_git_command(["rev-parse", "--show-toplevel"])
    return output if success else os.getcwd()
```

使用範例：

```python
root = get_project_root()
config_path = os.path.join(root, ".claude", "config.json")
```

## 常見錯誤與解決

### 錯誤 1: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'git_utils'
```

**解決方案**：確認 `sys.path.insert()` 在導入語句之前。

### 錯誤 2: 相對導入錯誤

```
ImportError: attempted relative import with no known parent package
```

**原因**：在腳本中使用相對導入。

**解決方案**：在腳本中使用絕對導入，相對導入只用於套件內部。

```python
# 錯誤：在腳本中使用相對導入
from .lib import git_utils

# 正確：使用絕對導入
from lib import git_utils
```

### 錯誤 3: 循環導入

```
ImportError: cannot import name 'xxx' from partially initialized module
```

**解決方案**：重構程式碼，避免模組間互相依賴。

## 導入風格指南

### 導入順序（PEP 8）

```python
# 1. 標準庫
import os
import sys
from pathlib import Path

# 2. 第三方套件
import yaml
import requests

# 3. 本地模組
from lib.git_utils import get_current_branch
from lib.hook_io import read_hook_input
```

### 避免 `import *`

```python
# 不推薦
from lib.git_utils import *

# 推薦
from lib.git_utils import (
    get_current_branch,
    get_project_root,
    is_protected_branch,
)
```

### 長導入的換行

```python
from lib.git_utils import (
    run_git_command,
    get_current_branch,
    get_project_root,
    get_worktree_list,
    is_protected_branch,
    is_allowed_branch,
)
```

## 實際範例：完整的 Hook 腳本開頭

```python
#!/usr/bin/env python3
"""
Branch Verify Hook

驗證當前分支是否適合進行編輯操作。
"""

# ===== 標準庫導入 =====
import os
import sys
from pathlib import Path

# ===== 路徑設定 =====
# 將 lib 目錄加入搜尋路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

# ===== 本地模組導入 =====
from git_utils import get_current_branch, is_protected_branch
from hook_io import read_hook_input, write_hook_output, create_pretooluse_output
from hook_logging import setup_hook_logging

# ===== 初始化 =====
logger = setup_hook_logging("branch-verify")
```

## 思考題

1. 為什麼不把 lib 目錄加入 `PYTHONPATH` 環境變數，而要在每個腳本中設定 `sys.path`？
2. `Path(__file__).resolve()` 和 `Path(__file__)` 有什麼區別？
3. 如何驗證一個路徑是否已經在 `sys.path` 中？

## 實作練習

1. 寫一個函式，列出 `sys.path` 中所有存在的目錄
2. 建立一個簡單的模組，然後在另一個檔案中使用兩種不同的方式導入它

---

*上一章：[模組與套件組織](../modules/)*
*下一模組：[型別系統](../../02-type-system/)*
