---
title: "5.4 實戰案例分析"
description: "分析知名 Python 專案如何使用 Rust"
weight: 4
---

# 實戰案例分析

本章分析幾個使用 Rust 的知名 Python 專案，學習實際應用的模式。

## 本章目標

學完本章後，你將能夠：

1. 理解 Rust 在數值計算的應用
2. 理解 Rust 在文字處理的應用
3. 評估自己的專案是否適合使用 Rust

---

## 【案例一】數值計算：實現快速排序

### 需求分析

```text
場景：需要對大量數值資料進行排序
問題：Python 內建排序雖然是 C 實現，但有特殊需求時需要自訂

實現目標：
├── 支援自訂比較函式
├── 支援並行排序（大資料集）
├── 與 NumPy 整合
└── 效能接近或超過 NumPy sort
```

### Rust 實現

```rust
// src/lib.rs
use pyo3::prelude::*;
use numpy::{PyArray1, PyReadonlyArray1};
use rayon::prelude::*;

/// 並行快速排序
#[pyfunction]
fn parallel_sort(py: Python<'_>, arr: PyReadonlyArray1<'_, f64>) -> Bound<'_, PyArray1<f64>> {
    let arr = arr.as_array();

    // 釋放 GIL 進行並行排序
    let mut data: Vec<f64> = py.allow_threads(|| {
        let mut data: Vec<f64> = arr.to_vec();
        data.par_sort_by(|a, b| a.partial_cmp(b).unwrap());
        data
    });

    PyArray1::from_vec(py, data)
}

/// 部分排序（只排序前 k 個元素）
#[pyfunction]
fn partial_sort(py: Python<'_>, arr: PyReadonlyArray1<'_, f64>, k: usize) -> PyResult<Bound<'_, PyArray1<f64>>> {
    let arr = arr.as_array();

    if k > arr.len() {
        return Err(PyValueError::new_err("k 大於陣列長度"));
    }

    let result = py.allow_threads(|| {
        let mut data: Vec<f64> = arr.to_vec();
        // 使用 select_nth_unstable 獲得前 k 個最小元素
        data.select_nth_unstable_by(k, |a, b| a.partial_cmp(b).unwrap());
        data[..k].to_vec()
    });

    Ok(PyArray1::from_vec(py, result))
}

/// 找出 top-k 元素（不完全排序，更快）
#[pyfunction]
fn top_k(py: Python<'_>, arr: PyReadonlyArray1<'_, f64>, k: usize) -> PyResult<Bound<'_, PyArray1<f64>>> {
    use std::collections::BinaryHeap;
    use std::cmp::Ordering;

    // 包裝 f64 以支援 BinaryHeap
    #[derive(PartialEq)]
    struct MinFloat(f64);

    impl Eq for MinFloat {}

    impl PartialOrd for MinFloat {
        fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
            // 反向比較，使 BinaryHeap 成為 min-heap
            other.0.partial_cmp(&self.0)
        }
    }

    impl Ord for MinFloat {
        fn cmp(&self, other: &Self) -> Ordering {
            self.partial_cmp(other).unwrap()
        }
    }

    let arr = arr.as_array();

    let result = py.allow_threads(|| {
        let mut heap: BinaryHeap<MinFloat> = BinaryHeap::with_capacity(k + 1);

        for &x in arr.iter() {
            heap.push(MinFloat(x));
            if heap.len() > k {
                heap.pop();
            }
        }

        heap.into_sorted_vec().into_iter().map(|x| x.0).collect::<Vec<_>>()
    });

    Ok(PyArray1::from_vec(py, result))
}

#[pymodule]
fn fast_sort(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parallel_sort, m)?)?;
    m.add_function(wrap_pyfunction!(partial_sort, m)?)?;
    m.add_function(wrap_pyfunction!(top_k, m)?)?;
    Ok(())
}
```

### 效能比較

```python
import numpy as np
import fast_sort
import timeit

# 測試資料
n = 1_000_000
data = np.random.rand(n)

# NumPy sort
t_numpy = timeit.timeit(lambda: np.sort(data.copy()), number=10)

# Rust parallel sort
t_rust = timeit.timeit(lambda: fast_sort.parallel_sort(data), number=10)

# 找 top-1000（Rust）
t_topk_rust = timeit.timeit(lambda: fast_sort.top_k(data, 1000), number=10)

# 找 top-1000（NumPy: 完整排序後取前 k）
t_topk_numpy = timeit.timeit(lambda: np.sort(data)[:1000], number=10)

print(f"完整排序 - NumPy: {t_numpy:.3f}s, Rust: {t_rust:.3f}s")
print(f"Top-1000 - NumPy: {t_topk_numpy:.3f}s, Rust: {t_topk_rust:.3f}s")

# 預期結果（依硬體而異）：
# 完整排序 - NumPy: 0.85s, Rust: 0.45s（使用多核心）
# Top-1000 - NumPy: 0.85s, Rust: 0.02s（不需完整排序）
```

---

## 【案例二】文字處理：高效能 Tokenizer

### 需求分析

```text
場景：NLP 應用需要將文字切分為 tokens
問題：純 Python 實現太慢，無法處理大量文字

實現目標：
├── 支援 Unicode
├── 支援正規表達式模式
├── 批次處理
└── 與現有 NLP 工具整合
```

### Rust 實現

```rust
// src/lib.rs
use pyo3::prelude::*;
use regex::Regex;
use rayon::prelude::*;

#[pyclass]
struct Tokenizer {
    pattern: Regex,
    lowercase: bool,
}

#[pymethods]
impl Tokenizer {
    #[new]
    #[pyo3(signature = (pattern=r"\w+", lowercase=true))]
    fn new(pattern: &str, lowercase: bool) -> PyResult<Self> {
        let pattern = Regex::new(pattern)
            .map_err(|e| PyValueError::new_err(format!("無效的正規表達式: {}", e)))?;
        Ok(Tokenizer { pattern, lowercase })
    }

    /// 對單一字串進行 tokenization
    fn tokenize(&self, text: &str) -> Vec<String> {
        self.pattern
            .find_iter(text)
            .map(|m| {
                let s = m.as_str();
                if self.lowercase {
                    s.to_lowercase()
                } else {
                    s.to_string()
                }
            })
            .collect()
    }

    /// 批次 tokenization（並行處理）
    fn tokenize_batch(&self, py: Python<'_>, texts: Vec<String>) -> Vec<Vec<String>> {
        py.allow_threads(|| {
            texts
                .par_iter()
                .map(|text| self.tokenize(text))
                .collect()
        })
    }

    /// 計算詞頻
    fn count_tokens(&self, py: Python<'_>, text: &str) -> HashMap<String, usize> {
        use std::collections::HashMap;

        py.allow_threads(|| {
            let mut counts = HashMap::new();
            for mat in self.pattern.find_iter(text) {
                let token = if self.lowercase {
                    mat.as_str().to_lowercase()
                } else {
                    mat.as_str().to_string()
                };
                *counts.entry(token).or_insert(0) += 1;
            }
            counts
        })
    }
}

// 簡單的 BPE（Byte Pair Encoding）實現
#[pyclass]
struct SimpleBPE {
    vocab: HashMap<String, u32>,
    merges: Vec<(String, String)>,
}

#[pymethods]
impl SimpleBPE {
    #[new]
    fn new() -> Self {
        SimpleBPE {
            vocab: HashMap::new(),
            merges: Vec::new(),
        }
    }

    /// 訓練 BPE
    fn train(&mut self, py: Python<'_>, texts: Vec<String>, vocab_size: usize) {
        use std::collections::HashMap;

        py.allow_threads(|| {
            // 初始化：每個字元是一個 token
            let mut word_freqs: HashMap<Vec<String>, usize> = HashMap::new();

            for text in &texts {
                for word in text.split_whitespace() {
                    let chars: Vec<String> = word.chars().map(|c| c.to_string()).collect();
                    *word_freqs.entry(chars).or_insert(0) += 1;
                }
            }

            // 迭代合併最頻繁的 pair
            while self.vocab.len() < vocab_size {
                // 計算 pair 頻率
                let mut pair_freqs: HashMap<(String, String), usize> = HashMap::new();

                for (word, freq) in &word_freqs {
                    for i in 0..word.len().saturating_sub(1) {
                        let pair = (word[i].clone(), word[i + 1].clone());
                        *pair_freqs.entry(pair).or_insert(0) += freq;
                    }
                }

                // 找出最頻繁的 pair
                if let Some((best_pair, _)) = pair_freqs.iter().max_by_key(|(_, &freq)| freq) {
                    let new_token = format!("{}{}", best_pair.0, best_pair.1);
                    self.merges.push(best_pair.clone());
                    self.vocab.insert(new_token.clone(), self.vocab.len() as u32);

                    // 更新 word_freqs
                    let mut new_word_freqs = HashMap::new();
                    for (word, freq) in word_freqs {
                        let mut new_word = Vec::new();
                        let mut i = 0;
                        while i < word.len() {
                            if i + 1 < word.len() && word[i] == best_pair.0 && word[i + 1] == best_pair.1 {
                                new_word.push(new_token.clone());
                                i += 2;
                            } else {
                                new_word.push(word[i].clone());
                                i += 1;
                            }
                        }
                        *new_word_freqs.entry(new_word).or_insert(0) += freq;
                    }
                    word_freqs = new_word_freqs;
                } else {
                    break;
                }
            }
        });
    }

    /// 編碼文字
    fn encode(&self, text: &str) -> Vec<u32> {
        let mut tokens: Vec<String> = text.chars().map(|c| c.to_string()).collect();

        for (a, b) in &self.merges {
            let merged = format!("{}{}", a, b);
            let mut new_tokens = Vec::new();
            let mut i = 0;
            while i < tokens.len() {
                if i + 1 < tokens.len() && &tokens[i] == a && &tokens[i + 1] == b {
                    new_tokens.push(merged.clone());
                    i += 2;
                } else {
                    new_tokens.push(tokens[i].clone());
                    i += 1;
                }
            }
            tokens = new_tokens;
        }

        tokens
            .iter()
            .filter_map(|t| self.vocab.get(t).copied())
            .collect()
    }
}

use std::collections::HashMap;

#[pymodule]
fn fast_tokenizer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Tokenizer>()?;
    m.add_class::<SimpleBPE>()?;
    Ok(())
}
```

### 使用範例

```python
from fast_tokenizer import Tokenizer, SimpleBPE

# 基本 tokenization
tokenizer = Tokenizer(r"\w+", lowercase=True)

text = "Hello, World! This is a test."
tokens = tokenizer.tokenize(text)
print(tokens)  # ['hello', 'world', 'this', 'is', 'a', 'test']

# 批次處理
texts = ["First sentence.", "Second sentence.", "Third one."]
batch_tokens = tokenizer.tokenize_batch(texts)
print(batch_tokens)

# 詞頻統計
counts = tokenizer.count_tokens("the cat sat on the mat")
print(counts)  # {'the': 2, 'cat': 1, 'sat': 1, 'on': 1, 'mat': 1}

# BPE 訓練
bpe = SimpleBPE()
corpus = ["hello world", "hello there", "world peace"]
bpe.train(corpus, vocab_size=100)
encoded = bpe.encode("hello world")
print(encoded)
```

---

## 【案例三】資料驗證：Pydantic 風格驗證器

### 需求分析

```text
場景：API 需要驗證大量輸入資料
問題：純 Python 驗證太慢（Pydantic v1 的問題）

實現目標：
├── 型別檢查
├── 範圍驗證
├── 自訂驗證函式
└── 清晰的錯誤訊息
```

### Rust 實現

```rust
// src/lib.rs
use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use std::collections::HashMap;

// 驗證錯誤
#[pyclass]
#[derive(Clone)]
struct ValidationError {
    #[pyo3(get)]
    field: String,
    #[pyo3(get)]
    message: String,
}

#[pymethods]
impl ValidationError {
    fn __repr__(&self) -> String {
        format!("ValidationError(field='{}', message='{}')", self.field, self.message)
    }
}

// 欄位驗證器
#[pyclass]
struct Field {
    name: String,
    field_type: String,
    required: bool,
    min_value: Option<f64>,
    max_value: Option<f64>,
    min_length: Option<usize>,
    max_length: Option<usize>,
    pattern: Option<regex::Regex>,
}

#[pymethods]
impl Field {
    #[new]
    #[pyo3(signature = (name, field_type, required=true, min_value=None, max_value=None, min_length=None, max_length=None, pattern=None))]
    fn new(
        name: String,
        field_type: String,
        required: bool,
        min_value: Option<f64>,
        max_value: Option<f64>,
        min_length: Option<usize>,
        max_length: Option<usize>,
        pattern: Option<String>,
    ) -> PyResult<Self> {
        let pattern = match pattern {
            Some(p) => Some(regex::Regex::new(&p)
                .map_err(|e| PyValueError::new_err(format!("無效的正規表達式: {}", e)))?),
            None => None,
        };

        Ok(Field {
            name,
            field_type,
            required,
            min_value,
            max_value,
            min_length,
            max_length,
            pattern,
        })
    }
}

// Schema 驗證器
#[pyclass]
struct Schema {
    fields: Vec<Field>,
}

#[pymethods]
impl Schema {
    #[new]
    fn new(fields: Vec<Py<Field>>) -> PyResult<Self> {
        Python::with_gil(|py| {
            let fields: Vec<Field> = fields
                .iter()
                .map(|f| f.borrow(py).clone())
                .collect();
            Ok(Schema { fields })
        })
    }

    /// 驗證單一物件
    fn validate(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<Vec<ValidationError>> {
        let mut errors = Vec::new();

        for field in &self.fields {
            let value = data.get_item(&field.name)?;

            match value {
                None => {
                    if field.required {
                        errors.push(ValidationError {
                            field: field.name.clone(),
                            message: "此欄位為必填".to_string(),
                        });
                    }
                }
                Some(v) => {
                    // 型別檢查
                    match field.field_type.as_str() {
                        "int" => {
                            if let Ok(num) = v.extract::<i64>() {
                                // 範圍檢查
                                if let Some(min) = field.min_value {
                                    if (num as f64) < min {
                                        errors.push(ValidationError {
                                            field: field.name.clone(),
                                            message: format!("值必須 >= {}", min),
                                        });
                                    }
                                }
                                if let Some(max) = field.max_value {
                                    if (num as f64) > max {
                                        errors.push(ValidationError {
                                            field: field.name.clone(),
                                            message: format!("值必須 <= {}", max),
                                        });
                                    }
                                }
                            } else {
                                errors.push(ValidationError {
                                    field: field.name.clone(),
                                    message: "必須是整數".to_string(),
                                });
                            }
                        }
                        "float" => {
                            if let Ok(num) = v.extract::<f64>() {
                                if let Some(min) = field.min_value {
                                    if num < min {
                                        errors.push(ValidationError {
                                            field: field.name.clone(),
                                            message: format!("值必須 >= {}", min),
                                        });
                                    }
                                }
                                if let Some(max) = field.max_value {
                                    if num > max {
                                        errors.push(ValidationError {
                                            field: field.name.clone(),
                                            message: format!("值必須 <= {}", max),
                                        });
                                    }
                                }
                            } else {
                                errors.push(ValidationError {
                                    field: field.name.clone(),
                                    message: "必須是浮點數".to_string(),
                                });
                            }
                        }
                        "str" => {
                            if let Ok(s) = v.extract::<String>() {
                                // 長度檢查
                                if let Some(min_len) = field.min_length {
                                    if s.len() < min_len {
                                        errors.push(ValidationError {
                                            field: field.name.clone(),
                                            message: format!("長度必須 >= {}", min_len),
                                        });
                                    }
                                }
                                if let Some(max_len) = field.max_length {
                                    if s.len() > max_len {
                                        errors.push(ValidationError {
                                            field: field.name.clone(),
                                            message: format!("長度必須 <= {}", max_len),
                                        });
                                    }
                                }
                                // 正規表達式檢查
                                if let Some(ref pattern) = field.pattern {
                                    if !pattern.is_match(&s) {
                                        errors.push(ValidationError {
                                            field: field.name.clone(),
                                            message: "格式不符合要求".to_string(),
                                        });
                                    }
                                }
                            } else {
                                errors.push(ValidationError {
                                    field: field.name.clone(),
                                    message: "必須是字串".to_string(),
                                });
                            }
                        }
                        _ => {}
                    }
                }
            }
        }

        Ok(errors)
    }

    /// 批次驗證
    fn validate_batch(&self, py: Python<'_>, data_list: Vec<Bound<'_, PyDict>>) -> PyResult<Vec<Vec<ValidationError>>> {
        let mut results = Vec::new();
        for data in data_list {
            results.push(self.validate(py, &data)?);
        }
        Ok(results)
    }
}

use pyo3::types::PyDict;

#[pymodule]
fn fast_validator(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Field>()?;
    m.add_class::<Schema>()?;
    m.add_class::<ValidationError>()?;
    Ok(())
}
```

### 使用範例

```python
from fast_validator import Field, Schema

# 定義 schema
schema = Schema([
    Field("name", "str", required=True, min_length=1, max_length=100),
    Field("age", "int", required=True, min_value=0, max_value=150),
    Field("email", "str", required=True, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$"),
    Field("score", "float", required=False, min_value=0, max_value=100),
])

# 驗證資料
data = {"name": "Alice", "age": 30, "email": "alice@example.com"}
errors = schema.validate(data)
if errors:
    for e in errors:
        print(f"{e.field}: {e.message}")
else:
    print("驗證通過")

# 無效資料
invalid_data = {"name": "", "age": -5, "email": "invalid"}
errors = schema.validate(invalid_data)
for e in errors:
    print(f"{e.field}: {e.message}")
# name: 長度必須 >= 1
# age: 值必須 >= 0
# email: 格式不符合要求
```

---

## 【總結】何時使用 Rust

### 決策清單

```text
✅ 應該使用 Rust：

1. 效能瓶頸明確
   □ profiler 顯示特定函式占用大量時間
   □ 純 Python 優化已到極限
   □ 現有 C 擴展不滿足需求

2. 資料處理需求
   □ 大量數值計算
   □ 頻繁的字串處理
   □ 需要並行處理

3. 安全性要求
   □ 處理不可信的輸入
   □ 需要避免記憶體錯誤
   □ 長期運行的服務

4. 跨平台需求
   □ 需要支援多個作業系統
   □ 需要支援多個 Python 版本

❌ 可能不需要 Rust：

1. 效能不是主要瓶頸
2. 團隊沒有 Rust 經驗且時間緊迫
3. 專案規模小且不會長期維護
4. 可以用現有函式庫解決
```

### 最佳實踐

```text
1. 設計階段
   ├── 明確定義 Python/Rust 邊界
   ├── 最小化跨語言呼叫次數
   ├── 使用批次處理減少開銷
   └── 設計清晰的錯誤處理

2. 開發階段
   ├── 先用 Python 原型驗證邏輯
   ├── 逐步將瓶頸移到 Rust
   ├── 完善的測試覆蓋
   └── 使用 maturin develop 快速迭代

3. 發布階段
   ├── 使用 CI/CD 自動建構 wheel
   ├── 支援主流 Python 版本
   ├── 提供 fallback 純 Python 實現
   └── 清楚的安裝文件
```

---

## 思考題

1. 在設計 Rust 擴展的 API 時，如何平衡效能和易用性？
2. 如何處理 Rust 函式庫沒有 Python 綁定的情況？
3. 在什麼情況下，應該用 Cython 而不是 Rust？

## 實作練習

1. 選擇一個你常用的純 Python 函式，用 Rust 重寫並比較效能
2. 分析 [Polars](https://github.com/pola-rs/polars) 的原始碼結構，理解大型 Rust Python 專案的組織方式
3. 實現一個簡單的 JSON parser，比較與 Python `json` 模組的效能差異

## 延伸閱讀

- [Polars 原始碼](https://github.com/pola-rs/polars)
- [Ruff 原始碼](https://github.com/astral-sh/ruff)
- [tiktoken 原始碼](https://github.com/openai/tiktoken)
- [pydantic-core 原始碼](https://github.com/pydantic/pydantic-core)

---

*上一章：[Maturin 開發流程](../maturin-workflow/)*
*下一模組：[模組六：打包與發布](../../06-packaging/)*
