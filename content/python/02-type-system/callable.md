---
title: "2.5 Callable 型別與高階函式"
date: 2026-04-24
description: "用 Callable 型別描述可呼叫物件與高階函式，讓 callback、decorator 與依賴注入的型別契約清楚起來"
weight: 5
---

`Callable` 的核心概念是「這個值可以被呼叫，而且我要求它的參數與回傳型別符合特定形狀」。當程式碼把函式當值傳進傳出（callback、decorator、依賴注入）時，`Callable` 讓型別系統幫你在呼叫前就驗證契約，而不是等 runtime 才 AttributeError。

## 什麼時候會用到 Callable

### 函式當作一等公民（first-class function）

Python 的函式是值，可以賦給變數、放進資料結構、當成參數傳遞。一旦函式流動起來，就需要描述它的形狀：

```python
def apply(operation, value):
    return operation(value)  # operation 是什麼？能不能呼叫？接受什麼參數？
```

沒有型別註解時，讀者得追 `operation` 怎麼來的、在哪裡用的，才能知道它的 contract。`Callable` 把這個 contract 提前到簽名。

### 加上 Callable 型別後

```python
from typing import Callable

def apply(operation: Callable[[int], int], value: int) -> int:
    return operation(value)

apply(lambda x: x * 2, 10)  # ✓ 型別檢查通過
apply("not callable", 10)   # ✗ IDE / mypy 立即標紅
```

讀者看簽名就知道：`operation` 必須接受一個 `int`、回傳一個 `int`。

## 基本語法

`Callable` 的泛型形式是 `Callable[[ParamType1, ParamType2, ...], ReturnType]`。

```python
from typing import Callable

# 無參數、回傳 None
on_shutdown: Callable[[], None]

# 接受 str，回傳 bool（驗證器）
validator: Callable[[str], bool]

# 接受兩個 int，回傳 int（雙元運算）
binary_op: Callable[[int, int], int]

# 接受任意型別，回傳任意型別
generic_callback: Callable[..., object]
```

內建函式、lambda、method、class（可實例化的）、有 `__call__` 方法的 class instance，都屬於 `Callable`。

### Python 3.9+ 的新寫法

從 Python 3.9 開始，`collections.abc.Callable` 支援直接用下標語法，不需要 `from typing import`：

```python
from collections.abc import Callable

def register(cb: Callable[[str], None]) -> None:
    ...
```

新程式碼優先用 `collections.abc.Callable`，避免 `typing` 模組的歷史包袱。

## 四種典型使用場景

### 場景一：高階函式（Higher-Order Function）

接受函式作為參數或回傳函式的函式：

```python
from collections.abc import Callable

def retry(operation: Callable[[], str], times: int = 3) -> str:
    last_error: Exception | None = None
    for _ in range(times):
        try:
            return operation()
        except Exception as e:
            last_error = e
    raise RuntimeError(f"retry exhausted") from last_error
```

呼叫端可以傳 lambda、named function、甚至 partial：

```python
from functools import partial

retry(lambda: fetch_user(user_id=42))
retry(partial(fetch_user, user_id=42))
```

### 場景二：Callback 與事件分派

事件系統、非同步流程、hook 註冊都走這個模式：

```python
from collections.abc import Callable

EventHandler = Callable[[dict], None]  # type alias 提升可讀性

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event, []).append(handler)

    def publish(self, event: str, payload: dict) -> None:
        for handler in self._handlers.get(event, []):
            handler(payload)
```

`EventHandler` type alias 讓「這個系統期望 handler 是什麼形狀」在多個呼叫點保持一致。

### 場景三：依賴注入

把相依行為抽成參數，讓測試能替換：

```python
from collections.abc import Callable

def process_order(
    order_id: str,
    fetch_order: Callable[[str], dict],
    save_invoice: Callable[[dict], None],
) -> None:
    order = fetch_order(order_id)
    invoice = build_invoice(order)
    save_invoice(invoice)
```

生產環境注入真實的資料庫與 API client，測試時注入 in-memory fake。型別簽名保證 fake 的形狀與真品一致。

### 場景四：Decorator 的型別標註

Decorator 本身就是「接受函式、回傳函式」的高階函式：

```python
from collections.abc import Callable
from functools import wraps

def log_calls(func: Callable[..., object]) -> Callable[..., object]:
    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> object:
        print(f"calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
```

`Callable[..., object]` 的 `...` 代表「任意參數」，`object` 作為回傳型別是最寬鬆的上界。這個簽名夠描述「這是個 decorator」，但沒法保留被裝飾函式原本的精確型別 — 那需要 `ParamSpec`，見下方進階用法。

## 實際範例：Hook 系統

來自 `.claude/lib/hook_runner.py` 的 hook 註冊模式：

```python
from collections.abc import Callable
from dataclasses import dataclass

HookFunc = Callable[[dict], dict]

@dataclass
class HookConfig:
    name: str
    func: HookFunc
    priority: int = 0

def register_pre_commit(hooks: list[HookConfig], func: HookFunc, name: str) -> None:
    hooks.append(HookConfig(name=name, func=func))

def run_hooks(hooks: list[HookConfig], context: dict) -> dict:
    for hook in sorted(hooks, key=lambda h: h.priority):
        context = hook.func(context)
    return context
```

所有 hook 都承諾 `dict → dict` 的 pipeline 契約。新的 hook 實作者不用讀 runner 程式碼就知道怎麼接。

## 進階用法：ParamSpec 保留精確型別

`Callable[..., T]` 雖然可用，但喪失了「原本的參數型別」。Python 3.10 的 `ParamSpec` 解決了這個問題，常見於 decorator：

```python
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def log_calls(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_calls
def greet(name: str, greeting: str = "Hi") -> str:
    return f"{greeting}, {name}"

greet("Ada")           # ✓ 保留原本簽名
greet(123)             # ✗ mypy 偵測：name 應該是 str
```

裝飾後的 `greet` 仍然具有 `(name: str, greeting: str = "Hi") -> str` 的精確簽名。沒有 `ParamSpec`，decorator 會把一切磨成 `Callable[..., object]`。

## Callable vs Protocol

當你需要的不只是「可呼叫」，而是「某個 class 要有特定方法集合」時，`Protocol` 是更好的選擇：

| 需求                         | 選擇       | 範例                                    |
| ---------------------------- | ---------- | --------------------------------------- |
| 只關心「可被呼叫」           | `Callable` | `Callable[[int], str]`                  |
| 需要多個方法（read / write） | `Protocol` | 定義一個有 `read()` 與 `write()` 的類型 |
| 需要屬性而非方法             | `Protocol` | 定義一個有 `name: str` 的類型           |

兩者互補：`Callable` 是 `Protocol` 的特例（只有 `__call__` 方法）。

## 常見陷阱

### 把 Callable 當成「任意函式」使用

```python
def process(callback: Callable) -> None:  # 失去型別資訊
    callback(some_value)
```

沒加參數型別的 `Callable` 等同於 `Callable[..., Any]`，型別檢查器會放行任何呼叫。這不是 type hints 的失敗，是契約寫太鬆。若真的要接受任何可呼叫物件，至少寫清楚參數與回傳上界：`Callable[..., object]`。

### 忽略 method 和 function 的差異

```python
class Logger:
    def log(self, msg: str) -> None:
        print(msg)

# 直接傳 Logger 的 log method（綁定方法）
cb: Callable[[str], None] = Logger().log  # ✓

# 直接傳 unbound class method（需要 self）
cb: Callable[[Logger, str], None] = Logger.log  # 另一種簽名
```

Bound method（實例呼叫的）已經把 `self` 隱藏起來，型別從簽名看是 `(msg: str) -> None`。Unbound method 會要你提供 `self`。混淆兩者在 decorator 場景特別常見。

### lambda 的型別推斷有限

```python
handler: Callable[[int], str] = lambda x: f"got {x}"  # ✓
handler = lambda x: f"got {x}"                          # lambda 參數型別推斷為 Any
```

lambda 本身不帶型別註解，要靠左側變數註解把型別灌進去。直接賦值給無註解變數時型別會退化。

## 小結

`Callable` 是 Python 型別系統描述「函式形狀」的基本工具。當函式開始當值流動（callbacks、decorators、dependency injection），`Callable` 把「能不能呼叫、接受什麼、回傳什麼」的契約寫進簽名，讓讀者與工具不必追到實作才能理解意圖。進階場景（保留 decorator 的精確型別）使用 `ParamSpec`；當契約擴展到多個方法或屬性時，升級到 `Protocol`。
