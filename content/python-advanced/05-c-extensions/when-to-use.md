---
title: "4.4 選擇指南與效能比較"
description: "比較不同 C 擴展工具的適用場景"
weight: 4
---

# 選擇指南與效能比較

本章比較各種 C 擴展工具，幫助你在不同場景下做出正確選擇。

## 本章目標

學完本章後，你將能夠：

1. 根據專案需求選擇適合的工具
2. 理解各工具的效能差異
3. 評估維護成本與學習曲線

---

## 【總覽】C 擴展工具比較

### 工具定位

```text
┌─────────────────────────────────────────────────────────────────┐
│                        C/C++ 擴展工具選擇                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   動態綁定（不需編譯）          靜態編譯                         │
│   ├── ctypes                   ├── Cython                      │
│   └── cffi (ABI)               ├── cffi (API)                  │
│                                ├── pybind11                    │
│                                └── nanobind                    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│   適合 Python 背景              適合 C/C++ 背景                  │
│   ├── ctypes                   ├── pybind11                    │
│   ├── cffi                     ├── nanobind                    │
│   └── Cython                   └── Python C API                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 快速比較表

| 特性 | ctypes | cffi | Cython | pybind11 |
|------|--------|------|--------|----------|
| 標準庫 | ✅ | ❌ | ❌ | ❌ |
| 不需編譯器 | ✅ | ✅ (ABI) | ❌ | ❌ |
| C++ 支援 | ❌ | ❌ | 有限 | ✅ |
| 效能 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 學習曲線 | 低 | 低 | 中 | 中高 |
| PyPy 支援 | 有限 | ✅ | 有限 | ❌ |

---

## 【決策】選擇流程圖

### 主要決策點

```text
開始
│
├── Q1: 有 C/C++ 原始碼嗎？
│   │
│   ├── 沒有（只有 .so/.dll）
│   │   └── → ctypes 或 cffi (ABI 模式)
│   │
│   └── 有原始碼
│       │
│       ├── Q2: 是 C++ 嗎？
│       │   │
│       │   ├── 是 C++
│       │   │   └── → pybind11 或 nanobind
│       │   │
│       │   └── 是純 C
│       │       │
│       │       ├── Q3: 想用 Python 語法寫？
│       │       │   ├── 是 → Cython
│       │       │   └── 否 → cffi (API 模式)
│       │       │
│       │       └── Q4: 需要優化現有 Python 程式碼？
│       │           └── 是 → Cython
│
├── Q5: 需要在 PyPy 上執行？
│   └── 是 → cffi
│
└── Q6: 需要最小依賴？
    └── 是 → ctypes（標準庫）
```

### 場景決策表

| 場景 | 推薦工具 | 原因 |
|------|---------|------|
| 呼叫系統 API (libc, Win32) | ctypes | 標準庫，無需額外安裝 |
| 包裝現有 C 函式庫（無原始碼） | cffi (ABI) | 較好的型別支援 |
| 包裝現有 C 函式庫（有原始碼） | cffi (API) 或 Cython | 效能更好 |
| 包裝 C++ 函式庫 | pybind11 | C++ 原生支援 |
| 優化 Python 程式碼瓶頸 | Cython | 漸進式優化 |
| 新專案追求最小二進位 | nanobind | 現代設計 |
| 需要跨直譯器支援 (PyPy) | cffi | PyPy 官方推薦 |

---

## 【效能】基準測試比較

### 測試案例：數值計算

計算 Fibonacci 數列第 n 項（迭代版）：

```python
# 純 Python 基準
def fib_python(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
```

### 效能數據

```text
計算 fib(40)，執行 10000 次：

工具              相對時間    說明
─────────────────────────────────────────
純 Python         1.00x      基準
ctypes            0.45x      呼叫 C 函式庫
cffi (ABI)        0.40x      動態載入
cffi (API)        0.15x      編譯後
Cython            0.08x      靜態型別
pybind11          0.08x      C++ 編譯

注意：
- 實際數據取決於具體任務
- 數值計算 Cython 和 pybind11 接近
- 字串處理 pybind11 通常更快（std::string）
- 函式呼叫開銷：ctypes > cffi ABI > cffi API ≈ Cython ≈ pybind11
```

### 函式呼叫開銷測試

```python
import timeit

# 測試空函式呼叫開銷
# 每個工具都實現 def noop(): pass

results = """
空函式呼叫 1,000,000 次：

工具              時間 (ms)   每次呼叫 (ns)
───────────────────────────────────────────
Python def        45          45
ctypes           280         280
cffi (ABI)       180         180
cffi (API)        55          55
Cython cdef       12          12  (只能從 Cython 呼叫)
Cython cpdef      50          50
pybind11          52          52
"""

# 結論：
# - ctypes/cffi ABI 的呼叫開銷較大
# - 對於頻繁呼叫的小函式，編譯方案更好
# - Cython cdef 最快，但不能從 Python 直接呼叫
```

### 記憶體使用比較

```text
匯入空模組的記憶體增加：

工具              額外記憶體
────────────────────────────
ctypes           ~50 KB
cffi             ~200 KB
Cython module    ~100 KB
pybind11 module  ~150 KB

編譯後的模組大小（簡單範例）：

工具              .so 檔案大小
─────────────────────────────
Cython           ~100 KB
pybind11         ~200 KB
nanobind         ~50 KB
```

---

## 【考量】維護性與開發體驗

### 學習曲線

```text
難度排序（由易到難）：

1. ctypes
   - Python 標準庫
   - 不需要 C 知識（但需要理解 C 型別）
   - 文件完整

2. cffi
   - 需要寫 C 宣告
   - ABI 模式很簡單
   - API 模式需要建構設定

3. Cython
   - Python 超集，逐步學習
   - 需要理解 C 型別系統
   - 建構系統有學習成本

4. pybind11
   - 需要 C++ 知識
   - 現代 C++ 語法
   - 需要 CMake 或類似工具
```

### 除錯難度

```text
除錯工具支援：

ctypes:
├── 可以用 Python debugger
├── 段錯誤難以追蹤
└── 沒有型別檢查

cffi:
├── API 模式有較好的錯誤訊息
├── 可以用 C debugger (gdb)
└── ABI 模式錯誤較難理解

Cython:
├── 可以產生帶行號的 C 程式碼
├── 支援 gdb/lldb
├── cython -a 產生效能報告
└── 支援 Python profiler

pybind11:
├── C++ 除錯器完整支援
├── 異常會轉換為 Python 異常
├── 編譯錯誤訊息可能很長
└── 模板錯誤較難理解
```

### IDE 支援

```text
IDE / 編輯器支援程度：

工具          型別提示    自動完成    語法高亮
─────────────────────────────────────────────
ctypes        ⭐⭐        ⭐⭐         ⭐⭐⭐⭐
cffi          ⭐⭐        ⭐⭐         ⭐⭐⭐⭐
Cython        ⭐⭐⭐      ⭐⭐⭐       ⭐⭐⭐
pybind11      ⭐⭐⭐⭐    ⭐⭐⭐⭐     ⭐⭐⭐⭐

註：
- Cython 有 VSCode 和 PyCharm 插件
- pybind11 使用標準 C++，IDE 支援完整
- ctypes/cffi 的 Python 部分支援完整
```

---

## 【案例】知名專案的選擇

### NumPy

```text
NumPy 的策略：

核心計算:
└── Python C API + 自訂機制
    - 歷史原因（比 pybind11 更早）
    - 需要極致效能
    - 大量使用 BLAS/LAPACK

周邊工具:
└── Cython
    - 部分輔助模組
    - 與 NumPy 陣列整合良好
```

### SciPy

```text
SciPy 的策略：

主要使用:
├── Cython（大部分新程式碼）
├── Fortran（歷史遺留的數值庫）
└── C（某些核心演算法）

選擇原因:
- Cython 與 NumPy 整合好
- 漸進式優化現有 Python 程式碼
- 科學計算社群熟悉
```

### PyTorch

```text
PyTorch 的策略：

C++ 核心:
└── pybind11
    - 大量 C++ 程式碼
    - 複雜的類別層級
    - 自動微分需要 C++ 特性

選擇原因:
- C++ 是主要開發語言
- 需要 RAII、模板、繼承
- 與 CUDA 程式碼整合
```

### Pillow (PIL)

```text
Pillow 的策略：

影像處理核心:
└── Python C API
    - 歷史遺留
    - 底層記憶體操作

周邊功能:
└── 純 Python 或 ctypes
    - 呼叫系統圖形庫
```

### cryptography

```text
cryptography 的策略：

主要使用:
└── cffi
    - 包裝 OpenSSL
    - 需要 PyPy 支援
    - 安全性考量（減少手動記憶體管理）
```

---

## 【建議】實務選擇指南

### 新專案建議

```text
2025 年新專案建議：

場景 1: 優化 Python 程式碼
推薦: Cython
理由:
- 漸進式優化
- 熟悉的 Python 語法
- 與 NumPy 整合好

場景 2: 包裝現有 C++ 函式庫
推薦: pybind11 或 nanobind
理由:
- C++ 原生支援
- 現代化 API
- 活躍的社群

場景 3: 簡單呼叫系統 API
推薦: ctypes
理由:
- 標準庫，無依賴
- 簡單場景足夠

場景 4: 需要 PyPy 支援
推薦: cffi
理由:
- PyPy 官方推薦
- 良好的效能
```

### 遷移建議

```text
從 ctypes 遷移到更快的方案：

如果瓶頸是呼叫頻率：
└── 考慮 cffi (API) 或 Cython
    - 減少每次呼叫的開銷

如果瓶頸是計算本身：
└── 考慮 Cython
    - 可以優化 Python 迴圈
    - 使用 C 型別

從 Cython 遷移到 pybind11：

通常不需要：
- Cython 和 pybind11 效能相近
- 遷移成本高

考慮遷移如果：
- 需要更多 C++ 特性
- 團隊更熟悉 C++
- 需要與 C++ 函式庫深度整合
```

### 混合使用

```text
可以在同一專案中混合使用：

範例結構：
my_package/
├── _core.cpython-311-xxx.so    # Cython：核心計算
├── _bindings.cpython-311-xxx.so # pybind11：C++ 函式庫綁定
├── _ffi.py                      # cffi：簡單 C 呼叫
└── utils.py                     # 純 Python

原則：
- 選擇最適合該任務的工具
- 保持介面一致（對使用者透明）
- 文件記錄每個部分的技術選擇
```

---

## 【未來】發展趨勢

### Free-threading 影響

```text
Python 3.13+ Free-threading 的影響：

需要注意的工具：
├── pybind11: 需要更新 GIL 管理方式
├── Cython: nogil 區塊的行為變化
└── cffi: 相對影響較小

趨勢：
- nanobind 已有 Free-threading 支援
- pybind11 正在積極適應
- Cython 3.1 計劃支援
```

### HPy：新一代 C API

```text
HPy (https://hpyproject.org/)

目標：
├── 統一的 C API（跨直譯器）
├── 更好的 PyPy/GraalPy 支援
├── 為 Free-threading 設計
└── 簡化記憶體管理

狀態（2025）：
- 仍在開發中
- 部分專案開始採用
- 長期可能取代 Python C API
```

### 建構系統演進

```text
建構系統趨勢：

傳統：
├── setup.py + setuptools
└── 複雜且不標準

現代：
├── scikit-build-core + CMake
├── meson-python
└── 統一使用 pyproject.toml

建議：
- 新專案使用 scikit-build-core 或 meson-python
- 舊專案可以繼續使用 setup.py
- 避免複雜的建構邏輯
```

---

## 總結

### 選擇原則

1. **簡單優先**：如果 ctypes 能滿足需求，就用 ctypes
2. **效能驅動**：當效能成為瓶頸時，才考慮編譯方案
3. **團隊技能**：選擇團隊熟悉的技術
4. **長期維護**：考慮依賴的活躍度和未來發展

### 快速決策

```text
你應該使用：

ctypes    → 簡單的系統 API 呼叫
cffi      → 需要 PyPy 支援，或包裝 C 函式庫
Cython    → 優化 Python 程式碼，或與 NumPy 密切整合
pybind11  → 包裝 C++ 函式庫
nanobind  → 新專案，追求最小化
```

---

## 實作練習

1. 使用本章學到的四種工具，分別實現同一個函式（如快速排序），比較：
   - 程式碼行數
   - 編譯時間
   - 執行效能
   - 除錯體驗

2. 選擇一個你熟悉的 C 函式庫，分別用 ctypes 和 cffi 包裝，比較開發體驗

3. 將一個 Python 效能瓶頸用 Cython 優化，記錄優化過程和效能提升

## 延伸閱讀

- [Real Python - Python Bindings Overview](https://realpython.com/python-bindings-overview/)
- [Stefan Behnel - Cython vs pybind11 vs cffi](http://blog.behnel.de/posts/cython-pybind11-cffi-which-tool-to-choose.html)
- [HPy Project](https://hpyproject.org/)
- [Python Packaging Guide - Binary Extensions](https://packaging.python.org/en/latest/guides/packaging-binary-extensions/)

---

*上一章：[pybind11](../pybind11/)*
*下一模組：[模組五：用 Rust 擴展 Python](../../05-rust-extensions/)*
