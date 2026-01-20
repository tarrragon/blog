---
title: "2.3 Dataclass 資料結構"
description: "快速定義資料類別"
weight: 3
---

# Dataclass 資料結構

`dataclass` 是 Python 3.7+ 引入的裝飾器，用於快速建立主要用於存放資料的類別。它自動產生 `__init__`、`__repr__` 等方法，減少樣板程式碼。

## 為什麼使用 Dataclass？

### 傳統類別

```python
class ValidationIssue:
    def __init__(self, level, message, line=None, suggestion=None):
        self.level = level
        self.message = message
        self.line = line
        self.suggestion = suggestion

    def __repr__(self):
        return f"ValidationIssue(level={self.level!r}, message={self.message!r})"

    def __eq__(self, other):
        if not isinstance(other, ValidationIssue):
            return False
        return (self.level == other.level and
                self.message == other.message and
                self.line == other.line and
                self.suggestion == other.suggestion)
```

### 使用 Dataclass

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ValidationIssue:
    level: str
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None
```

自動產生：
- `__init__`
- `__repr__`
- `__eq__`

## 實際範例：Hook 驗證器

來自 `.claude/lib/hook_validator.py`：

```python
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ValidationIssue:
    """驗證問題描述"""
    level: str          # "error" | "warning" | "info"
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """單個 Hook 的驗證結果"""
    hook_path: str
    issues: List[ValidationIssue] = field(default_factory=list)
    is_compliant: bool = True

    def __post_init__(self):
        """計算 is_compliant 狀態"""
        self.is_compliant = not any(
            issue.level == "error" for issue in self.issues
        )
```

## 基本語法

### 欄位定義

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Person:
    # 必要欄位（無預設值）
    name: str
    age: int

    # 可選欄位（有預設值）
    email: Optional[str] = None
    tags: List[str] = None  # 錯誤！見下方說明
```

### 可變預設值的問題

```python
from dataclasses import dataclass, field
from typing import List

# 錯誤：可變物件作為預設值
@dataclass
class Wrong:
    items: List[str] = []  # 所有實例會共用同一個列表！

# 正確：使用 field(default_factory=...)
@dataclass
class Correct:
    items: List[str] = field(default_factory=list)
```

## field() 函式

`field()` 提供更多欄位配置選項：

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class ValidationResult:
    hook_path: str
    # 使用 default_factory 建立可變預設值
    issues: List[ValidationIssue] = field(default_factory=list)
    # 不包含在 __repr__ 中
    _internal: str = field(default="", repr=False)
    # 不包含在比較中
    cached: bool = field(default=False, compare=False)
```

### field() 參數

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `default` | 預設值 | 無 |
| `default_factory` | 產生預設值的函式 | 無 |
| `repr` | 是否包含在 `__repr__` | True |
| `compare` | 是否包含在比較中 | True |
| `hash` | 是否包含在 hash 中 | None |
| `init` | 是否包含在 `__init__` | True |

## __post_init__

在 `__init__` 完成後執行，用於衍生欄位計算：

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class ValidationResult:
    hook_path: str
    issues: List[ValidationIssue] = field(default_factory=list)
    is_compliant: bool = True

    def __post_init__(self):
        """根據 issues 計算 is_compliant"""
        self.is_compliant = not any(
            issue.level == "error" for issue in self.issues
        )

# 使用
result = ValidationResult(
    hook_path="my_hook.py",
    issues=[ValidationIssue(level="error", message="Bad")]
)
print(result.is_compliant)  # False（自動計算）
```

## 不可變 Dataclass

使用 `frozen=True` 建立不可變物件：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    x: float
    y: float

p = Point(1.0, 2.0)
p.x = 3.0  # 錯誤！FrozenInstanceError
```

不可變 dataclass 可以用作字典鍵或集合元素。

## 轉換為字典

使用 `asdict()` 轉換為字典：

```python
from dataclasses import dataclass, asdict

@dataclass
class Config:
    name: str
    timeout: int

config = Config("test", 30)
config_dict = asdict(config)
# {'name': 'test', 'timeout': 30}

# 用於 JSON 序列化
import json
json.dumps(asdict(config))
```

## 實際應用：Markdown 連結檢查

來自 `.claude/lib/markdown_link_checker.py`：

```python
from dataclasses import dataclass, asdict, field
from typing import List

@dataclass
class BrokenLink:
    """失效連結描述"""
    file: str
    line: int
    link_text: str
    link_target: str
    suggestion: str = ""


@dataclass
class LinkCheckResult:
    """單個檔案的連結檢查結果"""
    file_path: str
    total_links: int
    broken_links: List[BrokenLink] = field(default_factory=list)
    is_valid: bool = True

    def __post_init__(self):
        """計算 is_valid 狀態"""
        self.is_valid = len(self.broken_links) == 0


# 使用範例
result = LinkCheckResult(
    file_path="docs/README.md",
    total_links=10,
    broken_links=[
        BrokenLink(
            file="docs/README.md",
            line=15,
            link_text="Guide",
            link_target="./guide.md",
            suggestion="檔案不存在"
        )
    ]
)

# 輸出 JSON
print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
```

## 與 TypedDict 的比較

| 特性 | dataclass | TypedDict |
|------|-----------|-----------|
| 用途 | 資料物件 | 字典型別提示 |
| 執行時驗證 | 有（可選） | 無 |
| 方法 | 可以定義 | 不能定義 |
| 輸出 | 物件 | 字典 |

```python
from typing import TypedDict
from dataclasses import dataclass

# TypedDict：給字典加型別
class ConfigDict(TypedDict):
    name: str
    timeout: int

config: ConfigDict = {"name": "test", "timeout": 30}

# dataclass：建立資料物件
@dataclass
class Config:
    name: str
    timeout: int

config = Config(name="test", timeout=30)
```

## 最佳實踐

### 1. 必要欄位放前面

```python
@dataclass
class Person:
    # 必要欄位
    name: str
    age: int
    # 可選欄位
    email: Optional[str] = None
```

### 2. 使用 field() 處理可變預設值

```python
@dataclass
class Container:
    items: List[str] = field(default_factory=list)  # 正確
    # items: List[str] = []  # 錯誤！
```

### 3. 善用 __post_init__

```python
@dataclass
class Result:
    items: List[str] = field(default_factory=list)
    count: int = 0

    def __post_init__(self):
        self.count = len(self.items)  # 自動計算
```

## 思考題

1. 為什麼 `issues: List[str] = []` 是危險的？
2. `__post_init__` 和在 `__init__` 中計算有什麼區別？
3. 什麼時候應該使用 `frozen=True`？

## 實作練習

1. 建立一個 `HookResult` dataclass，包含 hook 名稱、執行時間、成功狀態
2. 實作一個 dataclass，使用 `__post_init__` 計算衍生欄位
3. 將現有的字典結構重構為 dataclass

---

*上一章：[Optional、Union、泛型](../optional-union/)*
*下一章：[Enum 列舉型別](../enum/)*
