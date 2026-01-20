---
title: "6.2 建構系統比較"
description: "比較 setuptools、Poetry、Hatch 等建構系統"
weight: 2
---

# 建構系統比較

本章比較主流的 Python 套件建構系統。

## 本章目標

學完本章後，你將能夠：

1. 理解不同建構系統的設計理念
2. 根據專案需求選擇適合的工具
3. 在不同工具之間遷移

---

## 【總覽】建構系統生態

### 建構後端 vs 建構前端

```text
建構前端（Frontend）：使用者互動的工具
├── pip
├── build
└── 各工具的 CLI（poetry, hatch, etc.）

建構後端（Backend）：實際執行建構的程式
├── setuptools.build_meta
├── flit_core.buildapi
├── hatchling.build
├── poetry.core.masonry.api
└── maturin, scikit-build-core, mesonpy
```

### 主流工具比較

| 工具 | 定位 | 特點 | 適用場景 |
|------|------|------|----------|
| setuptools | 建構後端 | 歷史最久，功能最全 | 一般專案、C 擴展 |
| Flit | 建構後端 | 極簡設計 | 純 Python 小型專案 |
| Hatch | 全套工具 | 現代設計，環境管理 | 新專案 |
| Poetry | 全套工具 | 依賴鎖定，虛擬環境 | 應用程式開發 |
| PDM | 全套工具 | PEP 582，快速 | 實驗性專案 |

---

## 【工具一】setuptools

### 特點與定位

```text
setuptools：
├── Python 打包的「標準」
├── 歷史最悠久（2004 年開始）
├── 支援所有功能（C 擴展、資料檔案等）
├── 學習曲線較陡
└── PEP 621 支援（61.0.0+ 版本）
```

### 基本設定

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-package"
version = "1.0.0"
dependencies = ["requests"]

[tool.setuptools.packages.find]
where = ["src"]
```

### 進階設定

```toml
[tool.setuptools]
# 明確指定套件
packages = ["my_package", "my_package.submodule"]

# 包含資料檔案
package-data = {"my_package" = ["*.json", "data/*"]}

# 排除檔案
exclude-package-data = {"my_package" = ["test_*"]}

# Zip 安全（是否可以作為 zip 檔案匯入）
zip-safe = false

[tool.setuptools.dynamic]
version = {attr = "my_package.__version__"}
readme = {file = ["README.md"]}
```

### C 擴展支援

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0", "cython>=3.0"]
build-backend = "setuptools.build_meta"
```

```python
# setup.py（仍需要用於複雜的 C 擴展）
from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        "my_package.fast_module",
        ["src/my_package/fast_module.pyx"],
    )
]

setup(
    ext_modules=cythonize(extensions),
)
```

### 常用命令

```bash
# 建構
python -m build

# 可編輯安裝
pip install -e .

# 開發模式（含額外依賴）
pip install -e ".[dev]"
```

---

## 【工具二】Flit

### 特點與定位

```text
Flit：
├── 極簡設計
├── 只支援純 Python 套件
├── 不支援 C 擴展
├── 快速建構
└── 適合簡單函式庫
```

### 基本設定

```toml
# pyproject.toml
[build-system]
requires = ["flit_core>=3.4"]
build-backend = "flit_core.buildapi"

[project]
name = "my-package"
version = "1.0.0"
description = "A simple package"
authors = [{name = "Your Name", email = "you@example.com"}]
dependencies = ["requests"]

# Flit 自動從 __init__.py 讀取 docstring 和 version
# 所以常常不需要設定 description 和 version
```

```python
# src/my_package/__init__.py
"""A simple package for doing things."""
__version__ = "1.0.0"
```

### 常用命令

```bash
# 安裝 flit
pip install flit

# 建構
flit build

# 發布
flit publish

# 可編輯安裝
flit install --symlink  # Unix
flit install --pth-file # Windows
```

### 限制

```text
Flit 不支援：
├── C/C++/Rust 擴展
├── 複雜的建構腳本
├── 資料檔案的細粒度控制
├── 動態版本（需要在 __init__.py 中定義）
└── 依賴鎖定
```

---

## 【工具三】Hatch

### 特點與定位

```text
Hatch：
├── 現代化設計
├── 環境管理（類似 tox）
├── 版本管理
├── 腳本系統
├── PEP 標準優先
└── 由 PyPA 成員維護
```

### 基本設定

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "1.0.0"
dependencies = ["requests"]

[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]

[tool.hatch.build.targets.sdist]
include = ["/src", "/tests"]
```

### 環境管理

```toml
# 定義環境
[tool.hatch.envs.default]
dependencies = ["pytest", "pytest-cov"]

[tool.hatch.envs.default.scripts]
test = "pytest {args:tests}"
cov = "pytest --cov=my_package {args:tests}"

[tool.hatch.envs.lint]
dependencies = ["ruff", "mypy"]

[tool.hatch.envs.lint.scripts]
check = ["ruff check .", "mypy src"]
fix = "ruff check --fix ."

[tool.hatch.envs.docs]
dependencies = ["sphinx", "sphinx-rtd-theme"]

[tool.hatch.envs.docs.scripts]
build = "sphinx-build -b html docs docs/_build"
```

### 版本管理

```toml
[tool.hatch.version]
path = "src/my_package/__init__.py"

# 或使用 hatch-vcs 從 git 標籤讀取
# [tool.hatch.version]
# source = "vcs"
#
# [tool.hatch.build.hooks.vcs]
# version-file = "src/my_package/_version.py"
```

### 常用命令

```bash
# 安裝 hatch
pip install hatch

# 建立新專案
hatch new my-package

# 執行腳本
hatch run test
hatch run lint:check

# 進入環境 shell
hatch shell

# 版本管理
hatch version        # 顯示當前版本
hatch version minor  # 升級 minor 版本
hatch version 2.0.0  # 設定特定版本

# 建構
hatch build

# 發布
hatch publish
```

---

## 【工具四】Poetry

### 特點與定位

```text
Poetry：
├── 依賴解析與鎖定
├── 虛擬環境管理
├── 發布流程整合
├── 自己的設定格式（[tool.poetry]）
├── Poetry 2.0 支援 [project] 表
└── 適合應用程式開發
```

### 基本設定（Poetry 2.0+）

```toml
# pyproject.toml（Poetry 2.0 風格）
[build-system]
requires = ["poetry-core>=2.0"]
build-backend = "poetry.core.masonry.api"

[project]
name = "my-package"
version = "1.0.0"
description = "My awesome package"
authors = [{name = "Your Name", email = "you@example.com"}]
dependencies = ["requests>=2.28"]
requires-python = ">=3.8"

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff"]

# Poetry 特定設定仍在 [tool.poetry]
[tool.poetry]
packages = [{include = "my_package", from = "src"}]

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
ruff = "^0.1"
```

### 傳統設定（Poetry 1.x）

```toml
# pyproject.toml（舊風格，仍支援）
[tool.poetry]
name = "my-package"
version = "1.0.0"
description = "My awesome package"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.8"
requests = "^2.28"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
ruff = "^0.1"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

### 依賴鎖定

```bash
# poetry.lock 檔案
# - 記錄所有依賴的精確版本
# - 確保團隊成員使用相同版本
# - 應該提交到版本控制

# 安裝（使用 lock 檔案）
poetry install

# 更新依賴
poetry update

# 新增依賴
poetry add requests
poetry add pytest --group dev

# 移除依賴
poetry remove requests
```

### 常用命令

```bash
# 安裝 poetry
pip install poetry
# 或官方推薦的安裝方式
curl -sSL https://install.python-poetry.org | python3 -

# 建立新專案
poetry new my-package
poetry init  # 在現有目錄初始化

# 虛擬環境
poetry env use python3.11
poetry shell  # 進入虛擬環境

# 執行命令
poetry run python script.py
poetry run pytest

# 建構與發布
poetry build
poetry publish

# 設定 PyPI token
poetry config pypi-token.pypi <your-token>
```

---

## 【工具五】PDM

### 特點與定位

```text
PDM：
├── 支援 PEP 582（__pypackages__）
├── 快速的依賴解析
├── 支援 PEP 621
├── 插件系統
└── 實驗性功能多
```

### 基本設定

```toml
# pyproject.toml
[build-system]
requires = ["pdm-backend"]
build-backend = "pdm.backend"

[project]
name = "my-package"
version = "1.0.0"
dependencies = ["requests"]

[tool.pdm]
distribution = true

[tool.pdm.dev-dependencies]
dev = ["pytest", "ruff"]
```

### 常用命令

```bash
# 安裝 pdm
pip install pdm

# 初始化專案
pdm init

# 依賴管理
pdm add requests
pdm add -d pytest  # 開發依賴
pdm remove requests
pdm update

# 執行
pdm run python script.py
pdm run pytest

# 建構
pdm build
pdm publish
```

---

## 【選擇指南】決策流程

### 決策樹

```text
需要選擇建構系統？
│
├── 需要 C/Rust 擴展？
│   ├── 是 → setuptools + Cython/pybind11
│   │        或 maturin（Rust）
│   └── 否 ↓
│
├── 需要依賴鎖定？
│   ├── 是 → Poetry 或 PDM
│   └── 否 ↓
│
├── 需要環境管理？
│   ├── 是 → Hatch 或 Poetry
│   └── 否 ↓
│
├── 極簡專案？
│   ├── 是 → Flit
│   └── 否 → setuptools 或 Hatch
```

### 場景建議

```text
場景                         推薦工具
─────────────────────────────────────────────────────
純 Python 函式庫             Flit 或 Hatch
Web 應用程式                 Poetry
資料科學專案                 Poetry 或 PDM
有 C 擴展的函式庫            setuptools
Rust 擴展                    Maturin
開源專案（多貢獻者）         Hatch 或 setuptools
內部工具                     Poetry
```

### 遷移考量

```text
從 setup.py 遷移：
├── 純 Python → 任何工具都可以
├── 有 C 擴展 → setuptools（保留部分 setup.py）
└── 複雜建構 → 保持 setuptools

從 Poetry 1.x 遷移到 2.0：
├── 更新 poetry-core 版本
├── 可選：將 [tool.poetry.dependencies] 移到 [project]
└── 測試建構和安裝

工具之間遷移：
├── 所有現代工具都支援 PEP 621
├── 主要差異在 [tool.xxx] 設定
└── 依賴鎖定檔案不相容
```

---

## 【比較】功能對照表

### 核心功能

| 功能 | setuptools | Flit | Hatch | Poetry |
|------|------------|------|-------|--------|
| PEP 621 | ✅ | ✅ | ✅ | ✅ (2.0) |
| C 擴展 | ✅ | ❌ | ❌ | ❌ |
| 環境管理 | ❌ | ❌ | ✅ | ✅ |
| 依賴鎖定 | ❌ | ❌ | ❌ | ✅ |
| 腳本系統 | ❌ | ❌ | ✅ | ✅ |
| 版本管理 | ⚠️ | ❌ | ✅ | ✅ |
| 插件系統 | ✅ | ❌ | ✅ | ✅ |

### 效能比較

```text
建構速度（純 Python 專案）：
Flit > Hatch > Poetry > setuptools

依賴解析速度：
PDM > Poetry > pip

安裝速度：
pip + lock file > Poetry > PDM
```

---

## 思考題

1. 為什麼 Python 社群有這麼多打包工具？這是好事還是壞事？
2. 依賴鎖定對函式庫和應用程式的重要性有什麼不同？
3. 如果要開始一個新的開源專案，你會選擇哪個工具？為什麼？

## 實作練習

1. 用 setuptools、Flit、Hatch 三種工具建立相同的簡單套件，比較設定檔的差異
2. 使用 Poetry 建立一個有依賴鎖定的專案，模擬團隊協作場景
3. 將一個現有的 setup.py 專案遷移到 pyproject.toml

## 延伸閱讀

- [Python Packaging User Guide](https://packaging.python.org/)
- [Hatch 官方文件](https://hatch.pypa.io/)
- [Poetry 官方文件](https://python-poetry.org/docs/)
- [Flit 官方文件](https://flit.pypa.io/)

---

*上一章：[pyproject.toml 完整指南](../pyproject-toml/)*
*下一章：[發布到 PyPI](../distribution/)*
