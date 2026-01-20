---
title: "1.4 實戰：與同步程式碼整合"
date: 2026-01-20
description: "在現有專案中引入 asyncio，處理同步與異步的混合場景"
weight: 4
---

# 實戰：與同步程式碼整合

本章討論如何在現有專案中引入 asyncio，以及同步與異步程式碼的整合策略。

## 先備知識

- [1.3 設計模式與最佳實踐](../patterns/)

## 本章目標

學完本章後，你將能夠：

1. 在異步程式中呼叫同步函式
2. 在同步程式中呼叫異步函式
3. 制定漸進式遷移策略
4. 與常見框架整合

---

## 【原理層】混合程式設計的挑戰

### 兩個世界的衝突

同步和異步程式碼有根本性的差異：

```python
# 同步世界
def sync_fetch(url):
    response = requests.get(url)  # 阻塞等待
    return response.text

# 異步世界
async def async_fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()  # 非阻塞等待
```

問題在於：
- 在異步函式中呼叫同步函式會阻塞事件迴圈
- 在同步函式中無法直接 `await` 異步函式

### run_in_executor：橋樑

`run_in_executor` 在執行緒池中執行同步函式：

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def main():
    loop = asyncio.get_running_loop()

    # 使用預設執行緒池
    result = await loop.run_in_executor(None, sync_blocking_func)

    # 使用自訂執行緒池
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = await loop.run_in_executor(pool, sync_blocking_func)
```

---

## 【設計層】整合策略

### 在異步程式中呼叫同步函式

```python
import asyncio
import requests

def sync_fetch(url):
    return requests.get(url).text

async def async_wrapper(url):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, sync_fetch, url)

async def main():
    # 並發呼叫同步函式
    urls = ["https://example.com"] * 5
    tasks = [async_wrapper(url) for url in urls]
    results = await asyncio.gather(*tasks)
```

### 在同步程式中呼叫異步函式

```python
import asyncio

async def async_fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

def sync_main():
    # 方法 1：asyncio.run()
    result = asyncio.run(async_fetch("https://example.com"))

    # 方法 2：在已有事件迴圈中（例如 Jupyter）
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(async_fetch("https://example.com"))
```

### 漸進式遷移策略

```text
階段 1：識別 I/O 瓶頸
    └─→ profiling，找出最常等待的地方

階段 2：引入異步版本
    └─→ 新功能用異步，舊功能保持同步

階段 3：包裝同步程式碼
    └─→ 用 run_in_executor 包裝同步函式

階段 4：逐步替換
    └─→ 用異步函式庫替換同步函式庫

階段 5：完全異步（可選）
    └─→ 整個應用改為異步
```

---

## 【實作層】框架整合

### FastAPI / Starlette

FastAPI 原生支援異步：

```python
from fastapi import FastAPI
import asyncio

app = FastAPI()

@app.get("/async")
async def async_endpoint():
    await asyncio.sleep(1)
    return {"message": "異步完成"}

@app.get("/sync")
def sync_endpoint():
    # FastAPI 會自動在執行緒池中執行
    time.sleep(1)
    return {"message": "同步完成"}
```

### aiohttp 客戶端

```python
import aiohttp
import asyncio

async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        async def fetch(url):
            async with session.get(url) as response:
                return await response.json()

        return await asyncio.gather(*[fetch(url) for url in urls])
```

### SQLAlchemy 2.0

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine("postgresql+asyncpg://...")
async_session = sessionmaker(engine, class_=AsyncSession)

async def get_user(user_id):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
```

---

## 【測試策略】

### 測試異步程式碼

```python
import pytest
import asyncio

# pytest-asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await async_fetch("https://example.com")
    assert result is not None

# 使用 asyncio.run
def test_with_asyncio_run():
    result = asyncio.run(async_fetch("https://example.com"))
    assert result is not None
```

### Mock 異步函式

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock():
    mock_fetch = AsyncMock(return_value="mocked data")

    with patch("module.async_fetch", mock_fetch):
        result = await process_data()
        assert result == "processed: mocked data"
```

---

## 思考題

1. 為什麼 FastAPI 可以同時支援同步和異步端點？
2. `run_in_executor` 使用執行緒池，會不會有 GIL 的問題？
3. 在什麼情況下不值得遷移到 asyncio？

## 實作練習

1. 將一個使用 requests 的爬蟲改寫為使用 aiohttp
2. 實作一個支援同步和異步呼叫的函式庫包裝器
3. 為異步程式碼撰寫單元測試

## 延伸閱讀

- [FastAPI 官方文件](https://fastapi.tiangolo.com/)
- [SQLAlchemy 異步文件](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [aiohttp 文件](https://docs.aiohttp.org/)

---

*上一章：[設計模式與最佳實踐](../patterns/)*
*下一模組：[模組二：元編程](../../02-metaprogramming/)*
