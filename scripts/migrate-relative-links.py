#!/usr/bin/env python3
"""
一次性腳本：把 content/ 底下所有 markdown 的相對連結改寫成 content 根絕對路徑。

寫法轉換範例：
  舊：[text](../../knowledge-cards/waf/)   （從 backend/00-service-selection/foo.md 寫）
  新：[text](/backend/knowledge-cards/waf/)

規則：
  - 只處理 [text](path) 形式的 inline link
  - 只改寫以 "./" 或 "../" 開頭的相對路徑
  - 保留原本的 trailing slash 與 anchor
  - 跳過圖片 ![alt](src)、外部協定、絕對路徑、純 anchor
  - 若 normalize 結果逃出 content/（開頭是 ..），保留原連結不動並警告
  - 若 [text] 裡含 ]（Hugo 允許含轉義字元的 link text），用保守的最短貪婪匹配處理

用法：
  python3 scripts/migrate-relative-links.py             # dry-run，印出統計與前 20 筆樣本
  python3 scripts/migrate-relative-links.py --apply     # 實際修改檔案
  python3 scripts/migrate-relative-links.py --file X.md # 只處理單檔（配合 --apply 使用）
"""

from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path

CONTENT_DIR = Path("content")

# 匹配 markdown inline link：](...)，但不匹配圖片 ![alt](src)
# 用 (?<!!) 排除前面是 ! 的情況
LINK_RE = re.compile(r"(?<!!)\]\(([^)\s]+)(\s+\"[^\"]*\")?\)")


def compute_url_base(md_path: Path) -> str:
    """根據 markdown 檔案位置推算它的 URL base 目錄（Hugo pretty URL 空間）。

    regular page: content/a/b/foo.md -> URL /a/b/foo/ -> base = /a/b/foo/
    _index.md   : content/a/b/_index.md -> URL /a/b/ -> base = /a/b/
    """
    rel = md_path.relative_to(CONTENT_DIR)
    if rel.name == "_index.md":
        parent = rel.parent
        return "/" if str(parent) in (".", "") else f"/{parent.as_posix()}/"
    stem = rel.with_suffix("")
    return f"/{stem.as_posix()}/"


def resolve_link(md_path: Path, link: str) -> str | None:
    """把相對 link 轉成 content 根絕對路徑。若不應改寫回傳 None。"""
    if not link:
        return None

    # 分出 anchor
    if "#" in link:
        path_part, frag = link.split("#", 1)
        anchor = f"#{frag}"
    else:
        path_part, anchor = link, ""

    # 只處理明確相對（./ 或 ../），其他全部跳過
    if not (path_part.startswith("./") or path_part.startswith("../")):
        return None

    url_base = compute_url_base(md_path)
    combined = posixpath.join(url_base, path_part)
    normalized = posixpath.normpath(combined)

    # 若 normalize 後逃出 content root（開頭是 ..），視為無效
    if normalized.startswith(".."):
        return None

    # normpath 會吃掉 trailing slash，按原樣補回
    if path_part.endswith("/") and not normalized.endswith("/"):
        normalized += "/"

    # 根目錄邊界
    if normalized == "":
        normalized = "/"

    return normalized + anchor


def process_file(md_path: Path, apply: bool) -> list[tuple[str, str]]:
    """回傳 (old_link, new_link) 變更清單。apply=True 時實際寫回檔案。"""
    text = md_path.read_text(encoding="utf-8")
    changes: list[tuple[str, str]] = []

    def sub(match: re.Match) -> str:
        link = match.group(1)
        title_part = match.group(2) or ""
        resolved = resolve_link(md_path, link)
        if resolved is None or resolved == link:
            return match.group(0)
        changes.append((link, resolved))
        return f"]({resolved}{title_part})"

    new_text = LINK_RE.sub(sub, text)

    if apply and changes and new_text != text:
        md_path.write_text(new_text, encoding="utf-8")

    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="實際修改檔案（不加此旗標為 dry-run）")
    parser.add_argument("--file", type=Path, help="只處理單一檔案")
    parser.add_argument("--sample", type=int, default=20, help="dry-run 時印出的樣本數")
    args = parser.parse_args()

    if args.file:
        md_files = [args.file]
    else:
        md_files = sorted(CONTENT_DIR.rglob("*.md"))

    total_files_changed = 0
    total_links_changed = 0
    samples: list[tuple[Path, str, str]] = []

    for md_path in md_files:
        changes = process_file(md_path, apply=args.apply)
        if changes:
            total_files_changed += 1
            total_links_changed += len(changes)
            for old, new in changes:
                if len(samples) < args.sample:
                    samples.append((md_path, old, new))

    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"[{mode}] {total_links_changed} links in {total_files_changed} files")

    if samples:
        print(f"\n--- first {len(samples)} changes ---")
        for md_path, old, new in samples:
            print(f"{md_path}")
            print(f"  - {old}")
            print(f"  + {new}")

    if not args.apply:
        print("\n（這是 dry-run；加上 --apply 才會實際修改檔案。）")

    return 0


if __name__ == "__main__":
    sys.exit(main())
