#!/usr/bin/env python3
"""檢查知識卡的首段與「跟其他概念的關係」段各有沒有鄰卡連結。

用法（路徑照執行時所在的目錄起算；腳本本身寫出它在這支 skill 裡的完整路徑）：
    python3 <skill 目錄>/scripts/neighbor_link_check.py <卡片目錄> [<卡片> ...] [--heading 跟其他概念的關係]

- 不給卡片時，檢查卡片目錄第一層全部的 .md（_index.md 除外）。
- 給卡片時只檢查那幾張。可以給路徑；不含 `/` 的引數也可以只寫檔名或 slug
  （不帶 .md），這時在卡片目錄裡找。含 `/` 的路徑不存在時判 MISSING，不改找卡片目錄。
- 鄰卡連結：連結目標指到卡片目錄裡的另一張卡。目標的判讀：
  - 外部網址（含 `://`、`mailto:`）不算。
  - 絕對路徑（`/a/b/<slug>/`）：最後一段是卡的 slug，前面那幾段要是卡片目錄路徑的結尾
    （`/til/audio/knowledge-cards/x/` 對得上 `content/til/audio/knowledge-cards`）。
  - 帶 `.md` 的相對路徑（`x.md`、`./x.md`、`../dir/x.md`）：從卡片檔所在的目錄解析。
  - 不帶 `.md` 的相對路徑（`../x/`，網站的 pretty URL）：從這張卡的網址（卡片目錄/<自己的 slug>/）
    解析；只有一段的 `x` 視為同目錄。
  - 連到自己不算。圖片 `![](…)`、code fence 與行內程式碼裡的連結不算。
  - 連結形態：行內連結（標題可用雙引號、單引號或括號，目標可用尖括號包住）與參考式連結
    （`[text][ref]`、`[ref][]` 加 `[ref]: 目標` 定義行）。
- 首段：開頭的 frontmatter（`---` 或 `+++` 包住）之後、第一個 `## ` 段標之前。
- 「跟其他概念的關係」段：第一個內容等於 `## <heading>` 的段標（結尾的 `{#錨點}` 不計）之後、下一個 `## `
  段標之前。`--heading` 開頭的 `#` 與空白會被去掉，段標用字面比對。code fence 裡的行不當段標。

輸出（stdout，每張卡一行，tab 分欄）：
    OK       <檔案>  首段:<n> 跟其他概念的關係:<n>  <算到的鄰卡 slug，逗號分隔>
    NOLINK   <檔案>  首段:<n> 跟其他概念的關係:<n>  <算到的鄰卡 slug>
    NOHEAD   <檔案>  首段:<n>
    MISSING  <引數>
stderr 最後一行：`checked N card(s), M problem(s)`。

exit：0 = 全部 OK；1 = 有 NOLINK、NOHEAD 或 MISSING；
      2 = 引數錯、卡片目錄不存在，或沒有任何卡可檢查（這時沒有 checked 那一行）。
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path, PurePosixPath

INLINE_RE = re.compile(
    r"(?<!!)\[(?:[^\[\]]|\[[^\[\]]*\])*\]\(\s*(<[^>]*>|[^\s()]+(?:\([^\s()]*\))?)"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)
REF_USE_RE = re.compile(r"(?<!!)\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\[([^\]]*)\]")
REF_DEF_RE = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*<?([^\s>]+)>?", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")
ANCHOR_RE = re.compile(r"\s*\{#[^}]*\}\s*$")


def is_fence(line: str) -> bool:
    s = line.lstrip()
    return s.startswith("```") or s.startswith("~~~")


def strip_code(text: str) -> str:
    out, in_fence = [], False
    for line in text.splitlines():
        if is_fence(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(INLINE_CODE_RE.sub("", line))
    return "\n".join(out)


def card_slugs(card_dir: Path) -> set[str]:
    return {p.stem for p in card_dir.glob("*.md") if p.name != "_index.md"}


def resolve_target(target: str, card_dir: Path, self_slug: str) -> str | None:
    """連結目標指到卡片目錄裡某張卡時回傳那張卡的 slug，否則回傳 None。"""
    target = target.strip().strip("<>")
    if "://" in target or target.startswith("mailto:"):
        return None
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    is_md = target.rstrip("/").endswith(".md")
    if target.startswith("/"):
        parts = [p for p in target.split("/") if p]
        if len(parts) < 2:
            return None
        slug = parts[-1][:-3] if parts[-1].endswith(".md") else parts[-1]
        dir_parts = tuple(card_dir.resolve().parts)
        prefix = tuple(parts[:-1])
        return slug if dir_parts[-len(prefix):] == prefix else None
    if "/" not in target.rstrip("/") and not target.startswith("."):
        name = target.rstrip("/")
        return name[:-3] if name.endswith(".md") else name
    base = PurePosixPath(card_dir.as_posix()) if is_md else PurePosixPath(card_dir.as_posix()) / self_slug
    resolved = PurePosixPath(os.path.normpath(str(base / target.rstrip("/"))))
    if PurePosixPath(os.path.normpath(card_dir.as_posix())) != resolved.parent:
        return None
    name = resolved.name
    return name[:-3] if name.endswith(".md") else name


def split_sections(text: str, heading: str) -> tuple[str, str | None]:
    lines = text.lstrip("﻿").splitlines()
    i = 0
    if lines and lines[0].strip() in ("---", "+++"):
        fence = lines[0].strip()
        for j in range(1, len(lines)):
            if lines[j].strip() == fence:
                i = j + 1
                break
    target = heading.lstrip("#").strip()
    intro: list[str] = []
    pos: list[str] | None = None
    in_fence = False
    section = "intro"
    for line in lines[i:]:
        if is_fence(line):
            in_fence = not in_fence
        is_h2 = not in_fence and line.startswith("## ")
        if is_h2:
            if section == "pos":
                break
            title = ANCHOR_RE.sub("", line[3:]).strip()
            section = "pos" if (pos is None and title == target) else "other"
            if section == "pos":
                pos = []
            continue
        if section == "intro":
            intro.append(line)
        elif section == "pos":
            pos.append(line)
    return "\n".join(intro), ("\n".join(pos) if pos is not None else None)


def neighbor_links(section: str, full_text: str, slugs: set[str], card_dir: Path, self_slug: str) -> list[str]:
    body = strip_code(section)
    defs = {k.strip().lower(): v for k, v in REF_DEF_RE.findall(strip_code(full_text))}
    targets = [m.group(1) for m in INLINE_RE.finditer(body)]
    for m in REF_USE_RE.finditer(body):
        key = (m.group(2) or m.group(1)).strip().lower()
        if key in defs:
            targets.append(defs[key])
    found = []
    for t in targets:
        s = resolve_target(t, card_dir, self_slug)
        if s and s in slugs and s != self_slug:
            found.append(s)
    return found


def check(card_dir: Path, files: list[str], heading: str) -> tuple[list[str], int]:
    slugs = card_slugs(card_dir)
    if files:
        paths: list[tuple[str, Path]] = []
        for f in files:
            p = Path(f)
            if not p.is_file() and "/" not in f:
                for cand in (card_dir / f, card_dir / f"{f}.md"):
                    if cand.is_file():
                        p = cand
                        break
            paths.append((f, p))
    else:
        paths = [(str(p), p) for p in sorted(card_dir.glob("*.md")) if p.name != "_index.md"]
    out, problems = [], 0
    for arg, p in paths:
        if not p.is_file():
            out.append(f"MISSING\t{arg}")
            problems += 1
            continue
        text = p.read_text(encoding="utf-8")
        intro, pos = split_sections(text, heading)
        a = neighbor_links(intro, text, slugs, card_dir, p.stem)
        if pos is None:
            out.append(f"NOHEAD\t{p}\t首段:{len(a)}")
            problems += 1
            continue
        b = neighbor_links(pos, text, slugs, card_dir, p.stem)
        status = "OK" if a and b else "NOLINK"
        if status != "OK":
            problems += 1
        out.append(f"{status}\t{p}\t首段:{len(a)} 跟其他概念的關係:{len(b)}\t{','.join(a + b)}")
    return out, problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="知識卡的鄰卡連結檢查")
    ap.add_argument("card_dir")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--heading", default="跟其他概念的關係")
    args = ap.parse_args(argv)
    card_dir = Path(args.card_dir)
    if not card_dir.is_dir():
        print(f"卡片目錄不存在：{card_dir}", file=sys.stderr)
        return 2
    lines, problems = check(card_dir, args.files, args.heading)
    if not lines:
        print(f"沒有任何卡可檢查：{card_dir} 第一層沒有 .md（_index.md 除外）", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    print(f"checked {len(lines)} card(s), {problems} problem(s)", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
