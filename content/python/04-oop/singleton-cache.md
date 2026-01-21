---
title: "4.4 單例與快取模式"
date: 2026-01-20
description: "控制物件生命週期"
weight: 4
---

# 單例與快取模式

在某些情況下，我們需要控制物件的建立次數或快取計算結果以提升效能。本章介紹 Hook 系統中使用的快取模式。

## 模組級快取

Python 模組是天然的單例——模組只會被載入一次。利用這個特性，可以實作簡單的快取。

### 實際範例：配置快取

來自 `.claude/lib/config_loader.py`：

```python
from typing import Optional

# 模組級快取變數
_agents_config_cache: Optional[dict] = None
_quality_rules_cache: Optional[dict] = None

def load_agents_config() -> dict:
    """
    載入代理人配置

    使用模組級快取，避免重複讀取檔案。
    """
    global _agents_config_cache

    # 檢查快取
    if _agents_config_cache is None:
        try:
            _agents_config_cache = load_config("agents")
        except FileNotFoundError:
            _agents_config_cache = _get_default_agents_config()

    return _agents_config_cache

def load_quality_rules() -> dict:
    """載入品質規則配置"""
    global _quality_rules_cache

    if _quality_rules_cache is None:
        try:
            _quality_rules_cache = load_config("quality_rules")
        except FileNotFoundError:
            _quality_rules_cache = _get_default_quality_rules()

    return _quality_rules_cache

def clear_config_cache() -> None:
    """
    清除配置快取

    用於測試或配置熱更新。
    """
    global _agents_config_cache, _quality_rules_cache
    _agents_config_cache = None
    _quality_rules_cache = None
```

### 使用方式

```python
# 第一次呼叫：從檔案載入
config1 = load_agents_config()

# 第二次呼叫：直接返回快取
config2 = load_agents_config()

# config1 is config2  # True

# 需要重新載入時
clear_config_cache()
config3 = load_agents_config()  # 重新從檔案載入
```

## 為什麼使用這個模式？

### 效能考量

```python
# 沒有快取：每次都讀取檔案
def load_config_slow() -> dict:
    with open("config.yaml") as f:
        return yaml.safe_load(f)  # I/O 操作

# 有快取：只讀取一次
def load_config_fast() -> dict:
    global _cache
    if _cache is None:
        with open("config.yaml") as f:
            _cache = yaml.safe_load(f)
    return _cache
```

### 一致性

```python
# 確保所有地方使用相同的配置
config_a = load_agents_config()
config_b = load_agents_config()

# 修改 config_a 會影響 config_b（因為是同一個物件）
# 這可能是優點也可能是缺點，取決於使用場景
```

## 函式裝飾器快取

### @functools.lru_cache

Python 標準庫提供的快取裝飾器：

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(n: int) -> int:
    """計算結果會被快取"""
    print(f"Computing for {n}...")
    return sum(range(n))

# 第一次呼叫：執行計算
result1 = expensive_computation(1000)  # 印出 "Computing for 1000..."

# 第二次呼叫：直接返回快取
result2 = expensive_computation(1000)  # 不印出任何東西

# 清除快取
expensive_computation.cache_clear()
```

### @functools.cache (Python 3.9+)

無大小限制的快取：

```python
from functools import cache

@cache
def fibonacci(n: int) -> int:
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# 快取讓遞迴變得高效
fibonacci(100)  # 瞬間完成
```

## 手動實作快取

### 字典快取

```python
_cache: dict = {}

def get_user(user_id: int) -> dict:
    """取得使用者資料，使用快取"""
    if user_id not in _cache:
        _cache[user_id] = fetch_from_database(user_id)
    return _cache[user_id]

def invalidate_user(user_id: int) -> None:
    """使特定使用者的快取失效"""
    _cache.pop(user_id, None)

def clear_all_cache() -> None:
    """清除所有快取"""
    _cache.clear()
```

### 帶過期時間的快取

```python
from time import time
from typing import Optional, Any

_cache: dict = {}
_cache_time: dict = {}
CACHE_TTL = 300  # 5 分鐘

def get_with_ttl(key: str) -> Optional[Any]:
    """取得快取，檢查是否過期"""
    if key in _cache:
        if time() - _cache_time[key] < CACHE_TTL:
            return _cache[key]
        else:
            # 快取過期
            del _cache[key]
            del _cache_time[key]
    return None

def set_with_ttl(key: str, value: Any) -> None:
    """設定快取"""
    _cache[key] = value
    _cache_time[key] = time()
```

## 單例模式

當確實需要單例時的實作方式：

### 使用模組（最簡單）

```python
# singleton.py
class _Singleton:
    def __init__(self):
        self.value = 0

instance = _Singleton()

# 使用
from singleton import instance
instance.value = 42
```

### 使用類別裝飾器

```python
def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance

@singleton
class Database:
    def __init__(self):
        print("Connecting to database...")

# 使用
db1 = Database()  # 印出 "Connecting..."
db2 = Database()  # 不印出（返回同一個實例）
db1 is db2  # True
```

### 使用 __new__

```python
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

# 使用
s1 = Singleton()
s2 = Singleton()
s1 is s2  # True
```

## Hook 系統的實際應用

### 配置載入器的設計

```python
# config_loader.py

from typing import Optional

# 私有快取
_agents_config_cache: Optional[dict] = None

def load_agents_config() -> dict:
    """
    載入代理人配置

    特點：
    1. 使用模組級快取
    2. 支援預設配置
    3. 提供清除快取的方法
    """
    global _agents_config_cache

    if _agents_config_cache is None:
        try:
            _agents_config_cache = load_config("agents")
        except FileNotFoundError:
            # 返回預設配置
            _agents_config_cache = _get_default_agents_config()

    return _agents_config_cache

def _get_default_agents_config() -> dict:
    """預設配置"""
    return {
        "known_agents": [
            "basil-hook-architect",
            "thyme-documentation-integrator",
            # ...
        ],
        "agent_dispatch_rules": {
            "Hook 開發": "basil-hook-architect",
            # ...
        }
    }
```

## 測試快取程式碼

```python
import unittest

class TestConfigLoader(unittest.TestCase):

    def setUp(self):
        # 每個測試前清除快取
        clear_config_cache()

    def tearDown(self):
        # 每個測試後清除快取
        clear_config_cache()

    def test_config_is_cached(self):
        """測試配置被快取"""
        config1 = load_agents_config()
        config2 = load_agents_config()

        # 應該是同一個物件
        self.assertIs(config1, config2)

    def test_clear_cache_works(self):
        """測試清除快取"""
        config1 = load_agents_config()
        clear_config_cache()
        config2 = load_agents_config()

        # 應該是不同的物件
        self.assertIsNot(config1, config2)
```

## 最佳實踐

### 1. 提供清除快取的方法

```python
# 好：可以清除快取
def clear_config_cache():
    global _cache
    _cache = None

# 不好：無法重新載入
```

### 2. 考慮執行緒安全

```python
import threading

_lock = threading.Lock()
_cache = None

def get_cached_value():
    global _cache
    if _cache is None:
        with _lock:
            # 雙重檢查
            if _cache is None:
                _cache = expensive_computation()
    return _cache
```

### 3. 文件化快取行為

```python
def load_config() -> dict:
    """
    載入配置

    Note:
        結果會被快取，後續呼叫返回同一個物件。
        使用 clear_config_cache() 可重新載入。
    """
```

## 思考題

1. 模組級快取和 `@lru_cache` 有什麼區別？
2. 為什麼 `clear_config_cache()` 很重要？
3. 在多執行緒環境下，模組級快取可能有什麼問題？

## 實作練習

1. 使用 `@lru_cache` 實作一個帶快取的 API 呼叫函式
2. 實作一個帶 TTL（存活時間）的快取
3. 為現有的快取添加執行緒安全保護

## 延伸閱讀（進階系列）

- [進階設計模式](/python-advanced/03-design-patterns/) - 更多設計模式的深入探討
- [快取生命週期管理](/python-advanced/03-design-patterns/case-studies/cache-lifecycle/) - 進階快取策略
- [實戰效能優化：LRU 快取](/python-advanced/08-practical-optimization/case-studies/lru-cache-branch/) - lru_cache 的實際應用

---

*上一章：[工廠模式](../factory/)*
*下一模組：[錯誤處理與測試](../../05-error-testing/)*
