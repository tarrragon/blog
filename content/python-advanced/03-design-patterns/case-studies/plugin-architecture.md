---
title: "案例：插件架構設計"
date: 2026-01-21
description: "用 Protocol 和註冊機制實現可擴展的插件系統"
weight: 2
---

# 案例：插件架構設計

本案例基於 `.claude/lib/hook_validator.py` 的實際程式碼，展示如何用 Protocol 和註冊機制實現可擴展的插件系統。

## 先備知識

- [2.2 自動註冊機制](../../02-metaprogramming/case-studies/auto-registration/)
- [3.5.4 插件系統設計](../../plugin-system/)

## 問題背景

### 現有設計

`hook_validator.py` 的驗證邏輯直接寫在類別中：

```python
class HookValidator:
    """Hook 合規性驗證器"""

    def validate_hook(self, hook_path: str) -> ValidationResult:
        """驗證單個 Hook 檔案"""
        # ... 讀取檔案 ...

        # 執行各項檢查 - 硬編碼的驗證規則
        issues = []
        issues.extend(self.check_naming_convention(hook_path))
        issues.extend(self.check_lib_imports(content, hook_path))
        issues.extend(self.check_output_format(content))
        issues.extend(self.check_test_exists(hook_path))

        return ValidationResult(hook_path=str(hook_path), issues=issues)

    def check_naming_convention(self, hook_path: Path) -> List[ValidationIssue]:
        """檢查命名規範"""
        # ... 具體驗證邏輯 ...

    def check_lib_imports(self, content: str, hook_path: Path) -> List[ValidationIssue]:
        """檢查共用模組導入"""
        # ... 具體驗證邏輯 ...

    def check_output_format(self, content: str) -> List[ValidationIssue]:
        """檢查輸出格式"""
        # ... 具體驗證邏輯 ...

    def check_test_exists(self, hook_path: Path) -> List[ValidationIssue]:
        """檢查測試檔案是否存在"""
        # ... 具體驗證邏輯 ...
```

### 這個設計的優點

- 所有邏輯集中管理，容易找到相關程式碼
- 沒有額外的抽象層，直接明瞭
- 對小型專案來說足夠使用

### 這個設計的限制

當需要擴展時：

- **第三方無法新增自己的檢查項**：想加入「Docstring 檢查」必須修改 `HookValidator`
- **修改需要改動核心程式碼**：每新增一個檢查都要改 `validate_hook` 方法
- **違反開放封閉原則**：對擴展不開放，對修改不封閉

## 進階解決方案

### 設計目標

1. **定義清晰的插件介面**：用 Protocol 描述檢查項該有的行為
2. **支援第三方擴展**：外部套件可以新增檢查項
3. **插件可以獨立測試**：每個檢查項是獨立的單元
4. **支援插件的啟用/停用**：可以動態控制要執行哪些檢查

### 實作步驟

#### 步驟 1：用 Protocol 定義插件介面

Protocol 讓我們定義「檢查項該有的行為」，而不強制繼承關係：

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Optional, List, runtime_checkable

@dataclass
class ValidationIssue:
    """Validation issue description"""
    level: str  # "error" | "warning" | "info"
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class CheckContext:
    """Context passed to each check"""
    hook_path: Path
    content: str
    project_root: Path

@runtime_checkable
class ValidationCheck(Protocol):
    """
    Protocol for validation checks

    Any class implementing this protocol can be used as a validation check.
    No inheritance required - just implement the methods.
    """

    @property
    def name(self) -> str:
        """Check name for identification"""
        ...

    @property
    def description(self) -> str:
        """Human-readable description"""
        ...

    def check(self, context: CheckContext) -> List[ValidationIssue]:
        """
        Execute the validation check

        Args:
            context: Check context with file info

        Returns:
            List of validation issues found
        """
        ...
```

**為什麼用 Protocol 而不是 ABC？**

- Protocol 是「鴨子型別」的靜態版本
- 不強制繼承，現有類別只要有對應方法就能用
- `@runtime_checkable` 讓我們可以用 `isinstance()` 檢查

#### 步驟 2：實作插件註冊機制

註冊機制提供兩種方式：裝飾器和明確註冊：

```python
from typing import Type, Dict, Callable, TypeVar

# Type variable for check classes
C = TypeVar("C", bound=ValidationCheck)

class CheckRegistry:
    """
    Registry for validation checks

    Supports both decorator registration and explicit registration.
    """

    def __init__(self) -> None:
        self._checks: Dict[str, ValidationCheck] = {}
        self._disabled: set[str] = set()

    def register(self, check: ValidationCheck) -> ValidationCheck:
        """
        Register a check instance

        Args:
            check: Check instance to register

        Returns:
            The same check instance (for chaining)

        Example:
            registry.register(NamingCheck())
        """
        if not isinstance(check, ValidationCheck):
            raise TypeError(
                f"Check must implement ValidationCheck protocol, "
                f"got {type(check).__name__}"
            )
        self._checks[check.name] = check
        return check

    def check(self, name: Optional[str] = None) -> Callable[[Type[C]], Type[C]]:
        """
        Decorator for registering check classes

        Args:
            name: Optional custom name (default: class name)

        Returns:
            Class decorator

        Example:
            @registry.check()
            class MyCheck:
                ...
        """
        def decorator(cls: Type[C]) -> Type[C]:
            instance = cls()
            self._checks[name or instance.name] = instance
            return cls
        return decorator

    def get_check(self, name: str) -> Optional[ValidationCheck]:
        """Get a check by name"""
        return self._checks.get(name)

    def get_enabled_checks(self) -> List[ValidationCheck]:
        """Get all enabled checks"""
        return [
            check for name, check in self._checks.items()
            if name not in self._disabled
        ]

    def enable(self, name: str) -> None:
        """Enable a check"""
        self._disabled.discard(name)

    def disable(self, name: str) -> None:
        """Disable a check"""
        self._disabled.add(name)

    def list_checks(self) -> List[str]:
        """List all registered check names"""
        return list(self._checks.keys())

# Global registry instance
default_registry = CheckRegistry()
```

**兩種註冊方式的比較**：

| 方式 | 使用時機 | 優點 | 缺點 |
|------|---------|------|------|
| 裝飾器 `@registry.check()` | 類別定義時 | 簡潔、宣告式 | 模組載入時就註冊 |
| 明確註冊 `registry.register()` | 執行時 | 更靈活、可延遲 | 較囉嗦 |

#### 步驟 3：支援 entry_points 自動發現

`entry_points` 是 Python 打包系統的標準機制，讓外部套件可以註冊插件：

```python
import sys
from importlib.metadata import entry_points
from typing import Iterator

def discover_checks(
    group: str = "hook_validator.checks"
) -> Iterator[ValidationCheck]:
    """
    Discover checks from installed packages via entry_points

    Args:
        group: Entry point group name

    Yields:
        Discovered check instances

    Example:
        for check in discover_checks():
            registry.register(check)
    """
    # Python 3.10+ API
    if sys.version_info >= (3, 10):
        eps = entry_points(group=group)
    else:
        # Python 3.9 compatibility
        eps = entry_points().get(group, [])

    for ep in eps:
        try:
            # Load the check class/factory
            check_factory = ep.load()

            # Create instance
            if callable(check_factory):
                check = check_factory()
            else:
                check = check_factory

            # Validate it implements the protocol
            if isinstance(check, ValidationCheck):
                yield check
            else:
                import warnings
                warnings.warn(
                    f"Entry point {ep.name} does not implement "
                    f"ValidationCheck protocol"
                )

        except Exception as e:
            import warnings
            warnings.warn(f"Failed to load check {ep.name}: {e}")

def load_external_checks(registry: CheckRegistry) -> int:
    """
    Load all external checks into a registry

    Args:
        registry: Target registry

    Returns:
        Number of checks loaded
    """
    count = 0
    for check in discover_checks():
        registry.register(check)
        count += 1
    return count
```

#### 步驟 4：實作插件載入與管理

插件管理器整合了註冊、發現和執行：

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List

@dataclass
class ValidationResult:
    """Validation result for a single hook"""
    hook_path: str
    issues: List[ValidationIssue] = field(default_factory=list)
    is_compliant: bool = True
    checks_run: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Calculate compliance status"""
        self.is_compliant = not any(
            issue.level == "error" for issue in self.issues
        )

class PluginValidator:
    """
    Plugin-based hook validator

    Uses registered checks to validate hook files.
    """

    def __init__(
        self,
        registry: Optional[CheckRegistry] = None,
        project_root: Optional[str] = None,
        auto_discover: bool = True
    ) -> None:
        """
        Initialize validator

        Args:
            registry: Check registry (default: global registry)
            project_root: Project root directory
            auto_discover: Whether to auto-discover external checks
        """
        self.registry = registry or default_registry
        self.project_root = Path(
            project_root or os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        )

        if auto_discover:
            load_external_checks(self.registry)

    def validate_hook(self, hook_path: str) -> ValidationResult:
        """
        Validate a single hook file

        Args:
            hook_path: Path to hook file

        Returns:
            Validation result
        """
        path = self._resolve_path(hook_path)

        # Check file exists
        if not path.exists():
            return ValidationResult(
                hook_path=str(path),
                issues=[
                    ValidationIssue(
                        level="error",
                        message=f"Hook file not found: {path}"
                    )
                ]
            )

        # Read content
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return ValidationResult(
                hook_path=str(path),
                issues=[
                    ValidationIssue(
                        level="error",
                        message=f"Cannot read hook file: {e}"
                    )
                ]
            )

        # Build context
        context = CheckContext(
            hook_path=path,
            content=content,
            project_root=self.project_root
        )

        # Run all enabled checks
        all_issues: List[ValidationIssue] = []
        checks_run: List[str] = []

        for check in self.registry.get_enabled_checks():
            try:
                issues = check.check(context)
                all_issues.extend(issues)
                checks_run.append(check.name)
            except Exception as e:
                all_issues.append(
                    ValidationIssue(
                        level="error",
                        message=f"Check {check.name} failed: {e}"
                    )
                )

        return ValidationResult(
            hook_path=str(path),
            issues=all_issues,
            checks_run=checks_run
        )

    def _resolve_path(self, path: str) -> Path:
        """Resolve path to absolute"""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.project_root / p
```

### 完整程式碼

```python
#!/usr/bin/env python3
"""
Plugin-based Hook Validator

A validation system using Protocol and registry pattern,
allowing third-party extensions via entry_points.
"""

from __future__ import annotations

import os
import re
import sys
import warnings
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from pathlib import Path
from typing import (
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Protocol,
    Type,
    TypeVar,
    runtime_checkable,
)

# ============================================================
# Data Classes
# ============================================================

@dataclass
class ValidationIssue:
    """Validation issue description"""
    level: str  # "error" | "warning" | "info"
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class CheckContext:
    """Context passed to each check"""
    hook_path: Path
    content: str
    project_root: Path

@dataclass
class ValidationResult:
    """Validation result for a single hook"""
    hook_path: str
    issues: List[ValidationIssue] = field(default_factory=list)
    is_compliant: bool = True
    checks_run: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.is_compliant = not any(
            issue.level == "error" for issue in self.issues
        )

# ============================================================
# Protocol Definition
# ============================================================

@runtime_checkable
class ValidationCheck(Protocol):
    """Protocol for validation checks"""

    @property
    def name(self) -> str:
        """Check name for identification"""
        ...

    @property
    def description(self) -> str:
        """Human-readable description"""
        ...

    def check(self, context: CheckContext) -> List[ValidationIssue]:
        """Execute the validation check"""
        ...

# ============================================================
# Registry
# ============================================================

C = TypeVar("C", bound=ValidationCheck)

class CheckRegistry:
    """Registry for validation checks"""

    def __init__(self) -> None:
        self._checks: Dict[str, ValidationCheck] = {}
        self._disabled: set[str] = set()

    def register(self, check: ValidationCheck) -> ValidationCheck:
        """Register a check instance"""
        if not isinstance(check, ValidationCheck):
            raise TypeError(
                f"Check must implement ValidationCheck protocol, "
                f"got {type(check).__name__}"
            )
        self._checks[check.name] = check
        return check

    def check(self, name: Optional[str] = None) -> Callable[[Type[C]], Type[C]]:
        """Decorator for registering check classes"""
        def decorator(cls: Type[C]) -> Type[C]:
            instance = cls()
            self._checks[name or instance.name] = instance
            return cls
        return decorator

    def get_check(self, name: str) -> Optional[ValidationCheck]:
        """Get a check by name"""
        return self._checks.get(name)

    def get_enabled_checks(self) -> List[ValidationCheck]:
        """Get all enabled checks"""
        return [
            check for name, check in self._checks.items()
            if name not in self._disabled
        ]

    def enable(self, name: str) -> None:
        """Enable a check"""
        self._disabled.discard(name)

    def disable(self, name: str) -> None:
        """Disable a check"""
        self._disabled.add(name)

    def list_checks(self) -> List[str]:
        """List all registered check names"""
        return list(self._checks.keys())

# Global registry
default_registry = CheckRegistry()

# ============================================================
# Entry Points Discovery
# ============================================================

def discover_checks(
    group: str = "hook_validator.checks"
) -> Iterator[ValidationCheck]:
    """Discover checks from installed packages via entry_points"""
    if sys.version_info >= (3, 10):
        eps = entry_points(group=group)
    else:
        eps = entry_points().get(group, [])

    for ep in eps:
        try:
            check_factory = ep.load()
            check = check_factory() if callable(check_factory) else check_factory

            if isinstance(check, ValidationCheck):
                yield check
            else:
                warnings.warn(
                    f"Entry point {ep.name} does not implement "
                    f"ValidationCheck protocol"
                )
        except Exception as e:
            warnings.warn(f"Failed to load check {ep.name}: {e}")

def load_external_checks(registry: CheckRegistry) -> int:
    """Load all external checks into a registry"""
    count = 0
    for check in discover_checks():
        registry.register(check)
        count += 1
    return count

# ============================================================
# Built-in Checks
# ============================================================

@default_registry.check()
class NamingConventionCheck:
    """Check hook file naming convention"""

    VALID_PATTERNS = [
        r"^[a-z0-9]([a-z0-9\-_]*[a-z0-9])?\.py$",
    ]

    @property
    def name(self) -> str:
        return "naming_convention"

    @property
    def description(self) -> str:
        return "Check that hook files follow naming conventions"

    def check(self, context: CheckContext) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        filename = context.hook_path.name

        valid = any(
            re.match(pattern, filename)
            for pattern in self.VALID_PATTERNS
        )

        if not valid:
            issues.append(
                ValidationIssue(
                    level="warning",
                    message=f"Invalid file name: {filename}",
                    suggestion="Use snake_case or kebab-case naming"
                )
            )

        return issues

@default_registry.check()
class LibImportCheck:
    """Check that hooks import required libraries"""

    HOOK_IO_PATTERNS = [
        r"from\s+hook_io\s+import",
        r"from\s+lib\.hook_io\s+import",
    ]

    @property
    def name(self) -> str:
        return "lib_import"

    @property
    def description(self) -> str:
        return "Check that hooks import hook_io module"

    def check(self, context: CheckContext) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        has_import = any(
            re.search(pattern, context.content)
            for pattern in self.HOOK_IO_PATTERNS
        )

        if not has_import:
            issues.append(
                ValidationIssue(
                    level="warning",
                    message="Missing hook_io import",
                    suggestion="Add: from hook_io import read_hook_input, write_hook_output"
                )
            )

        return issues

@default_registry.check()
class OutputFormatCheck:
    """Check hook output format"""

    GOOD_PATTERNS = [
        r"write_hook_output\s*\(",
        r"create_pretooluse_output\s*\(",
        r"create_posttooluse_output\s*\(",
    ]

    BAD_PATTERNS = [
        r'print\s*\(\s*json\.dumps\s*\(',
        r'sys\.stdout\.write\s*\(\s*json\.dumps\s*\(',
    ]

    @property
    def name(self) -> str:
        return "output_format"

    @property
    def description(self) -> str:
        return "Check that hooks use proper output functions"

    def check(self, context: CheckContext) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        has_bad = any(
            re.search(pattern, context.content)
            for pattern in self.BAD_PATTERNS
        )

        if has_bad:
            issues.append(
                ValidationIssue(
                    level="warning",
                    message="Using print(json.dumps(...)) instead of write_hook_output()",
                    suggestion="Use write_hook_output() for proper output formatting"
                )
            )

        return issues

@default_registry.check()
class TestExistsCheck:
    """Check that corresponding test file exists"""

    @property
    def name(self) -> str:
        return "test_exists"

    @property
    def description(self) -> str:
        return "Check that hook has a corresponding test file"

    def check(self, context: CheckContext) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        hook_name = context.hook_path.stem
        test_name = f"test_{hook_name.replace('-', '_')}.py"

        possible_paths = [
            context.project_root / ".claude" / "lib" / "tests" / test_name,
            context.project_root / ".claude" / "hooks" / "tests" / test_name,
        ]

        if not any(p.exists() for p in possible_paths):
            issues.append(
                ValidationIssue(
                    level="info",
                    message=f"No test file found: {test_name}",
                    suggestion=f"Create test at .claude/lib/tests/{test_name}"
                )
            )

        return issues

# ============================================================
# Validator
# ============================================================

class PluginValidator:
    """Plugin-based hook validator"""

    def __init__(
        self,
        registry: Optional[CheckRegistry] = None,
        project_root: Optional[str] = None,
        auto_discover: bool = True
    ) -> None:
        self.registry = registry or default_registry
        self.project_root = Path(
            project_root or os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        )

        if auto_discover:
            load_external_checks(self.registry)

    def validate_hook(self, hook_path: str) -> ValidationResult:
        """Validate a single hook file"""
        path = self._resolve_path(hook_path)

        if not path.exists():
            return ValidationResult(
                hook_path=str(path),
                issues=[
                    ValidationIssue(
                        level="error",
                        message=f"Hook file not found: {path}"
                    )
                ]
            )

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return ValidationResult(
                hook_path=str(path),
                issues=[
                    ValidationIssue(
                        level="error",
                        message=f"Cannot read hook file: {e}"
                    )
                ]
            )

        context = CheckContext(
            hook_path=path,
            content=content,
            project_root=self.project_root
        )

        all_issues: List[ValidationIssue] = []
        checks_run: List[str] = []

        for check in self.registry.get_enabled_checks():
            try:
                issues = check.check(context)
                all_issues.extend(issues)
                checks_run.append(check.name)
            except Exception as e:
                all_issues.append(
                    ValidationIssue(
                        level="error",
                        message=f"Check {check.name} failed: {e}"
                    )
                )

        return ValidationResult(
            hook_path=str(path),
            issues=all_issues,
            checks_run=checks_run
        )

    def validate_all_hooks(self, hooks_dir: Optional[str] = None) -> List[ValidationResult]:
        """Validate all hook files in a directory"""
        if hooks_dir is None:
            hooks_dir = str(self.project_root / ".claude" / "hooks")

        hooks_path = self._resolve_path(hooks_dir)

        if not hooks_path.is_dir():
            return [
                ValidationResult(
                    hook_path=str(hooks_path),
                    issues=[
                        ValidationIssue(
                            level="error",
                            message=f"Hooks directory not found: {hooks_path}"
                        )
                    ]
                )
            ]

        results = []
        for hook_file in sorted(hooks_path.glob("*.py")):
            if hook_file.name.startswith("_"):
                continue
            results.append(self.validate_hook(str(hook_file)))

        return results

    def _resolve_path(self, path: str) -> Path:
        """Resolve path to absolute"""
        p = Path(path)
        return p if p.is_absolute() else self.project_root / p

# ============================================================
# Demo
# ============================================================

if __name__ == "__main__":
    import tempfile

    # Show registered checks
    print("Registered checks:")
    for name in default_registry.list_checks():
        check = default_registry.get_check(name)
        if check:
            print(f"  - {name}: {check.description}")

    # Create test hook
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir) / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True)

        # Create a hook file
        hook_file = hooks_dir / "check-permissions.py"
        hook_file.write_text("""
#!/usr/bin/env python3
from hook_io import read_hook_input, write_hook_output

def main():
    data = read_hook_input()
    write_hook_output({"decision": "allow"})

if __name__ == "__main__":
    main()
""")

        # Validate
        validator = PluginValidator(project_root=tmpdir, auto_discover=False)
        result = validator.validate_hook(str(hook_file))

        print(f"\nValidation result for {result.hook_path}:")
        print(f"  Compliant: {result.is_compliant}")
        print(f"  Checks run: {result.checks_run}")
        for issue in result.issues:
            print(f"  [{issue.level}] {issue.message}")
```

### 使用範例

#### 建立插件

建立自訂檢查項只需要實作 Protocol 定義的介面：

```python
from typing import List
import re

class DocstringCheck:
    """
    Check that hooks have proper docstrings

    A custom check that can be added to the validator.
    No inheritance required - just implement the protocol.
    """

    @property
    def name(self) -> str:
        return "docstring"

    @property
    def description(self) -> str:
        return "Check that hook has a module docstring"

    def check(self, context: CheckContext) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # Check for module docstring
        docstring_pattern = r'^(#!/.*\n)?[\s]*["\'\]{3}'

        if not re.match(docstring_pattern, context.content):
            issues.append(
                ValidationIssue(
                    level="info",
                    message="Missing module docstring",
                    suggestion='Add a docstring at the top: """Description of hook"""'
                )
            )

        return issues

class SecurityCheck:
    """
    Check for potential security issues

    Looks for dangerous patterns like eval(), exec(), subprocess with shell=True
    """

    DANGEROUS_PATTERNS = [
        (r'\beval\s*\(', "eval() is dangerous, consider alternatives"),
        (r'\bexec\s*\(', "exec() is dangerous, consider alternatives"),
        (r'subprocess.*shell\s*=\s*True', "shell=True is a security risk"),
        (r'os\.system\s*\(', "os.system() is insecure, use subprocess instead"),
    ]

    @property
    def name(self) -> str:
        return "security"

    @property
    def description(self) -> str:
        return "Check for potential security vulnerabilities"

    def check(self, context: CheckContext) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        for pattern, message in self.DANGEROUS_PATTERNS:
            if re.search(pattern, context.content):
                issues.append(
                    ValidationIssue(
                        level="warning",
                        message=message
                    )
                )

        return issues
```

#### 註冊插件

有三種方式可以註冊插件：

```python
# Method 1: Using decorator (at class definition time)
@default_registry.check()
class MyCheck:
    @property
    def name(self) -> str:
        return "my_check"
    # ...

# Method 2: Explicit registration (at runtime)
docstring_check = DocstringCheck()
security_check = SecurityCheck()

default_registry.register(docstring_check)
default_registry.register(security_check)

# Method 3: Create custom registry
custom_registry = CheckRegistry()
custom_registry.register(DocstringCheck())
custom_registry.register(SecurityCheck())

validator = PluginValidator(registry=custom_registry, auto_discover=False)
```

#### 使用 entry_points

對於要發布為獨立套件的插件，使用 `pyproject.toml` 設定 entry_points：

```toml
# pyproject.toml
[project]
name = "my-hook-checks"
version = "1.0.0"
description = "Custom hook validation checks"

dependencies = [
    # hook-validator is the core package
]

[project.entry-points."hook_validator.checks"]
# Format: name = "module:factory_or_class"
docstring = "my_hook_checks:DocstringCheck"
security = "my_hook_checks.security:SecurityCheck"
```

插件模組結構：

```python
# my_hook_checks/__init__.py
from .docstring import DocstringCheck
from .security import SecurityCheck

__all__ = ["DocstringCheck", "SecurityCheck"]

# my_hook_checks/docstring.py
class DocstringCheck:
    """Check for module docstrings"""

    @property
    def name(self) -> str:
        return "docstring"

    @property
    def description(self) -> str:
        return "Check that hook has a module docstring"

    def check(self, context):
        # ... implementation ...
        return []
```

安裝後，`PluginValidator` 會自動發現並載入這些檢查項：

```python
# Automatic discovery from entry_points
validator = PluginValidator(auto_discover=True)

# Check what's loaded
print(validator.registry.list_checks())
# ['naming_convention', 'lib_import', 'output_format', 'test_exists',
#  'docstring', 'security']  # <- external checks discovered!
```

## 設計權衡

| 面向 | 硬編碼方法 | 插件架構 |
|------|-----------|----------|
| **擴展性** | 差：需修改核心程式碼 | 優秀：第三方可自由擴展 |
| **初始複雜度** | 低：直接寫邏輯 | 中：需要理解 Protocol 和註冊機制 |
| **維護成本** | 隨功能增加而上升 | 穩定：新增功能不改核心 |
| **第三方擴展** | 不支援 | 支援：透過 entry_points |
| **測試難度** | 需要 mock 整個類別 | 容易：每個 check 獨立測試 |
| **執行時彈性** | 固定 | 高：可動態啟用/停用 |
| **除錯難度** | 簡單：程式碼集中 | 需要追蹤插件來源 |
| **效能開銷** | 無 | 輕微：註冊和迭代成本 |

## 什麼時候該用這個技術？

**適合使用**：

- 需要支援第三方擴展的工具（如 pytest、flake8、pre-commit）
- 功能模組化明確，各檢查項獨立
- 預期會頻繁新增功能
- 需要讓使用者自訂行為

**不建議使用**：

- 內部使用的小工具
- 功能很少變動
- 團隊對 Protocol 和 entry_points 不熟悉
- 效能關鍵的熱路徑

## 練習

### 基礎練習：實作格式檢查插件

實作一個 `IndentationCheck`，檢查 Python 檔案是否使用一致的縮排（空格 vs Tab）：

```python
class IndentationCheck:
    """Check for consistent indentation"""

    @property
    def name(self) -> str:
        return "indentation"

    @property
    def description(self) -> str:
        return "Check for consistent indentation style"

    def check(self, context: CheckContext) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # TODO: Implement
        # 1. Check each line's leading whitespace
        # 2. Detect if mixing tabs and spaces
        # 3. Report as warning if inconsistent

        return issues
```

提示：
- 使用 `context.content.splitlines()` 取得每一行
- 檢查每行開頭的空白字元 `line[:len(line) - len(line.lstrip())]`

### 進階練習：新增優先順序和相依性

擴展 `ValidationCheck` Protocol，支援：

1. **優先順序**：決定檢查項執行順序
2. **相依性**：某些檢查必須在其他檢查之後執行

```python
@runtime_checkable
class ValidationCheck(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def priority(self) -> int:
        """Lower number = higher priority (default: 100)"""
        return 100

    @property
    def depends_on(self) -> List[str]:
        """Names of checks that must run before this one"""
        return []

    def check(self, context: CheckContext) -> List[ValidationIssue]: ...
```

然後修改 `PluginValidator.validate_hook()` 使用拓撲排序執行檢查。

### 挑戰題：實作插件的熱載入

實作「不重啟程式就能載入新插件」的功能：

```python
class HotReloadableRegistry(CheckRegistry):
    """Registry that supports hot-reloading plugins"""

    def watch_directory(self, path: str) -> None:
        """Watch a directory for new plugin files"""
        # TODO: Use watchdog or polling to detect new files
        pass

    def reload_check(self, name: str) -> None:
        """Reload a specific check"""
        # TODO: Unload old module, load new version
        pass
```

提示：
- 使用 `importlib.reload()` 重新載入模組
- 使用 `watchdog` 套件監控檔案變化
- 注意處理模組快取 `sys.modules`

## 延伸閱讀

- [Python typing.Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol)
- [importlib.metadata entry_points](https://docs.python.org/3/library/importlib.metadata.html#entry-points)
- [pytest 插件系統](https://docs.pytest.org/en/stable/how-to/writing_plugins.html)
- [PEP 544 - Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- [setuptools entry_points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html)

---

*上一章：[快取生命週期管理](../cache-lifecycle/)*
*下一章：[異常設計架構](../exception-hierarchy/)*
