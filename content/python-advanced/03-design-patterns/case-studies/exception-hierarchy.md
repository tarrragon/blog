---
title: "案例：異常設計架構"
date: 2026-01-21
description: "設計清晰的異常階層，並用 ExceptionGroup 處理多重錯誤"
weight: 3
---

# 案例：異常設計架構

本案例基於 `.claude/lib/hook_io.py` 的實際程式碼，展示如何設計清晰的異常階層，並用 ExceptionGroup 處理多重錯誤。

## 先備知識

- 入門系列 [5.1 異常處理策略](../../../python/05-error-testing/exception/)
- [3.5.2 異常設計架構](../../exception-design/)

## 問題背景

### 現有設計

`.claude/lib/hook_io.py` 使用簡單的錯誤處理方式：

```python
def read_hook_input() -> dict:
    """
    從 stdin 讀取 Hook 輸入

    Returns:
        dict: 解析後的 JSON 資料，解析失敗時返回空字典
    """
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}
    except Exception:
        return {}
```

這個設計有以下特點：

1. **捕獲所有異常**：使用 `except Exception` 確保不會崩潰
2. **靜默失敗**：錯誤時返回空字典，不報告錯誤原因
3. **無法區分錯誤類型**：JSON 解析錯誤和其他錯誤用同樣方式處理

### 這個設計的優點

- **簡單可靠**：Hook 不會因為輸入問題而崩潰
- **使用標準異常**：不需要定義額外類別
- **API 簡潔**：呼叫者不需要處理異常

### 這個設計的限制

當錯誤處理變複雜時，這個設計會遇到問題：

#### 問題 1：無法區分不同來源的錯誤

```python
def process_hook():
    input_data = read_hook_input()
    if not input_data:
        # 問題：不知道是 JSON 解析失敗還是 stdin 讀取失敗
        # 無法給出有意義的錯誤訊息
        return {"error": "unknown error"}
```

#### 問題 2：多個錯誤只能報告第一個

```python
def validate_hook_config(config: dict) -> None:
    """驗證 Hook 配置"""
    if "tool_name" not in config:
        raise ValueError("missing tool_name")  # 第一個錯誤後就停止
    if "tool_input" not in config:
        raise ValueError("missing tool_input")  # 永遠不會執行到
```

#### 問題 3：錯誤恢復邏輯難以實作

```python
def handle_hook_error(error: Exception) -> dict:
    """處理 Hook 錯誤"""
    # 問題：只能用 isinstance 檢查，很難擴展
    if isinstance(error, json.JSONDecodeError):
        return {"error": "invalid json"}
    elif isinstance(error, FileNotFoundError):
        return {"error": "file not found"}
    else:
        return {"error": str(error)}
```

## 進階解決方案

### 設計目標

1. **建立清晰的異常階層**：不同錯誤類型有不同的異常類別
2. **支援多重錯誤收集**：使用 ExceptionGroup 收集多個驗證錯誤
3. **提供豐富的錯誤資訊**：異常攜帶足夠的上下文資訊
4. **支援錯誤恢復策略**：可以根據錯誤類型決定恢復方式

### 實作步驟

#### 步驟 1：設計異常階層

設計異常階層時，要考慮錯誤的分類和繼承關係：

```python
"""
Hook 異常階層設計

Exception hierarchy:
    HookError (base)
    ├── HookConfigError (configuration issues)
    │   ├── ConfigNotFoundError
    │   ├── ConfigParseError
    │   └── ConfigValidationError
    ├── HookInputError (input processing)
    │   ├── InputReadError
    │   └── InputValidationError
    └── HookExecutionError (runtime issues)
        ├── ToolNotFoundError
        └── PermissionDeniedError
"""

class HookError(Exception):
    """
    Hook 異常基礎類別

    所有 Hook 相關的異常都繼承自這個類別，
    讓呼叫者可以用 `except HookError` 捕獲所有 Hook 錯誤。
    """

    def __init__(self, message: str, *, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}

    def __str__(self) -> str:
        if self.context:
            ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.args[0]} ({ctx})"
        return self.args[0]

# === Configuration Errors ===

class HookConfigError(HookError):
    """配置相關錯誤的基礎類別"""
    pass

class ConfigNotFoundError(HookConfigError):
    """配置檔案不存在"""

    def __init__(self, config_name: str, search_paths: list[str] | None = None):
        self.config_name = config_name
        self.search_paths = search_paths or []
        super().__init__(
            f"Config '{config_name}' not found",
            context={"config_name": config_name, "search_paths": self.search_paths}
        )

class ConfigParseError(HookConfigError):
    """配置檔案解析失敗"""

    def __init__(self, config_name: str, line: int | None = None, detail: str = ""):
        self.config_name = config_name
        self.line = line
        self.detail = detail
        msg = f"Failed to parse config '{config_name}'"
        if line:
            msg += f" at line {line}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, context={"config_name": config_name, "line": line})

class ConfigValidationError(HookConfigError):
    """配置內容驗證失敗"""

    def __init__(self, config_name: str, field: str, reason: str):
        self.config_name = config_name
        self.field = field
        self.reason = reason
        super().__init__(
            f"Invalid config '{config_name}': field '{field}' {reason}",
            context={"config_name": config_name, "field": field}
        )

# === Input Errors ===

class HookInputError(HookError):
    """輸入相關錯誤的基礎類別"""
    pass

class InputReadError(HookInputError):
    """讀取輸入失敗"""

    def __init__(self, source: str = "stdin", cause: Exception | None = None):
        self.source = source
        self.cause = cause
        super().__init__(
            f"Failed to read from {source}",
            context={"source": source}
        )
        if cause:
            self.__cause__ = cause

class InputValidationError(HookInputError):
    """輸入驗證失敗"""

    def __init__(self, field: str, expected: str, actual: str | None = None):
        self.field = field
        self.expected = expected
        self.actual = actual
        msg = f"Invalid input: field '{field}' {expected}"
        if actual:
            msg += f", got {actual!r}"
        super().__init__(msg, context={"field": field, "expected": expected})

# === Execution Errors ===

class HookExecutionError(HookError):
    """執行時錯誤的基礎類別"""
    pass

class ToolNotFoundError(HookExecutionError):
    """工具不存在"""

    def __init__(self, tool_name: str, available_tools: list[str] | None = None):
        self.tool_name = tool_name
        self.available_tools = available_tools or []
        super().__init__(
            f"Tool '{tool_name}' not found",
            context={"tool_name": tool_name, "available": self.available_tools}
        )

class PermissionDeniedError(HookExecutionError):
    """權限不足"""

    def __init__(self, action: str, resource: str, reason: str = ""):
        self.action = action
        self.resource = resource
        self.reason = reason
        msg = f"Permission denied: cannot {action} '{resource}'"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg, context={"action": action, "resource": resource})
```

#### 步驟 2：豐富的錯誤資訊

異常類別可以攜帶豐富的上下文資訊，幫助除錯和錯誤恢復：

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class ErrorContext:
    """
    錯誤上下文資訊

    收集錯誤發生時的環境資訊，
    幫助除錯和錯誤報告。
    """
    timestamp: datetime = field(default_factory=datetime.now)
    hook_name: str = ""
    tool_name: str = ""
    tool_input: dict = field(default_factory=dict)
    environment: dict = field(default_factory=dict)
    stack_info: str = ""

    def to_dict(self) -> dict[str, Any]:
        """轉換為字典，方便序列化"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "hook_name": self.hook_name,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "environment": self.environment,
        }

class RichHookError(HookError):
    """
    帶有豐富上下文的 Hook 異常

    提供詳細的錯誤資訊，包含：
    - 錯誤發生的時間
    - 相關的 Hook 和工具資訊
    - 環境變數
    - 建議的修復方式
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "",
        error_context: ErrorContext | None = None,
        suggestions: list[str] | None = None,
        recoverable: bool = False,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.error_context = error_context or ErrorContext()
        self.suggestions = suggestions or []
        self.recoverable = recoverable

    def format_message(self) -> str:
        """格式化完整錯誤訊息"""
        lines = [f"[{self.error_code}] {self.args[0]}"]

        if self.error_context.hook_name:
            lines.append(f"  Hook: {self.error_context.hook_name}")
        if self.error_context.tool_name:
            lines.append(f"  Tool: {self.error_context.tool_name}")

        if self.suggestions:
            lines.append("\nSuggestions:")
            for i, suggestion in enumerate(self.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")

        return "\n".join(lines)

    def to_response(self) -> dict[str, Any]:
        """轉換為 Hook 回應格式"""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": str(self.args[0]),
            "context": self.error_context.to_dict(),
            "suggestions": self.suggestions,
            "recoverable": self.recoverable,
        }

# Example: specific error with rich context
class HookValidationError(RichHookError):
    """
    Hook 驗證錯誤

    當 Hook 輸入驗證失敗時拋出，
    提供詳細的錯誤資訊和修復建議。
    """

    def __init__(
        self,
        field: str,
        reason: str,
        *,
        actual_value: Any = None,
        error_context: ErrorContext | None = None,
    ):
        self.field = field
        self.reason = reason
        self.actual_value = actual_value

        message = f"Validation failed for '{field}': {reason}"
        suggestions = self._generate_suggestions(field, reason, actual_value)

        super().__init__(
            message,
            error_code="HOOK_VALIDATION_ERROR",
            error_context=error_context,
            suggestions=suggestions,
            recoverable=True,
        )

    def _generate_suggestions(
        self,
        field: str,
        reason: str,
        actual_value: Any
    ) -> list[str]:
        """根據錯誤類型生成修復建議"""
        suggestions = []

        if "required" in reason.lower():
            suggestions.append(f"Add the required field '{field}' to your input")
        if "type" in reason.lower():
            suggestions.append(f"Check the type of '{field}' - expected type may differ")
        if actual_value is not None:
            suggestions.append(f"Current value: {actual_value!r}")

        return suggestions
```

#### 步驟 3：使用 ExceptionGroup（Python 3.11+）

Python 3.11 引入的 `ExceptionGroup` 可以同時報告多個錯誤：

```python
from typing import Callable

class ValidationCollector:
    """
    驗證錯誤收集器

    收集多個驗證錯誤，最後用 ExceptionGroup 一次報告。
    這樣可以讓使用者一次看到所有錯誤，而不是修完一個才看到下一個。
    """

    def __init__(self, context_name: str = "validation"):
        self.context_name = context_name
        self.errors: list[Exception] = []

    def add_error(self, error: Exception) -> None:
        """新增一個錯誤"""
        self.errors.append(error)

    def check(self, condition: bool, error: Exception) -> None:
        """
        檢查條件，失敗時收集錯誤

        Args:
            condition: 要檢查的條件
            error: 條件為 False 時要收集的錯誤
        """
        if not condition:
            self.errors.append(error)

    def has_errors(self) -> bool:
        """是否有錯誤"""
        return len(self.errors) > 0

    def raise_if_errors(self) -> None:
        """
        如果有錯誤，拋出 ExceptionGroup

        Raises:
            ExceptionGroup: 包含所有收集到的錯誤
        """
        if self.errors:
            raise ExceptionGroup(
                f"{self.context_name} failed with {len(self.errors)} error(s)",
                self.errors
            )

def validate_hook_input(data: dict) -> dict:
    """
    驗證 Hook 輸入，收集所有錯誤

    使用 ExceptionGroup 一次報告所有驗證錯誤，
    而不是只報告第一個錯誤。

    Args:
        data: 待驗證的輸入資料

    Returns:
        驗證後的資料

    Raises:
        ExceptionGroup: 包含所有驗證錯誤
    """
    collector = ValidationCollector("Hook input validation")

    # Check required fields
    collector.check(
        "tool_name" in data,
        InputValidationError("tool_name", "is required")
    )
    collector.check(
        "tool_input" in data,
        InputValidationError("tool_input", "is required")
    )

    # Check types (only if fields exist)
    if "tool_name" in data:
        collector.check(
            isinstance(data["tool_name"], str),
            InputValidationError(
                "tool_name",
                "must be a string",
                actual=type(data["tool_name"]).__name__
            )
        )

    if "tool_input" in data:
        collector.check(
            isinstance(data["tool_input"], dict),
            InputValidationError(
                "tool_input",
                "must be a dict",
                actual=type(data["tool_input"]).__name__
            )
        )

    # Check tool-specific validation
    if data.get("tool_name") == "Write":
        collector.check(
            "file_path" in data.get("tool_input", {}),
            InputValidationError("tool_input.file_path", "is required for Write tool")
        )
        collector.check(
            "content" in data.get("tool_input", {}),
            InputValidationError("tool_input.content", "is required for Write tool")
        )

    # Raise all errors at once
    collector.raise_if_errors()

    return data

# Using except* to handle ExceptionGroup (Python 3.11+)
def handle_validation_errors_demo():
    """示範如何用 except* 處理 ExceptionGroup"""
    try:
        validate_hook_input({
            "tool_name": 123,  # Wrong type
            # Missing tool_input
        })
    except* InputValidationError as eg:
        # Handle all InputValidationError instances
        print(f"Found {len(eg.exceptions)} validation errors:")
        for error in eg.exceptions:
            print(f"  - {error.field}: {error.expected}")
    except* HookError as eg:
        # Handle other HookError instances
        print(f"Found {len(eg.exceptions)} hook errors")
```

#### 步驟 4：錯誤恢復策略

設計可以根據錯誤類型決定恢復方式的機制：

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic

T = TypeVar("T")

class RecoveryStrategy(ABC, Generic[T]):
    """
    錯誤恢復策略抽象基礎類別

    定義錯誤恢復的介面，讓不同類型的錯誤
    可以有不同的恢復方式。
    """

    @abstractmethod
    def can_recover(self, error: Exception) -> bool:
        """判斷是否可以恢復此錯誤"""
        pass

    @abstractmethod
    def recover(self, error: Exception) -> T:
        """執行恢復邏輯，返回恢復後的結果"""
        pass

class DefaultValueRecovery(RecoveryStrategy[dict]):
    """
    預設值恢復策略

    當錯誤發生時，返回預設值。
    """

    def __init__(self, default: dict):
        self.default = default

    def can_recover(self, error: Exception) -> bool:
        return isinstance(error, (ConfigNotFoundError, InputReadError))

    def recover(self, error: Exception) -> dict:
        return self.default.copy()

class RetryRecovery(RecoveryStrategy[dict]):
    """
    重試恢復策略

    當錯誤是暫時性的，嘗試重試。
    """

    def __init__(
        self,
        operation: Callable[[], dict],
        max_retries: int = 3,
        recoverable_errors: tuple[type[Exception], ...] = (IOError,)
    ):
        self.operation = operation
        self.max_retries = max_retries
        self.recoverable_errors = recoverable_errors

    def can_recover(self, error: Exception) -> bool:
        return isinstance(error, self.recoverable_errors)

    def recover(self, error: Exception) -> dict:
        import time

        last_error = error
        for attempt in range(self.max_retries):
            try:
                time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                return self.operation()
            except self.recoverable_errors as e:
                last_error = e
                continue

        # All retries failed, re-raise the last error
        raise last_error

class ErrorRecoveryChain:
    """
    錯誤恢復鏈

    按順序嘗試多個恢復策略，
    直到找到可以處理的策略。
    """

    def __init__(self):
        self.strategies: list[RecoveryStrategy] = []

    def add_strategy(self, strategy: RecoveryStrategy) -> "ErrorRecoveryChain":
        """新增恢復策略"""
        self.strategies.append(strategy)
        return self

    def try_recover(self, error: Exception) -> tuple[bool, Any]:
        """
        嘗試恢復錯誤

        Args:
            error: 要恢復的錯誤

        Returns:
            (是否成功恢復, 恢復結果或 None)
        """
        for strategy in self.strategies:
            if strategy.can_recover(error):
                try:
                    result = strategy.recover(error)
                    return (True, result)
                except Exception:
                    continue
        return (False, None)

def read_hook_input_with_recovery() -> dict:
    """
    讀取 Hook 輸入，帶有錯誤恢復機制

    使用恢復鏈處理不同類型的錯誤。
    """
    import json
    import sys

    # Set up recovery chain
    recovery = ErrorRecoveryChain()
    recovery.add_strategy(DefaultValueRecovery({"tool_name": "", "tool_input": {}}))

    try:
        data = json.load(sys.stdin)
        return validate_hook_input(data)

    except json.JSONDecodeError as e:
        # JSON parsing error - try to recover
        error = InputReadError("stdin", cause=e)
        recovered, result = recovery.try_recover(error)
        if recovered:
            return result
        raise error from e

    except ExceptionGroup as eg:
        # Multiple validation errors
        # Check if all errors are recoverable
        all_recoverable = all(
            isinstance(e, (InputValidationError,))
            for e in eg.exceptions
        )
        if all_recoverable:
            return {"tool_name": "", "tool_input": {}, "validation_errors": len(eg.exceptions)}
        raise

    except Exception as e:
        # Unknown error
        error = InputReadError("stdin", cause=e)
        recovered, result = recovery.try_recover(error)
        if recovered:
            return result
        raise error from e
```

### 完整程式碼

```python
#!/usr/bin/env python3
"""
Hook Exception Hierarchy - Complete Example

Demonstrates how to design a clear exception hierarchy
and use ExceptionGroup for multiple error handling.
"""

from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")

# ===== Exception Hierarchy =====

class HookError(Exception):
    """Base class for all Hook-related exceptions."""

    def __init__(self, message: str, *, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}

    def __str__(self) -> str:
        if self.context:
            ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.args[0]} ({ctx})"
        return self.args[0]

class HookConfigError(HookError):
    """Configuration-related errors."""
    pass

class ConfigNotFoundError(HookConfigError):
    """Config file not found."""

    def __init__(self, config_name: str, search_paths: list[str] | None = None):
        self.config_name = config_name
        self.search_paths = search_paths or []
        super().__init__(
            f"Config '{config_name}' not found",
            context={"config_name": config_name, "search_paths": self.search_paths}
        )

class ConfigParseError(HookConfigError):
    """Failed to parse config file."""

    def __init__(self, config_name: str, line: int | None = None, detail: str = ""):
        self.config_name = config_name
        self.line = line
        self.detail = detail
        msg = f"Failed to parse config '{config_name}'"
        if line:
            msg += f" at line {line}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, context={"config_name": config_name, "line": line})

class HookInputError(HookError):
    """Input-related errors."""
    pass

class InputReadError(HookInputError):
    """Failed to read input."""

    def __init__(self, source: str = "stdin", cause: Exception | None = None):
        self.source = source
        self.cause = cause
        super().__init__(f"Failed to read from {source}", context={"source": source})
        if cause:
            self.__cause__ = cause

class InputValidationError(HookInputError):
    """Input validation failed."""

    def __init__(self, field: str, expected: str, actual: str | None = None):
        self.field = field
        self.expected = expected
        self.actual = actual
        msg = f"Invalid input: field '{field}' {expected}"
        if actual:
            msg += f", got {actual!r}"
        super().__init__(msg, context={"field": field, "expected": expected})

class HookExecutionError(HookError):
    """Execution-related errors."""
    pass

class ToolNotFoundError(HookExecutionError):
    """Tool not found."""

    def __init__(self, tool_name: str, available_tools: list[str] | None = None):
        self.tool_name = tool_name
        self.available_tools = available_tools or []
        super().__init__(
            f"Tool '{tool_name}' not found",
            context={"tool_name": tool_name, "available": self.available_tools}
        )

class PermissionDeniedError(HookExecutionError):
    """Permission denied."""

    def __init__(self, action: str, resource: str, reason: str = ""):
        self.action = action
        self.resource = resource
        self.reason = reason
        msg = f"Permission denied: cannot {action} '{resource}'"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg, context={"action": action, "resource": resource})

# ===== Error Context =====

@dataclass
class ErrorContext:
    """Rich context information for errors."""

    timestamp: datetime = field(default_factory=datetime.now)
    hook_name: str = ""
    tool_name: str = ""
    tool_input: dict = field(default_factory=dict)
    environment: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "hook_name": self.hook_name,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "environment": self.environment,
        }

# ===== Validation Collector =====

class ValidationCollector:
    """Collects validation errors and raises ExceptionGroup."""

    def __init__(self, context_name: str = "validation"):
        self.context_name = context_name
        self.errors: list[Exception] = []

    def add_error(self, error: Exception) -> None:
        self.errors.append(error)

    def check(self, condition: bool, error: Exception) -> None:
        if not condition:
            self.errors.append(error)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def raise_if_errors(self) -> None:
        if self.errors:
            raise ExceptionGroup(
                f"{self.context_name} failed with {len(self.errors)} error(s)",
                self.errors
            )

# ===== Recovery Strategies =====

class RecoveryStrategy(ABC, Generic[T]):
    """Abstract base class for error recovery strategies."""

    @abstractmethod
    def can_recover(self, error: Exception) -> bool:
        pass

    @abstractmethod
    def recover(self, error: Exception) -> T:
        pass

class DefaultValueRecovery(RecoveryStrategy[dict]):
    """Returns a default value when error occurs."""

    def __init__(self, default: dict):
        self.default = default

    def can_recover(self, error: Exception) -> bool:
        return isinstance(error, (ConfigNotFoundError, InputReadError))

    def recover(self, error: Exception) -> dict:
        return self.default.copy()

class ErrorRecoveryChain:
    """Chain of recovery strategies."""

    def __init__(self):
        self.strategies: list[RecoveryStrategy] = []

    def add_strategy(self, strategy: RecoveryStrategy) -> "ErrorRecoveryChain":
        self.strategies.append(strategy)
        return self

    def try_recover(self, error: Exception) -> tuple[bool, Any]:
        for strategy in self.strategies:
            if strategy.can_recover(error):
                try:
                    result = strategy.recover(error)
                    return (True, result)
                except Exception:
                    continue
        return (False, None)

# ===== Main Functions =====

def validate_hook_input(data: dict) -> dict:
    """
    Validate hook input, collecting all errors.

    Uses ExceptionGroup to report all validation errors at once.
    """
    collector = ValidationCollector("Hook input validation")

    # Required fields
    collector.check(
        "tool_name" in data,
        InputValidationError("tool_name", "is required")
    )
    collector.check(
        "tool_input" in data,
        InputValidationError("tool_input", "is required")
    )

    # Type checks
    if "tool_name" in data:
        collector.check(
            isinstance(data["tool_name"], str),
            InputValidationError(
                "tool_name",
                "must be a string",
                actual=type(data["tool_name"]).__name__
            )
        )

    if "tool_input" in data:
        collector.check(
            isinstance(data["tool_input"], dict),
            InputValidationError(
                "tool_input",
                "must be a dict",
                actual=type(data["tool_input"]).__name__
            )
        )

    collector.raise_if_errors()
    return data

def read_hook_input_safe() -> dict:
    """
    Read hook input with error recovery.

    Enhanced version of the original read_hook_input()
    with proper exception handling.
    """
    recovery = ErrorRecoveryChain()
    recovery.add_strategy(DefaultValueRecovery({"tool_name": "", "tool_input": {}}))

    try:
        data = json.load(sys.stdin)
        return validate_hook_input(data)

    except json.JSONDecodeError as e:
        error = InputReadError("stdin", cause=e)
        recovered, result = recovery.try_recover(error)
        if recovered:
            return result
        raise error from e

    except ExceptionGroup:
        # Re-raise validation errors as-is
        raise

    except Exception as e:
        error = InputReadError("stdin", cause=e)
        recovered, result = recovery.try_recover(error)
        if recovered:
            return result
        raise error from e

def create_error_response(error: HookError) -> dict:
    """Create a standardized error response."""
    return {
        "decision": "deny",
        "reason": str(error),
        "error": {
            "type": type(error).__name__,
            "message": str(error.args[0]),
            "context": error.context,
        }
    }

# ===== Demo =====

if __name__ == "__main__":
    print("=== Exception Hierarchy Demo ===\n")

    # Demo 1: Basic exception
    print("1. Basic exception:")
    try:
        raise ConfigNotFoundError("agents", ["/path/1", "/path/2"])
    except HookConfigError as e:
        print(f"   Caught: {e}")
        print(f"   Context: {e.context}")

    # Demo 2: Exception chaining
    print("\n2. Exception chaining:")
    try:
        try:
            raise json.JSONDecodeError("Unexpected EOF", "", 0)
        except json.JSONDecodeError as e:
            raise InputReadError("stdin", cause=e) from e
    except InputReadError as e:
        print(f"   Caught: {e}")
        print(f"   Caused by: {e.__cause__}")

    # Demo 3: ExceptionGroup
    print("\n3. ExceptionGroup (multiple errors):")
    try:
        validate_hook_input({"tool_name": 123})  # Wrong type, missing tool_input
    except ExceptionGroup as eg:
        print(f"   Caught ExceptionGroup: {eg}")
        for i, err in enumerate(eg.exceptions, 1):
            print(f"   Error {i}: {err}")

    # Demo 4: except* syntax (Python 3.11+)
    print("\n4. Using except* to handle specific error types:")
    try:
        validate_hook_input({})  # Missing both fields
    except* InputValidationError as eg:
        print(f"   Caught {len(eg.exceptions)} InputValidationError(s)")
        for err in eg.exceptions:
            print(f"   - {err.field}: {err.expected}")

    # Demo 5: Error recovery
    print("\n5. Error recovery:")
    recovery = ErrorRecoveryChain()
    recovery.add_strategy(DefaultValueRecovery({"default": True}))

    error = ConfigNotFoundError("missing_config")
    recovered, result = recovery.try_recover(error)
    print(f"   Recovered: {recovered}, Result: {result}")

    print("\n=== Demo Complete ===")
```

### 使用範例

#### 基本使用

```python
from hook_exceptions import (
    HookError,
    ConfigNotFoundError,
    InputValidationError,
    create_error_response,
)

def process_hook():
    """處理 Hook 請求"""
    try:
        # Load configuration
        config = load_config("agents")

        # Validate input
        data = validate_hook_input(read_input())

        # Process...
        return {"decision": "allow"}

    except ConfigNotFoundError as e:
        # Specific handling for missing config
        print(f"Warning: {e}, using defaults")
        return {"decision": "allow", "warning": str(e)}

    except InputValidationError as e:
        # Input validation error
        return create_error_response(e)

    except HookError as e:
        # Catch-all for other hook errors
        return create_error_response(e)
```

#### 多重錯誤處理

```python
def validate_batch_inputs(inputs: list[dict]) -> list[dict]:
    """
    驗證多個輸入，收集所有錯誤

    即使某些輸入失敗，仍然處理其他輸入。
    """
    results = []
    all_errors = []

    for i, data in enumerate(inputs):
        try:
            validated = validate_hook_input(data)
            results.append({"index": i, "data": validated, "valid": True})
        except ExceptionGroup as eg:
            # Collect errors from this input
            all_errors.extend(eg.exceptions)
            results.append({
                "index": i,
                "errors": [str(e) for e in eg.exceptions],
                "valid": False
            })
        except HookError as e:
            all_errors.append(e)
            results.append({"index": i, "error": str(e), "valid": False})

    # Report summary
    if all_errors:
        print(f"Validation completed with {len(all_errors)} total errors")

    return results

# Using except* to handle different error types differently
def handle_mixed_errors():
    """示範用 except* 分別處理不同類型的錯誤"""
    try:
        # This might raise ExceptionGroup with mixed errors
        process_complex_operation()

    except* InputValidationError as eg:
        # Handle validation errors - maybe log and continue
        for err in eg.exceptions:
            log_validation_error(err)

    except* PermissionDeniedError as eg:
        # Handle permission errors - need to notify admin
        for err in eg.exceptions:
            notify_admin(err)

    except* HookExecutionError as eg:
        # Handle execution errors - maybe retry
        for err in eg.exceptions:
            schedule_retry(err)
```

#### 異常鏈（Exception Chaining）

```python
def load_config_with_chain(name: str) -> dict:
    """
    載入配置，保留原始錯誤資訊

    使用 `raise ... from ...` 保留異常鏈，
    讓除錯時可以看到完整的錯誤來源。
    """
    import yaml

    config_path = f"/config/{name}.yaml"

    try:
        with open(config_path) as f:
            return yaml.safe_load(f)

    except FileNotFoundError as e:
        # Wrap in domain-specific exception, preserve original
        raise ConfigNotFoundError(name, [config_path]) from e

    except yaml.YAMLError as e:
        # Extract line number if available
        line = getattr(e, "problem_mark", None)
        line_num = line.line if line else None
        raise ConfigParseError(name, line=line_num, detail=str(e)) from e

    except PermissionError as e:
        # Convert to domain exception
        raise PermissionDeniedError("read", config_path, str(e)) from e

# When catching, you can access the full chain
def debug_config_error():
    try:
        config = load_config_with_chain("agents")
    except HookConfigError as e:
        print(f"Error: {e}")
        print(f"Original cause: {e.__cause__}")

        # Print full traceback including cause
        import traceback
        traceback.print_exception(type(e), e, e.__traceback__)
```

## 設計權衡

| 面向 | 標準異常 | 自定義階層 | ExceptionGroup |
|------|----------|-----------|----------------|
| 學習成本 | 低 | 中 | 中高 |
| 錯誤辨識 | 困難 | 清晰 | 清晰 |
| 錯誤資訊 | 有限 | 豐富 | 豐富 |
| 多重錯誤 | 只報一個 | 只報一個 | 全部報告 |
| 恢復策略 | 難實作 | 易實作 | 可分類處理 |
| Python 版本 | 所有版本 | 所有版本 | 3.11+ |
| 程式碼量 | 最少 | 中等 | 較多 |

### 何時使用哪種方案？

#### 使用標準異常（如 `hook_io.py` 的做法）

- 簡單的腳本或工具
- 錯誤處理很簡單
- 不需要區分錯誤類型

#### 使用自定義階層

- 函式庫或框架
- 需要區分不同錯誤類型
- 需要提供錯誤恢復建議

#### 使用 ExceptionGroup

- 批次處理需要收集所有錯誤
- 驗證邏輯有多個檢查點
- 需要讓使用者一次看到所有問題

## 什麼時候該用這個技術？

✅ **適合使用**：

- 需要區分不同錯誤類型的函式庫
- 批次處理需要收集所有錯誤
- 需要提供錯誤恢復建議
- 需要保留完整的錯誤來源（異常鏈）
- Python 3.11+ 環境

❌ **不建議使用**：

- 簡單的腳本
- 錯誤類型很少（< 3 種）
- 不需要精細的錯誤處理
- 需要支援舊版 Python（< 3.11）使用 ExceptionGroup

## 練習

### 基礎練習

1. **設計異常階層**：為一個配置載入模組設計異常階層，包含：
   - 檔案不存在
   - 格式錯誤
   - 欄位缺失
   - 型別錯誤

提示：先畫出階層圖，再實作類別。

### 進階練習

1. **實作 ExceptionGroup 驗證器**：寫一個表單驗證器，可以：
   - 收集所有欄位的驗證錯誤
   - 用 ExceptionGroup 一次報告
   - 支援 `except*` 分類處理

```python
# 目標 API
def validate_form(data: dict) -> dict:
    """驗證表單，收集所有錯誤"""
    collector = ValidationCollector("form")

    collector.check(
        len(data.get("username", "")) >= 3,
        FieldError("username", "must be at least 3 characters")
    )
    collector.check(
        "@" in data.get("email", ""),
        FieldError("email", "must contain @")
    )

    collector.raise_if_errors()
    return data
```

### 挑戰題

1. **實作帶有自動修復建議的異常**：設計一個異常系統，可以：
   - 根據錯誤類型自動生成修復建議
   - 支援結構化的錯誤報告（JSON 格式）
   - 提供「可能的修復」和「參考文件」連結

```python
# 目標 API
try:
    validate_config(config)
except ConfigError as e:
    print(e.format_message())
    # Output:
    # [CONFIG_001] Invalid config 'agents.yaml'
    #   Field: known_agents
    #   Error: expected list, got string
    #
    # Suggestions:
    #   1. Change 'known_agents: "basil"' to 'known_agents: ["basil"]'
    #   2. See: https://docs.example.com/config#known_agents
```

## 延伸閱讀

- [PEP 654 - Exception Groups and except*](https://peps.python.org/pep-0654/)
- [PEP 3134 - Exception Chaining](https://peps.python.org/pep-3134/)
- [Python 異常最佳實踐](https://docs.python.org/3/tutorial/errors.html)
- [Real Python - Exception Groups](https://realpython.com/python311-exception-groups/)

---

*上一章：[插件架構設計](../plugin-architecture/)*
*下一章：[泛型驗證器](../generic-validator/)*
