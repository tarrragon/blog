---
title: "5.1 為什麼選擇 Rust？"
description: "比較 Rust 與 C/C++ 作為 Python 擴展語言"
weight: 1
---

# 為什麼選擇 Rust？

本章比較 Rust 與傳統 C/C++ 作為 Python 擴展語言的優缺點。

## 本章目標

學完本章後，你將能夠：

1. 理解 Rust 的記憶體安全保證
2. 評估 Rust vs C/C++ 的取捨
3. 認識使用 Rust 的知名 Python 專案

---

## 【原理層】Rust 的核心優勢

### 記憶體安全

Rust 透過所有權（Ownership）系統在編譯時保證記憶體安全：

```rust
// Rust 的所有權規則
fn main() {
    let s1 = String::from("hello");
    let s2 = s1;  // s1 的所有權轉移給 s2

    // println!("{}", s1);  // 編譯錯誤！s1 已經無效
    println!("{}", s2);     // OK
}

// 借用（Borrowing）
fn calculate_length(s: &String) -> usize {
    s.len()
}  // s 離開作用域，但不會釋放記憶體（只是借用）

fn main() {
    let s = String::from("hello");
    let len = calculate_length(&s);  // 借用 s
    println!("長度: {}, 字串: {}", len, s);  // s 仍然有效
}
```

與 C/C++ 的對比：

```c
// C 語言：常見的記憶體錯誤

// 1. Use After Free
char* ptr = malloc(100);
free(ptr);
printf("%s", ptr);  // 未定義行為！

// 2. Double Free
char* ptr = malloc(100);
free(ptr);
free(ptr);  // 未定義行為！

// 3. Buffer Overflow
char buffer[10];
strcpy(buffer, "This string is way too long!");  // 溢位！

// 4. Null Pointer Dereference
char* ptr = NULL;
printf("%c", *ptr);  // Crash!
```

```rust
// Rust：上述錯誤在編譯時就會被捕捉

// 1. Use After Free - 不可能
let s = String::from("hello");
drop(s);  // 明確釋放
// println!("{}", s);  // 編譯錯誤：value borrowed after move

// 2. Double Free - 不可能
// 所有權系統確保每個值只會被釋放一次

// 3. Buffer Overflow - 執行時檢查
let v = vec![1, 2, 3];
// v[10];  // 執行時 panic，不是未定義行為

// 4. Null Pointer - 使用 Option 類型
let maybe_value: Option<i32> = None;
// 必須明確處理 None 的情況
match maybe_value {
    Some(v) => println!("值: {}", v),
    None => println!("沒有值"),
}
```

### 並行安全

Rust 的類型系統在編譯時防止資料競爭：

```rust
use std::thread;

// ❌ 編譯錯誤：不能在多個執行緒中修改同一資料
fn wont_compile() {
    let mut data = vec![1, 2, 3];

    thread::spawn(|| {
        data.push(4);  // 錯誤：無法借用
    });

    data.push(5);
}

// ✅ 正確：使用 Arc 和 Mutex
use std::sync::{Arc, Mutex};

fn correct_approach() {
    let data = Arc::new(Mutex::new(vec![1, 2, 3]));
    let data_clone = Arc::clone(&data);

    let handle = thread::spawn(move || {
        let mut d = data_clone.lock().unwrap();
        d.push(4);
    });

    {
        let mut d = data.lock().unwrap();
        d.push(5);
    }

    handle.join().unwrap();
}
```

### 零成本抽象

高階語法不會帶來執行時開銷：

```rust
// 迭代器鏈式操作
let sum: i32 = (0..1000)
    .filter(|x| x % 2 == 0)
    .map(|x| x * x)
    .sum();

// 編譯後等同於手寫的迴圈
// 沒有額外的函式呼叫或記憶體分配
```

---

## 【比較】Rust vs C/C++

### 效能比較

```text
效能特性比較：

                    Rust        C           C++
────────────────────────────────────────────────────
執行速度            ⭐⭐⭐⭐⭐    ⭐⭐⭐⭐⭐    ⭐⭐⭐⭐⭐
編譯時間            ⭐⭐         ⭐⭐⭐⭐     ⭐⭐⭐
二進位大小          ⭐⭐⭐       ⭐⭐⭐⭐⭐    ⭐⭐⭐⭐
記憶體使用          ⭐⭐⭐⭐⭐    ⭐⭐⭐⭐⭐    ⭐⭐⭐⭐

說明：
- 執行速度三者相當（都編譯為原生機器碼）
- Rust 編譯時間較長（複雜的類型檢查）
- Rust 二進位可能較大（標準庫靜態連結）
```

### 開發體驗比較

```text
開發體驗：

                    Rust        C           C++
────────────────────────────────────────────────────
學習曲線            陡峭        中等         陡峭
除錯難度            較易        困難         困難
錯誤訊息            優秀        普通         差
套件管理 (Cargo)    ⭐⭐⭐⭐⭐    ❌           ⭐⭐
IDE 支援            ⭐⭐⭐⭐     ⭐⭐⭐⭐⭐    ⭐⭐⭐⭐⭐

說明：
- Rust 的學習曲線主要來自所有權系統
- Rust 的錯誤通常在編譯時發現，更容易修復
- Cargo 提供了優秀的套件管理和建構系統
```

### 安全性比較

```text
安全性：

問題類型              Rust                C/C++
──────────────────────────────────────────────────────
記憶體洩漏            可能（較少見）      常見
Use After Free        編譯時防止          常見
Buffer Overflow       執行時 panic        未定義行為
Null Pointer          使用 Option         常見 crash
Data Race             編譯時防止          常見
未初始化變數          編譯時防止          可能

Rust 的 unsafe：
- 可以繞過某些安全檢查
- 明確標記，易於審查
- 應該盡量減少使用
```

---

## 【案例】使用 Rust 的知名 Python 專案

### tiktoken（OpenAI）

```text
tiktoken - OpenAI 的 tokenizer

用途：
- GPT 模型的 token 編碼/解碼
- 處理大量文字資料

為什麼選擇 Rust：
- 效能要求高（處理大量請求）
- 需要處理各種邊界情況
- 記憶體安全很重要

效能數據：
- 比純 Python 實現快 3-10x
- 與 C++ 實現效能相當
```

### tokenizers（Hugging Face）

```text
tokenizers - Hugging Face 的 tokenizer 函式庫

用途：
- NLP 模型的 token 處理
- 支援多種 tokenization 演算法

特點：
- 純 Rust 核心
- PyO3 提供 Python 綁定
- 支援多種語言綁定（Node.js、Ruby 等）

為什麼選擇 Rust：
- 需要高效能的字串處理
- 需要安全地處理任意輸入
- 跨平台支援
```

### Polars

```text
Polars - 高效能 DataFrame 函式庫

用途：
- pandas 的替代方案
- 大規模資料處理

特點：
- 比 pandas 快 10-100x（某些操作）
- 惰性求值
- 多執行緒

為什麼選擇 Rust：
- 需要最佳效能
- 需要安全的並行處理
- Arrow 生態系統整合

使用範例：
import polars as pl

df = pl.read_csv("large_file.csv")
result = (
    df.lazy()
    .filter(pl.col("value") > 100)
    .group_by("category")
    .agg(pl.col("value").sum())
    .collect()
)
```

### Ruff

```text
Ruff - 超快的 Python linter

用途：
- Python 程式碼檢查
- 取代 flake8、isort、pyupgrade 等

特點：
- 比 flake8 快 10-100x
- 單一工具取代多個 linter

為什麼選擇 Rust：
- 需要處理大型程式碼庫
- 需要快速的回饋（IDE 整合）
- 字串處理效能關鍵

效能數據：
- CPython 程式碼庫（約 60 萬行）
- Ruff: 0.29 秒
- flake8: 22 秒
```

### pydantic-core

```text
pydantic-core - Pydantic v2 的核心

用途：
- 資料驗證和序列化
- 廣泛用於 FastAPI

特點：
- Pydantic v2 比 v1 快 5-50x
- 核心驗證邏輯用 Rust 重寫

為什麼選擇 Rust：
- 驗證邏輯被頻繁呼叫
- 需要處理各種邊界情況
- 需要安全地處理任意輸入
```

---

## 【評估】何時選擇 Rust

### 適合使用 Rust 的場景

```text
✅ 應該考慮 Rust：

1. 效能關鍵的程式碼
   - 大量數值計算
   - 頻繁呼叫的函式
   - 處理大型資料集

2. 需要安全地處理任意輸入
   - 解析使用者提供的資料
   - 網路協議處理
   - 檔案格式解析

3. 需要並行處理
   - 多執行緒計算
   - 非同步 I/O
   - 需要避免 GIL

4. 長期維護的核心函式庫
   - 減少記憶體相關 bug
   - 更容易重構
   - 跨語言共享

5. 跨平台發布
   - Rust 交叉編譯支援好
   - 減少平台特定 bug
```

### 不太適合 Rust 的場景

```text
❌ 可能不需要 Rust：

1. 快速原型開發
   - Python 本身就夠用
   - 學習成本高

2. 已有 C/C++ 程式碼
   - 直接用 pybind11 包裝
   - 除非需要大幅修改

3. 團隊不熟悉 Rust
   - 學習曲線陡峭
   - 維護成本考量

4. 效能不是瓶頸
   - 先用 profiler 確認
   - 可能 Python 優化就夠了

5. 只需要呼叫現有 C 函式庫
   - ctypes/cffi 更簡單
   - 不需要額外語言
```

### 決策流程

```text
需要 Python 擴展？
│
├── 有現有 C/C++ 程式碼？
│   ├── 是 → pybind11/Cython
│   └── 否 ↓
│
├── 效能是主要考量？
│   ├── 否 → 純 Python 或 Cython
│   └── 是 ↓
│
├── 需要並行安全？
│   ├── 是 → Rust (PyO3)
│   └── 否 ↓
│
├── 團隊熟悉 Rust？
│   ├── 是 → Rust (PyO3)
│   └── 否 → Cython 或學習 Rust
│
└── 長期維護的核心程式碼？
    ├── 是 → 考慮 Rust
    └── 否 → Cython 可能更實際
```

---

## 【入門】Rust 基礎概念

### 給 Python 開發者的快速入門

```rust
// 變數與型別
fn basics() {
    // 不可變變數（預設）
    let x = 5;
    // x = 6;  // 錯誤！

    // 可變變數
    let mut y = 5;
    y = 6;  // OK

    // 型別推斷
    let z = 10;       // i32
    let pi = 3.14;    // f64

    // 明確型別
    let a: i64 = 100;
    let b: f32 = 3.14;
}

// 函式
fn add(a: i32, b: i32) -> i32 {
    a + b  // 沒有分號 = 回傳值
}

// 結構體（類似 Python class）
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    // 關聯函式（類似 classmethod）
    fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }

    // 方法
    fn distance(&self, other: &Point) -> f64 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        (dx * dx + dy * dy).sqrt()
    }
}

// 列舉（比 Python enum 更強大）
enum Option<T> {
    Some(T),
    None,
}

enum Result<T, E> {
    Ok(T),
    Err(E),
}

// 模式匹配
fn handle_option(opt: Option<i32>) {
    match opt {
        Some(value) => println!("有值: {}", value),
        None => println!("沒有值"),
    }
}

// 迭代器（類似 Python generator）
fn iterators() {
    let v = vec![1, 2, 3, 4, 5];

    // 類似 Python 的 list comprehension
    let doubled: Vec<i32> = v.iter().map(|x| x * 2).collect();

    // 類似 Python 的 filter
    let evens: Vec<&i32> = v.iter().filter(|x| *x % 2 == 0).collect();
}
```

### Python vs Rust 語法對照

```text
Python                          Rust
──────────────────────────────────────────────────────
x = 5                           let x = 5;
x = 5  # mutable                let mut x = 5;
def foo(x):                     fn foo(x: i32) -> i32 {
    return x + 1                    x + 1
                                }
class Point:                    struct Point {
    def __init__(self, x, y):       x: f64,
        self.x = x                  y: f64,
        self.y = y              }
[x*2 for x in lst]              lst.iter().map(|x| x*2).collect()
if x is None:                   if x.is_none() {
    ...                             ...
for i in range(10):             for i in 0..10 {
    ...                             ...
try: ... except:                match result {
    ...                             Ok(v) => ...,
                                    Err(e) => ...,
                                }
```

---

## 思考題

1. Rust 的所有權系統如何與 Python 的垃圾回收協調？PyO3 如何處理這個問題？
2. 為什麼許多高效能 Python 函式庫選擇用 Rust 重寫而不是 C++？
3. 學習 Rust 對 Python 開發者有什麼長期價值？

## 實作練習

1. 安裝 Rust 並完成官方教學「rustlings」的前 20 個練習
2. 比較用 Python、Cython 和 Rust 實現 Fibonacci 函式的效能
3. 研究一個用 Rust 寫的 Python 函式庫（如 Polars），理解其專案結構

## 延伸閱讀

- [The Rust Programming Language](https://doc.rust-lang.org/book/)
- [Rust by Example](https://doc.rust-lang.org/rust-by-example/)
- [PyO3 User Guide](https://pyo3.rs/)
- [Are We Fast Yet? - Rust Performance Benchmarks](https://arewefastyet.rs/)

---

*下一章：[PyO3 基礎](../pyo3-basics/)*
