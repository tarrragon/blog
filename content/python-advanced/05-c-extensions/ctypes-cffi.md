---
title: "4.1 ctypes 與 cffi：動態綁定"
description: "使用 ctypes 和 cffi 呼叫 C 函式庫"
weight: 1
---

# ctypes 與 cffi：動態綁定

本章介紹如何使用 ctypes 和 cffi 動態載入和呼叫 C 函式庫。

## 本章目標

學完本章後，你將能夠：

1. 理解 FFI（Foreign Function Interface）的概念
2. 使用 ctypes 呼叫系統函式庫
3. 使用 cffi 的 ABI 和 API 模式

---

## 【原理層】什麼是 FFI？

### 動態連結庫

現代作業系統使用動態連結庫（Shared Library）來共享程式碼：

```text
不同平台的動態連結庫：
├── Linux:   .so  (Shared Object)
├── macOS:   .dylib (Dynamic Library)
└── Windows: .dll (Dynamic Link Library)

優點：
- 節省記憶體（多個程式共享同一份）
- 更新方便（不需重新編譯主程式）
- 模組化設計
```

### FFI 的概念

FFI（Foreign Function Interface）是一種讓程式語言呼叫其他語言函式的機制：

```text
Python 程式
    │
    ↓ FFI
┌───────────────┐
│  C 函式庫     │
│  - libc.so    │
│  - libm.so    │
│  - 自訂 .so   │
└───────────────┘
```

### ctypes vs cffi

| 特性 | ctypes | cffi |
|------|--------|------|
| 來源 | 標準庫 | 第三方 |
| 設計 | 物件導向 API | C 語法描述 |
| 效能 | 較慢 | 較快（API 模式） |
| 學習曲線 | 較平緩 | 需要 C 語法知識 |
| PyPy 支援 | 有限 | 完整 |

---

## 【設計層】ctypes 基礎

### 載入動態連結庫

```python
import ctypes
import ctypes.util

# 方法 1：直接載入
# Linux/macOS
libc = ctypes.CDLL("libc.so.6")  # Linux
libc = ctypes.CDLL("libc.dylib")  # macOS

# Windows
msvcrt = ctypes.CDLL("msvcrt")

# 方法 2：使用 find_library（推薦，跨平台）
from ctypes.util import find_library

libc_path = find_library("c")
print(f"libc 路徑: {libc_path}")
libc = ctypes.CDLL(libc_path)

# 方法 3：載入自訂函式庫
mylib = ctypes.CDLL("./mylib.so")
```

### C 型別對應

```python
import ctypes

# 基本型別對應
"""
C 型別           ctypes 型別        Python 型別
─────────────────────────────────────────────────
char             c_char            bytes (長度 1)
wchar_t          c_wchar           str (長度 1)
char *           c_char_p          bytes 或 None
wchar_t *        c_wchar_p         str 或 None
int              c_int             int
unsigned int     c_uint            int
long             c_long            int
unsigned long    c_ulong           int
long long        c_longlong        int
float            c_float           float
double           c_double          float
void *           c_void_p          int 或 None
"""

# 範例：設定函式的參數和回傳型別
libc = ctypes.CDLL(ctypes.util.find_library("c"))

# strlen 函式：size_t strlen(const char *s)
libc.strlen.argtypes = [ctypes.c_char_p]
libc.strlen.restype = ctypes.c_size_t

result = libc.strlen(b"Hello, World!")
print(f"字串長度: {result}")  # 13
```

### 指標操作

```python
import ctypes

# 建立指標
x = ctypes.c_int(42)
ptr = ctypes.pointer(x)  # 指向 x 的指標

print(f"值: {ptr.contents.value}")  # 42

# 修改值
ptr.contents.value = 100
print(f"新值: {x.value}")  # 100

# 指標型別
IntPtr = ctypes.POINTER(ctypes.c_int)

# 空指標
null_ptr = IntPtr()
print(f"是否為空: {not null_ptr}")  # True

# byref：輕量級的指標傳遞（不建立完整指標物件）
def example_with_byref():
    value = ctypes.c_int(0)
    # 假設某函式需要 int* 參數
    # some_func(ctypes.byref(value))
    return value.value
```

### 結構體與聯合

```python
import ctypes

# 定義結構體
class Point(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
    ]

# 使用結構體
p = Point(3.0, 4.0)
print(f"Point: ({p.x}, {p.y})")

# 巢狀結構體
class Rectangle(ctypes.Structure):
    _fields_ = [
        ("top_left", Point),
        ("bottom_right", Point),
    ]

rect = Rectangle(Point(0, 0), Point(10, 10))
print(f"矩形: ({rect.top_left.x}, {rect.top_left.y}) -> "
      f"({rect.bottom_right.x}, {rect.bottom_right.y})")

# 陣列
IntArray5 = ctypes.c_int * 5
arr = IntArray5(1, 2, 3, 4, 5)
print(f"陣列: {list(arr)}")

# 聯合（Union）
class IntOrFloat(ctypes.Union):
    _fields_ = [
        ("i", ctypes.c_int),
        ("f", ctypes.c_float),
    ]

u = IntOrFloat()
u.f = 3.14
print(f"作為 float: {u.f}")
print(f"作為 int: {u.i}")  # 記憶體的整數解釋
```

---

## 【實作層】ctypes 實戰

### 呼叫系統 API

```python
import ctypes
import ctypes.util
import os

# 取得 process ID（跨平台範例）
if os.name == 'posix':
    libc = ctypes.CDLL(ctypes.util.find_library("c"))

    # pid_t getpid(void)
    libc.getpid.restype = ctypes.c_int
    pid = libc.getpid()
    print(f"PID (ctypes): {pid}")
    print(f"PID (os): {os.getpid()}")

# 呼叫數學函式
libm = ctypes.CDLL(ctypes.util.find_library("m"))

# double sqrt(double x)
libm.sqrt.argtypes = [ctypes.c_double]
libm.sqrt.restype = ctypes.c_double

result = libm.sqrt(2.0)
print(f"sqrt(2) = {result}")
```

### 回呼函式

```python
import ctypes

# 定義回呼函式型別
# qsort 的比較函式：int (*compar)(const void *, const void *)
CMPFUNC = ctypes.CFUNCTYPE(
    ctypes.c_int,      # 回傳型別
    ctypes.c_void_p,   # 參數 1
    ctypes.c_void_p    # 參數 2
)

def py_compare(a, b):
    """Python 比較函式"""
    # 將 void* 轉換為 int*
    a_val = ctypes.cast(a, ctypes.POINTER(ctypes.c_int)).contents.value
    b_val = ctypes.cast(b, ctypes.POINTER(ctypes.c_int)).contents.value
    return a_val - b_val

# 包裝為 C 回呼
c_compare = CMPFUNC(py_compare)

# 使用 qsort
libc = ctypes.CDLL(ctypes.util.find_library("c"))

# void qsort(void *base, size_t nmemb, size_t size,
#            int (*compar)(const void *, const void *))
IntArray = ctypes.c_int * 5
arr = IntArray(5, 2, 8, 1, 9)

print(f"排序前: {list(arr)}")

libc.qsort(
    arr,                          # base
    len(arr),                     # nmemb
    ctypes.sizeof(ctypes.c_int),  # size
    c_compare                     # compar
)

print(f"排序後: {list(arr)}")
```

### 處理字串

```python
import ctypes

libc = ctypes.CDLL(ctypes.util.find_library("c"))

# 注意：Python 3 的字串是 unicode
# ctypes 的 c_char_p 需要 bytes

# 錯誤示範
# libc.strlen("Hello")  # TypeError

# 正確做法
result = libc.strlen(b"Hello")
print(f"長度: {result}")

# 建立可修改的字串緩衝區
buffer = ctypes.create_string_buffer(b"Hello", 20)
print(f"原始: {buffer.value}")

# strcpy：複製字串
libc.strcpy(buffer, b"World")
print(f"複製後: {buffer.value}")

# 處理 wchar_t（寬字元）
# wchar_t *wcscat(wchar_t *dest, const wchar_t *src)
if hasattr(libc, 'wcscat'):
    wbuffer = ctypes.create_unicode_buffer("Hello, ", 50)
    libc.wcscat(wbuffer, "World!")
    print(f"寬字串: {wbuffer.value}")
```

---

## 【設計層】cffi 基礎

### 安裝與基本使用

```bash
pip install cffi
```

```python
from cffi import FFI

ffi = FFI()

# ABI 模式：動態載入，不需編譯
ffi.cdef("""
    int strlen(const char *s);
    double sqrt(double x);
""")

# 載入函式庫
libc = ffi.dlopen(None)  # None = 載入預設 C 函式庫

# 呼叫函式
result = libc.strlen(b"Hello, cffi!")
print(f"strlen: {result}")
```

### ABI 模式 vs API 模式

```python
from cffi import FFI

# ========== ABI 模式 ==========
# 優點：簡單，不需編譯器
# 缺點：效能較差，型別檢查較弱

ffi_abi = FFI()
ffi_abi.cdef("""
    double sin(double x);
    double cos(double x);
""")
libm = ffi_abi.dlopen("m")  # 或 None 使用預設

import math
print(f"sin(π/2) = {libm.sin(math.pi / 2)}")

# ========== API 模式 ==========
# 優點：效能好，完整型別檢查
# 缺點：需要編譯器

ffi_api = FFI()
ffi_api.cdef("""
    double compute_something(double x, double y);
""")

# 設定原始碼（會編譯成擴展模組）
ffi_api.set_source("_example",
    """
    double compute_something(double x, double y) {
        return x * x + y * y;
    }
    """,
)

# 編譯（通常在 setup.py 中執行）
# ffi_api.compile()
```

### cffi 的型別系統

```python
from cffi import FFI

ffi = FFI()

# 定義結構體
ffi.cdef("""
    typedef struct {
        double x;
        double y;
    } Point;

    typedef struct {
        Point center;
        double radius;
    } Circle;
""")

# 建立結構體實例
point = ffi.new("Point *")
point.x = 3.0
point.y = 4.0

# 或者一次初始化
point2 = ffi.new("Point *", {'x': 1.0, 'y': 2.0})

# 巢狀結構體
circle = ffi.new("Circle *", {
    'center': {'x': 0.0, 'y': 0.0},
    'radius': 5.0
})

print(f"圓心: ({circle.center.x}, {circle.center.y})")
print(f"半徑: {circle.radius}")

# 陣列
arr = ffi.new("int[5]", [1, 2, 3, 4, 5])
print(f"陣列: {list(arr)}")

# 動態大小陣列
n = 10
dynamic_arr = ffi.new(f"double[{n}]")
for i in range(n):
    dynamic_arr[i] = i * 0.5
```

---

## 【實作層】cffi 實戰

### 包裝簡單的 C 函式庫

假設我們有一個簡單的 C 函式庫 `mathutil.c`：

```c
// mathutil.c
#include <math.h>

double vector_length(double x, double y, double z) {
    return sqrt(x*x + y*y + z*z);
}

int fibonacci(int n) {
    if (n <= 1) return n;
    int a = 0, b = 1;
    for (int i = 2; i <= n; i++) {
        int tmp = a + b;
        a = b;
        b = tmp;
    }
    return b;
}
```

使用 cffi 包裝：

```python
# build_mathutil.py
from cffi import FFI

ffi = FFI()

# 宣告要使用的函式
ffi.cdef("""
    double vector_length(double x, double y, double z);
    int fibonacci(int n);
""")

# 設定原始碼
ffi.set_source(
    "_mathutil",  # 模組名稱
    """
    #include <math.h>

    double vector_length(double x, double y, double z) {
        return sqrt(x*x + y*y + z*z);
    }

    int fibonacci(int n) {
        if (n <= 1) return n;
        int a = 0, b = 1;
        for (int i = 2; i <= n; i++) {
            int tmp = a + b;
            a = b;
            b = tmp;
        }
        return b;
    }
    """,
    libraries=['m'],  # 連結數學函式庫
)

if __name__ == "__main__":
    ffi.compile(verbose=True)
```

```python
# 使用編譯後的模組
from _mathutil import ffi, lib

length = lib.vector_length(1.0, 2.0, 2.0)
print(f"向量長度: {length}")  # 3.0

fib_10 = lib.fibonacci(10)
print(f"fibonacci(10): {fib_10}")  # 55
```

### 回呼函式

```python
from cffi import FFI

ffi = FFI()

ffi.cdef("""
    typedef int (*compare_func)(int, int);
    void custom_sort(int *arr, int size, compare_func cmp);
""")

ffi.set_source("_sort_example",
    """
    typedef int (*compare_func)(int, int);

    void custom_sort(int *arr, int size, compare_func cmp) {
        // 簡單的冒泡排序
        for (int i = 0; i < size - 1; i++) {
            for (int j = 0; j < size - i - 1; j++) {
                if (cmp(arr[j], arr[j+1]) > 0) {
                    int tmp = arr[j];
                    arr[j] = arr[j+1];
                    arr[j+1] = tmp;
                }
            }
        }
    }
    """
)

# 編譯後使用
# from _sort_example import ffi, lib

# @ffi.callback("int(int, int)")
# def py_compare(a, b):
#     return a - b

# arr = ffi.new("int[5]", [5, 2, 8, 1, 9])
# lib.custom_sort(arr, 5, py_compare)
# print(list(arr))  # [1, 2, 5, 8, 9]
```

### 記憶體管理

```python
from cffi import FFI

ffi = FFI()

# ffi.new() 分配的記憶體會自動管理
data = ffi.new("int[100]")  # 自動回收

# 需要手動管理的情況
ffi.cdef("""
    void *malloc(size_t size);
    void free(void *ptr);
""")

libc = ffi.dlopen(None)

# 手動分配
ptr = libc.malloc(100)
if ptr != ffi.NULL:
    # 使用記憶體...

    # 必須手動釋放
    libc.free(ptr)

# 使用 ffi.gc() 自動管理外部分配的記憶體
def auto_managed_alloc(size):
    ptr = libc.malloc(size)
    if ptr == ffi.NULL:
        raise MemoryError()
    # 設定 finalizer，當 Python 物件被回收時自動呼叫
    return ffi.gc(ptr, libc.free)

managed_ptr = auto_managed_alloc(100)
# 不需要手動 free，Python GC 會處理
```

---

## 【選擇指南】ctypes vs cffi

### 決策流程

```text
需要呼叫 C 函式庫？
│
├── 只需要簡單呼叫系統 API
│   └── ctypes（標準庫，不需額外安裝）
│
├── 需要包裝複雜的 C 函式庫
│   └── cffi API 模式（更好的型別檢查）
│
├── 在 PyPy 上執行
│   └── cffi（PyPy 原生支援）
│
└── 效能要求高
    └── cffi API 模式 或 考慮 Cython/pybind11
```

### 效能比較

```python
import timeit

# 測試函式呼叫開銷
setup_ctypes = """
import ctypes
import ctypes.util
libm = ctypes.CDLL(ctypes.util.find_library("m"))
libm.sqrt.argtypes = [ctypes.c_double]
libm.sqrt.restype = ctypes.c_double
"""

setup_cffi = """
from cffi import FFI
ffi = FFI()
ffi.cdef("double sqrt(double x);")
libm = ffi.dlopen("m")
"""

# 結果（僅供參考，實際數據取決於環境）
# ctypes: ~0.3 μs per call
# cffi ABI: ~0.2 μs per call
# cffi API: ~0.05 μs per call
# 原生 Python math.sqrt: ~0.02 μs per call
```

### 常見錯誤與除錯

```python
import ctypes

# 錯誤 1：忘記設定 argtypes/restype
libc = ctypes.CDLL(ctypes.util.find_library("c"))
# result = libc.strlen("hello")  # 可能 crash 或回傳錯誤值

# 正確做法
libc.strlen.argtypes = [ctypes.c_char_p]
libc.strlen.restype = ctypes.c_size_t
result = libc.strlen(b"hello")

# 錯誤 2：傳遞 Python str 而非 bytes
# libc.strlen("hello")  # TypeError

# 錯誤 3：回呼函式被垃圾回收
CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int)

def bad_example():
    def callback(x):
        return x * 2

    c_callback = CALLBACK(callback)
    # 如果這裡把 c_callback 傳給 C，然後函式結束
    # c_callback 可能被回收，C 呼叫時會 crash
    return c_callback  # 必須保持參考

# 正確做法：保持回呼的參考
_callbacks = []  # 全域列表保持參考

def safe_example():
    def callback(x):
        return x * 2

    c_callback = CALLBACK(callback)
    _callbacks.append(c_callback)  # 保持參考
    return c_callback
```

---

## 思考題

1. 為什麼 cffi 的 API 模式比 ABI 模式快？這與 Python 的執行模型有什麼關係？
2. 在什麼情況下，使用 ctypes/cffi 會比重新用 Python 實現更好？
3. 如何安全地處理 C 函式庫中的記憶體分配？

## 實作練習

1. 使用 ctypes 包裝 `time.h` 中的 `time()` 和 `localtime()` 函式
2. 使用 cffi 包裝一個簡單的數學函式庫，提供矩陣乘法功能
3. 比較 ctypes、cffi ABI 模式、cffi API 模式在大量函式呼叫時的效能差異

## 延伸閱讀

- [Python ctypes 官方文件](https://docs.python.org/3/library/ctypes.html)
- [CFFI 官方文件](https://cffi.readthedocs.io/)
- [Real Python - Python Bindings](https://realpython.com/python-bindings-overview/)

---

*下一章：[Cython](../cython/)*
