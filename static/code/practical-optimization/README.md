# 實戰效能優化 - 可執行程式碼

本目錄包含「模組八：實戰效能優化」的可執行範例程式碼。

## 目錄結構

```text
practical-optimization/
├── README.md               # 本說明文件
├── requirements.txt        # Python 相依套件
├── original/               # 原始版本（對照組）
│   ├── markdown_link_checker.py
│   ├── hook_validator.py
│   └── git_utils.py
├── optimized/              # 優化版本
│   ├── markdown_link_checker_parallel.py
│   ├── hook_validator_parallel.py
│   ├── hook_validator_optimized.py
│   └── git_utils_cached.py
├── benchmarks/             # 效能測試腳本
│   ├── benchmark_parallel.py
│   ├── benchmark_regex.py
│   ├── benchmark_cache.py
│   └── benchmark_data_structure.py
└── profiling/              # 效能分析腳本
    ├── profile_link_checker.py
    └── profile_hook_validator.py
```

## 快速開始

### 1. 建立虛擬環境（建議）

```bash
cd practical-optimization
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows
```

### 2. 安裝相依套件

```bash
pip install -r requirements.txt
```

### 3. 執行效能測試

```bash
# 並行處理效能測試
python benchmarks/benchmark_parallel.py

# 正則表達式預編譯測試
python benchmarks/benchmark_regex.py

# LRU 快取測試
python benchmarks/benchmark_cache.py

# 資料結構選擇測試
python benchmarks/benchmark_data_structure.py
```

### 4. 執行效能分析

```bash
# 分析 MarkdownLinkChecker
python profiling/profile_link_checker.py

# 分析 HookValidator
python profiling/profile_hook_validator.py
```

## 預期結果

| 優化項目 | 預期加速 |
| -------- | -------- |
| 並行檔案檢查 | 3-5x |
| 並行 Hook 驗證 | 3-5x |
| 正則表達式預編譯 | 1.2-1.3x |
| LRU 快取 | 視命中率 |
| Set 取代 List（查詢） | 10-100x |

## 注意事項

1. **效能數據會因環境而異**：CPU 核心數、磁碟速度、記憶體等都會影響結果
2. **並行測試需要足夠的測試檔案**：建議準備至少 20 個以上的 Markdown 檔案來測試並行效能
3. **快取測試需要重複執行**：LRU 快取的效果需要在重複查詢時才能體現

## 相關文件

- [模組八：實戰效能優化](https://your-blog.com/python-advanced/08-practical-optimization/)
- [入門系列 3.7 並行處理](https://your-blog.com/python/03-stdlib/concurrency/)
- [入門系列 3.8 效能優化](https://your-blog.com/python/03-stdlib/performance/)
