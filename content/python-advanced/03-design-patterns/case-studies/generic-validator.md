---
title: "案例：泛型驗證器"
date: 2026-01-21
description: "用 Generic 和 TypeVar 建立型別安全的通用驗證器"
weight: 4
---

# 案例：泛型驗證器

本案例基於 `.claude/lib/hook_validator.py` 的實際程式碼，展示如何用 Generic 和 TypeVar 建立型別安全的通用驗證器。

## 先備知識

- 入門系列 [2.2 Optional、Union、泛型](../../../python/02-type-system/optional-union/)
- [3.5.1 泛型進階](../../generics/)

## 問題背景

### 現有設計

`hook_validator.py` 針對特定類型設計：

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List

@dataclass
class ValidationIssue:
    """Single validation issue"""
    level: str  # "error" | "warning" | "info"
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    """Validation result for a single hook"""
    hook_path: str
    issues: List[ValidationIssue] = field(default_factory=list)
    is_compliant: bool = True

    def __post_init__(self):
        """Calculate is_compliant status"""
        self.is_compliant = not any(
            issue.level == "error" for issue in self.issues
        )

class HookValidator:
    """Hook compliance validator - specific to Path type"""

    def validate_hook(self, hook_path: str) -> ValidationResult:
        """Validate a single hook file"""
        hook_path = self._resolve_path(hook_path)

        if not hook_path.exists():
            return ValidationResult(
                hook_path=str(hook_path),
                issues=[ValidationIssue(
                    level="error",
                    message=f"Hook file not found: {hook_path}"
                )]
            )

        # ... more validation logic ...
        return ValidationResult(hook_path=str(hook_path))

    def _resolve_path(self, path: str) -> Path:
        """Resolve path to absolute path"""
        p = Path(path)
        return p if p.is_absolute() else Path.cwd() / p
```

### 這個設計的優點

- **針對具體需求設計**：專為驗證 Hook 檔案設計，邏輯清晰
- **型別明確**：輸入是 `str`，輸出是 `ValidationResult`

### 這個設計的限制

當需要驗證其他類型時：

- **需要複製大量相似程式碼**：如果要驗證 API 回應、設定檔、表單輸入，需要寫多個類似的 Validator
- **驗證邏輯無法重用**：「檢查是否為空」「檢查格式」這些通用邏輯無法跨 Validator 共享
- **型別檢查不夠通用**：`ValidationResult` 綁定了 `hook_path: str`，無法用於其他場景

## 進階解決方案

### 設計目標

1. **建立通用的驗證器介面**：定義 `Validator[T]` 協議
2. **支援任意輸入類型**：可以驗證 `Path`、`str`、`dict`、自訂類別
3. **保持型別安全**：靜態型別檢查器能捕捉型別錯誤
4. **支援驗證器組合**：用 `And`、`Or`、`Not` 組合基本驗證器

### 實作步驟

#### 步驟 1：定義泛型 Validator 協議

首先，我們需要定義「什麼是驗證器」。使用 Protocol 和 TypeVar 來建立泛型介面：

```python
from typing import Protocol, TypeVar, Generic
from dataclasses import dataclass, field
from abc import abstractmethod

# Define a type variable for the input type
T = TypeVar("T")

# Type variable with contravariance for Protocol
T_contra = TypeVar("T_contra", contravariant=True)

@dataclass
class ValidationResult(Generic[T]):
    """
    Generic validation result

    Type parameter T represents the validated value type.
    This allows type-safe access to the validated value.
    """
    value: T
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> "ValidationResult[T]":
        """Add an error and mark as invalid"""
        self.errors.append(message)
        self.is_valid = False
        return self

    def add_warning(self, message: str) -> "ValidationResult[T]":
        """Add a warning (does not affect validity)"""
        self.warnings.append(message)
        return self

class Validator(Protocol[T_contra]):
    """
    Generic validator protocol

    Any class that implements validate(value: T) -> ValidationResult[T]
    is considered a Validator[T].

    Using contravariant type variable because validators consume values.
    A Validator[Animal] can validate Dog (subtype), so it's contravariant.
    """

    def validate(self, value: T_contra) -> ValidationResult:
        """Validate the given value and return the result"""
        ...
```

**關鍵設計決策**：

- `T_contra` 使用逆變（contravariant），因為驗證器是「消費者」
- `ValidationResult[T]` 是泛型，讓結果可以攜帶原始值的型別資訊
- Protocol 而非 ABC，支援結構型子型別（不需要顯式繼承）

#### 步驟 2：實作具體驗證器

接下來實作幾個常用的基礎驗證器：

```python
from pathlib import Path
import re

class NotEmptyValidator:
    """Validate that a string is not empty"""

    def validate(self, value: str) -> ValidationResult[str]:
        result = ValidationResult(value=value)
        if not value or not value.strip():
            result.add_error("Value cannot be empty")
        return result

class PathExistsValidator:
    """Validate that a path exists"""

    def __init__(self, must_be_file: bool = False, must_be_dir: bool = False):
        self.must_be_file = must_be_file
        self.must_be_dir = must_be_dir

    def validate(self, value: Path) -> ValidationResult[Path]:
        result = ValidationResult(value=value)

        if not value.exists():
            result.add_error(f"Path does not exist: {value}")
        elif self.must_be_file and not value.is_file():
            result.add_error(f"Path is not a file: {value}")
        elif self.must_be_dir and not value.is_dir():
            result.add_error(f"Path is not a directory: {value}")

        return result

class PatternValidator:
    """Validate that a string matches a regex pattern"""

    def __init__(self, pattern: str, error_message: str | None = None):
        self.pattern = re.compile(pattern)
        self.error_message = error_message or f"Value must match pattern: {pattern}"

    def validate(self, value: str) -> ValidationResult[str]:
        result = ValidationResult(value=value)
        if not self.pattern.match(value):
            result.add_error(self.error_message)
        return result

class RangeValidator:
    """Validate that a number is within a range"""

    def __init__(
        self,
        min_value: float | None = None,
        max_value: float | None = None
    ):
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: float | int) -> ValidationResult[float | int]:
        result = ValidationResult(value=value)

        if self.min_value is not None and value < self.min_value:
            result.add_error(f"Value {value} is below minimum {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            result.add_error(f"Value {value} is above maximum {self.max_value}")

        return result
```

#### 步驟 3：驗證器組合（And、Or、Not）

驗證器的威力來自於組合。實作三個組合器：

```python
from typing import Sequence

class AndValidator(Generic[T]):
    """
    Combine multiple validators with AND logic

    All validators must pass for the result to be valid.
    """

    def __init__(self, validators: Sequence[Validator[T]]):
        self.validators = validators

    def validate(self, value: T) -> ValidationResult[T]:
        result = ValidationResult(value=value)

        for validator in self.validators:
            sub_result = validator.validate(value)
            result.errors.extend(sub_result.errors)
            result.warnings.extend(sub_result.warnings)

        result.is_valid = len(result.errors) == 0
        return result

class OrValidator(Generic[T]):
    """
    Combine multiple validators with OR logic

    At least one validator must pass for the result to be valid.
    """

    def __init__(self, validators: Sequence[Validator[T]]):
        self.validators = validators

    def validate(self, value: T) -> ValidationResult[T]:
        result = ValidationResult(value=value)
        all_errors: list[str] = []

        for validator in self.validators:
            sub_result = validator.validate(value)
            if sub_result.is_valid:
                # At least one passed, return success
                result.warnings.extend(sub_result.warnings)
                return result
            all_errors.extend(sub_result.errors)

        # All failed
        result.add_error(
            f"None of the validators passed. Errors: {'; '.join(all_errors)}"
        )
        return result

class NotValidator(Generic[T]):
    """
    Negate a validator

    The result is valid if the inner validator fails.
    """

    def __init__(self, validator: Validator[T], error_message: str | None = None):
        self.validator = validator
        self.error_message = error_message or "Validation should have failed"

    def validate(self, value: T) -> ValidationResult[T]:
        result = ValidationResult(value=value)
        sub_result = self.validator.validate(value)

        if sub_result.is_valid:
            result.add_error(self.error_message)
        # If inner failed, outer succeeds
        return result
```

#### 步驟 4：型別安全的建構器

為了讓組合更流暢，加入建構器模式：

```python
from typing import Callable

class ValidatorBuilder(Generic[T]):
    """
    Fluent builder for composing validators

    Provides a chainable API for building complex validators.
    """

    def __init__(self):
        self._validators: list[Validator[T]] = []

    def add(self, validator: Validator[T]) -> "ValidatorBuilder[T]":
        """Add a validator to the chain"""
        self._validators.append(validator)
        return self

    def add_if(
        self,
        condition: bool,
        validator: Validator[T]
    ) -> "ValidatorBuilder[T]":
        """Conditionally add a validator"""
        if condition:
            self._validators.append(validator)
        return self

    def build(self) -> Validator[T]:
        """Build the final AND-combined validator"""
        if len(self._validators) == 1:
            return self._validators[0]
        return AndValidator(self._validators)

    def build_or(self) -> Validator[T]:
        """Build with OR logic instead of AND"""
        if len(self._validators) == 1:
            return self._validators[0]
        return OrValidator(self._validators)

def validator_for(type_hint: type[T]) -> ValidatorBuilder[T]:
    """
    Create a type-safe validator builder

    Usage:
        validator = (
            validator_for(str)
            .add(NotEmptyValidator())
            .add(PatternValidator(r"^[a-z]+$"))
            .build()
        )
    """
    return ValidatorBuilder[T]()
```

### 完整程式碼

```python
#!/usr/bin/env python3
"""
Generic Validator System

A type-safe, composable validation framework using Generic and TypeVar.
"""

from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Callable,
    Generic,
    Protocol,
    Sequence,
    TypeVar,
    runtime_checkable,
)
import re

# ===== Type Variables =====

T = TypeVar("T")
T_contra = TypeVar("T_contra", contravariant=True)

# ===== Core Types =====

@dataclass
class ValidationResult(Generic[T]):
    """
    Generic validation result

    Attributes:
        value: The validated value (preserves type information)
        is_valid: Whether validation passed
        errors: List of error messages (cause validation failure)
        warnings: List of warning messages (informational only)
    """
    value: T
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> ValidationResult[T]:
        """Add an error and mark as invalid"""
        self.errors.append(message)
        self.is_valid = False
        return self

    def add_warning(self, message: str) -> ValidationResult[T]:
        """Add a warning (does not affect validity)"""
        self.warnings.append(message)
        return self

    def __bool__(self) -> bool:
        """Allow using result in boolean context"""
        return self.is_valid

@runtime_checkable
class Validator(Protocol[T_contra]):
    """
    Generic validator protocol

    Any class implementing validate(value) -> ValidationResult
    satisfies this protocol.
    """

    def validate(self, value: T_contra) -> ValidationResult:
        """Validate the given value"""
        ...

# ===== Basic Validators =====

class NotEmptyValidator:
    """Validate that a string is not empty"""

    def validate(self, value: str) -> ValidationResult[str]:
        result = ValidationResult(value=value)
        if not value or not value.strip():
            result.add_error("Value cannot be empty")
        return result

class PathExistsValidator:
    """Validate that a path exists"""

    def __init__(
        self,
        must_be_file: bool = False,
        must_be_dir: bool = False
    ):
        self.must_be_file = must_be_file
        self.must_be_dir = must_be_dir

    def validate(self, value: Path) -> ValidationResult[Path]:
        result = ValidationResult(value=value)

        if not value.exists():
            result.add_error(f"Path does not exist: {value}")
        elif self.must_be_file and not value.is_file():
            result.add_error(f"Path is not a file: {value}")
        elif self.must_be_dir and not value.is_dir():
            result.add_error(f"Path is not a directory: {value}")

        return result

class PatternValidator:
    """Validate string matches a regex pattern"""

    def __init__(self, pattern: str, error_message: str | None = None):
        self.pattern = re.compile(pattern)
        self.error_message = error_message or f"Must match pattern: {pattern}"

    def validate(self, value: str) -> ValidationResult[str]:
        result = ValidationResult(value=value)
        if not self.pattern.match(value):
            result.add_error(self.error_message)
        return result

class RangeValidator:
    """Validate number is within range"""

    def __init__(
        self,
        min_value: float | None = None,
        max_value: float | None = None
    ):
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: float | int) -> ValidationResult[float | int]:
        result = ValidationResult(value=value)
        if self.min_value is not None and value < self.min_value:
            result.add_error(f"Value {value} < minimum {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            result.add_error(f"Value {value} > maximum {self.max_value}")
        return result

class LengthValidator:
    """Validate string length"""

    def __init__(
        self,
        min_length: int | None = None,
        max_length: int | None = None
    ):
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: str) -> ValidationResult[str]:
        result = ValidationResult(value=value)
        length = len(value)

        if self.min_length is not None and length < self.min_length:
            result.add_error(f"Length {length} < minimum {self.min_length}")
        if self.max_length is not None and length > self.max_length:
            result.add_error(f"Length {length} > maximum {self.max_length}")

        return result

class TypeValidator(Generic[T]):
    """Validate value is of expected type"""

    def __init__(self, expected_type: type[T], type_name: str | None = None):
        self.expected_type = expected_type
        self.type_name = type_name or expected_type.__name__

    def validate(self, value: object) -> ValidationResult[T]:
        if isinstance(value, self.expected_type):
            return ValidationResult(value=value)  # type: ignore
        else:
            result = ValidationResult(value=value)  # type: ignore
            result.add_error(
                f"Expected {self.type_name}, got {type(value).__name__}"
            )
            return result

# ===== Composite Validators =====

class AndValidator(Generic[T]):
    """Combine validators with AND logic (all must pass)"""

    def __init__(self, validators: Sequence[Validator[T]]):
        self.validators = list(validators)

    def validate(self, value: T) -> ValidationResult[T]:
        result = ValidationResult(value=value)

        for validator in self.validators:
            sub_result = validator.validate(value)
            result.errors.extend(sub_result.errors)
            result.warnings.extend(sub_result.warnings)

        result.is_valid = len(result.errors) == 0
        return result

class OrValidator(Generic[T]):
    """Combine validators with OR logic (at least one must pass)"""

    def __init__(self, validators: Sequence[Validator[T]]):
        self.validators = list(validators)

    def validate(self, value: T) -> ValidationResult[T]:
        result = ValidationResult(value=value)
        all_errors: list[str] = []

        for validator in self.validators:
            sub_result = validator.validate(value)
            if sub_result.is_valid:
                result.warnings.extend(sub_result.warnings)
                return result
            all_errors.extend(sub_result.errors)

        result.add_error(f"No validator passed: {'; '.join(all_errors)}")
        return result

class NotValidator(Generic[T]):
    """Negate a validator (passes if inner validator fails)"""

    def __init__(self, validator: Validator[T], error_message: str | None = None):
        self.validator = validator
        self.error_message = error_message or "Validation should have failed"

    def validate(self, value: T) -> ValidationResult[T]:
        result = ValidationResult(value=value)
        sub_result = self.validator.validate(value)

        if sub_result.is_valid:
            result.add_error(self.error_message)

        return result

# ===== Builder =====

class ValidatorBuilder(Generic[T]):
    """Fluent builder for composing validators"""

    def __init__(self):
        self._validators: list[Validator[T]] = []

    def add(self, validator: Validator[T]) -> ValidatorBuilder[T]:
        """Add a validator"""
        self._validators.append(validator)
        return self

    def add_if(
        self,
        condition: bool,
        validator: Validator[T]
    ) -> ValidatorBuilder[T]:
        """Conditionally add a validator"""
        if condition:
            self._validators.append(validator)
        return self

    def build(self) -> Validator[T]:
        """Build AND-combined validator"""
        if len(self._validators) == 0:
            raise ValueError("No validators added")
        if len(self._validators) == 1:
            return self._validators[0]
        return AndValidator(self._validators)

    def build_or(self) -> Validator[T]:
        """Build OR-combined validator"""
        if len(self._validators) == 0:
            raise ValueError("No validators added")
        if len(self._validators) == 1:
            return self._validators[0]
        return OrValidator(self._validators)

def validator_for(type_hint: type[T]) -> ValidatorBuilder[T]:
    """Create a type-safe validator builder"""
    return ValidatorBuilder[T]()

# ===== List Validator =====

class ListValidator(Generic[T]):
    """Validate each element in a list"""

    def __init__(
        self,
        element_validator: Validator[T],
        min_length: int | None = None,
        max_length: int | None = None
    ):
        self.element_validator = element_validator
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: list[T]) -> ValidationResult[list[T]]:
        result = ValidationResult(value=value)

        # Check list length
        if self.min_length is not None and len(value) < self.min_length:
            result.add_error(f"List length {len(value)} < minimum {self.min_length}")
        if self.max_length is not None and len(value) > self.max_length:
            result.add_error(f"List length {len(value)} > maximum {self.max_length}")

        # Validate each element
        for i, item in enumerate(value):
            sub_result = self.element_validator.validate(item)
            for error in sub_result.errors:
                result.add_error(f"[{i}] {error}")
            for warning in sub_result.warnings:
                result.add_warning(f"[{i}] {warning}")

        return result

# ===== Demo =====

if __name__ == "__main__":
    print("=== Generic Validator Demo ===\n")

    # Example 1: Basic validators
    print("1. Basic Validators")
    print("-" * 40)

    not_empty = NotEmptyValidator()
    print(f"  NotEmpty(''): {not_empty.validate('')}")
    print(f"  NotEmpty('hello'): {not_empty.validate('hello')}")

    # Example 2: Path validator
    print("\n2. Path Validator")
    print("-" * 40)

    path_validator = PathExistsValidator(must_be_file=True)
    result = path_validator.validate(Path("/etc/hosts"))
    print(f"  /etc/hosts: valid={result.is_valid}")

    result = path_validator.validate(Path("/nonexistent"))
    print(f"  /nonexistent: valid={result.is_valid}, errors={result.errors}")

    # Example 3: Composed validators
    print("\n3. Composed Validators (AND)")
    print("-" * 40)

    username_validator = AndValidator[str]([
        NotEmptyValidator(),
        LengthValidator(min_length=3, max_length=20),
        PatternValidator(r"^[a-z][a-z0-9_]*$", "Must be lowercase alphanumeric"),
    ])

    test_usernames = ["", "ab", "valid_user", "Invalid", "a" * 25]
    for username in test_usernames:
        result = username_validator.validate(username)
        status = "PASS" if result.is_valid else "FAIL"
        print(f"  '{username}': {status}")
        if not result.is_valid:
            for error in result.errors:
                print(f"    - {error}")

    # Example 4: Builder pattern
    print("\n4. Builder Pattern")
    print("-" * 40)

    email_validator = (
        validator_for(str)
        .add(NotEmptyValidator())
        .add(PatternValidator(
            r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            "Invalid email format"
        ))
        .build()
    )

    test_emails = ["", "invalid", "test@example.com"]
    for email in test_emails:
        result = email_validator.validate(email)
        status = "PASS" if result.is_valid else "FAIL"
        print(f"  '{email}': {status}")

    # Example 5: List validator
    print("\n5. List Validator")
    print("-" * 40)

    tags_validator = ListValidator(
        element_validator=AndValidator[str]([
            NotEmptyValidator(),
            LengthValidator(max_length=20),
        ]),
        min_length=1,
        max_length=5
    )

    test_tags = [
        ["python", "typing"],
        [],
        ["valid", "", "also-valid"],
    ]

    for tags in test_tags:
        result = tags_validator.validate(tags)
        status = "PASS" if result.is_valid else "FAIL"
        print(f"  {tags}: {status}")
        if not result.is_valid:
            for error in result.errors:
                print(f"    - {error}")

    print("\n=== Demo Complete ===")
```

### 使用範例

#### 基本使用

```python
from pathlib import Path

# Create validators
not_empty = NotEmptyValidator()
path_exists = PathExistsValidator(must_be_file=True)

# Validate string
result = not_empty.validate("hello")
print(result.is_valid)  # True

result = not_empty.validate("")
print(result.is_valid)  # False
print(result.errors)    # ["Value cannot be empty"]

# Validate path
result = path_exists.validate(Path("/etc/hosts"))
print(result.is_valid)  # True (on Unix systems)

# Using ValidationResult in boolean context
if not_empty.validate("test"):
    print("Validation passed!")
```

#### 組合驗證

```python
# Username validator: non-empty, 3-20 chars, lowercase alphanumeric
username_validator = AndValidator[str]([
    NotEmptyValidator(),
    LengthValidator(min_length=3, max_length=20),
    PatternValidator(r"^[a-z][a-z0-9_]*$"),
])

# Test cases
result = username_validator.validate("valid_user")
print(result.is_valid)  # True

result = username_validator.validate("ab")
print(result.is_valid)  # False
print(result.errors)    # ["Length 2 < minimum 3"]

# OR validation: accept either email or username format
login_validator = OrValidator[str]([
    PatternValidator(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"),
    PatternValidator(r"^[a-z][a-z0-9_]{2,19}$"),
])

print(login_validator.validate("user@example.com").is_valid)  # True
print(login_validator.validate("valid_user").is_valid)        # True
print(login_validator.validate("X").is_valid)                  # False
```

#### 使用 Builder 模式

```python
# Fluent API for building validators
password_validator = (
    validator_for(str)
    .add(NotEmptyValidator())
    .add(LengthValidator(min_length=8, max_length=128))
    .add(PatternValidator(r".*[A-Z].*", "Must contain uppercase"))
    .add(PatternValidator(r".*[a-z].*", "Must contain lowercase"))
    .add(PatternValidator(r".*[0-9].*", "Must contain digit"))
    .build()
)

result = password_validator.validate("weakpass")
print(result.errors)
# ["Must contain uppercase", "Must contain digit"]

result = password_validator.validate("Strong1Password")
print(result.is_valid)  # True
```

#### 驗證列表元素

```python
# Validate a list of tags
tag_validator = NotEmptyValidator()
tags_validator = ListValidator(
    element_validator=tag_validator,
    min_length=1,
    max_length=10
)

result = tags_validator.validate(["python", "typing", "generic"])
print(result.is_valid)  # True

result = tags_validator.validate(["valid", "", "also-valid"])
print(result.is_valid)  # False
print(result.errors)    # ["[1] Value cannot be empty"]
```

## 設計權衡

| 面向 | 具體類型 | 泛型設計 |
|------|----------|----------|
| 重用性 | 低：每個類型需要獨立實作 | 高：一次實作，多處使用 |
| 型別推導 | 簡單：型別固定 | 需要技巧：需正確標註 TypeVar |
| 學習曲線 | 低：直覺易懂 | 中：需理解 Generic、Protocol |
| IDE 支援 | 完整：型別明確 | 需要正確標註才能獲得完整支援 |
| 執行效能 | 略佳：無泛型開銷 | 略差：有 Protocol 檢查開銷 |
| 錯誤訊息 | 清晰：直接指出問題 | 可能較模糊：泛型相關錯誤不易讀 |

### 何時選擇泛型設計？

**選擇泛型設計**當：

- 驗證邏輯會用於多種類型
- 需要組合多個驗證器
- 正在建立可重用的驗證函式庫
- 重視編譯時期的型別安全

**選擇具體類型**當：

- 只驗證單一特定類型
- 驗證邏輯非常簡單
- 團隊對泛型不熟悉
- 效能是關鍵考量

## 什麼時候該用這個技術？

**適合使用**：

- 需要驗證多種類型的函式庫
- 驗證邏輯需要組合重用
- 重視型別安全
- API 設計需要表達「這個驗證器接受 T 類型」

**不建議使用**：

- 只驗證單一類型
- 驗證邏輯很簡單（幾行 if-else 就能搞定）
- 團隊不熟悉泛型語法
- 程式碼不會被重用

## 練習

### 基礎練習

1. **實作 `RangeValidator[int]` 和 `LengthValidator[str]`**

   參考上面的 `RangeValidator` 實作，確保它可以正確驗證整數範圍。
   測試案例：

   ```python
   age_validator = RangeValidator(min_value=0, max_value=150)
   assert age_validator.validate(25).is_valid
   assert not age_validator.validate(-1).is_valid
   assert not age_validator.validate(200).is_valid
   ```

2. **實作 `EmailValidator`**

   建立一個 Email 驗證器，組合 `NotEmptyValidator` 和 `PatternValidator`：

   ```python
   email_validator = EmailValidator()
   assert email_validator.validate("user@example.com").is_valid
   assert not email_validator.validate("invalid").is_valid
   ```

### 進階練習

1. **實作 `ListValidator[T]` 驗證列表中的每個元素**

   建立一個泛型列表驗證器，可以：
   - 驗證列表長度
   - 對每個元素執行子驗證器
   - 收集所有錯誤，標註元素索引

   ```python
   int_list_validator = ListValidator(
       element_validator=RangeValidator(min_value=0),
       min_length=1
   )
   result = int_list_validator.validate([1, 2, -3, 4])
   # errors: ["[2] Value -3 < minimum 0"]
   ```

2. **實作 `ConditionalValidator[T]`**

   建立一個條件驗證器，只在條件成立時執行驗證：

   ```python
   # Only validate age if it's provided (not None)
   optional_age_validator = ConditionalValidator(
       condition=lambda x: x is not None,
       validator=RangeValidator(min_value=0, max_value=150)
   )
   ```

### 挑戰題

1. **實作 `SchemaValidator` 驗證字典結構**

   建立一個驗證器，可以驗證字典的結構和值：

   ```python
   user_schema = SchemaValidator({
       "name": NotEmptyValidator(),
       "age": RangeValidator(min_value=0, max_value=150),
       "email": EmailValidator(),
   }, required_keys=["name", "email"])

   result = user_schema.validate({
       "name": "Alice",
       "age": 30,
       "email": "alice@example.com"
   })
   assert result.is_valid

   result = user_schema.validate({
       "name": "",
       "age": -5,
   })
   # errors: ["name: Value cannot be empty", "age: Value -5 < minimum 0", "Missing required key: email"]
   ```

   提示：
   - 使用 `dict[str, Validator[Any]]` 作為 schema 類型
   - 處理可選欄位和必填欄位
   - 考慮巢狀 schema 的支援

## 延伸閱讀

- [Python typing.Generic](https://docs.python.org/3/library/typing.html#typing.Generic)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [PEP 544 - Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- [mypy Generics](https://mypy.readthedocs.io/en/stable/generics.html)

---

*上一章：[異常設計架構](../exception-hierarchy/)*
*返回：[模組 3.5：進階設計模式](../../)*
