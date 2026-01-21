---
title: "從 threading 到 asyncio：轉換指南"
date: 2026-01-21
description: "幫助你從傳統執行緒模型平滑過渡到異步程式設計"
weight: 0
---

# 從 threading 到 asyncio：轉換指南

如果你已經熟悉入門系列的 `threading` 模組，本章將幫助你理解為什麼需要 asyncio，以及如何將現有的多執行緒程式碼轉換為異步版本。

## 為什麼要從 threading 轉向 asyncio？

### threading 的限制

`threading` 是處理並發的傳統方案，但它有幾個固有限制：

#### 1. 資源消耗高

每個執行緒都需要分配記憶體（預設約 8MB stack）：

```python
import threading

# 建立 100 個執行緒
threads = [threading.Thread(target=some_task) for _ in range(100)]
# 記憶體消耗：約 800MB 的 stack 空間
```

當需要處理數千個並發連線時，執行緒模型會面臨資源瓶頸。

#### 2. 上下文切換成本

作業系統需要在執行緒之間切換，這涉及：

- 保存和恢復 CPU 暫存器
- 切換記憶體映射
- 快取失效

```text
執行緒 1 執行 → 上下文切換（耗時）→ 執行緒 2 執行 → 上下文切換（耗時）→ ...
```

#### 3. GIL 的限制

由於 GIL，多個執行緒無法真正並行執行 Python 程式碼：

```python
# 這段程式碼實際上是序列執行的
def cpu_task():
    total = 0
    for i in range(1000000):
        total += i
    return total

# 即使使用多執行緒，也無法利用多核 CPU
threads = [threading.Thread(target=cpu_task) for _ in range(4)]
```

### asyncio 的優勢

asyncio 採用不同的並發模型來解決這些問題：

#### 1. 輕量級協程

協程只是普通的 Python 物件，記憶體消耗極低：

```python
import asyncio

# 建立 10000 個協程
async def some_task():
    await asyncio.sleep(1)

# 記憶體消耗：幾十 KB
tasks = [some_task() for _ in range(10000)]
```

#### 2. 協作式切換

協程只在 `await` 點切換，沒有強制的上下文切換：

```text
協程 1 執行 → await（主動讓出）→ 協程 2 執行 → await（主動讓出）→ ...
```

#### 3. 單執行緒高並發

asyncio 在單執行緒中處理所有任務，避免了執行緒同步問題：

```python
async def handle_request(client):
    data = await client.read()    # 等待時處理其他請求
    result = process(data)
    await client.write(result)    # 等待時處理其他請求
```

## 並發模型比較

| 特性 | threading | asyncio |
|------|-----------|---------|
| 執行模型 | 多執行緒並行 | 單執行緒協作 |
| 切換方式 | 作業系統搶佔 | 程式主動讓出 |
| 記憶體消耗 | 高（每執行緒 ~8MB） | 低（每協程 ~KB） |
| 並發數量 | 百級 | 萬級 |
| GIL 影響 | 受限制 | 無影響（不需要多核） |
| 同步複雜度 | 需要鎖（Lock、Semaphore） | 較少（單執行緒） |
| 適用場景 | I/O 密集 + 共享記憶體 | I/O 密集 + 大規模並發 |

## 程式碼轉換模式

### 模式 1：簡單函式轉換

**threading 版本**：

```python
import time
import threading

def fetch_data(url):
    time.sleep(1)  # 模擬網路延遲
    return f"Data from {url}"

def main():
    urls = ["url1", "url2", "url3"]
    threads = []
    results = []

    for url in urls:
        t = threading.Thread(target=lambda u=url: results.append(fetch_data(u)))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return results
```

**asyncio 版本**：

```python
import asyncio

async def fetch_data(url):
    await asyncio.sleep(1)  # 非阻塞等待
    return f"Data from {url}"

async def main():
    urls = ["url1", "url2", "url3"]

    # 使用 gather 並發執行
    results = await asyncio.gather(*[fetch_data(url) for url in urls])

    return results

# 執行
asyncio.run(main())
```

**轉換要點**：

| 原本 | 轉換後 |
|------|--------|
| `def` | `async def` |
| `time.sleep()` | `await asyncio.sleep()` |
| `threading.Thread` + `join` | `asyncio.gather()` |

### 模式 2：ThreadPoolExecutor 轉換

**threading 版本**：

```python
from concurrent.futures import ThreadPoolExecutor

def process_file(filepath):
    with open(filepath) as f:
        return len(f.read())

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_file, file_paths))
```

**asyncio 版本**（使用 aiofiles）：

```python
import asyncio
import aiofiles

async def process_file(filepath):
    async with aiofiles.open(filepath) as f:
        content = await f.read()
        return len(content)

async def main():
    tasks = [process_file(fp) for fp in file_paths]
    results = await asyncio.gather(*tasks)
    return results

asyncio.run(main())
```

### 模式 3：保留同步程式碼（混合模式）

有時候你無法（或不想）將所有程式碼都轉為異步。asyncio 提供了 `run_in_executor` 來處理這種情況：

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 保持原有的同步函式
def blocking_operation(data):
    # 這是一個阻塞的第三方函式庫呼叫
    import time
    time.sleep(1)
    return f"Processed: {data}"

async def main():
    loop = asyncio.get_event_loop()

    # 在執行緒池中執行同步函式
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool,
            blocking_operation,
            "my_data"
        )

    return result

asyncio.run(main())
```

這種模式讓你可以漸進式地將程式碼遷移到 asyncio。

## 何時選擇哪種方案？

### 選擇 threading

- 需要與不支援 asyncio 的函式庫整合
- 需要共享記憶體且修改頻繁
- 並發數量較少（< 100）
- 團隊對 threading 更熟悉

### 選擇 asyncio

- 需要處理大量並發連線（Web 伺服器、聊天室）
- 主要是 I/O 操作（網路、檔案）
- 使用現代 async 函式庫（aiohttp、httpx、asyncpg）
- 需要高效能的單機並發

### 選擇 multiprocessing

- CPU 密集任務（資料處理、科學計算）
- 需要真正的並行計算
- 各任務相對獨立，不需要頻繁通訊

## 決策流程圖

```text
任務類型是什麼？
    │
    ├─ CPU 密集 ────────────────→ multiprocessing
    │
    └─ I/O 密集
        │
        ├─ 並發數 > 100 ─────────→ asyncio
        │
        ├─ 需要共享記憶體 ────────→ threading
        │
        └─ 第三方函式庫支援 async？
            │
            ├─ 是 ───────────────→ asyncio
            │
            └─ 否 ───────────────→ threading 或 asyncio + run_in_executor
```

## 常見轉換陷阱

### 陷阱 1：忘記 await

```python
# 錯誤：忘記 await
async def main():
    result = fetch_data("url")  # 這只會建立協程物件，不會執行
    print(result)  # <coroutine object fetch_data at 0x...>

# 正確
async def main():
    result = await fetch_data("url")
    print(result)
```

### 陷阱 2：在異步函式中使用阻塞呼叫

```python
# 錯誤：使用阻塞的 time.sleep
async def bad_sleep():
    time.sleep(1)  # 這會阻塞整個事件迴圈！

# 正確：使用非阻塞的 asyncio.sleep
async def good_sleep():
    await asyncio.sleep(1)  # 這會讓出控制權
```

### 陷阱 3：在同步函式中呼叫異步函式

```python
# 錯誤：在普通函式中直接呼叫
def sync_function():
    result = await fetch_data("url")  # SyntaxError!

# 正確：使用 asyncio.run
def sync_function():
    result = asyncio.run(fetch_data("url"))
```

## 實戰練習

### 練習 1：轉換簡單的多執行緒下載器

將以下 threading 程式碼轉換為 asyncio 版本：

```python
import threading
import time

def download(url):
    print(f"Downloading {url}...")
    time.sleep(2)  # 模擬下載
    print(f"Finished {url}")
    return f"Content of {url}"

def main():
    urls = ["url1", "url2", "url3", "url4"]
    threads = []

    for url in urls:
        t = threading.Thread(target=download, args=(url,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
```

### 練習 2：使用 run_in_executor 整合同步函式庫

假設你有一個只支援同步的第三方 API 客戶端，寫一個異步包裝器。

## 下一步

理解了 threading 和 asyncio 的區別後，你可以開始深入學習 asyncio 的核心概念：

- [1.1 基礎概念與事件迴圈](../fundamentals/) - 理解 asyncio 的運作原理
- [1.2 協程與 Task 管理](../coroutines-tasks/) - 掌握 async/await 語法
- [1.4 實戰：與同步程式碼整合](../real-world/) - 學習混合模式的最佳實踐

---

*上一章：[入門系列 3.7 並行處理](../../../python/03-stdlib/concurrency/)*
*下一章：[1.1 基礎概念與事件迴圈](../fundamentals/)*
