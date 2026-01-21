#!/usr/bin/env python3
"""
資料結構選擇效能測試

比較 list vs set 的查詢效能差異。
"""

import sys
import timeit


def benchmark_membership_test():
    """測試成員查詢效能"""
    print("成員查詢效能測試")
    print("-" * 50)

    sizes = [100, 1000, 10000, 100000]

    for size in sizes:
        # 建立測試資料
        items_list = list(range(size))
        items_set = set(range(size))

        # 查詢最後一個元素（最壞情況 for list）
        target = size - 1

        # List 查詢
        list_time = timeit.timeit(
            lambda: target in items_list,
            number=10000,
        )

        # Set 查詢
        set_time = timeit.timeit(
            lambda: target in items_set,
            number=10000,
        )

        speedup = list_time / set_time

        print(f"大小 {size:>6}：")
        print(f"  List：{list_time:.6f}s")
        print(f"  Set： {set_time:.6f}s")
        print(f"  加速：{speedup:.1f}x")
        print()


def benchmark_realistic_scenario():
    """模擬真實場景：檢查測試檔案是否存在"""
    print("真實場景：測試檔案存在性檢查")
    print("-" * 50)

    # 模擬測試檔案列表
    test_files_count = 100
    test_files_list = [f"test_{i:04d}.py" for i in range(test_files_count)]
    test_files_set = set(test_files_list)

    # 模擬 Hook 檔案列表（要檢查的目標）
    hook_files = [f"hook_{i:04d}.py" for i in range(50)]

    # 使用 List 檢查
    def check_with_list():
        results = []
        for hook in hook_files:
            expected_test = f"test_{hook[5:]}"  # hook_0001.py -> test_0001.py
            exists = expected_test in test_files_list
            results.append((hook, exists))
        return results

    # 使用 Set 檢查
    def check_with_set():
        results = []
        for hook in hook_files:
            expected_test = f"test_{hook[5:]}"
            exists = expected_test in test_files_set
            results.append((hook, exists))
        return results

    # 測量效能
    list_time = timeit.timeit(check_with_list, number=1000)
    set_time = timeit.timeit(check_with_set, number=1000)

    print(f"使用 List：{list_time:.4f}s (1000 次)")
    print(f"使用 Set： {set_time:.4f}s (1000 次)")
    print(f"加速：{list_time / set_time:.1f}x")
    print()


def show_memory_usage():
    """顯示記憶體使用比較"""
    print("記憶體使用比較")
    print("-" * 50)

    sizes = [100, 1000, 10000]

    for size in sizes:
        items = list(range(size))

        list_memory = sys.getsizeof(items)
        set_memory = sys.getsizeof(set(items))

        # 包含元素本身的記憶體（近似值）
        element_size = sys.getsizeof(0) * size
        list_total = list_memory + element_size
        set_total = set_memory + element_size

        print(f"大小 {size}：")
        print(f"  List 容器：{list_memory:>8} bytes")
        print(f"  Set 容器： {set_memory:>8} bytes")
        print(f"  Set/List 比值：{set_memory / list_memory:.2f}x")
        print()


def benchmark_insertion():
    """測試插入效能"""
    print("插入效能測試")
    print("-" * 50)

    sizes = [1000, 10000]

    for size in sizes:
        # List 插入（末尾）
        def list_append():
            items = []
            for i in range(size):
                items.append(i)
            return items

        # Set 插入
        def set_add():
            items = set()
            for i in range(size):
                items.add(i)
            return items

        list_time = timeit.timeit(list_append, number=100)
        set_time = timeit.timeit(set_add, number=100)

        print(f"大小 {size}：")
        print(f"  List append：{list_time:.4f}s")
        print(f"  Set add：    {set_time:.4f}s")
        print(f"  比值：{set_time / list_time:.2f}x（Set 較慢）")
        print()


def show_when_to_use():
    """顯示使用建議"""
    print("使用建議")
    print("-" * 50)
    print("""
| 場景 | 建議使用 | 原因 |
|------|----------|------|
| 頻繁查詢成員是否存在 | set | O(1) 查詢 |
| 需要保持順序 | list | set 無序 |
| 需要重複元素 | list | set 自動去重 |
| 需要索引存取 | list | set 不支援索引 |
| 去重操作 | set | 天然去重 |
| 集合運算（交集、聯集） | set | 內建運算子 |
| 記憶體受限 | list | 通常較省記憶體 |
""")


def main():
    print("=" * 60)
    print("資料結構選擇效能測試")
    print("=" * 60)
    print()

    benchmark_membership_test()
    benchmark_realistic_scenario()
    show_memory_usage()
    benchmark_insertion()
    show_when_to_use()

    print("=" * 60)
    print("結論")
    print("=" * 60)
    print("""
1. 成員查詢：set 比 list 快 10-1000 倍（視大小而定）
2. 記憶體：set 通常比 list 使用更多記憶體
3. 插入：兩者都是 O(1)，但 set 有雜湊計算開銷
4. 選擇依據：主要操作是什麼？
   - 頻繁查詢 → set
   - 需要順序或索引 → list
   - 需要去重 → set
""")


if __name__ == "__main__":
    main()
