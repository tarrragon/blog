---
title: "案例：記憶體優化"
date: 2026-01-21
description: "用 __slots__ 和 weakref 優化快取系統的記憶體使用"
weight: 2
---

# 案例：記憶體優化

本案例基於 `.claude/lib/config_loader.py` 的實際程式碼，展示如何用 `__slots__` 和 `weakref` 優化記憶體使用。

## 先備知識

- [模組四：CPython 內部機制](../../)
- [4.2 記憶體管理與垃圾回收](../../memory-gc/)

## 問題背景

### 現有設計

`config_loader.py` 使用全域字典作為快取，這是一個常見的設計模式：

```python
# Global cache variables
_agents_config_cache: Optional[dict] = None
_quality_rules_cache: Optional[dict] = None

def load_agents_config() -> dict:
    """
    載入代理人配置

    使用模組層級變數作為快取，避免重複讀取檔案。
    """
    global _agents_config_cache
    if _agents_config_cache is None:
        try:
            _agents_config_cache = load_config("agents")
        except FileNotFoundError:
            _agents_config_cache = _get_default_agents_config()
    return _agents_config_cache

def clear_config_cache() -> None:
    """清除配置快取（用於測試或配置熱更新）"""
    global _agents_config_cache, _quality_rules_cache
    _agents_config_cache = None
    _quality_rules_cache = None
```

這種設計簡單直觀，但當系統需要快取更複雜的物件時，會遇到記憶體問題。

### 記憶體問題

當快取大量物件時：

- **Python 字典有額外開銷**：每個字典需要維護 hash table、keys、values
- **物件的 `__dict__` 佔用記憶體**：每個實例都有自己的屬性字典
- **快取可能導致記憶體洩漏**：強引用阻止物件被回收

讓我們用一個更複雜的快取場景來說明問題：

```python
import sys

class ConfigItem:
    """配置項目，模擬複雜的快取物件"""
    def __init__(self, key: str, value: str, metadata: dict):
        self.key = key
        self.value = value
        self.metadata = metadata
        self.access_count = 0
        self.last_accessed = None

# Create a config item and measure memory
item = ConfigItem("database.host", "localhost", {"type": "string"})

# Object size
print(f"ConfigItem size: {sys.getsizeof(item)} bytes")
# ConfigItem size: 48 bytes

# But the real cost is in __dict__
print(f"__dict__ size: {sys.getsizeof(item.__dict__)} bytes")
# __dict__ size: 184 bytes
```

當快取數萬個這樣的物件時，記憶體開銷會非常可觀。

---

## 進階解決方案

### 優化目標

1. 減少每個物件的記憶體佔用
2. 避免快取導致的記憶體洩漏
3. 保持 API 不變

### 實作步驟

#### 步驟 1：使用 `__slots__` 減少物件大小

`__slots__` 告訴 Python 這個類別只會有哪些屬性，讓直譯器可以用更緊湊的方式儲存資料：

```python
import sys

class ConfigItemWithoutSlots:
    """標準類別，使用 __dict__"""
    def __init__(self, key: str, value: str, metadata: dict):
        self.key = key
        self.value = value
        self.metadata = metadata
        self.access_count = 0
        self.last_accessed = None

class ConfigItemWithSlots:
    """使用 __slots__ 優化記憶體"""
    __slots__ = ['key', 'value', 'metadata', 'access_count', 'last_accessed']

    def __init__(self, key: str, value: str, metadata: dict):
        self.key = key
        self.value = value
        self.metadata = metadata
        self.access_count = 0
        self.last_accessed = None

# Compare memory usage
item_without = ConfigItemWithoutSlots("db.host", "localhost", {"type": "str"})
item_with = ConfigItemWithSlots("db.host", "localhost", {"type": "str"})

print(f"Without __slots__: {sys.getsizeof(item_without)} bytes")
print(f"With __slots__:    {sys.getsizeof(item_with)} bytes")

# The real difference is __dict__
print(f"__dict__ overhead: {sys.getsizeof(item_without.__dict__)} bytes")
# item_with has no __dict__!
try:
    item_with.__dict__
except AttributeError as e:
    print(f"No __dict__: {e}")
```

**記憶體結構比較：**

```text
沒有 __slots__:
┌──────────────────────────────────┐
│ PyObject header         (16 B)   │
│ __dict__ 指標            (8 B)   │
│ __weakref__ 指標         (8 B)   │
│                                  │
│ __dict__ (separate object):      │
│   - hash table          (64 B)   │
│   - keys array          (40 B)   │
│   - values array        (40 B)   │
│   - key strings        (~80 B)   │
│                                  │
│ Total: ~256 bytes per object     │
└──────────────────────────────────┘

有 __slots__:
┌──────────────────────────────────┐
│ PyObject header         (16 B)   │
│ key slot                 (8 B)   │
│ value slot               (8 B)   │
│ metadata slot            (8 B)   │
│ access_count slot        (8 B)   │
│ last_accessed slot       (8 B)   │
│                                  │
│ Total: ~56 bytes per object      │
└──────────────────────────────────┘
```

**大量物件的記憶體節省：**

```python
import sys
import tracemalloc

def measure_memory(cls, count=10000):
    """Measure memory for creating multiple objects"""
    tracemalloc.start()

    objects = [
        cls(f"key_{i}", f"value_{i}", {"index": i})
        for i in range(count)
    ]

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return current, peak, objects

# Measure both classes
mem_without, peak_without, _ = measure_memory(ConfigItemWithoutSlots)
mem_with, peak_with, _ = measure_memory(ConfigItemWithSlots)

print(f"Without __slots__: {mem_without / 1024 / 1024:.2f} MB")
print(f"With __slots__:    {mem_with / 1024 / 1024:.2f} MB")
print(f"Savings:           {(mem_without - mem_with) / 1024 / 1024:.2f} MB")
print(f"Ratio:             {mem_without / mem_with:.1f}x")

# Typical output:
# Without __slots__: 3.82 MB
# With __slots__:    1.15 MB
# Savings:           2.67 MB
# Ratio:             3.3x
```

#### 步驟 2：使用 weakref 避免強引用

`weakref` 讓我們可以引用物件，但不阻止它被垃圾回收：

```python
import weakref

class CacheableConfig:
    """可以被弱引用的配置物件"""
    __slots__ = ['key', 'value', '_data', '__weakref__']  # Note: __weakref__ slot

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value
        self._data = None

    def __repr__(self):
        return f"CacheableConfig({self.key!r}, {self.value!r})"

# Create object and weak reference
config = CacheableConfig("app.name", "MyApp")
weak_ref = weakref.ref(config)

print(f"Object exists: {weak_ref()}")
# Object exists: CacheableConfig('app.name', 'MyApp')

# Delete the strong reference
del config

print(f"After del: {weak_ref()}")
# After del: None
```

**使用 callback 追蹤物件回收：**

```python
import weakref

def on_finalize(ref):
    """Callback when object is garbage collected"""
    print(f"Object was garbage collected!")

config = CacheableConfig("db.port", "5432")
weak_ref = weakref.ref(config, on_finalize)

print("Deleting object...")
del config
# Output: Object was garbage collected!
```

#### 步驟 3：使用 WeakValueDictionary

`WeakValueDictionary` 是實作自動清理快取的利器：

```python
import weakref
from typing import Callable, TypeVar, Generic

T = TypeVar('T')

class WeakCache(Generic[T]):
    """
    Auto-cleaning cache using weak references.

    Objects are automatically removed from cache when no strong
    references exist outside the cache.
    """

    def __init__(self):
        self._cache: weakref.WeakValueDictionary[str, T] = (
            weakref.WeakValueDictionary()
        )
        self._hits = 0
        self._misses = 0

    def get(self, key: str, factory: Callable[[], T]) -> T:
        """
        Get item from cache, creating it if necessary.

        Args:
            key: Cache key
            factory: Function to create value if not cached

        Returns:
            Cached or newly created value
        """
        value = self._cache.get(key)
        if value is not None:
            self._hits += 1
            return value

        self._misses += 1
        value = factory()
        self._cache[key] = value
        return value

    def __len__(self) -> int:
        return len(self._cache)

    def stats(self) -> dict:
        """Return cache statistics"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1%}",
            "size": len(self._cache),
        }

# Demo: automatic cleanup
cache = WeakCache[CacheableConfig]()

# Create and cache object
config1 = cache.get("app.name", lambda: CacheableConfig("app.name", "MyApp"))
config2 = cache.get("app.name", lambda: CacheableConfig("app.name", "MyApp"))  # Cache hit

print(f"Cache size: {len(cache)}")  # 1
print(f"Same object: {config1 is config2}")  # True
print(f"Stats: {cache.stats()}")  # hits=1, misses=1

# Delete strong reference
del config1
del config2

# Object is garbage collected, cache is auto-cleaned
import gc
gc.collect()

print(f"Cache size after cleanup: {len(cache)}")  # 0
```

#### 步驟 4：測量記憶體使用

使用 `sys.getsizeof` 和 `tracemalloc` 進行精確測量：

```python
import sys
import tracemalloc
from pympler import asizeof  # pip install pympler

def measure_object_size(obj, label="Object"):
    """Measure object size using different methods"""

    # Basic size (doesn't include referenced objects)
    basic = sys.getsizeof(obj)

    # Deep size (includes all referenced objects)
    # Using pympler for accurate measurement
    deep = asizeof.asizeof(obj)

    print(f"{label}:")
    print(f"  sys.getsizeof: {basic:,} bytes")
    print(f"  pympler deep:  {deep:,} bytes")

    return basic, deep

# Compare different object types
item_without = ConfigItemWithoutSlots("key", "value", {"a": 1, "b": 2})
item_with = ConfigItemWithSlots("key", "value", {"a": 1, "b": 2})

measure_object_size(item_without, "Without __slots__")
measure_object_size(item_with, "With __slots__")

# Using tracemalloc for allocation tracking
def track_allocations():
    """Track memory allocations during execution"""
    tracemalloc.start()

    # Simulate creating many cached objects
    items = []
    for i in range(1000):
        items.append(ConfigItemWithSlots(
            f"config.item.{i}",
            f"value_{i}",
            {"index": i, "active": True}
        ))

    # Get snapshot
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')

    print("\nTop 5 memory allocations:")
    for stat in top_stats[:5]:
        print(f"  {stat}")

    # Get traced memory
    current, peak = tracemalloc.get_traced_memory()
    print(f"\nCurrent memory: {current / 1024:.1f} KB")
    print(f"Peak memory:    {peak / 1024:.1f} KB")

    tracemalloc.stop()
    return items

track_allocations()
```

**比較記憶體差異的完整腳本：**

```python
import sys
import gc
import tracemalloc
from dataclasses import dataclass

class StandardConfig:
    """Standard class with __dict__"""
    def __init__(self, key, value, metadata):
        self.key = key
        self.value = value
        self.metadata = metadata
        self.hits = 0

class SlottedConfig:
    """Optimized with __slots__"""
    __slots__ = ['key', 'value', 'metadata', 'hits']

    def __init__(self, key, value, metadata):
        self.key = key
        self.value = value
        self.metadata = metadata
        self.hits = 0

@dataclass
class DataclassConfig:
    """Using dataclass"""
    key: str
    value: str
    metadata: dict
    hits: int = 0

@dataclass(slots=True)  # Python 3.10+
class SlottedDataclass:
    """Dataclass with __slots__"""
    key: str
    value: str
    metadata: dict
    hits: int = 0

def benchmark_memory(cls, count=10000, label=""):
    """Benchmark memory usage for a class"""
    gc.collect()
    tracemalloc.start()

    objects = [
        cls(f"key_{i}", f"value_{i}", {"index": i})
        for i in range(count)
    ]

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    per_object = current / count
    print(f"{label or cls.__name__:25} | "
          f"{current/1024:8.1f} KB | "
          f"{per_object:6.1f} B/obj")

    return objects  # Keep reference to prevent GC

print(f"{'Class':25} | {'Total':>10} | {'Per Object':>10}")
print("-" * 55)

benchmark_memory(StandardConfig)
benchmark_memory(SlottedConfig)
benchmark_memory(DataclassConfig)
benchmark_memory(SlottedDataclass)

# Typical output:
# Class                     |      Total |  Per Object
# -------------------------------------------------------
# StandardConfig            |   2578.5 KB |  263.6 B/obj
# SlottedConfig             |    859.4 KB |   87.9 B/obj
# DataclassConfig           |   2656.3 KB |  271.6 B/obj
# SlottedDataclass          |    898.4 KB |   91.9 B/obj
```

---

### 完整程式碼

以下是整合所有優化技術的完整實作：

```python
"""
Memory-optimized configuration cache system.

This module demonstrates:
- Using __slots__ to reduce object memory footprint
- Using weakref for automatic cache cleanup
- Using tracemalloc for memory profiling

Based on patterns from .claude/lib/config_loader.py
"""

import weakref
import sys
import gc
import tracemalloc
from typing import Any, Callable, Generic, Optional, TypeVar
from pathlib import Path
from datetime import datetime

T = TypeVar('T')

class ConfigEntry:
    """
    Memory-optimized configuration entry.

    Uses __slots__ to reduce memory footprint by ~3x compared
    to regular classes.
    """
    __slots__ = [
        'key', 'value', 'source', 'loaded_at',
        'access_count', '__weakref__'
    ]

    def __init__(
        self,
        key: str,
        value: Any,
        source: Optional[str] = None
    ):
        self.key = key
        self.value = value
        self.source = source
        self.loaded_at = datetime.now()
        self.access_count = 0

    def __repr__(self) -> str:
        return (
            f"ConfigEntry(key={self.key!r}, "
            f"value={self.value!r}, "
            f"accesses={self.access_count})"
        )

    def touch(self) -> None:
        """Record an access to this entry"""
        self.access_count += 1

class SmartConfigCache:
    """
    Smart configuration cache with automatic memory management.

    Features:
    - Weak references for automatic cleanup
    - Memory usage tracking
    - Hit/miss statistics
    - Optional size limits

    Example:
        cache = SmartConfigCache(max_size=1000)

        # Get or create config
        config = cache.get_or_create(
            "database.host",
            lambda: ConfigEntry("database.host", "localhost", "env")
        )

        # Check stats
        print(cache.stats())
    """

    def __init__(self, max_size: Optional[int] = None):
        """
        Initialize the cache.

        Args:
            max_size: Maximum number of entries. None for unlimited.
        """
        self._cache: weakref.WeakValueDictionary[str, ConfigEntry] = (
            weakref.WeakValueDictionary()
        )
        self._strong_refs: dict[str, ConfigEntry] = {}  # Keep important items
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[ConfigEntry]:
        """
        Get entry from cache.

        Args:
            key: Configuration key

        Returns:
            ConfigEntry if found, None otherwise
        """
        # Check strong refs first
        entry = self._strong_refs.get(key)
        if entry is not None:
            self._hits += 1
            entry.touch()
            return entry

        # Then check weak refs
        entry = self._cache.get(key)
        if entry is not None:
            self._hits += 1
            entry.touch()
            return entry

        self._misses += 1
        return None

    def get_or_create(
        self,
        key: str,
        factory: Callable[[], ConfigEntry],
        keep_strong: bool = False
    ) -> ConfigEntry:
        """
        Get existing entry or create new one.

        Args:
            key: Configuration key
            factory: Function to create entry if not found
            keep_strong: If True, keep a strong reference (won't auto-cleanup)

        Returns:
            Existing or newly created ConfigEntry
        """
        entry = self.get(key)
        if entry is not None:
            return entry

        # Create new entry
        entry = factory()
        self._cache[key] = entry

        if keep_strong:
            self._enforce_size_limit()
            self._strong_refs[key] = entry

        return entry

    def _enforce_size_limit(self) -> None:
        """Evict old entries if cache is full"""
        if self._max_size is None:
            return

        while len(self._strong_refs) >= self._max_size:
            # Evict least accessed entry
            if not self._strong_refs:
                break

            min_key = min(
                self._strong_refs.keys(),
                key=lambda k: self._strong_refs[k].access_count
            )
            del self._strong_refs[min_key]
            self._evictions += 1

    def pin(self, key: str) -> bool:
        """
        Pin an entry to prevent automatic cleanup.

        Args:
            key: Configuration key

        Returns:
            True if entry was pinned, False if not found
        """
        entry = self._cache.get(key)
        if entry is None:
            return False

        self._enforce_size_limit()
        self._strong_refs[key] = entry
        return True

    def unpin(self, key: str) -> bool:
        """
        Unpin an entry to allow automatic cleanup.

        Args:
            key: Configuration key

        Returns:
            True if entry was unpinned, False if not found
        """
        if key in self._strong_refs:
            del self._strong_refs[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cached entries"""
        self._cache.clear()
        self._strong_refs.clear()

    def stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with hits, misses, hit_rate, size, pinned, evictions
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1%}",
            "total_size": len(self._cache) + len(self._strong_refs),
            "weak_refs": len(self._cache),
            "pinned": len(self._strong_refs),
            "evictions": self._evictions,
        }

    def memory_usage(self) -> dict:
        """
        Estimate memory usage of cached entries.

        Returns:
            Dict with entry_count, estimated_bytes, per_entry_bytes
        """
        all_entries = list(self._cache.values()) + list(self._strong_refs.values())

        if not all_entries:
            return {
                "entry_count": 0,
                "estimated_bytes": 0,
                "per_entry_bytes": 0,
            }

        # Estimate based on first entry
        sample = all_entries[0]
        per_entry = sys.getsizeof(sample)

        return {
            "entry_count": len(all_entries),
            "estimated_bytes": per_entry * len(all_entries),
            "per_entry_bytes": per_entry,
        }

def demo_memory_optimization():
    """Demonstrate memory optimization techniques"""

    print("=" * 60)
    print("Memory Optimization Demo")
    print("=" * 60)

    # Start memory tracking
    tracemalloc.start()
    gc.collect()
    snapshot1 = tracemalloc.take_snapshot()

    # Create cache and populate
    cache = SmartConfigCache(max_size=100)

    # Simulate loading many configurations
    entries = []
    for i in range(1000):
        entry = cache.get_or_create(
            f"config.item.{i}",
            lambda i=i: ConfigEntry(
                f"config.item.{i}",
                f"value_{i}",
                "demo"
            ),
            keep_strong=(i < 100)  # Pin first 100
        )
        entries.append(entry)

    # Take snapshot after creation
    gc.collect()
    snapshot2 = tracemalloc.take_snapshot()

    # Print stats
    print("\nCache Statistics:")
    for key, value in cache.stats().items():
        print(f"  {key}: {value}")

    print("\nMemory Usage:")
    for key, value in cache.memory_usage().items():
        print(f"  {key}: {value:,}")

    # Show memory diff
    diff = snapshot2.compare_to(snapshot1, 'lineno')
    print("\nTop 5 Memory Allocations:")
    for stat in diff[:5]:
        print(f"  {stat}")

    # Demo weak reference cleanup
    print("\n" + "-" * 60)
    print("Weak Reference Cleanup Demo")
    print("-" * 60)

    print(f"Before cleanup - Cache size: {cache.stats()['total_size']}")

    # Delete external references to unpinned entries
    del entries
    gc.collect()

    print(f"After cleanup  - Cache size: {cache.stats()['total_size']}")
    print("(Only pinned entries remain)")

    tracemalloc.stop()

if __name__ == "__main__":
    demo_memory_optimization()
```

---

### 使用範例

```python
from memory_optimized_cache import SmartConfigCache, ConfigEntry

# Initialize cache with size limit
cache = SmartConfigCache(max_size=1000)

# Load configuration
def load_database_config():
    """Factory function to load database config"""
    return ConfigEntry(
        key="database",
        value={
            "host": "localhost",
            "port": 5432,
            "name": "myapp"
        },
        source="config.yaml"
    )

# Get or create (with strong reference for important config)
db_config = cache.get_or_create(
    "database",
    load_database_config,
    keep_strong=True  # Keep in memory
)

print(f"Database host: {db_config.value['host']}")

# Temporary config (will be auto-cleaned when not referenced)
temp_config = cache.get_or_create(
    "temp.setting",
    lambda: ConfigEntry("temp.setting", "temporary", "runtime")
)

# Check statistics
print(cache.stats())
# {'hits': 0, 'misses': 2, 'hit_rate': '0.0%',
#  'total_size': 2, 'weak_refs': 1, 'pinned': 1, 'evictions': 0}

# Memory usage
print(cache.memory_usage())
# {'entry_count': 2, 'estimated_bytes': 112, 'per_entry_bytes': 56}
```

---

## 設計權衡

### `__slots__` vs 標準類別

| 面向 | 標準類別 | `__slots__` |
| ---- | -------- | ----------- |
| **記憶體佔用** | 較多（有 `__dict__`） | 較少（節省 ~60-70%） |
| **動態屬性** | 支援 `obj.new_attr = x` | 不支援（除非加 `__dict__`） |
| **繼承** | 簡單 | 子類別需要自己的 `__slots__` |
| **弱引用** | 預設支援 | 需要加入 `__weakref__` slot |
| **Pickle** | 直接支援 | 需要 `__getstate__`/`__setstate__` |
| **多重繼承** | 正常運作 | 多個父類別不能都有非空 `__slots__` |

### 強引用 vs 弱引用快取

| 面向 | 強引用快取 | 弱引用快取 |
| ---- | --------- | --------- |
| **記憶體管理** | 需要手動清理 | 自動清理 |
| **資料保證** | 資料一定存在 | 資料可能被回收 |
| **適用場景** | 關鍵配置 | 暫時性資料 |
| **實作複雜度** | 簡單 | 稍微複雜 |

### 何時使用哪種技術？

```text
決策樹：

物件數量多嗎？
├── 是 → 考慮 __slots__
│   └── 需要動態屬性嗎？
│       ├── 是 → __slots__ = [..., '__dict__']
│       └── 否 → __slots__ = [...]
└── 否 → 標準類別即可

快取可能無限增長嗎？
├── 是 → 使用 WeakValueDictionary 或 LRU
└── 否 → 普通字典即可

資料可以被回收嗎？
├── 是 → weakref
└── 否 → 強引用
```

---

## 什麼時候該用這個技術？

### 適合使用

- **建立大量小物件**：如資料點、事件、配置項目
- **記憶體使用是瓶頸**：經過 profiling 確認
- **快取可能無限增長**：如用戶 session、請求資料
- **長時間運行的服務**：如 web server、daemon

### 不建議使用

- **物件數量很少**：優化效果不明顯
- **需要動態新增屬性**：`__slots__` 會限制彈性
- **過早優化**：先確認是否真的有問題
- **程式碼可讀性優先**：標準類別更直觀

### 優化決策流程

```python
# Step 1: Profile first!
# Don't optimize until you know where the problem is

import tracemalloc

tracemalloc.start()
# ... run your code ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)

# Step 2: If memory is the issue, identify the class
# Look for classes with many instances

import gc
from collections import Counter

counter = Counter(type(obj).__name__ for obj in gc.get_objects())
print(counter.most_common(10))

# Step 3: Only then apply __slots__ to hot classes
```

---

## 練習

### 基礎練習：比較有無 `__slots__` 的記憶體差異

撰寫一個腳本，比較以下三種類別建立 100,000 個實例的記憶體使用：

```python
# Exercise: Complete this benchmark script

import sys
import tracemalloc
from dataclasses import dataclass

# 1. Standard class
class PointStandard:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

# 2. Class with __slots__
class PointSlots:
    __slots__ = ['x', 'y', 'z']
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

# 3. Named tuple
from collections import namedtuple
PointNamed = namedtuple('PointNamed', ['x', 'y', 'z'])

# TODO: Write benchmark function
def benchmark(cls, count=100000):
    """Measure memory for creating `count` instances"""
    pass  # Implement this

# TODO: Compare results
# Expected: PointSlots uses ~3x less memory than PointStandard
```

### 進階練習：實作 weakref 快取

建立一個 `ImageCache` 類別，具有以下功能：

```python
# Exercise: Implement ImageCache

class ImageCache:
    """
    Cache for image data with automatic cleanup.

    Requirements:
    - Use WeakValueDictionary for auto-cleanup
    - Track hit/miss statistics
    - Support maximum size limit
    - Provide memory usage estimation

    Example usage:
        cache = ImageCache(max_size=100)

        img = cache.get_or_load("photo.jpg", lambda: load_image("photo.jpg"))

        print(cache.stats())
        # {'hits': 0, 'misses': 1, 'size': 1}
    """

    def __init__(self, max_size=None):
        # TODO: Initialize cache
        pass

    def get_or_load(self, key, loader):
        # TODO: Implement get or load logic
        pass

    def stats(self):
        # TODO: Return cache statistics
        pass
```

### 挑戰題：用 tracemalloc 追蹤記憶體洩漏

給定以下有記憶體洩漏的程式碼，使用 `tracemalloc` 找出問題並修復：

```python
# Exercise: Find and fix the memory leak

class EventHandler:
    _handlers = []  # Class variable - potential leak!

    def __init__(self, name):
        self.name = name
        self.callbacks = []
        EventHandler._handlers.append(self)  # Leak: strong reference

    def register(self, callback):
        self.callbacks.append(callback)

    def fire(self, event):
        for cb in self.callbacks:
            cb(event)

def process_events():
    """This function creates handlers but never cleans them up"""
    for i in range(1000):
        handler = EventHandler(f"handler_{i}")
        handler.register(lambda e: print(e))
        handler.fire(f"event_{i}")
        # handler goes out of scope but is still in _handlers!

# TODO:
# 1. Use tracemalloc to measure memory growth
# 2. Identify the leak
# 3. Fix EventHandler to use weak references
# 4. Verify the fix with tracemalloc
```

---

## 延伸閱讀

- [`__slots__` 官方文件](https://docs.python.org/3/reference/datamodel.html#slots)
- [weakref 官方文件](https://docs.python.org/3/library/weakref.html)
- [tracemalloc 官方文件](https://docs.python.org/3/library/tracemalloc.html)
- [Pympler - Memory profiling](https://pympler.readthedocs.io/)
- [Python Memory Management - Real Python](https://realpython.com/python-memory-management/)

---

*上一章：[效能分析實戰](../profiling/)*
*返回：[模組四：CPython 內部機制](../../)*
