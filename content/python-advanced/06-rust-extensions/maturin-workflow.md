---
title: "5.3 Maturin 開發流程"
description: "使用 Maturin 建構和發布 Rust Python 套件"
weight: 3
---

# Maturin 開發流程

本章介紹 Maturin，Rust Python 套件的建構工具。

## 本章目標

學完本章後，你將能夠：

1. 設定 Maturin 專案
2. 使用 maturin develop 快速迭代
3. 建構跨平台 wheel 並發布到 PyPI

---

## 【原理層】Maturin 是什麼？

### 建構工具的角色

```text
傳統 Python 擴展建構：
├── setuptools + setup.py
├── 複雜的編譯器設定
├── 手動處理連結問題
└── 跨平台建構困難

Maturin 提供：
├── 一鍵建構 Rust Python 套件
├── 自動處理 PyO3 設定
├── 跨平台 wheel 生成
├── 與 pyproject.toml 整合
└── 開發模式快速迭代
```

### 支援的專案類型

```text
Maturin 支援：
├── pyo3：純 Rust 擴展（最常用）
├── cffi：生成 cffi 綁定
├── uniffi：跨語言綁定
└── bin：Rust 二進位程式打包
```

---

## 【設計層】專案設定

### 安裝 Maturin

```bash
# 使用 pip
pip install maturin

# 使用 pipx（推薦，隔離環境）
pipx install maturin

# 使用 cargo
cargo install maturin

# 驗證安裝
maturin --version
```

### 建立新專案

```bash
# 互動式建立
maturin new my_rust_module
cd my_rust_module

# 或者指定綁定類型
maturin new my_rust_module --bindings pyo3

# 專案結構
my_rust_module/
├── Cargo.toml
├── pyproject.toml
├── src/
│   └── lib.rs
└── python/
    └── my_rust_module/
        └── __init__.py  # 選用
```

### pyproject.toml 設定

```toml
[build-system]
requires = ["maturin>=1.5,<2.0"]
build-backend = "maturin"

[project]
name = "my-rust-module"
version = "0.1.0"
description = "A Python module written in Rust"
requires-python = ">=3.8"
classifiers = [
    "Programming Language :: Rust",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
]

[project.optional-dependencies]
dev = ["pytest", "hypothesis"]

[tool.maturin]
# 模組名稱（如果與 crate 名稱不同）
module-name = "my_rust_module"

# Python 原始碼目錄（如果有純 Python 程式碼）
python-source = "python"

# 功能標誌
features = ["pyo3/extension-module"]

# 啟用 abi3
# features = ["pyo3/extension-module", "pyo3/abi3-py38"]

# 排除不需要的檔案
exclude = ["tests/*", "benches/*"]

# 建構設定
# strip = true  # 移除除錯符號（減小檔案大小）
```

### Cargo.toml 設定

```toml
[package]
name = "my_rust_module"
version = "0.1.0"
edition = "2021"

[lib]
name = "my_rust_module"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.23", features = ["extension-module"] }

[profile.release]
lto = true          # Link-Time Optimization
codegen-units = 1   # 更好的優化
strip = true        # 移除除錯符號

[profile.dev]
opt-level = 0       # 快速編譯
```

---

## 【實作層】開發流程

### maturin develop

```bash
# 開發模式：編譯並安裝到當前虛擬環境
maturin develop

# 使用 release 模式（較慢但更快的執行時效能）
maturin develop --release

# 指定功能
maturin develop --features "some-feature"

# 在其他虛擬環境中安裝
maturin develop --target-dir target -E /path/to/venv

# 使用後立即測試
maturin develop && python -c "import my_rust_module; print(my_rust_module.add(1, 2))"
```

### 完整開發循環

```bash
# 1. 建立虛擬環境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 2. 安裝開發依賴
pip install maturin pytest

# 3. 開發循環
while editing:
    # 編輯 Rust 程式碼
    vim src/lib.rs

    # 建構並安裝
    maturin develop

    # 執行測試
    pytest tests/

# 4. 準備發布
maturin build --release
```

### 混合 Python/Rust 專案

```text
專案結構：
my_package/
├── Cargo.toml
├── pyproject.toml
├── src/
│   └── lib.rs              # Rust 程式碼
└── python/
    └── my_package/
        ├── __init__.py     # 匯入 Rust 模組
        ├── utils.py        # 純 Python 程式碼
        └── py.typed        # 型別標記
```

```python
# python/my_package/__init__.py
from .my_package import *  # 從 Rust 模組匯入
from .utils import helper_function  # 純 Python

__version__ = "0.1.0"
```

```toml
# pyproject.toml
[tool.maturin]
python-source = "python"
module-name = "my_package.my_package"
```

---

## 【實作層】建構與發布

### maturin build

```bash
# 建構 wheel
maturin build

# Release 模式
maturin build --release

# 指定 Python 版本
maturin build --interpreter python3.11

# 多個 Python 版本
maturin build --interpreter python3.10 python3.11 python3.12

# 使用 abi3（穩定 ABI）
maturin build --release --features pyo3/abi3-py38

# 建構結果位置
ls target/wheels/
# my_rust_module-0.1.0-cp311-cp311-linux_x86_64.whl
```

### 跨平台建構

```bash
# 使用 Docker 建構 manylinux wheel
maturin build --release --manylinux 2014

# 常用的 manylinux 版本
# manylinux1:   CentOS 5 (非常老舊)
# manylinux2010: CentOS 6
# manylinux2014: CentOS 7 (推薦)
# manylinux_2_28: Debian 9 / Ubuntu 18.04

# 使用 zig 進行交叉編譯
pip install ziglang
maturin build --release --target x86_64-unknown-linux-gnu --zig

# 常見目標平台
# x86_64-unknown-linux-gnu
# aarch64-unknown-linux-gnu
# x86_64-apple-darwin
# aarch64-apple-darwin
# x86_64-pc-windows-msvc
```

### 發布到 PyPI

```bash
# 發布到 TestPyPI（測試）
maturin publish --repository testpypi

# 發布到 PyPI
maturin publish

# 使用 API token
maturin publish --username __token__ --password <your-pypi-token>

# 或者設定環境變數
export MATURIN_PYPI_TOKEN=<your-pypi-token>
maturin publish
```

---

## 【實作層】CI/CD 整合

### GitHub Actions

```yaml
# .github/workflows/build.yml
name: Build and Publish

on:
  push:
    tags:
      - 'v*'
  pull_request:
    branches:
      - main

jobs:
  # Linux
  linux:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target: [x86_64, aarch64]
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Build wheels
        uses: PyO3/maturin-action@v1
        with:
          target: ${{ matrix.target }}
          args: --release --out dist
          manylinux: auto

      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-linux-${{ matrix.target }}
          path: dist

  # macOS
  macos:
    runs-on: macos-latest
    strategy:
      matrix:
        target: [x86_64, aarch64]
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Build wheels
        uses: PyO3/maturin-action@v1
        with:
          target: ${{ matrix.target }}-apple-darwin
          args: --release --out dist

      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-macos-${{ matrix.target }}
          path: dist

  # Windows
  windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Build wheels
        uses: PyO3/maturin-action@v1
        with:
          args: --release --out dist

      - name: Upload wheels
        uses: actions/upload-artifact@v4
        with:
          name: wheels-windows
          path: dist

  # 發布
  publish:
    needs: [linux, macos, windows]
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: wheels-*
          merge-multiple: true
          path: dist

      - name: Publish to PyPI
        uses: PyO3/maturin-action@v1
        env:
          MATURIN_PYPI_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
        with:
          command: upload
          args: --non-interactive --skip-existing dist/*
```

### 測試工作流程

```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Install maturin
        run: pip install maturin pytest

      - name: Build and install
        run: maturin develop

      - name: Run tests
        run: pytest tests/
```

---

## 【進階】效能優化

### 編譯優化

```toml
# Cargo.toml
[profile.release]
lto = "fat"         # 最佳化連結（較慢編譯）
codegen-units = 1   # 單一編譯單元（更好優化）
panic = "abort"     # 不展開 panic（較小二進位）
strip = true        # 移除符號

# 針對特定 CPU 優化
# RUSTFLAGS="-C target-cpu=native" maturin build --release
```

### 減小二進位大小

```toml
# Cargo.toml
[profile.release]
opt-level = "z"     # 優化大小而非速度
lto = true
strip = true
panic = "abort"

[dependencies]
# 使用 features 減少不需要的程式碼
pyo3 = { version = "0.23", default-features = false, features = ["extension-module"] }
```

### 除錯技巧

```bash
# 保留除錯符號
maturin develop --profile dev

# 啟用 Rust backtrace
RUST_BACKTRACE=1 python -c "import my_module; my_module.buggy_function()"

# 使用 lldb/gdb
lldb python
(lldb) run -c "import my_module; my_module.buggy_function()"
```

---

## 【常見問題】疑難排解

### 編譯錯誤

```text
問題：找不到 Python

解決：
1. 確認 Python 在 PATH 中
2. 使用 --interpreter 指定路徑
   maturin develop --interpreter /usr/bin/python3.11

問題：連結錯誤（Linux）

解決：
1. 安裝 python3-dev
   sudo apt install python3-dev
2. 安裝 build-essential
   sudo apt install build-essential

問題：找不到 PyO3

解決：
1. 確認 Cargo.toml 中有正確的 pyo3 依賴
2. 執行 cargo update
```

### 執行時錯誤

```text
問題：ImportError: undefined symbol

原因：模組和 Python 版本不匹配

解決：
1. 重新建構
   maturin develop
2. 確認使用正確的 Python
   which python

問題：記憶體錯誤 / Segfault

原因：通常是 unsafe 程式碼或 GIL 問題

解決：
1. 檢查 unsafe 區塊
2. 確認正確使用 py.allow_threads()
3. 使用 RUST_BACKTRACE=1 獲取堆疊追蹤
```

---

## 完整範例專案

### 專案結構

```text
fibonacci_rs/
├── Cargo.toml
├── pyproject.toml
├── src/
│   └── lib.rs
├── python/
│   └── fibonacci_rs/
│       ├── __init__.py
│       └── py.typed
├── tests/
│   └── test_fib.py
└── README.md
```

### 完整程式碼

```toml
# Cargo.toml
[package]
name = "fibonacci_rs"
version = "0.1.0"
edition = "2021"

[lib]
name = "fibonacci_rs"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.23", features = ["extension-module"] }

[profile.release]
lto = true
codegen-units = 1
```

```toml
# pyproject.toml
[build-system]
requires = ["maturin>=1.5,<2.0"]
build-backend = "maturin"

[project]
name = "fibonacci-rs"
version = "0.1.0"
description = "Fast Fibonacci implementation in Rust"
requires-python = ">=3.8"

[tool.maturin]
python-source = "python"
module-name = "fibonacci_rs._core"
```

```rust
// src/lib.rs
use pyo3::prelude::*;

/// 計算 Fibonacci 數列第 n 項
#[pyfunction]
fn fib(n: u64) -> u64 {
    if n <= 1 {
        return n;
    }
    let mut a = 0u64;
    let mut b = 1u64;
    for _ in 2..=n {
        let tmp = a + b;
        a = b;
        b = tmp;
    }
    b
}

/// 計算 Fibonacci 數列前 n 項
#[pyfunction]
fn fib_sequence(py: Python<'_>, n: usize) -> Vec<u64> {
    py.allow_threads(|| {
        let mut seq = Vec::with_capacity(n);
        let (mut a, mut b) = (0u64, 1u64);
        for _ in 0..n {
            seq.push(a);
            let tmp = a + b;
            a = b;
            b = tmp;
        }
        seq
    })
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fib, m)?)?;
    m.add_function(wrap_pyfunction!(fib_sequence, m)?)?;
    Ok(())
}
```

```python
# python/fibonacci_rs/__init__.py
from ._core import fib, fib_sequence

__all__ = ["fib", "fib_sequence"]
__version__ = "0.1.0"
```

```python
# tests/test_fib.py
import fibonacci_rs

def test_fib_zero():
    assert fibonacci_rs.fib(0) == 0

def test_fib_one():
    assert fibonacci_rs.fib(1) == 1

def test_fib_ten():
    assert fibonacci_rs.fib(10) == 55

def test_fib_sequence():
    seq = fibonacci_rs.fib_sequence(10)
    assert seq == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

---

## 思考題

1. 為什麼 Maturin 使用 `cdylib` crate type？與 `rlib` 有什麼差異？
2. abi3 功能如何減少需要建構的 wheel 數量？有什麼限制？
3. 在 CI 中建構跨平台 wheel 時，最大的挑戰是什麼？

## 實作練習

1. 建立一個新的 Maturin 專案，實現一個簡單的字串處理函式
2. 設定 GitHub Actions 自動建構並發布到 TestPyPI
3. 比較 `maturin develop` 和 `maturin develop --release` 的編譯時間和執行效能

## 延伸閱讀

- [Maturin 官方文件](https://www.maturin.rs/)
- [Maturin GitHub](https://github.com/PyO3/maturin)
- [PyO3/maturin-action](https://github.com/PyO3/maturin-action)
- [Python Packaging User Guide](https://packaging.python.org/)

---

*上一章：[PyO3 基礎](../pyo3-basics/)*
*下一章：[實戰案例分析](../real-world-examples/)*
