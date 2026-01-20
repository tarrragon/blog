---
title: "4.2 抽象基類 ABC"
date: 2026-01-20
description: "定義介面契約"
weight: 2
---

# 抽象基類 ABC

抽象基類（Abstract Base Class，ABC）用於定義介面契約，確保子類別實作必要的方法。這在建立可擴展的框架時特別有用。

## 為什麼需要抽象基類？

### 問題場景

假設我們有多種檔案解析器：

```python
class JsonParser:
    def parse(self, content: str) -> dict:
        return json.loads(content)

class YamlParser:
    def parse(self, content: str) -> dict:
        return yaml.safe_load(content)

class XmlParser:
    # 忘記實作 parse 方法！
    def read(self, content: str) -> dict:  # 方法名稱錯誤
        ...
```

問題：沒有強制的介面，容易出錯。

### 使用 ABC 解決

```python
from abc import ABC, abstractmethod

class BaseParser(ABC):
    """解析器抽象基類"""

    @abstractmethod
    def parse(self, content: str) -> dict:
        """解析內容並返回字典"""
        pass

class XmlParser(BaseParser):
    # 如果沒有實作 parse，會報錯
    def parse(self, content: str) -> dict:
        ...
```

## 基本語法

### 定義抽象基類

```python
from abc import ABC, abstractmethod
from typing import Optional

class BaseParser(ABC):
    """解析器基類"""

    def __init__(self, encoding: str = "utf-8"):
        self.encoding = encoding

    @abstractmethod
    def parse(self, content: str) -> dict:
        """
        解析內容（子類別必須實作）

        Args:
            content: 要解析的內容

        Returns:
            dict: 解析後的資料
        """
        pass

    @abstractmethod
    def validate(self, content: str) -> bool:
        """驗證內容格式（子類別必須實作）"""
        pass

    def parse_file(self, path: str) -> dict:
        """
        解析檔案（共用方法）

        這是具體實作，子類別可以直接使用或覆寫。
        """
        with open(path, encoding=self.encoding) as f:
            content = f.read()
        return self.parse(content)
```

### 實作子類別

```python
class JsonParser(BaseParser):
    """JSON 解析器"""

    def parse(self, content: str) -> dict:
        return json.loads(content)

    def validate(self, content: str) -> bool:
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False


class YamlParser(BaseParser):
    """YAML 解析器"""

    def parse(self, content: str) -> dict:
        return yaml.safe_load(content) or {}

    def validate(self, content: str) -> bool:
        try:
            yaml.safe_load(content)
            return True
        except yaml.YAMLError:
            return False
```

## 抽象屬性

除了方法，也可以定義抽象屬性：

```python
from abc import ABC, abstractmethod

class BaseParser(ABC):

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """支援的檔案副檔名"""
        pass

    @property
    @abstractmethod
    def mime_type(self) -> str:
        """MIME 類型"""
        pass


class JsonParser(BaseParser):

    @property
    def file_extension(self) -> str:
        return ".json"

    @property
    def mime_type(self) -> str:
        return "application/json"
```

## 範本方法模式

ABC 常與範本方法模式搭配使用：

```python
from abc import ABC, abstractmethod

class DataProcessor(ABC):
    """資料處理器基類"""

    def process(self, data: str) -> dict:
        """
        範本方法：定義處理流程

        1. 驗證
        2. 前處理
        3. 解析
        4. 後處理
        """
        # 步驟 1：驗證（子類別實作）
        if not self.validate(data):
            raise ValueError("Invalid data")

        # 步驟 2：前處理（可選覆寫）
        data = self.preprocess(data)

        # 步驟 3：解析（子類別實作）
        result = self.parse(data)

        # 步驟 4：後處理（可選覆寫）
        return self.postprocess(result)

    @abstractmethod
    def validate(self, data: str) -> bool:
        """驗證資料（子類別必須實作）"""
        pass

    @abstractmethod
    def parse(self, data: str) -> dict:
        """解析資料（子類別必須實作）"""
        pass

    def preprocess(self, data: str) -> str:
        """前處理（預設不做任何處理）"""
        return data

    def postprocess(self, result: dict) -> dict:
        """後處理（預設不做任何處理）"""
        return result
```

## 實作檢查

### 無法直接實例化

```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: str) -> dict:
        pass

# 錯誤：無法實例化抽象類別
parser = BaseParser()  # TypeError!
```

### 必須實作所有抽象方法

```python
class IncompleteParser(BaseParser):
    # 沒有實作 parse 方法
    pass

# 錯誤：無法實例化
parser = IncompleteParser()  # TypeError!
```

## 檢查子類別關係

```python
from abc import ABC

class BaseParser(ABC):
    pass

class JsonParser(BaseParser):
    pass

# 使用 isinstance 和 issubclass
parser = JsonParser()
isinstance(parser, BaseParser)     # True
issubclass(JsonParser, BaseParser) # True
```

## 與 Protocol 的比較

Python 3.8+ 引入了 `Protocol`，提供結構化子型別（Structural Subtyping）：

### ABC（名義子型別）

```python
from abc import ABC, abstractmethod

class Parseable(ABC):
    @abstractmethod
    def parse(self, content: str) -> dict:
        pass

# 必須明確繼承
class JsonParser(Parseable):  # 必須繼承 Parseable
    def parse(self, content: str) -> dict:
        return json.loads(content)
```

### Protocol（結構化子型別）

```python
from typing import Protocol

class Parseable(Protocol):
    def parse(self, content: str) -> dict:
        ...

# 不需要繼承，只要有相同的方法
class JsonParser:  # 不需要繼承
    def parse(self, content: str) -> dict:
        return json.loads(content)

def process(parser: Parseable) -> None:
    parser.parse("...")

# JsonParser 自動符合 Parseable 協議
process(JsonParser())  # OK
```

### 何時使用哪個？

| 特性 | ABC | Protocol |
|------|-----|----------|
| 需要繼承 | 是 | 否 |
| 執行時檢查 | 支援 | 有限支援 |
| 可以有共用方法 | 是 | 是（3.8+） |
| 適合場景 | 框架設計 | 型別提示 |

## 最佳實踐

### 1. 保持介面簡潔

```python
# 好：專注於核心方法
class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: str) -> dict:
        pass

# 不好：太多抽象方法
class BaseParser(ABC):
    @abstractmethod
    def parse(self): pass
    @abstractmethod
    def validate(self): pass
    @abstractmethod
    def preprocess(self): pass
    @abstractmethod
    def postprocess(self): pass
    @abstractmethod
    def format(self): pass
```

### 2. 提供有用的預設實作

```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: str) -> dict:
        pass

    # 有預設實作的方法
    def parse_file(self, path: str) -> dict:
        with open(path) as f:
            return self.parse(f.read())
```

### 3. 清晰的文檔

```python
class BaseParser(ABC):
    """
    解析器抽象基類

    所有解析器都應繼承此類別並實作 parse 方法。

    Example:
        class MyParser(BaseParser):
            def parse(self, content: str) -> dict:
                return {"data": content}
    """

    @abstractmethod
    def parse(self, content: str) -> dict:
        """
        解析內容

        Args:
            content: 要解析的字串內容

        Returns:
            dict: 解析後的字典

        Raises:
            ParseError: 如果解析失敗
        """
        pass
```

## 思考題

1. 什麼時候應該使用 ABC，什麼時候使用 Protocol？
2. 抽象方法可以有實作嗎？有什麼用途？
3. 如何測試抽象基類？

## 實作練習

1. 設計一個 `BaseValidator` 抽象基類，定義驗證器的介面
2. 實作兩個繼承自 `BaseValidator` 的具體驗證器
3. 使用範本方法模式實作一個多步驟的資料處理流程

---

*上一章：[類別設計原則](../class-design/)*
*下一章：[工廠模式](../factory/)*
