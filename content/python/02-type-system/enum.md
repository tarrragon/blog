---
title: "2.4 Enum 列舉型別"
description: "定義有限選項集合"
weight: 4
---

# Enum 列舉型別

`Enum`（列舉）用於定義一組具名的常數值。當你有一組固定的選項時，使用 Enum 比使用字串或數字更安全、更易讀。

## 為什麼使用 Enum？

### 使用字串的問題

```python
# 使用字串：容易打錯
def handle_decision(decision: str) -> None:
    if decision == "alow":  # 打錯了！應該是 "allow"
        allow_action()
    elif decision == "deny":
        deny_action()

# 沒有 IDE 自動完成
# 沒有型別檢查
```

### 使用 Enum 的好處

```python
from enum import Enum

class Decision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"

def handle_decision(decision: Decision) -> None:
    if decision == Decision.ALLOW:  # IDE 會自動完成
        allow_action()
    elif decision == Decision.DENY:
        deny_action()

# 打錯會有 AttributeError
# Decision.ALOW  # 錯誤！
```

## 基本用法

### 定義 Enum

```python
from enum import Enum

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

# 存取
print(Color.RED)        # Color.RED
print(Color.RED.name)   # 'RED'
print(Color.RED.value)  # 1
```

### 字串值的 Enum

```python
from enum import Enum

class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

# 從值建立
level = LogLevel("info")
print(level)  # LogLevel.INFO
```

## 實際範例：Hook 決策

雖然 Hook 系統目前使用字串，但可以用 Enum 改善：

```python
from enum import Enum

class HookDecision(Enum):
    """Hook 決策類型"""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"
    BLOCK = "block"

class HookEventType(Enum):
    """Hook 事件類型"""
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    STOP = "Stop"
    SESSION_START = "SessionStart"

# 使用
def create_output(decision: HookDecision) -> dict:
    return {
        "hookSpecificOutput": {
            "permissionDecision": decision.value
        }
    }
```

## 進階功能

### auto() 自動值

```python
from enum import Enum, auto

class Priority(Enum):
    LOW = auto()     # 1
    MEDIUM = auto()  # 2
    HIGH = auto()    # 3
```

### IntEnum

當需要 Enum 值可以用作整數時：

```python
from enum import IntEnum

class HttpStatus(IntEnum):
    OK = 200
    NOT_FOUND = 404
    SERVER_ERROR = 500

# 可以直接比較整數
if response.status == HttpStatus.OK:
    ...

# 可以用於數學運算
print(HttpStatus.OK + 1)  # 201
```

### StrEnum (Python 3.11+)

```python
from enum import StrEnum

class Color(StrEnum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

# 可以直接當字串使用
print(f"Color is {Color.RED}")  # "Color is red"
```

### Flag（位元旗標）

```python
from enum import Flag, auto

class Permission(Flag):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()

# 組合權限
user_perms = Permission.READ | Permission.WRITE

# 檢查權限
if Permission.READ in user_perms:
    print("Can read")
```

## 迭代和比較

### 迭代所有成員

```python
from enum import Enum

class Status(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"

# 迭代
for status in Status:
    print(f"{status.name}: {status.value}")

# 取得所有值
all_values = [s.value for s in Status]
# ['pending', 'running', 'completed']
```

### 比較

```python
from enum import Enum

class Color(Enum):
    RED = 1
    GREEN = 2

# Enum 成員是單例
Color.RED is Color.RED  # True
Color.RED == Color.RED  # True

# 不能與原始值直接比較
Color.RED == 1  # False
Color.RED.value == 1  # True
```

## 從值建立 Enum

```python
from enum import Enum

class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

# 從值建立
status = Status("active")  # Status.ACTIVE

# 從名稱建立
status = Status["ACTIVE"]  # Status.ACTIVE

# 安全地從值建立
def get_status(value: str) -> Status:
    try:
        return Status(value)
    except ValueError:
        return Status.INACTIVE
```

## 實際應用模式

### 配置選項

```python
from enum import Enum

class OutputFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    TEXT = "text"

def export_data(data: dict, format: OutputFormat) -> str:
    if format == OutputFormat.JSON:
        return json.dumps(data)
    elif format == OutputFormat.YAML:
        return yaml.dump(data)
    else:
        return str(data)
```

### 狀態機

```python
from enum import Enum, auto

class TaskState(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()

class Task:
    def __init__(self):
        self.state = TaskState.PENDING

    def start(self):
        if self.state != TaskState.PENDING:
            raise ValueError("Cannot start non-pending task")
        self.state = TaskState.RUNNING

    def complete(self):
        if self.state != TaskState.RUNNING:
            raise ValueError("Cannot complete non-running task")
        self.state = TaskState.COMPLETED
```

### 驗證等級

```python
from enum import Enum

class ValidationLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def is_blocking(self) -> bool:
        """是否會阻止操作"""
        return self == ValidationLevel.ERROR

# 使用
issue_level = ValidationLevel.WARNING
if issue_level.is_blocking():
    raise ValidationError()
```

## 最佳實踐

### 1. 使用全大寫命名成員

```python
class Status(Enum):
    ACTIVE = "active"    # 好
    active = "active"    # 不推薦
```

### 2. 為 Enum 添加方法

```python
class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    def is_urgent(self) -> bool:
        return self == Priority.HIGH

    @classmethod
    def from_string(cls, value: str) -> "Priority":
        return cls[value.upper()]
```

### 3. 搭配型別提示使用

```python
from enum import Enum

class Color(Enum):
    RED = "red"
    BLUE = "blue"

def paint(color: Color) -> None:  # 型別提示
    print(f"Painting with {color.value}")

paint(Color.RED)      # OK
paint("red")          # 型別檢查會警告
```

## 思考題

1. `Enum` 和 `IntEnum` 有什麼區別？什麼時候用哪個？
2. 為什麼 `Color.RED == 1` 會是 `False`？
3. 如何為 Enum 添加自訂方法？

## 實作練習

1. 建立一個 `HookType` Enum，包含所有 Hook 事件類型
2. 實作一個包含 `is_valid()` 方法的 `FileExtension` Enum
3. 使用 `Flag` 實作一個權限系統

---

*上一章：[Dataclass 資料結構](../dataclass/)*
*下一模組：[標準庫實戰](../../03-stdlib/)*
