---
title: "3.3 Bytecode 與虛擬機"
date: 2026-01-20
description: "理解 Python 的執行過程"
weight: 3
---

# Bytecode 與虛擬機

Python 不是直接執行原始碼，而是先編譯成 bytecode，再由虛擬機執行。理解這個過程有助於優化程式碼效能。

## 先備知識

- [3.2 記憶體管理與垃圾回收](../memory-gc/)

## 本章目標

學完本章後，你將能夠：

1. 理解 Python 的編譯流程
2. 使用 `dis` 模組分析 bytecode
3. 從 bytecode 角度理解效能差異
4. 了解 Python 3.11+ 的效能優化

---

## 【原理層】Python 的執行流程

### 編譯與執行

```text
原始碼 (.py)
    │
    ▼
┌─────────────┐
│   詞法分析   │ ← 將原始碼分解成 tokens
│   (Lexer)   │
└─────────────┘
    │
    ▼
┌─────────────┐
│   語法分析   │ ← 建立抽象語法樹 (AST)
│   (Parser)  │
└─────────────┘
    │
    ▼
┌─────────────┐
│   編譯器    │ ← 將 AST 編譯成 bytecode
│  (Compiler) │
└─────────────┘
    │
    ▼
Bytecode (.pyc)
    │
    ▼
┌─────────────┐
│   虛擬機    │ ← 執行 bytecode
│    (VM)     │
└─────────────┘
    │
    ▼
  執行結果
```

### .pyc 檔案與 __pycache__

```python
# 當你 import 一個模組時，Python 會：
# 1. 檢查 __pycache__ 中是否有對應的 .pyc 檔案
# 2. 如果沒有或過期，重新編譯
# 3. 將編譯結果存入 __pycache__

# 檔案命名格式：
# module.cpython-312.pyc
# module.cpython-313.pyc

# 手動編譯
import py_compile
py_compile.compile('script.py')

# 編譯整個目錄
import compileall
compileall.compile_dir('my_package/')
```

### 程式碼物件（Code Object）

編譯後的 bytecode 儲存在程式碼物件中：

```python
def example(x, y):
    z = x + y
    return z * 2

code = example.__code__

print(code.co_name)       # example
print(code.co_varnames)   # ('x', 'y', 'z')
print(code.co_consts)     # (None, 2)
print(code.co_code)       # b'|\x00|\x01\x17\x00}\x02|\x02d\x01\x14\x00S\x00'
```

---

## 【設計層】Stack-based 虛擬機

### 工作原理

Python 虛擬機是 stack-based（堆疊式）：

```text
執行 x + y：

1. LOAD_FAST 0 (x)    Stack: [x]
2. LOAD_FAST 1 (y)    Stack: [x, y]
3. BINARY_ADD         Stack: [x+y]
```

```python
import dis

def add(x, y):
    return x + y

dis.dis(add)
# 輸出：
#   2           0 RESUME                   0
#
#   3           2 LOAD_FAST                0 (x)
#               4 LOAD_FAST                1 (y)
#               6 BINARY_OP                0 (+)
#              10 RETURN_VALUE
```

### 常見 Bytecode 指令

| 指令 | 說明 |
| ---- | ---- |
| LOAD_FAST | 載入區域變數 |
| LOAD_GLOBAL | 載入全域變數 |
| LOAD_CONST | 載入常數 |
| STORE_FAST | 儲存區域變數 |
| BINARY_OP | 二元運算 |
| CALL | 呼叫函式 |
| RETURN_VALUE | 返回值 |
| JUMP_FORWARD | 向前跳躍 |
| POP_JUMP_IF_FALSE | 條件跳躍 |

---

## 【實作層】使用 dis 模組

### 基本用法

```python
import dis

# 反組譯函式
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

dis.dis(factorial)
```

### 分析控制流程

```python
import dis

def loop_example():
    total = 0
    for i in range(10):
        total += i
    return total

dis.dis(loop_example)
# 可以看到 FOR_ITER、JUMP_BACKWARD 等指令
```

### 比較不同實現

```python
import dis

# 版本 1：使用迴圈
def sum_loop(n):
    total = 0
    for i in range(n):
        total += i
    return total

# 版本 2：使用內建函式
def sum_builtin(n):
    return sum(range(n))

print("=== 迴圈版本 ===")
dis.dis(sum_loop)

print("\n=== 內建函式版本 ===")
dis.dis(sum_builtin)

# 內建函式版本的 bytecode 更少，而且 sum() 是 C 實現
```

---

## 【效能】從 Bytecode 理解效能

### 為什麼區域變數比全域變數快？

```python
import dis

global_var = 10

def use_global():
    return global_var + 1

def use_local():
    local_var = 10
    return local_var + 1

dis.dis(use_global)
# LOAD_GLOBAL 0 (global_var)  ← 需要查找全域命名空間

dis.dis(use_local)
# LOAD_FAST 0 (local_var)     ← 直接用索引存取
```

```text
LOAD_GLOBAL: 需要在 globals() dict 中查找
LOAD_FAST:   直接用索引存取陣列（O(1)）
```

### 為什麼 list comprehension 比 for 迴圈快？

```python
import dis

def for_loop():
    result = []
    for i in range(100):
        result.append(i * 2)
    return result

def list_comp():
    return [i * 2 for i in range(100)]

dis.dis(for_loop)
# 更多指令，包括 LOAD_METHOD (append)、CALL

dis.dis(list_comp)
# 使用特殊的 LIST_APPEND 指令，更高效
```

### 字串連接的效能

```python
import dis

def concat_plus():
    s = ""
    for i in range(10):
        s = s + str(i)
    return s

def concat_join():
    return "".join(str(i) for i in range(10))

# plus 版本每次都建立新字串
# join 版本一次性建立
```

---

## 【深入】Python 3.11+ 的優化

### Specializing Adaptive Interpreter

Python 3.11 引入了自適應特化直譯器：

```python
# 針對常見模式進行優化
# 例如：如果一個函式總是接收 int 參數

def add(a, b):
    return a + b

# 前幾次呼叫：使用通用的 BINARY_OP
# 多次呼叫後：特化為 BINARY_OP_ADD_INT
```

### 查看特化指令

```python
import dis

def example():
    x = 1
    y = 2
    return x + y

# 使用 adaptive=True 查看特化指令
dis.dis(example, adaptive=True)
```

### 內聯快取（Inline Caching）

```python
# Python 3.11+ 在 bytecode 中包含快取空間
# 用於儲存運行時資訊

def get_attr(obj):
    return obj.value

# 第一次呼叫：查找 'value' 屬性
# 之後：使用快取的位置資訊
```

---

## 【實戰】效能調校

### 使用 bytecode 分析熱點

```python
import dis
import timeit

def version_a(data):
    total = 0
    for item in data:
        total = total + item
    return total

def version_b(data):
    total = 0
    for item in data:
        total += item
    return total

# 比較 bytecode
print("=== version_a ===")
dis.dis(version_a)
print("\n=== version_b ===")
dis.dis(version_b)

# 實際測量
data = list(range(1000))
print(timeit.timeit(lambda: version_a(data), number=10000))
print(timeit.timeit(lambda: version_b(data), number=10000))
# 結果相近，因為 total = total + item 和 total += item
# 在 Python 中編譯成相同的 bytecode
```

### 避免不必要的屬性查找

```python
import dis

class MyClass:
    def __init__(self):
        self.value = 0

    def slow_method(self):
        for i in range(100):
            self.value += i  # 每次都要查找 self.value

    def fast_method(self):
        value = self.value  # 快取到區域變數
        for i in range(100):
            value += i
        self.value = value

dis.dis(MyClass.slow_method)
# 迴圈內有 LOAD_FAST (self) + LOAD_ATTR (value)

dis.dis(MyClass.fast_method)
# 迴圈內只有 LOAD_FAST (value)
```

### 使用 __slots__ 加速屬性存取

```python
import dis

class WithoutSlots:
    def __init__(self, x):
        self.x = x

class WithSlots:
    __slots__ = ['x']
    def __init__(self, x):
        self.x = x

def access_without_slots(obj):
    return obj.x

def access_with_slots(obj):
    return obj.x

# bytecode 相同，但運行時 __slots__ 更快
# 因為不需要查找 __dict__
```

---

## 【參考】完整 Bytecode 列表

Python 3.12 的主要指令類別：

```text
載入指令：
  LOAD_CONST, LOAD_FAST, LOAD_GLOBAL, LOAD_NAME, LOAD_ATTR

儲存指令：
  STORE_FAST, STORE_GLOBAL, STORE_NAME, STORE_ATTR

運算指令：
  BINARY_OP, UNARY_NEGATIVE, UNARY_NOT

跳躍指令：
  JUMP_FORWARD, JUMP_BACKWARD, POP_JUMP_IF_TRUE, POP_JUMP_IF_FALSE

函式相關：
  CALL, RETURN_VALUE, PUSH_NULL

迭代相關：
  GET_ITER, FOR_ITER

容器相關：
  BUILD_LIST, BUILD_TUPLE, BUILD_MAP, LIST_APPEND
```

---

## 思考題

1. 為什麼 Python 選擇 stack-based VM 而不是 register-based VM？
2. `.pyc` 檔案可以跨平台使用嗎？為什麼？
3. JIT 編譯器（如 PyPy）與 CPython 的直譯器有什麼根本差異？

## 實作練習

1. 使用 `dis` 比較 `map()` 和 list comprehension 的 bytecode
2. 寫一個簡單的 bytecode 分析工具，計算指令數量
3. 研究 Python 3.11 和 3.12 的 bytecode 變化

## 延伸閱讀

- [Python 官方 - dis 模組](https://docs.python.org/3/library/dis.html)
- [Python 3.11 What's New - Faster CPython](https://docs.python.org/3/whatsnew/3.11.html#faster-cpython)
- [Inside The Python Virtual Machine](https://leanpub.com/insidethepythonvirtualmachine/read)

---

*上一章：[記憶體管理與垃圾回收](../memory-gc/)*
*下一章：[GIL 與執行緒模型](../gil-threading/)*
