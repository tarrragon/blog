---
title: "案例：打包共用庫"
date: 2026-01-21
description: "將 .claude/lib 打包成可重用的 Python 套件"
weight: 1
---

# 案例：打包共用庫

本案例基於 `.claude/lib` 整體結構，展示如何將內部共用庫打包成可重用的 Python 套件。

## 先備知識

- [模組六：打包與發布](../../)
- Python 模組與套件基礎

## 問題背景

### 現有設計

`.claude/lib` 目錄結構：

```text
.claude/lib/
├── __init__.py              # Package entry point with version
├── config_loader.py         # YAML/JSON configuration loader
├── git_utils.py             # Git operations (branch, worktree)
├── hook_io.py               # Hook I/O standardization
├── hook_logging.py          # Logging system for hooks
├── hook_validator.py        # Hook compliance validator
├── markdown_link_checker.py # Markdown link validation
├── README.md                # API documentation
└── tests/                   # Unit tests
    ├── __init__.py
    ├── test_config_loader.py
    ├── test_git_utils.py
    ├── test_hook_io.py
    └── test_hook_logging.py
```

這是一個典型的內部工具庫，包含四個核心模組：

| 模組 | 功能 | 相依性 |
|------|------|--------|
| `config_loader` | YAML/JSON 配置載入 | PyYAML (optional) |
| `git_utils` | Git 命令執行與分支管理 | 無（使用 subprocess） |
| `hook_io` | Hook 輸入輸出標準化 | 無（使用標準庫） |
| `hook_logging` | 日誌系統設定 | 無（使用標準庫） |

### 現有限制

作為內部目錄的問題：

- **無法跨專案重用**：程式碼被鎖定在單一專案中
- **沒有版本管理**：無法追蹤 API 變更
- **無法透過 pip 安裝**：其他專案必須複製程式碼
- **相依性管理不明確**：PyYAML 是可選還是必要？

## 進階解決方案

### 設計目標

1. **建立標準的 Python 套件結構**
2. **使用 pyproject.toml 管理元資料**
3. **支援 pip install**
4. **建立 CI/CD 發布流程**

### 實作步驟

#### 步驟 1：重組目錄結構

從內部目錄結構轉換為標準的 **src layout**：

```text
claude-hooks-lib/
├── pyproject.toml           # Package metadata and build config
├── README.md                # Package documentation
├── LICENSE                  # License file (MIT recommended)
├── CHANGELOG.md             # Version history
├── src/
│   └── claude_hooks_lib/    # Package directory (underscore for import)
│       ├── __init__.py      # Public API exports
│       ├── config_loader.py
│       ├── git_utils.py
│       ├── hook_io.py
│       ├── hook_logging.py
│       ├── hook_validator.py
│       └── py.typed         # PEP 561 marker for type hints
└── tests/
    ├── __init__.py
    ├── conftest.py          # Pytest fixtures
    ├── test_config_loader.py
    ├── test_git_utils.py
    ├── test_hook_io.py
    └── test_hook_logging.py
```

**為什麼選擇 src layout？**

```text
# Flat layout (不推薦用於套件發布)
my-package/
├── my_package/          # Package 直接在根目錄
│   └── __init__.py
└── tests/

# Src layout (推薦)
my-package/
├── src/
│   └── my_package/      # Package 在 src/ 下
│       └── __init__.py
└── tests/
```

| 特性 | Flat Layout | Src Layout |
|------|-------------|------------|
| 測試環境 | 可能意外導入本地版本 | 強制安裝後測試 |
| 套件發布 | 容易遺漏檔案 | 明確的套件邊界 |
| 複雜度 | 較低 | 稍高 |
| 推薦場景 | 簡單專案、應用程式 | 套件發布、函式庫 |

#### 步驟 2：建立 pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "claude-hooks-lib"
version = "0.28.0"
description = "Shared utilities for Claude Code hooks"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Your Name", email = "your.email@example.com" }
]
keywords = ["claude", "hooks", "utilities", "git"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
]

# Core dependencies (minimal)
dependencies = []

[project.optional-dependencies]
# YAML support
yaml = ["PyYAML>=6.0"]

# Development dependencies
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.4",
]

# All optional features
all = ["claude-hooks-lib[yaml]"]

[project.urls]
Homepage = "https://github.com/yourname/claude-hooks-lib"
Documentation = "https://github.com/yourname/claude-hooks-lib#readme"
Repository = "https://github.com/yourname/claude-hooks-lib.git"
Changelog = "https://github.com/yourname/claude-hooks-lib/blob/main/CHANGELOG.md"

[project.scripts]
# Command-line entry points
hook-validator = "claude_hooks_lib.hook_validator:main"

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests",
]

[tool.hatch.build.targets.wheel]
packages = ["src/claude_hooks_lib"]
```

**關鍵設定說明：**

1. **build-system**：使用 Hatch 作為建構後端（現代、快速）
2. **requires-python**：指定最低 Python 版本
3. **dependencies**：核心相依性保持為空（僅使用標準庫）
4. **optional-dependencies**：將 PyYAML 設為可選
5. **project.scripts**：定義命令列工具入口點

#### 步驟 3：處理相依性

相依性分層策略：

```toml
[project]
# 核心相依性：僅標準庫
dependencies = []

[project.optional-dependencies]
# 功能性相依性（用戶根據需求安裝）
yaml = ["PyYAML>=6.0"]

# 開發相依性（僅開發者需要）
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.4",
]

# 測試相依性（CI/CD 需要）
test = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
]

# 文件相依性
docs = [
    "mkdocs>=1.5",
    "mkdocs-material>=9.0",
]

# 完整安裝
all = [
    "claude-hooks-lib[yaml,dev,docs]",
]
```

**安裝方式範例：**

```bash
# 基本安裝（無可選相依性）
pip install claude-hooks-lib

# 包含 YAML 支援
pip install "claude-hooks-lib[yaml]"

# 開發者安裝
pip install -e ".[dev]"

# 完整安裝
pip install "claude-hooks-lib[all]"
```

#### 步驟 4：版本管理策略

**方法 A：單一來源版本（推薦）**

在 `__init__.py` 中定義版本：

```python
# src/claude_hooks_lib/__init__.py
"""
Claude Hooks Library

Shared utilities for building Claude Code hooks.
"""

__version__ = "0.28.0"
__all__ = [
    # Version
    "__version__",
    # git_utils
    "run_git_command",
    "get_current_branch",
    "get_project_root",
    "get_worktree_list",
    "is_protected_branch",
    "is_allowed_branch",
    # hook_logging
    "setup_hook_logging",
    # hook_io
    "read_hook_input",
    "write_hook_output",
    "create_pretooluse_output",
    "create_posttooluse_output",
    # config_loader
    "load_config",
    "load_agents_config",
    "load_quality_rules",
    "clear_config_cache",
]

from .git_utils import (
    run_git_command,
    get_current_branch,
    get_project_root,
    get_worktree_list,
    is_protected_branch,
    is_allowed_branch,
)

from .hook_logging import setup_hook_logging

from .hook_io import (
    read_hook_input,
    write_hook_output,
    create_pretooluse_output,
    create_posttooluse_output,
)

from .config_loader import (
    load_config,
    load_agents_config,
    load_quality_rules,
    clear_config_cache,
)
```

在 `pyproject.toml` 中使用動態版本：

```toml
[project]
name = "claude-hooks-lib"
dynamic = ["version"]

[tool.hatch.version]
path = "src/claude_hooks_lib/__init__.py"
```

**方法 B：使用 hatch-vcs（Git tag 版本）**

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/claude_hooks_lib/_version.py"
```

```bash
# Create version tag
git tag v0.28.0
git push --tags
```

#### 步驟 5：建立發布流程

**.github/workflows/publish.yml**：

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

permissions:
  contents: read
  id-token: write  # Required for trusted publishing

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install build tools
        run: |
          python -m pip install --upgrade pip
          pip install build

      - name: Build package
        run: python -m build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev,yaml]"

      - name: Run tests
        run: pytest tests/ -v --cov=src/claude_hooks_lib

      - name: Type check
        run: mypy src/claude_hooks_lib

  publish-testpypi:
    needs: [build, test]
    runs-on: ubuntu-latest
    environment: testpypi
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to TestPyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

  publish-pypi:
    needs: [publish-testpypi]
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

**CI 測試工作流程（.github/workflows/test.yml）**：

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.10", "3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev,yaml]"

      - name: Lint with ruff
        run: ruff check src/ tests/

      - name: Format check with ruff
        run: ruff format --check src/ tests/

      - name: Type check with mypy
        run: mypy src/claude_hooks_lib

      - name: Run tests with coverage
        run: |
          pytest tests/ -v --cov=src/claude_hooks_lib --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
```

### 完整程式碼

**完整的 pyproject.toml：**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "claude-hooks-lib"
dynamic = ["version"]
description = "Shared utilities for Claude Code hooks"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Your Name", email = "your.email@example.com" }
]
keywords = ["claude", "hooks", "utilities", "git", "automation"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

dependencies = []

[project.optional-dependencies]
yaml = ["PyYAML>=6.0"]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.4",
    "PyYAML>=6.0",
]
docs = [
    "mkdocs>=1.5",
    "mkdocs-material>=9.0",
]
all = ["claude-hooks-lib[yaml,dev,docs]"]

[project.urls]
Homepage = "https://github.com/yourname/claude-hooks-lib"
Documentation = "https://github.com/yourname/claude-hooks-lib#readme"
Repository = "https://github.com/yourname/claude-hooks-lib.git"
Changelog = "https://github.com/yourname/claude-hooks-lib/blob/main/CHANGELOG.md"

[project.scripts]
hook-validator = "claude_hooks_lib.hook_validator:main"

# ===== Build Configuration =====

[tool.hatch.version]
path = "src/claude_hooks_lib/__init__.py"

[tool.hatch.build.targets.sdist]
include = ["/src", "/tests", "/README.md", "/LICENSE"]

[tool.hatch.build.targets.wheel]
packages = ["src/claude_hooks_lib"]

# ===== Tool Configuration =====

[tool.ruff]
src = ["src"]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.ruff.lint.isort]
known-first-party = ["claude_hooks_lib"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
strict = true

[[tool.mypy.overrides]]
module = "yaml"
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["src/claude_hooks_lib"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

### 使用範例

**安裝套件：**

```bash
# From PyPI (after publishing)
pip install claude-hooks-lib

# With YAML support
pip install "claude-hooks-lib[yaml]"

# Development installation (from source)
git clone https://github.com/yourname/claude-hooks-lib
cd claude-hooks-lib
pip install -e ".[dev]"
```

**Python 使用範例：**

```python
# Basic usage
from claude_hooks_lib import (
    get_current_branch,
    is_protected_branch,
    setup_hook_logging,
    read_hook_input,
    write_hook_output,
    create_pretooluse_output,
)

# Initialize logging
logger = setup_hook_logging("my-custom-hook")

# Check branch protection
branch = get_current_branch()
if branch and is_protected_branch(branch):
    logger.warning(f"Operating on protected branch: {branch}")

# Process hook input
input_data = read_hook_input()
tool_name = input_data.get("tool_name", "")

# Generate output
output = create_pretooluse_output(
    decision="allow",
    reason="All checks passed"
)
write_hook_output(output)
```

**命令列工具使用：**

```bash
# Validate a single hook
hook-validator .claude/hooks/my-hook.py

# Validate all hooks
hook-validator --all

# Output as JSON
hook-validator --all --json

# Strict mode (warnings as errors)
hook-validator --all --strict
```

## 設計權衡

| 面向 | 內部目錄 | 獨立套件 |
|------|----------|----------|
| **重用性** | 僅限單專案 | 跨專案共用 |
| **版本管理** | 與專案綁定 | 獨立語意化版本 |
| **維護成本** | 低（無發布流程） | 中（需維護 CI/CD） |
| **相依管理** | 隱式（需手動追蹤） | 顯式（pyproject.toml） |
| **安裝方式** | 複製程式碼或 sys.path | pip install |
| **測試隔離** | 可能測試到本地版本 | 強制測試安裝版本 |
| **API 穩定性** | 無保證 | 版本號約束 |

### 專案結構比較

| Layout | 適用場景 | 優點 | 缺點 |
|--------|----------|------|------|
| **Flat Layout** | 簡單應用、腳本 | 簡單直覺 | 測試可能導入錯誤版本 |
| **Src Layout** | 函式庫、套件發布 | 測試隔離、明確邊界 | 額外一層目錄 |

### 建構工具比較

| 工具 | 特點 | 推薦場景 |
|------|------|----------|
| **setuptools** | 成熟穩定、生態最大 | 需要相容舊專案 |
| **Hatch** | 現代、快速、功能完整 | 新專案首選 |
| **Poetry** | 依賴鎖定、虛擬環境管理 | 需要嚴格依賴控制 |
| **Flit** | 極簡、僅純 Python | 簡單函式庫 |

## 什麼時候該打包成套件？

**適合打包：**

- 多個專案需要使用相同程式碼
- 程式碼相對穩定，API 不常變動
- 需要版本控制和變更追蹤
- 希望其他人能 pip install 使用
- 需要明確的相依性管理

**不建議打包：**

- 僅單一專案使用
- 程式碼還在快速迭代
- 與專案緊密耦合（如特定的配置路徑）
- 維護成本超過重用收益

**決策流程圖：**

```text
程式碼需要跨專案使用？
├── 否 → 保持內部目錄
└── 是 → API 穩定嗎？
         ├── 否 → 等待穩定後再打包
         └── 是 → 有維護能力嗎？
                  ├── 否 → 考慮 monorepo
                  └── 是 → 打包發布
```

## 練習

### 基礎練習：建立最小的 pyproject.toml

**目標**：為一個簡單的工具函式庫建立 pyproject.toml

```python
# src/my_utils/__init__.py
"""Simple utilities."""

__version__ = "0.1.0"

def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"
```

**要求**：
1. 使用 hatchling 作為建構後端
2. 設定專案名稱、版本、描述
3. 指定 Python 版本要求（>=3.10）

<details>
<summary>參考答案</summary>

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-utils"
version = "0.1.0"
description = "Simple utility functions"
requires-python = ">=3.10"

[tool.hatch.build.targets.wheel]
packages = ["src/my_utils"]
```

</details>

### 進階練習：新增 optional dependencies

**目標**：擴展上面的套件，加入可選的功能

**要求**：
1. 新增一個需要 `requests` 的函式
2. 將 `requests` 設為可選相依性
3. 加入開發相依性（pytest, ruff）

<details>
<summary>參考答案</summary>

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-utils"
version = "0.1.0"
description = "Simple utility functions"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
http = ["requests>=2.28"]
dev = [
    "pytest>=8.0",
    "ruff>=0.4",
    "my-utils[http]",  # Include http for testing
]

[tool.hatch.build.targets.wheel]
packages = ["src/my_utils"]
```

```python
# src/my_utils/http.py
"""HTTP utilities (requires requests)."""

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

def fetch_json(url: str) -> dict:
    """Fetch JSON from URL."""
    if not HAS_REQUESTS:
        raise ImportError(
            "requests is required for this feature. "
            "Install with: pip install my-utils[http]"
        )
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
```

</details>

### 挑戰題：設定 GitHub Actions 自動發布到 PyPI

**目標**：建立完整的 CI/CD 流程

**要求**：
1. Pull Request 時執行測試
2. 建立 Release 時自動發布到 PyPI
3. 使用 Trusted Publishing（不需要 API Token）
4. 多版本 Python 測試矩陣

**提示**：
- 需要在 PyPI 設定 Trusted Publisher
- 使用 `pypa/gh-action-pypi-publish@release/v1`
- 設定 `id-token: write` 權限

<details>
<summary>參考答案</summary>

1. 先在 PyPI 設定 Trusted Publisher：
   - 前往 https://pypi.org/manage/account/publishing/
   - 新增 GitHub publisher
   - 填入 repository owner、name、workflow 路徑

2. 建立工作流程檔案：

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: ruff check src/ tests/
      - run: pytest tests/ -v
```

```yaml
# .github/workflows/publish.yml
name: Publish

on:
  release:
    types: [published]

permissions:
  contents: read
  id-token: write

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

</details>

## 延伸閱讀

- [Python 打包使用者指南](https://packaging.python.org/)
- [pyproject.toml 規範 (PEP 621)](https://peps.python.org/pep-0621/)
- [Hatch 建置工具](https://hatch.pypa.io/)
- [Trusted Publishers (PyPI)](https://docs.pypi.org/trusted-publishers/)

---

*返回：[模組六：打包與發布](../../)*
