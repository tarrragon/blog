#!/usr/bin/env python3
"""列出文章正文裡出現、而只在同目錄 _index.md 段標裡定義的片語。

_index.md 的正文不會渲染（layouts/_default/list.html 不輸出 .Content），所以
文章正文引用那裡的段名或框架詞，讀者手上沒有對應的內容。

用法：
  scripts/index-leak-check.py content/sql             掃一個目錄
  scripts/index-leak-check.py content/sql a.md b.md   只掃指定的文章（驗證用）
  scripts/index-leak-check.py --all                   掃 content/ 下所有教學目錄

候選片語取自 _index.md 的 ##–#### 段標、切開標點之後至少五個漢字的片段。
文章的段標與連結文字不算（前者是文章自己的段名，後者是被連那一篇的標題），
在三篇以上出現的片語視為共用模板段名而略過。命中是候選，逐條判讀：
成員或定義就寫在同一段的合規，要讀者去目錄頁找那一段的違規。
"""
import glob
import os
import re
import sys

SKIP_DIRS = ("/report/", "/record/", "/work-log/", "/til/")  # 目錄頁在引述文章，方向相反


def phrases(index_path):
    text = open(index_path, encoding="utf-8").read()
    out = set()
    for m in re.finditer(r"^#{2,4}\s+(.+)$", text, re.M):
        heading = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", m.group(1))
        for seg in re.split(r"[，。：；、「」（）()\s—？?！]+|問|的是", heading):
            seg = seg.strip("*`")
            if len(re.findall(r"[一-鿿]", seg)) >= 5:
                out.add(seg)
    return out


def body(path):
    text = open(path, encoding="utf-8").read()
    text = re.sub(r"^---.*?---", "", text, count=1, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"^#.*$", "", text, flags=re.M)
    text = re.sub(r"\[[^\]]*\]\([^)]*\)", "", text)
    return text


def scan(directory, only=None):
    index_path = os.path.join(directory, "_index.md")
    if not os.path.exists(index_path):
        return 0
    cands = phrases(index_path)
    files = only or [f for f in glob.glob(os.path.join(directory, "*.md")) if not f.endswith("_index.md")]
    bodies = {f: body(f) for f in files}
    spread = {p: sum(p in b for b in bodies.values()) for p in cands}
    hits = 0
    for f, b in sorted(bodies.items()):
        for p in sorted(cands):
            if p in b and (only or spread[p] <= 2):
                i = b.index(p)
                ctx = b[max(0, i - 20): i + len(p) + 20].replace("\n", " ")
                print(f"{f}\t{p}\t…{ctx}…")
                hits += 1
    return hits


def main(argv):
    if argv[:1] == ["--all"]:
        total = 0
        for idx in sorted(glob.glob("content/**/_index.md", recursive=True)):
            d = os.path.dirname(idx)
            if not any(s in d + "/" for s in SKIP_DIRS):
                total += scan(d)
        print(f"hits {total}", file=sys.stderr)
        return
    if not argv:
        sys.exit(__doc__)
    print(f"hits {scan(argv[0], argv[1:] or None)}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
