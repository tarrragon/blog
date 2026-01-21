---
title: "3.7 並行處理 - threading、multiprocessing、concurrent.futures"
date: 2026-01-20
description: "Python 並行處理的三種方式與選擇指南"
weight: 7
---

# 並行處理 - threading、multiprocessing、concurrent.futures

Python 提供了多種並行處理的方式。本章介紹三個核心模組，幫助你根據任務特性選擇合適的方案。

## 為什麼需要並行處理？

在實際開發中，我們常遇到需要同時處理多個任務的情況：

```python
# 情境 1：批次下載多個檔案（I/O 密集）
urls = ["https://example.com/file1", "https://example.com/file2", ...]
# 一個一個下載太慢了！

# 情境 2：處理大量資料（CPU 密集）
data_chunks = [chunk1, chunk2, chunk3, ...]
# 能不能同時處理多個資料區塊？
```

並行處理可以顯著提升這類任務的效率。

## I/O 密集 vs CPU 密集

在選擇並行方案之前，首先要判斷你的任務類型：

### I/O 密集任務

程式大部分時間在「等待」外部資源：

- 網路請求（HTTP、API 呼叫）
- 檔案讀寫
- 資料庫查詢

```python
# I/O 密集的特徵：大部分時間在等待
def fetch_data():
    response = requests.get(url)  # 等待網路回應
    return response.json()
```

### CPU 密集任務

程式大部分時間在「計算」：

- 數學運算
- 資料處理與轉換
- 圖像處理

```python
# CPU 密集的特徵：大部分時間在計算
def compute_heavy(n):
    return sum(i * i for i in range(n))  # 純計算
```

## GIL（全域直譯器鎖）

在深入各模組之前，需要先了解 Python 的一個重要機制。

### 什麼是 GIL？

GIL（Global Interpreter Lock）是 CPython 直譯器的一個機制，它確保同一時間只有一個執行緒能執行 Python bytecode。

```text
┌─────────────────────────────────────────┐
│              Python 直譯器                │
│  ┌─────┐  ┌─────┐  ┌─────┐              │
│  │執行緒1│  │執行緒2│  │執行緒3│              │
│  └──┬──┘  └──┬──┘  └──┬──┘              │
│     │        │        │                 │
│     └────────┼────────┘                 │
│              ▼                          │
│         ┌───────┐                       │
│         │  GIL  │ ← 同時只有一個能執行      │
│         └───────┘                       │
└─────────────────────────────────────────┘
```

### GIL 的影響

| 任務類型 | GIL 影響 | 原因 |
|---------|---------|------|
| I/O 密集 | 影響小 | 等待 I/O 時會釋放 GIL |
| CPU 密集 | 影響大 | 多執行緒無法真正並行計算 |

這就是為什麼：

- **I/O 密集**：使用 `threading` 即可
- **CPU 密集**：需要使用 `multiprocessing` 繞過 GIL

> **注意**：Python 3.13+ 推出了 Free-threading（無 GIL）版本，詳見 [3.8 Free-Threading](../free-threading/)

## threading 模組

`threading` 模組提供執行緒級別的並行，適合 I/O 密集任務。

### 基本用法

```python
import threading
import time

def worker(name, delay):
    print(f"{name} 開始工作")
    time.sleep(delay)  # 模擬 I/O 等待
    print(f"{name} 完成工作")

# 建立執行緒
t1 = threading.Thread(target=worker, args=("Worker-1", 2))
t2 = threading.Thread(target=worker, args=("Worker-2", 1))

# 啟動執行緒
t1.start()
t2.start()

# 等待執行緒完成
t1.join()
t2.join()

print("所有工作完成")
```

### 執行緒安全與 Lock

當多個執行緒存取共享資源時，需要使用鎖來避免競爭條件：

```python
import threading

counter = 0
lock = threading.Lock()

def increment():
    global counter
    for _ in range(100000):
        with lock:  # 使用 context manager 自動獲取和釋放鎖
            counter += 1

# 建立多個執行緒
threads = [threading.Thread(target=increment) for _ in range(5)]

for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"Counter: {counter}")  # 應該是 500000
```

### 何時使用 threading

- 網路請求（HTTP、API）
- 檔案讀寫
- 資料庫操作
- 任何需要等待外部資源的任務

## multiprocessing 模組

`multiprocessing` 模組使用多個進程來實現真正的並行，繞過 GIL 限制。

### 基本用法

```python
from multiprocessing import Process

def cpu_intensive(n):
    """CPU 密集計算"""
    result = sum(i * i for i in range(n))
    print(f"計算完成: {result}")

if __name__ == "__main__":  # 在 Windows 上必須使用這個保護
    processes = []
    for i in range(4):
        p = Process(target=cpu_intensive, args=(10_000_000,))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    print("所有計算完成")
```

### 進程間通訊

進程之間不共享記憶體，需要使用 Queue 或 Pipe 來通訊：

```python
from multiprocessing import Process, Queue

def worker(queue, n):
    result = sum(i * i for i in range(n))
    queue.put(result)  # 將結果放入佇列

if __name__ == "__main__":
    queue = Queue()
    processes = []

    for i in range(4):
        p = Process(target=worker, args=(queue, 5_000_000))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    # 收集結果
    results = [queue.get() for _ in range(4)]
    print(f"結果: {results}")
```

### 何時使用 multiprocessing

- CPU 密集計算
- 資料處理與轉換
- 需要真正並行執行的任務

## concurrent.futures（推薦入門）

`concurrent.futures` 提供了更高階、更簡潔的 API，統一了執行緒和進程的使用方式。

### ThreadPoolExecutor

適合 I/O 密集任務：

```python
from concurrent.futures import ThreadPoolExecutor
import urllib.request

def fetch_url(url):
    """下載網頁並返回大小"""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return url, len(response.read())
    except Exception as e:
        return url, f"Error: {e}"

urls = [
    "https://www.python.org",
    "https://docs.python.org",
    "https://pypi.org",
]

# 使用執行緒池並行下載
with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(fetch_url, urls))

for url, size in results:
    print(f"{url}: {size}")
```

### ProcessPoolExecutor

適合 CPU 密集任務：

```python
from concurrent.futures import ProcessPoolExecutor, as_completed

def compute_heavy(n):
    """CPU 密集計算"""
    return n, sum(i * i for i in range(n))

if __name__ == "__main__":
    numbers = [10_000_000, 20_000_000, 15_000_000, 5_000_000]

    with ProcessPoolExecutor() as executor:
        # 方法 1：使用 map（保持順序）
        results = list(executor.map(compute_heavy, numbers))

        # 方法 2：使用 submit + as_completed（先完成先處理）
        futures = {executor.submit(compute_heavy, n): n for n in numbers}
        for future in as_completed(futures):
            n, result = future.result()
            print(f"n={n}: {result}")
```

### 處理異常

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def risky_task(n):
    if n == 3:
        raise ValueError("不喜歡 3！")
    return n * 2

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(risky_task, i): i for i in range(5)}

    for future in as_completed(futures):
        n = futures[future]
        try:
            result = future.result()
            print(f"任務 {n} 完成: {result}")
        except Exception as e:
            print(f"任務 {n} 失敗: {e}")
```

## 選擇指南

| 任務類型 | 推薦方案 | 原因 |
|---------|---------|------|
| I/O 密集 | `ThreadPoolExecutor` | 輕量、共享記憶體、GIL 影響小 |
| CPU 密集 | `ProcessPoolExecutor` | 繞過 GIL、真正並行 |
| 需要細控制 | `threading`/`multiprocessing` | 底層 API、更多控制 |
| Python 3.14+ CPU 密集 | `threading` + Free-threading | 真正的多執行緒並行 |

### 決策流程

```text
任務類型是什麼？
    │
    ├─→ I/O 密集（網路、檔案、DB）
    │       │
    │       └─→ 使用 ThreadPoolExecutor
    │
    └─→ CPU 密集（計算、處理）
            │
            ├─→ Python 3.14+ Free-threaded
            │       │
            │       └─→ 可以使用 threading
            │
            └─→ 傳統 Python
                    │
                    └─→ 使用 ProcessPoolExecutor
```

## 常見陷阱與最佳實踐

### 1. 設定合理的 worker 數量

```python
import os

# I/O 密集：可以設定較多的 worker
io_workers = min(32, os.cpu_count() + 4)

# CPU 密集：不要超過 CPU 核心數
cpu_workers = os.cpu_count()
```

### 2. 避免共享可變狀態

```python
# 不好：共享可變狀態
results = []

def bad_worker(n):
    results.append(n * 2)  # 危險！多執行緒存取

# 好：返回結果，由主執行緒收集
def good_worker(n):
    return n * 2

with ThreadPoolExecutor() as executor:
    results = list(executor.map(good_worker, range(10)))
```

### 3. 使用 context manager

```python
# 好：使用 with 語句自動管理資源
with ThreadPoolExecutor(max_workers=4) as executor:
    results = executor.map(task, items)

# 不好：手動管理
executor = ThreadPoolExecutor(max_workers=4)
results = executor.map(task, items)
executor.shutdown(wait=True)  # 容易忘記
```

### 4. multiprocessing 的 `if __name__ == "__main__"` 保護

```python
from multiprocessing import Process

def worker():
    print("Working...")

# Windows 上必須使用這個保護，否則會無限遞迴
if __name__ == "__main__":
    p = Process(target=worker)
    p.start()
    p.join()
```

## 思考題

1. 為什麼 I/O 密集任務使用 `threading` 就夠了，而 CPU 密集任務需要 `multiprocessing`？
2. `ThreadPoolExecutor` 和手動建立 `Thread` 有什麼優缺點？
3. 在什麼情況下，並行處理反而會比序列處理更慢？

## 實作練習

1. 寫一個函式，使用 `ThreadPoolExecutor` 同時檢查多個網址是否可以連線
2. 使用 `ProcessPoolExecutor` 計算一組大數字的質因數分解
3. 實作一個進度顯示器，顯示多個任務的完成進度

## 延伸閱讀（進階系列）

- [實戰效能優化：並行處理](/python-advanced/08-practical-optimization/parallel-processing/) - 真實案例的並行化改造
- [asyncio 非同步程式設計](/python-advanced/01-asyncio/) - 學習協程與事件迴圈
- [GIL 與執行緒模型](/python-advanced/04-cpython-internals/gil-threading/) - 深入理解 GIL 的設計與實現
- [Free-Threading](/python-advanced/04-cpython-internals/free-threading/) - Python 3.13+ 無 GIL 多執行緒

---

*上一章：[argparse - CLI 介面](../argparse/)*
*下一章：[效能迷思與優化策略](../performance/)*
