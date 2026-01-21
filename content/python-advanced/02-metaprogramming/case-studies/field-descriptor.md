---
title: "案例：類似 Django Field 的設計"
date: 2026-01-21
description: "結合 Descriptor 和 dataclass 設計類似 Django Model Field 的宣告式 API"
weight: 3
---

# 案例：類似 Django Field 的設計

本案例基於 `.claude/lib/hook_io.py` 的實際程式碼，展示如何結合 Descriptor 和 dataclass 設計類似 Django Model Field 的宣告式 API。

## 先備知識

- [2.1 宣告式驗證](../declarative-validation/)
- [2.3 類別裝飾器與動態類別](../../class-creation/)

## 問題背景

### 現有設計

`hook_io.py` 使用函式工廠模式建構 Hook 輸出：

```python
def create_pretooluse_output(
    decision: str,
    reason: str,
    user_prompt: Optional[str] = None,
    system_message: Optional[str] = None,
    suppress_output: bool = False
) -> dict:
    """
    建立 PreToolUse Hook 輸出格式

    Args:
        decision: 決策結果 ("allow" | "deny" | "ask")
        reason: 決策原因說明
        user_prompt: 詢問用戶的訊息（僅當 decision 為 "ask" 時使用）
        system_message: 系統訊息（可選）
        suppress_output: 是否抑制輸出（預設 False）

    Returns:
        dict: 標準 PreToolUse Hook 輸出格式
    """
    output: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason
        }
    }

    if user_prompt:
        output["hookSpecificOutput"]["userPrompt"] = user_prompt

    if system_message:
        output["systemMessage"] = system_message

    if suppress_output:
        output["suppressOutput"] = True

    return output
```

### 這個設計的優點

- **清晰的建構流程**：函式簽名清楚說明所需參數
- **支援可選參數**：使用 `Optional` 和預設值處理可選欄位
- **型別提示完整**：有完整的參數型別標註

### 這個設計的限制

當需要序列化/反序列化時：

- **需要手動處理每個欄位**：to_dict 和 from_dict 需要逐一處理
- **欄位定義與驗證分離**：型別檢查和業務驗證在不同地方
- **難以生成文件或 schema**：無法自動產生 JSON Schema 或 API 文件

## 進階解決方案

### 設計目標

1. **欄位定義包含型別、驗證、序列化**
2. **自動生成 `__init__`、`to_dict`、`from_dict`**
3. **支援巢狀結構**

### 實作步驟

#### 步驟 1：設計 Field 基類

```python
from typing import Any, Optional, Type, Generic, TypeVar, Callable, get_type_hints

T = TypeVar("T")

class Field(Generic[T]):
    """
    Field Descriptor base class

    Combines Django's field declaration style with Python's
    descriptor protocol for type-safe, declarative model design.
    """

    def __init__(
        self,
        *,
        default: Optional[T] = None,
        required: bool = True,
        serialized_name: Optional[str] = None,
        validator: Optional[Callable[[T], bool]] = None,
        error_msg: str = "Validation failed"
    ):
        """
        Args:
            default: Default value when not provided
            required: Whether field is required (default True)
            serialized_name: Name used in serialization (default: attribute name)
            validator: Optional validation function
            error_msg: Error message for validation failure
        """
        self.default = default
        self.required = required
        self.serialized_name = serialized_name
        self.validator = validator
        self.error_msg = error_msg

        # Set by __set_name__
        self.name: str = ""
        self.private_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        """
        Called automatically when the descriptor is assigned to a class attribute.

        This is where we get the attribute name from the class definition,
        eliminating the need to pass it explicitly.
        """
        self.name = name
        self.private_name = f"_field_{name}"
        # Use attribute name as serialized name if not specified
        if self.serialized_name is None:
            self.serialized_name = name

    def __get__(self, obj: Any, objtype: type = None) -> Any:
        """Return field value or descriptor itself if accessed on class."""
        if obj is None:
            return self  # Class access returns descriptor
        return getattr(obj, self.private_name, self.default)

    def __set__(self, obj: Any, value: Any) -> None:
        """Validate and set field value."""
        # Handle None for optional fields
        if value is None:
            if self.required and self.default is None:
                raise ValueError(f"{self.name}: This field is required")
            setattr(obj, self.private_name, self.default)
            return

        # Run custom validator if provided
        if self.validator and not self.validator(value):
            raise ValueError(f"{self.name}: {self.error_msg}")

        setattr(obj, self.private_name, value)

    def serialize(self, value: T) -> Any:
        """Convert Python value to serializable format."""
        return value

    def deserialize(self, value: Any) -> T:
        """Convert serialized value to Python type."""
        return value
```

**關鍵設計要點**：

1. **`__set_name__`** 自動取得屬性名稱，不需要像 Django 早期版本手動傳入
2. **`serialized_name`** 支援序列化時使用不同的欄位名稱（如 camelCase）
3. **`serialize`/`deserialize`** 方法供子類覆寫，實現型別轉換

#### 步驟 2：實作型別特定的 Field

```python
import re
from datetime import datetime
from typing import List, Type, TypeVar

class StringField(Field[str]):
    """String field with optional pattern validation."""

    def __init__(
        self,
        *,
        pattern: Optional[str] = None,
        min_length: int = 0,
        max_length: Optional[int] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.pattern = re.compile(pattern) if pattern else None
        self.min_length = min_length
        self.max_length = max_length

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None:
            if not isinstance(value, str):
                raise TypeError(f"{self.name}: Expected str, got {type(value).__name__}")

            if self.min_length and len(value) < self.min_length:
                raise ValueError(f"{self.name}: Minimum length is {self.min_length}")

            if self.max_length and len(value) > self.max_length:
                raise ValueError(f"{self.name}: Maximum length is {self.max_length}")

            if self.pattern and not self.pattern.match(value):
                raise ValueError(f"{self.name}: Does not match pattern")

        super().__set__(obj, value)

class IntField(Field[int]):
    """Integer field with range validation."""

    def __init__(
        self,
        *,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None:
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{self.name}: Expected int, got {type(value).__name__}")

            if self.min_value is not None and value < self.min_value:
                raise ValueError(f"{self.name}: Minimum value is {self.min_value}")

            if self.max_value is not None and value > self.max_value:
                raise ValueError(f"{self.name}: Maximum value is {self.max_value}")

        super().__set__(obj, value)

class BoolField(Field[bool]):
    """Boolean field."""

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None and not isinstance(value, bool):
            raise TypeError(f"{self.name}: Expected bool, got {type(value).__name__}")
        super().__set__(obj, value)

class ChoiceField(Field[str]):
    """Field with predefined choices."""

    def __init__(self, *, choices: tuple[str, ...], **kwargs):
        super().__init__(**kwargs)
        self.choices = choices

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None and value not in self.choices:
            choices_str = ", ".join(repr(c) for c in self.choices)
            raise ValueError(f"{self.name}: Must be one of: {choices_str}")
        super().__set__(obj, value)

class ListField(Field[list]):
    """List field with item type validation."""

    def __init__(self, *, item_field: Field, **kwargs):
        # ListField defaults to empty list, not required
        kwargs.setdefault("default", [])
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)
        self.item_field = item_field

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None:
            if not isinstance(value, list):
                raise TypeError(f"{self.name}: Expected list, got {type(value).__name__}")
            # Validate each item using item_field's validation logic
            # (simplified - in production you'd want proper item validation)
        super().__set__(obj, value if value is not None else [])

    def serialize(self, value: list) -> list:
        """Serialize list items."""
        return [self.item_field.serialize(item) for item in value]

    def deserialize(self, value: list) -> list:
        """Deserialize list items."""
        return [self.item_field.deserialize(item) for item in value]

class DateTimeField(Field[datetime]):
    """DateTime field with ISO format serialization."""

    def __init__(self, *, format: str = "%Y-%m-%dT%H:%M:%S", **kwargs):
        super().__init__(**kwargs)
        self.format = format

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None and not isinstance(value, datetime):
            raise TypeError(f"{self.name}: Expected datetime, got {type(value).__name__}")
        super().__set__(obj, value)

    def serialize(self, value: datetime) -> str:
        """Convert datetime to ISO string."""
        return value.strftime(self.format) if value else None

    def deserialize(self, value: str) -> datetime:
        """Parse ISO string to datetime."""
        return datetime.strptime(value, self.format) if value else None
```

#### 步驟 3：用 Metaclass 處理欄位收集

```python
class ModelMeta(type):
    """
    Metaclass for Model classes.

    Responsibilities:
    1. Collect all Field descriptors from class definition
    2. Store field metadata for serialization/deserialization
    3. Generate __init__ signature from fields
    """

    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        # Collect fields from this class and parent classes
        fields: dict[str, Field] = {}

        # Inherit fields from parent Model classes
        for base in bases:
            if hasattr(base, "_fields"):
                fields.update(base._fields)

        # Collect fields from current class
        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value

        # Store fields metadata
        namespace["_fields"] = fields

        return super().__new__(mcs, name, bases, namespace)

class Model(metaclass=ModelMeta):
    """
    Base class for declarative models.

    Provides:
    - Automatic __init__ from field definitions
    - to_dict() for serialization
    - from_dict() for deserialization
    """

    _fields: dict[str, Field]  # Set by metaclass

    def __init__(self, **kwargs):
        """
        Initialize model from keyword arguments.

        All defined fields can be passed as keyword arguments.
        Required fields must be provided unless they have defaults.
        """
        # Set each field value, triggering descriptor validation
        for field_name, field in self._fields.items():
            value = kwargs.get(field_name, field.default)
            setattr(self, field_name, value)

        # Check for unknown fields
        unknown = set(kwargs.keys()) - set(self._fields.keys())
        if unknown:
            raise TypeError(f"Unknown fields: {', '.join(unknown)}")

    def to_dict(self) -> dict:
        """
        Serialize model to dictionary.

        Uses each field's serialized_name and serialize() method.
        """
        result = {}
        for field_name, field in self._fields.items():
            value = getattr(self, field_name)
            if value is not None or field.required:
                serialized_name = field.serialized_name or field_name
                result[serialized_name] = field.serialize(value)
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Model":
        """
        Deserialize dictionary to model instance.

        Handles field name mapping and type conversion.
        """
        kwargs = {}

        for field_name, field in cls._fields.items():
            serialized_name = field.serialized_name or field_name

            if serialized_name in data:
                kwargs[field_name] = field.deserialize(data[serialized_name])
            elif field_name in data:
                # Fallback to field name if serialized name not found
                kwargs[field_name] = field.deserialize(data[field_name])

        return cls(**kwargs)

    def __repr__(self) -> str:
        """Generate readable representation."""
        field_strs = []
        for field_name in self._fields:
            value = getattr(self, field_name)
            field_strs.append(f"{field_name}={value!r}")
        return f"{self.__class__.__name__}({', '.join(field_strs)})"

    def __eq__(self, other) -> bool:
        """Compare models by their field values."""
        if not isinstance(other, self.__class__):
            return False
        for field_name in self._fields:
            if getattr(self, field_name) != getattr(other, field_name):
                return False
        return True
```

#### 步驟 4：加入巢狀 Model 支援

```python
class EmbeddedField(Field):
    """
    Embedded model field for nested structures.

    Allows nesting Model instances within other Models.
    """

    def __init__(self, *, model_class: Type[Model], **kwargs):
        super().__init__(**kwargs)
        self.model_class = model_class

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None:
            # Accept dict and convert to model
            if isinstance(value, dict):
                value = self.model_class.from_dict(value)
            elif not isinstance(value, self.model_class):
                raise TypeError(
                    f"{self.name}: Expected {self.model_class.__name__} or dict, "
                    f"got {type(value).__name__}"
                )
        super().__set__(obj, value)

    def serialize(self, value: Model) -> dict:
        """Serialize embedded model to dict."""
        return value.to_dict() if value else None

    def deserialize(self, value: dict) -> Model:
        """Deserialize dict to embedded model."""
        return self.model_class.from_dict(value) if value else None
```

### 完整程式碼

```python
#!/usr/bin/env python3
"""
Django-style Field Descriptor - Complete Implementation

Demonstrates how to combine Descriptor protocol with Metaclass
to create a declarative API similar to Django Model Fields.
"""

from __future__ import annotations
import re
from datetime import datetime
from typing import Any, Optional, Type, Generic, TypeVar, Callable

T = TypeVar("T")

# ===== Field Descriptors =====

class Field(Generic[T]):
    """Base Field Descriptor with validation and serialization."""

    def __init__(
        self,
        *,
        default: Optional[T] = None,
        required: bool = True,
        serialized_name: Optional[str] = None,
        validator: Optional[Callable[[T], bool]] = None,
        error_msg: str = "Validation failed"
    ):
        self.default = default
        self.required = required
        self.serialized_name = serialized_name
        self.validator = validator
        self.error_msg = error_msg
        self.name: str = ""
        self.private_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.private_name = f"_field_{name}"
        if self.serialized_name is None:
            self.serialized_name = name

    def __get__(self, obj: Any, objtype: type = None) -> Any:
        if obj is None:
            return self
        return getattr(obj, self.private_name, self.default)

    def __set__(self, obj: Any, value: Any) -> None:
        if value is None:
            if self.required and self.default is None:
                raise ValueError(f"{self.name}: This field is required")
            setattr(obj, self.private_name, self.default)
            return

        if self.validator and not self.validator(value):
            raise ValueError(f"{self.name}: {self.error_msg}")

        setattr(obj, self.private_name, value)

    def serialize(self, value: T) -> Any:
        return value

    def deserialize(self, value: Any) -> T:
        return value

class StringField(Field[str]):
    """String field with pattern and length validation."""

    def __init__(
        self,
        *,
        pattern: Optional[str] = None,
        min_length: int = 0,
        max_length: Optional[int] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.pattern = re.compile(pattern) if pattern else None
        self.min_length = min_length
        self.max_length = max_length

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None:
            if not isinstance(value, str):
                raise TypeError(f"{self.name}: Expected str, got {type(value).__name__}")
            if self.min_length and len(value) < self.min_length:
                raise ValueError(f"{self.name}: Minimum length is {self.min_length}")
            if self.max_length and len(value) > self.max_length:
                raise ValueError(f"{self.name}: Maximum length is {self.max_length}")
            if self.pattern and not self.pattern.match(value):
                raise ValueError(f"{self.name}: Does not match required pattern")
        super().__set__(obj, value)

class IntField(Field[int]):
    """Integer field with range validation."""

    def __init__(
        self,
        *,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None:
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{self.name}: Expected int, got {type(value).__name__}")
            if self.min_value is not None and value < self.min_value:
                raise ValueError(f"{self.name}: Minimum value is {self.min_value}")
            if self.max_value is not None and value > self.max_value:
                raise ValueError(f"{self.name}: Maximum value is {self.max_value}")
        super().__set__(obj, value)

class BoolField(Field[bool]):
    """Boolean field."""

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None and not isinstance(value, bool):
            raise TypeError(f"{self.name}: Expected bool, got {type(value).__name__}")
        super().__set__(obj, value)

class ChoiceField(Field[str]):
    """Field with predefined choices."""

    def __init__(self, *, choices: tuple[str, ...], **kwargs):
        super().__init__(**kwargs)
        self.choices = choices

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None and value not in self.choices:
            choices_str = ", ".join(repr(c) for c in self.choices)
            raise ValueError(f"{self.name}: Must be one of: {choices_str}")
        super().__set__(obj, value)

class ListField(Field[list]):
    """List field with item type."""

    def __init__(self, *, item_field: Field, **kwargs):
        kwargs.setdefault("default", [])
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)
        self.item_field = item_field

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None and not isinstance(value, list):
            raise TypeError(f"{self.name}: Expected list, got {type(value).__name__}")
        super().__set__(obj, value if value is not None else [])

    def serialize(self, value: list) -> list:
        return [self.item_field.serialize(item) for item in (value or [])]

    def deserialize(self, value: list) -> list:
        return [self.item_field.deserialize(item) for item in (value or [])]

class DateTimeField(Field[datetime]):
    """DateTime field with ISO format."""

    def __init__(self, *, format: str = "%Y-%m-%dT%H:%M:%S", **kwargs):
        super().__init__(**kwargs)
        self.format = format

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None and not isinstance(value, datetime):
            raise TypeError(f"{self.name}: Expected datetime, got {type(value).__name__}")
        super().__set__(obj, value)

    def serialize(self, value: datetime) -> Optional[str]:
        return value.strftime(self.format) if value else None

    def deserialize(self, value: str) -> Optional[datetime]:
        return datetime.strptime(value, self.format) if value else None

# ===== Metaclass and Model =====

class ModelMeta(type):
    """Metaclass that collects Field descriptors."""

    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        fields: dict[str, Field] = {}

        # Inherit from parent classes
        for base in bases:
            if hasattr(base, "_fields"):
                fields.update(base._fields)

        # Collect from current class
        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value

        namespace["_fields"] = fields
        return super().__new__(mcs, name, bases, namespace)

class Model(metaclass=ModelMeta):
    """Base Model with automatic serialization."""

    _fields: dict[str, Field]

    def __init__(self, **kwargs):
        for field_name, field in self._fields.items():
            value = kwargs.get(field_name, field.default)
            setattr(self, field_name, value)

        unknown = set(kwargs.keys()) - set(self._fields.keys())
        if unknown:
            raise TypeError(f"Unknown fields: {', '.join(unknown)}")

    def to_dict(self) -> dict:
        result = {}
        for field_name, field in self._fields.items():
            value = getattr(self, field_name)
            if value is not None or field.required:
                key = field.serialized_name or field_name
                result[key] = field.serialize(value)
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Model":
        kwargs = {}
        for field_name, field in cls._fields.items():
            key = field.serialized_name or field_name
            if key in data:
                kwargs[field_name] = field.deserialize(data[key])
            elif field_name in data:
                kwargs[field_name] = field.deserialize(data[field_name])
        return cls(**kwargs)

    def __repr__(self) -> str:
        parts = [f"{k}={getattr(self, k)!r}" for k in self._fields]
        return f"{self.__class__.__name__}({', '.join(parts)})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return all(
            getattr(self, k) == getattr(other, k)
            for k in self._fields
        )

class EmbeddedField(Field):
    """Embedded model field for nested structures."""

    def __init__(self, *, model_class: Type[Model], **kwargs):
        super().__init__(**kwargs)
        self.model_class = model_class

    def __set__(self, obj: Any, value: Any) -> None:
        if value is not None:
            if isinstance(value, dict):
                value = self.model_class.from_dict(value)
            elif not isinstance(value, self.model_class):
                raise TypeError(
                    f"{self.name}: Expected {self.model_class.__name__} or dict"
                )
        super().__set__(obj, value)

    def serialize(self, value: Model) -> Optional[dict]:
        return value.to_dict() if value else None

    def deserialize(self, value: dict) -> Optional[Model]:
        return self.model_class.from_dict(value) if value else None
```

### 使用範例

```python
# ===== Define Models =====

class HookSpecificOutput(Model):
    """Nested model for hook-specific output."""

    hook_event_name = ChoiceField(
        choices=("PreToolUse", "PostToolUse", "Stop"),
        serialized_name="hookEventName"
    )
    permission_decision = ChoiceField(
        choices=("allow", "deny", "ask"),
        serialized_name="permissionDecision"
    )
    permission_reason = StringField(
        min_length=1,
        serialized_name="permissionDecisionReason"
    )
    user_prompt = StringField(
        required=False,
        serialized_name="userPrompt"
    )

class HookOutput(Model):
    """
    Hook Output model - similar to create_pretooluse_output

    Declarative definition replaces the factory function.
    """

    hook_specific_output = EmbeddedField(
        model_class=HookSpecificOutput,
        serialized_name="hookSpecificOutput"
    )
    system_message = StringField(
        required=False,
        serialized_name="systemMessage"
    )
    suppress_output = BoolField(
        default=False,
        required=False,
        serialized_name="suppressOutput"
    )

# ===== Usage Examples =====

if __name__ == "__main__":
    # Create model instance
    output = HookOutput(
        hook_specific_output=HookSpecificOutput(
            hook_event_name="PreToolUse",
            permission_decision="allow",
            permission_reason="Operation permitted"
        ),
        system_message="Check completed"
    )
    print(f"Created: {output}")

    # Serialize to dict (ready for JSON)
    data = output.to_dict()
    print(f"Serialized: {data}")
    # Output:
    # {
    #     "hookSpecificOutput": {
    #         "hookEventName": "PreToolUse",
    #         "permissionDecision": "allow",
    #         "permissionDecisionReason": "Operation permitted"
    #     },
    #     "systemMessage": "Check completed",
    #     "suppressOutput": False
    # }

    # Deserialize from dict
    restored = HookOutput.from_dict(data)
    print(f"Restored: {restored}")
    print(f"Equal: {output == restored}")

    # Validation examples
    try:
        bad = HookSpecificOutput(
            hook_event_name="InvalidEvent",  # Error: not in choices
            permission_decision="allow",
            permission_reason="Test"
        )
    except ValueError as e:
        print(f"Validation error: {e}")

    # Nested dict conversion
    output2 = HookOutput(
        hook_specific_output={  # Auto-converts dict to model
            "hook_event_name": "PostToolUse",
            "permission_decision": "deny",
            "permission_reason": "Access denied"
        }
    )
    print(f"From nested dict: {output2}")
```

**執行結果**：

```text
Created: HookOutput(hook_specific_output=HookSpecificOutput(...), system_message='Check completed', suppress_output=False)
Serialized: {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'allow', 'permissionDecisionReason': 'Operation permitted'}, 'systemMessage': 'Check completed', 'suppressOutput': False}
Restored: HookOutput(hook_specific_output=HookSpecificOutput(...), system_message='Check completed', suppress_output=False)
Equal: True
Validation error: hook_event_name: Must be one of: 'PreToolUse', 'PostToolUse', 'Stop'
From nested dict: HookOutput(hook_specific_output=HookSpecificOutput(...), system_message=None, suppress_output=False)
```

## 設計權衡

| 面向 | 函式工廠模式 | Field Descriptor |
|------|-----------------|------------------|
| **學習曲線** | 低，只需了解函式 | 中，需理解 Descriptor + Metaclass |
| **程式碼量** | 每個輸出類型一個函式 | 一次性建立後可重用 |
| **欄位定義** | 分散在函式簽名和函式體 | 集中在類別定義中 |
| **型別提示** | 需手動維護 | 與欄位定義整合 |
| **序列化** | 每個函式獨立實作 | 自動生成 |
| **驗證時機** | 呼叫時驗證 | 賦值時驗證 |
| **巢狀結構** | 需手動處理 | EmbeddedField 自動處理 |
| **Schema 生成** | 無法自動化 | 可從 _fields 元資料生成 |
| **調試** | 直覺，錯誤位置明確 | 需理解 Descriptor 協議 |

### 關鍵差異說明

**函式工廠模式**（如 hook_io.py）：

- 適合簡單、一次性的資料建構
- 不需要額外的學習成本
- 但重複程式碼多，難以維護

**Field Descriptor 模式**：

- 初期投入較高，但長期收益大
- 欄位定義即文檔
- 易於擴展和測試

## 什麼時候該用這個技術？

**適合使用**：

- ORM/ODM 設計（如 Django Model、MongoDB ODM）
- 配置檔案解析（型別安全的 YAML/JSON 解析）
- API 請求/回應模型（REST API、GraphQL）
- 需要 Schema 自動生成的場景
- 多個類似結構的資料類別

**不建議使用**：
- 簡單的資料容器（直接用 dataclass）
- 不需要序列化的內部類別
- Pydantic 已經滿足需求
- 團隊不熟悉元編程
- 單一用途的資料結構

## 與 Pydantic 的比較

| 功能 | 自製 Field Descriptor | Pydantic |
| ---- | --------------------- | -------- |
| 型別驗證 | 手動實作 | 自動 |
| JSON Schema | 需額外實作 | 內建 |
| 效能 | 依實作而定 | 高度優化 |
| 學習價值 | 高，理解原理 | 低，直接使用 |
| 客製化彈性 | 完全控制 | 受框架限制 |

**建議**：在生產環境優先考慮 Pydantic；學習元編程時使用自製實作。

## 練習

### 基礎練習

1. **實作 `BoolField` 和 `DateTimeField`**

   完成以下 Field 類別，支援型別驗證和序列化：

   ```python
   class BoolField(Field[bool]):
       """Boolean field with strict type checking."""
       pass  # TODO: implement

   class DateTimeField(Field[datetime]):
       """DateTime field with custom format."""
       pass  # TODO: implement
   ```

2. **新增欄位的預設值和 required 屬性**

   修改 Field 基類，讓以下程式碼能正確運作：

   ```python
   class Config(Model):
       name = StringField(required=True)
       timeout = IntField(default=30, required=False)
       debug = BoolField(default=False, required=False)

   # 應該能建立實例
   config = Config(name="test")
   assert config.timeout == 30
   assert config.debug == False
   ```

### 進階練習

3. **實作巢狀 Model（`EmbeddedField`）**

   讓以下程式碼能正確運作：

   ```python
   class Address(Model):
       city = StringField()
       street = StringField()

   class Person(Model):
       name = StringField()
       address = EmbeddedField(model_class=Address)

   # 從巢狀 dict 建立
   person = Person.from_dict({
       "name": "Alice",
       "address": {"city": "Taipei", "street": "Main St"}
   })

   # 序列化回 dict
   data = person.to_dict()
   ```

4. **實作 ListField 的完整驗證**

   讓以下程式碼能驗證列表中的每個項目：

   ```python
   class Tag(Model):
       name = StringField(pattern=r"^[a-z]+$")
       priority = IntField(min_value=1, max_value=10)

   class Article(Model):
       title = StringField()
       tags = ListField(item_field=EmbeddedField(model_class=Tag))

   # 每個 tag 都應該被驗證
   article = Article(
       title="Python Tips",
       tags=[
           {"name": "python", "priority": 5},
           {"name": "INVALID", "priority": 5}  # Should raise error
       ]
   )
   ```

### 挑戰題

5. **實作 Schema 自動生成**

   為 Model 類別新增 `to_json_schema()` 類別方法，自動生成 JSON Schema：

   ```python
   class User(Model):
       name = StringField(min_length=1, max_length=100)
       age = IntField(min_value=0, max_value=150)
       email = StringField(pattern=r"^[\w.-]+@[\w.-]+\.\w+$")

   schema = User.to_json_schema()
   # 應該輸出：
   # {
   #     "type": "object",
   #     "properties": {
   #         "name": {"type": "string", "minLength": 1, "maxLength": 100},
   #         "age": {"type": "integer", "minimum": 0, "maximum": 150},
   #         "email": {"type": "string", "pattern": "^[\\w.-]+@[\\w.-]+\\.\\w+$"}
   #     },
   #     "required": ["name", "age", "email"]
   # }
   ```

## 延伸閱讀

- [Django Model Field 原始碼](https://github.com/django/django/blob/main/django/db/models/fields/__init__.py)
- [Pydantic Field 實作](https://github.com/pydantic/pydantic)
- [Python Descriptor HOWTO](https://docs.python.org/3/howto/descriptor.html)
- [attrs 專案](https://www.attrs.org/) - 另一個優秀的 Python 類別輔助工具

---

*上一章：[自動註冊機制](../auto-registration/)*
*返回：[模組二：元編程](../../)*
