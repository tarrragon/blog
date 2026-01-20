---
title: "6.4 套件維護最佳實踐"
description: "長期維護 Python 套件的最佳實踐"
weight: 4
---

# 套件維護最佳實踐

本章介紹維護 Python 套件的長期策略。

## 本章目標

學完本章後，你將能夠：

1. 建立良好的專案結構
2. 管理依賴與版本
3. 制定棄用與升級策略

---

## 【設計層】專案結構

### Src Layout vs Flat Layout

```text
Flat Layout：
my-package/
├── pyproject.toml
├── README.md
├── my_package/
│   ├── __init__.py
│   └── module.py
└── tests/
    └── test_module.py

Src Layout（推薦）：
my-package/
├── pyproject.toml
├── README.md
├── src/
│   └── my_package/
│       ├── __init__.py
│       └── module.py
└── tests/
    └── test_module.py
```

### 為什麼推薦 Src Layout？

```text
Flat Layout 的問題：
├── 可能意外匯入本地未安裝的套件
├── 測試可能使用開發版而非安裝版
└── 容易混淆專案根目錄和套件目錄

Src Layout 的優點：
├── 強制測試已安裝的套件
├── 清楚區分原始碼和設定檔
├── 避免命名衝突
└── 更接近使用者的安裝環境
```

### 完整專案結構範例

```text
my-package/
├── .github/
│   └── workflows/
│       ├── ci.yml              # 測試與檢查
│       └── publish.yml         # 發布流程
├── docs/
│   ├── conf.py
│   ├── index.rst
│   └── api/
├── src/
│   └── my_package/
│       ├── __init__.py
│       ├── py.typed            # 標記為有型別提示
│       ├── core.py
│       └── utils.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest fixtures
│   ├── test_core.py
│   └── test_utils.py
├── .gitignore
├── .pre-commit-config.yaml     # pre-commit 設定
├── CHANGELOG.md
├── LICENSE
├── README.md
└── pyproject.toml
```

---

## 【實作層】依賴管理

### 依賴版本約束策略

```text
版本約束類型：

精確版本（不推薦用於函式庫）：
└── requests==2.31.0

最小版本（推薦）：
└── requests>=2.28

相容版本（~= 運算子）：
└── requests~=2.28.0  # 等同於 >=2.28.0,<2.29.0

上限版本（謹慎使用）：
└── requests>=2.28,<3.0
```

### 函式庫 vs 應用程式的依賴策略

```text
函式庫（被其他專案依賴）：
├── 使用寬鬆的版本約束
├── 只指定最小版本
├── 不鎖定間接依賴
└── 讓使用者決定具體版本

dependencies = [
    "requests>=2.28",
    "click>=8.0",
]

應用程式（直接部署）：
├── 使用精確的版本鎖定
├── 鎖定所有間接依賴
├── 使用 lock 檔案
└── 確保可重現的環境

# 使用 Poetry/PDM 的 lock 檔案
# 或 pip-tools 的 requirements.txt
```

### 可選依賴（Optional Dependencies）

```toml
# pyproject.toml
[project.optional-dependencies]
# 開發依賴
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "ruff",
    "mypy",
]

# 文件依賴
docs = [
    "sphinx>=6.0",
    "sphinx-rtd-theme",
    "myst-parser",
]

# 特定功能
async = ["aiohttp>=3.8"]
cli = ["click>=8.0", "rich"]

# 全部安裝
all = [
    "my-package[async,cli]",
]
```

### 依賴更新策略

```text
定期更新流程：

1. 檢查過期依賴
   pip list --outdated
   # 或使用工具
   pip-audit  # 安全性檢查

2. 更新依賴
   # Poetry
   poetry update
   poetry update requests  # 更新特定套件

   # PDM
   pdm update

3. 執行測試
   pytest

4. 審查變更
   git diff pyproject.toml poetry.lock

5. 提交更新
   git commit -m "chore: update dependencies"
```

---

## 【實作層】品質保證

### 測試策略

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=my_package",
    "--cov-report=term-missing",
    "--cov-report=html",
]
markers = [
    "slow: marks tests as slow",
    "integration: marks integration tests",
]

[tool.coverage.run]
source = ["src/my_package"]
branch = true
parallel = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "@overload",
]
fail_under = 80
```

### 程式碼品質工具

```toml
# pyproject.toml

# Ruff（linter + formatter）
[tool.ruff]
line-length = 88
target-version = "py38"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "SIM", # flake8-simplify
    "RUF", # Ruff-specific rules
]
ignore = ["E501"]  # line too long（由 formatter 處理）

[tool.ruff.lint.isort]
known-first-party = ["my_package"]

# Mypy（型別檢查）
[tool.mypy]
python_version = "3.8"
strict = true
warn_return_any = true
warn_unused_ignores = true
show_error_codes = true

[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false
```

### Pre-commit 設定

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

```bash
# 安裝 pre-commit
pip install pre-commit
pre-commit install

# 手動執行
pre-commit run --all-files
```

---

## 【實作層】版本與變更管理

### 語義化版本實踐

```text
MAJOR.MINOR.PATCH

何時增加 MAJOR：
├── 移除已棄用的 API
├── 更改現有 API 的行為
├── 更改函式簽名（必要參數）
└── 不再支援舊版 Python

何時增加 MINOR：
├── 新增功能
├── 新增可選參數
├── 棄用現有 API（但不移除）
└── 效能改進

何時增加 PATCH：
├── 修復 bug
├── 安全性修補
├── 文件修正
└── 內部重構（不影響 API）
```

### CHANGELOG 格式

```markdown
# Changelog

本專案遵循 [Keep a Changelog](https://keepachangelog.com/) 格式。

## [Unreleased]

### Added
- 新功能描述

### Changed
- 變更描述

### Deprecated
- 棄用描述

### Removed
- 移除描述

### Fixed
- 修復描述

### Security
- 安全性修補描述

## [1.2.0] - 2025-01-15

### Added
- 新增 `process_async` 函式支援非同步處理 (#123)
- 新增 `Config` 類別用於設定管理

### Changed
- `process` 函式現在預設啟用快取

### Deprecated
- `old_function` 將在 2.0.0 移除，請使用 `new_function`

### Fixed
- 修復在 Windows 上的路徑處理問題 (#456)

## [1.1.0] - 2025-01-01
...

[Unreleased]: https://github.com/user/project/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/user/project/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/user/project/releases/tag/v1.1.0
```

### 自動化版本管理

```toml
# 使用 setuptools-scm
[build-system]
requires = ["setuptools>=61.0", "setuptools-scm>=8.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-package"
dynamic = ["version"]

[tool.setuptools_scm]
# 從 git tag 自動產生版本
# v1.0.0 → 1.0.0
# v1.0.0-5-g1234abc → 1.0.0.dev5+g1234abc
```

```bash
# 發布流程
git tag v1.2.0
git push --tags

# CI 自動建構並發布
```

---

## 【實作層】棄用策略

### 棄用流程

```text
棄用時間線（範例）：

v1.0: 引入 old_function
      │
v1.5: 引入 new_function
      標記 old_function 為棄用
      │
v1.6: old_function 發出棄用警告
v1.7: │
v1.8: │ 至少保留 2-3 個 minor 版本
      │
v2.0: 移除 old_function
```

### 實現棄用警告

```python
# my_package/deprecated.py
import warnings
from functools import wraps
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)

def deprecated(
    reason: str,
    version: str,
    replacement: str | None = None,
) -> Callable[[F], F]:
    """標記函式為棄用。

    Args:
        reason: 棄用原因
        version: 將移除的版本
        replacement: 替代方案

    Example:
        @deprecated(
            reason="使用新的 API",
            version="2.0.0",
            replacement="new_function",
        )
        def old_function():
            pass
    """

    def decorator(func: F) -> F:
        message = f"{func.__name__} 已棄用，將在 {version} 移除。{reason}"
        if replacement:
            message += f" 請使用 {replacement} 替代。"

        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                message,
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        # 更新 docstring
        wrapper.__doc__ = f".. deprecated:: {version}\n   {message}\n\n{func.__doc__ or ''}"

        return wrapper  # type: ignore

    return decorator

# 使用範例
@deprecated(
    reason="效能問題",
    version="2.0.0",
    replacement="process_v2",
)
def process_v1(data: list) -> list:
    """處理資料（舊版）。"""
    return [x * 2 for x in data]

def process_v2(data: list) -> list:
    """處理資料（新版，更高效）。"""
    # 新的實現
    return [x * 2 for x in data]
```

### 棄用類別屬性

```python
import warnings

class Config:
    def __init__(self):
        self._new_setting = "default"

    @property
    def old_setting(self) -> str:
        """已棄用，請使用 new_setting。"""
        warnings.warn(
            "old_setting 已棄用，將在 2.0.0 移除。請使用 new_setting。",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._new_setting

    @old_setting.setter
    def old_setting(self, value: str) -> None:
        warnings.warn(
            "old_setting 已棄用，將在 2.0.0 移除。請使用 new_setting。",
            DeprecationWarning,
            stacklevel=2,
        )
        self._new_setting = value

    @property
    def new_setting(self) -> str:
        """新的設定屬性。"""
        return self._new_setting

    @new_setting.setter
    def new_setting(self, value: str) -> None:
        self._new_setting = value
```

---

## 【實作層】向後相容性

### API 穩定性承諾

```text
API 穩定性等級：

Public API（穩定）：
├── 文件記載的函式和類別
├── __all__ 中導出的名稱
└── 遵循語義化版本

Internal API（不穩定）：
├── 以 _ 開頭的名稱
├── 未在文件中記載
└── 可能在任何版本變更

Experimental API：
├── 明確標記為實驗性
├── 可能在 minor 版本變更
└── 不保證向後相容
```

### 維護向後相容的技巧

```python
# 1. 新增可選參數時使用預設值
def process(data, *, new_option=None):  # 新增 new_option
    if new_option is not None:
        # 新行為
        pass
    # 舊行為保持不變

# 2. 使用 **kwargs 保持彈性
def create_client(host, port, **kwargs):
    # 未來可以新增參數而不破壞現有程式碼
    timeout = kwargs.get("timeout", 30)
    # ...

# 3. 提供相容層
def old_api(*args, **kwargs):
    """已棄用，請使用 new_api。"""
    warnings.warn("...", DeprecationWarning, stacklevel=2)
    # 轉換參數格式
    return new_api(*args, **kwargs)

# 4. 版本檢查
import sys

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias
```

---

## 【實作層】文件與社群

### 文件結構

```text
docs/
├── index.rst           # 首頁
├── installation.rst    # 安裝指南
├── quickstart.rst      # 快速開始
├── tutorial/           # 教學
│   ├── basics.rst
│   └── advanced.rst
├── api/                # API 參考
│   ├── index.rst
│   └── modules.rst
├── changelog.rst       # 變更日誌
└── contributing.rst    # 貢獻指南
```

### README 模板

```markdown
# My Package

[![PyPI version](https://badge.fury.io/py/my-package.svg)](https://pypi.org/project/my-package/)
[![Python versions](https://img.shields.io/pypi/pyversions/my-package.svg)](https://pypi.org/project/my-package/)
[![License](https://img.shields.io/pypi/l/my-package.svg)](https://github.com/user/my-package/blob/main/LICENSE)
[![CI](https://github.com/user/my-package/actions/workflows/ci.yml/badge.svg)](https://github.com/user/my-package/actions)
[![codecov](https://codecov.io/gh/user/my-package/branch/main/graph/badge.svg)](https://codecov.io/gh/user/my-package)

簡短描述這個套件做什麼。

## 特點

- 功能 1
- 功能 2
- 功能 3

## 安裝

\`\`\`bash
pip install my-package
\`\`\`

## 快速開始

\`\`\`python
from my_package import something

result = something.do_thing()
\`\`\`

## 文件

完整文件請見：https://my-package.readthedocs.io/

## 貢獻

歡迎貢獻！請見 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 授權

MIT License - 詳見 [LICENSE](LICENSE)
```

### Issue 與 PR 模板

```markdown
<!-- .github/ISSUE_TEMPLATE/bug_report.md -->
---
name: Bug 回報
about: 回報問題以協助改進
---

**描述問題**
清楚簡潔地描述問題。

**重現步驟**
1. ...
2. ...

**預期行為**
描述你期望的行為。

**環境**
- OS: [e.g., macOS 14.0]
- Python: [e.g., 3.11.0]
- Package version: [e.g., 1.2.0]

**額外資訊**
任何其他相關資訊。
```

---

## 【進階】維護者工作流程

### 發布檢查清單

```text
發布前檢查：

□ 所有測試通過
□ 程式碼覆蓋率達標
□ 型別檢查通過
□ 文件已更新
□ CHANGELOG 已更新
□ 版本號已更新
□ 無安全性漏洞（pip-audit）

發布步驟：

1. 更新 CHANGELOG
   - 將 [Unreleased] 內容移到新版本
   - 新增發布日期

2. 建立發布 commit
   git add CHANGELOG.md
   git commit -m "chore: prepare release v1.2.0"

3. 建立 tag
   git tag v1.2.0
   git push origin main --tags

4. CI 自動發布到 PyPI

5. 建立 GitHub Release
   - 使用 CHANGELOG 內容
   - 附上二進位檔案（如適用）

6. 宣布發布
   - 更新文件網站
   - 社群媒體/郵件列表
```

### 安全性維護

```bash
# 檢查已知漏洞
pip install pip-audit
pip-audit

# 檢查依賴更新
pip list --outdated

# 使用 Dependabot（GitHub）
# .github/dependabot.yml
```

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    commit-message:
      prefix: "chore(deps)"
    labels:
      - "dependencies"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

## 總結

### 最佳實踐清單

```text
專案結構：
✅ 使用 src layout
✅ 清楚的目錄組織
✅ 包含 py.typed 標記

依賴管理：
✅ 函式庫使用寬鬆版本
✅ 應用程式使用 lock 檔案
✅ 定期更新依賴

品質保證：
✅ 完整的測試覆蓋
✅ 型別提示和 mypy
✅ 使用 pre-commit

版本管理：
✅ 遵循語義化版本
✅ 維護 CHANGELOG
✅ 自動化版本號

向後相容：
✅ 清楚的棄用流程
✅ 至少 2-3 個版本的過渡期
✅ 明確的 API 穩定性承諾

文件與社群：
✅ 完整的 README
✅ API 文件
✅ 貢獻指南
```

---

## 思考題

1. 函式庫和應用程式的依賴管理策略為什麼不同？各有什麼優缺點？
2. 如何平衡「保持向後相容」和「改進 API 設計」的矛盾？
3. 開源專案的維護者應該如何處理安全性漏洞的披露？

## 實作練習

1. 為一個現有專案加入 pre-commit 設定，包含 ruff 和 mypy
2. 實作一個 `@deprecated` 裝飾器，並寫測試驗證警告訊息
3. 為一個開源專案撰寫完整的 CONTRIBUTING.md

## 延伸閱讀

- [Python Packaging User Guide](https://packaging.python.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [Scientific Python Development Guide](https://learn.scientific-python.org/development/)

---

*上一章：[發布到 PyPI](../distribution/)*
*返回：[模組六首頁](../)*
