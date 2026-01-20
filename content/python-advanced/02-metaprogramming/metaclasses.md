---
title: "2.2 Metaclass 設計與應用"
description: "理解 Python 的類別建立機制與 Metaclass"
weight: 2
---

# Metaclass 設計與應用

Metaclass 是「類別的類別」，控制類別本身的建立過程。這是 Python 中最深層的元編程機制。

## 先備知識

- [2.1 Descriptor Protocol](../descriptors/)

## 本章目標

學完本章後，你將能夠：

1. 理解「類別也是物件」的概念
2. 理解類別的建立流程
3. 使用 Metaclass 控制類別行為
4. 選擇適當的元編程工具

---

## 【原理層】類別也是物件

### type 是所有類別的 Metaclass

在 Python 中，類別本身也是物件：

```python
class MyClass:
    pass

# 類別是 type 的實例
print(type(MyClass))  # <class 'type'>
print(isinstance(MyClass, type))  # True

# 物件是類別的實例
obj = MyClass()
print(type(obj))  # <class '__main__.MyClass'>
print(isinstance(obj, MyClass))  # True
```

```text
關係圖：

type ─────────────┐
  │               │
  ├── MyClass ────┤
  │     │         │ (都是 type 的實例)
  │     └── obj   │
  │               │
  └── int ────────┘
        │
        └── 42
```

### type() 的三參數形式

`type()` 可以動態建立類別：

```python
# 這兩種方式等價
class MyClass:
    x = 10
    def method(self):
        return self.x

# 等價於
def method(self):
    return self.x

MyClass = type('MyClass', (), {'x': 10, 'method': method})
```

參數說明：
- 第一個參數：類別名稱
- 第二個參數：父類別的 tuple
- 第三個參數：屬性和方法的 dict

```python
# 繼承的例子
class Parent:
    def greet(self):
        return "Hello"

Child = type('Child', (Parent,), {'name': 'Child Class'})

c = Child()
print(c.greet())  # Hello
print(c.name)     # Child Class
```

---

## 【設計層】類別建立過程

### 建立流程

當 Python 執行 `class` 語句時，會依序呼叫這些方法：

```text
class MyClass(Parent, metaclass=Meta):
    ...

執行流程：
1. Meta.__prepare__(name, bases) → 返回類別的 namespace（通常是 dict）
2. 執行類別主體，填充 namespace
3. Meta.__new__(mcs, name, bases, namespace) → 建立類別物件
4. Meta.__init__(cls, name, bases, namespace) → 初始化類別物件
```

```python
class LoggingMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        print(f"1. __prepare__: 準備 {name} 的 namespace")
        return {}

    def __new__(mcs, name, bases, namespace):
        print(f"2. __new__: 建立 {name}")
        return super().__new__(mcs, name, bases, namespace)

    def __init__(cls, name, bases, namespace):
        print(f"3. __init__: 初始化 {name}")
        super().__init__(name, bases, namespace)

class MyClass(metaclass=LoggingMeta):
    x = 10
    print("   （執行類別主體）")

# 輸出：
# 1. __prepare__: 準備 MyClass 的 namespace
#    （執行類別主體）
# 2. __new__: 建立 MyClass
# 3. __init__: 初始化 MyClass
```

### __call__ 控制實例建立

Metaclass 的 `__call__` 控制類別被呼叫時的行為：

```python
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Singleton(metaclass=SingletonMeta):
    def __init__(self, value):
        self.value = value

s1 = Singleton(1)
s2 = Singleton(2)
print(s1 is s2)  # True
print(s1.value)  # 1（第二次初始化被跳過）
```

---

## 【設計層】__init_subclass__ - 輕量替代方案

Python 3.6 引入了 `__init_subclass__`，很多情況下可以替代 Metaclass：

```python
class Plugin:
    _plugins = {}

    def __init_subclass__(cls, plugin_name=None, **kwargs):
        super().__init_subclass__(**kwargs)
        name = plugin_name or cls.__name__
        cls._plugins[name] = cls
        print(f"註冊插件: {name}")

class EmailPlugin(Plugin, plugin_name="email"):
    pass

class SMSPlugin(Plugin, plugin_name="sms"):
    pass

print(Plugin._plugins)
# {'email': <class 'EmailPlugin'>, 'sms': <class 'SMSPlugin'>}
```

### 何時用 __init_subclass__，何時用 Metaclass？

| 需求 | 推薦方案 |
|------|---------|
| 註冊子類別 | `__init_subclass__` |
| 驗證類別屬性 | `__init_subclass__` |
| 修改類別的 namespace | Metaclass（`__prepare__`） |
| 控制實例建立 | Metaclass（`__call__`） |
| 修改類別建立過程 | Metaclass |
| 需要影響多層繼承 | Metaclass |

---

## 【實作層】實用範例

### 自動註冊子類別

```python
class Registry:
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__name__ != 'Base':  # 跳過中間類別
            Registry._registry[cls.__name__] = cls

    @classmethod
    def get(cls, name):
        return cls._registry.get(name)

    @classmethod
    def create(cls, name, *args, **kwargs):
        klass = cls.get(name)
        if klass:
            return klass(*args, **kwargs)
        raise ValueError(f"Unknown type: {name}")

class Handler(Registry):
    pass

class JSONHandler(Handler):
    def process(self, data):
        return f"Processing JSON: {data}"

class XMLHandler(Handler):
    def process(self, data):
        return f"Processing XML: {data}"

# 使用
handler = Registry.create("JSONHandler")
print(handler.process("data"))  # Processing JSON: data
```

### 介面驗證

```python
class InterfaceMeta(type):
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        # 跳過基類本身
        if bases:
            # 檢查是否實現了必要的方法
            required = getattr(cls, '_required_methods', [])
            for method in required:
                if method not in namespace:
                    raise TypeError(
                        f"{name} 必須實現 {method} 方法"
                    )
        return cls

class Serializable(metaclass=InterfaceMeta):
    _required_methods = ['serialize', 'deserialize']

# 這會引發 TypeError
# class BadSerializer(Serializable):
#     pass

class GoodSerializer(Serializable):
    def serialize(self, obj):
        return str(obj)

    def deserialize(self, data):
        return eval(data)
```

### 使用 __prepare__ 記錄定義順序

```python
from collections import OrderedDict

class OrderedMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        return OrderedDict()

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, dict(namespace))
        cls._field_order = [
            k for k in namespace.keys()
            if not k.startswith('_')
        ]
        return cls

class Form(metaclass=OrderedMeta):
    name = "text"
    email = "email"
    age = "number"

print(Form._field_order)  # ['name', 'email', 'age']
```

### 簡單的 ORM 基類

```python
class Field:
    pass

class CharField(Field):
    def __init__(self, max_length):
        self.max_length = max_length

class IntegerField(Field):
    pass

class ModelMeta(type):
    def __new__(mcs, name, bases, namespace):
        # 收集欄位
        fields = {}
        for key, value in namespace.items():
            if isinstance(value, Field):
                fields[key] = value

        cls = super().__new__(mcs, name, bases, namespace)
        cls._fields = fields
        return cls

class Model(metaclass=ModelMeta):
    def __init__(self, **kwargs):
        for name in self._fields:
            setattr(self, name, kwargs.get(name))

    def __repr__(self):
        fields = ', '.join(
            f"{k}={getattr(self, k)!r}"
            for k in self._fields
        )
        return f"{self.__class__.__name__}({fields})"

class User(Model):
    name = CharField(max_length=100)
    age = IntegerField()

u = User(name="Alice", age=30)
print(u)  # User(name='Alice', age=30)
print(User._fields)  # {'name': CharField, 'age': IntegerField}
```

---

## 【選擇指南】元編程工具比較

```text
問題：我需要修改類別的行為

├── 只是想在子類別定義時做些事？
│   └── 用 __init_subclass__
│
├── 需要驗證或轉換類別屬性？
│   ├── 簡單驗證 → __init_subclass__
│   └── 需要修改 namespace → Metaclass
│
├── 需要控制實例建立？
│   ├── 簡單快取 → __new__
│   └── 複雜邏輯 → Metaclass.__call__
│
├── 需要記錄屬性定義順序？
│   └── Metaclass.__prepare__
│
└── 只是想在實例上添加行為？
    └── 用類別裝飾器（下一章）
```

---

## 思考題

1. 為什麼 `type(type)` 是 `type` 自己？這是如何實現的？
2. 如果一個類別同時有 Metaclass 和 `__init_subclass__`，執行順序是什麼？
3. Django 的 Model 是如何使用 Metaclass 的？

## 實作練習

1. 實作一個 Metaclass，自動為類別添加 `__repr__` 方法
2. 實作一個 `@abstractmethod` 裝飾器和配套的 Metaclass
3. 使用 `__init_subclass__` 實作一個事件處理器註冊系統

## 延伸閱讀

- [Python 官方 - Data Model](https://docs.python.org/3/reference/datamodel.html#customizing-class-creation)
- [Ionel MC - Understanding Python Metaclasses](https://blog.ionelmc.ro/2015/02/09/understanding-python-metaclasses/)

---

*上一章：[Descriptor Protocol 完整指南](../descriptors/)*
*下一章：[類別裝飾器與動態類別](../class-creation/)*
