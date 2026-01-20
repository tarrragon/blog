---
title: "1.3 設計模式與最佳實踐"
date: 2026-01-20
description: "學習常見的異步設計模式，避免常見陷阱"
weight: 3
---

# 設計模式與最佳實踐

本章介紹 asyncio 的常見設計模式，以及如何避免常見陷阱。

## 先備知識

- [1.2 協程與 Task 管理](../coroutines-tasks/)

## 本章目標

學完本章後，你將能夠：

1. 使用異步上下文管理器管理資源
2. 實作異步迭代器處理串流資料
3. 使用 Semaphore 控制並發
4. 避免阻塞事件迴圈的陷阱

---

## 【原理層】異步協議

### 異步上下文管理器

同步版本使用 `__enter__` 和 `__exit__`，異步版本使用 `__aenter__` 和 `__aexit__`：

```python
class AsyncResource:
    async def __aenter__(self):
        print("獲取資源")
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("釋放資源")
        await self.disconnect()

    async def connect(self):
        await asyncio.sleep(0.1)

    async def disconnect(self):
        await asyncio.sleep(0.1)

async def main():
    async with AsyncResource() as resource:
        print("使用資源")
```

### 異步迭代器

同步版本使用 `__iter__` 和 `__next__`，異步版本使用 `__aiter__` 和 `__anext__`：

```python
class AsyncCounter:
    def __init__(self, stop):
        self.current = 0
        self.stop = stop

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.current >= self.stop:
            raise StopAsyncIteration
        await asyncio.sleep(0.1)  # 模擬異步操作
        self.current += 1
        return self.current

async def main():
    async for num in AsyncCounter(5):
        print(num)
```

### 異步生成器

更簡潔的異步迭代器寫法：

```python
async def async_range(stop):
    for i in range(stop):
        await asyncio.sleep(0.1)
        yield i

async def main():
    async for num in async_range(5):
        print(num)
```

---

## 【設計層】常見模式

### 協程鏈（Chaining）

```python
async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def parse(html):
    # 假設這是 CPU 密集操作，應該放到執行緒池
    await asyncio.sleep(0)  # 讓出控制權
    return html[:100]

async def process(data):
    await asyncio.sleep(0.1)
    return f"處理完成：{data}"

async def pipeline(url):
    html = await fetch(url)
    parsed = await parse(html)
    result = await process(parsed)
    return result
```

### Semaphore 並發控制

限制同時執行的任務數量：

```python
async def fetch_with_limit(sem, url):
    async with sem:  # 獲取信號量
        return await fetch(url)

async def main():
    sem = asyncio.Semaphore(10)  # 最多 10 個並發
    urls = [f"https://example.com/{i}" for i in range(100)]

    tasks = [fetch_with_limit(sem, url) for url in urls]
    results = await asyncio.gather(*tasks)
```

### 生產者-消費者

```python
async def producer(queue):
    for i in range(10):
        await asyncio.sleep(0.1)
        await queue.put(i)
        print(f"生產：{i}")
    await queue.put(None)  # 結束信號

async def consumer(queue):
    while True:
        item = await queue.get()
        if item is None:
            break
        await asyncio.sleep(0.2)
        print(f"消費：{item}")

async def main():
    queue = asyncio.Queue(maxsize=5)
    await asyncio.gather(
        producer(queue),
        consumer(queue)
    )
```

---

## 【實作層】實用範例

### 異步 Rate Limiter

```python
class RateLimiter:
    def __init__(self, rate, per):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = asyncio.get_event_loop().time()

    async def acquire(self):
        current = asyncio.get_event_loop().time()
        elapsed = current - self.last_check
        self.last_check = current
        self.allowance += elapsed * (self.rate / self.per)

        if self.allowance > self.rate:
            self.allowance = self.rate

        if self.allowance < 1.0:
            wait_time = (1.0 - self.allowance) * (self.per / self.rate)
            await asyncio.sleep(wait_time)
            self.allowance = 0
        else:
            self.allowance -= 1.0
```

### 重試模式

```python
async def retry(coro_func, max_retries=3, delay=1.0):
    for attempt in range(max_retries):
        try:
            return await coro_func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"重試 {attempt + 1}/{max_retries}")
            await asyncio.sleep(delay * (attempt + 1))
```

---

## 【陷阱與避免】

### 阻塞事件迴圈

```python
import time

async def bad_example():
    time.sleep(1)  # 阻塞！整個事件迴圈停止

async def good_example():
    await asyncio.sleep(1)  # 非阻塞

# 如果必須執行同步阻塞函式
async def run_blocking():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, time.sleep, 1)
```

### 資源洩漏

```python
# 錯誤：沒有正確關閉
async def bad():
    session = aiohttp.ClientSession()
    response = await session.get("https://example.com")
    return await response.text()

# 正確：使用 async with
async def good():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://example.com") as response:
            return await response.text()
```

---

## 思考題

1. 為什麼 Semaphore 在 asyncio 中不需要擔心執行緒安全？
2. 異步生成器在什麼場景下比異步迭代器更適合？
3. 如何檢測程式碼是否阻塞了事件迴圈？

## 實作練習

1. 實作一個異步連線池
2. 實作一個帶有指數退避的重試裝飾器
3. 實作一個異步的 debounce 函式

## 延伸閱讀

- [Python 官方文件 - asyncio Queue](https://docs.python.org/3/library/asyncio-queue.html)
- [aio-libs 系列函式庫](https://github.com/aio-libs)

---

*上一章：[協程與 Task 管理](../coroutines-tasks/)*
*下一章：[實戰：與同步程式碼整合](../real-world/)*
