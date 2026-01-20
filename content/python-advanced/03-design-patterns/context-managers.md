---
title: "3.5.3 進階上下文管理"
date: 2026-01-20
description: "上下文管理器協議、contextlib 工具、嵌套與組合、async with"
weight: 3
---

# 進階上下文管理

入門系列介紹了 `with` 語句的基本使用。本章深入探討上下文管理器的實現原理與進階應用，包括 `contextlib` 工具、嵌套組合、以及非同步上下文管理。

## 先備知識

- 入門系列的 `with` 語句使用
- 基本的類別定義與魔術方法

## 上下文管理器協議

### `__enter__` 與 `__exit__`

```python
class ManagedResource:
    """展示上下文管理器協議"""

    def __init__(self, name: str) -> None:
        self.name = name
        print(f"Creating {name}")

    def __enter__(self) -> "ManagedResource":
        """進入 with 區塊時呼叫

        Returns:
            as 子句綁定的物件
        """
        print(f"Entering {self.name}")
        return self  # 這會被 as 子句捕獲

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> bool:
        """離開 with 區塊時呼叫

        Args:
            exc_type: 異常類型（無異常時為 None）
            exc_val: 異常實例（無異常時為 None）
            exc_tb: 追蹤資訊（無異常時為 None）

        Returns:
            True 表示已處理異常，不再傳播
            False 或 None 表示讓異常繼續傳播
        """
        print(f"Exiting {self.name}")
        if exc_type is not None:
            print(f"  Exception: {exc_type.__name__}: {exc_val}")
        return False  # 讓異常繼續傳播

# 使用
with ManagedResource("test") as resource:
    print(f"Using {resource.name}")
    # raise ValueError("oops")  # 取消註解測試異常處理

# 輸出：
# Creating test
# Entering test
# Using test
# Exiting test
```

### `__exit__` 的異常處理

```python
from types import TracebackType

class SuppressErrors:
    """抑制特定異常的上下文管理器"""

    def __init__(self, *exceptions: type[BaseException]) -> None:
        self.exceptions = exceptions

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> bool:
        # 如果是我們要抑制的異常類型，返回 True
        if exc_type is not None and issubclass(exc_type, self.exceptions):
            print(f"Suppressed: {exc_type.__name__}: {exc_val}")
            return True  # 吞掉異常
        return False

# 使用
with SuppressErrors(ValueError, KeyError):
    raise ValueError("This will be suppressed")

print("Continues normally")
```

### 返回值的重要性

```python
class DatabaseConnection:
    """展示 __enter__ 返回值的用法"""

    def __init__(self, url: str) -> None:
        self.url = url
        self._connection = None

    def __enter__(self) -> "Cursor":
        self._connection = connect(self.url)
        return self._connection.cursor()  # 返回 cursor，不是 self

    def __exit__(self, *args) -> None:
        if self._connection:
            self._connection.close()

# 使用
with DatabaseConnection("postgres://...") as cursor:
    cursor.execute("SELECT * FROM users")
    # cursor 是 Cursor 物件，不是 DatabaseConnection
```

## contextlib 工具

### @contextmanager 裝飾器

用生成器函式建立上下文管理器，比定義類別更簡潔：

```python
from contextlib import contextmanager
from typing import Iterator

@contextmanager
def timer(name: str) -> Iterator[None]:
    """計時上下文管理器"""
    import time
    start = time.perf_counter()
    print(f"Starting {name}...")

    try:
        yield  # 這裡是 with 區塊執行的地方
    finally:
        elapsed = time.perf_counter() - start
        print(f"{name} took {elapsed:.3f}s")

# 使用
with timer("data processing"):
    process_large_dataset()

# 如果需要返回值
@contextmanager
def temp_directory() -> Iterator[Path]:
    """建立臨時目錄，結束後自動清理"""
    import tempfile
    import shutil
    from pathlib import Path

    path = Path(tempfile.mkdtemp())
    try:
        yield path  # path 會被 as 子句捕獲
    finally:
        shutil.rmtree(path)

with temp_directory() as tmpdir:
    (tmpdir / "test.txt").write_text("hello")
```

### ExitStack

動態管理多個上下文管理器：

```python
from contextlib import ExitStack

def process_multiple_files(filenames: list[str]) -> list[str]:
    """處理多個檔案，確保全部關閉"""
    with ExitStack() as stack:
        files = [
            stack.enter_context(open(fn))
            for fn in filenames
        ]
        return [f.read() for f in files]

# 更複雜的例子：條件式資源
def connect_services(config: dict) -> dict:
    """根據配置連接多個服務"""
    with ExitStack() as stack:
        services = {}

        if config.get("database"):
            services["db"] = stack.enter_context(
                DatabaseConnection(config["database"])
            )

        if config.get("cache"):
            services["cache"] = stack.enter_context(
                CacheConnection(config["cache"])
            )

        if config.get("queue"):
            services["queue"] = stack.enter_context(
                QueueConnection(config["queue"])
            )

        # 所有連接都會在離開時按相反順序關閉
        return do_work(services)
```

### ExitStack 的回調功能

```python
from contextlib import ExitStack

def complex_setup() -> None:
    with ExitStack() as stack:
        # 註冊清理回調
        stack.callback(print, "Cleanup 1")
        stack.callback(print, "Cleanup 2")

        # 推遲上下文管理器
        cm = some_context_manager()
        stack.push(cm)  # 不立即進入，但會在結束時呼叫 __exit__

        # 做一些工作...
        pass

    # 離開時會執行：
    # 1. cm.__exit__()
    # 2. print("Cleanup 2")
    # 3. print("Cleanup 1")  # 注意順序是相反的
```

### nullcontext

需要可選的上下文管理器時使用：

```python
from contextlib import nullcontext

def process_data(lock: Lock | None = None) -> None:
    """可選的鎖定"""
    with lock if lock else nullcontext():
        # 處理資料
        pass

# 更清楚的寫法
def process_data(lock: Lock | None = None) -> None:
    cm = lock if lock else nullcontext()
    with cm:
        pass

# 帶返回值的 nullcontext
from contextlib import nullcontext

def get_stream(filename: str | None) -> Iterator[TextIO]:
    if filename:
        return open(filename)
    return nullcontext(sys.stdout)  # 返回 stdout

with get_stream(None) as f:
    f.write("Hello")  # 寫到 stdout
```

## 嵌套與組合上下文

### 資源的有序獲取與釋放

```python
# 傳統嵌套
with open("input.txt") as infile:
    with open("output.txt", "w") as outfile:
        outfile.write(infile.read())

# Python 3.9+ 可以用括號分組
with (
    open("input.txt") as infile,
    open("output.txt", "w") as outfile
):
    outfile.write(infile.read())

# 多個資源：ExitStack 更靈活
with ExitStack() as stack:
    files = [stack.enter_context(open(f)) for f in filenames]
```

### 組合上下文管理器

```python
from contextlib import contextmanager
from typing import Iterator

@contextmanager
def database_transaction(db: Database) -> Iterator[Transaction]:
    """資料庫交易上下文"""
    tx = db.begin_transaction()
    try:
        yield tx
        tx.commit()
    except Exception:
        tx.rollback()
        raise

@contextmanager
def acquire_lock(lock: Lock, timeout: float = 30) -> Iterator[None]:
    """帶超時的鎖定獲取"""
    if not lock.acquire(timeout=timeout):
        raise TimeoutError(f"Could not acquire lock within {timeout}s")
    try:
        yield
    finally:
        lock.release()

# 組合使用
@contextmanager
def safe_update(db: Database, lock: Lock) -> Iterator[Transaction]:
    """帶鎖定的安全更新"""
    with acquire_lock(lock):
        with database_transaction(db) as tx:
            yield tx
```

## async context manager

### 基本語法

```python
class AsyncResource:
    """非同步上下文管理器"""

    async def __aenter__(self) -> "AsyncResource":
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> bool:
        await self.disconnect()
        return False

# 使用
async def main():
    async with AsyncResource() as resource:
        await resource.do_something()
```

### @asynccontextmanager

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def async_timer(name: str) -> AsyncIterator[None]:
    """非同步計時器"""
    import time
    start = time.perf_counter()
    print(f"Starting {name}...")

    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        print(f"{name} took {elapsed:.3f}s")

async def main():
    async with async_timer("async task"):
        await asyncio.sleep(1)
```

### 與 asyncio 模組的連結

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_task(coro) -> AsyncIterator[asyncio.Task]:
    """管理 Task 生命週期"""
    task = asyncio.create_task(coro)
    try:
        yield task
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

async def main():
    async with managed_task(background_worker()) as task:
        # 做一些工作
        await asyncio.sleep(5)
    # 離開時自動取消 task
```

## 實際範例：交易管理器

結合所有概念，建立一個完整的交易管理器：

```python
from contextlib import contextmanager
from typing import Iterator, Protocol
from dataclasses import dataclass, field
from enum import Enum, auto

class TransactionState(Enum):
    PENDING = auto()
    ACTIVE = auto()
    COMMITTED = auto()
    ROLLED_BACK = auto()

class Transactional(Protocol):
    """可參與交易的資源協議"""

    def begin(self) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

@dataclass
class Transaction:
    """交易物件"""
    id: str
    resources: list[Transactional] = field(default_factory=list)
    state: TransactionState = TransactionState.PENDING

    def add_resource(self, resource: Transactional) -> None:
        if self.state != TransactionState.ACTIVE:
            raise RuntimeError("Transaction is not active")
        resource.begin()
        self.resources.append(resource)

    def commit(self) -> None:
        if self.state != TransactionState.ACTIVE:
            raise RuntimeError("Transaction is not active")

        try:
            for resource in self.resources:
                resource.commit()
            self.state = TransactionState.COMMITTED
        except Exception:
            self.rollback()
            raise

    def rollback(self) -> None:
        if self.state not in (TransactionState.ACTIVE, TransactionState.PENDING):
            return

        errors = []
        for resource in reversed(self.resources):
            try:
                resource.rollback()
            except Exception as e:
                errors.append(e)

        self.state = TransactionState.ROLLED_BACK

        if errors:
            raise ExceptionGroup("Rollback failed", errors)

class TransactionManager:
    """交易管理器"""

    def __init__(self) -> None:
        self._tx_counter = 0

    @contextmanager
    def transaction(self) -> Iterator[Transaction]:
        """建立新交易"""
        self._tx_counter += 1
        tx = Transaction(id=f"tx-{self._tx_counter}")
        tx.state = TransactionState.ACTIVE

        try:
            yield tx
            tx.commit()
        except Exception:
            tx.rollback()
            raise

# 使用範例
class DatabaseResource:
    """模擬資料庫資源"""

    def __init__(self, name: str) -> None:
        self.name = name

    def begin(self) -> None:
        print(f"{self.name}: BEGIN")

    def commit(self) -> None:
        print(f"{self.name}: COMMIT")

    def rollback(self) -> None:
        print(f"{self.name}: ROLLBACK")

def main():
    manager = TransactionManager()
    db1 = DatabaseResource("primary")
    db2 = DatabaseResource("replica")

    with manager.transaction() as tx:
        tx.add_resource(db1)
        tx.add_resource(db2)

        # 做一些操作...
        print("Doing work in transaction")

        # 如果拋出異常，兩個資源都會 rollback
        # raise ValueError("Something went wrong")

    # 正常結束時，兩個資源都會 commit
```

## 常見錯誤

### 1. 忘記 yield

```python
@contextmanager
def broken():
    print("enter")
    # 忘記 yield！
    print("exit")

# 使用時會報錯：generator didn't yield
```

### 2. 在 finally 中 yield

```python
@contextmanager
def also_broken():
    try:
        yield
    finally:
        yield  # 錯誤！不能在 finally 中 yield
```

### 3. 異常處理不當

```python
@contextmanager
def risky():
    resource = acquire_resource()
    yield resource
    release_resource(resource)  # 如果 with 區塊拋異常，這行不會執行！

# 正確做法
@contextmanager
def safe():
    resource = acquire_resource()
    try:
        yield resource
    finally:
        release_resource(resource)  # 一定會執行
```

## 小結

| 概念 | 用途 |
|------|------|
| `__enter__`/`__exit__` | 上下文管理器協議 |
| `@contextmanager` | 用生成器建立上下文管理器 |
| `ExitStack` | 動態管理多個上下文 |
| `nullcontext` | 可選的上下文管理器 |
| `async with` | 非同步上下文管理 |
| `@asynccontextmanager` | 用非同步生成器建立上下文管理器 |

## 思考題

1. `__exit__` 返回 `True` 和 `False` 的差別是什麼？
2. 什麼時候應該用 `ExitStack` 而不是巢狀 `with`？
3. `@contextmanager` 中 `yield` 前後的程式碼分別對應什麼？

---

*上一章：[3.5.2 異常設計架構](../exception-design/)*
*下一章：[3.5.4 插件系統設計](../plugin-system/)*
