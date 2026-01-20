---
title: "3.4 GIL 與執行緒模型"
description: "深入理解 GIL 的設計與實現"
weight: 4
---

# GIL 與執行緒模型

GIL（Global Interpreter Lock）是 CPython 中最具爭議的設計之一。本章深入探討 GIL 的歷史、實現，以及 Python 3.13+ Free-threading 的技術細節。

## 先備知識

- [3.3 Bytecode 與虛擬機](../bytecode/)
- 入門系列 [3.7 並行處理](../../../python/03-stdlib/concurrency/)
- 入門系列 [3.8 Free-Threading](../../../python/03-stdlib/free-threading/)

## 本章目標

學完本章後，你將能夠：

1. 理解 GIL 存在的歷史原因
2. 理解 GIL 的釋放時機
3. 理解 Free-threading 的實現挑戰
4. 做出正確的並行策略選擇

---

## 【原理層】為什麼需要 GIL？

### 歷史背景

GIL 是 1992 年 Python 初創時的設計決策：

```text
當時的考量：
1. 單核 CPU 是主流
2. 簡化記憶體管理（參考計數）
3. 簡化 C 擴展開發
4. 避免細粒度鎖的複雜性
```

### 參考計數與執行緒安全

GIL 主要保護參考計數操作：

```c
// 沒有 GIL 時，這個操作不是原子的
Py_INCREF(obj);
// 展開後：
// 1. 讀取 ob_refcnt
// 2. 加 1
// 3. 寫回 ob_refcnt

// 如果兩個執行緒同時執行，可能會：
// Thread 1: 讀取 refcnt = 1
// Thread 2: 讀取 refcnt = 1
// Thread 1: 寫入 refcnt = 2
// Thread 2: 寫入 refcnt = 2  ← 錯誤！應該是 3
```

### GIL 的實現

```c
// 簡化版的 GIL 結構
typedef struct {
    PyMutex mutex;           // 互斥鎖
    PyThread_type_lock lock; // 執行緒鎖
    int locked;              // 鎖定狀態
} _gil_runtime_state;
```

---

## 【設計層】GIL 的釋放時機

### 自動釋放

GIL 在以下情況會自動釋放：

```python
# 1. I/O 操作
f = open('file.txt', 'r')  # 釋放 GIL
content = f.read()          # 釋放 GIL

# 2. sleep
import time
time.sleep(1)  # 釋放 GIL

# 3. 某些 C 擴展操作
import numpy as np
result = np.dot(a, b)  # NumPy 可能釋放 GIL

# 4. 定期釋放（每 N 個 bytecode 指令）
# Python 3.2+ 預設約每 5ms 檢查一次
```

### 檢查間隔

```python
import sys

# 查看切換間隔（秒）
print(sys.getswitchinterval())  # 0.005（5ms）

# 設定切換間隔
sys.setswitchinterval(0.001)  # 1ms
```

### C 擴展中手動釋放 GIL

```c
// C 擴展可以明確釋放 GIL
static PyObject* compute_intensive(PyObject* self, PyObject* args) {
    // 釋放 GIL
    Py_BEGIN_ALLOW_THREADS

    // 這裡的程式碼可以並行執行
    do_heavy_computation();

    // 重新獲取 GIL
    Py_END_ALLOW_THREADS

    Py_RETURN_NONE;
}
```

---

## 【實驗】測量 GIL 的影響

### CPU 密集任務

```python
import threading
import time

def cpu_intensive(n):
    """純 Python CPU 密集計算"""
    total = 0
    for i in range(n):
        total += i * i
    return total

def benchmark(func, args, num_threads):
    threads = []
    start = time.perf_counter()

    for _ in range(num_threads):
        t = threading.Thread(target=func, args=args)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return time.perf_counter() - start

n = 5_000_000

# 單執行緒
time_1 = benchmark(cpu_intensive, (n,), 1)
print(f"1 執行緒: {time_1:.3f}s")

# 多執行緒（受 GIL 限制）
time_4 = benchmark(cpu_intensive, (n,), 4)
print(f"4 執行緒: {time_4:.3f}s")

# 結果：多執行緒可能更慢（執行緒切換開銷）
```

### I/O 密集任務

```python
import threading
import time
import urllib.request

def io_intensive(url):
    """I/O 密集操作"""
    try:
        with urllib.request.urlopen(url, timeout=5) as f:
            return len(f.read())
    except:
        return 0

urls = ["https://example.com"] * 10

# 單執行緒
start = time.perf_counter()
for url in urls:
    io_intensive(url)
time_sequential = time.perf_counter() - start
print(f"序列: {time_sequential:.3f}s")

# 多執行緒
start = time.perf_counter()
threads = [threading.Thread(target=io_intensive, args=(url,)) for url in urls]
for t in threads:
    t.start()
for t in threads:
    t.join()
time_parallel = time.perf_counter() - start
print(f"並行: {time_parallel:.3f}s")

# 結果：多執行緒明顯更快（I/O 時釋放 GIL）
```

---

## 【深入】Free-threading 技術細節

### Biased Reference Counting

Python 3.13+ Free-threading 使用「偏向參考計數」解決多執行緒問題：

```text
傳統參考計數：
┌─────────────────────────────────────┐
│  ob_refcnt = 2                      │
│  每次操作都需要原子操作或鎖         │
└─────────────────────────────────────┘

偏向參考計數：
┌─────────────────────────────────────┐
│  local_refcnt[thread_id] = 1        │  ← 每個執行緒有自己的計數
│  local_refcnt[thread_id] = 1        │
│  shared_refcnt = 0                  │  ← 共享計數
└─────────────────────────────────────┘

優點：
- 大多數操作只需更新區域計數（無鎖）
- 只有跨執行緒參考才需要更新共享計數
```

### 延遲參考計數

```python
# Free-threading 中的優化策略

# 對於不朽物件（immortal objects）
# 如 None、True、False、小整數
# 完全跳過參考計數

# 對於局部物件
# 使用區域計數，無需同步

# 只有跨執行緒共享的物件
# 才需要使用原子操作
```

### 記憶體模型變化

```text
傳統 CPython（有 GIL）：
┌──────────────────────────────────────────┐
│  Thread 1  │  Thread 2  │  Thread 3      │
│     ↓            ↓            ↓          │
│     └────────────┼────────────┘          │
│                  ↓                       │
│               [ GIL ]                    │
│                  ↓                       │
│        [ Python Interpreter ]            │
│                  ↓                       │
│          [ 共享記憶體 ]                  │
└──────────────────────────────────────────┘

Free-threaded CPython：
┌──────────────────────────────────────────┐
│  Thread 1  │  Thread 2  │  Thread 3      │
│     ↓            ↓            ↓          │
│  [Local]     [Local]     [Local]         │
│  State       State       State           │
│     ↓            ↓            ↓          │
│     └────────────┼────────────┘          │
│                  ↓                       │
│     [ 原子操作 / 鎖 / 無鎖資料結構 ]     │
│                  ↓                       │
│          [ 共享記憶體 ]                  │
└──────────────────────────────────────────┘
```

---

## 【實戰】Free-threading 程式設計

### 檢查執行環境

```python
import sys

def check_environment():
    """檢查 Free-threading 環境"""
    try:
        gil_enabled = sys._is_gil_enabled()
        print(f"GIL 啟用: {gil_enabled}")
        return not gil_enabled
    except AttributeError:
        print("傳統 Python（有 GIL）")
        return False

is_free_threaded = check_environment()
```

### 執行緒安全的程式設計

```python
import threading

# ❌ 不安全：共享可變狀態
counter = 0

def unsafe_increment():
    global counter
    for _ in range(100000):
        counter += 1  # 競爭條件！

# ✅ 安全：使用鎖
counter = 0
lock = threading.Lock()

def safe_increment():
    global counter
    for _ in range(100000):
        with lock:
            counter += 1

# ✅ 更好：使用原子操作或不可變資料
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

def better_approach(data_chunk):
    """每個執行緒處理自己的資料，最後合併"""
    local_count = 0
    for item in data_chunk:
        local_count += process(item)
    return local_count

with ThreadPoolExecutor() as executor:
    results = executor.map(better_approach, data_chunks)
    total = sum(results)
```

### 適應性程式碼

```python
import sys

def compute(data):
    """根據環境選擇策略"""
    free_threaded = getattr(sys, '_is_gil_enabled', lambda: True)() == False

    if free_threaded:
        # 可以安全使用多執行緒
        return parallel_compute_threading(data)
    else:
        # 使用多進程或保持單執行緒
        return parallel_compute_multiprocess(data)
```

---

## 【選擇指南】並行策略

### 決策流程

```text
你的任務是什麼類型？
│
├── I/O 密集（網路、檔案、資料庫）
│   └── 使用 threading 或 asyncio
│       （GIL 不影響）
│
└── CPU 密集（計算、處理）
    │
    ├── 使用 Free-threaded Python (3.13+)?
    │   ├── 是 → 可以使用 threading
    │   └── 否 → 選擇以下方案
    │
    ├── 可以用 C 擴展？
    │   └── NumPy、Cython 等（會釋放 GIL）
    │
    └── 純 Python？
        └── 使用 multiprocessing 或 ProcessPoolExecutor
```

### 效能比較總結

| 任務類型 | threading (有 GIL) | threading (Free) | multiprocessing |
| -------- | ------------------ | ---------------- | --------------- |
| I/O 密集 | ✅ 好 | ✅ 好 | ⚠️ 過重 |
| CPU 密集 | ❌ 無效 | ✅ 好 | ✅ 好 |
| 記憶體共享 | ✅ 簡單 | ✅ 簡單 | ❌ 複雜 |
| 啟動成本 | ✅ 低 | ✅ 低 | ❌ 高 |

---

## 【未來】GIL 的發展

### 路線圖

```text
Python 3.13 (2024): 實驗性 Free-threading
Python 3.14 (2025): 正式支援 Free-threading
Python 3.15/3.16:   可能成為預設
未來:               GIL 可能完全移除
```

### 生態系統遷移

```python
# 檢查套件是否支援 Free-threading
# pip index versions package-name

# 主要框架的支援狀態（2025年底）
# NumPy 2.1+:       ✅ 支援
# pandas 2.2+:      ✅ 支援
# scikit-learn 1.6+: ✅ 支援
# PyTorch 2.6+:     ✅ 支援
```

---

## 思考題

1. 如果沒有 GIL，CPython 需要做哪些改變來保證記憶體安全？
2. 為什麼其他 Python 實現（如 Jython、IronPython）沒有 GIL？
3. Free-threading 的效能損失主要來自哪裡？如何最小化？

## 實作練習

1. 寫一個程式，測量 GIL 切換間隔對效能的影響
2. 比較 Free-threaded 和傳統 Python 在相同 CPU 密集任務上的效能
3. 將一個使用 multiprocessing 的程式改寫為 Free-threading 版本

## 延伸閱讀

- [PEP 703 - Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [Python Free-Threading Guide](https://py-free-threading.github.io/)
- [Understanding the Python GIL - David Beazley](https://www.dabeaz.com/python/UnderstandingGIL.pdf)

---

*上一章：[Bytecode 與虛擬機](../bytecode/)*
*下一模組：[模組四：用 C 擴展 Python](../../04-c-extensions/)*
