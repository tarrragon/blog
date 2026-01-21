---
title: "案例：使用 Poetry 完整工作流"
date: 2026-01-21
description: "從專案建立到發布的 Poetry 完整工作流程"
weight: 2
---

# 案例：使用 Poetry 完整工作流

本案例展示如何使用 Poetry 管理現代 Python 專案的完整生命週期，從專案建立到套件發布。

## 先備知識

- [建構系統比較](../build-systems/)
- Python 虛擬環境基礎
- 套件相依性概念

## 問題背景

### 現代專案的挑戰

傳統的 Python 專案管理面臨以下問題：

```text
傳統工作流程的痛點：
├── 相依性管理
│   ├── requirements.txt 無法鎖定間接相依性
│   ├── pip freeze 產生的版本可能過於嚴格
│   └── 開發與生產環境相依性混在一起
├── 虛擬環境
│   ├── 需要手動建立和管理
│   ├── 不同專案的環境容易混淆
│   └── 缺乏與專案的關聯性
├── 建構與發布
│   ├── setup.py 設定複雜
│   ├── 發布流程需要多個工具
│   └── 版本管理不一致
└── 團隊協作
    ├── 環境難以重現
    ├── 「在我電腦上可以跑」問題
    └── 新成員上手困難
```

### 為什麼選擇 Poetry？

| 特性 | pip + venv | Poetry |
|------|------------|--------|
| 相依性鎖定 | 手動（pip freeze） | 自動（poetry.lock） |
| 間接相依性追蹤 | 無 | 完整追蹤 |
| 虛擬環境管理 | 手動 | 自動整合 |
| 建構系統 | 需要額外工具 | 內建 |
| 發布流程 | 需要 twine | 內建 |
| 相依性群組 | 無原生支援 | 完整支援 |

## 解決方案

### 安裝 Poetry

```bash
# 官方推薦的安裝方式（獨立安裝）
curl -sSL https://install.python-poetry.org | python3 -

# 或使用 pipx（推薦用於 CLI 工具）
pipx install poetry

# 確認安裝
poetry --version
```

**設定 Poetry：**

```bash
# 在專案目錄中建立虛擬環境（推薦）
poetry config virtualenvs.in-project true

# 查看所有設定
poetry config --list
```

### 工作流一：建立新專案

#### 使用 poetry new（完整專案結構）

```bash
# 建立新專案
poetry new my-awesome-lib

# 產生的目錄結構
my-awesome-lib/
├── pyproject.toml
├── README.md
├── my_awesome_lib/
│   └── __init__.py
└── tests/
    └── __init__.py
```

```bash
# 使用 src layout（推薦用於函式庫）
poetry new --src my-awesome-lib

# 產生的目錄結構
my-awesome-lib/
├── pyproject.toml
├── README.md
├── src/
│   └── my_awesome_lib/
│       └── __init__.py
└── tests/
    └── __init__.py
```

#### 使用 poetry init（現有專案）

```bash
# 在現有目錄初始化
cd existing-project
poetry init

# 互動式問答
# - Package name
# - Version
# - Description
# - Author
# - License
# - Python version
# - Dependencies
```

**互動式初始化範例：**

```text
This command will guide you through creating your pyproject.toml config.

Package name [existing-project]:  my-package
Version [0.1.0]:  1.0.0
Description []:  A useful Python package
Author [Your Name <you@example.com>, n to skip]:
License []:  MIT
Compatible Python versions [^3.10]:  ^3.10

Would you like to define your main dependencies interactively? (yes/no) [yes]
Search for package to add (or leave blank to continue): requests
...
```

### 工作流二：管理相依性

#### 新增相依性

```bash
# 新增生產相依性
poetry add requests
poetry add "httpx>=0.24"

# 新增開發相依性
poetry add pytest --group dev
poetry add ruff mypy --group dev

# 新增文件相依性
poetry add mkdocs mkdocs-material --group docs

# 新增可選相依性（extras）
poetry add pyyaml --optional
```

**pyproject.toml 的變化：**

```toml
[tool.poetry.dependencies]
python = "^3.10"
requests = "^2.31.0"
httpx = ">=0.24"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
ruff = "^0.4.0"
mypy = "^1.10.0"

[tool.poetry.group.docs.dependencies]
mkdocs = "^1.5.0"
mkdocs-material = "^9.5.0"

[tool.poetry.extras]
yaml = ["pyyaml"]
```

#### 移除相依性

```bash
# 移除生產相依性
poetry remove requests

# 移除開發相依性
poetry remove pytest --group dev
```

#### 更新相依性

```bash
# 更新所有相依性
poetry update

# 更新特定套件
poetry update requests

# 檢視可更新的套件
poetry show --outdated

# 檢視相依性樹
poetry show --tree
```

**相依性樹範例輸出：**

```text
requests 2.31.0 Python HTTP for Humans.
├── certifi >=2017.4.17
├── charset-normalizer >=2,<4
├── idna >=2.5,<4
└── urllib3 >=1.21.1,<3
```

### 工作流三：虛擬環境管理

#### 自動環境管理

```bash
# 安裝所有相依性（自動建立虛擬環境）
poetry install

# 僅安裝生產相依性
poetry install --only main

# 安裝包含特定群組
poetry install --with dev,docs

# 排除特定群組
poetry install --without docs

# 安裝 extras
poetry install --extras yaml
poetry install --all-extras
```

#### 環境操作

```bash
# 進入虛擬環境 shell
poetry shell

# 在虛擬環境中執行命令（不進入 shell）
poetry run python script.py
poetry run pytest
poetry run python -c "import my_package; print(my_package.__version__)"

# 顯示環境資訊
poetry env info

# 顯示環境路徑
poetry env info --path

# 列出所有環境
poetry env list

# 切換 Python 版本
poetry env use python3.11
poetry env use 3.12

# 刪除環境
poetry env remove python3.11
poetry env remove --all
```

**環境資訊範例輸出：**

```text
Virtualenv
Python:         3.11.6
Implementation: CPython
Path:           /path/to/project/.venv
Executable:     /path/to/project/.venv/bin/python
Valid:          True

Base
Platform:   darwin
OS:         posix
Python:     3.11.6
Path:       /opt/homebrew/Cellar/python@3.11/3.11.6/Frameworks/Python.framework/Versions/3.11
Executable: /opt/homebrew/Cellar/python@3.11/3.11.6/Frameworks/Python.framework/Versions/3.11/bin/python3.11
```

### 工作流四：建構與發布

#### 建構套件

```bash
# 建構 sdist 和 wheel
poetry build

# 僅建構 wheel
poetry build --format wheel

# 建構結果
dist/
├── my_package-1.0.0-py3-none-any.whl
└── my_package-1.0.0.tar.gz
```

#### 發布到 PyPI

```bash
# 設定 PyPI token
poetry config pypi-token.pypi pypi-XXXXXXXXXXXX

# 發布到 PyPI
poetry publish

# 建構並發布（一步完成）
poetry publish --build

# 發布到 TestPyPI
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi pypi-XXXXXXXXXXXX
poetry publish --repository testpypi
```

**版本管理：**

```bash
# 查看當前版本
poetry version

# 升級版本
poetry version patch   # 1.0.0 -> 1.0.1
poetry version minor   # 1.0.0 -> 1.1.0
poetry version major   # 1.0.0 -> 2.0.0

# 設定特定版本
poetry version 2.0.0

# 預發布版本
poetry version prepatch  # 1.0.0 -> 1.0.1a0
poetry version preminor  # 1.0.0 -> 1.1.0a0
poetry version premajor  # 1.0.0 -> 2.0.0a0
```

### 完整 pyproject.toml 範例

```toml
[build-system]
requires = ["poetry-core>=2.0"]
build-backend = "poetry.core.masonry.api"

[project]
name = "my-awesome-lib"
version = "1.0.0"
description = "A feature-rich Python library"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
keywords = ["python", "library", "utilities"]
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

[project.urls]
Homepage = "https://github.com/yourname/my-awesome-lib"
Documentation = "https://my-awesome-lib.readthedocs.io"
Repository = "https://github.com/yourname/my-awesome-lib.git"
Changelog = "https://github.com/yourname/my-awesome-lib/blob/main/CHANGELOG.md"

[project.scripts]
my-cli = "my_awesome_lib.cli:main"

[project.optional-dependencies]
yaml = ["pyyaml>=6.0"]
all = ["my-awesome-lib[yaml]"]

# ===== Poetry 特定設定 =====

[tool.poetry]
packages = [{ include = "my_awesome_lib", from = "src" }]

[tool.poetry.dependencies]
python = "^3.10"
requests = "^2.31"
click = "^8.1"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-cov = "^4.1"
pytest-asyncio = "^0.23"
mypy = "^1.10"
ruff = "^0.4"

[tool.poetry.group.docs]
optional = true

[tool.poetry.group.docs.dependencies]
mkdocs = "^1.5"
mkdocs-material = "^9.5"

# ===== 工具設定 =====

[tool.ruff]
src = ["src"]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP"]

[tool.mypy]
python_version = "3.10"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

## 與其他工具的比較

### Poetry vs pip

| 操作 | pip | Poetry |
|------|-----|--------|
| 安裝相依性 | `pip install -r requirements.txt` | `poetry install` |
| 新增相依性 | 手動編輯 requirements.txt | `poetry add package` |
| 鎖定版本 | `pip freeze > requirements.txt` | 自動更新 poetry.lock |
| 建立環境 | `python -m venv .venv` | 自動建立 |
| 執行命令 | `source .venv/bin/activate && python` | `poetry run python` |
| 建構套件 | `python -m build` | `poetry build` |
| 發布套件 | `twine upload dist/*` | `poetry publish` |

### Poetry vs setuptools

| 面向 | setuptools | Poetry |
|------|------------|--------|
| 設定格式 | pyproject.toml + 可能需要 setup.py | 僅 pyproject.toml |
| 相依性管理 | 需要額外工具 | 內建完整支援 |
| 環境管理 | 無 | 內建 |
| 學習曲線 | 較陡（歷史包袱） | 較平緩 |
| C 擴展支援 | 完整 | 不支援 |
| 生態系統 | 最廣泛 | 持續成長 |

### Poetry vs Hatch

| 面向 | Hatch | Poetry |
|------|-------|--------|
| 設計理念 | PEP 標準優先 | 使用者體驗優先 |
| 相依性鎖定 | 無內建 | 核心功能 |
| 環境管理 | 多環境（類似 tox） | 單一虛擬環境 |
| 腳本系統 | 完整 | 基本 |
| 建構後端 | hatchling | poetry-core |
| 適用場景 | 開源函式庫 | 應用程式、內部工具 |

## 實用技巧

### 技巧一：善用 Lock 檔案

```bash
# poetry.lock 的重要性
# - 記錄所有相依性的精確版本（包含間接相依性）
# - 確保團隊成員、CI/CD 使用相同版本
# - 應該提交到版本控制

# 根據 lock 檔案安裝（不更新）
poetry install --no-update

# 驗證 lock 檔案與 pyproject.toml 一致
poetry check --lock

# 匯出為 requirements.txt（部署用）
poetry export -f requirements.txt -o requirements.txt
poetry export -f requirements.txt --with dev -o requirements-dev.txt
poetry export --without-hashes -o requirements.txt
```

### 技巧二：善用相依性群組

```toml
# 開發相依性
[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
ruff = "^0.4"

# 可選群組（預設不安裝）
[tool.poetry.group.docs]
optional = true

[tool.poetry.group.docs.dependencies]
mkdocs = "^1.5"

# CI 專用群組
[tool.poetry.group.ci]
optional = true

[tool.poetry.group.ci.dependencies]
pytest-cov = "^4.1"
codecov = "^2.1"
```

```bash
# 安裝特定群組
poetry install --with docs
poetry install --with ci

# CI 環境中的安裝
poetry install --only main,ci
```

### 技巧三：善用 Extras

```toml
[project.optional-dependencies]
# 功能性 extras
yaml = ["pyyaml>=6.0"]
async = ["httpx>=0.24", "aiofiles>=23.0"]

# 完整安裝
all = ["my-package[yaml,async]"]
```

```bash
# 使用者安裝方式
pip install my-package           # 基本功能
pip install "my-package[yaml]"   # 包含 YAML 支援
pip install "my-package[all]"    # 所有功能
```

### 技巧四：本地相依性和 Git 相依性

```toml
[tool.poetry.dependencies]
# 本地路徑相依性
my-local-lib = { path = "../my-local-lib", develop = true }

# Git 相依性
my-git-lib = { git = "https://github.com/user/repo.git" }
my-git-lib = { git = "https://github.com/user/repo.git", branch = "develop" }
my-git-lib = { git = "https://github.com/user/repo.git", tag = "v1.0.0" }
my-git-lib = { git = "https://github.com/user/repo.git", rev = "abc123" }
```

### 技巧五：平台特定相依性

```toml
[tool.poetry.dependencies]
# 僅 Windows
pywin32 = { version = "^306", markers = "sys_platform == 'win32'" }

# 僅 Linux
uvloop = { version = "^0.19", markers = "sys_platform == 'linux'" }

# Python 版本限制
typing-extensions = { version = "^4.0", python = "<3.11" }
```

### 技巧六：Poetry 腳本

```toml
[tool.poetry.scripts]
my-cli = "my_package.cli:main"
my-tool = "my_package.tools:run"
```

```python
# src/my_package/cli.py
import click

@click.command()
@click.option("--name", default="World", help="Name to greet")
def main(name: str) -> None:
    """Greet someone."""
    click.echo(f"Hello, {name}!")

if __name__ == "__main__":
    main()
```

```bash
# 安裝後即可使用
my-cli --name Python
# 輸出：Hello, Python!
```

## 常見問題與解決

### 問題一：相依性解析衝突

```bash
# 錯誤訊息
SolverProblemError: ...

# 解決方法
# 1. 檢視衝突詳情
poetry show --tree

# 2. 放寬版本限制
poetry add "package>=1.0,<3.0"

# 3. 強制更新 lock 檔案
poetry lock --no-update
```

### 問題二：虛擬環境問題

```bash
# 重建虛擬環境
poetry env remove --all
poetry install

# 指定 Python 版本
poetry env use /usr/bin/python3.11
```

### 問題三：CI/CD 快取

```yaml
# GitHub Actions 範例
- name: Install Poetry
  uses: snok/install-poetry@v1
  with:
    virtualenvs-create: true
    virtualenvs-in-project: true

- name: Load cached venv
  uses: actions/cache@v4
  with:
    path: .venv
    key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}

- name: Install dependencies
  if: steps.cache.outputs.cache-hit != 'true'
  run: poetry install --no-interaction
```

## 設計權衡

| 面向 | 優點 | 缺點 |
|------|------|------|
| **相依性鎖定** | 環境可重現、團隊一致 | lock 檔案衝突、更新需謹慎 |
| **一體化工具** | 學習成本低、工作流統一 | 與其他工具整合需調整 |
| **虛擬環境整合** | 自動管理、不易混淆 | 自訂環境位置需設定 |
| **建構與發布** | 流程簡化 | 不支援 C 擴展 |

## 練習

### 基礎練習：建立 Poetry 專案

**目標**：使用 Poetry 建立一個簡單的專案

1. 使用 `poetry new --src my-utils` 建立專案
2. 新增 `requests` 作為生產相依性
3. 新增 `pytest` 和 `ruff` 作為開發相依性
4. 執行 `poetry install` 並驗證環境

### 進階練習：設定相依性群組

**目標**：建立完整的相依性管理結構

1. 建立 `dev`、`docs`、`ci` 三個群組
2. 將 `docs` 和 `ci` 設為可選群組
3. 練習使用 `--with` 和 `--without` 選項

### 挑戰題：完整發布流程

**目標**：將專案發布到 TestPyPI

1. 設定 TestPyPI repository
2. 使用 `poetry version` 管理版本
3. 執行 `poetry build` 建構套件
4. 執行 `poetry publish --repository testpypi` 發布

## 延伸閱讀

- [Poetry 官方文件](https://python-poetry.org/docs/)
- [Poetry CLI 參考](https://python-poetry.org/docs/cli/)
- [pyproject.toml 規範 (PEP 621)](https://peps.python.org/pep-0621/)
- [Python 打包使用者指南](https://packaging.python.org/)

---

*返回：[案例研究](../)*
