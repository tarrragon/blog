---
title: "3.2 記憶體管理與垃圾回收"
date: 2026-01-20
description: "理解 Python 的記憶體管理機制"
weight: 2
---

# 記憶體管理與垃圾回收

Python 的記憶體管理結合了參考計數和分代垃圾回收。理解這些機制有助於寫出更高效的程式碼。

## 先備知識

- [3.1 PyObject 與物件模型](../object-model/)

## 本章目標

學完本章後，你將能夠：

1. 理解參考計數的限制
2. 理解分代垃圾回收的原理
3. 使用 `__slots__` 優化記憶體
4. 使用 `tracemalloc` 分析記憶體使用

---

## 【原理層】記憶體模型

### Stack vs Heap

Python 的記憶體分為兩個主要區域：

```text
┌─────────────────────────────────────┐
│              Stack                   │
│  ┌─────────────────────────────────┐│
│  │ 變數名稱 → 指向 Heap 的指標      ││
│  │ a ──────→ [指標]                ││
│  │ b ──────→ [指標]                ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│              Heap                    │
│  ┌─────────────────────────────────┐│
│  │ PyObject: [1, 2, 3]             ││
│  │ PyObject: "hello"               ││
│  │ PyObject: 42                    ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

- **Stack**：儲存變數名稱和指標（參考）
- **Heap**：儲存實際的 Python 物件

### Python 的記憶體分配器

CPython 使用分層的記憶體分配器：

```text
┌─────────────────────────────────────┐
│     Python 物件分配器               │
│     (PyObject_Malloc)               │
├─────────────────────────────────────┤
│     Python 記憶體分配器             │
│     (PyMem_Malloc)                  │
├─────────────────────────────────────┤
│     C 標準函式庫                    │
│     (malloc)                        │
├─────────────────────────────────────┤
│     作業系統                        │
└─────────────────────────────────────┘
```

對於小於 512 bytes 的物件，Python 使用自己的分配器來減少系統呼叫。

---

## 【設計層】循環參考問題

### 參考計數的限制

參考計數無法處理循環參考：

```python
import gc

class Node:
    def __init__(self, name):
        self.name = name
        self.ref = None

# 建立循環參考
a = Node("A")
b = Node("B")
a.ref = b
b.ref = a

# 刪除外部參考
del a
del b

# 此時 A 和 B 仍互相參考，參考計數都是 1
# 但它們已經無法被存取了（垃圾）
```

```text
刪除前：
外部 ─→ A ←──→ B ←─ 外部
        refcnt=2  refcnt=2

刪除後：
        A ←──→ B
        refcnt=1  refcnt=1
        （無法被存取，但參考計數不為 0）
```

### 分代垃圾回收

為了解決循環參考，Python 使用分代垃圾回收：

```python
import gc

# 查看 GC 統計
print(gc.get_count())  # (700, 10, 0) - 各代的物件數

# 三個世代（Python 3.12 以前）
# Generation 0: 新物件
# Generation 1: 存活過一次 GC 的物件
# Generation 2: 存活過多次 GC 的物件

# Python 3.12+ 改為四個世代
# Young generation (1 代)
# Old generations (2 代)
# Permanent generation (永久)
```

### GC 觸發時機

```python
import gc

# 查看閾值
print(gc.get_threshold())  # (700, 10, 10)

# 意義：
# - 當 Generation 0 有 700 個物件時，觸發 Gen 0 GC
# - 當 Gen 0 GC 執行 10 次後，觸發 Gen 1 GC
# - 當 Gen 1 GC 執行 10 次後，觸發 Gen 2 GC

# 手動觸發 GC
gc.collect()

# 設定閾值
gc.set_threshold(1000, 15, 15)
```

---

## 【實作層】記憶體優化

### 使用 __slots__

`__slots__` 可以顯著減少物件的記憶體使用：

```python
import sys

class WithoutSlots:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class WithSlots:
    __slots__ = ['x', 'y']

    def __init__(self, x, y):
        self.x = x
        self.y = y

obj1 = WithoutSlots(1, 2)
obj2 = WithSlots(1, 2)

print(sys.getsizeof(obj1))  # 48
print(sys.getsizeof(obj2))  # 48（但沒有 __dict__）

# 實際差異在 __dict__
print(sys.getsizeof(obj1.__dict__))  # 104
# obj2 沒有 __dict__
```

**為什麼 `__slots__` 省記憶體？**

```text
沒有 __slots__：
┌─────────────────────────┐
│ PyObject header (16 B)  │
│ __dict__ 指標 (8 B)      │
│ __weakref__ 指標 (8 B)   │
│ __dict__ → { 'x': 1,    │
│              'y': 2 }   │
│            （額外 100+ B）│
└─────────────────────────┘

有 __slots__：
┌─────────────────────────┐
│ PyObject header (16 B)  │
│ x (8 B)                 │
│ y (8 B)                 │
└─────────────────────────┘
```

### __slots__ 的限制

```python
class Base:
    __slots__ = ['x']

class Derived(Base):
    __slots__ = ['y']  # 不能與父類別重複

    def __init__(self):
        self.x = 1
        self.y = 2
        # self.z = 3  # 錯誤！沒有 __dict__

# 如果需要動態屬性，加入 '__dict__'
class Flexible:
    __slots__ = ['x', '__dict__']
```

### 使用弱參考

弱參考不增加參考計數，適合用於快取：

```python
import weakref

class ExpensiveObject:
    def __init__(self, value):
        self.value = value

# 建立物件和弱參考
obj = ExpensiveObject(42)
weak_ref = weakref.ref(obj)

print(weak_ref())  # <ExpensiveObject object>
print(weak_ref().value)  # 42

# 刪除強參考
del obj

print(weak_ref())  # None（物件已被回收）
```

**使用 WeakValueDictionary 實作快取：**

```python
import weakref

class Cache:
    def __init__(self):
        self._cache = weakref.WeakValueDictionary()

    def get(self, key, factory):
        value = self._cache.get(key)
        if value is None:
            value = factory()
            self._cache[key] = value
        return value

cache = Cache()

def create_expensive():
    return ExpensiveObject(100)

obj = cache.get('key1', create_expensive)
# 當 obj 不再被使用時，快取會自動清理
```

---

## 【實作層】記憶體分析工具

### 使用 tracemalloc

```python
import tracemalloc

# 開始追蹤
tracemalloc.start()

# 執行程式碼
data = [i ** 2 for i in range(10000)]
more_data = {str(i): i for i in range(10000)}

# 取得記憶體快照
snapshot = tracemalloc.take_snapshot()

# 顯示前 10 個記憶體使用最多的位置
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)

# 比較兩個快照
tracemalloc.start()
snapshot1 = tracemalloc.take_snapshot()

# 執行更多程式碼
big_list = list(range(100000))

snapshot2 = tracemalloc.take_snapshot()
diff = snapshot2.compare_to(snapshot1, 'lineno')

for stat in diff[:5]:
    print(stat)
```

### 使用 gc 模組除錯

```python
import gc

# 啟用除錯
gc.set_debug(gc.DEBUG_LEAK)

# 找出無法回收的物件
gc.collect()
print(gc.garbage)  # 無法回收的物件列表

# 取得所有被追蹤的物件
all_objects = gc.get_objects()
print(f"被追蹤的物件數量: {len(all_objects)}")

# 找出特定類別的實例
class MyClass:
    pass

instances = [obj for obj in gc.get_objects() if isinstance(obj, MyClass)]
print(f"MyClass 實例數量: {len(instances)}")
```

### 檢測記憶體洩漏

```python
import gc
import tracemalloc

def find_memory_leak():
    tracemalloc.start()

    # 記錄初始狀態
    gc.collect()
    snapshot1 = tracemalloc.take_snapshot()

    # 執行可能洩漏的程式碼
    for _ in range(1000):
        suspicious_function()

    # 記錄最終狀態
    gc.collect()
    snapshot2 = tracemalloc.take_snapshot()

    # 比較
    diff = snapshot2.compare_to(snapshot1, 'lineno')

    print("記憶體增長最多的位置：")
    for stat in diff[:10]:
        print(stat)
```

---

## 【實戰】常見記憶體問題

### 問題 1：大量小物件

```python
# 不好：建立大量小物件
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

points = [Point(i, i) for i in range(1000000)]

# 好：使用 __slots__
class Point:
    __slots__ = ['x', 'y']
    def __init__(self, x, y):
        self.x = x
        self.y = y

# 更好：使用 NumPy（如果是數值資料）
import numpy as np
points = np.zeros((1000000, 2))
```

### 問題 2：循環參考

```python
# 不好：物件間的循環參考
class Parent:
    def __init__(self):
        self.children = []

class Child:
    def __init__(self, parent):
        self.parent = parent
        parent.children.append(self)

# 好：使用弱參考
import weakref

class Child:
    def __init__(self, parent):
        self.parent = weakref.ref(parent)
        parent.children.append(self)
```

### 問題 3：全域變數累積

```python
# 不好：全域快取無限增長
_cache = {}

def process(key, value):
    if key not in _cache:
        _cache[key] = expensive_compute(value)
    return _cache[key]

# 好：使用 LRU cache
from functools import lru_cache

@lru_cache(maxsize=1000)
def process(key, value):
    return expensive_compute(value)
```

---

## 思考題

1. 為什麼 Python 需要同時使用參考計數和垃圾回收？只用其中一種不行嗎？
2. `__slots__` 為什麼不能用於繼承自內建型別的類別？
3. 在什麼情況下應該手動呼叫 `gc.collect()`？

## 實作練習

1. 使用 `tracemalloc` 分析一個現有程式的記憶體使用
2. 將一個使用大量物件的程式改用 `__slots__` 優化
3. 使用 `WeakValueDictionary` 實作一個自動清理的快取

## 延伸閱讀

- [Python 官方 - gc 模組](https://docs.python.org/3/library/gc.html)
- [Python 官方 - tracemalloc 模組](https://docs.python.org/3/library/tracemalloc.html)
- [Coding Confessions - CPython GC Internals](https://blog.codingconfessions.com/p/cpython-garbage-collection-internals)

---

*上一章：[PyObject 與物件模型](../object-model/)*
*下一章：[Bytecode 與虛擬機](../bytecode/)*
