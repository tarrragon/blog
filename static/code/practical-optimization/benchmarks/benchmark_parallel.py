#!/usr/bin/env python3
"""
並行處理效能測試

比較循序處理與並行處理的效能差異。
"""

import time
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable


def create_test_files(directory: Path, count: int) -> list[Path]:
    """建立測試用的 Markdown 檔案"""
    files = []
    for i in range(count):
        file_path = directory / f"test_{i:04d}.md"
        content = f"""# Test Document {i}

This is a test markdown file.

## Links

- [Link 1](./other_{i}.md)
- [Link 2](https://example.com/{i})
- [Link 3](../parent/doc.md)

## Code Block

```python
# This [link](should_be_ignored.md) is in a code block
print("Hello, World!")
```

Some more content here.
"""
        file_path.write_text(content)
        files.append(file_path)
    return files


def simulate_file_check(file_path: Path) -> dict:
    """模擬檔案檢查（I/O 密集操作）"""
    # 讀取檔案
    content = file_path.read_text()

    # 模擬一些處理時間（例如正則表達式匹配）
    time.sleep(0.01)  # 10ms 模擬 I/O 延遲

    return {
        "file": str(file_path),
        "lines": len(content.split("\n")),
        "chars": len(content),
    }


def check_sequential(files: list[Path]) -> list[dict]:
    """循序檢查"""
    results = []
    for file_path in files:
        results.append(simulate_file_check(file_path))
    return results


def check_parallel_map(files: list[Path], max_workers: int = 4) -> list[dict]:
    """並行檢查（使用 map）"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(simulate_file_check, files))
    return results


def check_parallel_as_completed(files: list[Path], max_workers: int = 4) -> list[dict]:
    """並行檢查（使用 as_completed）"""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(simulate_file_check, f): f for f in files}
        for future in as_completed(futures):
            results.append(future.result())
    return results


def benchmark(
    name: str,
    func: Callable,
    files: list[Path],
    iterations: int = 3,
    **kwargs,
) -> tuple[float, float]:
    """執行效能測試"""
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        func(files, **kwargs)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    min_time = min(times)

    return avg_time, min_time


def main():
    print("=" * 60)
    print("並行處理效能測試")
    print("=" * 60)

    # 建立測試環境
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 測試不同數量的檔案
        file_counts = [10, 20, 50, 100]

        for count in file_counts:
            print(f"\n測試 {count} 個檔案")
            print("-" * 40)

            # 建立測試檔案
            files = create_test_files(tmpdir_path, count)

            # 循序檢查
            seq_avg, seq_min = benchmark("循序", check_sequential, files)
            print(f"循序處理：平均 {seq_avg:.3f}s，最快 {seq_min:.3f}s")

            # 並行檢查（不同的 worker 數量）
            for workers in [2, 4, 8]:
                par_avg, par_min = benchmark(
                    f"並行(map, {workers})",
                    check_parallel_map,
                    files,
                    max_workers=workers,
                )
                speedup = seq_avg / par_avg
                print(
                    f"並行處理 (map, {workers} workers)："
                    f"平均 {par_avg:.3f}s，最快 {par_min:.3f}s，"
                    f"加速 {speedup:.1f}x"
                )

            # 使用 as_completed
            par_avg, par_min = benchmark(
                "並行(as_completed, 4)",
                check_parallel_as_completed,
                files,
                max_workers=4,
            )
            speedup = seq_avg / par_avg
            print(
                f"並行處理 (as_completed, 4 workers)："
                f"平均 {par_avg:.3f}s，最快 {par_min:.3f}s，"
                f"加速 {speedup:.1f}x"
            )

            # 清理測試檔案
            for f in files:
                f.unlink()

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
