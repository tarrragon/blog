---
title: "4.3 工廠模式"
date: 2026-01-20
description: "動態建立物件"
weight: 3
---

# 工廠模式

工廠模式用於封裝物件的建立邏輯，讓使用者不需要知道具體的類別名稱，只需要提供識別資訊即可取得適當的物件。

## 為什麼需要工廠模式？

### 問題場景

```python
# 使用者需要知道所有具體類別
if file_type == "json":
    parser = JsonParser()
elif file_type == "yaml":
    parser = YamlParser()
elif file_type == "xml":
    parser = XmlParser()
else:
    raise ValueError(f"Unknown type: {file_type}")

# 問題：
# 1. 使用者需要導入所有具體類別
# 2. 新增類型需要修改多處程式碼
# 3. 建立邏輯重複
```

### 使用工廠解決

```python
# 使用者只需要知道工廠
parser = ParserFactory.create(file_type)

# 新增類型只需要註冊到工廠
# 使用者程式碼不需要修改
```

## 基本實作

### 簡單工廠

```python
from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: str) -> dict:
        pass

class JsonParser(BaseParser):
    def parse(self, content: str) -> dict:
        return json.loads(content)

class YamlParser(BaseParser):
    def parse(self, content: str) -> dict:
        return yaml.safe_load(content)


class ParserFactory:
    """解析器工廠"""

    # 註冊表
    _parsers: dict[str, type] = {
        "json": JsonParser,
        "yaml": YamlParser,
        "yml": YamlParser,
    }

    @classmethod
    def create(cls, parser_type: str) -> BaseParser:
        """
        建立解析器

        Args:
            parser_type: 解析器類型

        Returns:
            BaseParser: 解析器實例

        Raises:
            ValueError: 未知的解析器類型
        """
        parser_class = cls._parsers.get(parser_type.lower())
        if parser_class is None:
            raise ValueError(f"Unknown parser type: {parser_type}")
        return parser_class()

    @classmethod
    def register(cls, parser_type: str, parser_class: type) -> None:
        """註冊新的解析器"""
        cls._parsers[parser_type.lower()] = parser_class

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """取得支援的解析器類型"""
        return list(cls._parsers.keys())
```

### 使用工廠

```python
# 建立解析器
json_parser = ParserFactory.create("json")
yaml_parser = ParserFactory.create("yaml")

# 查詢支援的類型
types = ParserFactory.get_supported_types()
# ['json', 'yaml', 'yml']

# 註冊新類型
class XmlParser(BaseParser):
    def parse(self, content: str) -> dict:
        ...

ParserFactory.register("xml", XmlParser)
```

## 進階：帶參數的工廠

```python
class ParserFactory:
    _parsers: dict[str, type] = {}

    @classmethod
    def create(
        cls,
        parser_type: str,
        **kwargs
    ) -> BaseParser:
        """
        建立解析器（支援傳入參數）

        Args:
            parser_type: 解析器類型
            **kwargs: 傳給解析器的參數

        Example:
            parser = ParserFactory.create(
                "json",
                encoding="utf-8",
                strict=True
            )
        """
        parser_class = cls._parsers.get(parser_type.lower())
        if parser_class is None:
            raise ValueError(f"Unknown parser type: {parser_type}")
        return parser_class(**kwargs)
```

## 使用裝飾器註冊

更優雅的註冊方式：

```python
class ParserFactory:
    _parsers: dict[str, type] = {}

    @classmethod
    def register(cls, *names: str):
        """
        註冊解析器的裝飾器

        Example:
            @ParserFactory.register("json")
            class JsonParser(BaseParser):
                ...
        """
        def decorator(parser_class: type) -> type:
            for name in names:
                cls._parsers[name.lower()] = parser_class
            return parser_class
        return decorator

    @classmethod
    def create(cls, parser_type: str) -> BaseParser:
        parser_class = cls._parsers.get(parser_type.lower())
        if parser_class is None:
            raise ValueError(f"Unknown parser type: {parser_type}")
        return parser_class()


# 使用裝飾器註冊
@ParserFactory.register("json")
class JsonParser(BaseParser):
    def parse(self, content: str) -> dict:
        return json.loads(content)


@ParserFactory.register("yaml", "yml")
class YamlParser(BaseParser):
    def parse(self, content: str) -> dict:
        return yaml.safe_load(content)
```

## 根據檔案自動選擇

```python
class ParserFactory:
    _parsers: dict[str, type] = {}
    _extension_map: dict[str, str] = {
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".xml": "xml",
    }

    @classmethod
    def create_from_file(cls, file_path: str) -> BaseParser:
        """
        根據檔案副檔名自動選擇解析器

        Args:
            file_path: 檔案路徑

        Example:
            parser = ParserFactory.create_from_file("config.yaml")
        """
        from pathlib import Path
        ext = Path(file_path).suffix.lower()

        parser_type = cls._extension_map.get(ext)
        if parser_type is None:
            raise ValueError(f"Unsupported file extension: {ext}")

        return cls.create(parser_type)
```

## 完整範例

```python
from abc import ABC, abstractmethod
from pathlib import Path


class BaseParser(ABC):
    """解析器基類"""

    @abstractmethod
    def parse(self, content: str) -> dict:
        """解析內容"""
        pass

    def parse_file(self, path: str) -> dict:
        """解析檔案"""
        content = Path(path).read_text(encoding="utf-8")
        return self.parse(content)


class ParserFactory:
    """解析器工廠"""

    _parsers: dict[str, type] = {}
    _extensions: dict[str, str] = {}

    @classmethod
    def register(cls, name: str, extensions: list[str] = None):
        """
        註冊解析器的裝飾器

        Args:
            name: 解析器名稱
            extensions: 對應的副檔名列表
        """
        def decorator(parser_class: type) -> type:
            cls._parsers[name.lower()] = parser_class

            if extensions:
                for ext in extensions:
                    cls._extensions[ext.lower()] = name.lower()

            return parser_class
        return decorator

    @classmethod
    def create(cls, parser_type: str) -> BaseParser:
        """建立解析器"""
        parser_class = cls._parsers.get(parser_type.lower())
        if parser_class is None:
            available = ", ".join(cls._parsers.keys())
            raise ValueError(
                f"Unknown parser type: {parser_type}. "
                f"Available: {available}"
            )
        return parser_class()

    @classmethod
    def create_from_file(cls, file_path: str) -> BaseParser:
        """根據檔案副檔名自動建立解析器"""
        ext = Path(file_path).suffix.lower()
        parser_type = cls._extensions.get(ext)

        if parser_type is None:
            available = ", ".join(cls._extensions.keys())
            raise ValueError(
                f"No parser for extension: {ext}. "
                f"Supported: {available}"
            )

        return cls.create(parser_type)


# 註冊解析器
@ParserFactory.register("json", extensions=[".json"])
class JsonParser(BaseParser):
    def parse(self, content: str) -> dict:
        import json
        return json.loads(content)


@ParserFactory.register("yaml", extensions=[".yaml", ".yml"])
class YamlParser(BaseParser):
    def parse(self, content: str) -> dict:
        import yaml
        return yaml.safe_load(content) or {}


# 使用
def load_config(path: str) -> dict:
    """載入配置檔案（自動選擇解析器）"""
    parser = ParserFactory.create_from_file(path)
    return parser.parse_file(path)

# 使用範例
config = load_config("settings.yaml")
config = load_config("data.json")
```

## 工廠與依賴注入

工廠模式也可以用於依賴注入：

```python
class ServiceFactory:
    """服務工廠"""

    _services: dict[str, object] = {}

    @classmethod
    def register_singleton(cls, name: str, instance: object):
        """註冊單例服務"""
        cls._services[name] = instance

    @classmethod
    def get(cls, name: str) -> object:
        """取得服務"""
        if name not in cls._services:
            raise ValueError(f"Service not registered: {name}")
        return cls._services[name]


# 應用程式啟動時註冊服務
ServiceFactory.register_singleton("database", Database())
ServiceFactory.register_singleton("cache", RedisCache())

# 在其他地方使用
db = ServiceFactory.get("database")
```

## 最佳實踐

### 1. 提供清楚的錯誤訊息

```python
@classmethod
def create(cls, parser_type: str) -> BaseParser:
    parser_class = cls._parsers.get(parser_type.lower())
    if parser_class is None:
        available = ", ".join(sorted(cls._parsers.keys()))
        raise ValueError(
            f"Unknown parser type: '{parser_type}'. "
            f"Available types: {available}"
        )
    return parser_class()
```

### 2. 支援查詢可用類型

```python
@classmethod
def get_available_types(cls) -> list[str]:
    """返回所有可用的解析器類型"""
    return sorted(cls._parsers.keys())
```

### 3. 考慮快取實例

```python
class ParserFactory:
    _parsers: dict[str, type] = {}
    _instances: dict[str, BaseParser] = {}

    @classmethod
    def create(cls, parser_type: str, cached: bool = True):
        """建立或取得快取的解析器"""
        if cached and parser_type in cls._instances:
            return cls._instances[parser_type]

        instance = cls._parsers[parser_type]()

        if cached:
            cls._instances[parser_type] = instance

        return instance
```

## 思考題

1. 工廠模式和直接使用 `if-elif` 有什麼區別？
2. 使用裝飾器註冊有什麼優點？
3. 什麼時候應該快取工廠建立的實例？

## 實作練習

1. 實作一個驗證器工廠，支援不同類型的驗證器
2. 為現有的工廠添加快取功能
3. 實作一個支援依賴注入的服務工廠

---

*上一章：[抽象基類 ABC](../abc/)*
*下一章：[單例與快取模式](../singleton-cache/)*
