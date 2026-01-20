---
title: "6.2 如何擴展共用模組"
description: "為 Hook 系統添加新功能"
weight: 2
---

# 如何擴展共用模組

本章介紹如何為 `.claude/lib/` 共用程式庫添加新功能。這是維護和擴展 Hook 系統的關鍵技能。

## 前置知識

建議先閱讀：
- [1.2 模組與套件組織](../../01-basics/modules/)
- [2.1 Type Hints 基礎](../../02-type-system/type-hints/)
- [4.1 類別設計原則](../../04-oop/class-design/)
- [5.3 unittest 基礎](../../05-error-testing/unittest/)

## 共用模組架構

目前的 `.claude/lib/` 結構：

```
.claude/lib/
├── __init__.py          # 模組初始化與匯出
├── git_utils.py         # Git 操作工具
├── hook_logging.py      # 日誌系統
├── hook_io.py           # 輸入輸出處理
├── config_loader.py     # 配置載入器
├── hook_validator.py    # Hook 驗證器
└── markdown_link_checker.py  # Markdown 連結檢查
```

## 步驟 1：規劃新模組

### 決定放置位置

| 情況 | 建議 |
|------|------|
| 新的獨立功能 | 建立新檔案 |
| 擴展現有功能 | 修改現有檔案 |
| 工具函式 | 加入相關現有模組 |

### 設計介面

在寫程式碼之前，先規劃公開介面：

```python
# 思考要提供什麼功能給使用者

# 函式：簡單操作
def validate_yaml(content: str) -> bool:
    """驗證 YAML 格式"""
    pass

# 類別：複雜操作或需要狀態
class YamlValidator:
    """YAML 驗證器"""

    def __init__(self, strict: bool = True):
        """初始化"""
        pass

    def validate(self, content: str) -> ValidationResult:
        """驗證內容"""
        pass
```

## 步驟 2：實作新模組

### 範例：建立 YAML 工具模組

```python
# .claude/lib/yaml_utils.py
"""
YAML 工具模組

提供 YAML 檔案的讀取、驗證和處理功能。
"""

from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass

# 嘗試導入 yaml
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class YamlResult:
    """YAML 處理結果"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


def load_yaml(path: str, encoding: str = "utf-8") -> YamlResult:
    """
    載入 YAML 檔案

    Args:
        path: 檔案路徑
        encoding: 檔案編碼

    Returns:
        YamlResult: 載入結果

    Example:
        result = load_yaml("config.yaml")
        if result.success:
            print(result.data)
        else:
            print(f"錯誤: {result.error}")
    """
    if not HAS_YAML:
        return YamlResult(
            success=False,
            error="PyYAML 未安裝。請執行: pip install pyyaml"
        )

    file_path = Path(path)

    if not file_path.exists():
        return YamlResult(
            success=False,
            error=f"檔案不存在: {path}"
        )

    try:
        content = file_path.read_text(encoding=encoding)
        data = yaml.safe_load(content)
        return YamlResult(success=True, data=data or {})
    except yaml.YAMLError as e:
        return YamlResult(success=False, error=f"YAML 解析錯誤: {e}")


def validate_yaml(content: str) -> bool:
    """
    驗證 YAML 格式

    Args:
        content: YAML 內容字串

    Returns:
        bool: 格式正確返回 True
    """
    if not HAS_YAML:
        return False

    try:
        yaml.safe_load(content)
        return True
    except yaml.YAMLError:
        return False


def merge_yaml_configs(*configs: dict) -> dict:
    """
    合併多個 YAML 配置

    後面的配置會覆蓋前面的。

    Args:
        *configs: 要合併的配置字典

    Returns:
        dict: 合併後的配置

    Example:
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = merge_yaml_configs(base, override)
        # result = {"a": 1, "b": 3, "c": 4}
    """
    result = {}
    for config in configs:
        if config:
            _deep_merge(result, config)
    return result


def _deep_merge(base: dict, override: dict) -> None:
    """深度合併字典（就地修改 base）"""
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value
```

## 步驟 3：更新 `__init__.py`

在 `__init__.py` 中註冊新模組：

```python
# .claude/lib/__init__.py
"""
Claude Hooks 共用程式庫
"""

# 現有匯入
from .git_utils import (
    run_git_command,
    get_current_branch,
    # ...
)

from .hook_logging import setup_hook_logging
from .hook_io import read_hook_input, write_hook_output

# 新增：YAML 工具
from .yaml_utils import (
    load_yaml,
    validate_yaml,
    merge_yaml_configs,
    YamlResult,
)

__all__ = [
    # 現有匯出
    "run_git_command",
    "get_current_branch",
    "setup_hook_logging",
    "read_hook_input",
    "write_hook_output",
    # 新增
    "load_yaml",
    "validate_yaml",
    "merge_yaml_configs",
    "YamlResult",
]

__version__ = "0.29.0"  # 更新版本
```

## 步驟 4：撰寫測試

```python
# tests/lib/test_yaml_utils.py
"""
YAML 工具模組測試
"""

import unittest
from unittest.mock import patch, mock_open
import sys
from pathlib import Path

# 添加 lib 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "lib"))

from yaml_utils import load_yaml, validate_yaml, merge_yaml_configs, YamlResult


class TestLoadYaml(unittest.TestCase):
    """測試 load_yaml 函式"""

    def test_load_valid_yaml(self):
        """測試載入有效的 YAML 檔案"""
        yaml_content = "key: value\nlist:\n  - item1\n  - item2"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=yaml_content):
                result = load_yaml("test.yaml")

        self.assertTrue(result.success)
        self.assertEqual(result.data["key"], "value")
        self.assertEqual(len(result.data["list"]), 2)

    def test_load_nonexistent_file(self):
        """測試載入不存在的檔案"""
        with patch("pathlib.Path.exists", return_value=False):
            result = load_yaml("nonexistent.yaml")

        self.assertFalse(result.success)
        self.assertIn("不存在", result.error)

    def test_load_invalid_yaml(self):
        """測試載入無效的 YAML"""
        invalid_content = "key: [invalid yaml"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=invalid_content):
                result = load_yaml("invalid.yaml")

        self.assertFalse(result.success)
        self.assertIn("解析錯誤", result.error)


class TestValidateYaml(unittest.TestCase):
    """測試 validate_yaml 函式"""

    def test_valid_yaml(self):
        """測試有效的 YAML"""
        self.assertTrue(validate_yaml("key: value"))
        self.assertTrue(validate_yaml("list:\n  - a\n  - b"))

    def test_invalid_yaml(self):
        """測試無效的 YAML"""
        self.assertFalse(validate_yaml("key: [unclosed"))
        self.assertFalse(validate_yaml("  bad indent\nkey: value"))


class TestMergeYamlConfigs(unittest.TestCase):
    """測試 merge_yaml_configs 函式"""

    def test_simple_merge(self):
        """測試簡單合併"""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = merge_yaml_configs(base, override)

        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], 3)  # 被覆蓋
        self.assertEqual(result["c"], 4)

    def test_deep_merge(self):
        """測試深度合併"""
        base = {
            "database": {
                "host": "localhost",
                "port": 5432
            }
        }
        override = {
            "database": {
                "port": 3306,
                "name": "mydb"
            }
        }

        result = merge_yaml_configs(base, override)

        self.assertEqual(result["database"]["host"], "localhost")
        self.assertEqual(result["database"]["port"], 3306)
        self.assertEqual(result["database"]["name"], "mydb")

    def test_multiple_configs(self):
        """測試多個配置合併"""
        config1 = {"a": 1}
        config2 = {"b": 2}
        config3 = {"c": 3}

        result = merge_yaml_configs(config1, config2, config3)

        self.assertEqual(result, {"a": 1, "b": 2, "c": 3})


if __name__ == "__main__":
    unittest.main()
```

## 步驟 5：更新文件

### 在模組文檔中說明

在模組開頭加入詳細的 docstring：

```python
"""
YAML 工具模組

提供 YAML 檔案的讀取、驗證和處理功能。

主要功能:
- load_yaml: 載入 YAML 檔案
- validate_yaml: 驗證 YAML 格式
- merge_yaml_configs: 合併配置

依賴:
- PyYAML (可選，但建議安裝)

使用方式:
    from lib.yaml_utils import load_yaml, validate_yaml

    # 載入配置
    result = load_yaml("config.yaml")
    if result.success:
        config = result.data

    # 驗證格式
    is_valid = validate_yaml(content)

版本: 0.29.0
"""
```

## 擴展現有模組

### 範例：為 git_utils 添加新功能

```python
# 在 .claude/lib/git_utils.py 中添加

def get_uncommitted_changes() -> list[str]:
    """
    取得未提交的變更檔案列表

    Returns:
        list[str]: 變更檔案的路徑列表

    Example:
        changes = get_uncommitted_changes()
        if changes:
            print(f"有 {len(changes)} 個未提交的變更")
    """
    success, output = run_git_command(["status", "--porcelain"])

    if not success:
        return []

    files = []
    for line in output.strip().split("\n"):
        if line.strip():
            # 格式: "XY filename" 或 "XY filename -> newname"
            parts = line[3:].split(" -> ")
            files.append(parts[-1])

    return files


def has_staged_changes() -> bool:
    """
    檢查是否有已暫存的變更

    Returns:
        bool: 有暫存變更返回 True
    """
    success, output = run_git_command(["diff", "--cached", "--name-only"])
    return success and bool(output.strip())
```

然後在 `__init__.py` 中更新匯出：

```python
from .git_utils import (
    run_git_command,
    get_current_branch,
    get_project_root,
    get_worktree_list,
    is_protected_branch,
    is_allowed_branch,
    # 新增
    get_uncommitted_changes,
    has_staged_changes,
)

__all__ = [
    # ... 現有匯出 ...
    "get_uncommitted_changes",
    "has_staged_changes",
]
```

## 設計原則

### 1. 單一職責

每個模組專注一個領域：

```python
# 好：專注於 Git 操作
# git_utils.py
def get_current_branch(): ...
def run_git_command(): ...
def is_protected_branch(): ...

# 不好：混合不同功能
# utils.py
def get_current_branch(): ...
def validate_yaml(): ...
def send_notification(): ...
```

### 2. 統一的返回值模式

使用一致的返回值設計：

```python
# 簡單操作：返回 (bool, str)
def run_command(cmd: str) -> tuple[bool, str]:
    """返回 (成功與否, 輸出或錯誤訊息)"""
    pass

# 複雜操作：返回 dataclass
@dataclass
class OperationResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

def complex_operation() -> OperationResult:
    pass
```

### 3. 優雅的依賴處理

```python
# 處理可選依賴
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

def validate_yaml(content: str) -> bool:
    if not HAS_YAML:
        raise ImportError("需要安裝 PyYAML: pip install pyyaml")
    # ...
```

### 4. 完整的文檔字串

```python
def load_config(name: str) -> dict:
    """
    載入配置檔案

    Args:
        name: 配置名稱（不含副檔名）

    Returns:
        dict: 配置內容

    Raises:
        FileNotFoundError: 配置檔案不存在

    Example:
        config = load_config("agents")
        print(config["known_agents"])
    """
```

## 完整檢查清單

擴展共用模組時的檢查項目：

- [ ] 設計清晰的公開介面
- [ ] 使用 Type Hints
- [ ] 撰寫完整的 docstring
- [ ] 處理可選依賴
- [ ] 統一返回值模式
- [ ] 更新 `__init__.py`
- [ ] 更新 `__all__` 匯出
- [ ] 更新版本號
- [ ] 撰寫單元測試
- [ ] 測試與現有 Hook 的整合

## 思考題

1. 什麼時候應該建立新模組，什麼時候應該擴展現有模組？
2. 如何設計 API 使其易於測試？
3. `__all__` 的作用是什麼？為什麼要維護它？

---

*上一章：[如何新增一個 Hook](../new-hook/)*
*下一章：[如何新增語言解析器](../new-parser/)*
*回到首頁：[Python 維護工程師實戰指南](../../)*
