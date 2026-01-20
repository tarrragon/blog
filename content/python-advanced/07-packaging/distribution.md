---
title: "6.3 發布到 PyPI"
description: "學習如何建構 wheel 並發布到 PyPI"
weight: 3
---

# 發布到 PyPI

本章介紹如何將套件發布到 PyPI。

## 本章目標

學完本章後，你將能夠：

1. 建構 sdist 和 wheel
2. 使用 twine 上傳到 PyPI
3. 設定 CI/CD 自動發布

---

## 【原理層】套件分發格式

### sdist vs wheel

```text
sdist（Source Distribution）：
├── 格式：.tar.gz
├── 內容：原始碼 + pyproject.toml
├── 安裝時需要建構
├── 可能需要編譯器（C 擴展）
└── 作為備用方案

wheel（Built Distribution）：
├── 格式：.whl（實際上是 zip）
├── 內容：已編譯的套件
├── 安裝時直接解壓
├── 不需要編譯器
└── 安裝速度快
```

### wheel 命名規則

```text
{distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl

範例：
my_package-1.0.0-py3-none-any.whl
├── my_package: 套件名稱
├── 1.0.0: 版本
├── py3: Python 3
├── none: 無特定 ABI
└── any: 任何平台

numpy-1.26.0-cp311-cp311-manylinux_2_17_x86_64.whl
├── numpy: 套件名稱
├── 1.26.0: 版本
├── cp311: CPython 3.11
├── cp311: CPython 3.11 ABI
└── manylinux_2_17_x86_64: Linux x86_64
```

### 常見的 platform tag

```text
純 Python：
├── py3-none-any（Python 3，任何平台）
├── py2.py3-none-any（Python 2 和 3）

有 C 擴展：
├── cp311-cp311-manylinux_2_17_x86_64
├── cp311-cp311-macosx_11_0_arm64
├── cp311-cp311-win_amd64

使用 abi3（穩定 ABI）：
└── cp38-abi3-manylinux_2_17_x86_64
```

---

## 【實作層】建構套件

### 使用 build 工具

```bash
# 安裝 build
pip install build

# 建構 sdist 和 wheel
python -m build

# 只建構 wheel
python -m build --wheel

# 只建構 sdist
python -m build --sdist

# 建構結果
ls dist/
# my_package-1.0.0.tar.gz     (sdist)
# my_package-1.0.0-py3-none-any.whl  (wheel)
```

### 檢查建構結果

```bash
# 安裝 twine
pip install twine

# 檢查套件
twine check dist/*

# 檢查 wheel 內容
unzip -l dist/my_package-1.0.0-py3-none-any.whl

# 或使用 wheel 工具
pip install wheel
wheel unpack dist/my_package-1.0.0-py3-none-any.whl
```

### 測試安裝

```bash
# 在新的虛擬環境中測試
python -m venv test_env
source test_env/bin/activate

# 從本地檔案安裝
pip install dist/my_package-1.0.0-py3-none-any.whl

# 測試匯入
python -c "import my_package; print(my_package.__version__)"

# 清理
deactivate
rm -rf test_env
```

---

## 【實作層】發布到 PyPI

### 註冊帳號

```text
1. 前往 https://pypi.org/account/register/
2. 建立帳號並驗證 email
3. 啟用雙因素認證（強烈建議）
4. 建立 API Token
   - Account Settings → API tokens → Add API token
   - Scope: Entire account（首次）或特定專案
   - 複製 token（只會顯示一次）
```

### 設定認證

```bash
# 方法 1：使用 .pypirc 檔案
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-xxxxxxxxxxxx

[testpypi]
username = __token__
password = pypi-xxxxxxxxxxxx
EOF

# 設定檔案權限
chmod 600 ~/.pypirc

# 方法 2：使用環境變數
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxxxxxxxxx

# 方法 3：使用 keyring
pip install keyring
keyring set https://upload.pypi.org/legacy/ __token__
```

### 發布到 TestPyPI（測試）

```bash
# TestPyPI 是 PyPI 的測試環境
# 用於在正式發布前測試

# 註冊 TestPyPI 帳號
# https://test.pypi.org/account/register/

# 上傳到 TestPyPI
twine upload --repository testpypi dist/*

# 從 TestPyPI 安裝測試
pip install --index-url https://test.pypi.org/simple/ my-package
```

### 發布到 PyPI

```bash
# 確認一切就緒
twine check dist/*

# 上傳
twine upload dist/*

# 或指定檔案
twine upload dist/my_package-1.0.0*

# 驗證
pip install my-package
```

### 使用其他工具發布

```bash
# Poetry
poetry publish

# Hatch
hatch publish

# Flit
flit publish

# Maturin（Rust 擴展）
maturin publish
```

---

## 【實作層】版本管理

### 語義化版本

```text
MAJOR.MINOR.PATCH

範例：1.2.3
├── MAJOR (1): 不相容的 API 變更
├── MINOR (2): 新增功能，向後相容
└── PATCH (3): 修復 bug，向後相容

預發布版本：
├── 1.0.0a1  (alpha)
├── 1.0.0b1  (beta)
├── 1.0.0rc1 (release candidate)

開發版本：
├── 1.0.0.dev1
├── 1.0.0.post1 (post-release)
```

### PEP 440 版本格式

```text
合法的版本號：
├── 1.0
├── 1.0.0
├── 1.0.0a1
├── 1.0.0b2
├── 1.0.0rc1
├── 1.0.0.dev1
├── 1.0.0.post1
└── 1.0.0+local

不合法（會被正規化）：
├── 1.0.0-alpha1 → 1.0.0a1
├── v1.0.0 → 1.0.0
└── 1.0.0.RELEASE → 1.0.0
```

### 自動版本管理

```bash
# 使用 setuptools-scm
# 從 git tag 自動產生版本

# 安裝
pip install setuptools-scm

# pyproject.toml 設定
# [tool.setuptools_scm]

# 建立 tag
git tag v1.0.0
git push --tags

# 建構（版本自動從 tag 取得）
python -m build

# 使用 hatch
hatch version minor  # 1.0.0 → 1.1.0
hatch version patch  # 1.1.0 → 1.1.1

# 使用 poetry
poetry version minor
poetry version patch
```

---

## 【實作層】CI/CD 自動發布

### GitHub Actions

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install build tools
        run: pip install build twine

      - name: Build package
        run: python -m build

      - name: Check package
        run: twine check dist/*

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish-testpypi:
    needs: build
    runs-on: ubuntu-latest
    environment: testpypi
    permissions:
      id-token: write  # 用於 Trusted Publishing
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to TestPyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

  publish-pypi:
    needs: [build, publish-testpypi]
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

### Trusted Publishing（推薦）

```text
Trusted Publishing：
├── 不需要儲存 API token
├── 使用 OIDC（OpenID Connect）
├── 更安全的發布方式
└── GitHub Actions 原生支援

設定步驟：
1. 在 PyPI 專案設定中新增 Publisher
2. 選擇 GitHub Actions
3. 填入 repository 和 workflow 資訊
4. 在 workflow 中使用 id-token: write
```

在 PyPI 設定 Trusted Publisher：

```text
PyPI → Your Project → Settings → Publishing

新增 publisher：
├── Owner: your-github-username
├── Repository: your-repo-name
├── Workflow name: publish.yml
└── Environment name: pypi (選填)
```

### 完整的 CI/CD 流程

```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
  release:
    types: [published]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run tests
        run: pytest --cov

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # 完整 history（用於 setuptools-scm）

      - name: Build
        run: |
          pip install build
          python -m build

      - name: Upload
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    if: github.event_name == 'release'
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - uses: pypa/gh-action-pypi-publish@release/v1
```

---

## 【進階】多平台 wheel 建構

### 使用 cibuildwheel

```yaml
# .github/workflows/wheels.yml
name: Build wheels

on:
  release:
    types: [published]

jobs:
  build_wheels:
    name: Build wheels on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-13, macos-14]

    steps:
      - uses: actions/checkout@v4

      - name: Build wheels
        uses: pypa/cibuildwheel@v2.17
        env:
          # 建構 Python 3.9-3.12
          CIBW_BUILD: cp39-* cp310-* cp311-* cp312-*
          # 跳過 32-bit 和 musl
          CIBW_SKIP: "*-win32 *-manylinux_i686 *-musllinux*"
          # 測試命令
          CIBW_TEST_COMMAND: pytest {project}/tests

      - uses: actions/upload-artifact@v4
        with:
          name: wheels-${{ matrix.os }}
          path: ./wheelhouse/*.whl

  build_sdist:
    name: Build source distribution
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build sdist
        run: |
          pip install build
          python -m build --sdist

      - uses: actions/upload-artifact@v4
        with:
          name: sdist
          path: dist/*.tar.gz

  publish:
    needs: [build_wheels, build_sdist]
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: wheels-*
          merge-multiple: true
          path: dist/

      - uses: actions/download-artifact@v4
        with:
          name: sdist
          path: dist/

      - uses: pypa/gh-action-pypi-publish@release/v1
```

### cibuildwheel 設定

```toml
# pyproject.toml
[tool.cibuildwheel]
# 建構的 Python 版本
build = "cp39-* cp310-* cp311-* cp312-*"

# 跳過的組合
skip = [
    "*-win32",
    "*-manylinux_i686",
    "*-musllinux*",
]

# 測試設定
test-command = "pytest {project}/tests"
test-requires = "pytest"

# 環境變數
[tool.cibuildwheel.environment]
MY_VAR = "value"

# 平台特定設定
[tool.cibuildwheel.linux]
archs = ["x86_64", "aarch64"]
manylinux-x86_64-image = "manylinux2014"

[tool.cibuildwheel.macos]
archs = ["x86_64", "arm64"]

[tool.cibuildwheel.windows]
archs = ["AMD64"]
```

---

## 【常見問題】疑難排解

### 上傳失敗

```text
問題：HTTPError 403 Forbidden
原因：認證失敗
解決：
1. 確認 token 正確
2. 確認使用 __token__ 作為使用者名稱
3. 確認 token 的 scope 包含該專案

問題：File already exists
原因：該版本已經上傳過
解決：
1. 升級版本號
2. PyPI 不允許覆蓋已發布的版本

問題：Invalid distribution file
原因：套件格式錯誤
解決：
1. 執行 twine check dist/*
2. 確認 pyproject.toml 設定正確
```

### 安裝問題

```text
問題：No matching distribution found
原因：沒有相容的 wheel
解決：
1. 確認有發布 sdist
2. 確認有對應平台的 wheel
3. 檢查 requires-python 設定

問題：Could not build wheels
原因：建構失敗（通常是 C 擴展）
解決：
1. 安裝編譯器（gcc, MSVC）
2. 安裝 python-dev 套件
3. 提供預編譯的 wheel
```

---

## 思考題

1. 為什麼 PyPI 不允許刪除或覆蓋已發布的版本？
2. Trusted Publishing 相比 API token 有什麼優勢？
3. 在什麼情況下應該同時發布 sdist 和 wheel？

## 實作練習

1. 建立一個簡單套件並發布到 TestPyPI
2. 設定 GitHub Actions 自動發布流程
3. 使用 cibuildwheel 建構多平台 wheel

## 延伸閱讀

- [PyPI 官方文件](https://pypi.org/help/)
- [Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [cibuildwheel](https://cibuildwheel.readthedocs.io/)
- [gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish)

---

*上一章：[建構系統比較](../build-systems/)*
*下一章：[最佳實踐](../best-practices/)*
