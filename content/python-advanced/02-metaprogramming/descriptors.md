---
title: "2.1 Descriptor Protocol 完整指南"
description: "深入理解 Python 的 Descriptor Protocol，@property 的本質"
weight: 1
---

# Descriptor Protocol 完整指南

Descriptor 是 Python 中最強大但也最容易被忽略的機制之一。理解 Descriptor 是深入 Python 物件模型的關鍵。

## 先備知識

- 入門系列 [4.4 單例與快取](../../../python/04-oop/singleton-cache/)（@property 的使用）

## 本章目標

學完本章後，你將能夠：

1. 理解 @property 實際上是一個 Descriptor
2. 區分 Data Descriptor 和 Non-data Descriptor
3. 理解屬性查找順序
4. 實作自訂的 Descriptor

---

## 【原理層】@property 的真相

### property 是一個 Descriptor

當你使用 `@property` 時，實際上是建立了一個 Descriptor：

```python
class Circle:
    def __init__(self, radius):
        self._radius = radius

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, value):
        if value < 0:
            raise ValueError("半徑不能為負")
        self._radius = value

# 等價於
class Circle:
    def __init__(self, radius):
        self._radius = radius

    def get_radius(self):
        return self._radius

    def set_radius(self, value):
        if value < 0:
            raise ValueError("半徑不能為負")
        self._radius = value

    radius = property(get_radius, set_radius)
```

`property` 是 Python 內建的 Descriptor 類別。

### Descriptor Protocol

Descriptor 是實現了以下方法之一的物件：

```python
class Descriptor:
    def __get__(self, obj, objtype=None):
        """讀取屬性時呼叫"""
        pass

    def __set__(self, obj, value):
        """設定屬性時呼叫"""
        pass

    def __delete__(self, obj):
        """刪除屬性時呼叫"""
        pass

    def __set_name__(self, owner, name):
        """Python 3.6+：設定屬性名時呼叫"""
        pass
```

### 簡單範例

```python
class Verbose:
    """一個會報告存取情況的 Descriptor"""

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        print(f"讀取 {self.name}")
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        print(f"設定 {self.name} = {value}")
        obj.__dict__[self.name] = value

class MyClass:
    x = Verbose()

m = MyClass()
m.x = 10  # 輸出：設定 x = 10
print(m.x)  # 輸出：讀取 x，然後 10
```

---

## 【設計層】Data vs Non-data Descriptor

### 兩種 Descriptor

```python
# Data Descriptor：有 __set__ 或 __delete__
class DataDescriptor:
    def __get__(self, obj, objtype=None):
        return "data descriptor"

    def __set__(self, obj, value):
        pass

# Non-data Descriptor：只有 __get__
class NonDataDescriptor:
    def __get__(self, obj, objtype=None):
        return "non-data descriptor"
```

### 屬性查找順序

這是理解 Descriptor 的關鍵：

```text
obj.attr 的查找順序：

1. Data Descriptor（在類別或父類別中）
2. Instance __dict__
3. Non-data Descriptor（在類別或父類別中）
4. Class __dict__
5. __getattr__（如果定義了）
```

```python
class DataDesc:
    def __get__(self, obj, objtype=None):
        return "data descriptor"
    def __set__(self, obj, value):
        pass

class NonDataDesc:
    def __get__(self, obj, objtype=None):
        return "non-data descriptor"

class MyClass:
    data = DataDesc()
    nondata = NonDataDesc()

m = MyClass()
m.__dict__['data'] = "instance value"
m.__dict__['nondata'] = "instance value"

print(m.data)     # data descriptor（Data Descriptor 優先）
print(m.nondata)  # instance value（Instance 優先於 Non-data）
```

### 為什麼 method 是 Non-data Descriptor？

```python
class MyClass:
    def method(self):
        return "method"

# 可以在實例上覆蓋方法
m = MyClass()
m.method = lambda: "overridden"
print(m.method())  # overridden
```

如果 method 是 Data Descriptor，就無法這樣覆蓋了。

---

## 【實作層】實用的 Descriptor

### 延遲計算屬性

```python
class LazyProperty:
    def __init__(self, func):
        self.func = func

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        value = self.func(obj)
        obj.__dict__[self.name] = value  # 快取到實例
        return value

class Data:
    def __init__(self, values):
        self.values = values

    @LazyProperty
    def average(self):
        print("計算平均值...")
        return sum(self.values) / len(self.values)

d = Data([1, 2, 3, 4, 5])
print(d.average)  # 計算平均值... 3.0
print(d.average)  # 3.0（從快取讀取）
```

### 型別驗證器

```python
class Typed:
    def __init__(self, expected_type):
        self.expected_type = expected_type

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(
                f"{self.name} 必須是 {self.expected_type.__name__}"
            )
        obj.__dict__[self.name] = value

class Person:
    name = Typed(str)
    age = Typed(int)

    def __init__(self, name, age):
        self.name = name
        self.age = age

p = Person("Alice", 30)  # OK
p = Person("Bob", "thirty")  # TypeError!
```

### 類似 Django Model Field

```python
class Field:
    def __init__(self, default=None):
        self.default = default

    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, self.default)

    def __set__(self, obj, value):
        setattr(obj, self.private_name, value)

class CharField(Field):
    def __init__(self, max_length, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length

    def __set__(self, obj, value):
        if len(value) > self.max_length:
            raise ValueError(f"超過最大長度 {self.max_length}")
        super().__set__(obj, value)

class User:
    name = CharField(max_length=50)
    email = CharField(max_length=100)
```

---

## 思考題

1. 為什麼 `__set_name__` 是 Python 3.6 才加入的？之前怎麼解決這個問題？
2. `@property` 是 Data Descriptor 還是 Non-data Descriptor？為什麼？
3. 如果 Descriptor 存在於實例的 `__dict__` 中會怎樣？

## 實作練習

1. 實作一個 `@cached_property` 裝飾器
2. 實作一個範圍驗證的 Descriptor（如 `age = Range(0, 150)`）
3. 實作一個只讀屬性的 Descriptor

## 延伸閱讀

- [Python 官方 Descriptor Guide](https://docs.python.org/3/howto/descriptor.html)
- [Real Python - Python Descriptors](https://realpython.com/python-descriptors/)

---

*下一章：[Metaclass 設計與應用](../metaclasses/)*
