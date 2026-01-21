---
title: "4.1 類別設計原則"
date: 2026-01-20
description: "設計清晰的類別介面"
weight: 1
---

# 類別設計原則

Python 支援物件導向程式設計，但並不強制使用。本章介紹何時該使用類別，以及如何設計清晰的類別介面。

## 何時使用類別？

### 使用類別的情況

1. **封裝狀態和行為**
   ```python
   class MarkdownLinkChecker:
       def __init__(self, project_root):
           self.project_root = Path(project_root)

       def check_file(self, path):
           ...

       def check_directory(self, path):
           ...
   ```

2. **需要多個實例**
   ```python
   checker1 = MarkdownLinkChecker("/project1")
   checker2 = MarkdownLinkChecker("/project2")
   ```

3. **有複雜的初始化邏輯**

### 使用函式的情況

1. **無狀態的操作**
   ```python
   def run_git_command(args):
       # 不需要保存狀態
       ...
   ```

2. **簡單的工具函式**
   ```python
   def is_protected_branch(branch):
       return branch in PROTECTED_BRANCHES
   ```

## 實際範例：Hook 驗證器

來自 `.claude/lib/hook_validator.py`：

```python
class HookValidator:
    """Hook 合規性驗證器"""

    # 類別常數
    HOOK_IO_PATTERNS = [
        r"from\s+hook_io\s+import",
        r"from\s+lib\.hook_io\s+import",
    ]

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化驗證器

        Args:
            project_root: 專案根目錄
        """
        if project_root is None:
            project_root = os.environ.get(
                "CLAUDE_PROJECT_DIR",
                os.getcwd()
            )
        self.project_root = Path(project_root)

    def validate_hook(self, hook_path: str) -> ValidationResult:
        """驗證單個 Hook 檔案"""
        hook_path = self._resolve_path(hook_path)
        # ... 驗證邏輯 ...
        return ValidationResult(...)

    def validate_all_hooks(self, hooks_dir: Optional[str] = None):
        """驗證所有 Hook 檔案"""
        ...

    # 私有方法
    def _resolve_path(self, path: str) -> Path:
        """解析路徑為絕對路徑"""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.project_root / p
```

### 設計分析

| 元素 | 說明 |
|------|------|
| 類別常數 | `HOOK_IO_PATTERNS` - 共用的配置 |
| 實例變數 | `self.project_root` - 每個實例可能不同 |
| 公開方法 | `validate_hook()`, `validate_all_hooks()` |
| 私有方法 | `_resolve_path()` - 內部使用 |

## 類別設計原則

### 1. 單一職責原則（SRP）

每個類別只負責一件事：

```python
# 好：每個類別有單一職責
class MarkdownLinkChecker:
    """只負責檢查 Markdown 連結"""
    def check_file(self, path): ...
    def check_directory(self, path): ...

class HookValidator:
    """只負責驗證 Hook"""
    def validate_hook(self, path): ...
    def validate_all_hooks(self): ...

# 不好：一個類別做太多事
class FileProcessor:
    def check_links(self): ...
    def validate_hooks(self): ...
    def format_code(self): ...
    def run_tests(self): ...
```

### 2. 封裝

隱藏內部實作，只暴露必要的介面：

```python
class MarkdownLinkChecker:
    # 私有常數（Python 慣例用底線）
    _EXTERNAL_PATTERNS = [r'^https?://', r'^mailto:']

    def __init__(self, project_root):
        # 私有屬性
        self._project_root = Path(project_root)

    # 公開方法
    def check_file(self, path):
        return self._do_check(path)

    # 私有方法
    def _do_check(self, path):
        ...

    def _is_external_link(self, target):
        ...
```

### 3. 明確的初始化

`__init__` 應該完成所有必要的初始化：

```python
class HookValidator:
    def __init__(self, project_root: Optional[str] = None):
        # 處理預設值
        if project_root is None:
            project_root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # 初始化所有實例變數
        self.project_root = Path(project_root)

        # 不要在這裡做複雜的 I/O 操作
```

## 實際範例：Markdown 連結檢查器

來自 `.claude/lib/markdown_link_checker.py`：

```python
class MarkdownLinkChecker:
    """Markdown 連結檢查器"""

    # 編譯好的正則表達式（類別常數）
    INLINE_LINK_PATTERN = re.compile(
        r'(?<!!)\[([^\]]+)\]\(([^)]+)\)'
    )

    EXTERNAL_PATTERNS = [
        r'^https?://',
        r'^mailto:',
        r'^tel:',
    ]

    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            project_root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        self.project_root = Path(project_root)

    def check_file(self, file_path: str) -> LinkCheckResult:
        """檢查單個 Markdown 檔案"""
        file_path = self._resolve_path(file_path)

        if not file_path.exists():
            return self._create_error_result(file_path, "檔案不存在")

        content = file_path.read_text(encoding="utf-8")
        links = self.parse_markdown_links(content)
        broken_links = self._check_links(links, file_path.parent)

        return LinkCheckResult(
            file_path=str(file_path),
            total_links=len(links),
            broken_links=broken_links
        )

    def check_directory(self, dir_path: str, recursive=True):
        """檢查目錄下所有 Markdown 檔案"""
        ...

    def parse_markdown_links(self, content: str) -> list[dict]:
        """解析 Markdown 中的連結"""
        ...

    # === 私有方法 ===

    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.project_root / p

    def _is_external_link(self, target: str) -> bool:
        return any(re.match(p, target) for p in self.EXTERNAL_PATTERNS)

    def _create_error_result(self, path, message):
        ...
```

## 類別與模組函式的搭配

提供方便的模組層級函式：

```python
# markdown_link_checker.py

class MarkdownLinkChecker:
    """類別實作"""
    ...

# 方便使用的模組函式
def check_markdown_links(file_path: str, project_root: Optional[str] = None):
    """
    檢查單個檔案（便捷函式）

    Example:
        result = check_markdown_links("docs/README.md")
    """
    checker = MarkdownLinkChecker(project_root)
    return checker.check_file(file_path)

def check_directory(dir_path: str, project_root: Optional[str] = None):
    """檢查目錄（便捷函式）"""
    checker = MarkdownLinkChecker(project_root)
    return checker.check_directory(dir_path)
```

## 文檔字串

### 類別文檔

```python
class HookValidator:
    """
    Hook 合規性驗證器

    驗證 Hook 腳本是否遵循專案規範，包含：
    - 共用模組導入檢查
    - 輸出格式檢查
    - 測試存在性檢查

    Attributes:
        project_root: 專案根目錄路徑

    Example:
        validator = HookValidator()
        result = validator.validate_hook("my_hook.py")
        if not result.is_compliant:
            print(result.issues)
    """
```

### 方法文檔

```python
def validate_hook(self, hook_path: str) -> ValidationResult:
    """
    驗證單個 Hook 檔案

    Args:
        hook_path: Hook 檔案路徑（相對或絕對）

    Returns:
        ValidationResult: 驗證結果

    Raises:
        FileNotFoundError: 如果檔案不存在

    Example:
        result = validator.validate_hook(".claude/hooks/my_hook.py")
    """
```

## 最佳實踐

### 1. 優先使用組合而非繼承

```python
# 好：組合
class HookValidator:
    def __init__(self):
        self.link_checker = MarkdownLinkChecker()
        self.config_loader = ConfigLoader()

# 避免：深層繼承
class SpecialValidator(HookValidator, LinkChecker, ConfigLoader):
    ...
```

### 2. 保持類別小巧

```python
# 如果類別太大，考慮拆分
class ValidationEngine:
    def __init__(self):
        self.import_checker = ImportChecker()
        self.format_checker = FormatChecker()
        self.test_checker = TestChecker()
```

### 3. 使用有意義的命名

```python
# 好
class MarkdownLinkChecker:
    def check_file(self, path): ...

# 不好
class Checker:
    def do_it(self, x): ...
```

## 思考題

1. 什麼時候應該使用類別，什麼時候應該使用函式？
2. `_method` 和 `__method` 有什麼區別？
3. 為什麼 Hook 系統同時提供類別和便捷函式？

## 實作練習

1. 將一組相關的函式重構為一個類別
2. 為現有類別添加完整的文檔字串
3. 實作一個遵循單一職責原則的驗證器類別

## 延伸閱讀（進階系列）

- [進階設計模式](/python-advanced/03-design-patterns/) - 深入設計模式的高級應用
- [插件系統設計](/python-advanced/03-design-patterns/plugin-system/) - 建構可擴展的系統架構

---

*下一章：[抽象基類 ABC](../abc/)*
