#!/usr/bin/env python3
"""
MarkdownLinkChecker 效能分析

使用 cProfile 分析 Markdown 連結檢查器的效能瓶頸。
"""

import cProfile
import pstats
import re
import tempfile
from io import StringIO
from pathlib import Path


class MarkdownLinkChecker:
    """簡化版的 Markdown 連結檢查器（用於效能分析）"""

    INLINE_LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
    REFERENCE_DEF_PATTERN = re.compile(r"(?m)^\s*\[([^\]]+)\]:\s*(.+)$")
    REFERENCE_USE_PATTERN = re.compile(r"\[([^\]]+)\]\[([^\]]+)\]")

    def parse_links(self, content: str) -> list[dict]:
        """解析 Markdown 內容中的連結"""
        links = []

        # 收集引用式連結定義
        reference_defs = {}
        for match in self.REFERENCE_DEF_PATTERN.finditer(content):
            ref_name = match.group(1).lower()
            ref_target = match.group(2).strip()
            reference_defs[ref_name] = ref_target

        # 追蹤程式碼區塊狀態
        in_code_block = False
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            # 檢查程式碼區塊
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # 行內連結
            for match in self.INLINE_LINK_PATTERN.finditer(line):
                links.append({
                    "text": match.group(1),
                    "target": match.group(2),
                    "line": line_num,
                })

            # 引用式連結
            for match in self.REFERENCE_USE_PATTERN.finditer(line):
                ref_name = match.group(2).lower()
                if ref_name in reference_defs:
                    links.append({
                        "text": match.group(1),
                        "target": reference_defs[ref_name],
                        "line": line_num,
                    })

        return links

    def check_file(self, file_path: str) -> dict:
        """檢查單一檔案"""
        path = Path(file_path)

        if not path.exists():
            return {"file": file_path, "error": "File not found", "links": []}

        content = path.read_text(encoding="utf-8")
        links = self.parse_links(content)

        return {
            "file": file_path,
            "total_links": len(links),
            "links": links,
        }

    def check_directory(self, directory: str) -> list[dict]:
        """檢查目錄中的所有 Markdown 檔案"""
        results = []
        dir_path = Path(directory)

        md_files = list(dir_path.rglob("*.md"))

        for md_file in md_files:
            result = self.check_file(str(md_file))
            results.append(result)

        return results


def create_test_files(directory: Path, count: int) -> list[Path]:
    """建立測試用的 Markdown 檔案"""
    files = []

    for i in range(count):
        file_path = directory / f"test_{i:04d}.md"
        content = f"""# Test Document {i}

This is a test markdown file with various links.

## Inline Links

- [Link to file {i}](./file_{i}.md)
- [External link](https://example.com/page/{i})
- [Another file](../parent/doc_{i}.md)
- [Deep link](./folder/subfolder/deep_{i}.md)

## Reference Links

Check the [documentation][docs] for more information.
See also the [API reference][api] and [examples][examples].

[docs]: ./docs/index.md
[api]: ./api/reference.md
[examples]: ./examples/demo.md

## Code Block

```python
# Links in code blocks should be ignored
link = "[not a link](./ignored.md)"
print("This [link](also_ignored.md) is in code")
```

## More Content

Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

Here's another [inline link](./another_{i}.md) in the middle of text.
"""
        file_path.write_text(content)
        files.append(file_path)

    return files


def profile_checker(file_count: int = 50):
    """執行效能分析"""
    print(f"建立 {file_count} 個測試檔案...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 建立測試檔案
        create_test_files(tmpdir_path, file_count)

        # 建立檢查器
        checker = MarkdownLinkChecker()

        # 使用 cProfile 進行分析
        print("執行效能分析...")
        profiler = cProfile.Profile()
        profiler.enable()

        # 執行被分析的程式碼
        results = checker.check_directory(str(tmpdir_path))

        profiler.disable()

        # 輸出結果
        print(f"\n檢查了 {len(results)} 個檔案")
        total_links = sum(r["total_links"] for r in results)
        print(f"共找到 {total_links} 個連結")

        # 輸出效能分析結果
        print("\n" + "=" * 60)
        print("效能分析結果（按累計時間排序，前 20 個）")
        print("=" * 60)

        stream = StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats("cumulative")
        stats.print_stats(20)
        print(stream.getvalue())

        # 按呼叫次數排序
        print("=" * 60)
        print("效能分析結果（按呼叫次數排序，前 10 個）")
        print("=" * 60)

        stream = StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats("calls")
        stats.print_stats(10)
        print(stream.getvalue())


def main():
    print("=" * 60)
    print("MarkdownLinkChecker 效能分析")
    print("=" * 60)
    print()

    profile_checker(50)

    print("=" * 60)
    print("分析完成")
    print("=" * 60)
    print("""
常見瓶頸：
1. 檔案 I/O（read_text）
2. 正則表達式匹配（finditer）
3. 字串分割（split）
4. 字典操作

優化建議：
1. 並行處理檔案 I/O
2. 預編譯正則表達式
3. 使用生成器避免記憶體配置
""")


if __name__ == "__main__":
    main()
