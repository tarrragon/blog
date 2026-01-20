---
title: "1.1 基礎概念與事件迴圈"
description: "理解 asyncio 的核心概念：事件迴圈、協程與並發模型"
weight: 1
---

# 基礎概念與事件迴圈

本章介紹 asyncio 的核心概念。理解這些概念是掌握異步程式設計的基礎。

## 先備知識

- 入門系列 [3.7 並行處理](../../../python/03-stdlib/concurrency/)
- 了解 I/O 密集任務的特性

## 本章目標

學完本章後，你將能夠：

1. 理解並發、並行、異步的區別
2. 解釋事件迴圈的工作原理
3. 寫出第一個異步程式
4. 判斷何時使用 asyncio

---

## 【原理層】並發、並行與異步

### 三個容易混淆的概念

在開始之前，我們需要釐清三個經常被混用的概念：

```text
並發（Concurrency）：
  同時「處理」多件事情（不一定同時執行）
  重點是結構和設計

並行（Parallelism）：
  同時「執行」多件事情
  需要多核 CPU 或多台機器

異步（Asynchronous）：
  不等待結果就繼續執行
  一種實現並發的方式
```

用一個生活化的例子：

```text
同步做早餐：
  1. 煮咖啡（等 5 分鐘）
  2. 烤土司（等 3 分鐘）
  3. 煎蛋（等 4 分鐘）
  總共：12 分鐘

異步做早餐（一個人）：
  1. 啟動咖啡機
  2. 放土司進烤箱
  3. 開始煎蛋
  4. 等待全部完成
  總共：約 5 分鐘（最長任務的時間）

並行做早餐（三個人）：
  三人同時分別處理
  總共：約 5 分鐘
```

### asyncio 是並發，不是並行

這是最重要的概念：**asyncio 在單執行緒中實現並發**。

```python
import asyncio
import time

async def task(name, delay):
    print(f"{name} 開始")
    await asyncio.sleep(delay)  # 非阻塞等待
    print(f"{name} 完成")
    return name

async def main():
    start = time.perf_counter()

    # 同時啟動三個任務
    results = await asyncio.gather(
        task("A", 2),
        task("B", 1),
        task("C", 1.5)
    )

    elapsed = time.perf_counter() - start
    print(f"總耗時：{elapsed:.2f}s")  # 約 2 秒，不是 4.5 秒

asyncio.run(main())
```

輸出：

```text
A 開始
B 開始
C 開始
B 完成
C 完成
A 完成
總耗時：2.00s
```

三個任務「並發」執行，但都在同一個執行緒中。

### 為什麼不用多執行緒？

你可能會問：用 threading 也能達到類似效果，為什麼要用 asyncio？

| 面向 | threading | asyncio |
|------|-----------|---------|
| 記憶體開銷 | 每執行緒約 8MB stack | 每協程約幾 KB |
| 切換成本 | OS 排程，較高 | 用戶空間切換，極低 |
| 並發數量 | 數百到數千 | 數萬到數十萬 |
| 執行緒安全 | 需要鎖保護 | 單執行緒，天生安全 |
| 除錯難度 | 競爭條件難以重現 | 確定性較高 |

當你需要處理大量 I/O 並發（如 Web 伺服器、爬蟲）時，asyncio 通常是更好的選擇。

---

## 【設計層】事件迴圈

### 什麼是事件迴圈？

事件迴圈（Event Loop）是 asyncio 的核心，它負責：

1. 排程和執行協程
2. 處理 I/O 事件
3. 管理回呼函式

```text
事件迴圈的運作：

┌─────────────────────────────────────┐
│           事件迴圈                    │
│  ┌─────────────────────────────┐    │
│  │    就緒佇列（Ready Queue）    │    │
│  │  [協程A] [協程B] [協程C]      │    │
│  └─────────────────────────────┘    │
│              ↓                       │
│         執行就緒任務                  │
│              ↓                       │
│         遇到 await                   │
│              ↓                       │
│  ┌─────────────────────────────┐    │
│  │   等待佇列（Waiting Queue）   │    │
│  │  [等待 I/O] [等待計時器]      │    │
│  └─────────────────────────────┘    │
│              ↓                       │
│         I/O 完成                     │
│              ↓                       │
│         放回就緒佇列                  │
└─────────────────────────────────────┘
```

### 協作式多任務

asyncio 使用「協作式多任務」（Cooperative Multitasking）：

- 任務主動讓出控制權（透過 `await`）
- 事件迴圈選擇下一個就緒任務執行
- 沒有強制搶佔

```python
async def cooperative_task(name):
    for i in range(3):
        print(f"{name}: 步驟 {i}")
        await asyncio.sleep(0)  # 主動讓出控制權
    print(f"{name}: 完成")

async def main():
    await asyncio.gather(
        cooperative_task("A"),
        cooperative_task("B")
    )

asyncio.run(main())
```

輸出：

```text
A: 步驟 0
B: 步驟 0
A: 步驟 1
B: 步驟 1
A: 步驟 2
B: 步驟 2
A: 完成
B: 完成
```

注意任務是交替執行的，每次 `await` 都是一個切換點。

### asyncio.run() 的背後

`asyncio.run()` 是 Python 3.7+ 推薦的入口點：

```python
# 這是簡化的偽代碼
def run(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()
```

它做了三件事：

1. 建立新的事件迴圈
2. 執行協程直到完成
3. 關閉事件迴圈

---

## 【實作層】第一個異步程式

### async 和 await

```python
import asyncio

# async def 定義協程函式
async def greet(name, delay):
    print(f"開始問候 {name}")
    await asyncio.sleep(delay)  # await 等待可等待物件
    print(f"你好，{name}！")
    return f"問候 {name} 完成"

async def main():
    # 方法 1：依序執行
    result1 = await greet("Alice", 1)
    result2 = await greet("Bob", 1)
    # 總共約 2 秒

    # 方法 2：並發執行
    results = await asyncio.gather(
        greet("Charlie", 1),
        greet("David", 1)
    )
    # 總共約 1 秒

asyncio.run(main())
```

### 協程 vs 協程函式

這是一個常見的混淆點：

```python
async def my_coro():
    return 42

# my_coro 是協程函式（coroutine function）
print(type(my_coro))  # <class 'function'>

# my_coro() 是協程物件（coroutine object）
coro = my_coro()
print(type(coro))  # <class 'coroutine'>

# 協程物件需要被執行
result = asyncio.run(coro)
print(result)  # 42
```

### 常見錯誤：忘記 await

```python
async def fetch_data():
    await asyncio.sleep(1)
    return {"data": "value"}

async def main():
    # 錯誤：沒有 await
    result = fetch_data()  # 這只是建立協程物件，沒有執行
    print(result)  # <coroutine object fetch_data at 0x...>

    # 正確：使用 await
    result = await fetch_data()
    print(result)  # {'data': 'value'}

asyncio.run(main())
```

Python 會發出警告：

```text
RuntimeWarning: coroutine 'fetch_data' was never awaited
```

### 偵錯技巧

```python
import asyncio

async def main():
    # 取得當前事件迴圈
    loop = asyncio.get_running_loop()
    print(f"事件迴圈：{loop}")

    # 檢查是否在事件迴圈中
    print(f"正在執行：{loop.is_running()}")

asyncio.run(main())
```

---

## 【選擇指南】何時使用 asyncio

### 適合 asyncio 的場景

1. **Web 伺服器**：處理大量並發請求
2. **API 客戶端**：批次呼叫多個 API
3. **網路爬蟲**：同時抓取多個網頁
4. **即時應用**：WebSocket、聊天室
5. **資料庫操作**：批次查詢

```python
# 範例：並發下載多個網頁
import asyncio
import aiohttp

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    urls = [
        "https://python.org",
        "https://docs.python.org",
        "https://pypi.org"
    ]

    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        results = await asyncio.gather(*tasks)

    for url, html in zip(urls, results):
        print(f"{url}: {len(html)} bytes")

asyncio.run(main())
```

### 不適合 asyncio 的場景

1. **CPU 密集任務**：asyncio 無法繞過 GIL
2. **簡單腳本**：增加複雜度沒有好處
3. **依賴同步函式庫**：需要額外處理

### 決策流程

```text
任務類型？
    │
    ├─→ CPU 密集
    │       └─→ multiprocessing 或 Free-threading
    │
    └─→ I/O 密集
            │
            ├─→ 並發量 < 100
            │       └─→ threading 可能夠用
            │
            └─→ 並發量 > 100
                    │
                    ├─→ 需要共享複雜狀態
                    │       └─→ threading + Lock
                    │
                    └─→ 任務相對獨立
                            └─→ asyncio（推薦）
```

---

## 思考題

1. 為什麼說 asyncio 是「協作式」而不是「搶佔式」？這對程式設計有什麼影響？
2. 如果一個協程中有 CPU 密集的計算而沒有 `await`，會發生什麼事？
3. `asyncio.sleep(0)` 的作用是什麼？

## 實作練習

1. 寫一個程式，同時「下載」5 個檔案（用 `asyncio.sleep()` 模擬下載時間），並顯示總耗時
2. 修改上面的程式，讓它顯示每個檔案完成的順序
3. 實作一個簡單的計時器，每秒印出一次時間，持續 5 秒

## 延伸閱讀

- [Python 官方文件 - asyncio 概念總覽](https://docs.python.org/3/howto/a-conceptual-overview-of-asyncio.html)
- [Real Python - Asyncio Walkthrough](https://realpython.com/async-io-python/)

---

*下一章：[協程與 Task 管理](../coroutines-tasks/)*
