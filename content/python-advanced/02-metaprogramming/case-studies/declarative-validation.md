---
title: "案例：宣告式驗證"
date: 2026-01-21
description: "用 Descriptor Protocol 將驗證邏輯從方法變成屬性定義"
weight: 1
---

# 案例：宣告式驗證

本案例基於 `.claude/lib/hook_validator.py` 的實際程式碼，展示如何用 Descriptor Protocol 實現宣告式驗證。

## 先備知識

- [2.1 Descriptor Protocol 完整指南](../../descriptors/)

## 問題背景

### 現有設計

`hook_validator.py` 使用命令式驗證方式：

```python
class HookValidator:
    """Hook 合規性驗證器"""

    # 驗證模式定義為類別常數
    VALID_NAME_PATTERNS = [
        r"^[a-z0-9]([a-z0-9\-_]*[a-z0-9])?\.py$",
    ]

    HOOK_IO_PATTERNS = [
        r"from\s+hook_io\s+import",
        r"from\s+lib\.hook_io\s+import",
    ]

    def validate_hook(self, hook_path: str) -> ValidationResult:
        """驗證單個 Hook 檔案"""
        issues = []
        issues.extend(self.check_naming_convention(hook_path))
        issues.extend(self.check_lib_imports(content, hook_path))
        issues.extend(self.check_output_format(content))
        issues.extend(self.check_test_exists(hook_path))
        return ValidationResult(hook_path=str(hook_path), issues=issues)

    def check_naming_convention(self, hook_path: Path) -> List[ValidationIssue]:
        """檢查命名規範"""
        filename = hook_path.name
        valid_name = any(
            re.match(pattern, filename)
            for pattern in self.VALID_NAME_PATTERNS
        )
        if not valid_name:
            return [ValidationIssue(
                level="warning",
                message=f"檔案名稱不符合規範: {filename}",
                suggestion="建議使用 snake-case 或 kebab-case 命名"
            )]
        return []
```

### 這個設計的優點

1. **直覺易懂**：每個 `check_*` 方法負責一項檢查
2. **彈性高**：容易新增或修改檢查邏輯
3. **調試方便**：可以單獨執行任一檢查方法

### 這個設計的限制

當需要**設定類別**時（例如 Hook 配置），命令式驗證會有問題：

```python
class HookConfig:
    """Hook 配置類別"""
    def __init__(self, name: str, event: str, command: str):
        # 驗證邏輯散落在 __init__ 中
        if not re.match(r"^[a-z0-9][a-z0-9\-_]*[a-z0-9]$", name):
            raise ValueError(f"無效的 Hook 名稱: {name}")
        if event not in ("PreToolUse", "PostToolUse", "Stop"):
            raise ValueError(f"無效的事件類型: {event}")
        if not command:
            raise ValueError("命令不能為空")

        self.name = name
        self.event = event
        self.command = command
```

問題：
- 驗證邏輯在 `__init__` 中，不容易重用
- 修改屬性時不會重新驗證
- 無法在類別定義中看到驗證規則

## 進階解決方案：宣告式驗證

### 設計目標

1. **驗證規則在類別定義中可見**
2. **賦值時自動驗證**
3. **驗證邏輯可重用**

### 實作步驟

#### 步驟 1：建立基礎 Descriptor

```python
import re
from typing import Any, Callable, Optional

class ValidatedField:
    """
    驗證欄位 Descriptor

    將驗證邏輯封裝在屬性定義中，
    賦值時自動執行驗證。
    """

    def __init__(
        self,
        validator: Callable[[Any], bool],
        error_msg: str = "驗證失敗"
    ):
        """
        Args:
            validator: 驗證函式，接受值，返回 bool
            error_msg: 驗證失敗時的錯誤訊息
        """
        self.validator = validator
        self.error_msg = error_msg
        # __set_name__ 會設定這些
        self.name: str = ""
        self.private_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        """
        Python 3.6+ 自動呼叫，取得屬性名稱

        Args:
            owner: 擁有此 Descriptor 的類別
            name: 屬性名稱
        """
        self.name = name
        self.private_name = f"_{name}"

    def __get__(self, obj: Any, objtype: type = None) -> Any:
        """
        讀取屬性時呼叫

        Args:
            obj: 實例（如果透過實例存取）
            objtype: 類別

        Returns:
            屬性值，或透過類別存取時返回 Descriptor 本身
        """
        if obj is None:
            return self  # 透過類別存取，返回 Descriptor
        return getattr(obj, self.private_name, None)

    def __set__(self, obj: Any, value: Any) -> None:
        """
        設定屬性時呼叫，執行驗證

        Args:
            obj: 實例
            value: 要設定的值

        Raises:
            ValueError: 驗證失敗時
        """
        if not self.validator(value):
            raise ValueError(f"{self.name}: {self.error_msg}")
        setattr(obj, self.private_name, value)
```

#### 步驟 2：建立特化的驗證 Descriptor

```python
class PatternField(ValidatedField):
    """
    正則表達式驗證欄位

    簡化常見的模式匹配驗證。
    """

    def __init__(self, pattern: str, error_msg: str = "格式不符"):
        """
        Args:
            pattern: 正則表達式模式
            error_msg: 驗證失敗時的錯誤訊息
        """
        self.pattern = re.compile(pattern)
        super().__init__(
            validator=lambda v: bool(self.pattern.match(str(v))),
            error_msg=error_msg
        )

class ChoiceField(ValidatedField):
    """
    選項驗證欄位

    限制值必須在指定選項中。
    """

    def __init__(self, choices: tuple, error_msg: str = "無效的選項"):
        """
        Args:
            choices: 允許的選項
            error_msg: 驗證失敗時的錯誤訊息
        """
        self.choices = choices
        super().__init__(
            validator=lambda v: v in self.choices,
            error_msg=f"{error_msg}，必須是: {', '.join(str(c) for c in choices)}"
        )

class NonEmptyField(ValidatedField):
    """
    非空驗證欄位

    確保值不為空。
    """

    def __init__(self, error_msg: str = "不能為空"):
        super().__init__(
            validator=lambda v: bool(v),
            error_msg=error_msg
        )

class RangeField(ValidatedField):
    """
    範圍驗證欄位

    確保數值在指定範圍內。
    """

    def __init__(
        self,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        error_msg: str = "超出範圍"
    ):
        """
        Args:
            min_val: 最小值（None 表示無下限）
            max_val: 最大值（None 表示無上限）
            error_msg: 驗證失敗時的錯誤訊息
        """
        self.min_val = min_val
        self.max_val = max_val

        def validator(v):
            if min_val is not None and v < min_val:
                return False
            if max_val is not None and v > max_val:
                return False
            return True

        range_desc = []
        if min_val is not None:
            range_desc.append(f">= {min_val}")
        if max_val is not None:
            range_desc.append(f"<= {max_val}")

        super().__init__(
            validator=validator,
            error_msg=f"{error_msg}，必須 {' 且 '.join(range_desc)}"
        )
```

#### 步驟 3：使用宣告式驗證

```python
class HookConfig:
    """
    Hook 配置類別 - 宣告式驗證版本

    驗證規則直接在類別定義中可見。
    """

    # 宣告式驗證：欄位定義即驗證規則
    name = PatternField(
        r"^[a-z0-9][a-z0-9\-_]*[a-z0-9]$",
        "Hook 名稱必須是小寫字母、數字、連字號或底線，且不能以連字號開頭或結尾"
    )

    event = ChoiceField(
        ("PreToolUse", "PostToolUse", "Stop", "SessionStart", "SessionEnd"),
        "無效的事件類型"
    )

    command = NonEmptyField("命令不能為空")

    timeout = RangeField(
        min_val=0,
        max_val=300,
        error_msg="超時時間無效"
    )

    def __init__(
        self,
        name: str,
        event: str,
        command: str,
        timeout: int = 30
    ):
        """
        初始化 Hook 配置

        Args:
            name: Hook 名稱
            event: 事件類型
            command: 執行的命令
            timeout: 超時時間（秒）

        驗證會在賦值時自動執行。
        """
        self.name = name      # 自動驗證名稱格式
        self.event = event    # 自動驗證事件類型
        self.command = command  # 自動驗證非空
        self.timeout = timeout  # 自動驗證範圍

    def __repr__(self) -> str:
        return (
            f"HookConfig(name={self.name!r}, event={self.event!r}, "
            f"command={self.command!r}, timeout={self.timeout})"
        )
```

### 完整程式碼

```python
#!/usr/bin/env python3
"""
宣告式驗證 - 完整範例

展示如何用 Descriptor Protocol 實現宣告式驗證。
"""

import re
from typing import Any, Callable, Optional

# ===== Descriptor 定義 =====

class ValidatedField:
    """驗證欄位 Descriptor 基類"""

    def __init__(
        self,
        validator: Callable[[Any], bool],
        error_msg: str = "驗證失敗"
    ):
        self.validator = validator
        self.error_msg = error_msg
        self.name: str = ""
        self.private_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.private_name = f"_{name}"

    def __get__(self, obj: Any, objtype: type = None) -> Any:
        if obj is None:
            return self
        return getattr(obj, self.private_name, None)

    def __set__(self, obj: Any, value: Any) -> None:
        if not self.validator(value):
            raise ValueError(f"{self.name}: {self.error_msg}")
        setattr(obj, self.private_name, value)

class PatternField(ValidatedField):
    """正則表達式驗證欄位"""

    def __init__(self, pattern: str, error_msg: str = "格式不符"):
        self.pattern = re.compile(pattern)
        super().__init__(
            validator=lambda v: bool(self.pattern.match(str(v))),
            error_msg=error_msg
        )

class ChoiceField(ValidatedField):
    """選項驗證欄位"""

    def __init__(self, choices: tuple, error_msg: str = "無效的選項"):
        self.choices = choices
        super().__init__(
            validator=lambda v: v in self.choices,
            error_msg=f"{error_msg}，必須是: {', '.join(str(c) for c in choices)}"
        )

class NonEmptyField(ValidatedField):
    """非空驗證欄位"""

    def __init__(self, error_msg: str = "不能為空"):
        super().__init__(
            validator=lambda v: bool(v),
            error_msg=error_msg
        )

class RangeField(ValidatedField):
    """範圍驗證欄位"""

    def __init__(
        self,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        error_msg: str = "超出範圍"
    ):
        self.min_val = min_val
        self.max_val = max_val

        def validator(v):
            if min_val is not None and v < min_val:
                return False
            if max_val is not None and v > max_val:
                return False
            return True

        range_desc = []
        if min_val is not None:
            range_desc.append(f">= {min_val}")
        if max_val is not None:
            range_desc.append(f"<= {max_val}")

        super().__init__(
            validator=validator,
            error_msg=f"{error_msg}，必須 {' 且 '.join(range_desc)}"
        )

# ===== 使用範例 =====

class HookConfig:
    """Hook 配置類別 - 宣告式驗證"""

    name = PatternField(
        r"^[a-z0-9][a-z0-9\-_]*[a-z0-9]$",
        "Hook 名稱格式無效"
    )

    event = ChoiceField(
        ("PreToolUse", "PostToolUse", "Stop", "SessionStart", "SessionEnd"),
        "無效的事件類型"
    )

    command = NonEmptyField("命令不能為空")

    timeout = RangeField(min_val=0, max_val=300, error_msg="超時時間無效")

    def __init__(self, name: str, event: str, command: str, timeout: int = 30):
        self.name = name
        self.event = event
        self.command = command
        self.timeout = timeout

    def __repr__(self) -> str:
        return f"HookConfig({self.name!r}, {self.event!r}, {self.command!r})"

# ===== 測試 =====

if __name__ == "__main__":
    # 正確的配置
    config = HookConfig(
        name="check-format",
        event="PreToolUse",
        command="python check.py"
    )
    print(f"建立成功: {config}")

    # 修改屬性也會驗證
    config.timeout = 60
    print(f"修改 timeout: {config.timeout}")

    # 驗證失敗的例子
    try:
        bad_config = HookConfig(
            name="Check-Format",  # 錯誤：大寫
            event="PreToolUse",
            command="python check.py"
        )
    except ValueError as e:
        print(f"驗證失敗: {e}")

    try:
        config.event = "InvalidEvent"  # 錯誤：無效的事件
    except ValueError as e:
        print(f"驗證失敗: {e}")

    try:
        config.timeout = 500  # 錯誤：超出範圍
    except ValueError as e:
        print(f"驗證失敗: {e}")
```

### 使用範例

```python
# 正確的配置
>>> config = HookConfig(
...     name="check-format",
...     event="PreToolUse",
...     command="python check.py"
... )
>>> config
HookConfig('check-format', 'PreToolUse', 'python check.py')

# 修改屬性也會驗證
>>> config.timeout = 60
>>> config.timeout
60

# 驗證失敗
>>> config.name = "Invalid Name"
ValueError: name: Hook 名稱格式無效

>>> config.event = "BadEvent"
ValueError: event: 無效的事件類型，必須是: PreToolUse, PostToolUse, Stop, SessionStart, SessionEnd

>>> config.timeout = -1
ValueError: timeout: 超時時間無效，必須 >= 0 且 <= 300
```

## 設計權衡

| 面向 | 命令式驗證 | 宣告式驗證（Descriptor） |
|------|------------|--------------------------|
| 可讀性 | 驗證邏輯散落在方法中 | 驗證規則在類別定義中可見 |
| 重用性 | 需要複製驗證邏輯 | Descriptor 可在多個類別重用 |
| 賦值驗證 | 需要手動呼叫驗證 | 自動在賦值時驗證 |
| 複雜度 | 簡單直覺 | 需要理解 Descriptor Protocol |
| 調試 | 容易追蹤 | 需要了解 `__get__`/`__set__` |
| 彈性 | 高 | 中等（需要遵循 Descriptor 協議） |

## 什麼時候該用宣告式驗證？

✅ **適合使用**：

- 資料類別（Data Class）需要驗證
- 同樣的驗證規則需要在多處使用
- 希望在類別定義中清楚看到驗證規則
- 需要在屬性賦值時自動驗證

❌ **不建議使用**：

- 簡單的一次性驗證
- 驗證邏輯需要存取多個欄位
- 團隊不熟悉 Descriptor Protocol
- 驗證邏輯經常變動

## 進階：與 dataclass 結合

Python 3.7+ 的 `dataclass` 可以與 Descriptor 結合：

```python
from dataclasses import dataclass, field

@dataclass
class HookConfigDataclass:
    """使用 dataclass + Descriptor"""

    # Descriptor 欄位需要特殊處理
    _name: str = field(init=False, repr=False)
    _event: str = field(init=False, repr=False)

    # 公開欄位
    name: str = field(default="")
    event: str = field(default="PreToolUse")

    # Descriptor 定義（類別變數）
    name = PatternField(r"^[a-z0-9][a-z0-9\-_]*[a-z0-9]$", "無效的名稱")
    event = ChoiceField(("PreToolUse", "PostToolUse", "Stop"), "無效的事件")

    def __post_init__(self):
        # 觸發 Descriptor 驗證
        self.name = self.name
        self.event = self.event
```

## 練習

### 基礎練習

1. 實作一個 `EmailField` Descriptor，驗證 email 格式
2. 實作一個 `LengthField` Descriptor，驗證字串長度

### 進階練習

3. 修改 `ValidatedField`，支援可選欄位（允許 `None`）
4. 實作一個 `CompositeField`，可以組合多個驗證規則

### 挑戰題

5. 參考 `hook_validator.py` 的 `check_lib_imports` 方法，用 Descriptor 實現「根據欄位值決定是否需要驗證另一個欄位」的邏輯

## 延伸閱讀

- [Python Descriptor HOWTO](https://docs.python.org/3/howto/descriptor.html)
- [Django Model Field](https://docs.djangoproject.com/en/5.0/howto/custom-model-fields/)
- [Pydantic Field Validators](https://docs.pydantic.dev/latest/concepts/validators/)

---

*上一章：[案例研究索引](../)*
*下一章：[案例：自動註冊機制](../auto-registration/)*
