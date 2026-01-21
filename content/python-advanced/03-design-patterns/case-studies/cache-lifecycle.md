---
title: "案例：快取生命週期管理"
date: 2026-01-21
description: "用 Context Manager 控制快取的生命週期，解決全域狀態問題"
weight: 1
---

# 案例：快取生命週期管理

本案例基於 `.claude/lib/config_loader.py` 的實際程式碼，展示如何用 Context Manager 管理快取生命週期。

## 先備知識

- [3.3 進階上下文管理](../../context-managers/)

## 問題背景

### 現有設計

`config_loader.py` 使用全域變數實現快取：

```python
# 全域快取變數
_agents_config_cache: Optional[dict] = None
_quality_rules_cache: Optional[dict] = None

def load_agents_config() -> dict:
    """
    載入代理人配置

    使用全域快取避免重複讀取檔案。
    """
    global _agents_config_cache
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
    """清除配置快取（用於測試或配置熱更新）"""
    global _agents_config_cache, _quality_rules_cache
    _agents_config_cache = None
    _quality_rules_cache = None
```

### 這個設計的優點

1. **簡單直覺**：全域變數是最簡單的快取方式
2. **效能好**：配置只讀取一次
3. **API 簡潔**：呼叫者不需要管理快取

### 這個設計的限制

**問題 1：測試難以隔離**

```python
def test_load_agents_config():
    # 測試 A：預設配置
    config = load_agents_config()
    assert "known_agents" in config

def test_load_agents_config_custom():
    # 測試 B：自訂配置檔案
    # 問題：測試 A 的快取會影響測試 B！
    config = load_agents_config()
    # 可能拿到測試 A 的快取結果
```

**問題 2：快取生命週期不明確**

```python
def process_hooks():
    config = load_agents_config()
    # ... 處理完成

    # 問題：什麼時候應該清除快取？
    # 如果配置檔案改了，這裡會用到舊的快取
```

**問題 3：清除快取容易忘記**

```python
def test_something():
    # 設定測試環境
    os.environ["CLAUDE_PROJECT_DIR"] = "/tmp/test"

    # 執行測試
    config = load_agents_config()

    # 問題：忘記清除快取！
    # 下一個測試會用到這個測試的快取
```

## 進階解決方案：Context Manager 管理快取

### 設計目標

1. **明確的快取範圍**：快取的生命週期有明確的開始和結束
2. **自動清理**：離開範圍時自動清除快取
3. **測試友好**：每個測試可以有獨立的快取

### 實作步驟

#### 步驟 1：建立快取管理類別

```python
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional
import os

class ConfigManager:
    """
    配置管理器

    用 Context Manager 控制快取的生命週期，
    解決全域快取的問題。
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            project_root: 專案根目錄，預設從環境變數讀取
        """
        if project_root is None:
            project_root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        self.project_root = Path(project_root)
        self._cache: dict[str, Any] = {}

    @property
    def config_dir(self) -> Path:
        """配置目錄路徑"""
        return self.project_root / ".claude" / "config"

    def load_config(self, name: str) -> dict:
        """
        載入配置（使用快取）

        Args:
            name: 配置名稱

        Returns:
            配置內容
        """
        if name not in self._cache:
            self._cache[name] = self._load_from_file(name)
        return self._cache[name]

    def _load_from_file(self, name: str) -> dict:
        """從檔案載入配置（內部方法）"""
        yaml_path = self.config_dir / f"{name}.yaml"
        if yaml_path.exists():
            import yaml
            with open(yaml_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        raise FileNotFoundError(f"Config not found: {name}")

    def clear_cache(self) -> None:
        """清除所有快取"""
        self._cache.clear()
```

#### 步驟 2：加入 Context Manager 支援

```python
class ConfigManager:
    # ... 前面的程式碼 ...

    @contextmanager
    def cached_scope(self) -> Iterator["ConfigManager"]:
        """
        快取範圍 Context Manager

        在這個範圍內，配置會被快取。
        離開範圍時自動清除快取。

        Yields:
            ConfigManager: 自己，方便鏈式呼叫

        Example:
            manager = ConfigManager()
            with manager.cached_scope():
                config = manager.load_config("agents")
                # ... 使用配置 ...
            # 離開時快取自動清除
        """
        try:
            yield self
        finally:
            self.clear_cache()

    @contextmanager
    def isolated_scope(
        self,
        project_root: Optional[str] = None
    ) -> Iterator["ConfigManager"]:
        """
        隔離範圍 Context Manager

        建立一個完全隔離的配置環境，
        適合用於測試。

        Args:
            project_root: 臨時的專案根目錄

        Yields:
            ConfigManager: 新的管理器實例

        Example:
            with manager.isolated_scope("/tmp/test") as isolated:
                config = isolated.load_config("agents")
                # 完全隔離，不影響原本的 manager
        """
        isolated_manager = ConfigManager(
            project_root=project_root or str(self.project_root)
        )
        try:
            yield isolated_manager
        finally:
            isolated_manager.clear_cache()
```

#### 步驟 3：加入便利方法

```python
class ConfigManager:
    # ... 前面的程式碼 ...

    def load_agents_config(self) -> dict:
        """載入代理人配置（帶預設值）"""
        try:
            return self.load_config("agents")
        except FileNotFoundError:
            return self._get_default_agents_config()

    def load_quality_rules(self) -> dict:
        """載入品質規則配置（帶預設值）"""
        try:
            return self.load_config("quality_rules")
        except FileNotFoundError:
            return self._get_default_quality_rules()

    def _get_default_agents_config(self) -> dict:
        """預設代理人配置"""
        return {
            "known_agents": ["basil", "thyme", "mint"],
            "agent_dispatch_rules": {},
        }

    def _get_default_quality_rules(self) -> dict:
        """預設品質規則配置"""
        return {
            "trigger_conditions": {"allowed_tools": ["Write", "Edit"]},
            "cache": {"ttl_minutes": 5},
        }
```

### 完整程式碼

```python
#!/usr/bin/env python3
"""
快取生命週期管理 - 完整範例

展示如何用 Context Manager 管理配置快取的生命週期。
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional
import os

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    import json

class ConfigManager:
    """
    配置管理器

    用 Context Manager 控制快取的生命週期。
    """

    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            project_root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        self.project_root = Path(project_root)
        self._cache: dict[str, Any] = {}

    @property
    def config_dir(self) -> Path:
        return self.project_root / ".claude" / "config"

    # ===== 載入方法 =====

    def load_config(self, name: str) -> dict:
        """載入配置（使用快取）"""
        if name not in self._cache:
            self._cache[name] = self._load_from_file(name)
        return self._cache[name]

    def _load_from_file(self, name: str) -> dict:
        """從檔案載入配置"""
        yaml_path = self.config_dir / f"{name}.yaml"
        json_path = self.config_dir / f"{name}.json"

        if yaml_path.exists() and HAS_YAML:
            with open(yaml_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)

        raise FileNotFoundError(f"Config not found: {name}")

    def clear_cache(self) -> None:
        """清除所有快取"""
        self._cache.clear()

    # ===== Context Manager =====

    @contextmanager
    def cached_scope(self) -> Iterator["ConfigManager"]:
        """快取範圍：離開時自動清除快取"""
        try:
            yield self
        finally:
            self.clear_cache()

    @contextmanager
    def isolated_scope(
        self,
        project_root: Optional[str] = None
    ) -> Iterator["ConfigManager"]:
        """隔離範圍：建立獨立的配置環境"""
        isolated = ConfigManager(project_root or str(self.project_root))
        try:
            yield isolated
        finally:
            isolated.clear_cache()

    # ===== 便利方法 =====

    def load_agents_config(self) -> dict:
        """載入代理人配置"""
        try:
            return self.load_config("agents")
        except FileNotFoundError:
            return {"known_agents": [], "agent_dispatch_rules": {}}

    def load_quality_rules(self) -> dict:
        """載入品質規則配置"""
        try:
            return self.load_config("quality_rules")
        except FileNotFoundError:
            return {"trigger_conditions": {}, "cache": {"ttl_minutes": 5}}

# ===== 全域便利函式（相容舊 API）=====

_default_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """獲取預設的配置管理器"""
    global _default_manager
    if _default_manager is None:
        _default_manager = ConfigManager()
    return _default_manager

def load_agents_config() -> dict:
    """相容舊 API：載入代理人配置"""
    return get_config_manager().load_agents_config()

def load_quality_rules() -> dict:
    """相容舊 API：載入品質規則配置"""
    return get_config_manager().load_quality_rules()

@contextmanager
def config_scope(project_root: Optional[str] = None) -> Iterator[ConfigManager]:
    """
    配置範圍 Context Manager

    建立一個有明確生命週期的配置環境。

    Args:
        project_root: 專案根目錄

    Yields:
        ConfigManager: 配置管理器

    Example:
        with config_scope("/path/to/project") as config:
            agents = config.load_agents_config()
            rules = config.load_quality_rules()
        # 離開時快取自動清除
    """
    manager = ConfigManager(project_root)
    with manager.cached_scope():
        yield manager

# ===== 測試範例 =====

if __name__ == "__main__":
    import tempfile

    # 建立測試配置
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".claude" / "config"
        config_dir.mkdir(parents=True)

        # 寫入測試配置
        (config_dir / "agents.json").write_text(
            '{"known_agents": ["test-agent-1", "test-agent-2"]}'
        )

        # 使用 Context Manager
        with config_scope(tmpdir) as config:
            agents = config.load_agents_config()
            print(f"代理人配置: {agents}")

            # 第二次呼叫會使用快取
            agents2 = config.load_agents_config()
            print(f"快取命中: {agents is agents2}")

        # 離開範圍後快取已清除
        print("離開範圍，快取已清除")

    # 測試隔離範圍
    print("\n=== 測試隔離範圍 ===")
    manager = ConfigManager()

    with manager.isolated_scope() as isolated:
        # 隔離環境
        try:
            config = isolated.load_config("nonexistent")
        except FileNotFoundError as e:
            print(f"預期的錯誤: {e}")

    print("隔離範圍結束")
```

### 使用範例

#### 基本使用

```python
# 建立配置管理器
manager = ConfigManager()

# 使用快取範圍
with manager.cached_scope():
    agents = manager.load_agents_config()
    rules = manager.load_quality_rules()

    # 第二次呼叫會使用快取
    agents2 = manager.load_agents_config()
    assert agents is agents2  # 同一個物件

# 離開範圍後快取已清除
```

#### 測試中使用

```python
import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def config_manager():
    """測試用的配置管理器"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 準備測試配置
        config_dir = Path(tmpdir) / ".claude" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "agents.json").write_text(
            '{"known_agents": ["test-agent"]}'
        )

        # 使用隔離範圍
        manager = ConfigManager()
        with manager.isolated_scope(tmpdir) as isolated:
            yield isolated

def test_load_agents_config(config_manager):
    """測試載入代理人配置"""
    config = config_manager.load_agents_config()
    assert config["known_agents"] == ["test-agent"]

def test_cache_works(config_manager):
    """測試快取功能"""
    config1 = config_manager.load_agents_config()
    config2 = config_manager.load_agents_config()
    assert config1 is config2  # 同一個物件
```

#### 相容舊 API

```python
# 如果有既有程式碼使用舊 API
from config_loader import load_agents_config, config_scope

# 舊的呼叫方式仍然可用
config = load_agents_config()

# 新的呼叫方式有明確的生命週期
with config_scope() as manager:
    config = manager.load_agents_config()
```

## 設計權衡

| 面向 | 全域快取 | Context Manager |
|------|----------|-----------------|
| 簡單性 | 最簡單 | 需要理解 Context Manager |
| 生命週期 | 不明確（程式結束前一直存在） | 明確（範圍結束時清除） |
| 測試隔離 | 困難（需要手動清除） | 容易（自動隔離） |
| 並行安全 | 不安全（共用全域變數） | 可以安全（每個範圍獨立） |
| 記憶體管理 | 可能洩漏 | 自動清理 |
| API 相容性 | N/A | 可以相容舊 API |

## 什麼時候該用 Context Manager 管理快取？

✅ **適合使用**：

- 需要明確的快取生命週期
- 測試需要隔離的快取
- 可能並行存取快取
- 快取資料量大，需要及時釋放

❌ **不建議使用**：

- 快取需要跨多個函式呼叫共享
- 快取很小，不需要特別管理
- 程式很簡單，不需要測試隔離

## 進階：與 ExitStack 結合

當需要管理多個快取時：

```python
from contextlib import ExitStack

def process_with_multiple_caches():
    """使用 ExitStack 管理多個快取"""
    with ExitStack() as stack:
        # 進入多個快取範圍
        config = stack.enter_context(config_scope())
        db_cache = stack.enter_context(database_cache_scope())
        api_cache = stack.enter_context(api_cache_scope())

        # 使用各種快取
        agents = config.load_agents_config()
        users = db_cache.get_users()
        data = api_cache.fetch_data()

        return process(agents, users, data)

    # ExitStack 會自動清理所有快取
```

## 練習

### 基礎練習

1. 為 `ConfigManager` 加入 `reload_config` 方法，強制重新載入配置
2. 實作一個 `@cached_config` 裝飾器，讓函式自動使用快取範圍

### 進階練習

3. 加入 TTL（Time To Live）支援，讓快取自動過期
4. 實作一個執行緒安全的 `ConfigManager`，支援多執行緒存取

### 挑戰題

5. 參考 `config_loader.py` 的 Fallback Pattern（YAML → JSON → 預設值），用 Context Manager 實現「配置來源優先級」的管理

## 延伸閱讀

- [contextlib 官方文件](https://docs.python.org/3/library/contextlib.html)
- [functools.lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache)
- [cachetools](https://cachetools.readthedocs.io/) - 更多快取策略

---

*上一章：[案例研究索引](../)*
*下一章：[案例：插件架構設計](../plugin-architecture/)*
