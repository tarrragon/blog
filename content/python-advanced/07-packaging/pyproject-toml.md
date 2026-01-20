---
title: "6.1 pyproject.toml 完整指南"
date: 2026-01-20
description: "理解現代 Python 套件的設定標準"
weight: 1
---

# pyproject.toml 完整指南

本章介紹 pyproject.toml 的結構與設定方式。

## 本章目標

學完本章後，你將能夠：

1. 理解 pyproject.toml 的三個主要表
2. 設定專案元數據（PEP 621）
3. 設定建構系統（PEP 518）

---

## 【原理層】pyproject.toml 的演進

### 歷史背景

```text
Python 打包的演進：
├── 2000s: setup.py（純 Python 腳本）
├── 2010s: setup.cfg（宣告式設定）
├── 2016: PEP 518（pyproject.toml 誕生）
├── 2020: PEP 621（標準化元數據）
└── 2025: pyproject.toml 成為主流標準
```

### 為什麼需要 pyproject.toml？

```text
setup.py 的問題：
├── 需要執行程式碼才能讀取元數據
├── 安全風險（任意程式碼執行）
├── 無法標準化建構依賴
└── 不同工具使用不同設定檔

pyproject.toml 的優點：
├── 靜態設定，不需執行
├── 標準化格式（TOML）
├── 統一的設定位置
└── 支援多種建構後端
```

### 相關 PEP

| PEP | 內容 | 狀態 |
|-----|------|------|
| PEP 518 | build-system 表 | 已採納 |
| PEP 621 | project 元數據 | 已採納 |
| PEP 639 | license 欄位改進 | 已採納 |
| PEP 660 | 可編輯安裝 | 已採納 |
| PEP 735 | 依賴群組 | 草案中 |

---

## 【設計層】三個主要表

### 檔案結構總覽

```toml
# pyproject.toml 的三個主要表

[build-system]
# 定義如何建構套件
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
# 定義套件的元數據
name = "my-package"
version = "1.0.0"
# ...

[tool.xxx]
# 各種工具的設定
# [tool.setuptools], [tool.pytest], [tool.ruff], etc.
```

### [build-system]：建構設定

```toml
[build-system]
# 建構時需要的套件（PEP 518）
requires = [
    "setuptools>=61.0",
    "wheel",
    # 如果有 C 擴展
    # "cython>=3.0",
]

# 建構後端（PEP 517）
build-backend = "setuptools.build_meta"

# 選用：後端路徑（較少使用）
# backend-path = ["."]
```

常見的建構後端：

```text
建構後端                     requires
─────────────────────────────────────────────────────
setuptools.build_meta       ["setuptools>=61.0"]
flit_core.buildapi          ["flit_core>=3.4"]
hatchling.build             ["hatchling"]
poetry.core.masonry.api     ["poetry-core>=1.0.0"]
maturin                     ["maturin>=1.5"]
scikit_build_core.build     ["scikit-build-core>=0.5"]
mesonpy                     ["meson-python"]
```

### [project]：專案元數據

```toml
[project]
# === 必填欄位 ===
name = "my-awesome-package"
version = "1.0.0"

# === 基本資訊 ===
description = "A short description of the package"
readme = "README.md"  # 或 {file = "README.md", content-type = "text/markdown"}
license = {text = "MIT"}  # 或 {file = "LICENSE"}
requires-python = ">=3.8"

# === 作者資訊 ===
authors = [
    {name = "Your Name", email = "you@example.com"},
]
maintainers = [
    {name = "Maintainer", email = "maintainer@example.com"},
]

# === 分類與關鍵字 ===
keywords = ["example", "package", "demo"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

# === URL ===
[project.urls]
Homepage = "https://github.com/user/project"
Documentation = "https://project.readthedocs.io"
Repository = "https://github.com/user/project"
Changelog = "https://github.com/user/project/blob/main/CHANGELOG.md"

# === 依賴 ===
dependencies = [
    "requests>=2.28",
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "ruff",
    "mypy",
]
docs = [
    "sphinx>=6.0",
    "sphinx-rtd-theme",
]

# === 入口點 ===
[project.scripts]
my-cli = "my_package.cli:main"

[project.gui-scripts]
my-gui = "my_package.gui:main"

[project.entry-points."my_package.plugins"]
plugin1 = "my_package.plugins.plugin1:Plugin"
```

### [tool.xxx]：工具設定

```toml
# === setuptools 設定 ===
[tool.setuptools]
packages = ["my_package"]
# 或使用自動發現
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
my_package = ["*.json", "data/*"]

# === pytest 設定 ===
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=my_package"

# === ruff 設定 ===
[tool.ruff]
line-length = 88
target-version = "py38"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP"]
ignore = ["E501"]

# === mypy 設定 ===
[tool.mypy]
python_version = "3.8"
strict = true
warn_return_any = true

# === coverage 設定 ===
[tool.coverage.run]
source = ["my_package"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
]
```

---

## 【實作層】完整範例

### 最小可行設定

```toml
# 最小的 pyproject.toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-package"
version = "0.1.0"
```

### 標準函式庫風格

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-package"
version = "1.0.0"
description = "A well-documented Python package"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.8"
authors = [{name = "Your Name", email = "you@example.com"}]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Typing :: Typed",
]
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff", "mypy"]

[project.urls]
Homepage = "https://github.com/user/my-package"
Repository = "https://github.com/user/my-package"

[tool.setuptools.packages.find]
where = ["src"]
```

### 含 CLI 的應用程式

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-cli-tool"
version = "2.0.0"
description = "A powerful CLI tool"
readme = "README.md"
license = {text = "Apache-2.0"}
requires-python = ">=3.9"
authors = [{name = "CLI Team"}]
dependencies = [
    "click>=8.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-cov"]

[project.scripts]
my-tool = "my_cli_tool.main:cli"

[project.urls]
Homepage = "https://my-cli-tool.dev"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
my_cli_tool = ["templates/*.txt", "config/*.yaml"]
```

---

## 【進階】動態欄位

### 動態版本

```toml
[project]
name = "my-package"
dynamic = ["version"]  # 版本由其他來源決定

[tool.setuptools.dynamic]
version = {attr = "my_package.__version__"}
# 或從檔案讀取
# version = {file = "VERSION"}
```

```python
# src/my_package/__init__.py
__version__ = "1.2.3"
```

### 動態依賴

```toml
[project]
name = "my-package"
dynamic = ["dependencies", "optional-dependencies"]

[tool.setuptools.dynamic]
dependencies = {file = ["requirements.txt"]}
optional-dependencies.dev = {file = ["requirements-dev.txt"]}
```

### 使用 setuptools-scm（Git 標籤版本）

```toml
[build-system]
requires = ["setuptools>=61.0", "setuptools-scm>=8.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-package"
dynamic = ["version"]

[tool.setuptools_scm]
# 版本從 git tag 自動產生
# v1.0.0 -> 1.0.0
# v1.0.0-2-gabcdef -> 1.0.0.dev2+gabcdef
```

---

## 【實作層】專案結構對應

### Flat Layout

```text
my-package/
├── pyproject.toml
├── README.md
├── my_package/
│   ├── __init__.py
│   └── module.py
└── tests/
    └── test_module.py
```

```toml
[tool.setuptools]
packages = ["my_package"]
```

### Src Layout（推薦）

```text
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

```toml
[tool.setuptools.packages.find]
where = ["src"]
```

### 為什麼推薦 src layout？

```text
Src Layout 的優點：
├── 避免匯入本地未安裝的套件
├── 強制測試已安裝的版本
├── 清楚區分原始碼和專案根目錄
└── 避免名稱衝突
```

---

## 【進階】PEP 639 授權條款

### 新的 license 語法

```toml
# PEP 639（Python 3.14+，但建構工具已支援）

# SPDX 表示法
[project]
license = "MIT"
# 或
license = "Apache-2.0 OR MIT"
# 或
license = "GPL-3.0-only"

# 授權檔案
license-files = ["LICENSE", "LICENSES/*"]
```

### 常見的 SPDX 識別碼

```text
識別碼              完整名稱
─────────────────────────────────────────
MIT                 MIT License
Apache-2.0          Apache License 2.0
GPL-3.0-only        GNU GPL v3.0 only
GPL-3.0-or-later    GNU GPL v3.0 or later
BSD-3-Clause        BSD 3-Clause License
BSD-2-Clause        BSD 2-Clause License
MPL-2.0             Mozilla Public License 2.0
LGPL-3.0-only       GNU LGPL v3.0 only
ISC                 ISC License
Unlicense           The Unlicense
```

---

## 【驗證】檢查設定

### 使用 validate-pyproject

```bash
pip install validate-pyproject

# 驗證 pyproject.toml
validate-pyproject pyproject.toml
```

### 使用 build 測試建構

```bash
pip install build

# 建構套件（會驗證設定）
python -m build

# 建構結果
ls dist/
# my_package-1.0.0.tar.gz
# my_package-1.0.0-py3-none-any.whl
```

### 常見錯誤

```text
錯誤：Unknown key in [project]
原因：使用了非標準欄位
解決：檢查 PEP 621 允許的欄位

錯誤：Invalid version
原因：版本格式不符合 PEP 440
解決：使用正確格式，如 "1.0.0", "1.0.0a1", "1.0.0.dev1"

錯誤：Missing required key
原因：缺少必填欄位
解決：至少要有 name 和 version（或 dynamic）
```

---

## 思考題

1. 為什麼 Python 社群花了這麼長時間才標準化打包設定？
2. `[build-system]` 中的 `requires` 和 `[project]` 中的 `dependencies` 有什麼區別？
3. 動態欄位在什麼情況下有用？有什麼潛在問題？

## 實作練習

1. 將一個使用 setup.py 的舊專案遷移到 pyproject.toml
2. 建立一個包含 CLI 入口點的套件，並在本地測試安裝
3. 使用 setuptools-scm 設定自動版本管理

## 延伸閱讀

- [PEP 518 - build-system](https://peps.python.org/pep-0518/)
- [PEP 621 - project metadata](https://peps.python.org/pep-0621/)
- [PEP 639 - license](https://peps.python.org/pep-0639/)
- [Python Packaging Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)

---

*下一章：[建構系統比較](../build-systems/)*
