---
title: "1.2 模組與套件組織"
date: 2026-01-20
description: "理解 Python 的模組系統和套件結構"
weight: 2
---

# 模組與套件組織

Python 的模組系統是組織程式碼的基礎。理解模組如何運作，是維護和擴展 Hook 系統的關鍵。

## 基本概念

### 模組（Module）

一個 `.py` 檔案就是一個模組。例如 `git_utils.py` 就是 `git_utils` 模組。

```python
# git_utils.py 是一個模組
# 可以被其他檔案導入

from git_utils import get_current_branch
```

### 套件（Package）

包含 `__init__.py` 的目錄就是一個套件。套件可以包含多個模組。

```
.claude/lib/
├── __init__.py      # 使 lib 成為套件
├── git_utils.py     # 模組
├── hook_io.py       # 模組
├── hook_logging.py  # 模組
└── config_loader.py # 模組
```

## `__init__.py` 的作用

`__init__.py` 是套件的初始化檔案，它在套件被導入時執行。

### 實際範例：Hook 系統的 `__init__.py`

來自 `.claude/lib/__init__.py`：

```python
"""
Claude Hooks 共用程式庫

提供 Hook 腳本共用的工具函式，消除程式碼重複。

模組結構:
- git_utils: Git 操作工具（分支、worktree、專案根目錄）
- hook_logging: Hook 日誌系統
- hook_io: Hook 輸入輸出處理
"""

# 從子模組導入並重新匯出
from .git_utils import (
    run_git_command,
    get_current_branch,
    get_project_root,
    get_worktree_list,
    is_protected_branch,
    is_allowed_branch,
)

from .hook_logging import setup_hook_logging

from .hook_io import (
    read_hook_input,
    write_hook_output,
    create_pretooluse_output,
    create_posttooluse_output,
)

from .config_loader import (
    load_config,
    load_agents_config,
    load_quality_rules,
    clear_config_cache,
)

# 定義公開 API
__all__ = [
    # git_utils
    "run_git_command",
    "get_current_branch",
    # ... 省略其他
]

__version__ = "0.28.0"
```

### `__init__.py` 的三個主要功能

#### 1. 宣告套件身份

空的 `__init__.py` 也能讓目錄成為套件：

```python
# lib/__init__.py（最簡形式）
# 即使是空檔案，也使 lib 成為套件
```

#### 2. 定義公開 API

透過 `__all__` 列表控制 `from package import *` 的行為：

```python
__all__ = [
    "run_git_command",
    "get_current_branch",
    "setup_hook_logging",
]

# 當使用者執行 from lib import * 時
# 只會導入 __all__ 中列出的名稱
```

#### 3. 簡化導入路徑

使用者可以直接從套件導入，而不需要知道子模組：

```python
# 有 __init__.py 的重新匯出：簡潔
from lib import get_current_branch, setup_hook_logging

# 沒有 __init__.py 的重新匯出：冗長
from lib.git_utils import get_current_branch
from lib.hook_logging import setup_hook_logging
```

## 相對導入與絕對導入

### 相對導入（使用 `.`）

在套件內部使用相對導入：

```python
# 在 lib/config_loader.py 中
from .git_utils import get_project_root  # 同級模組
from . import hook_io                     # 導入整個模組
```

### 絕對導入

從套件外部或在腳本中使用絕對導入：

```python
# 在 .claude/hooks/some_hook.py 中
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from git_utils import get_current_branch  # 絕對導入
from hook_io import read_hook_input
```

## 套件版本管理

在 `__init__.py` 中定義版本號是常見做法：

```python
__version__ = "0.28.0"
```

這樣使用者可以查詢版本：

```python
import lib
print(lib.__version__)  # "0.28.0"
```

## 模組載入順序

Python 搜尋模組的順序：

1. 內建模組
2. `sys.path[0]`（腳本所在目錄）
3. `PYTHONPATH` 環境變數
4. 標準庫
5. site-packages（第三方套件）

### 實際範例：Hook 腳本的路徑設定

```python
#!/usr/bin/env python3
"""Branch Verify Hook"""

import sys
from pathlib import Path

# 將 lib 目錄加入搜尋路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

# 現在可以導入 lib 中的模組
from git_utils import get_current_branch
from hook_io import read_hook_input, write_hook_output
```

## 最佳實踐

### 1. 避免循環導入

```python
# 不好：a.py 和 b.py 互相導入
# a.py
from b import func_b
# b.py
from a import func_a  # 循環導入！

# 好：重構為第三個模組
# common.py
def shared_function(): ...
# a.py
from common import shared_function
# b.py
from common import shared_function
```

### 2. 延遲導入

對於可選依賴或避免循環導入：

```python
def load_yaml_config():
    # 只在需要時才導入
    try:
        import yaml
        return yaml.safe_load(...)
    except ImportError:
        # 備案方案
        import json
        return json.load(...)
```

### 3. 清晰的模組邊界

每個模組應該有單一、明確的職責：

```
lib/
├── git_utils.py      # Git 操作（單一職責）
├── hook_io.py        # 輸入輸出處理（單一職責）
├── hook_logging.py   # 日誌系統（單一職責）
└── config_loader.py  # 配置載入（單一職責）
```

## 思考題

1. 為什麼 `__init__.py` 使用 `from .git_utils import ...` 而不是 `from git_utils import ...`？
2. Hook 腳本中的 `sys.path.insert(0, ...)` 為什麼使用 `0` 作為索引？
3. `__all__` 列表的作用是什麼？如果不定義會怎樣？

## 實作練習

閱讀 `.claude/lib/__init__.py`，回答以下問題：

1. 這個套件匯出了多少個公開函式？
2. 套件的版本號是多少？
3. 如果要新增一個 `utils.py` 模組並匯出 `format_message` 函式，需要修改哪些地方？

---

*上一章：[Python 哲學與設計理念](../philosophy/)*
*下一章：[導入機制與路徑管理](../imports/)*
