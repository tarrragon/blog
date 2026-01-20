---
title: "3.5.2 異常設計架構"
date: 2026-01-20
description: "異常層級設計、異常鏈、ExceptionGroup、異常 vs 返回值"
weight: 2
---

# 異常設計架構

入門系列介紹了異常處理的基本策略。本章深入探討如何為大型專案設計異常架構，包括異常層級、異常鏈、以及 Python 3.11 引入的 ExceptionGroup。

## 先備知識

- 入門系列 [5.1 異常處理策略](../../python/05-error-testing/exception/)

## 異常層級設計

### 為什麼需要層級設計？

當專案規模增長，你會需要：

- **區分錯誤來源**：資料庫錯誤 vs 網路錯誤 vs 驗證錯誤
- **提供不同處理策略**：有些錯誤可重試，有些需要通知用戶
- **方便呼叫者選擇處理粒度**：捕獲所有錯誤 vs 只捕獲特定錯誤

### 模組級異常基類

```python
# myapp/exceptions.py

class AppError(Exception):
    """應用程式的基礎異常類別

    所有自訂異常都應繼承此類別，讓呼叫者可以：
    - except AppError: 捕獲所有應用程式錯誤
    - except SpecificError: 只捕獲特定錯誤
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code  # 可選的錯誤碼，方便 API 回應

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message
```

### 細粒度異常分類

```python
# 第一層：按錯誤類型分類
class ValidationError(AppError):
    """驗證相關錯誤"""
    pass

class DataAccessError(AppError):
    """資料存取相關錯誤"""
    pass

class NetworkError(AppError):
    """網路相關錯誤"""
    pass

class ConfigurationError(AppError):
    """配置相關錯誤"""
    pass

# 第二層：更細的分類
class FieldValidationError(ValidationError):
    """欄位驗證錯誤"""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"Field '{field}': {message}", code="VALIDATION_FIELD")
        self.field = field

class SchemaValidationError(ValidationError):
    """資料結構驗證錯誤"""

    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message, code="VALIDATION_SCHEMA")
        self.errors = errors

class EntityNotFoundError(DataAccessError):
    """實體不存在"""

    def __init__(self, entity_type: str, entity_id: int | str) -> None:
        super().__init__(
            f"{entity_type} with id '{entity_id}' not found",
            code="NOT_FOUND"
        )
        self.entity_type = entity_type
        self.entity_id = entity_id

class DuplicateEntityError(DataAccessError):
    """實體已存在"""

    def __init__(self, entity_type: str, field: str, value: str) -> None:
        super().__init__(
            f"{entity_type} with {field}='{value}' already exists",
            code="DUPLICATE"
        )
```

### 使用範例

```python
from myapp.exceptions import (
    AppError,
    ValidationError,
    FieldValidationError,
    EntityNotFoundError
)

def create_user(data: dict) -> User:
    # 驗證
    if not data.get("email"):
        raise FieldValidationError("email", "Email is required")

    if not is_valid_email(data["email"]):
        raise FieldValidationError("email", "Invalid email format")

    # 檢查重複
    if user_exists(data["email"]):
        raise DuplicateEntityError("User", "email", data["email"])

    return User(**data)

# 呼叫者可以選擇處理粒度
def handle_user_creation(data: dict) -> dict:
    try:
        user = create_user(data)
        return {"status": "success", "user_id": user.id}

    except FieldValidationError as e:
        # 處理欄位驗證錯誤
        return {"status": "error", "field": e.field, "message": e.message}

    except ValidationError as e:
        # 處理所有驗證錯誤
        return {"status": "error", "message": str(e)}

    except AppError as e:
        # 處理所有應用程式錯誤
        return {"status": "error", "code": e.code, "message": str(e)}
```

## 異常鏈的進階用法

### `__cause__` vs `__context__`

Python 有兩種異常鏈機制：

```python
# __cause__：明確指定的原因（使用 from）
try:
    result = int("not a number")
except ValueError as e:
    raise DataAccessError("Failed to parse ID") from e
    # e 會被設為 __cause__

# __context__：隱式的上下文（在 except 中 raise）
try:
    result = int("not a number")
except ValueError:
    raise DataAccessError("Failed to parse ID")
    # 原始的 ValueError 會被設為 __context__
```

輸出差異：

```text
# 使用 from（__cause__）
DataAccessError: Failed to parse ID

The above exception was the direct cause of the following exception:
...

# 不使用 from（__context__）
DataAccessError: Failed to parse ID

During handling of the above exception, another exception occurred:
...
```

### 何時使用 from

```python
# 情況 1：轉換異常型別
def load_user(user_id: int) -> User:
    try:
        data = database.query(f"SELECT * FROM users WHERE id = {user_id}")
        return User(**data)
    except DatabaseError as e:
        # 將底層資料庫錯誤轉換為應用層錯誤
        raise EntityNotFoundError("User", user_id) from e

# 情況 2：添加上下文資訊
def process_config(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        # 添加檔案路徑資訊
        raise ConfigurationError(f"Invalid JSON in {path}") from e
```

### suppress context

有時你想切斷異常鏈：

```python
def get_value(data: dict, key: str) -> str:
    try:
        return data[key]
    except KeyError:
        # 使用 from None 切斷異常鏈
        raise ValueError(f"Required key '{key}' not found") from None
```

輸出：

```text
# 沒有 from None：會顯示原始 KeyError
# 有 from None：只顯示 ValueError，不顯示 KeyError
ValueError: Required key 'name' not found
```

使用時機：

- 原始異常不相關或會造成困惑
- 刻意隱藏實作細節
- 簡化錯誤訊息

## ExceptionGroup（Python 3.11+）

### 問題情境

當需要同時處理多個異常時，傳統方式有限制：

```python
# 傳統方式：只能記錄第一個錯誤，或全部收集後手動處理
errors = []
for task in tasks:
    try:
        task.run()
    except Exception as e:
        errors.append(e)

if errors:
    # 該拋出哪一個？或如何表示多個錯誤？
    raise errors[0]  # 丟失其他錯誤
```

### ExceptionGroup 解決方案

```python
# Python 3.11+
def run_all_tasks(tasks: list[Task]) -> None:
    errors = []
    for task in tasks:
        try:
            task.run()
        except Exception as e:
            errors.append(e)

    if errors:
        raise ExceptionGroup("Multiple tasks failed", errors)
```

### except* 語法

```python
try:
    run_all_tasks(tasks)
except* ValueError as eg:
    # eg 是包含所有 ValueError 的 ExceptionGroup
    print(f"Value errors: {eg.exceptions}")
except* TypeError as eg:
    # eg 是包含所有 TypeError 的 ExceptionGroup
    print(f"Type errors: {eg.exceptions}")
```

### 實際範例：並行任務處理

```python
import asyncio
from typing import Callable, Any

async def run_parallel(
    tasks: list[Callable[[], Any]]
) -> list[Any]:
    """並行執行多個任務，收集所有錯誤"""

    async def run_task(task: Callable[[], Any]) -> Any:
        return task()

    # 使用 TaskGroup（Python 3.11+）
    results = []
    async with asyncio.TaskGroup() as tg:
        futures = [tg.create_task(run_task(task)) for task in tasks]

    # 如果有異常，TaskGroup 會拋出 ExceptionGroup
    return [f.result() for f in futures]

# 處理
async def main():
    tasks = [task1, task2, task3]

    try:
        results = await run_parallel(tasks)
    except* ValueError as eg:
        for e in eg.exceptions:
            print(f"Validation failed: {e}")
    except* ConnectionError as eg:
        for e in eg.exceptions:
            print(f"Connection failed: {e}")
```

### 巢狀 ExceptionGroup

```python
# ExceptionGroup 可以巢狀
outer = ExceptionGroup("outer", [
    ValueError("value error"),
    ExceptionGroup("inner", [
        TypeError("type error 1"),
        TypeError("type error 2"),
    ])
])

# 使用 .subgroup() 過濾
type_errors = outer.subgroup(lambda e: isinstance(e, TypeError))
# 返回只包含 TypeError 的新 ExceptionGroup
```

## 異常 vs 返回值

### 何時使用異常

```python
# 適合使用異常的情況：

# 1. 無法繼續執行的錯誤
def connect_database(url: str) -> Connection:
    if not url:
        raise ConfigurationError("Database URL is required")
    # ...

# 2. 呼叫者通常不處理的錯誤
def validate_schema(data: dict) -> None:
    errors = find_schema_errors(data)
    if errors:
        raise SchemaValidationError("Invalid data", errors)

# 3. 深層呼叫需要跨多層傳遞錯誤
def process_order(order_id: int) -> Order:
    order = load_order(order_id)  # 可能 raise EntityNotFoundError
    validate_order(order)          # 可能 raise ValidationError
    return execute_order(order)    # 可能 raise PaymentError
```

### 何時使用 Result 模式

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")

@dataclass
class Ok(Generic[T]):
    value: T

@dataclass
class Err(Generic[E]):
    error: E

Result = Ok[T] | Err[E]

# 適合使用 Result 的情況：

# 1. 錯誤是預期的、常見的
def find_user(user_id: int) -> Result[User, str]:
    user = db.get_user(user_id)
    if user is None:
        return Err(f"User {user_id} not found")
    return Ok(user)

# 2. 需要強制呼叫者處理錯誤
def parse_config(text: str) -> Result[Config, list[str]]:
    errors = []
    # ... 解析邏輯
    if errors:
        return Err(errors)
    return Ok(config)

# 使用
match parse_config(text):
    case Ok(config):
        use_config(config)
    case Err(errors):
        show_errors(errors)

# 3. 效能敏感的熱點路徑
# 異常有效能成本，頻繁拋出會影響效能
```

### 混合使用

```python
class UserService:
    """服務層：使用異常表示錯誤"""

    def create_user(self, data: dict) -> User:
        if not data.get("email"):
            raise FieldValidationError("email", "required")
        # ...
        return user

class UserAPI:
    """API 層：將異常轉換為 Result"""

    def __init__(self, service: UserService) -> None:
        self.service = service

    def create_user(self, data: dict) -> Result[dict, dict]:
        try:
            user = self.service.create_user(data)
            return Ok({"id": user.id, "email": user.email})
        except FieldValidationError as e:
            return Err({"field": e.field, "message": e.message})
        except AppError as e:
            return Err({"code": e.code, "message": str(e)})
```

## 補充：contextlib.suppress

簡潔地忽略特定異常：

```python
from contextlib import suppress

# 傳統方式
try:
    os.remove(temp_file)
except FileNotFoundError:
    pass

# 使用 suppress
with suppress(FileNotFoundError):
    os.remove(temp_file)

# 可以同時忽略多種異常
with suppress(FileNotFoundError, PermissionError):
    os.remove(temp_file)
```

**注意**：只應該用於「真正可以安全忽略」的異常。

## 設計檢查表

設計異常架構時，考慮以下問題：

| 問題 | 建議 |
|------|------|
| 錯誤會被如何處理？ | 決定用異常還是返回值 |
| 需要區分多少種錯誤？ | 決定異常層級深度 |
| 呼叫者需要什麼資訊？ | 決定異常屬性 |
| 原始錯誤重要嗎？ | 決定是否使用 `from` |
| 會有並行錯誤嗎？ | 考慮 ExceptionGroup |

## 小結

| 概念 | 用途 |
|------|------|
| 異常層級 | 區分錯誤來源，提供不同處理粒度 |
| `raise ... from e` | 明確指定異常原因，保留追蹤資訊 |
| `raise ... from None` | 切斷異常鏈，隱藏實作細節 |
| ExceptionGroup | 同時處理多個異常 |
| `except*` | 按型別過濾 ExceptionGroup |
| Result 模式 | 強制錯誤處理，適合預期的錯誤 |

## 思考題

1. 為什麼要使用異常層級而不是一個通用的 `AppError`？
2. `from e` 和 `from None` 分別在什麼情況下使用？
3. ExceptionGroup 解決了什麼問題？在什麼場景下最有用？

---

*上一章：[3.5.1 泛型進階](../generics/)*
*下一章：[3.5.3 進階上下文管理](../context-managers/)*
