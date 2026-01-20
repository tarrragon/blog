---
title: "5.2 PyO3 基礎"
date: 2026-01-20
description: "使用 PyO3 建立 Rust 與 Python 的綁定"
weight: 2
---

# PyO3 基礎

本章介紹 PyO3，Rust 的 Python 綁定函式庫。

## 本章目標

學完本章後，你將能夠：

1. 理解 PyO3 的設計原理
2. 使用 #[pyfunction] 和 #[pyclass] 建立綁定
3. 處理型別轉換和錯誤

---

## 【原理層】PyO3 的設計

### PyO3 是什麼？

PyO3 是 Rust 與 Python 之間的橋樑：

```text
PyO3 提供：
├── Rust → Python：將 Rust 程式碼編譯為 Python 模組
├── Python → Rust：在 Rust 中嵌入 Python 直譯器
├── 型別轉換：自動處理 Rust ↔ Python 型別
└── GIL 管理：安全地處理 Python 的全域直譯器鎖
```

### 版本要求

```toml
# Cargo.toml（2025 年建議）
[dependencies]
pyo3 = { version = "0.23", features = ["extension-module"] }

# 支援的版本：
# - Rust: 1.63+（建議 1.75+）
# - Python: 3.8+
# - PyO3: 0.23+（支援 Free-threading）
```

### 與 Python 的互動模型

```text
Python 程式
    │
    ↓ import
┌─────────────────────────────────┐
│  Rust 編譯的 .so/.pyd 模組      │
│  ┌─────────────────────────┐   │
│  │  PyO3 綁定層            │   │
│  │  - 型別轉換             │   │
│  │  - GIL 管理             │   │
│  │  - 錯誤處理             │   │
│  └─────────────────────────┘   │
│  ┌─────────────────────────┐   │
│  │  純 Rust 程式碼         │   │
│  │  - 核心邏輯             │   │
│  │  - 無 GIL 限制          │   │
│  └─────────────────────────┘   │
└─────────────────────────────────┘
```

---

## 【設計層】專案設定

### Cargo.toml 設定

```toml
[package]
name = "my_rust_module"
version = "0.1.0"
edition = "2021"

[lib]
name = "my_rust_module"
crate-type = ["cdylib"]  # 編譯為動態連結庫

[dependencies]
pyo3 = { version = "0.23", features = ["extension-module"] }

# 選用功能
# pyo3 = { version = "0.23", features = [
#     "extension-module",
#     "abi3-py38",        # 穩定 ABI（支援 Python 3.8+）
#     "multiple-pymethods",
# ]}
```

### 基本模組結構

```rust
// src/lib.rs
use pyo3::prelude::*;

/// 簡單的加法函式
#[pyfunction]
fn add(a: i64, b: i64) -> i64 {
    a + b
}

/// 建立 Python 模組
#[pymodule]
fn my_rust_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(add, m)?)?;
    Ok(())
}
```

### abi3：穩定 ABI

```toml
# 啟用 abi3 的好處：
# 1. 一次編譯，多版本 Python 使用
# 2. 減少發布的 wheel 數量
# 3. 更好的向前相容性

[dependencies]
pyo3 = { version = "0.23", features = ["extension-module", "abi3-py38"] }
```

```text
不使用 abi3：
├── my_module-cp38-cp38-linux_x86_64.whl
├── my_module-cp39-cp39-linux_x86_64.whl
├── my_module-cp310-cp310-linux_x86_64.whl
├── my_module-cp311-cp311-linux_x86_64.whl
└── my_module-cp312-cp312-linux_x86_64.whl

使用 abi3-py38：
└── my_module-cp38-abi3-linux_x86_64.whl  # 支援 Python 3.8+
```

---

## 【實作層】函式綁定

### #[pyfunction] 基礎

```rust
use pyo3::prelude::*;

// 基本函式
#[pyfunction]
fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

// 帶預設參數
#[pyfunction]
#[pyo3(signature = (a, b=1.0))]
fn divide(a: f64, b: f64) -> f64 {
    a / b
}

// 可變參數
#[pyfunction]
#[pyo3(signature = (*args))]
fn sum_all(args: Vec<i64>) -> i64 {
    args.iter().sum()
}

// 關鍵字參數
#[pyfunction]
#[pyo3(signature = (**kwargs))]
fn print_kwargs(kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<()> {
    if let Some(dict) = kwargs {
        for (key, value) in dict.iter() {
            println!("{}: {}", key, value);
        }
    }
    Ok(())
}

// 文件字串
/// 計算兩個數的最大公因數
///
/// Args:
///     a: 第一個整數
///     b: 第二個整數
///
/// Returns:
///     最大公因數
#[pyfunction]
fn gcd(a: u64, b: u64) -> u64 {
    if b == 0 { a } else { gcd(b, a % b) }
}

#[pymodule]
fn my_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(greet, m)?)?;
    m.add_function(wrap_pyfunction!(divide, m)?)?;
    m.add_function(wrap_pyfunction!(sum_all, m)?)?;
    m.add_function(wrap_pyfunction!(print_kwargs, m)?)?;
    m.add_function(wrap_pyfunction!(gcd, m)?)?;
    Ok(())
}
```

### 型別轉換

```rust
use pyo3::prelude::*;
use pyo3::types::{PyList, PyDict, PyTuple};

// 自動型別轉換
#[pyfunction]
fn process_list(items: Vec<i64>) -> Vec<i64> {
    // Python list 自動轉換為 Vec
    items.iter().map(|x| x * 2).collect()
}

#[pyfunction]
fn process_dict(data: HashMap<String, i64>) -> i64 {
    // Python dict 自動轉換為 HashMap
    data.values().sum()
}

// 手動處理 Python 物件
#[pyfunction]
fn manual_conversion(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<String> {
    // 檢查型別
    if obj.is_instance_of::<PyList>() {
        let list = obj.downcast::<PyList>()?;
        Ok(format!("List with {} items", list.len()))
    } else if obj.is_instance_of::<PyDict>() {
        let dict = obj.downcast::<PyDict>()?;
        Ok(format!("Dict with {} keys", dict.len()))
    } else {
        Ok(format!("Unknown type: {}", obj.get_type().name()?))
    }
}

// 回傳多個值（使用 tuple）
#[pyfunction]
fn divmod(a: i64, b: i64) -> (i64, i64) {
    (a / b, a % b)
}

// 回傳 Option（轉換為 None 或值）
#[pyfunction]
fn find_item(items: Vec<i64>, target: i64) -> Option<usize> {
    items.iter().position(|&x| x == target)
}
```

---

## 【實作層】類別綁定

### #[pyclass] 基礎

```rust
use pyo3::prelude::*;

#[pyclass]
struct Point {
    #[pyo3(get, set)]  // 自動產生 getter 和 setter
    x: f64,
    #[pyo3(get, set)]
    y: f64,
}

#[pymethods]
impl Point {
    // 建構子
    #[new]
    fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }

    // 方法
    fn distance(&self, other: &Point) -> f64 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        (dx * dx + dy * dy).sqrt()
    }

    // 類別方法
    #[classmethod]
    fn origin(_cls: &Bound<'_, PyType>) -> Self {
        Point { x: 0.0, y: 0.0 }
    }

    // 靜態方法
    #[staticmethod]
    fn from_polar(r: f64, theta: f64) -> Self {
        Point {
            x: r * theta.cos(),
            y: r * theta.sin(),
        }
    }

    // __repr__
    fn __repr__(&self) -> String {
        format!("Point({}, {})", self.x, self.y)
    }

    // __str__
    fn __str__(&self) -> String {
        format!("({}, {})", self.x, self.y)
    }
}

#[pymodule]
fn geometry(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Point>()?;
    Ok(())
}
```

Python 使用：

```python
from geometry import Point

p1 = Point(3.0, 4.0)
p2 = Point.origin()  # 類別方法
p3 = Point.from_polar(5.0, 0.927)  # 靜態方法

print(p1)  # (3.0, 4.0)
print(repr(p1))  # Point(3.0, 4.0)
print(p1.distance(p2))  # 5.0

p1.x = 10.0  # setter
print(p1.x)  # getter
```

### 運算子重載

```rust
use pyo3::prelude::*;
use std::ops::{Add, Sub, Mul};

#[pyclass]
#[derive(Clone)]
struct Vector2D {
    x: f64,
    y: f64,
}

#[pymethods]
impl Vector2D {
    #[new]
    fn new(x: f64, y: f64) -> Self {
        Vector2D { x, y }
    }

    // __add__
    fn __add__(&self, other: &Vector2D) -> Vector2D {
        Vector2D {
            x: self.x + other.x,
            y: self.y + other.y,
        }
    }

    // __sub__
    fn __sub__(&self, other: &Vector2D) -> Vector2D {
        Vector2D {
            x: self.x - other.x,
            y: self.y - other.y,
        }
    }

    // __mul__（標量乘法）
    fn __mul__(&self, scalar: f64) -> Vector2D {
        Vector2D {
            x: self.x * scalar,
            y: self.y * scalar,
        }
    }

    // __rmul__（右乘）
    fn __rmul__(&self, scalar: f64) -> Vector2D {
        self.__mul__(scalar)
    }

    // __neg__
    fn __neg__(&self) -> Vector2D {
        Vector2D {
            x: -self.x,
            y: -self.y,
        }
    }

    // __eq__
    fn __eq__(&self, other: &Vector2D) -> bool {
        (self.x - other.x).abs() < 1e-10 &&
        (self.y - other.y).abs() < 1e-10
    }

    // __len__（向量維度）
    fn __len__(&self) -> usize {
        2
    }

    // __getitem__
    fn __getitem__(&self, index: usize) -> PyResult<f64> {
        match index {
            0 => Ok(self.x),
            1 => Ok(self.y),
            _ => Err(PyIndexError::new_err("Index out of range")),
        }
    }

    fn __repr__(&self) -> String {
        format!("Vector2D({}, {})", self.x, self.y)
    }
}
```

### 繼承與多型

```rust
use pyo3::prelude::*;

// 基礎類別
#[pyclass(subclass)]  // 允許被繼承
struct Animal {
    #[pyo3(get)]
    name: String,
}

#[pymethods]
impl Animal {
    #[new]
    fn new(name: String) -> Self {
        Animal { name }
    }

    // 可被覆寫的方法
    fn speak(&self) -> String {
        "...".to_string()
    }
}

// 子類別
#[pyclass(extends=Animal)]
struct Dog {}

#[pymethods]
impl Dog {
    #[new]
    fn new(name: String) -> (Self, Animal) {
        (Dog {}, Animal { name })
    }

    fn speak(&self) -> String {
        "Woof!".to_string()
    }
}

#[pyclass(extends=Animal)]
struct Cat {}

#[pymethods]
impl Cat {
    #[new]
    fn new(name: String) -> (Self, Animal) {
        (Cat {}, Animal { name })
    }

    fn speak(&self) -> String {
        "Meow!".to_string()
    }
}
```

---

## 【實作層】錯誤處理

### PyResult 與錯誤轉換

```rust
use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyTypeError, PyIOError};

// 回傳 PyResult
#[pyfunction]
fn safe_divide(a: f64, b: f64) -> PyResult<f64> {
    if b == 0.0 {
        Err(PyValueError::new_err("除數不能為零"))
    } else {
        Ok(a / b)
    }
}

// 自訂錯誤類型
use std::io;

fn read_file_internal(path: &str) -> Result<String, io::Error> {
    std::fs::read_to_string(path)
}

#[pyfunction]
fn read_file(path: &str) -> PyResult<String> {
    read_file_internal(path).map_err(|e| {
        PyIOError::new_err(format!("無法讀取檔案: {}", e))
    })
}

// 使用 ? 運算子
#[pyfunction]
fn parse_and_double(s: &str) -> PyResult<i64> {
    let num: i64 = s.parse().map_err(|_| {
        PyValueError::new_err(format!("無法解析為整數: {}", s))
    })?;
    Ok(num * 2)
}

// 自動轉換 Rust 錯誤
use thiserror::Error;

#[derive(Error, Debug)]
enum MyError {
    #[error("數值錯誤: {0}")]
    ValueError(String),
    #[error("IO 錯誤: {0}")]
    IoError(#[from] io::Error),
}

impl From<MyError> for PyErr {
    fn from(err: MyError) -> PyErr {
        match err {
            MyError::ValueError(msg) => PyValueError::new_err(msg),
            MyError::IoError(e) => PyIOError::new_err(e.to_string()),
        }
    }
}

#[pyfunction]
fn risky_operation(value: i64) -> Result<i64, MyError> {
    if value < 0 {
        Err(MyError::ValueError("負數不允許".to_string()))
    } else {
        Ok(value * 2)
    }
}
```

### 自訂異常

```rust
use pyo3::prelude::*;
use pyo3::create_exception;

// 建立自訂異常
create_exception!(my_module, ValidationError, pyo3::exceptions::PyException);
create_exception!(my_module, ProcessingError, pyo3::exceptions::PyException);

#[pyfunction]
fn validate_data(data: &str) -> PyResult<()> {
    if data.is_empty() {
        return Err(ValidationError::new_err("資料不能為空"));
    }
    if data.len() > 100 {
        return Err(ValidationError::new_err("資料太長"));
    }
    Ok(())
}

#[pymodule]
fn my_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("ValidationError", m.py().get_type::<ValidationError>())?;
    m.add("ProcessingError", m.py().get_type::<ProcessingError>())?;
    m.add_function(wrap_pyfunction!(validate_data, m)?)?;
    Ok(())
}
```

---

## 【實作層】GIL 管理

### 釋放 GIL

```rust
use pyo3::prelude::*;

// CPU 密集計算，應該釋放 GIL
#[pyfunction]
fn heavy_computation(n: u64) -> f64 {
    // 釋放 GIL，允許其他 Python 執行緒執行
    Python::with_gil(|py| {
        py.allow_threads(|| {
            // 這裡的程式碼不持有 GIL
            let mut result = 0.0;
            for i in 0..n {
                result += (i as f64).sin() * (i as f64).cos();
            }
            result
        })
    })
}

// 或者使用 Python 參數
#[pyfunction]
fn parallel_sum(py: Python<'_>, data: Vec<f64>) -> f64 {
    py.allow_threads(|| {
        // 可以安全地使用多執行緒
        use rayon::prelude::*;
        data.par_iter().sum()
    })
}
```

### 需要 GIL 的操作

```rust
use pyo3::prelude::*;

#[pyfunction]
fn callback_example(py: Python<'_>, callback: PyObject) -> PyResult<()> {
    // 模擬一些計算
    let results: Vec<i64> = py.allow_threads(|| {
        (0..10).map(|x| x * x).collect()
    });

    // 呼叫 Python 回呼需要 GIL
    for result in results {
        callback.call1(py, (result,))?;
    }

    Ok(())
}

#[pyfunction]
fn mixed_workload(py: Python<'_>, n: u64) -> PyResult<Vec<f64>> {
    let mut results = Vec::new();

    for i in 0..n {
        // 計算（釋放 GIL）
        let value = py.allow_threads(|| {
            (i as f64).sin()
        });

        // Python 互動（需要 GIL）
        results.push(value);

        // 定期檢查是否有 Python 訊號（如 Ctrl+C）
        if i % 1000 == 0 {
            py.check_signals()?;
        }
    }

    Ok(results)
}
```

---

## 【進階】與 NumPy 整合

### numpy crate

```toml
[dependencies]
pyo3 = { version = "0.23", features = ["extension-module"] }
numpy = "0.23"
ndarray = "0.16"
```

```rust
use pyo3::prelude::*;
use numpy::{PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use ndarray::{Array1, Array2};

// 接受 NumPy 陣列
#[pyfunction]
fn array_sum(arr: PyReadonlyArray1<'_, f64>) -> f64 {
    arr.as_array().sum()
}

// 回傳 NumPy 陣列
#[pyfunction]
fn create_range(py: Python<'_>, n: usize) -> Bound<'_, PyArray1<f64>> {
    let arr: Array1<f64> = Array1::from_iter((0..n).map(|x| x as f64));
    PyArray1::from_owned_array(py, arr)
}

// 處理 2D 陣列
#[pyfunction]
fn matrix_multiply<'py>(
    py: Python<'py>,
    a: PyReadonlyArray2<'py, f64>,
    b: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyArray2<f64>>> {
    let a = a.as_array();
    let b = b.as_array();

    // 檢查維度
    if a.ncols() != b.nrows() {
        return Err(PyValueError::new_err("矩陣維度不匹配"));
    }

    // 計算（釋放 GIL）
    let result = py.allow_threads(|| {
        a.dot(&b)
    });

    Ok(PyArray2::from_owned_array(py, result))
}

// 原地修改
#[pyfunction]
fn normalize_inplace(mut arr: PyReadwriteArray1<'_, f64>) {
    let mut arr = arr.as_array_mut();
    let sum: f64 = arr.sum();
    if sum != 0.0 {
        arr.mapv_inplace(|x| x / sum);
    }
}
```

---

## 思考題

1. PyO3 如何處理 Rust 的所有權系統和 Python 的垃圾回收之間的衝突？
2. 什麼時候應該使用 `py.allow_threads()`？有什麼風險？
3. 為什麼 PyO3 使用 `Bound<'_, T>` 而不是直接傳遞 Python 物件？

## 實作練習

1. 使用 PyO3 實現一個簡單的 Counter 類別，支援 `+`、`-`、`+=` 運算子
2. 實現一個接受 Python 回呼的函式，用於處理大量資料
3. 使用 numpy crate 實現一個高效能的向量運算函式

## 延伸閱讀

- [PyO3 User Guide](https://pyo3.rs/)
- [PyO3 API Documentation](https://docs.rs/pyo3/)
- [numpy crate](https://docs.rs/numpy/)
- [PyO3 Examples](https://github.com/PyO3/pyo3/tree/main/examples)

---

*上一章：[為什麼選擇 Rust？](../why-rust/)*
*下一章：[Maturin 開發流程](../maturin-workflow/)*
