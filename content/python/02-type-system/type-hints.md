---
title: "2.1 Type Hints 基礎"
description: "為函式添加型別註解，提升程式碼可讀性"
weight: 1
---

# Type Hints 基礎

Python 3.5 引入了型別提示（Type Hints），讓你可以為變數和函式添加型別註解。型別提示不會影響執行，但能大幅提升程式碼的可讀性和 IDE 的智慧提示功能。

## 為什麼需要型別提示？

### 沒有型別提示的程式碼

```python
def process(data):
    return data.strip()

result = process(input_value)  # data 是什麼型別？strip() 能用嗎？
```

### 有型別提示的程式碼

```python
def process(data: str) -> str:
    return data.strip()

result = process(input_value)  # 清楚知道需要字串，返回字串
```

## 基本語法

### 變數型別註解

```python
# 基本型別
name: str = "Python"
count: int = 42
ratio: float = 3.14
is_valid: bool = True

# 可以不賦值（用於宣告）
message: str  # 稍後賦值
```

### 函式型別註解

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    return a + b

def print_message(msg: str) -> None:
    print(msg)  # 沒有返回值用 None
```

## 實際範例：Hook 系統

來自 `.claude/lib/git_utils.py` 的範例：

```python
def run_git_command(
    args: list[str],
    cwd: Optional[str] = None,
    timeout: int = 10
) -> tuple[bool, str]:
    """
    執行 git 命令並返回結果

    Args:
        args: git 命令參數列表（不含 'git'）
        cwd: 執行目錄，預設為當前目錄
        timeout: 命令超時時間（秒）

    Returns:
        tuple[bool, str]: (是否成功, 輸出內容或錯誤訊息)
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s"
```

分析這個函式的型別提示：

| 參數 | 型別 | 說明 |
|------|------|------|
| `args` | `list[str]` | 字串列表 |
| `cwd` | `Optional[str]` | 可選字串，可以是 None |
| `timeout` | `int` | 整數，有預設值 |
| 返回值 | `tuple[bool, str]` | 布林和字串組成的元組 |

## 容器型別

### 列表（List）

```python
from typing import List  # Python 3.9 前需要

# Python 3.9+
def process_names(names: list[str]) -> list[str]:
    return [name.upper() for name in names]

# Python 3.8 及之前
def process_names(names: List[str]) -> List[str]:
    return [name.upper() for name in names]
```

### 字典（Dict）

```python
from typing import Dict

# Python 3.9+
def get_config() -> dict[str, int]:
    return {"timeout": 10, "retries": 3}

# Python 3.8 及之前
def get_config() -> Dict[str, int]:
    return {"timeout": 10, "retries": 3}
```

### 集合（Set）

```python
# Python 3.9+
def get_unique_items(items: list[str]) -> set[str]:
    return set(items)
```

### 元組（Tuple）

```python
# 固定長度和型別
def get_position() -> tuple[int, int]:
    return (10, 20)

# 可變長度（同質）
def get_values() -> tuple[int, ...]:
    return (1, 2, 3, 4, 5)
```

## 實際應用：Hook 輸出建立

來自 `.claude/lib/hook_io.py`：

```python
def create_pretooluse_output(
    decision: str,
    reason: str,
    user_prompt: Optional[str] = None,
    system_message: Optional[str] = None,
    suppress_output: bool = False
) -> dict:
    """
    建立 PreToolUse Hook 輸出格式

    Args:
        decision: 決策結果 ("allow" | "deny" | "ask")
        reason: 決策原因說明
        user_prompt: 詢問用戶的訊息
        system_message: 系統訊息
        suppress_output: 是否抑制輸出
    """
    output: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason
        }
    }

    if user_prompt:
        output["hookSpecificOutput"]["userPrompt"] = user_prompt

    if system_message:
        output["systemMessage"] = system_message

    if suppress_output:
        output["suppressOutput"] = True

    return output
```

## 型別別名

為複雜型別建立別名提升可讀性：

```python
from typing import Dict, List, Tuple

# 定義型別別名
ValidationResult = Tuple[bool, str]
ConfigDict = Dict[str, Any]
NameList = List[str]

# 使用別名
def validate_input(data: str) -> ValidationResult:
    if data:
        return True, "Valid"
    return False, "Empty input"

def load_config() -> ConfigDict:
    return {"key": "value"}
```

## 型別檢查工具

型別提示本身不會在執行時檢查，但可以用工具進行靜態檢查：

### mypy

```bash
# 安裝
pip install mypy

# 檢查檔案
mypy my_script.py

# 檢查目錄
mypy .claude/lib/
```

### IDE 整合

現代 IDE（VS Code、PyCharm）會自動利用型別提示：
- 自動完成更準確
- 型別錯誤即時提示
- 重構更安全

## 最佳實踐

### 1. 為公開 API 添加型別提示

```python
# 公開函式必須有型別提示
def get_current_branch() -> Optional[str]:
    """獲取當前分支名稱"""
    ...

# 內部輔助函式可以省略
def _parse_output(text):
    ...
```

### 2. 使用有意義的型別別名

```python
# 好：清楚表達意圖
BranchName = str
ValidationResult = Tuple[bool, str]

def validate_branch(name: BranchName) -> ValidationResult:
    ...

# 不好：型別別名沒有增加資訊
MyStr = str  # 這有什麼意義？
```

### 3. 逐步添加型別提示

不需要一次為所有程式碼添加型別提示，可以從以下開始：
- 公開 API
- 複雜函式
- 經常被呼叫的函式

## 思考題

1. `list[str]` 和 `List[str]` 有什麼區別？什麼時候用哪個？
2. 為什麼 `run_git_command` 返回 `tuple[bool, str]` 而不是自定義類別？
3. 型別提示會影響程式執行速度嗎？

## 實作練習

為以下函式添加適當的型別提示：

```python
def parse_config(file_path):
    with open(file_path) as f:
        return json.load(f)

def filter_valid_items(items):
    return [item for item in items if item.get("valid")]

def merge_dicts(dict1, dict2):
    result = dict1.copy()
    result.update(dict2)
    return result
```

---

*下一章：[Optional、Union、泛型](../optional-union/)*
