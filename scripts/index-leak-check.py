#!/usr/bin/env python3
"""列出文章正文裡出現、而只在同目錄 _index.md 段標裡定義的片語。

_index.md 的正文不會渲染（layouts/_default/list.html 不輸出 .Content），所以
文章正文引用那裡的段名或框架詞，讀者手上沒有對應的內容。

用法：
  scripts/index-leak-check.py content/sql             掃一個目錄
  scripts/index-leak-check.py content/sql a.md b.md   只掃指定的文章（驗證用）
  scripts/index-leak-check.py --all                   掃 content/ 下所有教學目錄
  scripts/index-leak-check.py --anchors               列出連到目錄頁錨點的連結（任何層數的路徑）

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


def page_url(path):
    """content/a/b/c.md → /a/b/c/；content/a/b/_index.md → /a/b/"""
    rel = os.path.relpath(path, "content")
    d, name = os.path.split(rel)
    return "/" + (d + "/" if d else "") + ("" if name == "_index.md" else name[:-3] + "/")


def anchors():
    """文章連到目錄頁錨點：目錄頁正文不渲染，錨點在網站上不存在。
    絕對路徑（/a/b/#x）與相對路徑（../#x、topics/#x）都解析；mdtools cards 比對的是
    markdown 裡有沒有那個段標，目錄頁的 markdown 有，所以 cards 對這一類放行。"""
    import posixpath
    sections = {"/" + os.path.dirname(p)[len("content/"):] + "/" for p in glob.glob("content/**/_index.md", recursive=True)}
    sections.add("/")
    hits = 0
    for f in sorted(glob.glob("content/**/*.md", recursive=True)):
        if f.endswith("_index.md"):
            continue
        base = page_url(f)
        for m in re.finditer(r"\]\(([^)#\s]*)#([^)]+)\)", open(f, encoding="utf-8").read()):
            target = m.group(1)
            if target == "" or target.startswith(("http:", "https:")):
                continue
            url = target if target.startswith("/") else posixpath.normpath(posixpath.join(base, target)) + "/"
            url = url.replace("//", "/")
            if url in sections:
                print(f"{f}\t{m.group(1)}#{m.group(2)}\t→ {url}")
                hits += 1
    return hits


def main(argv):
    if argv[:1] == ["--anchors"]:
        print(f"hits {anchors()}", file=sys.stderr)
        return
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
