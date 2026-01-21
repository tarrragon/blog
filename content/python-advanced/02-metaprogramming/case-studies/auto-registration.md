---
title: "案例：自動註冊機制"
date: 2026-01-21
description: "用 Metaclass 實現檢查器的自動註冊，消除手動維護註冊表的負擔"
weight: 2
---

# 案例：自動註冊機制

本案例基於 `.claude/lib/hook_validator.py` 的實際程式碼，展示如何用 Metaclass 實現檢查器的自動註冊。

## 先備知識

- [2.1 宣告式驗證](../declarative-validation/)
- [2.2 Metaclass 設計與應用](../../metaclasses/)

## 問題背景

### 現有設計

`hook_validator.py` 的 `HookValidator` 類別包含多個 `check_*` 方法，需要在 `validate_hook()` 中手動呼叫：

```python
class HookValidator:
    """Hook 合規性驗證器"""

    def validate_hook(self, hook_path: str) -> ValidationResult:
        """驗證單個 Hook 檔案"""
        # ... 前置處理 ...

        # 執行各項檢查 - 手動呼叫每個 check 方法
        issues = []
        issues.extend(self.check_naming_convention(hook_path))
        issues.extend(self.check_lib_imports(content, hook_path))
        issues.extend(self.check_output_format(content))
        issues.extend(self.check_test_exists(hook_path))

        return ValidationResult(hook_path=str(hook_path), issues=issues)

    def check_naming_convention(self, hook_path: Path) -> List[ValidationIssue]:
        """檢查命名規範"""
        # ... 實作 ...

    def check_lib_imports(self, content: str, hook_path: Path) -> List[ValidationIssue]:
        """檢查共用模組導入"""
        # ... 實作 ...

    def check_output_format(self, content: str) -> List[ValidationIssue]:
        """檢查 Hook 輸出格式"""
        # ... 實作 ...

    def check_test_exists(self, hook_path: Path) -> List[ValidationIssue]:
        """檢查對應的測試檔案是否存在"""
        # ... 實作 ...
```

### 這個設計的優點

- **明確的執行順序**：可以精確控制檢查項的執行順序
- **容易理解呼叫流程**：閱讀 `validate_hook()` 就知道會執行哪些檢查
- **簡單直覺**：不需要學習額外的抽象概念

### 這個設計的限制

新增檢查項時：

1. **需要修改兩處程式碼**：新增 `check_*` 方法 + 修改 `validate_hook()` 呼叫
2. **容易忘記註冊**：新增方法後忘記在 `validate_hook()` 中呼叫
3. **無法動態控制**：無法在執行時期啟用/停用特定檢查項
4. **難以擴展**：子類別新增檢查項也需要覆寫 `validate_hook()`

## 進階解決方案

### 設計目標

1. 定義檢查方法時**自動註冊**到執行清單
2. 支援**優先順序控制**
3. 支援**動態啟用/停用**特定檢查項
4. 子類別的檢查項**自動繼承**

### 實作步驟

#### 步驟 1：用裝飾器標記檢查方法

首先，我們需要一個方式來標記哪些方法是「檢查器」。裝飾器是最自然的選擇：

```python
from functools import wraps
from typing import Callable, Optional

def check(
    priority: int = 100,
    enabled: bool = True,
    description: str = ""
) -> Callable:
    """
    Decorator to mark a method as a checker.

    Args:
        priority: Execution order (lower runs first)
        enabled: Whether this check is enabled by default
        description: Human-readable description

    Example:
        @check(priority=10, description="Validate filename format")
        def check_naming(self, hook_path):
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Store metadata on the function object
        func._is_checker = True
        func._checker_priority = priority
        func._checker_enabled = enabled
        func._checker_description = description or func.__doc__ or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Copy metadata to wrapper
        wrapper._is_checker = True
        wrapper._checker_priority = priority
        wrapper._checker_enabled = enabled
        wrapper._checker_description = description or func.__doc__ or func.__name__

        return wrapper
    return decorator
```

使用方式：

```python
class Validator:
    @check(priority=10, description="Check filename format")
    def check_naming_convention(self, hook_path):
        """檢查命名規範"""
        ...

    @check(priority=20, description="Check library imports")
    def check_lib_imports(self, content, hook_path):
        """檢查共用模組導入"""
        ...
```

#### 步驟 2：用 Metaclass 收集標記的方法

接下來，用 Metaclass 在類別建立時自動收集所有被 `@check` 標記的方法：

```python
class CheckerMeta(type):
    """
    Metaclass that automatically collects methods marked with @check.

    When a class is created, this metaclass:
    1. Scans all methods for the _is_checker attribute
    2. Collects them into a _checkers registry
    3. Sorts by priority for execution order
    """

    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        # Create the class first
        cls = super().__new__(mcs, name, bases, namespace)

        # Collect checkers from parent classes
        inherited_checkers = {}
        for base in bases:
            if hasattr(base, '_checkers'):
                inherited_checkers.update(base._checkers)

        # Collect checkers from current class
        current_checkers = {}
        for attr_name, attr_value in namespace.items():
            if callable(attr_value) and getattr(attr_value, '_is_checker', False):
                current_checkers[attr_name] = {
                    'method': attr_name,
                    'priority': attr_value._checker_priority,
                    'enabled': attr_value._checker_enabled,
                    'description': attr_value._checker_description,
                }

        # Merge: current class can override parent checkers
        all_checkers = {**inherited_checkers, **current_checkers}

        # Store as class attribute
        cls._checkers = all_checkers

        return cls
```

#### 步驟 3：實作優先順序

在 Metaclass 中已經收集了優先順序資訊，現在需要一個方法按順序執行：

```python
class CheckerBase(metaclass=CheckerMeta):
    """
    Base class for validators with auto-registration.

    Provides run_all_checks() to execute registered checkers.
    """

    def get_sorted_checkers(self) -> list:
        """
        Get all enabled checkers sorted by priority.

        Returns:
            List of (method_name, checker_info) tuples
        """
        checkers = [
            (name, info)
            for name, info in self._checkers.items()
            if info['enabled']
        ]
        # Sort by priority (lower number = higher priority)
        return sorted(checkers, key=lambda x: x[1]['priority'])

    def run_all_checks(self, *args, **kwargs) -> list:
        """
        Run all enabled checkers in priority order.

        Args:
            *args, **kwargs: Arguments passed to each checker

        Returns:
            Combined list of issues from all checkers
        """
        all_issues = []

        for method_name, info in self.get_sorted_checkers():
            method = getattr(self, method_name)
            try:
                issues = method(*args, **kwargs)
                if issues:
                    all_issues.extend(issues)
            except Exception as e:
                # Optionally handle checker errors
                all_issues.append({
                    'level': 'error',
                    'message': f"Checker {method_name} failed: {e}"
                })

        return all_issues
```

#### 步驟 4：實作啟用/停用機制

允許在執行時期動態控制檢查項：

```python
class CheckerBase(metaclass=CheckerMeta):
    """
    Base class for validators with auto-registration.
    """

    def __init__(self):
        # Instance-level override for checker states
        self._checker_overrides = {}

    def enable_checker(self, checker_name: str) -> None:
        """
        Enable a specific checker for this instance.

        Args:
            checker_name: Name of the checker method
        """
        if checker_name not in self._checkers:
            raise ValueError(f"Unknown checker: {checker_name}")
        self._checker_overrides[checker_name] = True

    def disable_checker(self, checker_name: str) -> None:
        """
        Disable a specific checker for this instance.

        Args:
            checker_name: Name of the checker method
        """
        if checker_name not in self._checkers:
            raise ValueError(f"Unknown checker: {checker_name}")
        self._checker_overrides[checker_name] = False

    def is_checker_enabled(self, checker_name: str) -> bool:
        """
        Check if a specific checker is enabled.

        Instance overrides take precedence over class defaults.
        """
        if checker_name in self._checker_overrides:
            return self._checker_overrides[checker_name]
        return self._checkers.get(checker_name, {}).get('enabled', False)

    def get_sorted_checkers(self) -> list:
        """Get all enabled checkers sorted by priority."""
        checkers = [
            (name, info)
            for name, info in self._checkers.items()
            if self.is_checker_enabled(name)
        ]
        return sorted(checkers, key=lambda x: x[1]['priority'])

    def list_checkers(self) -> list:
        """
        List all available checkers with their status.

        Returns:
            List of dicts with checker information
        """
        result = []
        for name, info in sorted(
            self._checkers.items(),
            key=lambda x: x[1]['priority']
        ):
            result.append({
                'name': name,
                'priority': info['priority'],
                'enabled': self.is_checker_enabled(name),
                'description': info['description'],
            })
        return result
```

### 完整程式碼

```python
#!/usr/bin/env python3
"""
Auto-registration pattern using Metaclass.

This module demonstrates how to automatically register checker methods
using a combination of decorators and metaclasses.
"""

from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Callable, List, Optional, Any
import re

# ===== Data Classes =====

@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    level: str  # "error" | "warning" | "info"
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    """Validation result for a single target."""
    target: str
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if no errors found."""
        return not any(issue.level == "error" for issue in self.issues)

# ===== Decorator =====

def check(
    priority: int = 100,
    enabled: bool = True,
    description: str = ""
) -> Callable:
    """
    Decorator to mark a method as a checker.

    Args:
        priority: Execution order (lower runs first)
        enabled: Whether this check is enabled by default
        description: Human-readable description
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Store metadata
        wrapper._is_checker = True
        wrapper._checker_priority = priority
        wrapper._checker_enabled = enabled
        wrapper._checker_description = description or func.__doc__ or func.__name__

        return wrapper
    return decorator

# ===== Metaclass =====

class CheckerMeta(type):
    """
    Metaclass that automatically collects @check decorated methods.
    """

    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        cls = super().__new__(mcs, name, bases, namespace)

        # Inherit checkers from parent classes
        inherited_checkers = {}
        for base in bases:
            if hasattr(base, '_checkers'):
                inherited_checkers.update(base._checkers)

        # Collect checkers from current class
        current_checkers = {}
        for attr_name, attr_value in namespace.items():
            if callable(attr_value) and getattr(attr_value, '_is_checker', False):
                current_checkers[attr_name] = {
                    'method': attr_name,
                    'priority': attr_value._checker_priority,
                    'enabled': attr_value._checker_enabled,
                    'description': attr_value._checker_description,
                }

        # Merge checkers
        cls._checkers = {**inherited_checkers, **current_checkers}

        return cls

# ===== Base Class =====

class CheckerBase(metaclass=CheckerMeta):
    """
    Base class providing auto-registration functionality.
    """

    def __init__(self):
        self._checker_overrides = {}

    def enable_checker(self, name: str) -> None:
        """Enable a checker for this instance."""
        if name not in self._checkers:
            raise ValueError(f"Unknown checker: {name}")
        self._checker_overrides[name] = True

    def disable_checker(self, name: str) -> None:
        """Disable a checker for this instance."""
        if name not in self._checkers:
            raise ValueError(f"Unknown checker: {name}")
        self._checker_overrides[name] = False

    def is_checker_enabled(self, name: str) -> bool:
        """Check if a checker is enabled."""
        if name in self._checker_overrides:
            return self._checker_overrides[name]
        return self._checkers.get(name, {}).get('enabled', False)

    def get_sorted_checkers(self) -> list:
        """Get enabled checkers sorted by priority."""
        return sorted(
            [(n, i) for n, i in self._checkers.items() if self.is_checker_enabled(n)],
            key=lambda x: x[1]['priority']
        )

    def list_checkers(self) -> list:
        """List all checkers with their status."""
        return [
            {
                'name': name,
                'priority': info['priority'],
                'enabled': self.is_checker_enabled(name),
                'description': info['description'],
            }
            for name, info in sorted(
                self._checkers.items(),
                key=lambda x: x[1]['priority']
            )
        ]

# ===== Implementation Example =====

class HookValidator(CheckerBase):
    """
    Hook validator with auto-registered checkers.

    Checkers are automatically discovered and executed in priority order.
    """

    # Pattern constants
    VALID_NAME_PATTERN = r"^[a-z0-9]([a-z0-9\-_]*[a-z0-9])?\.py$"
    HOOK_IO_PATTERNS = [
        r"from\s+hook_io\s+import",
        r"from\s+lib\.hook_io\s+import",
    ]
    BAD_OUTPUT_PATTERNS = [
        r'print\s*\(\s*json\.dumps\s*\(',
    ]

    def __init__(self, project_root: Optional[str] = None):
        super().__init__()
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def validate(self, hook_path: str) -> ValidationResult:
        """
        Validate a hook file by running all enabled checkers.

        Args:
            hook_path: Path to the hook file

        Returns:
            ValidationResult with all issues found
        """
        path = Path(hook_path)
        if not path.is_absolute():
            path = self.project_root / path

        # Read file content
        try:
            content = path.read_text(encoding='utf-8')
        except Exception as e:
            return ValidationResult(
                target=str(path),
                issues=[ValidationIssue(
                    level="error",
                    message=f"Cannot read file: {e}"
                )]
            )

        # Prepare context for checkers
        context = {
            'path': path,
            'content': content,
            'filename': path.name,
        }

        # Run all enabled checkers
        all_issues = []
        for method_name, _ in self.get_sorted_checkers():
            method = getattr(self, method_name)
            try:
                issues = method(context)
                if issues:
                    all_issues.extend(issues)
            except Exception as e:
                all_issues.append(ValidationIssue(
                    level="error",
                    message=f"Checker '{method_name}' crashed: {e}"
                ))

        return ValidationResult(target=str(path), issues=all_issues)

    @check(priority=10, description="Check filename format")
    def check_naming_convention(self, ctx: dict) -> List[ValidationIssue]:
        """Validate hook filename follows naming convention."""
        issues = []
        filename = ctx['filename']

        if not re.match(self.VALID_NAME_PATTERN, filename):
            issues.append(ValidationIssue(
                level="warning",
                message=f"Filename '{filename}' doesn't follow naming convention",
                suggestion="Use snake_case or kebab-case, e.g., check_format.py"
            ))

        return issues

    @check(priority=20, description="Check hook_io import")
    def check_lib_imports(self, ctx: dict) -> List[ValidationIssue]:
        """Check if hook_io module is properly imported."""
        issues = []
        content = ctx['content']

        has_import = any(
            re.search(pattern, content)
            for pattern in self.HOOK_IO_PATTERNS
        )

        if not has_import:
            issues.append(ValidationIssue(
                level="warning",
                message="hook_io module not imported",
                suggestion="Add: from hook_io import read_hook_input, write_hook_output"
            ))

        return issues

    @check(priority=30, description="Check output format")
    def check_output_format(self, ctx: dict) -> List[ValidationIssue]:
        """Check if proper output functions are used."""
        issues = []
        content = ctx['content']

        for pattern in self.BAD_OUTPUT_PATTERNS:
            if re.search(pattern, content):
                issues.append(ValidationIssue(
                    level="warning",
                    message="Using print(json.dumps(...)) instead of write_hook_output()",
                    suggestion="Replace with: write_hook_output(output_dict)"
                ))
                break

        return issues

    @check(priority=40, enabled=False, description="Check test file exists")
    def check_test_exists(self, ctx: dict) -> List[ValidationIssue]:
        """Check if corresponding test file exists."""
        issues = []
        hook_name = ctx['path'].stem
        test_name = f"test_{hook_name.replace('-', '_')}.py"

        test_path = self.project_root / ".claude" / "lib" / "tests" / test_name
        if not test_path.exists():
            issues.append(ValidationIssue(
                level="info",
                message=f"No test file found: {test_name}",
                suggestion=f"Create test at: {test_path}"
            ))

        return issues

# ===== Extended Example: Subclass =====

class StrictHookValidator(HookValidator):
    """
    Extended validator with additional checks.

    Inherits all checks from HookValidator and adds more.
    """

    @check(priority=15, description="Check shebang line")
    def check_shebang(self, ctx: dict) -> List[ValidationIssue]:
        """Check if file starts with proper shebang."""
        issues = []
        content = ctx['content']

        if not content.startswith('#!/usr/bin/env python'):
            issues.append(ValidationIssue(
                level="info",
                message="Missing shebang line",
                suggestion="Add: #!/usr/bin/env python3"
            ))

        return issues

    @check(priority=25, description="Check docstring exists")
    def check_docstring(self, ctx: dict) -> List[ValidationIssue]:
        """Check if module has a docstring."""
        issues = []
        content = ctx['content']

        # Simple check: look for triple quotes near the start
        lines = content.split('\n')[:10]  # First 10 lines
        has_docstring = any('"""' in line or "'''" in line for line in lines)

        if not has_docstring:
            issues.append(ValidationIssue(
                level="info",
                message="Module docstring not found",
                suggestion="Add a docstring at the top of the file"
            ))

        return issues

# ===== Demo =====

if __name__ == "__main__":
    print("=" * 60)
    print("Auto-Registration Demo")
    print("=" * 60)

    # Create validator
    validator = HookValidator()

    # List all registered checkers
    print("\n[Registered Checkers]")
    for checker in validator.list_checkers():
        status = "ON" if checker['enabled'] else "OFF"
        print(f"  [{status}] {checker['name']} (priority: {checker['priority']})")
        print(f"        {checker['description']}")

    # Enable disabled checker
    print("\n[Enable check_test_exists]")
    validator.enable_checker('check_test_exists')
    for checker in validator.list_checkers():
        if checker['name'] == 'check_test_exists':
            status = "ON" if checker['enabled'] else "OFF"
            print(f"  [{status}] {checker['name']}")

    # Demo with extended validator
    print("\n[Extended Validator - StrictHookValidator]")
    strict_validator = StrictHookValidator()
    for checker in strict_validator.list_checkers():
        status = "ON" if checker['enabled'] else "OFF"
        print(f"  [{status}] {checker['name']} (priority: {checker['priority']})")

    print("\n" + "=" * 60)
```

### 使用範例

```python
# Create validator instance
validator = HookValidator(project_root="/path/to/project")

# List available checkers
for checker in validator.list_checkers():
    print(f"[{'ON' if checker['enabled'] else 'OFF'}] {checker['name']}")

# Output:
# [ON] check_naming_convention
# [ON] check_lib_imports
# [ON] check_output_format
# [OFF] check_test_exists

# Enable/disable checkers dynamically
validator.enable_checker('check_test_exists')
validator.disable_checker('check_output_format')

# Validate a hook file
result = validator.validate(".claude/hooks/my-hook.py")
print(f"Valid: {result.is_valid}")
for issue in result.issues:
    print(f"  [{issue.level}] {issue.message}")

# Create extended validator with more checks
strict = StrictHookValidator()
print(f"Total checkers: {len(strict.list_checkers())}")  # Inherits parent's checkers
```

## 替代方案：`__init_subclass__`

Python 3.6 引入了 `__init_subclass__`，可以在不使用 Metaclass 的情況下實現部分功能：

```python
class CheckerBase:
    """
    Base class using __init_subclass__ for auto-registration.

    Simpler than metaclass, but less powerful.
    """
    _checkers = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Collect checkers from this subclass
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name, None)
            if callable(attr) and getattr(attr, '_is_checker', False):
                cls._checkers[attr_name] = {
                    'method': attr_name,
                    'priority': attr._checker_priority,
                    'enabled': attr._checker_enabled,
                    'description': attr._checker_description,
                }

class HookValidator(CheckerBase):
    """Validator using __init_subclass__."""

    @check(priority=10)
    def check_naming(self, ctx):
        """Check naming convention."""
        pass

    @check(priority=20)
    def check_imports(self, ctx):
        """Check imports."""
        pass
```

### `__init_subclass__` vs Metaclass

| 面向 | `__init_subclass__` | Metaclass |
|------|---------------------|-----------|
| 複雜度 | 低 | 高 |
| 適用場景 | 子類別註冊 | 完整控制類別建立 |
| 效能 | 較好 | 略差 |
| 修改類別 | 有限 | 完整 |
| 繼承處理 | 需手動 | 自動 |
| 推薦情況 | 優先使用 | 需要進階功能時 |

**原則**：如果 `__init_subclass__` 能滿足需求，優先使用它。

## 設計權衡

| 面向 | 手動註冊 | Metaclass 自動註冊 |
|------|----------|-------------------|
| 程式碼重複 | 高（每次新增都要改兩處） | 低（只需加裝飾器） |
| 理解難度 | 低 | 中（需理解 Metaclass） |
| 擴展性 | 差（子類別需覆寫） | 好（自動繼承） |
| 除錯難度 | 低 | 中（執行流程隱含） |
| 動態控制 | 需額外實作 | 內建支援 |
| 執行順序 | 明確可見 | 由 priority 決定 |

## 什麼時候該用這個技術？

適合使用：

- **插件系統**：需要自動發現和載入插件
- **框架開發**：Django admin、pytest fixtures 等
- **大量相似元件**：多個檢查器/處理器需統一管理
- **需要動態控制**：執行時期啟用/停用功能

不建議使用：

- **只有少數幾個檢查項**：手動維護更簡單
- **團隊不熟悉 Metaclass**：增加維護負擔
- **簡單的應用程式**：過度工程
- **執行順序非常重要**：手動呼叫更明確

## 練習

### 基礎練習

實作一個簡單的命令註冊系統：

```python
class CommandRegistry:
    """
    命令註冊系統

    需求：
    1. 用 @command(name="xxx") 裝飾器註冊命令
    2. 提供 execute(name, *args) 執行指定命令
    3. 提供 list_commands() 列出所有命令
    """
    pass

# 使用範例
class MyApp(CommandRegistry):
    @command(name="greet")
    def say_hello(self, name):
        return f"Hello, {name}!"

    @command(name="add")
    def add_numbers(self, a, b):
        return a + b

app = MyApp()
print(app.execute("greet", "World"))  # Hello, World!
print(app.list_commands())  # ['add', 'greet']
```

### 進階練習

新增檢查項的相依性管理：

```python
@check(priority=10, depends_on=['check_file_exists'])
def check_content(self, ctx):
    """只有在檔案存在檢查通過後才執行"""
    pass
```

提示：

1. 在 `@check` 裝飾器加入 `depends_on` 參數
2. 在 `run_all_checks()` 中追蹤每個檢查項的結果
3. 檢查相依項是否通過再執行

### 挑戰題

實作跨模組的檢查項發現（類似 pytest）：

```python
# checkers/naming.py
@check(priority=10)
def check_naming(ctx):
    pass

# checkers/imports.py
@check(priority=20)
def check_imports(ctx):
    pass

# main.py
validator = HookValidator()
validator.discover_checkers('checkers/')  # 自動載入目錄下的所有檢查項
```

提示：

1. 使用 `importlib` 動態載入模組
2. 掃描模組中帶有 `_is_checker` 標記的函式
3. 將函式綁定為實例方法

## 延伸閱讀

- [Python Metaclass 官方文件](https://docs.python.org/3/reference/datamodel.html#metaclasses)
- [Django Model 的 Metaclass 實作](https://github.com/django/django/blob/main/django/db/models/base.py)
- [PEP 487 -- `__init_subclass__`](https://peps.python.org/pep-0487/)
- [pytest 插件發現機制](https://docs.pytest.org/en/latest/how-to/writing_plugins.html)

---

*上一章：[宣告式驗證](../declarative-validation/)*
*下一章：[類似 Django Field](../field-descriptor/)*
