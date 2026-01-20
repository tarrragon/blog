---
title: "2.3 類別裝飾器與動態類別"
description: "使用類別裝飾器和 type() 動態建立類別"
weight: 3
---

# 類別裝飾器與動態類別

類別裝飾器是比 Metaclass 更簡單、更實用的元編程工具。大多數情況下，類別裝飾器就能滿足需求。

## 先備知識

- [2.2 Metaclass 設計與應用](../metaclasses/)

## 本章目標

學完本章後，你將能夠：

1. 編寫類別裝飾器
2. 理解 `@dataclass` 的實現原理
3. 使用 `type()` 動態建立類別
4. 選擇合適的元編程工具

---

## 【原理層】類別裝飾器

### 基本結構

類別裝飾器是一個接收類別、返回類別的函式：

```python
def my_decorator(cls):
    # 修改或增強 cls
    return cls

@my_decorator
class MyClass:
    pass

# 等價於
class MyClass:
    pass
MyClass = my_decorator(MyClass)
```

### 與函式裝飾器的差異

```python
# 函式裝飾器通常返回包裝函式
def func_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before")
        result = func(*args, **kwargs)
        print("After")
        return result
    return wrapper

# 類別裝飾器通常直接修改類別
def class_decorator(cls):
    cls.new_attribute = "added"
    return cls
```

### 執行時機

```python
def decorator(cls):
    print(f"裝飾 {cls.__name__}")
    return cls

@decorator
class MyClass:
    print("定義類別主體")

# 輸出：
# 定義類別主體
# 裝飾 MyClass
```

類別裝飾器在類別定義完成後立即執行。

---

## 【設計層】帶參數的裝飾器

### 裝飾器工廠

```python
def repeat_method(times):
    """讓指定方法重複執行 times 次"""
    def decorator(cls):
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            for _ in range(times):
                original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls

    return decorator

@repeat_method(3)
class Counter:
    count = 0

    def __init__(self):
        Counter.count += 1

c = Counter()
print(Counter.count)  # 3
```

### 實用範例：@singleton

```python
def singleton(cls):
    """單例模式裝飾器"""
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance

@singleton
class Database:
    def __init__(self, host):
        self.host = host
        print(f"連接到 {host}")

db1 = Database("localhost")  # 連接到 localhost
db2 = Database("remote")     # 不會再次連接
print(db1 is db2)  # True
```

注意：這個實現返回的是函式而不是類別，所以 `isinstance(db1, Database)` 會失敗。更好的實現：

```python
def singleton(cls):
    """保持類別特性的單例裝飾器"""
    _instance = None

    class SingletonWrapper(cls):
        def __new__(wrapper_cls, *args, **kwargs):
            nonlocal _instance
            if _instance is None:
                _instance = super().__new__(wrapper_cls)
            return _instance

    SingletonWrapper.__name__ = cls.__name__
    SingletonWrapper.__qualname__ = cls.__qualname__
    return SingletonWrapper
```

---

## 【實作層】實用類別裝飾器

### @auto_repr

```python
def auto_repr(cls):
    """自動生成 __repr__ 方法"""
    def __repr__(self):
        attrs = ', '.join(
            f"{k}={v!r}"
            for k, v in self.__dict__.items()
            if not k.startswith('_')
        )
        return f"{cls.__name__}({attrs})"

    cls.__repr__ = __repr__
    return cls

@auto_repr
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

p = Person("Alice", 30)
print(p)  # Person(name='Alice', age=30)
```

### @dataclass 的簡化實現

```python
def dataclass(cls):
    """簡化版 dataclass"""
    # 收集類別屬性中的型別註解
    annotations = getattr(cls, '__annotations__', {})

    # 生成 __init__
    def __init__(self, **kwargs):
        for name in annotations:
            setattr(self, name, kwargs.get(name))

    # 生成 __repr__
    def __repr__(self):
        attrs = ', '.join(
            f"{name}={getattr(self, name)!r}"
            for name in annotations
        )
        return f"{cls.__name__}({attrs})"

    # 生成 __eq__
    def __eq__(self, other):
        if not isinstance(other, cls):
            return NotImplemented
        return all(
            getattr(self, name) == getattr(other, name)
            for name in annotations
        )

    cls.__init__ = __init__
    cls.__repr__ = __repr__
    cls.__eq__ = __eq__

    return cls

@dataclass
class Point:
    x: int
    y: int

p1 = Point(x=1, y=2)
p2 = Point(x=1, y=2)
print(p1)         # Point(x=1, y=2)
print(p1 == p2)   # True
```

### @timer（方法計時）

```python
import time
from functools import wraps

def timer(cls):
    """為所有公開方法添加計時"""
    for name, method in list(cls.__dict__.items()):
        if callable(method) and not name.startswith('_'):
            @wraps(method)
            def timed_method(self, *args, _method=method, _name=name, **kwargs):
                start = time.perf_counter()
                result = _method(self, *args, **kwargs)
                elapsed = time.perf_counter() - start
                print(f"{_name}: {elapsed:.4f}s")
                return result

            setattr(cls, name, timed_method)

    return cls

@timer
class Calculator:
    def slow_add(self, a, b):
        time.sleep(0.1)
        return a + b

calc = Calculator()
calc.slow_add(1, 2)  # slow_add: 0.1001s
```

---

## 【設計層】動態建立類別

### 使用 type()

```python
# 基本用法
def greet(self):
    return f"Hello, {self.name}"

Person = type('Person', (), {
    'species': 'Human',
    'greet': greet,
})

p = Person()
p.name = "Alice"
print(p.greet())  # Hello, Alice
```

### 動態繼承

```python
def create_model(name, fields):
    """動態建立模型類別"""

    def __init__(self, **kwargs):
        for field in fields:
            setattr(self, field, kwargs.get(field))

    def __repr__(self):
        attrs = ', '.join(f"{f}={getattr(self, f)!r}" for f in fields)
        return f"{name}({attrs})"

    return type(name, (), {
        '__init__': __init__,
        '__repr__': __repr__,
        '_fields': fields,
    })

User = create_model('User', ['id', 'name', 'email'])
Product = create_model('Product', ['id', 'name', 'price'])

u = User(id=1, name="Alice", email="alice@example.com")
print(u)  # User(id=1, name='Alice', email='alice@example.com')
```

### 條件繼承

```python
def create_handler(use_async=False):
    """根據條件選擇基類"""

    if use_async:
        import asyncio

        class AsyncBase:
            async def handle(self, data):
                await asyncio.sleep(0.1)
                return f"Async: {data}"

        base = AsyncBase
    else:
        class SyncBase:
            def handle(self, data):
                return f"Sync: {data}"

        base = SyncBase

    return type('Handler', (base,), {})

SyncHandler = create_handler(use_async=False)
AsyncHandler = create_handler(use_async=True)
```

---

## 【選擇指南】

### Metaclass vs 類別裝飾器 vs __init_subclass__

| 特性 | 類別裝飾器 | __init_subclass__ | Metaclass |
|------|-----------|-------------------|-----------|
| 學習曲線 | 低 | 低 | 高 |
| 影響子類別 | 否 | 是 | 是 |
| 可堆疊 | 是 | 是（需 super） | 困難 |
| 控制程度 | 類別建立後 | 子類別定義時 | 類別建立中 |
| 適用場景 | 添加/修改方法 | 註冊/驗證 | 深度自訂 |

### 決策流程

```text
需要修改類別的行為？
│
├── 只在單一類別上？
│   └── 類別裝飾器
│
├── 需要自動影響所有子類別？
│   ├── 只是註冊或簡單驗證？
│   │   └── __init_subclass__
│   │
│   └── 需要修改類別建立過程？
│       └── Metaclass
│
└── 需要完全動態建立類別？
    └── type()
```

---

## 【實戰】組合使用

```python
from functools import wraps

def validate_types(cls):
    """型別驗證裝飾器"""
    original_init = cls.__init__
    annotations = getattr(cls, '__annotations__', {})

    @wraps(original_init)
    def validated_init(self, *args, **kwargs):
        # 將位置參數轉換為關鍵字參數
        import inspect
        sig = inspect.signature(original_init)
        params = list(sig.parameters.keys())[1:]  # 跳過 self

        for i, arg in enumerate(args):
            if i < len(params):
                kwargs[params[i]] = arg

        # 驗證型別
        for name, expected_type in annotations.items():
            if name in kwargs:
                value = kwargs[name]
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"{name} 應為 {expected_type.__name__}，"
                        f"但得到 {type(value).__name__}"
                    )

        original_init(self, **kwargs)

    cls.__init__ = validated_init
    return cls

@validate_types
class User:
    name: str
    age: int

    def __init__(self, name, age):
        self.name = name
        self.age = age

User("Alice", 30)  # OK
# User("Bob", "thirty")  # TypeError!
```

---

## 思考題

1. 類別裝飾器和 Metaclass 可以同時使用嗎？執行順序是什麼？
2. `@dataclass` 實際上使用了哪些技術？
3. 動態建立的類別和靜態定義的類別有什麼差異？

## 實作練習

1. 實作一個 `@frozen` 裝飾器，讓類別的實例不可變
2. 實作一個 `@trace` 裝飾器，追蹤所有方法呼叫
3. 使用 `type()` 建立一個簡單的 Enum 類別

## 延伸閱讀

- [PEP 557 - Data Classes](https://peps.python.org/pep-0557/)
- [Python 官方 - dataclasses 模組](https://docs.python.org/3/library/dataclasses.html)

---

*上一章：[Metaclass 設計與應用](../metaclasses/)*
*下一章：[反射與 inspect 模組](../introspection/)*
