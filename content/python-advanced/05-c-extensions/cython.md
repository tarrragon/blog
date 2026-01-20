---
title: "4.2 Cython：Python 語法的 C 速度"
date: 2026-01-20
description: "使用 Cython 加速 Python 程式碼"
weight: 2
---

# Cython：Python 語法的 C 速度

本章介紹 Cython，一種 Python 的超集語言，可以編譯成 C 程式碼。

## 本章目標

學完本章後，你將能夠：

1. 理解 Cython 的編譯流程
2. 使用型別宣告加速程式碼
3. 使用 Cython 包裝 C 函式庫

---

## 【原理層】Cython 是什麼？

### Python 的超集

Cython 是一種程式語言，它是 Python 的超集：

```text
合法的 Python 程式碼 → 合法的 Cython 程式碼
                    → 但 Cython 可以加入更多語法

Cython 特有語法：
- cdef：宣告 C 變數或函式
- cpdef：同時暴露給 Python 和 C
- cimport：匯入 .pxd 檔案
- nogil：標記不需要 GIL 的區塊
```

### 編譯流程

```text
.pyx (Cython 原始碼)
    │
    ↓ Cython 編譯器
.c (C 原始碼)
    │
    ↓ C 編譯器 (gcc, clang, MSVC)
.so / .pyd (Python 擴展模組)
    │
    ↓ import
Python 程式
```

### 為什麼 Cython 比 Python 快？

```python
# 純 Python：每次操作都是物件操作
def python_sum(n):
    total = 0           # 建立 int 物件
    for i in range(n):  # 建立 range 物件，迭代器
        total += i      # 呼叫 __add__，建立新物件
    return total

# Cython：可以使用原生 C 型別
def cython_sum(int n):
    cdef int total = 0  # C 的 int，不是 Python 物件
    cdef int i
    for i in range(n):  # 編譯成 C 的 for 迴圈
        total += i      # 單一 CPU 指令
    return total
```

效能差異的來源：

| 操作 | Python | Cython (有型別) |
|------|--------|-----------------|
| 變數存取 | dict 查找 | 直接記憶體存取 |
| 整數加法 | 物件方法呼叫 | CPU 指令 |
| 迴圈 | 迭代器協議 | C for 迴圈 |
| 函式呼叫 | 建立 frame 物件 | C 函式呼叫 |

---

## 【設計層】Cython 基礎語法

### 安裝與設定

```bash
pip install cython

# 檢查版本
python -c "import cython; print(cython.__version__)"
```

### 第一個 Cython 模組

建立 `example.pyx`：

```cython
# example.pyx

def say_hello(name):
    """純 Python 函式，也是合法的 Cython"""
    print(f"Hello, {name}!")

def compute_sum(int n):
    """加入型別宣告的函式"""
    cdef int i
    cdef long total = 0

    for i in range(n):
        total += i

    return total
```

建立 `setup.py`：

```python
# setup.py
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize("example.pyx"),
)
```

編譯與使用：

```bash
# 編譯
python setup.py build_ext --inplace

# 使用
python -c "import example; example.say_hello('Cython')"
```

### 變數宣告

```cython
# 型別宣告語法

# cdef：宣告 C 變數（只在 Cython 內部可見）
cdef int x = 10
cdef double y = 3.14
cdef char* s = "hello"

# 多個變數
cdef:
    int a, b, c
    double d = 0.0
    list my_list = []

# 型別推斷（Python 3 風格）
cdef int x = 10      # 明確宣告
x: cython.int = 10   # 註解風格（Pure Python 模式）
```

### 函式類型

```cython
# def：Python 函式，可從 Python 呼叫
def python_func(x, y):
    return x + y

# cdef：C 函式，只能從 Cython 呼叫，最快
cdef int c_func(int x, int y):
    return x + y

# cpdef：同時產生 Python 和 C 版本
cpdef int hybrid_func(int x, int y):
    return x + y

# 使用情境
def api_func(int n):
    """公開 API"""
    cdef int i
    cdef int total = 0
    for i in range(n):
        total = _helper(total, i)  # 呼叫 cdef 函式
    return total

cdef int _helper(int a, int b):
    """內部輔助函式，不暴露給 Python"""
    return a + b
```

### 型別轉換

```cython
# 隱式轉換
cdef int i = 10
cdef double d = i  # int → double，自動轉換

# 明確轉換
cdef double x = 3.14
cdef int y = <int>x  # 截斷為 3

# Python 物件與 C 型別
def convert_example(obj):
    cdef int c_int

    # Python int → C int
    c_int = <int>obj  # 可能 overflow

    # 安全轉換
    if isinstance(obj, int) and -2147483648 <= obj <= 2147483647:
        c_int = obj

    return c_int
```

---

## 【實作層】Cython 優化技巧

### 使用 cython -a 分析

```bash
# 產生帶註解的 HTML 報告
cython -a example.pyx
```

```text
HTML 報告的顏色含義：
├── 白色：純 C 程式碼，最快
├── 淺黃色：少量 Python API 呼叫
├── 深黃色：較多 Python 互動
└── 橙色/紅色：大量 Python 操作，需要優化
```

### 常見優化模式

```cython
# 優化前：大量黃色
def slow_function(data):
    total = 0
    for item in data:
        total += item * item
    return total

# 優化後：大部分白色
def fast_function(double[:] data):  # 型別化記憶體視圖
    cdef:
        int i
        int n = data.shape[0]
        double total = 0.0

    for i in range(n):
        total += data[i] * data[i]

    return total
```

### 停用邊界檢查

```cython
# 預設：有邊界檢查（安全但較慢）
cdef double[:] arr = some_array

# 停用檢查（確定安全時使用）
cimport cython

@cython.boundscheck(False)  # 停用邊界檢查
@cython.wraparound(False)   # 停用負數索引
def optimized_sum(double[:] arr):
    cdef int i
    cdef int n = arr.shape[0]
    cdef double total = 0.0

    for i in range(n):
        total += arr[i]

    return total

# 或者使用全域設定
# cython: boundscheck=False
# cython: wraparound=False
```

### 釋放 GIL

```cython
from cython.parallel import prange

# nogil：標記不需要 GIL 的區塊
cdef double compute_heavy(double x) nogil:
    """純 C 計算，不涉及 Python 物件"""
    cdef double result = 0.0
    cdef int i
    for i in range(1000):
        result += x * i
    return result

def parallel_compute(double[:] data):
    cdef int i
    cdef int n = data.shape[0]
    cdef double[:] results = np.zeros(n)

    # 使用 OpenMP 平行化
    with nogil:
        for i in prange(n):
            results[i] = compute_heavy(data[i])

    return np.asarray(results)
```

---

## 【實作層】與 NumPy 整合

### 記憶體視圖

```cython
import numpy as np
cimport numpy as cnp

# 型別化記憶體視圖（推薦）
def process_array(double[:, :] arr):
    """處理 2D double 陣列"""
    cdef int i, j
    cdef int rows = arr.shape[0]
    cdef int cols = arr.shape[1]
    cdef double total = 0.0

    for i in range(rows):
        for j in range(cols):
            total += arr[i, j]

    return total

# 使用
# import numpy as np
# data = np.random.rand(100, 100)
# result = process_array(data)
```

### 矩陣運算範例

```cython
# matrix_ops.pyx
import numpy as np
cimport numpy as cnp
cimport cython

@cython.boundscheck(False)
@cython.wraparound(False)
def matrix_multiply(double[:, :] A, double[:, :] B):
    """矩陣乘法 C = A @ B"""
    cdef int i, j, k
    cdef int m = A.shape[0]
    cdef int n = A.shape[1]
    cdef int p = B.shape[1]

    if B.shape[0] != n:
        raise ValueError("矩陣維度不匹配")

    cdef double[:, :] C = np.zeros((m, p), dtype=np.float64)

    for i in range(m):
        for j in range(p):
            for k in range(n):
                C[i, j] += A[i, k] * B[k, j]

    return np.asarray(C)

# 注意：這只是教學範例
# 實際應用應使用 numpy.dot 或 BLAS
```

### 效能比較

```python
import numpy as np
import timeit

# 假設已編譯 matrix_ops
# from matrix_ops import matrix_multiply

def benchmark():
    A = np.random.rand(100, 100)
    B = np.random.rand(100, 100)

    # NumPy（使用 BLAS）
    t1 = timeit.timeit(lambda: A @ B, number=100)

    # Cython（我們的實現）
    # t2 = timeit.timeit(lambda: matrix_multiply(A, B), number=100)

    # 純 Python
    def py_matmul(A, B):
        m, n = A.shape
        p = B.shape[1]
        C = [[0.0] * p for _ in range(m)]
        for i in range(m):
            for j in range(p):
                for k in range(n):
                    C[i][j] += A[i, k] * B[k, j]
        return C

    t3 = timeit.timeit(lambda: py_matmul(A, B), number=1)

    print(f"NumPy (BLAS):  {t1:.4f}s")
    # print(f"Cython:        {t2:.4f}s")
    print(f"Pure Python:   {t3:.4f}s (x1)")
```

---

## 【實作層】包裝 C 函式庫

### 宣告外部函式

```cython
# 宣告 C 標準函式庫函式
from libc.math cimport sqrt, sin, cos, pow
from libc.stdlib cimport malloc, free
from libc.string cimport memcpy, strlen

def compute_distance(double x1, double y1, double x2, double y2):
    """使用 C 的 sqrt"""
    cdef double dx = x2 - x1
    cdef double dy = y2 - y1
    return sqrt(dx * dx + dy * dy)
```

### 宣告自訂 C 函式庫

假設有 C 標頭檔 `mylib.h`：

```c
// mylib.h
typedef struct {
    double x, y, z;
} Vector3D;

double vector_length(Vector3D* v);
Vector3D vector_add(Vector3D* a, Vector3D* b);
```

建立 Cython 宣告檔 `mylib.pxd`：

```cython
# mylib.pxd
cdef extern from "mylib.h":
    ctypedef struct Vector3D:
        double x
        double y
        double z

    double vector_length(Vector3D* v)
    Vector3D vector_add(Vector3D* a, Vector3D* b)
```

使用宣告：

```cython
# mylib_wrapper.pyx
from mylib cimport Vector3D, vector_length, vector_add

cdef class PyVector3D:
    """Python 包裝類別"""
    cdef Vector3D _vec

    def __init__(self, double x, double y, double z):
        self._vec.x = x
        self._vec.y = y
        self._vec.z = z

    @property
    def x(self):
        return self._vec.x

    @property
    def y(self):
        return self._vec.y

    @property
    def z(self):
        return self._vec.z

    def length(self):
        return vector_length(&self._vec)

    def __add__(self, PyVector3D other):
        cdef Vector3D result = vector_add(&self._vec, &other._vec)
        return PyVector3D(result.x, result.y, result.z)

    def __repr__(self):
        return f"Vector3D({self.x}, {self.y}, {self.z})"
```

### 記憶體管理

```cython
from libc.stdlib cimport malloc, free

cdef class DynamicArray:
    """管理動態分配記憶體的範例"""
    cdef double* data
    cdef int size

    def __cinit__(self, int size):
        """C 層級初始化，保證在 __init__ 之前執行"""
        self.size = size
        self.data = <double*>malloc(size * sizeof(double))
        if self.data == NULL:
            raise MemoryError("無法分配記憶體")

    def __dealloc__(self):
        """C 層級解構，保證釋放記憶體"""
        if self.data != NULL:
            free(self.data)

    def __init__(self, int size):
        """Python 層級初始化"""
        cdef int i
        for i in range(self.size):
            self.data[i] = 0.0

    def __getitem__(self, int index):
        if index < 0 or index >= self.size:
            raise IndexError("索引超出範圍")
        return self.data[index]

    def __setitem__(self, int index, double value):
        if index < 0 or index >= self.size:
            raise IndexError("索引超出範圍")
        self.data[index] = value

    def __len__(self):
        return self.size
```

---

## 【進階】Pure Python 模式

### 使用型別註解

從 Cython 3.0 開始，支援純 Python 語法：

```python
# pure_example.py（純 Python 檔案）
import cython

@cython.cfunc
def c_function(x: cython.int, y: cython.int) -> cython.int:
    """等同於 cdef int c_function(int x, int y)"""
    return x + y

@cython.ccall
def hybrid_function(x: cython.int) -> cython.int:
    """等同於 cpdef int hybrid_function(int x)"""
    return c_function(x, x)

def public_api(n: cython.int) -> cython.long:
    """普通 Python 函式，但有型別最佳化"""
    total: cython.long = 0
    i: cython.int

    for i in range(n):
        total += hybrid_function(i)

    return total
```

### 優點

```text
Pure Python 模式的好處：
1. 不需要 .pyx 檔案，直接用 .py
2. IDE 支援更好（型別提示）
3. 可以同時作為 Python 和 Cython 使用
4. 測試更容易（不需編譯就能跑 Python）
```

---

## 【建構】現代化建構方式

### 使用 pyproject.toml

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0", "cython>=3.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-cython-package"
version = "0.1.0"

[tool.setuptools]
ext-modules = [
    {name = "my_module", sources = ["src/my_module.pyx"]}
]
```

### 使用 meson-python

```toml
# pyproject.toml
[build-system]
requires = ["meson-python", "cython"]
build-backend = "mesonpy"

[project]
name = "my-cython-package"
version = "0.1.0"
```

```meson
# meson.build
project('my-cython-package', 'cython')

py = import('python').find_installation()

py.extension_module(
    'my_module',
    'src/my_module.pyx',
    install: true
)
```

---

## 思考題

1. 為什麼 cdef 函式比 def 函式快？從呼叫協議的角度解釋。
2. 在什麼情況下，Cython 的效能提升最明顯？什麼情況下提升有限？
3. 如何決定哪些函式應該用 cdef、cpdef 還是 def？

## 實作練習

1. 將入門系列效能章節的 `is_prime` 函式用 Cython 改寫，比較效能差異
2. 使用 Cython 實現一個簡單的 LRU Cache，與 `functools.lru_cache` 比較效能
3. 包裝一個簡單的 C 函式庫（如 zlib）並在 Python 中使用

## 延伸閱讀

- [Cython 官方文件](https://cython.readthedocs.io/)
- [Cython 最佳實踐](https://cython.readthedocs.io/en/latest/src/userguide/numpy_tutorial.html)
- [Kurt Smith - Cython: A Guide for Python Programmers](https://www.oreilly.com/library/view/cython/9781491901731/)

---

*上一章：[ctypes 與 cffi](../ctypes-cffi/)*
*下一章：[pybind11](../pybind11/)*
