#!/usr/bin/env python3
"""
LRU 快取效能測試

比較有無 @lru_cache 裝飾器的效能差異。
"""

import fnmatch
import timeit
from functools import lru_cache

# 模擬的保護分支模式（來自 git_utils.py）
PROTECTED_BRANCHES = [
    "main",
    "master",
    "develop",
    "release/*",
    "hotfix/*",
    "production",
    "staging",
]

ALLOWED_BRANCHES = [
    "feature/*",
    "fix/*",
    "chore/*",
    "docs/*",
    "test/*",
    "refactor/*",
]


def is_protected_branch_nocache(branch: str) -> bool:
    """沒有快取的版本"""
    for pattern in PROTECTED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False


@lru_cache(maxsize=128)
def is_protected_branch_cached(branch: str) -> bool:
    """有 lru_cache 的版本"""
    for pattern in PROTECTED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False


def is_allowed_branch_nocache(branch: str) -> bool:
    """沒有快取的版本"""
    for pattern in ALLOWED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False


@lru_cache(maxsize=128)
def is_allowed_branch_cached(branch: str) -> bool:
    """有 lru_cache 的版本"""
    for pattern in ALLOWED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False


def benchmark_single_call():
    """測試單次呼叫的效能（冷啟動）"""
    print("單次呼叫測試（冷啟動）")
    print("-" * 50)

    branch = "feature/add-new-feature"

    # 清除快取
    is_protected_branch_cached.cache_clear()
    is_allowed_branch_cached.cache_clear()

    # 無快取版本
    nocache_time = timeit.timeit(
        lambda: is_protected_branch_nocache(branch),
        number=10000,
    )

    # 有快取版本（但每次都清除快取模擬冷啟動）
    def cached_with_clear():
        is_protected_branch_cached.cache_clear()
        return is_protected_branch_cached(branch)

    cached_cold_time = timeit.timeit(cached_with_clear, number=10000)

    print(f"無快取版本：{nocache_time:.4f}s (10000 次)")
    print(f"快取版本（冷啟動）：{cached_cold_time:.4f}s (10000 次)")
    print(f"冷啟動時，快取版本稍慢（因為有額外的快取機制開銷）")
    print()


def benchmark_repeated_calls():
    """測試重複呼叫的效能（快取命中）"""
    print("重複呼叫測試（快取命中）")
    print("-" * 50)

    branches = [
        "feature/add-new-feature",
        "main",
        "fix/bug-123",
        "develop",
        "release/v1.0",
    ]

    # 清除快取
    is_protected_branch_cached.cache_clear()

    # 無快取版本
    def check_all_nocache():
        for branch in branches:
            is_protected_branch_nocache(branch)
            is_allowed_branch_nocache(branch)

    nocache_time = timeit.timeit(check_all_nocache, number=10000)

    # 有快取版本
    def check_all_cached():
        for branch in branches:
            is_protected_branch_cached(branch)
            is_allowed_branch_cached(branch)

    # 預熱快取
    check_all_cached()

    cached_time = timeit.timeit(check_all_cached, number=10000)

    print(f"無快取版本：{nocache_time:.4f}s (10000 次)")
    print(f"快取版本（快取命中）：{cached_time:.4f}s (10000 次)")
    print(f"加速比：{nocache_time / cached_time:.2f}x")
    print()


def show_cache_stats():
    """顯示快取統計資訊"""
    print("快取統計資訊")
    print("-" * 50)

    # 清除快取
    is_protected_branch_cached.cache_clear()
    is_allowed_branch_cached.cache_clear()

    # 模擬一些呼叫
    branches = [
        "feature/add-new-feature",
        "main",
        "fix/bug-123",
        "main",  # 重複
        "feature/add-new-feature",  # 重複
        "develop",
        "main",  # 重複
    ]

    for branch in branches:
        is_protected_branch_cached(branch)
        is_allowed_branch_cached(branch)

    # 顯示統計
    info = is_protected_branch_cached.cache_info()
    print(f"is_protected_branch 快取統計：")
    print(f"  命中次數：{info.hits}")
    print(f"  未命中次數：{info.misses}")
    print(f"  最大容量：{info.maxsize}")
    print(f"  當前大小：{info.currsize}")
    print(f"  命中率：{info.hits / (info.hits + info.misses) * 100:.1f}%")
    print()


def benchmark_different_maxsize():
    """測試不同 maxsize 的影響"""
    print("不同 maxsize 的影響")
    print("-" * 50)

    # 建立不同 maxsize 的快取函式
    @lru_cache(maxsize=8)
    def cached_8(branch: str) -> bool:
        for pattern in PROTECTED_BRANCHES:
            if fnmatch.fnmatch(branch, pattern):
                return True
        return False

    @lru_cache(maxsize=64)
    def cached_64(branch: str) -> bool:
        for pattern in PROTECTED_BRANCHES:
            if fnmatch.fnmatch(branch, pattern):
                return True
        return False

    @lru_cache(maxsize=None)
    def cached_unlimited(branch: str) -> bool:
        for pattern in PROTECTED_BRANCHES:
            if fnmatch.fnmatch(branch, pattern):
                return True
        return False

    # 產生測試資料（20 個不同的分支名稱）
    test_branches = [f"feature/feature-{i}" for i in range(20)]

    # 測試各種 maxsize
    for name, func in [
        ("maxsize=8", cached_8),
        ("maxsize=64", cached_64),
        ("maxsize=None", cached_unlimited),
    ]:
        func.cache_clear()

        # 執行測試
        def check_all():
            for branch in test_branches * 10:  # 重複 10 次
                func(branch)

        time_taken = timeit.timeit(check_all, number=100)
        info = func.cache_info()
        hit_rate = info.hits / (info.hits + info.misses) * 100

        print(f"{name}：{time_taken:.4f}s，命中率 {hit_rate:.1f}%")

    print()


def main():
    print("=" * 60)
    print("LRU 快取效能測試")
    print("=" * 60)
    print()

    benchmark_single_call()
    benchmark_repeated_calls()
    show_cache_stats()
    benchmark_different_maxsize()

    print("=" * 60)
    print("結論")
    print("=" * 60)
    print("""
1. lru_cache 在重複呼叫時有顯著的效能提升（視命中率而定）
2. 冷啟動時有輕微的額外開銷
3. maxsize 應根據預期的不同輸入數量來設定
4. 使用 cache_info() 可以監控快取效能
5. 適合純函數、可雜湊參數、計算成本較高的場景
""")


if __name__ == "__main__":
    main()
