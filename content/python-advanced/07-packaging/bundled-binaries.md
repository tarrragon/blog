---
title: "6.5 封裝預編譯二進位"
date: 2026-02-02
description: "Python 套件如何封裝其他語言編譯的二進位檔案"
weight: 5
---

本章介紹 Python 套件封裝預編譯二進位的架構模式，讓 Python 能夠調用高效能的原生程式碼。

## 本章目標

學完本章後，你將能夠：

1. 理解「Python 封裝二進位」的架構模式
2. 評估何時使用這種模式
3. 了解知名套件如何應用這種技術
4. 在純 Python 與封裝二進位之間做出正確選擇

---

## 【概念】什麼是封裝預編譯二進位？

### 架構模式

這種模式將其他語言（如 Go、Rust、C++）編譯的二進位檔案，包裝在 Python 套件中：

```text
┌─────────────────────────────────────────┐
│       Python API（薄封裝層）              │  ← 使用者接觸的介面
├─────────────────────────────────────────┤
│   subprocess / FFI / ctypes / cffi      │  ← 呼叫機制
├─────────────────────────────────────────┤
│   預編譯二進位（Go/Rust/C/C++）          │  ← 實際執行邏輯
└─────────────────────────────────────────┘
```

### 與 C 擴展的差異

| 面向       | C 擴展（模組四/五）     | 封裝預編譯二進位        |
| ---------- | ----------------------- | ----------------------- |
| 編譯時機   | 安裝時編譯              | 發布前預編譯            |
| 使用者需求 | 可能需要編譯器          | 不需要編譯器            |
| 整合方式   | Python C API / pybind11 | subprocess / FFI        |
| 典型來源   | 專為 Python 寫的擴展    | 獨立的 CLI 工具或函式庫 |

---

## 【案例】

### TensorFlow / PyTorch

```text
TensorFlow 架構：
├── Python API（tf.* 模組）
│   └── 使用者撰寫的程式碼
├── 綁定層（pybind11）
│   └── Python ↔ C++ 橋接
└── C++ 核心 + CUDA
    └── 預編譯的運算核心
```

**選擇原因**：

- GPU 運算需要原生效能
- 大量的 C++ 程式碼庫
- 安裝時編譯太慢（數小時）

### cryptography

```text
cryptography 架構：
├── Python API（cryptography.*)
├── cffi 綁定層
└── OpenSSL / BoringSSL
    └── 預編譯的加密函式庫
```

**選擇原因**：

- 加密演算法需要經過審計的實現
- 效能關鍵
- 支援 PyPy（cffi 是 PyPy 官方推薦）

### ruff（Python Linter）

```text
ruff 架構：
├── Python 封裝（ruff 套件）
│   └── 提供 CLI 和簡單 API
└── Rust 二進位
    └── 實際的 lint 邏輯
```

**選擇原因**：

- 追求極致速度（比 Flake8 快 10-100 倍）
- Rust 的記憶體安全
- 作為獨立工具也可使用

### mermaid-ascii（PyPI 封裝）

```text
osl-packages/mermaid-ascii 架構：
├── Python API（mermaid_ascii 模組）
│   └── mermaid_to_ascii() 函式
├── subprocess 呼叫
└── Go 編譯的 mermaid-ascii 二進位
    └── Mermaid → ASCII 轉換
```

**選擇原因**：

- 重用現有的 Go 實現
- 不需要 Node.js 依賴
- 提供 Python 友善的介面

---

## 【優點】為什麼使用這種模式？

### 1. 效能

核心邏輯用高效能語言實現，Python 只做介面：

```python
# 使用者感受不到底層是 Rust
import ruff

# 實際上是呼叫 Rust 編譯的二進位
result = ruff.check("my_code.py")
```

### 2. 重用現有實現

不需要用 Python 重寫已經穩定的程式碼：

```text
情境：有一個優秀的 Go CLI 工具
選項 A：用 Python 重寫（大量工作）
選項 B：封裝 Go 二進位（少量工作）← 通常更好
```

### 3. 跨語言生態整合

讓 Python 使用者能夠使用其他語言的優秀工具：

```python
# Python 使用者不需要安裝 Go
from mermaid_ascii import mermaid_to_ascii

diagram = mermaid_to_ascii("graph LR; A-->B")
```

### 4. 維護分離

核心邏輯與 Python 封裝可以獨立更新：

```text
mermaid-ascii（Go）: v0.6.1 → v0.7.0（核心更新）
mermaid-ascii（PyPI）: 0.6.1 → 0.7.0（同步更新封裝）
```

---

## 【缺點】這種模式的限制

### 1. 平台依賴

需要為每個作業系統和 CPU 架構提供預編譯二進位：

```text
典型的 wheel 矩陣：
├── manylinux_x86_64
├── manylinux_aarch64
├── macosx_x86_64
├── macosx_arm64
└── win_amd64

缺點：
- 維護成本高
- 新平台支援需要時間
- CI/CD 複雜度增加
```

### 2. 安裝體積

wheel 檔案較大（包含二進位）：

```text
套件大小比較：
純 Python 套件   ~50 KB
封裝二進位套件   ~5-50 MB（依二進位大小）
```

### 3. 除錯困難

錯誤可能發生在二進位層，難以追蹤：

```python
# 錯誤訊息可能是二進位的 stderr
try:
    result = some_binary_wrapper()
except subprocess.CalledProcessError as e:
    # e.stderr 是二進位的錯誤訊息
    # 可能不是 Python 友善的格式
```

### 4. 無法修改核心邏輯

想改變底層行為必須重編譯核心：

```text
如果你需要：
- 修改演算法
- 加入自訂功能
- 修復底層 bug

你必須：
1. 修改原始語言的程式碼
2. 重新編譯
3. 重新打包 wheel
```

### 5. 供應鏈風險

二進位來源需要信任：

```text
風險考量：
├── 二進位是否來自可信來源？
├── 是否有可驗證的建構流程？
└── 是否有安全審計？

最佳實踐：
├── 使用知名維護者的套件
├── 檢查 GitHub Actions 等 CI 建構紀錄
└── 考慮自行建構（如果可能）
```

---

## 【比較】純 Python vs 封裝二進位

### 特性比較表

| 面向           | 純 Python                    | 封裝預編譯二進位 |
| -------------- | ---------------------------- | ---------------- |
| **效能**       | 較慢                         | 可達原生速度     |
| **可移植性**   | 極佳（任何有 Python 的地方） | 受限於預編譯平台 |
| **除錯**       | 容易（Python 工具鏈）        | 困難（跨語言）   |
| **修改靈活度** | 高（直接修改程式碼）         | 低（需重新編譯） |
| **安裝體積**   | 小                           | 大（含二進位）   |
| **依賴管理**   | 簡單                         | 複雜             |
| **透明度**     | 完全可見                     | 部分黑箱         |
| **開發速度**   | 快（Python 生態）            | 需要多語言技能   |

### 決策流程

```text
選擇純 Python 如果：
├── 效能不是關鍵瓶頸
├── 需要頻繁修改邏輯
├── 需要最大可移植性
├── 功能相對簡單
└── 希望保持程式碼透明

選擇封裝二進位如果：
├── 效能是關鍵需求
├── 已有成熟的非 Python 實現
├── 核心邏輯穩定，不常修改
├── 需要系統級別的操作
└── 安全性要求使用審計過的實現
```

---

## 【實作】如何封裝二進位

### 方法一：subprocess 呼叫

最簡單的封裝方式，適合 CLI 工具：

```python
# my_wrapper/core.py
import subprocess
import shutil
from pathlib import Path

def find_binary():
    """找到封裝的二進位檔案"""
    # 二進位通常放在套件目錄內
    package_dir = Path(__file__).parent
    binary = package_dir / "bin" / "my_tool"

    if binary.exists():
        return binary

    # 或者在 PATH 中尋找
    return shutil.which("my_tool")

def run_tool(input_text: str) -> str:
    """呼叫封裝的工具"""
    binary = find_binary()
    if not binary:
        raise RuntimeError("找不到 my_tool 二進位")

    result = subprocess.run(
        [str(binary)],
        input=input_text,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout
```

### 方法二：ctypes / cffi

適合函式庫（.so / .dll）：

```python
# my_wrapper/bindings.py
import ctypes
from pathlib import Path

def load_library():
    """載入共享函式庫"""
    package_dir = Path(__file__).parent

    # 根據平台選擇正確的檔案
    import platform
    if platform.system() == "Darwin":
        lib_name = "libmy_tool.dylib"
    elif platform.system() == "Windows":
        lib_name = "my_tool.dll"
    else:
        lib_name = "libmy_tool.so"

    lib_path = package_dir / "lib" / lib_name
    return ctypes.CDLL(str(lib_path))

# 載入並設定函式簽名
_lib = load_library()
_lib.process_data.argtypes = [ctypes.c_char_p]
_lib.process_data.restype = ctypes.c_char_p

def process_data(data: str) -> str:
    """Python 友善的介面"""
    result = _lib.process_data(data.encode('utf-8'))
    return result.decode('utf-8')
```

### 方法三：使用專門工具

```text
推薦工具：
├── PyOxidizer：打包 Python + Rust
├── Briefcase：跨平台打包
├── Nuitka：Python → 原生編譯
└── 自訂 GitHub Actions：建構多平台 wheel
```

---

## 【打包】建立 wheel

### 專案結構

```text
my_package/
├── pyproject.toml
├── src/
│   └── my_package/
│       ├── __init__.py
│       ├── core.py          # Python 封裝
│       └── bin/             # 預編譯二進位
│           ├── my_tool-linux-x64
│           ├── my_tool-darwin-arm64
│           └── my_tool-windows-x64.exe
└── scripts/
    └── build_binaries.sh    # 建構腳本
```

### pyproject.toml 設定

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
description = "Python wrapper for my_tool"

[tool.hatch.build.targets.wheel]
# 包含二進位檔案
include = [
    "src/my_package/bin/*"
]

# 設定平台特定的 wheel
[tool.hatch.build.targets.wheel.hooks.custom]
# 自訂 hook 來處理平台特定二進位
```

### GitHub Actions 範例

```yaml
# .github/workflows/build.yml
name: Build wheels

on: [push, release]

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        arch: [x64, arm64]

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Build binary
        run: |
          # 根據目標平台建構二進位
          ./scripts/build_binary.sh ${{ matrix.arch }}

      - name: Build wheel
        run: |
          pip install build
          python -m build --wheel

      - name: Upload wheel
        uses: actions/upload-artifact@v4
        with:
          name: wheel-${{ matrix.os }}-${{ matrix.arch }}
          path: dist/*.whl
```

---

## 【案例研究】beautiful-mermaid-py

### 背景

將 Mermaid 圖表轉換為 ASCII 藝術的工具，存在多種實現：

| 專案                       | 語言       | 實現方式           | 圖表支援 |
| -------------------------- | ---------- | ------------------ | -------- |
| mermaid-ascii              | Go         | 原創實現           | 2 種     |
| beautiful-mermaid          | TypeScript | 從 Go 移植並擴展   | 5 種     |
| beautiful-mermaid-py       | Python     | 從 TypeScript 移植 | 5 種     |
| osl-packages/mermaid-ascii | Python     | 封裝 Go 二進位     | 2 種     |

### 兩種 Python 方案比較

```text
方案 A：封裝 Go 二進位（osl-packages）
├── 優點：效能較好、維護成本低
├── 缺點：平台依賴、無法修改邏輯
└── 適合：追求效能、不需自訂

方案 B：純 Python 移植（beautiful-mermaid-py）
├── 優點：無依賴、可自訂、跨平台
├── 缺點：效能略低（但對此任務足夠）
└── 適合：需要修改、追求簡潔
```

### 決策分析

對於 Mermaid ASCII 渲染這個需求：

```text
效能需求：低（渲染一次圖表不需要毫秒級優化）
修改需求：可能（未來可能想客製化輸出格式）
平台多樣性：高（不同開發環境）
維護成本：純 Python 更低

結論：對於這個場景，純 Python 是更好的選擇
```

---

## 總結

### 何時封裝二進位

```text
適合封裝二進位：
├── 效能關鍵的運算（加密、ML、圖像處理）
├── 已有成熟的非 Python 實現
├── 需要系統級別的操作
└── 安全性要求使用審計過的程式碼

不適合封裝二進位：
├── 簡單的文字處理或資料轉換
├── 需要頻繁修改邏輯的功能
├── 追求最大可移植性的工具
└── 功能用純 Python 就能達到足夠效能
```

### 架構選擇原則

1. **效能驅動**：只有當效能是瓶頸時才考慮封裝二進位
2. **重用優先**：有成熟實現時考慮封裝，否則考慮純 Python
3. **維護成本**：評估長期維護的複雜度
4. **團隊技能**：選擇團隊能夠維護的方案

---

## 延伸閱讀

- [Python Packaging Guide - Binary Extensions](https://packaging.python.org/en/latest/guides/packaging-binary-extensions/)
- [manylinux 標準](https://github.com/pypa/manylinux)
- [PyOxidizer 文件](https://pyoxidizer.readthedocs.io/)
- [模組四：用 C 擴展 Python](../05-c-extensions/) - 另一種整合原生程式碼的方式

---

_上一章：[套件維護最佳實踐](../best-practices/)_
_下一模組：[模組七：實戰效能優化](../../08-practical-optimization/)_
