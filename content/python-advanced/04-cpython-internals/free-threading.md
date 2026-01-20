---
title: "4.5 Free-Threading - Python 的真正多執行緒時代"
date: 2026-01-20
description: "Python 3.13+ 無 GIL 版本的完整指南"
weight: 5
---

# Free-Threading - Python 的真正多執行緒時代

Python 3.13 開始提供實驗性的 Free-threading 支援，Python 3.14 正式將其升級為官方支援功能。這是 Python 歷史上最重要的並行處理改進之一。

## 什麼是 Free-Threading？

### GIL 的歷史與限制

長久以來，CPython 使用 GIL（Global Interpreter Lock）來簡化記憶體管理和 C 擴展的開發。但這也意味著：

```text
傳統 Python（有 GIL）：
┌─────────────────────────────────┐
│  Thread 1  →  執行中             │
│  Thread 2  →  等待 GIL...        │
│  Thread 3  →  等待 GIL...        │
│  Thread 4  →  等待 GIL...        │
└─────────────────────────────────┘
   同一時間只有一個執行緒能執行 Python 程式碼
```

```text
Free-threaded Python（無 GIL）：
┌─────────────────────────────────┐
│  Thread 1  →  執行中  (Core 1)   │
│  Thread 2  →  執行中  (Core 2)   │
│  Thread 3  →  執行中  (Core 3)   │
│  Thread 4  →  執行中  (Core 4)   │
└─────────────────────────────────┘
   多個執行緒可以真正並行執行
```

### 發展歷程

| 版本 | 狀態 | PEP |
|------|------|-----|
| Python 3.13 | 實驗性支援 | PEP 703 |
| Python 3.14 | 正式支援 | PEP 779 |
| Python 3.15/3.16 | 可能成為預設 | 待定 |

## 安裝與啟用

### 各平台安裝方式

**Windows / macOS**

從 [python.org](https://www.python.org/downloads/) 下載安裝程式，選擇「Customize installation」，勾選「Free threaded mode」。

**Ubuntu / Debian**

```bash
# 使用 deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.13-nogil
# 或
sudo apt install python3.14-nogil
```

安裝後可使用 `python3.13t` 或 `python3.14t` 執行。

**從原始碼編譯**

```bash
./configure --disable-gil
make -j$(nproc)
sudo make install
```

### 確認安裝

```bash
# 檢查版本資訊
python3.14t -VV
# 輸出應包含 "free-threading build"

# 確認 GIL 狀態
python3.14t -c "import sys; print('GIL enabled:', sys._is_gil_enabled())"
# 應該輸出：GIL enabled: False
```

### 控制 GIL 狀態

```bash
# 強制停用 GIL（即使有不相容模組）
PYTHON_GIL=0 python3.14t script.py

# 或使用命令列參數
python3.14t -Xgil=0 script.py

# 強制啟用 GIL（在 free-threaded 版本中）
python3.14t -Xgil=1 script.py
```

## 效能實測數據

以下數據來自多個可信來源（Real Python、CodSpeed、Facebook Benchmarking）：

### 單執行緒 vs 多執行緒效能

| 場景 | 傳統 Python | Free-threaded | 差異 |
|------|------------|---------------|------|
| 單執行緒 | 1.44s | 1.86s | 慢 ~30% (3.13) |
| 單執行緒 | 基準 | 慢 ~9% | (3.14 改善) |
| 多執行緒 4 核 | 1.37s | 0.39s | **快 3.5x** |
| Fibonacci 並行 | 1377ms | 279ms | **快 ~5x** |

### 關鍵數據

- **Python 3.13 單執行緒額外負擔**：約 40%
- **Python 3.14 單執行緒額外負擔**：約 5-10%（大幅改善）
- **多執行緒加速比**：接近線性擴展（視任務而定）

> **重點**：Free-threading 在單執行緒下有效能損失，但在多執行緒 CPU 密集任務中可獲得顯著加速。

## 適用場景判斷

### 適合使用 Free-threading

- **CPU 密集的並行計算**：數學運算、資料處理
- **可分割的獨立任務**：批次處理、平行搜尋
- **資料科學工作流程**：大規模資料轉換
- **科學計算**：模擬、數值分析

### 不適合使用 Free-threading

- **單執行緒應用**：會有 5-10% 效能損失
- **I/O 密集任務**：傳統 threading 已經足夠
- **大量使用尚未支援的 C 擴展**：可能導致 GIL 被重新啟用
- **需要穩定性的生產環境**：生態系統仍在成熟中

## 實際範例

### 範例 1：檢查是否在 Free-threaded 模式

```python
import sys

def is_free_threaded() -> bool:
    """檢查是否在 free-threaded 模式執行"""
    try:
        return not sys._is_gil_enabled()
    except AttributeError:
        # Python 3.12 或更早版本沒有這個函式
        return False

def get_python_build_info() -> dict:
    """取得 Python 建置資訊"""
    return {
        "version": sys.version,
        "free_threaded": is_free_threaded(),
        "gil_enabled": getattr(sys, '_is_gil_enabled', lambda: True)(),
    }

if __name__ == "__main__":
    info = get_python_build_info()
    print(f"Python 版本: {info['version']}")
    print(f"Free-threaded: {info['free_threaded']}")
    print(f"GIL 啟用: {info['gil_enabled']}")
```

### 範例 2：並行 CPU 計算

```python
import threading
import time
import sys

def cpu_intensive(n: int) -> int:
    """CPU 密集計算：計算平方和"""
    return sum(i * i for i in range(n))

def sequential_compute(numbers: list[int]) -> list[int]:
    """序列計算"""
    return [cpu_intensive(n) for n in numbers]

def parallel_compute(numbers: list[int]) -> list[int]:
    """並行計算"""
    results = [None] * len(numbers)

    def worker(idx: int, n: int):
        results[idx] = cpu_intensive(n)

    threads = [
        threading.Thread(target=worker, args=(i, n))
        for i, n in enumerate(numbers)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return results

def benchmark():
    """效能比較"""
    numbers = [5_000_000] * 4

    # 序列執行
    start = time.perf_counter()
    sequential_compute(numbers)
    sequential_time = time.perf_counter() - start

    # 並行執行
    start = time.perf_counter()
    parallel_compute(numbers)
    parallel_time = time.perf_counter() - start

    print(f"序列執行: {sequential_time:.3f}s")
    print(f"並行執行: {parallel_time:.3f}s")
    print(f"加速比: {sequential_time / parallel_time:.2f}x")

    # 在傳統 Python 中，加速比接近 1（無改善）
    # 在 Free-threaded Python 中，加速比接近 CPU 核心數

if __name__ == "__main__":
    try:
        print(f"GIL 啟用: {sys._is_gil_enabled()}")
    except AttributeError:
        print("GIL 狀態: 無法檢測（舊版 Python）")

    benchmark()
```

### 範例 3：使用 ThreadPoolExecutor

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import sys

def process_chunk(chunk_id: int, size: int) -> dict:
    """處理一個資料區塊"""
    result = sum(i * i for i in range(size))
    return {"chunk_id": chunk_id, "result": result}

def parallel_process(num_chunks: int = 8, chunk_size: int = 2_000_000):
    """並行處理多個資料區塊"""
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=num_chunks) as executor:
        futures = {
            executor.submit(process_chunk, i, chunk_size): i
            for i in range(num_chunks)
        }

        results = []
        for future in as_completed(futures):
            chunk_id = futures[future]
            result = future.result()
            results.append(result)
            print(f"Chunk {chunk_id} 完成")

    elapsed = time.perf_counter() - start
    print(f"\n總耗時: {elapsed:.3f}s")
    print(f"平均每個 chunk: {elapsed / num_chunks:.3f}s")

    return results

if __name__ == "__main__":
    try:
        print(f"Free-threaded 模式: {not sys._is_gil_enabled()}\n")
    except AttributeError:
        print("傳統 Python 模式\n")

    parallel_process()
```

## concurrent.interpreters 模組（Python 3.14 新增）

Python 3.14 引入了全新的 `concurrent.interpreters` 模組，提供了另一種並行方式。

### 什麼是多解釋器？

多解釋器（Multiple Interpreters）是在同一個進程中運行多個獨立的 Python 直譯器：

```text
┌─────────────────────────────────────────┐
│              單一進程                     │
│  ┌──────────┐  ┌──────────┐             │
│  │ 解釋器 1  │  │ 解釋器 2  │             │
│  │ (獨立)   │  │ (獨立)   │             │
│  │ sys.path │  │ sys.path │  ← 完全隔離  │
│  │ modules  │  │ modules  │             │
│  └──────────┘  └──────────┘             │
└─────────────────────────────────────────┘
```

### 基本用法

```python
from concurrent.futures import InterpreterPoolExecutor

def cpu_task(n: int) -> int:
    """在獨立解釋器中執行的任務"""
    return sum(i * i for i in range(n))

if __name__ == "__main__":
    numbers = [1_000_000, 2_000_000, 3_000_000, 4_000_000]

    # 使用多解釋器池
    with InterpreterPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(cpu_task, numbers))

    print(f"結果: {results}")
```

### 多解釋器 vs 多進程 vs 多執行緒

| 特性 | threading | multiprocessing | interpreters |
|------|-----------|-----------------|--------------|
| 隔離程度 | 共享記憶體 | 完全隔離 | 部分隔離 |
| 資源消耗 | 最低 | 最高 | 中等 |
| 啟動速度 | 最快 | 最慢 | 中等 |
| 通訊方式 | 直接存取 | pickle/Queue | pickle |
| GIL 影響 | 受限（傳統）/ 無（Free-threaded） | 無 | 無 |

### 何時使用多解釋器

- 需要隔離但不想付出多進程的代價
- 想要類似 CSP/Actor 模型的並行方式
- 需要在同一進程中運行不同配置的 Python 環境

## 已知問題與陷阱

### 來自 GitHub Issues 的真實案例

**1. pathlib 的 race condition**（[#139001](https://github.com/python/cpython/issues/139001)）

```python
# 在 3.14t 中可能有問題
from pathlib import Path
import threading

path = Path("/some/path")

def check_path():
    # is_dir() 在多執行緒下可能有競爭條件
    return path.is_dir()
```

**2. click 套件的問題**（[#136248](https://github.com/python/cpython/issues/136248)）

使用 click 套件時，在 free-threaded 模式下可能出現意外行為。

**3. buffer interface 的資料競爭**（[#130977](https://github.com/python/cpython/issues/130977)）

使用 memoryview 或其他 buffer interface 時需特別注意。

### 常見錯誤模式

```python
# ❌ 錯誤：全域狀態未加鎖保護
cache = {}

def get_cached(key):
    if key not in cache:
        cache[key] = expensive_compute(key)  # 競爭條件！
    return cache[key]

# ✅ 正確：使用 Lock 保護
import threading

cache = {}
cache_lock = threading.Lock()

def get_cached_safe(key):
    with cache_lock:
        if key not in cache:
            cache[key] = expensive_compute(key)
        return cache[key]
```

```python
# ❌ 錯誤：依賴內建型別的「隱式」執行緒安全
results = []

def worker(n):
    result = compute(n)
    results.append(result)  # 在 free-threaded 中可能不安全

# ✅ 正確：返回結果，由主執行緒收集
def worker_safe(n):
    return compute(n)

with ThreadPoolExecutor() as executor:
    results = list(executor.map(worker_safe, items))
```

## 套件相容性現況（2025 年底）

### 已完全支援

| 套件 | 版本 | 備註 |
|------|------|------|
| NumPy | 2.1.0+ | 科學計算基礎 |
| SciPy | 1.15.0+ | 科學計算 |
| pandas | 2.2.3+ | 資料分析 |
| PyTorch | 2.6.0+ | 深度學習 |
| scikit-learn | 1.6.0+ | 機器學習 |
| Pillow | 11.0.0+ | 圖像處理 |
| Matplotlib | 3.9.0+ | 繪圖 |

### 部分支援或開發中

- cryptography、h5py、polars
- aiohttp、multidict、yarl
- 多個 aio-libs 套件

### 尚未支援

- lxml、cupy 等特定套件
- 部分 C 擴展模組

> **追蹤最新狀態**：[py-free-threading.github.io/tracking](https://py-free-threading.github.io/tracking/)

## 最佳實踐與建議

### 1. 漸進式採用

```python
import sys

def main():
    # 檢查執行環境
    free_threaded = getattr(sys, '_is_gil_enabled', lambda: True)() == False

    if free_threaded:
        print("使用 Free-threaded 最佳化路徑")
        run_parallel_optimized()
    else:
        print("使用傳統多進程路徑")
        run_multiprocess_fallback()
```

### 2. 明確使用同步原語

```python
import threading

# 永遠明確使用 Lock，不要依賴「可能」的執行緒安全
lock = threading.Lock()

def thread_safe_operation():
    with lock:
        # 關鍵區段
        pass
```

### 3. 測試策略

```python
# 使用較短的執行緒切換間隔來暴露潛在的競爭條件
import sys
sys.setswitchinterval(0.0001)  # 測試時使用

# 運行大量並行測試
import concurrent.futures
import random

def stress_test(func, iterations=1000):
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(func) for _ in range(iterations)]
        for f in concurrent.futures.as_completed(futures):
            f.result()  # 會拋出任何異常
```

### 4. 檢查依賴套件相容性

```python
def check_dependencies():
    """檢查關鍵依賴是否支援 free-threading"""
    import importlib.metadata

    packages_to_check = ['numpy', 'pandas', 'scikit-learn']
    results = {}

    for pkg in packages_to_check:
        try:
            version = importlib.metadata.version(pkg)
            results[pkg] = version
        except importlib.metadata.PackageNotFoundError:
            results[pkg] = "未安裝"

    return results
```

## 未來展望

### 路線圖

- **Python 3.15**：預期 Free-threading 將成為可選的預設選項
- **Python 3.16**：可能成為真正的預設建置
- **長期**：GIL 可能完全移除

### 社群呼籲

> 「Free-threaded 建置是這個語言的未來。現階段我們需要更多來自真實工作流程的回饋報告。」
> — Quansight Labs

如果你正在使用 Free-threaded Python，歡迎：

- 回報問題到 [Python Bug Tracker](https://github.com/python/cpython/issues)
- 參與 [py-free-threading Discord](https://discord.gg/rqgHCDqdRr) 討論
- 測試你的套件並提交相容性報告

## 思考題

1. 為什麼 Free-threading 在單執行緒下會有效能損失？這個損失從 40% 降到 9% 是如何達成的？
2. 什麼情況下應該使用 `InterpreterPoolExecutor` 而不是 `ThreadPoolExecutor`？
3. 如果你的程式依賴一個尚未支援 Free-threading 的套件，有什麼替代方案？

## 實作練習

1. 寫一個程式，比較在傳統 Python 和 Free-threaded Python 下的多執行緒效能差異
2. 使用 `InterpreterPoolExecutor` 實作一個簡單的任務佇列系統
3. 為一個現有的單執行緒程式添加 Free-threading 支援，並處理執行緒安全問題

## 延伸閱讀

- [Python 3.14 官方文件 - Free Threading](https://docs.python.org/3/howto/free-threading-python.html)
- [Python Free-Threading Guide](https://py-free-threading.github.io/)
- [PEP 703 - Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [PEP 779 - Criteria for Supported Status](https://peps.python.org/pep-0779/)
- [Quansight Labs - Free-Threaded Python 第一年回顧](https://labs.quansight.org/blog/free-threaded-one-year-recap)

## 相關章節

- [GIL 與執行緒模型](../gil-threading/) - 深入理解 GIL 的設計與實現
- [用 C 擴展 Python](../../05-c-extensions/) - 使用 C 擴展繞過 GIL 的傳統方法
- [用 Rust 擴展 Python](../../06-rust-extensions/) - 使用 PyO3 建立高效能擴展

## 先備知識

- 入門系列 [並行處理](../../../python/03-stdlib/concurrency/) - threading、multiprocessing 基礎

---

*上一章：[GIL 與執行緒模型](../gil-threading/)*
*下一模組：[模組五：用 C 擴展 Python](../../05-c-extensions/)*
