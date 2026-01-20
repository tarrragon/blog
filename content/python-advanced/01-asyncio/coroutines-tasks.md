---
title: "1.2 協程與 Task 管理"
date: 2026-01-20
description: "深入理解協程、Task 與 Future，掌握 async/await 的進階用法"
weight: 2
---

# 協程與 Task 管理

本章深入探討協程的執行機制，以及如何使用 Task 管理並發任務。

## 先備知識

- [1.1 基礎概念與事件迴圈](../fundamentals/)

## 本章目標

學完本章後，你將能夠：

1. 理解協程、Task、Future 的區別與關係
2. 使用 `create_task()` 建立並發任務
3. 使用 `gather()`、`wait()` 和 `TaskGroup` 管理多個任務
4. 正確處理任務取消與超時

---

## 【原理層】可等待物件

### 協程、Task、Future

在 asyncio 中，有三種「可等待物件」（Awaitable）：

```python
import asyncio

# 1. 協程（Coroutine）
async def my_coroutine():
    return 42

# 2. Task - 協程的包裝，可追蹤狀態
task = asyncio.create_task(my_coroutine())

# 3. Future - 底層的「未來結果」容器
future = asyncio.Future()
```

它們的關係：

```text
         ┌─────────────────────┐
         │     Awaitable       │
         │   （可等待物件）      │
         └─────────────────────┘
                   ▲
         ┌─────────┼─────────┐
         │         │         │
    Coroutine   Future     Task
     （協程）   （未來）  （任務）
                   ▲
                   │
                 Task
           （Task 繼承自 Future）
```

### await 的語義

當你 `await` 一個物件時：

1. 如果結果已就緒，立即返回
2. 如果結果未就緒，暫停當前協程，讓出控制權
3. 當結果就緒時，恢復執行

```python
async def demo():
    # await 協程
    result1 = await some_coroutine()

    # await Task
    task = asyncio.create_task(some_coroutine())
    result2 = await task

    # await Future
    future = asyncio.Future()
    # ... 某處設定 future.set_result(value)
    result3 = await future
```

---

## 【設計層】Task 管理

### create_task() 的時機

`create_task()` 將協程包裝成 Task 並排程執行：

```python
async def worker(name, delay):
    print(f"{name} 開始")
    await asyncio.sleep(delay)
    print(f"{name} 完成")
    return f"{name} 結果"

async def main():
    # 方法 1：依序執行（不並發）
    result1 = await worker("A", 1)
    result2 = await worker("B", 1)
    # 總時間：2 秒

    # 方法 2：先建立 Task，再 await（並發）
    task1 = asyncio.create_task(worker("C", 1))
    task2 = asyncio.create_task(worker("D", 1))
    result3 = await task1
    result4 = await task2
    # 總時間：1 秒

asyncio.run(main())
```

**重要**：`create_task()` 會立即排程任務，即使你還沒 `await` 它。

### gather() vs wait() vs TaskGroup

三種管理多個任務的方式：

```python
async def main():
    tasks = [worker(f"Task-{i}", 1) for i in range(3)]

    # gather()：等待所有完成，返回結果列表
    results = await asyncio.gather(*tasks)

    # wait()：更細緻的控制
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED  # 或 ALL_COMPLETED
    )

    # TaskGroup（Python 3.11+）：結構化並發
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(worker("A", 1))
        task2 = tg.create_task(worker("B", 1))
    # 離開 context 時，所有任務都已完成
```

| 方法 | 特點 | 使用場景 |
|------|------|---------|
| `gather()` | 簡單，返回結果列表 | 等待所有任務完成 |
| `wait()` | 可選擇等待策略 | 需要處理先完成的任務 |
| `TaskGroup` | 結構化，異常處理更好 | Python 3.11+，推薦使用 |

---

## 【實作層】任務生命週期

### 任務狀態

```python
async def demo():
    task = asyncio.create_task(asyncio.sleep(1))

    print(f"已完成：{task.done()}")      # False
    print(f"已取消：{task.cancelled()}")  # False

    await task

    print(f"已完成：{task.done()}")      # True
    print(f"結果：{task.result()}")      # None（sleep 返回 None）
```

### 取消任務

```python
async def long_running():
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("任務被取消")
        raise  # 重要：要重新拋出

async def main():
    task = asyncio.create_task(long_running())
    await asyncio.sleep(1)  # 讓任務開始
    task.cancel()           # 請求取消

    try:
        await task
    except asyncio.CancelledError:
        print("確認已取消")
```

### 超時控制

```python
async def main():
    # 方法 1：wait_for
    try:
        result = await asyncio.wait_for(long_running(), timeout=2.0)
    except asyncio.TimeoutError:
        print("超時")

    # 方法 2：timeout（Python 3.11+）
    try:
        async with asyncio.timeout(2.0):
            result = await long_running()
    except asyncio.TimeoutError:
        print("超時")
```

---

## 【常見錯誤】

### 1. 協程從未執行

```python
async def main():
    # 錯誤：只建立了協程物件，沒有執行
    worker("A", 1)  # RuntimeWarning!

    # 正確
    await worker("A", 1)
```

### 2. Task 被垃圾回收

```python
async def main():
    # 錯誤：task 沒有被引用，可能被 GC
    asyncio.create_task(worker("A", 1))

    # 正確：保持引用
    task = asyncio.create_task(worker("A", 1))
    await task
```

### 3. 異常被吞掉

```python
async def failing_task():
    raise ValueError("出錯了")

async def main():
    task = asyncio.create_task(failing_task())
    await asyncio.sleep(1)  # 異常不會在這裡拋出
    # 必須 await task 才會看到異常
```

---

## 思考題

1. `await task` 和 `await asyncio.gather(task)` 有什麼區別？
2. 為什麼 `CancelledError` 要重新拋出？
3. `TaskGroup` 相比 `gather()` 有什麼優勢？

## 實作練習

1. 實作一個函式，並發執行多個任務，但限制同時執行的數量（提示：使用 `Semaphore`）
2. 實作一個「競速」函式，返回最先完成的任務結果
3. 實作一個任務管理器，可以動態新增和取消任務

## 延伸閱讀

- [Python 官方文件 - Task](https://docs.python.org/3/library/asyncio-task.html)
- [PEP 654 - Exception Groups](https://peps.python.org/pep-0654/)

---

*上一章：[基礎概念與事件迴圈](../fundamentals/)*
*下一章：[設計模式與最佳實踐](../patterns/)*
