---
title: "3.1 PyObject 與物件模型"
description: "深入理解 Python 的物件模型"
weight: 1
---

# PyObject 與物件模型

Python 中「一切皆物件」不只是一句口號，而是 CPython 實現的核心設計。理解 PyObject 是深入 Python 內部的第一步。

## 先備知識

- 進階系列 [模組二：元編程](../../02-metaprogramming/)
- 基本的 C 語言知識（結構體、指標）

## 本章目標

學完本章後，你將能夠：

1. 理解 PyObject 結構
2. 理解參考計數的工作原理
3. 解釋「一切皆物件」的實現方式
4. 觀察物件的記憶體佈局

---

## 【原理層】一切皆物件

### 什麼是「一切皆物件」？

在 Python 中，所有東西都是物件：

```python
# 數字是物件
x = 42
print(type(x))        # <class 'int'>
print(x.__class__)    # <class 'int'>
print(x.bit_length()) # 6（呼叫方法）

# 函式是物件
def hello():
    pass
print(type(hello))    # <class 'function'>
print(hello.__name__) # hello

# 類別是物件
class MyClass:
    pass
print(type(MyClass))  # <class 'type'>

# 甚至 type 本身也是物件
print(type(type))     # <class 'type'>
```

### PyObject 結構

在 C 語言層面，所有 Python 物件都基於 `PyObject` 結構：

```c
// CPython 原始碼中的定義（簡化版）
typedef struct _object {
    Py_ssize_t ob_refcnt;  // 參考計數
    PyTypeObject *ob_type; // 型別指標
} PyObject;
```

每個 Python 物件在記憶體中至少包含這兩個欄位：

```text
┌─────────────────────────────────────┐
│           PyObject                   │
├─────────────────────────────────────┤
│  ob_refcnt (參考計數)    8 bytes    │
│  ob_type   (型別指標)    8 bytes    │
├─────────────────────────────────────┤
│  ... 物件特定的資料 ...              │
└─────────────────────────────────────┘
```

### 變長物件：PyVarObject

對於長度可變的物件（如 list、str），使用 `PyVarObject`：

```c
typedef struct {
    PyObject ob_base;
    Py_ssize_t ob_size;  // 元素數量
} PyVarObject;
```

```text
┌─────────────────────────────────────┐
│         PyVarObject                  │
├─────────────────────────────────────┤
│  ob_refcnt (參考計數)    8 bytes    │
│  ob_type   (型別指標)    8 bytes    │
│  ob_size   (元素數量)    8 bytes    │
├─────────────────────────────────────┤
│  ... 元素資料 ...                    │
└─────────────────────────────────────┘
```

---

## 【設計層】參考計數

### 工作原理

Python 使用參考計數來追蹤物件的使用：

```python
import sys

a = [1, 2, 3]
print(sys.getrefcount(a))  # 2（a 本身 + getrefcount 的參數）

b = a  # 增加參考
print(sys.getrefcount(a))  # 3

del b  # 減少參考
print(sys.getrefcount(a))  # 2
```

### 參考計數的增減時機

```python
# 增加參考計數的操作
x = obj          # 賦值
container.append(obj)  # 加入容器
func(obj)        # 作為參數傳遞

# 減少參考計數的操作
del x            # 刪除變數
x = other        # 重新賦值
container.remove(obj)  # 從容器移除
函式返回         # 區域變數離開作用域
```

### 參考計數的優缺點

| 優點 | 缺點 |
| ---- | ---- |
| 即時回收 | 無法處理循環參考 |
| 可預測的記憶體使用 | 每次操作都要更新計數 |
| 簡單易理解 | 多執行緒下需要鎖（GIL 的原因之一） |

---

## 【實作層】觀察物件

### 使用 id() 觀察記憶體位址

```python
a = [1, 2, 3]
b = a
c = [1, 2, 3]

print(id(a))  # 140234567890112
print(id(b))  # 140234567890112（同一物件）
print(id(c))  # 140234567890176（不同物件）

print(a is b)  # True
print(a is c)  # False
print(a == c)  # True（值相等）
```

### 小整數快取

CPython 對 -5 到 256 的整數進行快取：

```python
a = 256
b = 256
print(a is b)  # True（同一物件）

a = 257
b = 257
print(a is b)  # False（不同物件）

# 但在同一行的情況可能會被編譯器優化
a, b = 257, 257
print(a is b)  # True（編譯時優化）
```

### 字串駐留（String Interning）

簡單的字串會被自動駐留：

```python
a = "hello"
b = "hello"
print(a is b)  # True（駐留）

a = "hello world"
b = "hello world"
print(a is b)  # False（含空格，不駐留）

# 手動駐留
import sys
a = sys.intern("hello world")
b = sys.intern("hello world")
print(a is b)  # True
```

### 使用 ctypes 觀察記憶體

```python
import ctypes
import sys

def get_refcount(obj_id):
    """直接從記憶體讀取參考計數"""
    return ctypes.c_long.from_address(obj_id).value

a = [1, 2, 3]
obj_id = id(a)

print(f"sys.getrefcount: {sys.getrefcount(a)}")
print(f"ctypes 直接讀取: {get_refcount(obj_id)}")
# 注意：sys.getrefcount 會多 1（因為參數傳遞）
```

### 觀察物件大小

```python
import sys

# 基本物件大小
print(sys.getsizeof(None))      # 16
print(sys.getsizeof(True))      # 28
print(sys.getsizeof(0))         # 28
print(sys.getsizeof(1))         # 28
print(sys.getsizeof(10**100))   # 72（大整數）

# 容器大小（不包含元素）
print(sys.getsizeof([]))        # 56
print(sys.getsizeof([1, 2, 3])) # 88
print(sys.getsizeof({}))        # 64

# 注意：getsizeof 不遞迴計算
nested = [[1, 2], [3, 4]]
print(sys.getsizeof(nested))    # 只計算外層 list
```

---

## 【深入】PyTypeObject

### 型別物件的結構

每個型別（int、str、list 等）都是 `PyTypeObject` 的實例：

```c
// 簡化版
typedef struct _typeobject {
    PyObject_VAR_HEAD
    const char *tp_name;       // 型別名稱
    Py_ssize_t tp_basicsize;   // 基本大小
    Py_ssize_t tp_itemsize;    // 元素大小（變長物件）

    // 方法槽（slots）
    destructor tp_dealloc;     // 解構函式
    reprfunc tp_repr;          // __repr__
    hashfunc tp_hash;          // __hash__
    // ... 更多方法槽
} PyTypeObject;
```

### 在 Python 中觀察型別資訊

```python
# 型別的基本資訊
print(int.__name__)       # int
print(int.__basicsize__)  # 28（64-bit 系統）

# 方法解析順序
class A: pass
class B(A): pass
class C(B): pass

print(C.__mro__)
# (<class 'C'>, <class 'B'>, <class 'A'>, <class 'object'>)

# 型別的型別
print(type(int))    # <class 'type'>
print(type(type))   # <class 'type'>（type 是自己的實例）
```

### 為什麼 is 比 == 快？

```python
# is 只比較記憶體位址（一個指標比較）
# == 需要呼叫 __eq__ 方法（可能很複雜）

import timeit

a = [1, 2, 3]
b = a
c = [1, 2, 3]

# is 比較（非常快）
print(timeit.timeit('a is b', globals=globals(), number=1000000))
# 約 0.02 秒

# == 比較（需要比較內容）
print(timeit.timeit('a == c', globals=globals(), number=1000000))
# 約 0.05 秒
```

---

## 【實戰】效能影響

### 避免不必要的物件建立

```python
# 不好：每次迭代都建立新的 tuple
for i in range(1000):
    point = (i, i * 2)

# 好：如果結構固定，考慮使用 __slots__ 的類別
class Point:
    __slots__ = ['x', 'y']
    def __init__(self, x, y):
        self.x = x
        self.y = y

# 或者使用 namedtuple
from collections import namedtuple
Point = namedtuple('Point', ['x', 'y'])
```

### 使用物件池

```python
# 對於頻繁建立的小物件，考慮重複使用
class ObjectPool:
    def __init__(self, factory, max_size=100):
        self._factory = factory
        self._pool = []
        self._max_size = max_size

    def acquire(self):
        if self._pool:
            return self._pool.pop()
        return self._factory()

    def release(self, obj):
        if len(self._pool) < self._max_size:
            self._pool.append(obj)

# 使用
pool = ObjectPool(list)
lst = pool.acquire()
lst.extend([1, 2, 3])
# 使用完畢
lst.clear()
pool.release(lst)
```

---

## 思考題

1. 為什麼 CPython 選擇 -5 到 256 作為小整數快取的範圍？
2. 如果參考計數是 Python 物件的核心，那多執行緒時會發生什麼問題？
3. `None` 是單例，這是如何實現的？

## 實作練習

1. 寫一個函式，計算一個巢狀資料結構的「真實」記憶體使用量
2. 使用 `ctypes` 觀察 list 物件的內部結構
3. 實驗不同大小的整數的 `is` 行為

## 延伸閱讀

- [CPython Source - object.h](https://github.com/python/cpython/blob/main/Include/object.h)
- [Real Python - Python Memory Management](https://realpython.com/python-memory-management/)

---

*下一章：[記憶體管理與垃圾回收](../memory-gc/)*
