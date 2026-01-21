---
title: "案例：使用 Hatch 完整工作流"
date: 2026-01-21
description: "從專案建立到發布的 Hatch 實戰指南"
weight: 3
---

# 案例：使用 Hatch 完整工作流

本案例展示如何使用 Hatch 這個 PyPA 推薦的現代 Python 專案管理工具，完成從專案建立到發布的完整流程。

## 先備知識

- [6.2 建構系統比較](../../build-systems/)
- Python 虛擬環境基礎
- 基本的命令列操作

## 問題背景

### Hatch 是什麼？

Hatch 是由 PyPA（Python Packaging Authority）成員開發維護的現代 Python 專案管理工具，整合了：

```text
Hatch 功能整合：
├── 專案腳手架（hatch new）
├── 環境管理（類似 tox + virtualenv）
├── 版本管理（自動更新版本號）
├── 建構系統（hatchling）
└── 發布工具（hatch publish）
```

### 為什麼選擇 Hatch？

| 優勢 | 說明 |
|------|------|
| **標準優先** | 完全遵循 PEP 517/518/621 標準 |
| **一站式工具** | 不需要額外安裝 tox、virtualenv、bump2version |
| **快速建構** | hatchling 建構速度優於 setuptools |
| **環境矩陣** | 內建多 Python 版本測試支援 |
| **腳本系統** | 定義可重用的專案腳本 |

## 完整工作流

### 第一步：安裝 Hatch

```bash
# 使用 pip 安裝
pip install hatch

# 或使用 pipx（推薦，隔離安裝）
pipx install hatch

# 驗證安裝
hatch --version
```

### 第二步：建立新專案

```bash
# 建立新專案
hatch new my-awesome-lib

# 互動式建立（可自訂選項）
hatch new my-awesome-lib --init

# 建立應用程式專案（非函式庫）
hatch new --cli my-cli-app
```

**預設專案結構：**

```text
my-awesome-lib/
├── src/
│   └── my_awesome_lib/
│       ├── __init__.py
│       └── __about__.py      # 版本資訊
├── tests/
│   └── __init__.py
├── pyproject.toml
├── README.md
└── LICENSE.txt
```

**生成的 pyproject.toml：**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-awesome-lib"
dynamic = ["version"]
description = ''
readme = "README.md"
requires-python = ">=3.8"
license = "MIT"
keywords = []
authors = [
  { name = "Your Name", email = "you@example.com" },
]
classifiers = [
  "Development Status :: 4 - Beta",
  "Programming Language :: Python",
  "Programming Language :: Python :: 3.8",
  "Programming Language :: Python :: 3.9",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
]
dependencies = []

[project.urls]
Documentation = "https://github.com/yourname/my-awesome-lib#readme"
Issues = "https://github.com/yourname/my-awesome-lib/issues"
Source = "https://github.com/yourname/my-awesome-lib"

[tool.hatch.version]
path = "src/my_awesome_lib/__about__.py"
```

### 第三步：環境管理（hatch env）

#### 定義環境

```toml
# pyproject.toml

# 預設環境
[tool.hatch.envs.default]
dependencies = [
  "pytest",
  "pytest-cov",
]

[tool.hatch.envs.default.scripts]
test = "pytest {args:tests}"
test-cov = "pytest --cov=my_awesome_lib --cov-report=term-missing {args:tests}"

# Lint 環境
[tool.hatch.envs.lint]
dependencies = [
  "ruff>=0.4",
  "mypy>=1.0",
]

[tool.hatch.envs.lint.scripts]
check = [
  "ruff check src tests",
  "ruff format --check src tests",
]
fix = [
  "ruff check --fix src tests",
  "ruff format src tests",
]
typing = "mypy src"
all = ["check", "typing"]

# 文件環境
[tool.hatch.envs.docs]
dependencies = [
  "mkdocs>=1.5",
  "mkdocs-material>=9.0",
]

[tool.hatch.envs.docs.scripts]
build = "mkdocs build"
serve = "mkdocs serve"
```

#### 使用環境

```bash
# 顯示所有環境
hatch env show

# 執行預設環境的腳本
hatch run test
hatch run test-cov

# 執行特定環境的腳本
hatch run lint:check
hatch run lint:fix
hatch run lint:typing

# 進入環境 shell
hatch shell

# 進入特定環境
hatch shell lint

# 移除環境
hatch env remove
hatch env remove lint

# 清除所有環境
hatch env prune
```

### 第四步：版本管理（hatch version）

#### 設定版本來源

**方法 A：從檔案讀取版本**

```toml
[tool.hatch.version]
path = "src/my_awesome_lib/__about__.py"
```

```python
# src/my_awesome_lib/__about__.py
__version__ = "0.1.0"
```

**方法 B：從 Git 標籤讀取版本（推薦用於開源專案）**

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/my_awesome_lib/_version.py"
```

#### 版本操作

```bash
# 顯示當前版本
hatch version

# 設定特定版本
hatch version 1.0.0

# 語意化版本升級
hatch version patch   # 0.1.0 → 0.1.1
hatch version minor   # 0.1.1 → 0.2.0
hatch version major   # 0.2.0 → 1.0.0

# 預發布版本
hatch version alpha   # 1.0.0 → 1.0.1a0
hatch version beta    # 1.0.1a0 → 1.0.1b0
hatch version rc      # 1.0.1b0 → 1.0.1rc0
hatch version release # 1.0.1rc0 → 1.0.1

# 開發版本
hatch version dev     # 1.0.0 → 1.0.1.dev0
```

### 第五步：建構與發布

#### 建構套件

```bash
# 建構 wheel 和 sdist
hatch build

# 只建構 wheel
hatch build --target wheel

# 只建構 sdist
hatch build --target sdist

# 清除建構產物後重建
hatch build --clean
```

**建構產物：**

```text
dist/
├── my_awesome_lib-0.1.0-py3-none-any.whl
└── my_awesome_lib-0.1.0.tar.gz
```

#### 發布套件

```bash
# 發布到 PyPI（需要設定認證）
hatch publish

# 發布到 TestPyPI
hatch publish --repo test

# 指定發布的檔案
hatch publish dist/my_awesome_lib-0.1.0-py3-none-any.whl
```

**設定 PyPI 認證：**

```bash
# 設定 PyPI token
hatch config set pypi.auth.username __token__
hatch config set pypi.auth.password pypi-xxxxx

# 或使用環境變數
export HATCH_INDEX_USER=__token__
export HATCH_INDEX_AUTH=pypi-xxxxx
```

## pyproject.toml 的 Hatch 特定設定

### [tool.hatch.build] 建構設定

```toml
[tool.hatch.build]
# 包含的檔案（支援 glob）
include = [
  "src/my_awesome_lib",
  "README.md",
]

# 排除的檔案
exclude = [
  "*.pyc",
  "__pycache__",
  ".git",
]

# 是否可重現建構
reproducible = true

# 開發模式設定
dev-mode-dirs = ["src"]

[tool.hatch.build.targets.sdist]
# 原始碼發布設定
include = [
  "/src",
  "/tests",
  "/README.md",
  "/LICENSE.txt",
]

[tool.hatch.build.targets.wheel]
# Wheel 發布設定
packages = ["src/my_awesome_lib"]

# 只包含特定平台
# only-include = ["my_awesome_lib"]
```

### [tool.hatch.envs] 環境設定

```toml
[tool.hatch.envs.default]
# 相依性
dependencies = ["pytest"]

# 額外安裝的 features
features = ["yaml"]

# 環境變數
[tool.hatch.envs.default.env-vars]
PYTHONPATH = "src"
LOG_LEVEL = "DEBUG"

# 腳本定義
[tool.hatch.envs.default.scripts]
test = "pytest {args}"

# 平台特定設定
[tool.hatch.envs.default.overrides]
platform.windows.scripts = [
  'test = "pytest --no-header {args}"',
]
```

### [tool.hatch.version] 版本設定

```toml
# 從檔案讀取
[tool.hatch.version]
path = "src/my_awesome_lib/__about__.py"
pattern = "^__version__ = ['\"](?P<version>[^'\"]+)['\"]"

# 從 VCS 讀取
[tool.hatch.version]
source = "vcs"
raw-options = { local_scheme = "no-local-version" }

[tool.hatch.build.hooks.vcs]
version-file = "src/my_awesome_lib/_version.py"
```

### [tool.hatch.metadata] 元資料設定

```toml
[tool.hatch.metadata]
# 允許直接依賴（通常應該避免）
allow-direct-references = false

# 動態讀取 README
[tool.hatch.metadata.hooks.fancy-pypi-readme]
content-type = "text/markdown"

[[tool.hatch.metadata.hooks.fancy-pypi-readme.fragments]]
path = "README.md"
```

## 與 Poetry 的比較

### 設計理念差異

```text
Hatch：
├── 遵循 PEP 標準優先
├── 環境管理內建
├── 不提供依賴鎖定
├── 建構系統（hatchling）可獨立使用
└── 設定完全在 [tool.hatch]

Poetry：
├── 自有生態系統
├── 強調依賴鎖定（poetry.lock）
├── 虛擬環境管理
├── poetry.core 可獨立使用
└── 混合 [project] 和 [tool.poetry]
```

### 功能對照

| 功能 | Hatch | Poetry |
|------|-------|--------|
| 依賴鎖定 | 不支援 | poetry.lock |
| 環境管理 | 內建矩陣支援 | 單一環境 |
| PEP 621 | 完全支援 | Poetry 2.0 支援 |
| 腳本系統 | 強大（環境分離） | 基本 |
| 版本管理 | 內建 bump | 需外掛或手動 |
| 插件系統 | 支援 | 支援 |

### pyproject.toml 比較

**Hatch 風格：**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "1.0.0"
dependencies = ["requests>=2.28"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.hatch.envs.default]
features = ["dev"]
```

**Poetry 風格（2.0）：**

```toml
[build-system]
requires = ["poetry-core>=2.0"]
build-backend = "poetry.core.masonry.api"

[project]
name = "my-package"
version = "1.0.0"
dependencies = ["requests>=2.28"]

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
```

### 選擇建議

```text
選擇 Hatch：
├── 開發 Python 函式庫
├── 需要多環境測試
├── 偏好標準優先
└── 不需要依賴鎖定

選擇 Poetry：
├── 開發應用程式
├── 需要嚴格的依賴鎖定
├── 團隊習慣 Poetry 工作流
└── 需要與現有 Poetry 專案整合
```

## 實用技巧

### 多環境測試矩陣

```toml
# 定義多 Python 版本測試
[tool.hatch.envs.test]
dependencies = ["pytest", "pytest-cov"]

[[tool.hatch.envs.test.matrix]]
python = ["3.9", "3.10", "3.11", "3.12", "3.13"]

[tool.hatch.envs.test.scripts]
run = "pytest {args:tests}"
cov = "pytest --cov=my_awesome_lib {args:tests}"
```

```bash
# 在所有矩陣環境執行測試
hatch run test:run

# 在特定版本執行
hatch run +py=3.12 test:run

# 顯示矩陣環境
hatch env show --ascii
```

### 複合腳本

```toml
[tool.hatch.envs.default.scripts]
# 單一命令
test = "pytest {args:tests}"

# 多命令（依序執行）
ci = [
  "ruff check src tests",
  "pytest --cov",
  "mypy src",
]

# 呼叫其他腳本
all = ["lint:check", "test:cov"]

# 帶預設參數
lint = "ruff check {args:.}"
```

### 環境繼承

```toml
# 基礎環境
[tool.hatch.envs.base]
dependencies = ["pytest"]

# 繼承基礎環境
[tool.hatch.envs.coverage]
template = "base"
dependencies = ["pytest-cov"]

[tool.hatch.envs.coverage.scripts]
run = "pytest --cov {args:tests}"
```

### 條件依賴

```toml
[tool.hatch.envs.default]
dependencies = [
  "pytest",
]

# 根據平台新增依賴
[tool.hatch.envs.default.overrides]
platform.linux.dependencies = ["pytest-xdist"]
platform.darwin.dependencies = ["pytest-xdist"]

# 根據 Python 版本
python.3.8.dependencies = ["typing-extensions"]
```

### 自訂建構 Hook

```toml
[tool.hatch.build.hooks.custom]
# 建構前執行
path = "hatch_build.py"
```

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # 建構前的自訂邏輯
        print(f"Building version {version}")
```

## 完整範例：CLI 應用程式

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-cli"
dynamic = ["version"]
description = "A useful CLI tool"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
dependencies = [
  "click>=8.0",
  "rich>=13.0",
]

[project.scripts]
my-cli = "my_cli.main:app"

[project.optional-dependencies]
yaml = ["PyYAML>=6.0"]

[tool.hatch.version]
path = "src/my_cli/__about__.py"

[tool.hatch.build.targets.wheel]
packages = ["src/my_cli"]

# ===== 環境設定 =====

[tool.hatch.envs.default]
dependencies = [
  "pytest>=8.0",
  "pytest-cov>=4.0",
]

[tool.hatch.envs.default.scripts]
test = "pytest {args:tests}"
cov = "pytest --cov=my_cli --cov-report=term-missing {args:tests}"

[tool.hatch.envs.lint]
dependencies = [
  "ruff>=0.4",
  "mypy>=1.0",
]

[tool.hatch.envs.lint.scripts]
check = ["ruff check src tests", "ruff format --check src tests"]
fix = ["ruff check --fix src tests", "ruff format src tests"]
typing = "mypy src"
all = ["check", "typing"]

[[tool.hatch.envs.test.matrix]]
python = ["3.10", "3.11", "3.12", "3.13"]

# ===== 工具設定 =====

[tool.ruff]
src = ["src"]
line-length = 88

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP"]

[tool.mypy]
python_version = "3.10"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

## 發布檢查清單

```text
發布前檢查：
├── [ ] hatch run lint:all 通過
├── [ ] hatch run test:run 在所有 Python 版本通過
├── [ ] hatch version 更新版本號
├── [ ] 更新 CHANGELOG.md
├── [ ] hatch build 建構成功
├── [ ] 在虛擬環境測試安裝：pip install dist/*.whl
├── [ ] hatch publish --repo test 發布到 TestPyPI
├── [ ] 從 TestPyPI 測試安裝
└── [ ] hatch publish 發布到 PyPI
```

## 延伸閱讀

- [Hatch 官方文件](https://hatch.pypa.io/)
- [Hatchling 建構後端](https://hatch.pypa.io/latest/plugins/build-hook/reference/)
- [PEP 621 - pyproject.toml 元資料](https://peps.python.org/pep-0621/)
- [Python 打包使用者指南](https://packaging.python.org/)

---

*返回：[案例研究](../)*
