---
title: "2.2 Optional、Union、泛型"
description: "處理可能為 None 的值和複合型別"
weight: 2
---

# Optional、Union、泛型

當函式的參數或返回值可能是多種型別時，我們需要使用 `Optional`、`Union` 或泛型來表達。這些工具讓型別提示更加精確。

## Optional

`Optional[T]` 表示值可能是 `T` 型別，也可能是 `None`。

### 基本用法

```python
from typing import Optional

def get_current_branch() -> Optional[str]:
    """
    獲取當前分支名稱

    Returns:
        str | None: 分支名稱，如果無法獲取則返回 None
    """
    success, output = run_git_command(["branch", "--show-current"])
    return output if success and output else None
```

### Optional 等同於 Union[T, None]

```python
from typing import Optional, Union

# 這兩種寫法等價
def find_user(id: int) -> Optional[User]:
    ...

def find_user(id: int) -> Union[User, None]:
    ...

# Python 3.10+ 可以使用 | 語法
def find_user(id: int) -> User | None:
    ...
```

## 實際範例：配置載入

來自 `.claude/lib/config_loader.py`：

```python
from typing import Optional

# 模組級快取變數
_agents_config_cache: Optional[dict] = None
_quality_rules_cache: Optional[dict] = None


def load_agents_config() -> dict:
    """載入代理人配置"""
    global _agents_config_cache

    # 快取為 None 表示尚未載入
    if _agents_config_cache is None:
        try:
            _agents_config_cache = load_config("agents")
        except FileNotFoundError:
            _agents_config_cache = _get_default_agents_config()

    return _agents_config_cache
```

## Union

`Union[A, B, C]` 表示值可能是 A、B 或 C 型別。

### 基本用法

```python
from typing import Union

def process_input(data: Union[str, bytes]) -> str:
    """處理字串或位元組輸入"""
    if isinstance(data, bytes):
        return data.decode("utf-8")
    return data

# Python 3.10+ 語法
def process_input(data: str | bytes) -> str:
    ...
```

### 常見應用

```python
from typing import Union, List

# 接受單一值或列表
def ensure_list(value: Union[str, List[str]]) -> List[str]:
    if isinstance(value, str):
        return [value]
    return value

# 返回不同型別
def parse_value(text: str) -> Union[int, float, str]:
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text
```

## 泛型（Generic）

泛型讓你建立可以與多種型別一起使用的類別和函式。

### TypeVar

```python
from typing import TypeVar, List

T = TypeVar("T")

def first_element(items: List[T]) -> T:
    """返回列表的第一個元素"""
    return items[0]

# 使用時會推斷型別
names = ["Alice", "Bob"]
first_name = first_element(names)  # 推斷為 str

numbers = [1, 2, 3]
first_num = first_element(numbers)  # 推斷為 int
```

### 有限制的 TypeVar

```python
from typing import TypeVar

# 只能是 str 或 bytes
StrOrBytes = TypeVar("StrOrBytes", str, bytes)

def process(data: StrOrBytes) -> StrOrBytes:
    return data.strip()  # str 和 bytes 都有 strip()
```

## 實際範例：Hook 輸出建立

來自 `.claude/lib/hook_io.py`：

```python
from typing import Any, Optional

def create_pretooluse_output(
    decision: str,
    reason: str,
    user_prompt: Optional[str] = None,
    system_message: Optional[str] = None,
    suppress_output: bool = False
) -> dict:
    """建立 PreToolUse Hook 輸出格式"""

    # 使用 dict[str, Any] 表示值可以是任意型別
    output: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason
        }
    }

    # Optional 參數的處理
    if user_prompt:
        output["hookSpecificOutput"]["userPrompt"] = user_prompt

    if system_message:
        output["systemMessage"] = system_message

    if suppress_output:
        output["suppressOutput"] = True

    return output
```

## Any

`Any` 表示任意型別，相當於關閉型別檢查。

```python
from typing import Any

def log_value(value: Any) -> None:
    """記錄任意型別的值"""
    print(f"Value: {value}")

# 字典值為任意型別
config: dict[str, Any] = {
    "name": "test",      # str
    "count": 10,         # int
    "enabled": True,     # bool
    "items": [1, 2, 3]   # list
}
```

### 何時使用 Any？

- 處理動態資料（如 JSON）
- 與外部 API 互動
- 型別過於複雜難以表達

**注意**：過度使用 `Any` 會降低型別檢查的效果。

## Callable

表示可呼叫物件（函式、方法、lambda）。

```python
from typing import Callable

def apply_operation(
    value: int,
    operation: Callable[[int], int]
) -> int:
    """對值應用操作"""
    return operation(value)

# 使用
result = apply_operation(5, lambda x: x * 2)  # 10
```

## Python 3.9+ 語法

從 Python 3.9 開始，可以直接使用內建型別：

```python
# Python 3.9+
def process(items: list[str]) -> dict[str, int]:
    ...

# Python 3.8 及之前需要導入
from typing import List, Dict
def process(items: List[str]) -> Dict[str, int]:
    ...
```

從 Python 3.10 開始，可以使用 `|` 語法：

```python
# Python 3.10+
def find(id: int) -> User | None:
    ...

# Python 3.9 及之前
from typing import Optional
def find(id: int) -> Optional[User]:
    ...
```

## 常見模式

### 可選參數

```python
def setup_logging(
    name: str,
    level: Optional[int] = None,    # 可以是 int 或 None
    path: Optional[str] = None      # 可以是 str 或 None
) -> Logger:
    if level is None:
        level = logging.INFO
    ...
```

### 返回值可能為空

```python
def find_config(name: str) -> Optional[dict]:
    """找不到配置時返回 None"""
    path = get_config_path(name)
    if not path.exists():
        return None
    return load_config(path)
```

### 字典值型別不確定

```python
from typing import Any

def parse_json(text: str) -> dict[str, Any]:
    """JSON 值可能是任意型別"""
    return json.loads(text)
```

## 思考題

1. `Optional[str]` 和 `str | None` 有什麼區別？
2. 什麼時候應該用 `Any`？什麼時候應該避免？
3. 如何為一個接受任意可迭代物件的函式添加型別提示？

## 實作練習

1. 為以下函式添加型別提示：
   ```python
   def get_value(data, key, default=None):
       return data.get(key, default)
   ```

2. 寫一個泛型函式，返回列表中的最大和最小值
3. 為一個回調函式參數添加 `Callable` 型別提示

---

*上一章：[Type Hints 基礎](../type-hints/)*
*下一章：[Dataclass 資料結構](../dataclass/)*
