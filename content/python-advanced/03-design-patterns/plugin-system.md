---
title: "3.5.4 插件系統設計"
date: 2026-01-20
description: "插件架構模式、動態載入模組、entry_points、實際範例"
weight: 4
---

# 插件系統設計

插件系統讓應用程式可以在不修改核心程式碼的情況下擴展功能。本章介紹三種常見的插件架構模式，以及如何使用 Python 的動態載入機制實現它們。

## 先備知識

- 本進階系列 [模組二：元編程](../02-metaprogramming/)
- 特別是 Metaclass 與 `__init_subclass__`

## 插件架構模式

### 模式一：基於繼承

最簡單的插件模式，插件必須繼承基類：

```python
from abc import ABC, abstractmethod
from typing import ClassVar

class Plugin(ABC):
    """插件基類"""
    name: ClassVar[str]  # 每個插件必須定義名稱

    @abstractmethod
    def execute(self, context: dict) -> dict:
        """執行插件邏輯"""
        ...

class LoggingPlugin(Plugin):
    name = "logging"

    def execute(self, context: dict) -> dict:
        print(f"Processing: {context}")
        return context

class ValidationPlugin(Plugin):
    name = "validation"

    def execute(self, context: dict) -> dict:
        if not context.get("valid"):
            raise ValueError("Invalid context")
        return context
```

**優點**：簡單明確，IDE 支援好
**缺點**：強制耦合，無法使用第三方類別

### 模式二：基於註冊

使用裝飾器或顯式註冊，更靈活：

```python
from typing import Callable, TypeAlias

PluginFunc: TypeAlias = Callable[[dict], dict]

class PluginRegistry:
    """插件註冊表"""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginFunc] = {}

    def register(self, name: str) -> Callable[[PluginFunc], PluginFunc]:
        """裝飾器：註冊插件"""
        def decorator(func: PluginFunc) -> PluginFunc:
            if name in self._plugins:
                raise ValueError(f"Plugin '{name}' already registered")
            self._plugins[name] = func
            return func
        return decorator

    def get(self, name: str) -> PluginFunc | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[str]:
        return list(self._plugins.keys())

# 全域註冊表
registry = PluginRegistry()

@registry.register("uppercase")
def uppercase_plugin(context: dict) -> dict:
    context["text"] = context.get("text", "").upper()
    return context

@registry.register("lowercase")
def lowercase_plugin(context: dict) -> dict:
    context["text"] = context.get("text", "").lower()
    return context

# 使用
plugin = registry.get("uppercase")
if plugin:
    result = plugin({"text": "Hello"})
```

**優點**：靈活，支援函式和類別
**缺點**：需要顯式註冊

### 模式三：基於發現（使用 `__init_subclass__`）

利用 Python 的元編程機制自動發現插件：

```python
from typing import ClassVar

class AutoRegisterPlugin:
    """自動註冊的插件基類"""
    _registry: ClassVar[dict[str, type["AutoRegisterPlugin"]]] = {}
    name: ClassVar[str]

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        # 跳過沒有定義 name 的中間類別
        if hasattr(cls, "name") and cls.name:
            if cls.name in AutoRegisterPlugin._registry:
                raise ValueError(f"Plugin '{cls.name}' already registered")
            AutoRegisterPlugin._registry[cls.name] = cls

    @classmethod
    def get_plugin(cls, name: str) -> type["AutoRegisterPlugin"] | None:
        return cls._registry.get(name)

    @classmethod
    def list_plugins(cls) -> list[str]:
        return list(cls._registry.keys())

    def execute(self, context: dict) -> dict:
        raise NotImplementedError

# 定義插件只需要繼承，自動註冊
class FormatPlugin(AutoRegisterPlugin):
    name = "format"

    def execute(self, context: dict) -> dict:
        context["formatted"] = True
        return context

class CompressPlugin(AutoRegisterPlugin):
    name = "compress"

    def execute(self, context: dict) -> dict:
        context["compressed"] = True
        return context

# 自動發現
print(AutoRegisterPlugin.list_plugins())  # ['format', 'compress']
```

**優點**：無需顯式註冊，只要繼承就會被發現
**缺點**：必須繼承基類，Python 專屬

### 使用 Metaclass 的進階版本

```python
from typing import ClassVar

class PluginMeta(type):
    """插件元類別"""
    _registry: dict[str, type] = {}

    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> type:
        cls = super().__new__(mcs, name, bases, namespace)

        # 跳過基類
        if bases and hasattr(cls, "plugin_name"):
            plugin_name = cls.plugin_name
            if plugin_name in mcs._registry:
                raise ValueError(f"Plugin '{plugin_name}' already registered")
            mcs._registry[plugin_name] = cls

        return cls

    @classmethod
    def get_plugin(mcs, name: str) -> type | None:
        return mcs._registry.get(name)

class PluginBase(metaclass=PluginMeta):
    """插件基類"""
    plugin_name: ClassVar[str]

    def run(self) -> None:
        raise NotImplementedError

class MyPlugin(PluginBase):
    plugin_name = "my_plugin"

    def run(self) -> None:
        print("MyPlugin running")

# 使用
plugin_cls = PluginMeta.get_plugin("my_plugin")
if plugin_cls:
    plugin_cls().run()
```

## 動態載入模組

### importlib 基礎

```python
import importlib
from types import ModuleType

def load_module(module_path: str) -> ModuleType:
    """動態載入模組"""
    return importlib.import_module(module_path)

def load_class(module_path: str, class_name: str) -> type:
    """從模組載入類別"""
    module = importlib.import_module(module_path)
    return getattr(module, class_name)

# 使用
# 假設有 myapp/plugins/custom.py 定義了 CustomPlugin
plugin_cls = load_class("myapp.plugins.custom", "CustomPlugin")
plugin = plugin_cls()
```

### 從檔案路徑載入

```python
import importlib.util
from pathlib import Path
from types import ModuleType

def load_module_from_path(path: Path) -> ModuleType:
    """從檔案路徑載入模組"""
    spec = importlib.util.spec_from_file_location(
        path.stem,  # 模組名稱
        path        # 檔案路徑
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# 使用
plugin_module = load_module_from_path(Path("./plugins/custom_plugin.py"))
```

### importlib.metadata 的 entry_points（現代做法）

這是 Python 套件生態系統推薦的插件發現機制：

```python
# 在 pyproject.toml 中定義 entry points
"""
[project.entry-points."myapp.plugins"]
format = "myapp_format_plugin:FormatPlugin"
compress = "myapp_compress_plugin:CompressPlugin"
"""

from importlib.metadata import entry_points

def discover_plugins(group: str) -> dict[str, type]:
    """發現已安裝套件中的插件"""
    plugins = {}

    # Python 3.10+
    eps = entry_points(group=group)

    for ep in eps:
        try:
            plugin_cls = ep.load()
            plugins[ep.name] = plugin_cls
        except Exception as e:
            print(f"Failed to load plugin {ep.name}: {e}")

    return plugins

# 發現所有 myapp.plugins 群組的插件
plugins = discover_plugins("myapp.plugins")
for name, cls in plugins.items():
    print(f"Found plugin: {name} -> {cls}")
```

**優點**：
- 標準化的發現機制
- 支援第三方套件提供插件
- pip 安裝即可使用

## 實際範例一：Hook 系統的插件化改造

基於入門系列的 Hook 系統概念，設計一個插件化的 Hook 框架：

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import ClassVar
import importlib.util

class HookEvent(Enum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"

@dataclass
class HookContext:
    """Hook 執行的上下文"""
    event: HookEvent
    tool_name: str | None = None
    input_data: dict | None = None

@dataclass
class HookResult:
    """Hook 執行結果"""
    success: bool
    message: str
    modified_context: HookContext | None = None

class HookPlugin(ABC):
    """Hook 插件基類"""
    _registry: ClassVar[dict[str, list[type["HookPlugin"]]]] = {}

    # 子類別必須定義的屬性
    name: ClassVar[str]
    events: ClassVar[list[HookEvent]]
    priority: ClassVar[int] = 100  # 預設優先級

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "name") and hasattr(cls, "events"):
            for event in cls.events:
                event_name = event.value
                if event_name not in HookPlugin._registry:
                    HookPlugin._registry[event_name] = []
                HookPlugin._registry[event_name].append(cls)
                # 按優先級排序
                HookPlugin._registry[event_name].sort(
                    key=lambda c: c.priority
                )

    @abstractmethod
    def execute(self, context: HookContext) -> HookResult:
        """執行 Hook 邏輯"""
        ...

    @classmethod
    def get_hooks_for_event(cls, event: HookEvent) -> list[type["HookPlugin"]]:
        """取得特定事件的所有 Hook"""
        return cls._registry.get(event.value, [])

# 定義具體的 Hook 插件
class SecurityCheckHook(HookPlugin):
    """安全檢查 Hook"""
    name = "security_check"
    events = [HookEvent.PRE_TOOL_USE]
    priority = 10  # 高優先級，先執行

    DANGEROUS_PATTERNS = ["rm -rf", "DROP TABLE", "sudo"]

    def execute(self, context: HookContext) -> HookResult:
        if context.input_data:
            command = context.input_data.get("command", "")
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern in command:
                    return HookResult(
                        success=False,
                        message=f"Blocked dangerous pattern: {pattern}"
                    )
        return HookResult(success=True, message="Security check passed")

class LoggingHook(HookPlugin):
    """日誌記錄 Hook"""
    name = "logging"
    events = [HookEvent.PRE_TOOL_USE, HookEvent.POST_TOOL_USE]
    priority = 1000  # 低優先級，最後執行

    def execute(self, context: HookContext) -> HookResult:
        print(f"[{context.event.value}] Tool: {context.tool_name}")
        return HookResult(success=True, message="Logged")

# Hook 執行器
class HookRunner:
    """執行 Hook 的管理器"""

    def run_hooks(self, event: HookEvent, context: HookContext) -> list[HookResult]:
        """執行特定事件的所有 Hook"""
        results = []
        hook_classes = HookPlugin.get_hooks_for_event(event)

        for hook_cls in hook_classes:
            hook = hook_cls()
            try:
                result = hook.execute(context)
                results.append(result)
                # 如果 Hook 失敗且事件是 PRE，中斷執行
                if not result.success and event == HookEvent.PRE_TOOL_USE:
                    break
            except Exception as e:
                results.append(HookResult(
                    success=False,
                    message=f"Hook {hook_cls.name} failed: {e}"
                ))

        return results

# 使用
runner = HookRunner()
context = HookContext(
    event=HookEvent.PRE_TOOL_USE,
    tool_name="Bash",
    input_data={"command": "ls -la"}
)
results = runner.run_hooks(HookEvent.PRE_TOOL_USE, context)
```

## 實際範例二：通用插件框架設計

一個更通用的插件框架，支援動態載入和生命週期管理：

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any
import importlib.util

class PluginState(Enum):
    UNLOADED = auto()
    LOADED = auto()
    ACTIVE = auto()
    ERROR = auto()

@dataclass
class PluginInfo:
    """插件元資訊"""
    name: str
    version: str
    description: str
    author: str = ""
    dependencies: list[str] = field(default_factory=list)

class BasePlugin(ABC):
    """插件基類"""

    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """返回插件資訊"""
        ...

    def on_load(self) -> None:
        """插件載入時呼叫"""
        pass

    def on_unload(self) -> None:
        """插件卸載時呼叫"""
        pass

    def on_activate(self) -> None:
        """插件啟用時呼叫"""
        pass

    def on_deactivate(self) -> None:
        """插件停用時呼叫"""
        pass

@dataclass
class LoadedPlugin:
    """已載入的插件包裝"""
    plugin: BasePlugin
    state: PluginState = PluginState.UNLOADED
    error: str | None = None

class PluginManager:
    """插件管理器"""

    def __init__(self, plugin_dir: Path | None = None) -> None:
        self._plugins: dict[str, LoadedPlugin] = {}
        self._plugin_dir = plugin_dir

    def load_plugin(self, path: Path) -> str:
        """從檔案載入插件"""
        try:
            # 動態載入模組
            spec = importlib.util.spec_from_file_location(
                path.stem, path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load {path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 尋找 BasePlugin 的子類別
            plugin_cls = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, BasePlugin) and
                    attr is not BasePlugin):
                    plugin_cls = attr
                    break

            if plugin_cls is None:
                raise ImportError(f"No plugin class found in {path}")

            # 實例化插件
            plugin = plugin_cls()
            plugin_name = plugin.info.name

            # 檢查依賴
            for dep in plugin.info.dependencies:
                if dep not in self._plugins:
                    raise ImportError(f"Missing dependency: {dep}")

            # 呼叫生命週期方法
            plugin.on_load()

            self._plugins[plugin_name] = LoadedPlugin(
                plugin=plugin,
                state=PluginState.LOADED
            )

            return plugin_name

        except Exception as e:
            raise ImportError(f"Failed to load plugin from {path}: {e}")

    def unload_plugin(self, name: str) -> None:
        """卸載插件"""
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not found")

        loaded = self._plugins[name]

        # 先停用
        if loaded.state == PluginState.ACTIVE:
            self.deactivate_plugin(name)

        # 呼叫生命週期方法
        loaded.plugin.on_unload()

        del self._plugins[name]

    def activate_plugin(self, name: str) -> None:
        """啟用插件"""
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not found")

        loaded = self._plugins[name]
        if loaded.state != PluginState.LOADED:
            raise RuntimeError(f"Plugin '{name}' is not in LOADED state")

        try:
            loaded.plugin.on_activate()
            loaded.state = PluginState.ACTIVE
        except Exception as e:
            loaded.state = PluginState.ERROR
            loaded.error = str(e)
            raise

    def deactivate_plugin(self, name: str) -> None:
        """停用插件"""
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not found")

        loaded = self._plugins[name]
        if loaded.state != PluginState.ACTIVE:
            return

        loaded.plugin.on_deactivate()
        loaded.state = PluginState.LOADED

    def discover_plugins(self) -> list[Path]:
        """發現插件目錄中的所有插件"""
        if self._plugin_dir is None:
            return []

        return list(self._plugin_dir.glob("*.py"))

    def load_all_plugins(self) -> dict[str, str | None]:
        """載入所有發現的插件"""
        results: dict[str, str | None] = {}
        for path in self.discover_plugins():
            try:
                name = self.load_plugin(path)
                results[name] = None
            except Exception as e:
                results[path.stem] = str(e)
        return results

    def get_plugin(self, name: str) -> BasePlugin | None:
        """取得插件實例"""
        loaded = self._plugins.get(name)
        return loaded.plugin if loaded else None

    def list_plugins(self) -> list[PluginInfo]:
        """列出所有已載入的插件"""
        return [lp.plugin.info for lp in self._plugins.values()]

# 範例插件（放在獨立檔案中）
class GreeterPlugin(BasePlugin):
    """簡單的問候插件"""

    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="greeter",
            version="1.0.0",
            description="A simple greeting plugin"
        )

    def on_activate(self) -> None:
        print("Greeter plugin activated!")

    def greet(self, name: str) -> str:
        return f"Hello, {name}!"

# 使用
manager = PluginManager(Path("./plugins"))
manager.load_all_plugins()
manager.activate_plugin("greeter")

greeter = manager.get_plugin("greeter")
if isinstance(greeter, GreeterPlugin):
    print(greeter.greet("World"))
```

## 設計考量

### 安全性

```python
# 限制插件可以存取的模組
import sys
from types import ModuleType

class SandboxedImporter:
    """限制插件可以 import 的模組"""
    ALLOWED_MODULES = {"json", "re", "datetime", "typing"}

    def find_module(self, name: str, path=None):
        if name.split(".")[0] not in self.ALLOWED_MODULES:
            return self  # 攔截
        return None

    def load_module(self, name: str) -> ModuleType:
        raise ImportError(f"Module '{name}' is not allowed in plugins")

# 使用時插入到 sys.meta_path
# sys.meta_path.insert(0, SandboxedImporter())
```

### 版本相容性

```python
from packaging import version

def check_compatibility(
    plugin_info: PluginInfo,
    app_version: str
) -> bool:
    """檢查插件與應用程式版本相容性"""
    # 插件可以定義 min_app_version 屬性
    min_version = getattr(plugin_info, "min_app_version", "0.0.0")
    return version.parse(app_version) >= version.parse(min_version)
```

## 小結

| 模式 | 適用場景 |
|------|---------|
| 基於繼承 | 簡單場景，需要型別安全 |
| 基於註冊 | 需要靈活性，支援函式插件 |
| 基於發現 | 自動發現，減少樣板程式碼 |
| entry_points | 套件生態系統，第三方插件 |

## 思考題

1. 三種插件模式各有什麼優缺點？
2. 如何實現插件之間的依賴管理？
3. 如何確保插件的安全性？

---

*上一章：[3.5.3 進階上下文管理](../context-managers/)*
*下一章：[3.5.5 設計模式整合案例](../integration/)*
