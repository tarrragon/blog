---
title: "4.3 pybind11：現代 C++ 綁定"
date: 2026-01-20
description: "使用 pybind11 建立 Python 與 C++ 的綁定"
weight: 3
---

# pybind11：現代 C++ 綁定

本章介紹 pybind11，一個輕量級的 header-only C++ 函式庫，用於建立 Python 綁定。

## 本章目標

學完本章後，你將能夠：

1. 理解 pybind11 的設計哲學
2. 建立函式和類別綁定
3. 處理 NumPy 陣列

---

## 【原理層】pybind11 的設計哲學

### 為什麼需要 pybind11？

傳統的 Python C API 非常繁瑣：

```c
// 傳統 Python C API
static PyObject* add(PyObject* self, PyObject* args) {
    int a, b;
    if (!PyArg_ParseTuple(args, "ii", &a, &b)) {
        return NULL;
    }
    return PyLong_FromLong(a + b);
}

static PyMethodDef methods[] = {
    {"add", add, METH_VARARGS, "Add two integers"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "example",
    NULL,
    -1,
    methods
};

PyMODINIT_FUNC PyInit_example(void) {
    return PyModule_Create(&module);
}
```

pybind11 讓這變得簡單：

```cpp
// pybind11
#include <pybind11/pybind11.h>

int add(int a, int b) {
    return a + b;
}

PYBIND11_MODULE(example, m) {
    m.def("add", &add, "Add two integers");
}
```

### Header-only 設計

```text
pybind11 的特點：
├── Header-only：不需要編譯函式庫
├── C++11：使用現代 C++ 特性
├── 自動型別轉換：Python ↔ C++ 型別
├── 最小化模板程式碼
└── 與 NumPy 無縫整合
```

### 型別轉換原理

```text
Python 呼叫 C++ 函式時：

Python int  ──→  pybind11 type_caster  ──→  C++ int
Python str  ──→  pybind11 type_caster  ──→  std::string
Python list ──→  pybind11 type_caster  ──→  std::vector<T>

回傳時反向轉換
```

---

## 【設計層】開發環境設定

### 安裝 pybind11

```bash
# 方法 1：pip 安裝
pip install pybind11

# 方法 2：conda 安裝
conda install -c conda-forge pybind11

# 方法 3：系統套件管理器
# Ubuntu/Debian
sudo apt install pybind11-dev

# macOS
brew install pybind11
```

### 專案結構

```text
my_project/
├── CMakeLists.txt        # CMake 建構檔
├── pyproject.toml        # Python 打包設定
├── src/
│   └── example.cpp       # C++ 原始碼
└── tests/
    └── test_example.py   # 測試
```

### 最小 CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.15)
project(example)

# 找到 pybind11
find_package(pybind11 REQUIRED)

# 建立 Python 模組
pybind11_add_module(example src/example.cpp)
```

### 使用 setup.py（簡單專案）

```python
# setup.py
from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "example",
        ["src/example.cpp"],
    ),
]

setup(
    name="example",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
```

---

## 【實作層】基礎綁定

### 函式綁定

```cpp
#include <pybind11/pybind11.h>
#include <string>

namespace py = pybind11;

// 簡單函式
int add(int a, int b) {
    return a + b;
}

// 帶預設參數
double divide(double a, double b = 1.0) {
    return a / b;
}

// 多載函式
int multiply(int a, int b) { return a * b; }
double multiply(double a, double b) { return a * b; }

// 接受字串
std::string greet(const std::string& name) {
    return "Hello, " + name + "!";
}

PYBIND11_MODULE(example, m) {
    m.doc() = "Example module";

    // 基本綁定
    m.def("add", &add, "Add two integers");

    // 帶預設參數
    m.def("divide", &divide, "Divide two numbers",
          py::arg("a"), py::arg("b") = 1.0);

    // 處理多載：需要明確指定簽名
    m.def("multiply", py::overload_cast<int, int>(&multiply));
    m.def("multiply", py::overload_cast<double, double>(&multiply));

    // 字串函式
    m.def("greet", &greet, "Greet someone");
}
```

Python 使用：

```python
import example

print(example.add(1, 2))           # 3
print(example.divide(10, 2))       # 5.0
print(example.divide(10))          # 10.0（使用預設值）
print(example.multiply(3, 4))      # 12
print(example.multiply(1.5, 2.0))  # 3.0
print(example.greet("pybind11"))   # Hello, pybind11!
```

### 類別綁定

```cpp
#include <pybind11/pybind11.h>
#include <string>

namespace py = pybind11;

class Pet {
public:
    Pet(const std::string& name, int age)
        : name_(name), age_(age) {}

    // getter/setter
    const std::string& get_name() const { return name_; }
    void set_name(const std::string& name) { name_ = name; }

    int get_age() const { return age_; }
    void set_age(int age) { age_ = age; }

    // 方法
    std::string describe() const {
        return name_ + " is " + std::to_string(age_) + " years old";
    }

private:
    std::string name_;
    int age_;
};

PYBIND11_MODULE(example, m) {
    py::class_<Pet>(m, "Pet")
        // 建構子
        .def(py::init<const std::string&, int>())

        // 屬性（getter/setter）
        .def_property("name", &Pet::get_name, &Pet::set_name)
        .def_property("age", &Pet::get_age, &Pet::set_age)

        // 唯讀屬性
        // .def_property_readonly("name", &Pet::get_name)

        // 方法
        .def("describe", &Pet::describe)

        // __repr__
        .def("__repr__", [](const Pet& p) {
            return "<Pet '" + p.get_name() + "'>";
        });
}
```

### 繼承

```cpp
#include <pybind11/pybind11.h>
#include <string>

namespace py = pybind11;

class Animal {
public:
    Animal(const std::string& name) : name_(name) {}
    virtual ~Animal() = default;

    virtual std::string speak() const = 0;  // 純虛函式
    const std::string& name() const { return name_; }

protected:
    std::string name_;
};

class Dog : public Animal {
public:
    Dog(const std::string& name) : Animal(name) {}
    std::string speak() const override { return "Woof!"; }
};

class Cat : public Animal {
public:
    Cat(const std::string& name) : Animal(name) {}
    std::string speak() const override { return "Meow!"; }
};

// 用於在 Python 中繼承 C++ 類別
class PyAnimal : public Animal {
public:
    using Animal::Animal;

    std::string speak() const override {
        PYBIND11_OVERRIDE_PURE(std::string, Animal, speak);
    }
};

PYBIND11_MODULE(example, m) {
    py::class_<Animal, PyAnimal>(m, "Animal")
        .def(py::init<const std::string&>())
        .def("speak", &Animal::speak)
        .def_property_readonly("name", &Animal::name);

    py::class_<Dog, Animal>(m, "Dog")
        .def(py::init<const std::string&>());

    py::class_<Cat, Animal>(m, "Cat")
        .def(py::init<const std::string&>());
}
```

---

## 【實作層】進階功能

### STL 容器轉換

```cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>  // 必須包含！
#include <vector>
#include <map>
#include <set>

namespace py = pybind11;

// 自動轉換 std::vector ↔ Python list
std::vector<int> double_values(const std::vector<int>& input) {
    std::vector<int> result;
    result.reserve(input.size());
    for (int x : input) {
        result.push_back(x * 2);
    }
    return result;
}

// std::map ↔ Python dict
std::map<std::string, int> count_chars(const std::string& s) {
    std::map<std::string, int> counts;
    for (char c : s) {
        counts[std::string(1, c)]++;
    }
    return counts;
}

PYBIND11_MODULE(example, m) {
    m.def("double_values", &double_values);
    m.def("count_chars", &count_chars);
}
```

### NumPy 整合

```cpp
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>  // NumPy 支援
#include <cmath>

namespace py = pybind11;

// 處理 NumPy 陣列
py::array_t<double> compute_sin(py::array_t<double> input) {
    // 取得輸入資訊
    auto buf = input.request();

    if (buf.ndim != 1) {
        throw std::runtime_error("輸入必須是一維陣列");
    }

    // 建立輸出陣列
    py::array_t<double> result(buf.size);
    auto result_buf = result.request();

    // 取得原始指標
    double* in_ptr = static_cast<double*>(buf.ptr);
    double* out_ptr = static_cast<double*>(result_buf.ptr);

    // 計算
    for (size_t i = 0; i < buf.size; i++) {
        out_ptr[i] = std::sin(in_ptr[i]);
    }

    return result;
}

// 多維陣列
py::array_t<double> matrix_add(
    py::array_t<double, py::array::c_style | py::array::forcecast> a,
    py::array_t<double, py::array::c_style | py::array::forcecast> b
) {
    auto buf_a = a.request();
    auto buf_b = b.request();

    if (buf_a.ndim != 2 || buf_b.ndim != 2) {
        throw std::runtime_error("需要二維陣列");
    }

    if (buf_a.shape[0] != buf_b.shape[0] ||
        buf_a.shape[1] != buf_b.shape[1]) {
        throw std::runtime_error("陣列形狀必須相同");
    }

    size_t rows = buf_a.shape[0];
    size_t cols = buf_a.shape[1];

    py::array_t<double> result({rows, cols});
    auto buf_r = result.request();

    double* ptr_a = static_cast<double*>(buf_a.ptr);
    double* ptr_b = static_cast<double*>(buf_b.ptr);
    double* ptr_r = static_cast<double*>(buf_r.ptr);

    for (size_t i = 0; i < rows * cols; i++) {
        ptr_r[i] = ptr_a[i] + ptr_b[i];
    }

    return result;
}

PYBIND11_MODULE(example, m) {
    m.def("compute_sin", &compute_sin, "Compute sin for each element");
    m.def("matrix_add", &matrix_add, "Add two matrices");
}
```

### GIL 管理

```cpp
#include <pybind11/pybind11.h>
#include <thread>
#include <chrono>

namespace py = pybind11;

// 長時間 CPU 計算，應該釋放 GIL
double heavy_computation(int iterations) {
    // 釋放 GIL
    py::gil_scoped_release release;

    double result = 0.0;
    for (int i = 0; i < iterations; i++) {
        result += std::sin(i) * std::cos(i);
    }

    return result;
    // GIL 自動重新獲取
}

// 回呼 Python 函式，需要 GIL
void process_with_callback(py::function callback) {
    for (int i = 0; i < 10; i++) {
        // 如果在無 GIL 的上下文中，需要獲取
        // py::gil_scoped_acquire acquire;

        callback(i);
    }
}

// 多執行緒範例
std::vector<double> parallel_compute(int n_threads, int iterations) {
    std::vector<double> results(n_threads);
    std::vector<std::thread> threads;

    {
        // 釋放 GIL 讓執行緒可以並行
        py::gil_scoped_release release;

        for (int t = 0; t < n_threads; t++) {
            threads.emplace_back([&results, t, iterations]() {
                double sum = 0.0;
                for (int i = 0; i < iterations; i++) {
                    sum += std::sin(t + i);
                }
                results[t] = sum;
            });
        }

        for (auto& thread : threads) {
            thread.join();
        }
    }

    return results;
}

PYBIND11_MODULE(example, m) {
    m.def("heavy_computation", &heavy_computation);
    m.def("process_with_callback", &process_with_callback);
    m.def("parallel_compute", &parallel_compute);
}
```

### 異常處理

```cpp
#include <pybind11/pybind11.h>
#include <stdexcept>

namespace py = pybind11;

double safe_divide(double a, double b) {
    if (b == 0.0) {
        throw std::invalid_argument("除數不能為零");
    }
    return a / b;
}

void custom_exception_example() {
    // 拋出特定的 Python 異常
    throw py::value_error("這是一個 ValueError");
}

PYBIND11_MODULE(example, m) {
    // std::invalid_argument 自動轉換為 ValueError
    m.def("safe_divide", &safe_divide);

    m.def("custom_exception", &custom_exception_example);

    // 註冊自訂異常
    static py::exception<std::runtime_error> exc(m, "CustomError");
    py::register_exception_translator([](std::exception_ptr p) {
        try {
            if (p) std::rethrow_exception(p);
        } catch (const std::runtime_error& e) {
            exc(e.what());
        }
    });
}
```

---

## 【建構】現代化建構方式

### scikit-build-core（推薦）

```toml
# pyproject.toml
[build-system]
requires = ["scikit-build-core>=0.5", "pybind11"]
build-backend = "scikit_build_core.build"

[project]
name = "my-cpp-extension"
version = "0.1.0"
requires-python = ">=3.8"

[tool.scikit-build]
wheel.packages = ["src/my_package"]
```

```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.15)
project(my_cpp_extension LANGUAGES CXX)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_core src/core.cpp)

install(TARGETS _core DESTINATION .)
```

### meson-python

```toml
# pyproject.toml
[build-system]
requires = ["meson-python", "pybind11"]
build-backend = "mesonpy"

[project]
name = "my-cpp-extension"
version = "0.1.0"
```

```meson
# meson.build
project('my-cpp-extension', 'cpp',
  version: '0.1.0',
  default_options: ['cpp_std=c++17']
)

pybind11 = dependency('pybind11')
py = import('python').find_installation(pure: false)

py.extension_module(
  '_core',
  'src/core.cpp',
  dependencies: pybind11,
  install: true
)
```

---

## 【比較】pybind11 vs nanobind

### nanobind 簡介

nanobind 是 pybind11 作者開發的下一代工具：

```text
nanobind vs pybind11：

nanobind:
├── 更小的二進位檔案（~3-5x 減少）
├── 更快的編譯時間
├── 需要 C++17
├── 更嚴格的型別檢查
└── 更好的 Free-threading 支援

pybind11:
├── 更成熟、更多文件
├── C++11 即可
├── 更廣泛的社群支援
└── 更多現有專案使用
```

### 選擇建議

```text
選擇 pybind11：
- 需要支援舊編譯器（C++11）
- 需要豐富的文件和範例
- 現有專案已使用 pybind11

選擇 nanobind：
- 新專案
- 追求最小二進位大小
- 需要更好的 Free-threading 支援
- 可以使用 C++17
```

---

## 思考題

1. pybind11 如何實現 Python 和 C++ 之間的自動型別轉換？
2. 什麼時候應該在 C++ 程式碼中釋放 GIL？有什麼風險？
3. 為什麼 pybind11 使用 header-only 設計？這有什麼優缺點？

## 實作練習

1. 使用 pybind11 包裝一個簡單的 C++ 類別（如二維向量），支援運算子重載
2. 實現一個接受 NumPy 陣列的 C++ 函式，計算陣列的移動平均
3. 比較 pybind11 和 Cython 在相同任務上的效能和程式碼複雜度

## 延伸閱讀

- [pybind11 官方文件](https://pybind11.readthedocs.io/)
- [pybind11 GitHub](https://github.com/pybind/pybind11)
- [nanobind](https://github.com/wjakob/nanobind)
- [scikit-build-core](https://scikit-build-core.readthedocs.io/)

---

*上一章：[Cython](../cython/)*
*下一章：[選擇指南](../when-to-use/)*
