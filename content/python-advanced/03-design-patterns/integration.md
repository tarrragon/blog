---
title: "3.5.5 設計模式整合案例"
description: "結合泛型、異常、上下文、插件建立完整系統"
weight: 5
---

# 設計模式整合案例

本章透過兩個完整案例，展示如何將前四章的設計模式結合應用。每個案例都會說明各模式的協作關係。

## 先備知識

- 本模組 3.5.1-3.5.4 所有章節

## 案例一：迷你 ORM 框架

建立一個簡化的 ORM（Object-Relational Mapping）框架，展示各模式的整合。

### 設計概覽

```text
┌─────────────────────────────────────────────────────────┐
│                     MiniORM Framework                    │
├─────────────────────────────────────────────────────────┤
│  泛型        │ Repository[T] - 型別安全的資料存取       │
│  異常        │ 階層式異常 - 精確的錯誤處理              │
│  上下文      │ Transaction - 交易管理                   │
│  插件        │ FieldType - 可擴展的欄位型別             │
└─────────────────────────────────────────────────────────┘
```

### 異常層級設計

```python
# miniorm/exceptions.py

class ORMError(Exception):
    """ORM 框架的基礎異常"""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

class ConnectionError(ORMError):
    """資料庫連接錯誤"""
    pass

class QueryError(ORMError):
    """查詢執行錯誤"""
    pass

class EntityNotFoundError(ORMError):
    """實體不存在"""

    def __init__(self, model: str, pk: int | str) -> None:
        super().__init__(f"{model} with pk={pk} not found", code="NOT_FOUND")
        self.model = model
        self.pk = pk

class ValidationError(ORMError):
    """資料驗證錯誤"""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"Validation failed for '{field}': {message}", code="VALIDATION")
        self.field = field

class TransactionError(ORMError):
    """交易錯誤"""
    pass
```

### 插件系統：可擴展的欄位型別

```python
# miniorm/fields.py

from abc import ABC, abstractmethod
from typing import Any, ClassVar
from datetime import datetime

class FieldType(ABC):
    """欄位型別插件基類"""
    _registry: ClassVar[dict[str, type["FieldType"]]] = {}

    # 子類別必須定義
    type_name: ClassVar[str]
    python_type: ClassVar[type]

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "type_name"):
            FieldType._registry[cls.type_name] = cls

    @abstractmethod
    def to_db(self, value: Any) -> Any:
        """Python 值轉換為資料庫值"""
        ...

    @abstractmethod
    def from_db(self, value: Any) -> Any:
        """資料庫值轉換為 Python 值"""
        ...

    @abstractmethod
    def validate(self, value: Any) -> None:
        """驗證值，失敗時拋出 ValidationError"""
        ...

    @classmethod
    def get_type(cls, name: str) -> type["FieldType"] | None:
        return cls._registry.get(name)

# 內建欄位型別
class IntegerField(FieldType):
    type_name = "integer"
    python_type = int

    def to_db(self, value: Any) -> int:
        return int(value)

    def from_db(self, value: Any) -> int:
        return int(value) if value is not None else 0

    def validate(self, value: Any) -> None:
        if value is not None and not isinstance(value, int):
            raise ValidationError("value", f"Expected int, got {type(value).__name__}")

class StringField(FieldType):
    type_name = "string"
    python_type = str

    def __init__(self, max_length: int = 255) -> None:
        self.max_length = max_length

    def to_db(self, value: Any) -> str:
        return str(value)

    def from_db(self, value: Any) -> str:
        return str(value) if value is not None else ""

    def validate(self, value: Any) -> None:
        if value is not None:
            if not isinstance(value, str):
                raise ValidationError("value", f"Expected str, got {type(value).__name__}")
            if len(value) > self.max_length:
                raise ValidationError("value", f"Max length is {self.max_length}")

class DateTimeField(FieldType):
    type_name = "datetime"
    python_type = datetime

    def to_db(self, value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def from_db(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def validate(self, value: Any) -> None:
        if value is not None and not isinstance(value, datetime):
            raise ValidationError("value", f"Expected datetime, got {type(value).__name__}")

# 使用者可以擴展新的欄位型別
class JSONField(FieldType):
    """自訂欄位型別範例"""
    type_name = "json"
    python_type = dict

    def to_db(self, value: Any) -> str:
        import json
        return json.dumps(value)

    def from_db(self, value: Any) -> dict:
        import json
        if isinstance(value, dict):
            return value
        return json.loads(str(value))

    def validate(self, value: Any) -> None:
        if value is not None and not isinstance(value, (dict, list)):
            raise ValidationError("value", "Expected dict or list")
```

### 泛型 Repository

```python
# miniorm/repository.py

from typing import TypeVar, Generic, Protocol, ClassVar
from abc import abstractmethod

class HasId(Protocol):
    """具有 id 屬性的協議"""
    id: int

T = TypeVar("T", bound=HasId)

class Repository(Generic[T]):
    """泛型 Repository 基類"""

    model_class: ClassVar[type]

    def __init__(self, connection: "Connection") -> None:
        self._connection = connection

    @abstractmethod
    def get(self, pk: int) -> T | None:
        """根據主鍵取得實體"""
        ...

    @abstractmethod
    def save(self, entity: T) -> T:
        """儲存實體"""
        ...

    @abstractmethod
    def delete(self, pk: int) -> bool:
        """刪除實體"""
        ...

    @abstractmethod
    def find_all(self) -> list[T]:
        """取得所有實體"""
        ...

    def get_or_raise(self, pk: int) -> T:
        """取得實體，不存在時拋出異常"""
        entity = self.get(pk)
        if entity is None:
            raise EntityNotFoundError(self.model_class.__name__, pk)
        return entity

class InMemoryRepository(Repository[T]):
    """記憶體實作的 Repository"""

    def __init__(self, connection: "Connection") -> None:
        super().__init__(connection)
        self._storage: dict[int, T] = {}
        self._next_id = 1

    def get(self, pk: int) -> T | None:
        return self._storage.get(pk)

    def save(self, entity: T) -> T:
        # 驗證欄位
        self._validate_entity(entity)

        if entity.id == 0:
            entity.id = self._next_id
            self._next_id += 1
        self._storage[entity.id] = entity
        return entity

    def delete(self, pk: int) -> bool:
        if pk in self._storage:
            del self._storage[pk]
            return True
        return False

    def find_all(self) -> list[T]:
        return list(self._storage.values())

    def _validate_entity(self, entity: T) -> None:
        """驗證實體的所有欄位"""
        # 這裡可以整合 FieldType 的驗證邏輯
        pass
```

### 上下文管理：交易

```python
# miniorm/transaction.py

from contextlib import contextmanager
from typing import Iterator
from dataclasses import dataclass
from enum import Enum, auto

class TransactionState(Enum):
    ACTIVE = auto()
    COMMITTED = auto()
    ROLLED_BACK = auto()

@dataclass
class Transaction:
    """交易物件"""
    id: int
    state: TransactionState = TransactionState.ACTIVE
    _operations: list = None

    def __post_init__(self):
        self._operations = []

    def add_operation(self, op: dict) -> None:
        if self.state != TransactionState.ACTIVE:
            raise TransactionError("Transaction is not active")
        self._operations.append(op)

    def commit(self) -> None:
        if self.state != TransactionState.ACTIVE:
            raise TransactionError("Transaction is not active")
        # 實際應用中這裡會提交到資料庫
        self.state = TransactionState.COMMITTED

    def rollback(self) -> None:
        if self.state == TransactionState.COMMITTED:
            raise TransactionError("Cannot rollback committed transaction")
        # 實際應用中這裡會回滾操作
        self._operations.clear()
        self.state = TransactionState.ROLLED_BACK

class Connection:
    """資料庫連接"""

    def __init__(self, url: str) -> None:
        self.url = url
        self._tx_counter = 0
        self._current_tx: Transaction | None = None

    @contextmanager
    def transaction(self) -> Iterator[Transaction]:
        """交易上下文管理器"""
        if self._current_tx is not None:
            raise TransactionError("Nested transactions not supported")

        self._tx_counter += 1
        tx = Transaction(id=self._tx_counter)
        self._current_tx = tx

        try:
            yield tx
            if tx.state == TransactionState.ACTIVE:
                tx.commit()
        except Exception:
            if tx.state == TransactionState.ACTIVE:
                tx.rollback()
            raise
        finally:
            self._current_tx = None

    @property
    def in_transaction(self) -> bool:
        return self._current_tx is not None
```

### 整合使用範例

```python
# 定義 Model
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class User:
    id: int = 0
    name: str = ""
    email: str = ""
    created_at: datetime = field(default_factory=datetime.now)

# 定義具體的 Repository
class UserRepository(InMemoryRepository[User]):
    model_class = User

# 使用
def main():
    # 建立連接
    conn = Connection("memory://")

    # 建立 Repository
    users = UserRepository(conn)

    # 使用交易
    with conn.transaction() as tx:
        # 建立使用者
        user = User(name="Alice", email="alice@example.com")
        users.save(user)

        # 更多操作...
        user.name = "Alice Smith"
        users.save(user)

    # 交易外的操作
    try:
        found = users.get_or_raise(999)
    except EntityNotFoundError as e:
        print(f"Error: {e.message}")

    # 列出所有使用者
    for user in users.find_all():
        print(f"User: {user.name} ({user.email})")
```

## 案例二：任務排程器

建立一個支援並行執行的任務排程器。

### 設計概覽

```text
┌─────────────────────────────────────────────────────────┐
│                    Task Scheduler                        │
├─────────────────────────────────────────────────────────┤
│  泛型        │ Task[T] - 型別安全的任務定義             │
│  異常        │ ExceptionGroup - 並行錯誤處理            │
│  上下文      │ TaskContext - 資源生命週期               │
│  插件        │ TaskHandler - 可擴展的處理器             │
└─────────────────────────────────────────────────────────┘
```

### 異常設計

```python
# scheduler/exceptions.py

class SchedulerError(Exception):
    """排程器基礎異常"""
    pass

class TaskError(SchedulerError):
    """任務執行錯誤"""

    def __init__(self, task_id: str, message: str, cause: Exception | None = None) -> None:
        super().__init__(f"Task '{task_id}' failed: {message}")
        self.task_id = task_id
        if cause:
            self.__cause__ = cause

class TimeoutError(TaskError):
    """任務超時"""
    pass

class DependencyError(TaskError):
    """依賴任務失敗"""

    def __init__(self, task_id: str, failed_deps: list[str]) -> None:
        super().__init__(task_id, f"Dependencies failed: {failed_deps}")
        self.failed_deps = failed_deps
```

### 泛型任務定義

```python
# scheduler/task.py

from typing import TypeVar, Generic, Callable, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime

T = TypeVar("T")

class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

@dataclass
class TaskResult(Generic[T]):
    """任務執行結果"""
    value: T | None = None
    error: Exception | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def duration(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

@dataclass
class Task(Generic[T]):
    """泛型任務"""
    id: str
    handler: Callable[["TaskContext"], T]
    dependencies: list[str] = field(default_factory=list)
    timeout: float | None = None
    status: TaskStatus = TaskStatus.PENDING
    result: TaskResult[T] | None = None

    def execute(self, ctx: "TaskContext") -> TaskResult[T]:
        """執行任務"""
        result = TaskResult[T](started_at=datetime.now())
        self.status = TaskStatus.RUNNING

        try:
            value = self.handler(ctx)
            result.value = value
            self.status = TaskStatus.COMPLETED
        except Exception as e:
            result.error = e
            self.status = TaskStatus.FAILED
        finally:
            result.completed_at = datetime.now()

        self.result = result
        return result
```

### 插件系統：任務處理器

```python
# scheduler/handlers.py

from typing import Any, ClassVar, Protocol
from abc import abstractmethod

class TaskHandlerProtocol(Protocol):
    """任務處理器協議"""

    def can_handle(self, task_type: str) -> bool:
        ...

    def handle(self, ctx: "TaskContext", payload: dict) -> Any:
        ...

class TaskHandler:
    """任務處理器基類（基於註冊）"""
    _registry: ClassVar[dict[str, "TaskHandler"]] = {}

    task_type: ClassVar[str]

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "task_type"):
            TaskHandler._registry[cls.task_type] = cls()

    @abstractmethod
    def handle(self, ctx: "TaskContext", payload: dict) -> Any:
        """處理任務"""
        ...

    @classmethod
    def get_handler(cls, task_type: str) -> "TaskHandler | None":
        return cls._registry.get(task_type)

# 具體的處理器
class HttpRequestHandler(TaskHandler):
    """HTTP 請求處理器"""
    task_type = "http_request"

    def handle(self, ctx: "TaskContext", payload: dict) -> dict:
        import urllib.request
        url = payload["url"]
        method = payload.get("method", "GET")

        # 簡化的實作
        with urllib.request.urlopen(url) as response:
            return {
                "status": response.status,
                "body": response.read().decode()
            }

class ShellCommandHandler(TaskHandler):
    """Shell 命令處理器"""
    task_type = "shell"

    def handle(self, ctx: "TaskContext", payload: dict) -> dict:
        import subprocess
        command = payload["command"]
        timeout = payload.get("timeout", 30)

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

class DataProcessHandler(TaskHandler):
    """資料處理器"""
    task_type = "data_process"

    def handle(self, ctx: "TaskContext", payload: dict) -> Any:
        # 從上下文取得共享資源
        data = ctx.get_resource("data")
        operation = payload.get("operation", "identity")

        if operation == "transform":
            return [item * 2 for item in data]
        elif operation == "filter":
            return [item for item in data if item > 0]
        else:
            return data
```

### 上下文管理：任務上下文

```python
# scheduler/context.py

from contextlib import contextmanager, ExitStack
from typing import Any, Iterator
from dataclasses import dataclass, field

@dataclass
class TaskContext:
    """任務執行上下文"""
    task_id: str
    _resources: dict[str, Any] = field(default_factory=dict)
    _cleanup_callbacks: list = field(default_factory=list)

    def set_resource(self, name: str, value: Any) -> None:
        """設定共享資源"""
        self._resources[name] = value

    def get_resource(self, name: str) -> Any | None:
        """取得共享資源"""
        return self._resources.get(name)

    def add_cleanup(self, callback) -> None:
        """註冊清理回調"""
        self._cleanup_callbacks.append(callback)

    def cleanup(self) -> None:
        """執行所有清理回調"""
        errors = []
        for callback in reversed(self._cleanup_callbacks):
            try:
                callback()
            except Exception as e:
                errors.append(e)

        if errors:
            raise ExceptionGroup("Cleanup failed", errors)

@contextmanager
def task_context(task_id: str) -> Iterator[TaskContext]:
    """任務上下文管理器"""
    ctx = TaskContext(task_id=task_id)

    try:
        yield ctx
    finally:
        ctx.cleanup()
```

### 排程器：整合所有模式

```python
# scheduler/scheduler.py

import asyncio
from typing import Any
from dataclasses import dataclass, field

@dataclass
class Scheduler:
    """任務排程器"""
    _tasks: dict[str, Task] = field(default_factory=dict)
    _results: dict[str, TaskResult] = field(default_factory=dict)

    def add_task(self, task: Task) -> None:
        """新增任務"""
        self._tasks[task.id] = task

    def _get_execution_order(self) -> list[list[str]]:
        """計算執行順序（拓撲排序）"""
        # 簡化實作：按依賴深度分層
        layers: list[list[str]] = []
        remaining = set(self._tasks.keys())
        completed: set[str] = set()

        while remaining:
            # 找出所有依賴已完成的任務
            ready = [
                tid for tid in remaining
                if all(dep in completed for dep in self._tasks[tid].dependencies)
            ]

            if not ready:
                # 有循環依賴
                raise SchedulerError(f"Circular dependency detected: {remaining}")

            layers.append(ready)
            for tid in ready:
                remaining.remove(tid)
                completed.add(tid)

        return layers

    async def run_async(self) -> dict[str, TaskResult]:
        """非同步執行所有任務"""
        layers = self._get_execution_order()

        for layer in layers:
            # 同一層的任務可以並行執行
            tasks_to_run = []

            for task_id in layer:
                task = self._tasks[task_id]

                # 檢查依賴是否成功
                failed_deps = [
                    dep for dep in task.dependencies
                    if dep in self._results and not self._results[dep].success
                ]

                if failed_deps:
                    # 依賴失敗，跳過此任務
                    result = TaskResult(
                        error=DependencyError(task_id, failed_deps)
                    )
                    self._results[task_id] = result
                    continue

                tasks_to_run.append(self._run_task_async(task))

            # 並行執行，收集所有錯誤
            if tasks_to_run:
                try:
                    async with asyncio.TaskGroup() as tg:
                        for coro in tasks_to_run:
                            tg.create_task(coro)
                except* TaskError as eg:
                    # 記錄錯誤但繼續執行
                    for e in eg.exceptions:
                        print(f"Task failed: {e}")

        return self._results

    async def _run_task_async(self, task: Task) -> None:
        """執行單個任務"""
        with task_context(task.id) as ctx:
            # 設定共享資源（從依賴任務的結果）
            for dep_id in task.dependencies:
                if dep_id in self._results:
                    ctx.set_resource(f"result_{dep_id}", self._results[dep_id].value)

            result = task.execute(ctx)
            self._results[task.id] = result

            if result.error:
                raise TaskError(task.id, str(result.error), result.error)

    def run(self) -> dict[str, TaskResult]:
        """同步執行"""
        return asyncio.run(self.run_async())
```

### 完整使用範例

```python
# 建立排程器
scheduler = Scheduler()

# 定義任務
def fetch_data(ctx: TaskContext) -> list[int]:
    """模擬取得資料"""
    return [1, 2, 3, 4, 5]

def process_data(ctx: TaskContext) -> list[int]:
    """處理資料"""
    data = ctx.get_resource("result_fetch")
    return [x * 2 for x in data]

def save_result(ctx: TaskContext) -> str:
    """儲存結果"""
    data = ctx.get_resource("result_process")
    return f"Saved {len(data)} items"

# 新增任務（有依賴關係）
scheduler.add_task(Task(
    id="fetch",
    handler=fetch_data
))

scheduler.add_task(Task(
    id="process",
    handler=process_data,
    dependencies=["fetch"]
))

scheduler.add_task(Task(
    id="save",
    handler=save_result,
    dependencies=["process"]
))

# 執行
results = scheduler.run()

# 檢查結果
for task_id, result in results.items():
    if result.success:
        print(f"✓ {task_id}: {result.value} ({result.duration:.3f}s)")
    else:
        print(f"✗ {task_id}: {result.error}")
```

## 模式協作關係圖

```text
┌─────────────────────────────────────────────────────────────────┐
│                         應用程式                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│   │   泛型      │────▶│   異常      │────▶│   上下文    │       │
│   │ Repository  │     │ 層級設計    │     │ Transaction │       │
│   │ Task[T]     │     │ 異常鏈      │     │ TaskContext │       │
│   └─────────────┘     └─────────────┘     └─────────────┘       │
│          │                   │                   │               │
│          │                   │                   │               │
│          ▼                   ▼                   ▼               │
│   ┌─────────────────────────────────────────────────────┐       │
│   │                      插件系統                        │       │
│   │  FieldType  │  TaskHandler  │  HookPlugin          │       │
│   └─────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

協作方式：
1. 泛型確保型別安全，在編譯期捕獲錯誤
2. 異常提供精確的錯誤處理，支援錯誤傳播和轉換
3. 上下文管理資源生命週期，確保正確清理
4. 插件系統提供擴展點，允許自訂行為
```

## 設計原則總結

| 模式 | 解決的問題 | 使用時機 |
|------|-----------|---------|
| 泛型 | 型別安全的重用 | 容器、Repository、服務介面 |
| 異常層級 | 精確的錯誤處理 | 大型專案、API 設計 |
| 上下文管理 | 資源生命週期 | 連接、交易、臨時資源 |
| 插件系統 | 可擴展性 | 框架設計、開放式架構 |

## 思考題

1. 如何在這些案例中加入日誌記錄？
2. 如果要支援分散式執行，需要修改哪些部分？
3. 如何為這些框架加入效能監控？

---

*上一章：[3.5.4 插件系統設計](../plugin-system/)*
*回到模組目錄：[模組 3.5：進階設計模式](../)*
