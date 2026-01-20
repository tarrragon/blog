---
title: "6.3 如何新增語言解析器"
date: 2026-01-20
description: "繼承 ABC 實作新解析器"
weight: 3
---

# 如何新增語言解析器

本章示範如何透過繼承抽象基類來新增語言解析器。這是一個完整的實作範例，展示了前面學到的 ABC、工廠模式和型別提示等概念。

## 前置知識

建議先閱讀：
- [4.2 抽象基類 ABC](../../04-oop/abc/)
- [4.3 工廠模式](../../04-oop/factory/)
- [2.1 Type Hints 基礎](../../02-type-system/type-hints/)

## 場景說明

假設 Hook 系統需要支援新的配置格式（例如 TOML），我們需要：

1. 建立繼承自 `BaseParser` 的 `TomlParser` 類別
2. 實作所有抽象方法
3. 註冊到工廠
4. 撰寫測試

## 步驟 1：了解基類介面

首先檢視抽象基類的定義：

```python
# parsers/base.py
from abc import ABC, abstractmethod
from typing import Optional

class BaseParser(ABC):
    """解析器抽象基類"""

    def __init__(self, encoding: str = "utf-8"):
        self.encoding = encoding

    @abstractmethod
    def parse(self, content: str) -> dict:
        """
        解析內容

        Args:
            content: 要解析的字串

        Returns:
            dict: 解析後的字典

        Raises:
            ParseError: 解析失敗時拋出
        """
        pass

    @abstractmethod
    def validate(self, content: str) -> bool:
        """
        驗證內容格式是否正確

        Args:
            content: 要驗證的字串

        Returns:
            bool: 格式正確返回 True
        """
        pass

    @property
    @abstractmethod
    def file_extensions(self) -> list[str]:
        """支援的檔案副檔名列表"""
        pass

    # 共用方法（不是抽象的）
    def parse_file(self, path: str) -> dict:
        """解析檔案"""
        from pathlib import Path
        content = Path(path).read_text(encoding=self.encoding)
        return self.parse(content)
```

## 步驟 2：實作新解析器

```python
# parsers/toml_parser.py
"""
TOML 解析器

支援 TOML 格式的配置檔案解析。
"""

from typing import Optional
from .base import BaseParser

# 嘗試導入 toml 模組
try:
    import tomllib  # Python 3.11+ 內建
except ImportError:
    try:
        import toml as tomllib  # 第三方套件
    except ImportError:
        tomllib = None


class TomlParser(BaseParser):
    """
    TOML 格式解析器

    支援 .toml 檔案的解析。

    Example:
        parser = TomlParser()
        config = parser.parse_file("config.toml")
    """

    def __init__(self, encoding: str = "utf-8"):
        """
        初始化 TOML 解析器

        Args:
            encoding: 檔案編碼

        Raises:
            ImportError: 如果 toml 模組不可用
        """
        if tomllib is None:
            raise ImportError(
                "TOML parser requires 'tomllib' (Python 3.11+) "
                "or 'toml' package. Install with: pip install toml"
            )
        super().__init__(encoding)

    def parse(self, content: str) -> dict:
        """
        解析 TOML 內容

        Args:
            content: TOML 格式的字串

        Returns:
            dict: 解析後的字典

        Raises:
            ValueError: 如果 TOML 格式錯誤
        """
        try:
            # Python 3.11+ 的 tomllib 需要 bytes
            if hasattr(tomllib, 'loads'):
                return tomllib.loads(content)
            else:
                # tomllib (3.11+) 只接受 bytes
                return tomllib.load(content.encode(self.encoding))
        except Exception as e:
            raise ValueError(f"Failed to parse TOML: {e}") from e

    def validate(self, content: str) -> bool:
        """
        驗證 TOML 格式

        Args:
            content: 要驗證的字串

        Returns:
            bool: 格式正確返回 True
        """
        try:
            self.parse(content)
            return True
        except ValueError:
            return False

    @property
    def file_extensions(self) -> list[str]:
        """支援的副檔名"""
        return [".toml"]
```

## 步驟 3：註冊到工廠

```python
# parsers/__init__.py
"""
解析器模組

提供多種格式的檔案解析功能。
"""

from .base import BaseParser
from .factory import ParserFactory
from .json_parser import JsonParser
from .yaml_parser import YamlParser

# 註冊內建解析器
ParserFactory.register("json", [".json"])(JsonParser)
ParserFactory.register("yaml", [".yaml", ".yml"])(YamlParser)

# 嘗試註冊 TOML 解析器（可選依賴）
try:
    from .toml_parser import TomlParser
    ParserFactory.register("toml", [".toml"])(TomlParser)
except ImportError:
    pass  # TOML 支援不可用

__all__ = [
    "BaseParser",
    "ParserFactory",
    "JsonParser",
    "YamlParser",
]
```

或者使用裝飾器直接在類別定義時註冊：

```python
# parsers/toml_parser.py
from .factory import ParserFactory
from .base import BaseParser

@ParserFactory.register("toml", [".toml"])
class TomlParser(BaseParser):
    """TOML 解析器"""
    # ... 實作 ...
```

## 步驟 4：撰寫測試

```python
# tests/test_toml_parser.py
"""
TOML 解析器測試
"""

import unittest
from unittest.mock import patch

# 跳過測試如果 toml 不可用
try:
    from parsers.toml_parser import TomlParser
    HAS_TOML = True
except ImportError:
    HAS_TOML = False


@unittest.skipUnless(HAS_TOML, "TOML support not available")
class TestTomlParser(unittest.TestCase):
    """測試 TomlParser 類別"""

    def setUp(self):
        """測試前準備"""
        self.parser = TomlParser()

    def test_parse_simple_toml(self):
        """測試解析簡單的 TOML"""
        content = """
        [server]
        host = "localhost"
        port = 8080
        """
        result = self.parser.parse(content)

        self.assertEqual(result["server"]["host"], "localhost")
        self.assertEqual(result["server"]["port"], 8080)

    def test_parse_nested_toml(self):
        """測試解析巢狀的 TOML"""
        content = """
        [database]
        host = "localhost"

        [database.connection]
        timeout = 30
        retries = 3
        """
        result = self.parser.parse(content)

        self.assertEqual(result["database"]["host"], "localhost")
        self.assertEqual(result["database"]["connection"]["timeout"], 30)

    def test_validate_valid_toml(self):
        """測試驗證有效的 TOML"""
        content = '[section]\nkey = "value"'
        self.assertTrue(self.parser.validate(content))

    def test_validate_invalid_toml(self):
        """測試驗證無效的 TOML"""
        content = "this is not valid TOML ["
        self.assertFalse(self.parser.validate(content))

    def test_parse_invalid_raises_error(self):
        """測試解析無效 TOML 時拋出錯誤"""
        content = "invalid [ toml"
        with self.assertRaises(ValueError):
            self.parser.parse(content)

    def test_file_extensions(self):
        """測試檔案副檔名"""
        self.assertIn(".toml", self.parser.file_extensions)


@unittest.skipUnless(HAS_TOML, "TOML support not available")
class TestTomlParserFactory(unittest.TestCase):
    """測試 TOML 解析器與工廠的整合"""

    def test_factory_creates_toml_parser(self):
        """測試工廠可以建立 TOML 解析器"""
        from parsers import ParserFactory

        parser = ParserFactory.create("toml")
        self.assertIsInstance(parser, TomlParser)

    def test_factory_creates_from_file(self):
        """測試工廠根據副檔名建立解析器"""
        from parsers import ParserFactory

        parser = ParserFactory.create_from_file("config.toml")
        self.assertIsInstance(parser, TomlParser)


if __name__ == "__main__":
    unittest.main()
```

## 步驟 5：更新文件

在 README 或相關文件中記錄新功能：

```markdown
## 支援的配置格式

- JSON (.json) - 內建支援
- YAML (.yaml, .yml) - 需要 PyYAML
- TOML (.toml) - 需要 Python 3.11+ 或 toml 套件

### 安裝 TOML 支援

```bash
# Python 3.11+ 內建支援
# 或安裝第三方套件
pip install toml
```

### 使用範例

```python
from parsers import ParserFactory

# 自動選擇解析器
parser = ParserFactory.create_from_file("config.toml")
config = parser.parse_file("config.toml")
```
```

## 完整檢查清單

新增解析器時的檢查項目：

- [ ] 繼承 `BaseParser`
- [ ] 實作所有 `@abstractmethod`
  - [ ] `parse(content: str) -> dict`
  - [ ] `validate(content: str) -> bool`
  - [ ] `file_extensions` 屬性
- [ ] 處理可選依賴
- [ ] 註冊到 `ParserFactory`
- [ ] 撰寫單元測試
  - [ ] 正常解析
  - [ ] 錯誤處理
  - [ ] 驗證功能
  - [ ] 工廠整合
- [ ] 更新文件
- [ ] 更新 `__all__` 匯出

## 常見問題

### Q: 如果依賴套件不可用怎麼辦？

在 `__init__` 中檢查並提供清楚的錯誤訊息：

```python
def __init__(self):
    if required_module is None:
        raise ImportError(
            "TomlParser requires 'toml' package. "
            "Install with: pip install toml"
        )
```

### Q: 如何處理不同版本的 API？

```python
try:
    import tomllib  # Python 3.11+
    def parse_toml(content: str) -> dict:
        return tomllib.loads(content)
except ImportError:
    import toml
    def parse_toml(content: str) -> dict:
        return toml.loads(content)
```

### Q: 解析錯誤應該拋出什麼異常？

建議轉換為標準異常並保留原始資訊：

```python
try:
    return toml.loads(content)
except toml.TomlDecodeError as e:
    raise ValueError(f"Invalid TOML: {e}") from e
```

## 思考題

1. 為什麼要將原始異常作為 `from e` 傳遞？
2. 如何設計讓解析器支援串流處理（大檔案）？
3. 如果要支援解析器鏈（先解密再解析），應該如何設計？

---

*上一章：[如何擴展共用模組](../extend-lib/)*
*回到首頁：[Python 維護工程師實戰指南](../../)*
