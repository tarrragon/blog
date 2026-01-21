---
title: "案例：pybind11 綁定 C++ 類別"
date: 2026-01-21
description: "用 pybind11 將 C++ 類別綁定到 Python，展示建構子、方法、屬性、運算子重載與記憶體管理"
weight: 3
---

# 案例：pybind11 綁定 C++ 類別

本案例展示如何使用 pybind11 將 C++ 類別完整綁定到 Python，包含建構子、方法、屬性、運算子重載，以及記憶體管理與生命週期控制。

## 先備知識

- [4.3 pybind11：現代 C++ 綁定](../../pybind11/)
- [模組五：用 C 擴展 Python](../../)

## 問題背景

### 使用情境

在以下情境中，你可能需要在 Python 中使用 C++ 類別：

1. **複用現有 C++ 程式庫**：公司有成熟的 C++ 資料結構或演算法，想在 Python 專案中使用
2. **效能敏感的資料處理**：需要高效的記憶體管理和計算效能
3. **自訂資料結構**：標準 Python 容器無法滿足特定需求

### 設計目標

本案例將建立一個 `StringProcessor` 類別，展示：

```text
StringProcessor 功能：
├── 建構子：支援預設和參數化初始化
├── 方法：字串處理（大小寫轉換、統計、搜尋）
├── 屬性：可讀寫的狀態屬性
├── 運算子重載：+ 運算子串接、[] 索引存取
├── 記憶體管理：正確處理物件生命週期
└── 效能優化：避免不必要的記憶體複製
```

## 實作步驟

### 步驟 1：專案結構

```text
pybind11_string_processor/
├── CMakeLists.txt
├── setup.py
├── src/
│   ├── string_processor.hpp    # C++ 標頭檔
│   ├── string_processor.cpp    # C++ 實作
│   └── bindings.cpp            # pybind11 綁定
├── tests/
│   └── test_string_processor.py
└── benchmark.py
```

### 步驟 2：C++ 類別定義

首先，建立 C++ 類別的標頭檔：

```cpp
// src/string_processor.hpp
#ifndef STRING_PROCESSOR_HPP
#define STRING_PROCESSOR_HPP

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <stdexcept>

/**
 * StringProcessor: 高效能字串處理類別
 *
 * 提供字串操作、統計分析和搜尋功能。
 * 設計用於展示 pybind11 的類別綁定特性。
 */
class StringProcessor {
public:
    // ========================================
    // 建構子與解構子
    // ========================================

    // 預設建構子
    StringProcessor();

    // 參數化建構子
    explicit StringProcessor(const std::string& content);

    // 複製建構子
    StringProcessor(const StringProcessor& other);

    // 移動建構子
    StringProcessor(StringProcessor&& other) noexcept;

    // 解構子
    ~StringProcessor();

    // ========================================
    // 基本方法
    // ========================================

    // 取得內容
    const std::string& content() const { return content_; }

    // 設定內容
    void set_content(const std::string& content);

    // 取得長度
    size_t length() const { return content_.length(); }

    // 是否為空
    bool empty() const { return content_.empty(); }

    // ========================================
    // 字串處理方法
    // ========================================

    // 轉換為大寫
    std::string to_upper() const;

    // 轉換為小寫
    std::string to_lower() const;

    // 反轉字串
    std::string reverse() const;

    // 移除前後空白
    std::string trim() const;

    // 分割字串
    std::vector<std::string> split(const std::string& delimiter = " ") const;

    // 取代子字串
    std::string replace(const std::string& old_str,
                        const std::string& new_str) const;

    // ========================================
    // 統計分析方法
    // ========================================

    // 字元頻率統計
    std::unordered_map<char, int> char_frequency() const;

    // 單字計數
    size_t word_count() const;

    // 子字串出現次數
    size_t count_occurrences(const std::string& substring) const;

    // ========================================
    // 搜尋方法
    // ========================================

    // 搜尋子字串位置（找不到回傳 -1）
    int find(const std::string& substring, size_t start = 0) const;

    // 搜尋所有出現位置
    std::vector<size_t> find_all(const std::string& substring) const;

    // 是否包含子字串
    bool contains(const std::string& substring) const;

    // 是否以指定字串開頭
    bool starts_with(const std::string& prefix) const;

    // 是否以指定字串結尾
    bool ends_with(const std::string& suffix) const;

    // ========================================
    // 運算子重載
    // ========================================

    // + 運算子：串接
    StringProcessor operator+(const StringProcessor& other) const;

    // += 運算子：原地串接
    StringProcessor& operator+=(const StringProcessor& other);

    // [] 運算子：索引存取
    char operator[](size_t index) const;

    // == 運算子：相等比較
    bool operator==(const StringProcessor& other) const;

    // != 運算子：不等比較
    bool operator!=(const StringProcessor& other) const;

    // ========================================
    // 指派運算子
    // ========================================

    StringProcessor& operator=(const StringProcessor& other);
    StringProcessor& operator=(StringProcessor&& other) noexcept;

private:
    std::string content_;

    // 處理計數器（用於展示狀態追蹤）
    mutable size_t operation_count_ = 0;

    // 輔助方法
    void increment_operation_count() const { ++operation_count_; }

public:
    // 取得操作計數（用於效能分析）
    size_t operation_count() const { return operation_count_; }
    void reset_operation_count() { operation_count_ = 0; }
};

#endif // STRING_PROCESSOR_HPP
```

### 步驟 3：C++ 實作

```cpp
// src/string_processor.cpp
#include "string_processor.hpp"
#include <algorithm>
#include <cctype>
#include <sstream>

// ========================================
// 建構子與解構子
// ========================================

StringProcessor::StringProcessor() : content_("") {}

StringProcessor::StringProcessor(const std::string& content)
    : content_(content) {}

StringProcessor::StringProcessor(const StringProcessor& other)
    : content_(other.content_), operation_count_(0) {}

StringProcessor::StringProcessor(StringProcessor&& other) noexcept
    : content_(std::move(other.content_)), operation_count_(0) {
    other.content_.clear();
}

StringProcessor::~StringProcessor() = default;

// ========================================
// 基本方法
// ========================================

void StringProcessor::set_content(const std::string& content) {
    content_ = content;
    increment_operation_count();
}

// ========================================
// 字串處理方法
// ========================================

std::string StringProcessor::to_upper() const {
    increment_operation_count();
    std::string result = content_;
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::toupper(c); });
    return result;
}

std::string StringProcessor::to_lower() const {
    increment_operation_count();
    std::string result = content_;
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

std::string StringProcessor::reverse() const {
    increment_operation_count();
    std::string result = content_;
    std::reverse(result.begin(), result.end());
    return result;
}

std::string StringProcessor::trim() const {
    increment_operation_count();
    size_t start = content_.find_first_not_of(" \t\n\r\f\v");
    if (start == std::string::npos) {
        return "";
    }
    size_t end = content_.find_last_not_of(" \t\n\r\f\v");
    return content_.substr(start, end - start + 1);
}

std::vector<std::string> StringProcessor::split(const std::string& delimiter) const {
    increment_operation_count();
    std::vector<std::string> result;

    if (delimiter.empty()) {
        // 空分隔符：按字元分割
        for (char c : content_) {
            result.push_back(std::string(1, c));
        }
        return result;
    }

    size_t start = 0;
    size_t end = content_.find(delimiter);

    while (end != std::string::npos) {
        result.push_back(content_.substr(start, end - start));
        start = end + delimiter.length();
        end = content_.find(delimiter, start);
    }

    result.push_back(content_.substr(start));
    return result;
}

std::string StringProcessor::replace(const std::string& old_str,
                                     const std::string& new_str) const {
    increment_operation_count();
    if (old_str.empty()) {
        return content_;
    }

    std::string result = content_;
    size_t pos = 0;
    while ((pos = result.find(old_str, pos)) != std::string::npos) {
        result.replace(pos, old_str.length(), new_str);
        pos += new_str.length();
    }
    return result;
}

// ========================================
// 統計分析方法
// ========================================

std::unordered_map<char, int> StringProcessor::char_frequency() const {
    increment_operation_count();
    std::unordered_map<char, int> freq;
    for (char c : content_) {
        freq[c]++;
    }
    return freq;
}

size_t StringProcessor::word_count() const {
    increment_operation_count();
    if (content_.empty()) {
        return 0;
    }

    std::istringstream iss(content_);
    size_t count = 0;
    std::string word;
    while (iss >> word) {
        count++;
    }
    return count;
}

size_t StringProcessor::count_occurrences(const std::string& substring) const {
    increment_operation_count();
    if (substring.empty()) {
        return 0;
    }

    size_t count = 0;
    size_t pos = 0;
    while ((pos = content_.find(substring, pos)) != std::string::npos) {
        count++;
        pos += substring.length();
    }
    return count;
}

// ========================================
// 搜尋方法
// ========================================

int StringProcessor::find(const std::string& substring, size_t start) const {
    increment_operation_count();
    size_t pos = content_.find(substring, start);
    return (pos == std::string::npos) ? -1 : static_cast<int>(pos);
}

std::vector<size_t> StringProcessor::find_all(const std::string& substring) const {
    increment_operation_count();
    std::vector<size_t> positions;
    if (substring.empty()) {
        return positions;
    }

    size_t pos = 0;
    while ((pos = content_.find(substring, pos)) != std::string::npos) {
        positions.push_back(pos);
        pos += substring.length();
    }
    return positions;
}

bool StringProcessor::contains(const std::string& substring) const {
    increment_operation_count();
    return content_.find(substring) != std::string::npos;
}

bool StringProcessor::starts_with(const std::string& prefix) const {
    increment_operation_count();
    if (prefix.length() > content_.length()) {
        return false;
    }
    return content_.compare(0, prefix.length(), prefix) == 0;
}

bool StringProcessor::ends_with(const std::string& suffix) const {
    increment_operation_count();
    if (suffix.length() > content_.length()) {
        return false;
    }
    return content_.compare(content_.length() - suffix.length(),
                            suffix.length(), suffix) == 0;
}

// ========================================
// 運算子重載
// ========================================

StringProcessor StringProcessor::operator+(const StringProcessor& other) const {
    increment_operation_count();
    return StringProcessor(content_ + other.content_);
}

StringProcessor& StringProcessor::operator+=(const StringProcessor& other) {
    increment_operation_count();
    content_ += other.content_;
    return *this;
}

char StringProcessor::operator[](size_t index) const {
    increment_operation_count();
    if (index >= content_.length()) {
        throw std::out_of_range("Index out of range: " + std::to_string(index));
    }
    return content_[index];
}

bool StringProcessor::operator==(const StringProcessor& other) const {
    return content_ == other.content_;
}

bool StringProcessor::operator!=(const StringProcessor& other) const {
    return content_ != other.content_;
}

// ========================================
// 指派運算子
// ========================================

StringProcessor& StringProcessor::operator=(const StringProcessor& other) {
    if (this != &other) {
        content_ = other.content_;
        operation_count_ = 0;
    }
    return *this;
}

StringProcessor& StringProcessor::operator=(StringProcessor&& other) noexcept {
    if (this != &other) {
        content_ = std::move(other.content_);
        operation_count_ = 0;
        other.content_.clear();
    }
    return *this;
}
```

### 步驟 4：pybind11 綁定

這是最關鍵的部分，將 C++ 類別暴露給 Python：

```cpp
// src/bindings.cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>  // 支援 STL 容器自動轉換
#include <pybind11/operators.h>  // 支援運算子重載

#include "string_processor.hpp"

namespace py = pybind11;

PYBIND11_MODULE(string_processor, m) {
    m.doc() = "StringProcessor: 高效能字串處理模組";

    // ========================================
    // 類別綁定
    // ========================================
    py::class_<StringProcessor>(m, "StringProcessor")
        // ----------------------------------------
        // 建構子
        // ----------------------------------------
        .def(py::init<>(), "建立空的 StringProcessor")
        .def(py::init<const std::string&>(),
             py::arg("content"),
             "使用指定內容建立 StringProcessor")

        // 複製建構（Python 的 copy 模組會使用）
        .def(py::init<const StringProcessor&>())

        // ----------------------------------------
        // 屬性
        // ----------------------------------------
        // content 屬性：可讀寫
        .def_property("content",
                      &StringProcessor::content,
                      &StringProcessor::set_content,
                      "字串內容")

        // 唯讀屬性
        .def_property_readonly("length",
                               &StringProcessor::length,
                               "字串長度")
        .def_property_readonly("empty",
                               &StringProcessor::empty,
                               "是否為空")
        .def_property_readonly("operation_count",
                               &StringProcessor::operation_count,
                               "操作計數器")

        // ----------------------------------------
        // 基本方法
        // ----------------------------------------
        .def("reset_operation_count",
             &StringProcessor::reset_operation_count,
             "重置操作計數器")

        // ----------------------------------------
        // 字串處理方法
        // ----------------------------------------
        .def("to_upper",
             &StringProcessor::to_upper,
             "轉換為大寫")
        .def("to_lower",
             &StringProcessor::to_lower,
             "轉換為小寫")
        .def("reverse",
             &StringProcessor::reverse,
             "反轉字串")
        .def("trim",
             &StringProcessor::trim,
             "移除前後空白")
        .def("split",
             &StringProcessor::split,
             py::arg("delimiter") = " ",
             "以分隔符分割字串")
        .def("replace",
             &StringProcessor::replace,
             py::arg("old_str"),
             py::arg("new_str"),
             "取代子字串")

        // ----------------------------------------
        // 統計分析方法
        // ----------------------------------------
        .def("char_frequency",
             &StringProcessor::char_frequency,
             "統計字元頻率")
        .def("word_count",
             &StringProcessor::word_count,
             "計算單字數量")
        .def("count_occurrences",
             &StringProcessor::count_occurrences,
             py::arg("substring"),
             "計算子字串出現次數")

        // ----------------------------------------
        // 搜尋方法
        // ----------------------------------------
        .def("find",
             &StringProcessor::find,
             py::arg("substring"),
             py::arg("start") = 0,
             "搜尋子字串位置（找不到回傳 -1）")
        .def("find_all",
             &StringProcessor::find_all,
             py::arg("substring"),
             "搜尋所有出現位置")
        .def("contains",
             &StringProcessor::contains,
             py::arg("substring"),
             "是否包含子字串")
        .def("starts_with",
             &StringProcessor::starts_with,
             py::arg("prefix"),
             "是否以指定字串開頭")
        .def("ends_with",
             &StringProcessor::ends_with,
             py::arg("suffix"),
             "是否以指定字串結尾")

        // ----------------------------------------
        // 運算子重載
        // ----------------------------------------

        // + 運算子：StringProcessor + StringProcessor
        .def(py::self + py::self)

        // += 運算子
        .def(py::self += py::self)

        // == 和 != 運算子
        .def(py::self == py::self)
        .def(py::self != py::self)

        // [] 運算子：索引存取
        .def("__getitem__",
             &StringProcessor::operator[],
             py::arg("index"),
             "取得指定位置的字元")

        // ----------------------------------------
        // Python 特殊方法
        // ----------------------------------------

        // __repr__：物件表示
        .def("__repr__",
             [](const StringProcessor& sp) {
                 std::string repr = "<StringProcessor content='";
                 if (sp.length() > 50) {
                     repr += sp.content().substr(0, 47) + "...";
                 } else {
                     repr += sp.content();
                 }
                 repr += "' length=" + std::to_string(sp.length()) + ">";
                 return repr;
             })

        // __str__：字串轉換
        .def("__str__",
             [](const StringProcessor& sp) {
                 return sp.content();
             })

        // __len__：長度
        .def("__len__",
             &StringProcessor::length)

        // __bool__：布林轉換
        .def("__bool__",
             [](const StringProcessor& sp) {
                 return !sp.empty();
             })

        // __contains__：in 運算子
        .def("__contains__",
             &StringProcessor::contains,
             py::arg("substring"))

        // __iter__：迭代支援
        .def("__iter__",
             [](const StringProcessor& sp) {
                 return py::make_iterator(sp.content().begin(),
                                          sp.content().end());
             },
             py::keep_alive<0, 1>())  // 保持物件存活

        // __hash__：雜湊支援（讓物件可作為 dict key）
        .def("__hash__",
             [](const StringProcessor& sp) {
                 return std::hash<std::string>{}(sp.content());
             })

        // 支援 pickle
        .def(py::pickle(
            // __getstate__
            [](const StringProcessor& sp) {
                return py::make_tuple(sp.content());
            },
            // __setstate__
            [](py::tuple t) {
                if (t.size() != 1) {
                    throw std::runtime_error("Invalid state");
                }
                return StringProcessor(t[0].cast<std::string>());
            }
        ));

    // ========================================
    // 模組層級函式
    // ========================================
    m.def("concatenate",
          [](const std::vector<StringProcessor>& processors,
             const std::string& separator) {
              if (processors.empty()) {
                  return StringProcessor();
              }
              std::string result = processors[0].content();
              for (size_t i = 1; i < processors.size(); i++) {
                  result += separator + processors[i].content();
              }
              return StringProcessor(result);
          },
          py::arg("processors"),
          py::arg("separator") = "",
          "串接多個 StringProcessor");

    // 版本資訊
    m.attr("__version__") = "0.1.0";
}
```

### 步驟 5：建構檔案

**CMakeLists.txt**：

```cmake
cmake_minimum_required(VERSION 3.15)
project(string_processor LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 找到 pybind11
find_package(pybind11 REQUIRED)

# 建立 Python 模組
pybind11_add_module(string_processor
    src/string_processor.cpp
    src/bindings.cpp
)

# 包含標頭檔目錄
target_include_directories(string_processor PRIVATE src)

# 優化設定
target_compile_options(string_processor PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang>:-O3 -march=native>
    $<$<CXX_COMPILER_ID:MSVC>:/O2>
)
```

**setup.py**：

```python
# setup.py
from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "string_processor",
        sources=[
            "src/string_processor.cpp",
            "src/bindings.cpp",
        ],
        include_dirs=["src"],
        cxx_std=17,
        extra_compile_args=["-O3"],
    ),
]

setup(
    name="string_processor",
    version="0.1.0",
    description="High-performance string processor using pybind11",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    python_requires=">=3.8",
)
```

## 記憶體管理與物件生命週期

### pybind11 的記憶體管理策略

pybind11 提供多種方式控制物件的所有權：

```cpp
// 1. return_value_policy::automatic（預設）
// pybind11 自動決定最佳策略
.def("get_content", &StringProcessor::content)

// 2. return_value_policy::copy
// 總是建立副本，Python 擁有副本
.def("get_content_copy", &StringProcessor::content,
     py::return_value_policy::copy)

// 3. return_value_policy::reference
// 回傳參考，不轉移所有權（危險：可能產生懸空指標）
.def("get_content_ref", &StringProcessor::content,
     py::return_value_policy::reference)

// 4. return_value_policy::reference_internal
// 回傳參考，並保持父物件存活
.def("get_content_internal", &StringProcessor::content,
     py::return_value_policy::reference_internal)
```

### keep_alive 策略

當物件間有依賴關係時，使用 `keep_alive` 確保生命週期正確：

```cpp
// keep_alive<Nurse, Patient>
// Nurse: 需要被保持存活的物件的引數索引
// Patient: 依賴 Nurse 的物件的引數索引
// 0 = 回傳值, 1 = self, 2+ = 其他引數

// 範例：迭代器需要保持原物件存活
.def("__iter__",
     [](const StringProcessor& sp) {
         return py::make_iterator(sp.content().begin(),
                                  sp.content().end());
     },
     py::keep_alive<0, 1>())  // 回傳值(0)存活期間，self(1)必須存活
```

### 智慧指標支援

pybind11 自動支援 `std::shared_ptr` 和 `std::unique_ptr`：

```cpp
// 使用 shared_ptr 管理物件
py::class_<StringProcessor, std::shared_ptr<StringProcessor>>(m, "StringProcessor")
    // ...

// 工廠函式回傳 shared_ptr
m.def("create_processor", []() {
    return std::make_shared<StringProcessor>("factory created");
});
```

## Python 使用範例

### 基本使用

```python
from string_processor import StringProcessor, concatenate

# 建立物件
sp = StringProcessor("Hello, World!")
print(sp)           # Hello, World!
print(repr(sp))     # <StringProcessor content='Hello, World!' length=13>
print(len(sp))      # 13

# 屬性存取
print(sp.content)   # Hello, World!
print(sp.length)    # 13
print(sp.empty)     # False

# 修改內容
sp.content = "New content"
print(sp.content)   # New content
```

### 字串處理

```python
sp = StringProcessor("  Hello, Python World!  ")

# 大小寫轉換
print(sp.to_upper())  # "  HELLO, PYTHON WORLD!  "
print(sp.to_lower())  # "  hello, python world!  "

# 修剪空白
print(sp.trim())      # "Hello, Python World!"

# 反轉
print(sp.reverse())   # "  !dlroW nohtyP ,olleH  "

# 分割
sp = StringProcessor("apple,banana,cherry")
print(sp.split(","))  # ['apple', 'banana', 'cherry']

# 取代
print(sp.replace(",", " | "))  # "apple | banana | cherry"
```

### 統計與搜尋

```python
sp = StringProcessor("hello hello world")

# 統計
print(sp.word_count())              # 3
print(sp.count_occurrences("hello")) # 2
print(sp.char_frequency())          # {'h': 2, 'e': 2, 'l': 5, ...}

# 搜尋
print(sp.find("world"))             # 12
print(sp.find_all("hello"))         # [0, 6]
print(sp.contains("world"))         # True
print(sp.starts_with("hello"))      # True
print(sp.ends_with("world"))        # True
```

### 運算子使用

```python
sp1 = StringProcessor("Hello")
sp2 = StringProcessor(" World")

# + 運算子
sp3 = sp1 + sp2
print(sp3.content)   # "Hello World"

# += 運算子
sp1 += sp2
print(sp1.content)   # "Hello World"

# [] 索引
print(sp3[0])        # 'H'
print(sp3[6])        # 'W'

# in 運算子
print("World" in sp3)  # True

# 比較運算子
print(sp1 == sp3)    # True
print(sp1 != sp2)    # True
```

### Python 特殊功能

```python
import copy
import pickle

sp = StringProcessor("test data")

# 迭代
for char in sp:
    print(char, end="")  # t e s t   d a t a

# 複製
sp_copy = copy.copy(sp)

# 序列化
data = pickle.dumps(sp)
sp_restored = pickle.loads(data)
print(sp_restored.content)  # "test data"

# 作為 dict key
cache = {sp: "cached value"}
print(cache[sp])  # "cached value"
```

## 效能測試

建立效能測試腳本，比較 C++ 綁定與純 Python 實作：

```python
# benchmark.py
"""
效能比較：pybind11 StringProcessor vs 純 Python
"""

import time
import statistics
from typing import Callable, Any

# pybind11 版本
from string_processor import StringProcessor

# 純 Python 版本
class PyStringProcessor:
    """純 Python 實作作為效能基準"""

    def __init__(self, content: str = ""):
        self._content = content

    @property
    def content(self) -> str:
        return self._content

    @content.setter
    def content(self, value: str):
        self._content = value

    def to_upper(self) -> str:
        return self._content.upper()

    def to_lower(self) -> str:
        return self._content.lower()

    def reverse(self) -> str:
        return self._content[::-1]

    def split(self, delimiter: str = " ") -> list:
        return self._content.split(delimiter)

    def char_frequency(self) -> dict:
        freq = {}
        for c in self._content:
            freq[c] = freq.get(c, 0) + 1
        return freq

    def word_count(self) -> int:
        return len(self._content.split())

    def count_occurrences(self, substring: str) -> int:
        count = 0
        start = 0
        while True:
            pos = self._content.find(substring, start)
            if pos == -1:
                break
            count += 1
            start = pos + len(substring)
        return count

    def find_all(self, substring: str) -> list:
        positions = []
        start = 0
        while True:
            pos = self._content.find(substring, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + len(substring)
        return positions

def benchmark(func: Callable[[], Any],
              iterations: int = 1000,
              warmup: int = 100) -> dict:
    """執行效能測試並回傳統計資料"""
    # 預熱
    for _ in range(warmup):
        func()

    # 正式測試
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1000)  # 轉換為毫秒

    return {
        "mean": statistics.mean(times),
        "stdev": statistics.stdev(times),
        "min": min(times),
        "max": max(times),
        "median": statistics.median(times),
    }

def generate_test_content(size: int) -> str:
    """產生測試用字串"""
    base = "Hello World! This is a test string for benchmarking. "
    return (base * (size // len(base) + 1))[:size]

def run_benchmarks():
    """執行所有效能測試"""
    print("=" * 70)
    print("StringProcessor 效能測試：pybind11 vs 純 Python")
    print("=" * 70)

    sizes = [1_000, 10_000, 100_000, 1_000_000]

    for size in sizes:
        content = generate_test_content(size)
        cpp_sp = StringProcessor(content)
        py_sp = PyStringProcessor(content)

        print(f"\n--- 字串長度：{size:,} 字元 ---\n")

        # 測試項目
        tests = [
            ("to_upper", lambda: cpp_sp.to_upper(), lambda: py_sp.to_upper()),
            ("to_lower", lambda: cpp_sp.to_lower(), lambda: py_sp.to_lower()),
            ("reverse", lambda: cpp_sp.reverse(), lambda: py_sp.reverse()),
            ("char_frequency", lambda: cpp_sp.char_frequency(), lambda: py_sp.char_frequency()),
            ("word_count", lambda: cpp_sp.word_count(), lambda: py_sp.word_count()),
            ("count_occurrences", lambda: cpp_sp.count_occurrences("test"), lambda: py_sp.count_occurrences("test")),
            ("find_all", lambda: cpp_sp.find_all("Hello"), lambda: py_sp.find_all("Hello")),
        ]

        for name, cpp_func, py_func in tests:
            cpp_result = benchmark(cpp_func, iterations=500)
            py_result = benchmark(py_func, iterations=500)

            speedup = py_result["mean"] / cpp_result["mean"]

            print(f"{name:20s}")
            print(f"  C++:    {cpp_result['mean']:8.4f} ms (stdev: {cpp_result['stdev']:.4f})")
            print(f"  Python: {py_result['mean']:8.4f} ms (stdev: {py_result['stdev']:.4f})")
            print(f"  加速比: {speedup:.2f}x")
            print()

    print("=" * 70)

if __name__ == "__main__":
    run_benchmarks()
```

### 預期效能結果

```text
======================================================================
StringProcessor 效能測試：pybind11 vs 純 Python
======================================================================

--- 字串長度：1,000 字元 ---

to_upper
  C++:      0.0012 ms (stdev: 0.0003)
  Python:   0.0008 ms (stdev: 0.0002)
  加速比: 0.67x

char_frequency
  C++:      0.0089 ms (stdev: 0.0012)
  Python:   0.0423 ms (stdev: 0.0045)
  加速比: 4.75x

word_count
  C++:      0.0034 ms (stdev: 0.0008)
  Python:   0.0028 ms (stdev: 0.0006)
  加速比: 0.82x

--- 字串長度：100,000 字元 ---

to_upper
  C++:      0.0892 ms (stdev: 0.0089)
  Python:   0.0634 ms (stdev: 0.0067)
  加速比: 0.71x

char_frequency
  C++:      0.7823 ms (stdev: 0.0456)
  Python:   4.2341 ms (stdev: 0.2134)
  加速比: 5.41x

count_occurrences
  C++:      0.0234 ms (stdev: 0.0034)
  Python:   0.0567 ms (stdev: 0.0078)
  加速比: 2.42x

find_all
  C++:      0.0312 ms (stdev: 0.0045)
  Python:   0.0823 ms (stdev: 0.0098)
  加速比: 2.64x

======================================================================
```

### 效能分析

| 操作類型 | C++ 優勢 | 說明 |
|---------|---------|------|
| **字元頻率統計** | 4-6x | C++ unordered_map 比 Python dict 更快 |
| **搜尋操作** | 2-3x | C++ string::find 效率高 |
| **大小寫轉換** | 0.7x | Python 內建函式已高度優化 |
| **單字計數** | 0.8-1x | Python split() 非常高效 |

**重點觀察**：

1. **不是所有操作都能加速**：Python 的內建字串方法（如 `upper()`、`split()`）已經用 C 實作，pybind11 包裝反而增加呼叫開銷
2. **複雜操作效益明顯**：需要多次迴圈或資料結構操作的方法（如字元頻率統計）獲益最大
3. **資料量影響顯著**：資料量越大，C++ 的優勢越明顯

## 設計權衡

| 面向 | 純 Python | pybind11 C++ 綁定 |
|------|-----------|------------------|
| **開發速度** | 快 | 中（需要 C++ 開發經驗） |
| **效能** | 基準 | 特定操作 2-6x 加速 |
| **記憶體使用** | 較高 | 較低（C++ 記憶體管理） |
| **除錯難度** | 低 | 中高（需要 C++ 除錯工具） |
| **部署複雜度** | 簡單 | 需要編譯環境 |
| **可維護性** | 高 | 中（需要維護兩種語言） |

### 何時使用 pybind11 綁定 C++ 類別？

**適合使用**：

- 已有成熟的 C++ 程式庫需要在 Python 中使用
- 需要精細的記憶體管理
- 效能瓶頸在資料結構操作而非 I/O
- 需要與其他 C++ 系統整合

**不建議使用**：

- 純字串處理（Python 內建已很快）
- 簡單的資料容器（用 Python dataclass 更簡潔）
- 快速原型開發
- 團隊沒有 C++ 經驗

## 練習

### 基礎練習

擴展 StringProcessor，新增以下方法：

1. `join(separator: str, strings: list[str])` - 用分隔符串接字串列表
2. `pad_left(width: int, char: str)` - 左側填充字元
3. `pad_right(width: int, char: str)` - 右側填充字元

### 進階練習

建立一個 `DataBuffer` 類別，展示：

1. 使用 `std::vector<uint8_t>` 儲存二進位資料
2. 支援 Python buffer protocol（可與 NumPy 互通）
3. 實作切片操作（`__getitem__` 支援 slice）

### 挑戰題

比較三種綁定方式的效能：

1. pybind11 直接綁定
2. pybind11 + 釋放 GIL
3. 使用 NumPy 陣列避免資料複製

## 延伸閱讀

- [pybind11 官方文件：類別](https://pybind11.readthedocs.io/en/stable/classes.html)
- [pybind11 官方文件：運算子重載](https://pybind11.readthedocs.io/en/stable/operators.html)
- [pybind11 官方文件：智慧指標](https://pybind11.readthedocs.io/en/stable/advanced/smart_ptrs.html)
- [pybind11 記憶體管理最佳實踐](https://pybind11.readthedocs.io/en/stable/advanced/functions.html#return-value-policies)

---

*返回：[案例研究](../)*
*返回：[模組五：用 C 擴展 Python](../../)*
