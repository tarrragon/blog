---
title: "2.4 反射與 inspect 模組"
date: 2026-01-20
description: "使用反射和 inspect 模組檢視和操作 Python 物件"
weight: 4
---

# 反射與 inspect 模組

反射是程式檢視和修改自身結構的能力。Python 提供了強大的反射工具，讓你能夠動態地檢視物件、取得函式簽名、甚至修改執行中的程式。

## 先備知識

- [2.3 類別裝飾器與動態類別](../class-creation/)

## 本章目標

學完本章後，你將能夠：

1. 使用內建反射函式（getattr、setattr 等）
2. 使用 inspect 模組分析物件
3. 理解 __getattr__ 和 __getattribute__ 的差異
4. 實作動態代理和 Mock 物件

---

## 【原理層】反射的基本概念

### 什麼是反射？

反射是程式在執行時檢視自身結構的能力：

```python
class MyClass:
    def __init__(self, value):
        self.value = value

    def method(self):
        return self.value * 2

obj = MyClass(10)

# 反射：程式檢視自己
print(type(obj))                    # <class 'MyClass'>
print(obj.__class__.__name__)       # MyClass
print(dir(obj))                     # ['__class__', 'method', 'value', ...]
print(hasattr(obj, 'value'))        # True
print(getattr(obj, 'value'))        # 10
```

### 內建反射函式

```python
obj = MyClass(10)

# getattr - 取得屬性
value = getattr(obj, 'value')                    # 10
default = getattr(obj, 'missing', 'default')     # 'default'

# setattr - 設定屬性
setattr(obj, 'value', 20)
print(obj.value)  # 20

# hasattr - 檢查屬性是否存在
print(hasattr(obj, 'value'))   # True
print(hasattr(obj, 'missing')) # False

# delattr - 刪除屬性
delattr(obj, 'value')
print(hasattr(obj, 'value'))   # False
```

### vars() 和 __dict__

```python
class Person:
    species = "Human"  # 類別屬性

    def __init__(self, name):
        self.name = name  # 實例屬性

p = Person("Alice")

# 實例的 __dict__：只包含實例屬性
print(vars(p))         # {'name': 'Alice'}
print(p.__dict__)      # {'name': 'Alice'}

# 類別的 __dict__：包含類別屬性和方法
print(vars(Person))    # {'species': 'Human', '__init__': ..., ...}
```

---

## 【設計層】__getattr__ vs __getattribute__

### __getattr__

當正常屬性查找失敗時呼叫：

```python
class FlexibleObject:
    def __init__(self):
        self.existing = "I exist"

    def __getattr__(self, name):
        return f"動態屬性: {name}"

obj = FlexibleObject()
print(obj.existing)  # I exist（正常查找成功）
print(obj.missing)   # 動態屬性: missing（__getattr__ 被呼叫）
```

### __getattribute__

所有屬性存取都會呼叫（包括存在的屬性）：

```python
class LoggedObject:
    def __init__(self, value):
        object.__setattr__(self, 'value', value)

    def __getattribute__(self, name):
        print(f"存取屬性: {name}")
        return object.__getattribute__(self, name)

obj = LoggedObject(10)
print(obj.value)
# 輸出：
# 存取屬性: value
# 10
```

注意：在 `__getattribute__` 中要避免無限遞迴：

```python
class Dangerous:
    def __getattribute__(self, name):
        # 錯誤！這會造成無限遞迴
        # return self.data[name]

        # 正確：使用 object.__getattribute__
        data = object.__getattribute__(self, 'data')
        return data.get(name)
```

---

## 【實作層】inspect 模組

### 檢視物件類型

```python
import inspect

def my_function():
    pass

class MyClass:
    def method(self):
        pass

print(inspect.isfunction(my_function))  # True
print(inspect.ismethod(my_function))    # False
print(inspect.isclass(MyClass))         # True

obj = MyClass()
print(inspect.ismethod(obj.method))     # True
```

### 取得函式簽名

```python
import inspect

def greet(name: str, greeting: str = "Hello") -> str:
    """打招呼函式"""
    return f"{greeting}, {name}!"

# 取得簽名
sig = inspect.signature(greet)
print(sig)  # (name: str, greeting: str = 'Hello') -> str

# 檢視參數
for param_name, param in sig.parameters.items():
    print(f"  {param_name}:")
    print(f"    default: {param.default}")
    print(f"    annotation: {param.annotation}")
    print(f"    kind: {param.kind}")

# 輸出：
#   name:
#     default: <class 'inspect._empty'>
#     annotation: <class 'str'>
#     kind: POSITIONAL_OR_KEYWORD
#   greeting:
#     default: Hello
#     annotation: <class 'str'>
#     kind: POSITIONAL_OR_KEYWORD
```

### 取得原始碼

```python
import inspect

def example_function():
    """這是範例函式"""
    x = 1
    return x + 1

# 取得原始碼
print(inspect.getsource(example_function))
# def example_function():
#     """這是範例函式"""
#     x = 1
#     return x + 1

# 取得文件字串
print(inspect.getdoc(example_function))
# 這是範例函式

# 取得檔案位置
print(inspect.getfile(example_function))
```

### 取得呼叫堆疊

```python
import inspect

def inner():
    stack = inspect.stack()
    for frame_info in stack:
        print(f"{frame_info.function} at {frame_info.lineno}")

def outer():
    inner()

def main():
    outer()

main()
# 輸出：
# inner at 5
# outer at 9
# main at 12
# <module> at 14
```

---

## 【實戰】實用應用

### 動態呼叫方法

```python
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b

def execute(calc, operation, a, b):
    """動態執行運算"""
    method = getattr(calc, operation, None)
    if method and callable(method):
        return method(a, b)
    raise ValueError(f"不支援的運算: {operation}")

calc = Calculator()
print(execute(calc, "add", 5, 3))       # 8
print(execute(calc, "multiply", 5, 3))  # 15
```

### 簡單的 Mock 物件

```python
class Mock:
    """簡單的 Mock 物件"""

    def __init__(self):
        self._calls = []

    def __getattr__(self, name):
        def method(*args, **kwargs):
            self._calls.append({
                'method': name,
                'args': args,
                'kwargs': kwargs,
            })
            return Mock()  # 支援鏈式呼叫

        return method

    @property
    def call_count(self):
        return len(self._calls)

    def assert_called_with(self, method, *args, **kwargs):
        for call in self._calls:
            if (call['method'] == method and
                call['args'] == args and
                call['kwargs'] == kwargs):
                return True
        raise AssertionError(f"{method} 沒有以預期的參數被呼叫")

# 使用
mock = Mock()
mock.save("data", flush=True)
mock.load("file.txt")

print(mock.call_count)  # 2
mock.assert_called_with("save", "data", flush=True)  # OK
```

### 動態代理

```python
class LoggingProxy:
    """記錄所有方法呼叫的代理"""

    def __init__(self, target):
        object.__setattr__(self, '_target', target)
        object.__setattr__(self, '_log', [])

    def __getattr__(self, name):
        attr = getattr(self._target, name)

        if callable(attr):
            def logged_method(*args, **kwargs):
                self._log.append({
                    'method': name,
                    'args': args,
                    'kwargs': kwargs,
                })
                return attr(*args, **kwargs)
            return logged_method

        return attr

    def __setattr__(self, name, value):
        setattr(self._target, name, value)

    def get_log(self):
        return self._log

# 使用
class Database:
    def query(self, sql):
        return f"執行: {sql}"

    def insert(self, table, data):
        return f"插入到 {table}"

db = LoggingProxy(Database())
db.query("SELECT * FROM users")
db.insert("users", {"name": "Alice"})

for entry in db.get_log():
    print(entry)
# {'method': 'query', 'args': ('SELECT * FROM users',), 'kwargs': {}}
# {'method': 'insert', 'args': ('users', {'name': 'Alice'}), 'kwargs': {}}
```

### 自動生成 API 文件

```python
import inspect

def generate_api_doc(cls):
    """為類別生成簡單的 API 文件"""
    lines = [f"# {cls.__name__}", ""]

    if cls.__doc__:
        lines.extend([cls.__doc__, ""])

    lines.append("## Methods")
    lines.append("")

    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith('_'):
            continue

        sig = inspect.signature(method)
        doc = inspect.getdoc(method) or "No description"

        lines.append(f"### `{name}{sig}`")
        lines.append("")
        lines.append(doc)
        lines.append("")

    return '\n'.join(lines)

class UserService:
    """用戶服務類別"""

    def create_user(self, name: str, email: str) -> dict:
        """建立新用戶

        Args:
            name: 用戶名稱
            email: 電子郵件

        Returns:
            新建立的用戶資料
        """
        pass

    def get_user(self, user_id: int) -> dict:
        """取得用戶資料"""
        pass

print(generate_api_doc(UserService))
```

---

## 【框架應用】

### pytest 的反射使用

```python
# pytest 使用反射來發現測試
import inspect

def discover_tests(module):
    """模擬 pytest 的測試發現"""
    tests = []

    for name, obj in inspect.getmembers(module):
        if name.startswith('test_') and inspect.isfunction(obj):
            tests.append(obj)

    return tests

# 使用
def test_addition():
    assert 1 + 1 == 2

def test_subtraction():
    assert 2 - 1 == 1

def helper_function():  # 不會被發現
    pass

import sys
tests = discover_tests(sys.modules[__name__])
for test in tests:
    print(f"發現測試: {test.__name__}")
```

### FastAPI 的參數解析

```python
import inspect
from typing import get_type_hints

def parse_function_params(func):
    """模擬 FastAPI 的參數解析"""
    sig = inspect.signature(func)
    hints = get_type_hints(func)

    params = []
    for name, param in sig.parameters.items():
        params.append({
            'name': name,
            'type': hints.get(name, 'Any'),
            'default': None if param.default is inspect.Parameter.empty else param.default,
            'required': param.default is inspect.Parameter.empty,
        })

    return params

def create_user(name: str, age: int, active: bool = True):
    pass

params = parse_function_params(create_user)
for p in params:
    print(p)
# {'name': 'name', 'type': <class 'str'>, 'default': None, 'required': True}
# {'name': 'age', 'type': <class 'int'>, 'default': None, 'required': True}
# {'name': 'active', 'type': <class 'bool'>, 'default': True, 'required': False}
```

---

## 思考題

1. 為什麼 `hasattr` 可能會觸發副作用？什麼情況下應該避免使用？
2. `__getattr__` 和 `__getattribute__` 在效能上有什麼差異？
3. 如何用反射實作一個簡單的依賴注入框架？

## 實作練習

1. 實作一個 `@deprecated` 裝飾器，使用 `inspect` 記錄呼叫位置
2. 建立一個簡單的 RPC 框架，根據方法名稱動態呼叫遠端方法
3. 實作一個物件比較工具，使用反射比較兩個物件的所有屬性

## 延伸閱讀

- [Python 官方 - inspect 模組](https://docs.python.org/3/library/inspect.html)
- [Python 官方 - 內建函式](https://docs.python.org/3/library/functions.html)

---

*上一章：[類別裝飾器與動態類別](../class-creation/)*
*下一模組：[模組三：CPython 內部機制](../../03-cpython-internals/)*
