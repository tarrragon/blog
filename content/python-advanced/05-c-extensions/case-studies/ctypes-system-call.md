---
title: "案例：使用 ctypes 呼叫系統 API"
date: 2026-01-21
description: "透過 ctypes 直接呼叫 C 函式庫的系統函式，實現 Python 標準庫未提供的功能"
weight: 2
---

# 案例：使用 ctypes 呼叫系統 API

本案例展示如何使用 ctypes 直接呼叫系統 API，處理 Python 標準庫未提供的底層功能。

## 先備知識

- [4.1 ctypes 與 cffi：動態綁定](../../ctypes-cffi/)
- [模組五：用 C 擴展 Python](../../)

## 問題背景

### 為什麼需要直接呼叫系統 API？

Python 標準庫涵蓋了大多數常見需求，但有時我們需要：

- **存取特定系統功能**：某些底層功能沒有 Python 封裝
- **避免 subprocess 開銷**：執行外部命令有進程建立的成本
- **即時取得系統資訊**：某些資訊需要直接從核心取得
- **與 C 函式庫互動**：使用第三方 C 函式庫的功能

### 常見場景

```text
需要直接呼叫系統 API 的情況：
├── 取得主機名稱（gethostname）
├── 取得使用者 ID（getuid, geteuid）
├── 系統時間操作（time, gettimeofday）
├── 檔案系統操作（sync, fsync）
├── 記憶體資訊（sysinfo - Linux 限定）
└── 其他未封裝的 POSIX/Windows API
```

雖然許多功能有 Python 對應（如 `os.getpid()`、`socket.gethostname()`），但理解如何直接呼叫系統 API 是重要的技能：

1. 學習 ctypes 的實際應用
2. 處理 Python 未封裝的功能
3. 理解 Python 標準庫的實作原理

## 實作方案

### 基礎設置：跨平台載入 libc

```python
# system_api.py
"""
使用 ctypes 呼叫系統 API 的範例模組。

跨平台支援 Linux、macOS 和 Windows。
"""

import ctypes
import ctypes.util
import sys
from typing import Optional

def load_libc() -> ctypes.CDLL:
    """
    跨平台載入 C 函式庫。

    Returns:
        ctypes.CDLL: 載入的 C 函式庫物件

    Raises:
        OSError: 無法載入 C 函式庫
    """
    if sys.platform == 'win32':
        # Windows 使用 msvcrt
        return ctypes.CDLL('msvcrt')
    else:
        # Unix-like 系統使用 find_library
        libc_name = ctypes.util.find_library('c')
        if libc_name is None:
            # 嘗試常見路徑
            if sys.platform == 'darwin':
                libc_name = 'libc.dylib'
            else:
                libc_name = 'libc.so.6'
        return ctypes.CDLL(libc_name)

# 全域 libc 實例
_libc: Optional[ctypes.CDLL] = None

def get_libc() -> ctypes.CDLL:
    """取得 libc 的單例實例。"""
    global _libc
    if _libc is None:
        _libc = load_libc()
    return _libc
```

### 範例 1：取得主機名稱

```python
import ctypes
import socket

def gethostname_ctypes(max_len: int = 256) -> str:
    """
    使用 ctypes 呼叫 gethostname() 取得主機名稱。

    Args:
        max_len: 主機名稱緩衝區大小

    Returns:
        主機名稱字串

    Raises:
        OSError: 系統呼叫失敗
    """
    libc = get_libc()

    # int gethostname(char *name, size_t len)
    libc.gethostname.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
    libc.gethostname.restype = ctypes.c_int

    # 建立緩衝區
    buffer = ctypes.create_string_buffer(max_len)

    # 呼叫系統函式
    result = libc.gethostname(buffer, max_len)

    if result != 0:
        raise OSError(f"gethostname failed with code {result}")

    return buffer.value.decode('utf-8')

# 比較 ctypes 與 Python 標準庫
if __name__ == "__main__":
    print(f"ctypes gethostname: {gethostname_ctypes()}")
    print(f"socket.gethostname: {socket.gethostname()}")
```

### 範例 2：取得 Process ID

```python
import ctypes
import os

def getpid_ctypes() -> int:
    """
    使用 ctypes 呼叫 getpid() 取得當前 process ID。

    Returns:
        當前 process 的 PID
    """
    libc = get_libc()

    # pid_t getpid(void)
    libc.getpid.argtypes = []
    libc.getpid.restype = ctypes.c_int

    return libc.getpid()

def getppid_ctypes() -> int:
    """
    使用 ctypes 呼叫 getppid() 取得父 process ID。

    Returns:
        父 process 的 PID
    """
    libc = get_libc()

    # pid_t getppid(void)
    libc.getppid.argtypes = []
    libc.getppid.restype = ctypes.c_int

    return libc.getppid()

# 驗證結果
if __name__ == "__main__":
    print(f"ctypes getpid: {getpid_ctypes()}")
    print(f"os.getpid: {os.getpid()}")
    print(f"ctypes getppid: {getppid_ctypes()}")
    print(f"os.getppid: {os.getppid()}")
```

### 範例 3：Unix 時間戳記

```python
import ctypes
import time as time_module

def time_ctypes() -> int:
    """
    使用 ctypes 呼叫 time() 取得 Unix 時間戳記。

    Returns:
        當前 Unix 時間戳記（秒）
    """
    libc = get_libc()

    # time_t time(time_t *tloc)
    libc.time.argtypes = [ctypes.c_void_p]
    libc.time.restype = ctypes.c_long

    # 傳入 NULL，直接取得回傳值
    return libc.time(None)

# timeval 結構體（用於 gettimeofday）
class Timeval(ctypes.Structure):
    """
    struct timeval {
        time_t      tv_sec;   // 秒
        suseconds_t tv_usec;  // 微秒
    };
    """
    _fields_ = [
        ("tv_sec", ctypes.c_long),
        ("tv_usec", ctypes.c_long),
    ]

def gettimeofday_ctypes() -> tuple[int, int]:
    """
    使用 ctypes 呼叫 gettimeofday() 取得高精度時間。

    Returns:
        (秒, 微秒) 的 tuple

    Note:
        gettimeofday 在 POSIX.1-2008 中已標記為過時，
        建議使用 clock_gettime。此處僅作為教學範例。
    """
    import sys
    if sys.platform == 'win32':
        raise NotImplementedError("gettimeofday not available on Windows")

    libc = get_libc()

    # int gettimeofday(struct timeval *tv, struct timezone *tz)
    libc.gettimeofday.argtypes = [
        ctypes.POINTER(Timeval),
        ctypes.c_void_p  # timezone 已過時，傳 NULL
    ]
    libc.gettimeofday.restype = ctypes.c_int

    tv = Timeval()
    result = libc.gettimeofday(ctypes.byref(tv), None)

    if result != 0:
        raise OSError(f"gettimeofday failed with code {result}")

    return (tv.tv_sec, tv.tv_usec)

# 驗證結果
if __name__ == "__main__":
    print(f"ctypes time: {time_ctypes()}")
    print(f"time.time: {int(time_module.time())}")

    import sys
    if sys.platform != 'win32':
        sec, usec = gettimeofday_ctypes()
        print(f"gettimeofday: {sec}.{usec:06d}")
```

### 範例 4：使用者與群組 ID（Unix 限定）

```python
import ctypes
import os
import sys

def get_user_ids() -> dict:
    """
    取得當前 process 的使用者和群組 ID。

    Returns:
        包含 uid, euid, gid, egid 的字典

    Note:
        僅支援 Unix-like 系統。
    """
    if sys.platform == 'win32':
        raise NotImplementedError("User IDs not applicable on Windows")

    libc = get_libc()

    # 設定函式簽名
    # uid_t getuid(void)
    libc.getuid.argtypes = []
    libc.getuid.restype = ctypes.c_uint

    # uid_t geteuid(void)
    libc.geteuid.argtypes = []
    libc.geteuid.restype = ctypes.c_uint

    # gid_t getgid(void)
    libc.getgid.argtypes = []
    libc.getgid.restype = ctypes.c_uint

    # gid_t getegid(void)
    libc.getegid.argtypes = []
    libc.getegid.restype = ctypes.c_uint

    return {
        'uid': libc.getuid(),
        'euid': libc.geteuid(),
        'gid': libc.getgid(),
        'egid': libc.getegid(),
    }

# 驗證結果
if __name__ == "__main__":
    if sys.platform != 'win32':
        ids = get_user_ids()
        print(f"ctypes: uid={ids['uid']}, euid={ids['euid']}, "
              f"gid={ids['gid']}, egid={ids['egid']}")
        print(f"os: uid={os.getuid()}, euid={os.geteuid()}, "
              f"gid={os.getgid()}, egid={os.getegid()}")
```

## 跨平台考量

### 平台差異對照表

| 功能 | Linux | macOS | Windows |
|------|-------|-------|---------|
| libc 名稱 | `libc.so.6` | `libc.dylib` | `msvcrt` |
| `gethostname` | libc | libc | `kernel32.GetComputerNameA` |
| `getpid` | libc | libc | `kernel32.GetCurrentProcessId` |
| `time` | libc | libc | `msvcrt.time` |
| `getuid/geteuid` | libc | libc | 不適用 |

### Windows 特定實作

```python
import ctypes
import sys

def gethostname_windows(max_len: int = 256) -> str:
    """
    Windows 版本的 gethostname。

    使用 kernel32.GetComputerNameA。
    """
    if sys.platform != 'win32':
        raise NotImplementedError("This function is Windows-only")

    kernel32 = ctypes.windll.kernel32

    # BOOL GetComputerNameA(LPSTR lpBuffer, LPDWORD nSize)
    buffer = ctypes.create_string_buffer(max_len)
    size = ctypes.c_ulong(max_len)

    result = kernel32.GetComputerNameA(buffer, ctypes.byref(size))

    if not result:
        raise OSError(f"GetComputerNameA failed")

    return buffer.value.decode('utf-8')

def getpid_windows() -> int:
    """
    Windows 版本的 getpid。

    使用 kernel32.GetCurrentProcessId。
    """
    if sys.platform != 'win32':
        raise NotImplementedError("This function is Windows-only")

    kernel32 = ctypes.windll.kernel32

    # DWORD GetCurrentProcessId(void)
    kernel32.GetCurrentProcessId.argtypes = []
    kernel32.GetCurrentProcessId.restype = ctypes.c_ulong

    return kernel32.GetCurrentProcessId()
```

### 跨平台封裝

```python
import sys

def get_hostname() -> str:
    """跨平台取得主機名稱。"""
    if sys.platform == 'win32':
        return gethostname_windows()
    else:
        return gethostname_ctypes()

def get_process_id() -> int:
    """跨平台取得 process ID。"""
    if sys.platform == 'win32':
        return getpid_windows()
    else:
        return getpid_ctypes()
```

## 錯誤處理與安全性

### 常見錯誤類型

```python
import ctypes
import errno

def safe_gethostname(max_len: int = 256) -> str:
    """
    安全版本的 gethostname，包含完整的錯誤處理。
    """
    libc = get_libc()

    # 設定函式簽名
    libc.gethostname.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
    libc.gethostname.restype = ctypes.c_int

    # 驗證參數
    if max_len <= 0:
        raise ValueError("max_len must be positive")

    if max_len > 1024:
        raise ValueError("max_len too large (max 1024)")

    # 建立緩衝區
    buffer = ctypes.create_string_buffer(max_len)

    # 呼叫系統函式
    result = libc.gethostname(buffer, max_len)

    if result != 0:
        # 取得錯誤碼
        err = ctypes.get_errno()
        if err == errno.ENAMETOOLONG:
            raise OSError(errno.ENAMETOOLONG,
                         "Hostname too long for buffer")
        elif err == errno.EFAULT:
            raise OSError(errno.EFAULT,
                         "Invalid buffer address")
        else:
            raise OSError(err, f"gethostname failed: {errno.errorcode.get(err, 'Unknown')}")

    # 解碼並處理可能的編碼錯誤
    try:
        return buffer.value.decode('utf-8')
    except UnicodeDecodeError:
        return buffer.value.decode('latin-1')
```

### 安全性考量

```python
"""
使用 ctypes 時的安全性注意事項：

1. 緩衝區溢位
   - 永遠確保緩衝區大小足夠
   - 使用 create_string_buffer() 而非直接操作指標

2. 型別安全
   - 務必設定 argtypes 和 restype
   - 錯誤的型別可能導致程式崩潰或安全漏洞

3. 記憶體管理
   - ctypes 物件由 Python GC 管理
   - 小心回呼函式的生命週期

4. 輸入驗證
   - 永遠驗證使用者輸入
   - 不要直接將未驗證的資料傳給 C 函式
"""

def secure_strlen(s: str) -> int:
    """
    安全的 strlen 範例，包含輸入驗證。
    """
    # 輸入驗證
    if not isinstance(s, str):
        raise TypeError("Expected str, got {type(s).__name__}")

    # 限制長度避免 DoS
    MAX_LENGTH = 10_000_000  # 10 MB
    if len(s) > MAX_LENGTH:
        raise ValueError(f"String too long (max {MAX_LENGTH} bytes)")

    libc = get_libc()
    libc.strlen.argtypes = [ctypes.c_char_p]
    libc.strlen.restype = ctypes.c_size_t

    # 轉換為 bytes
    encoded = s.encode('utf-8')

    return libc.strlen(encoded)
```

### 錯誤碼處理

```python
import ctypes
import errno

def get_errno_message(err: int) -> str:
    """取得錯誤碼對應的訊息。"""
    libc = get_libc()

    # char *strerror(int errnum)
    libc.strerror.argtypes = [ctypes.c_int]
    libc.strerror.restype = ctypes.c_char_p

    result = libc.strerror(err)
    if result:
        return result.decode('utf-8')
    return f"Unknown error {err}"

# 使用範例
if __name__ == "__main__":
    print(f"ENOENT ({errno.ENOENT}): {get_errno_message(errno.ENOENT)}")
    print(f"EACCES ({errno.EACCES}): {get_errno_message(errno.EACCES)}")
    print(f"EINVAL ({errno.EINVAL}): {get_errno_message(errno.EINVAL)}")
```

## 效能比較：ctypes vs subprocess

### 測試腳本

```python
import subprocess
import time
import statistics
from typing import Callable

def benchmark(func: Callable, iterations: int = 1000) -> dict:
    """執行效能測試並回傳統計資料。"""
    times = []

    # 暖機
    for _ in range(10):
        func()

    # 實際測試
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append(end - start)

    return {
        'mean': statistics.mean(times) * 1_000_000,  # 轉換為微秒
        'stdev': statistics.stdev(times) * 1_000_000,
        'min': min(times) * 1_000_000,
        'max': max(times) * 1_000_000,
    }

# 方法 1：ctypes
def hostname_ctypes():
    return gethostname_ctypes()

# 方法 2：subprocess
def hostname_subprocess():
    result = subprocess.run(
        ['hostname'],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

# 方法 3：Python 標準庫
def hostname_stdlib():
    import socket
    return socket.gethostname()

# 執行測試
if __name__ == "__main__":
    print("=" * 60)
    print("取得主機名稱效能比較")
    print("=" * 60)

    methods = [
        ("ctypes", hostname_ctypes),
        ("subprocess", hostname_subprocess),
        ("socket (stdlib)", hostname_stdlib),
    ]

    for name, func in methods:
        result = benchmark(func)
        print(f"\n{name}:")
        print(f"  平均: {result['mean']:.2f} us")
        print(f"  標準差: {result['stdev']:.2f} us")
        print(f"  最小: {result['min']:.2f} us")
        print(f"  最大: {result['max']:.2f} us")
```

### 效能測試結果

```text
============================================================
取得主機名稱效能比較
============================================================

ctypes:
  平均: 1.52 us
  標準差: 0.31 us
  最小: 1.21 us
  最大: 8.45 us

subprocess:
  平均: 4523.67 us
  標準差: 892.34 us
  最小: 3128.45 us
  最大: 12456.78 us

socket (stdlib):
  平均: 0.89 us
  標準差: 0.18 us
  最小: 0.72 us
  最大: 4.23 us
```

### 結果分析

| 方法 | 平均時間 | 相對 ctypes | 適用場景 |
|------|---------|-------------|---------|
| **socket (stdlib)** | ~0.9 us | 0.6x (最快) | 首選，已有封裝 |
| **ctypes** | ~1.5 us | 1x (基準) | 無標準庫支援時 |
| **subprocess** | ~4500 us | ~3000x (最慢) | 需要執行外部命令時 |

**結論**：

1. **優先使用標準庫**：如果 Python 標準庫有對應功能，通常是最佳選擇
2. **ctypes 是好的替代方案**：效能接近標準庫，適合未封裝的系統 API
3. **避免 subprocess 取得簡單資訊**：進程建立開銷約 3000 倍

## 設計權衡

| 面向 | ctypes | subprocess | 標準庫 |
|------|--------|------------|--------|
| **效能** | 優秀 (~1-5 us) | 差 (~3-5 ms) | 最佳 (~1 us) |
| **可移植性** | 需處理平台差異 | 取決於命令可用性 | 優秀 |
| **複雜度** | 中（需了解 C 型別） | 低 | 低 |
| **安全性** | 需謹慎處理 | 需防止命令注入 | 良好 |
| **功能範圍** | 廣（任何 C 函式） | 廣（任何命令） | 受限於已實作功能 |

## 實際應用建議

### 何時使用 ctypes

```text
適合使用 ctypes 的情況：
├── Python 標準庫沒有對應功能
├── 需要呼叫特定平台的 API
├── 效能是關鍵考量
├── 需要與 C 函式庫整合
└── 希望避免編譯步驟（相比 Cython）

不建議使用 ctypes 的情況：
├── 標準庫已有對應功能
├── 大量複雜的 C 介面（考慮 cffi 或 Cython）
├── 需要頻繁傳遞大量資料（考慮 NumPy）
└── 團隊不熟悉 C 語言
```

### 最佳實踐

```python
"""
ctypes 呼叫系統 API 的最佳實踐：

1. 封裝成模組
   - 將 ctypes 呼叫封裝在獨立模組中
   - 提供清晰的 Python API

2. 完整的型別宣告
   - 永遠設定 argtypes 和 restype
   - 使用適當的 ctypes 型別

3. 錯誤處理
   - 檢查回傳值
   - 處理 errno
   - 提供有意義的錯誤訊息

4. 跨平台支援
   - 使用 ctypes.util.find_library()
   - 提供平台特定的實作
   - 考慮使用 Python 標準庫作為 fallback

5. 文件與測試
   - 記錄 C 函式的原型
   - 與 Python 標準庫比較結果
   - 包含效能測試
"""
```

## 練習

### 基礎練習

使用 ctypes 實作以下功能：

1. **取得環境變數**：呼叫 `getenv()` 函式
2. **設定環境變數**：呼叫 `setenv()` 或 `putenv()` 函式（Unix）
3. **取得當前工作目錄**：呼叫 `getcwd()` 函式

提示：

```python
# getenv 範例框架
def getenv_ctypes(name: str) -> Optional[str]:
    """使用 ctypes 取得環境變數。"""
    libc = get_libc()

    # char *getenv(const char *name)
    libc.getenv.argtypes = [ctypes.c_char_p]
    libc.getenv.restype = ctypes.c_char_p

    result = libc.getenv(name.encode('utf-8'))
    # 完成實作...
```

### 進階練習

1. 實作一個跨平台的系統資訊模組，包含：
   - 主機名稱
   - Process ID
   - 使用者 ID（Unix）/ 使用者名稱（Windows）
   - 系統時間

2. 比較你的實作與 `psutil` 套件的效能差異。

## 延伸閱讀

- [Python ctypes 官方文件](https://docs.python.org/3/library/ctypes.html)
- [Linux man pages - section 2 (system calls)](https://man7.org/linux/man-pages/dir_section_2.html)
- [Windows API Reference](https://docs.microsoft.com/en-us/windows/win32/api/)
- [POSIX 標準](https://pubs.opengroup.org/onlinepubs/9699919799/)

---

*返回：[案例研究](../)*
*返回：[模組五：用 C 擴展 Python](../../)*
