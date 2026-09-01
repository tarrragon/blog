#!/usr/bin/env python3
"""找出一張 report / record 卡在 skill 側的副本，並回報哪一邊比較新。

為什麼不用單一個鍵：副本與本體的對應在本庫有四種形態，每一種只有一個鍵抓得到。
檔名相同的用檔名；去專案化時改過標題的用 H1；兩者都改過的靠 bin/skill-mirror
的 mapping table；只在正文引用的靠內容掃描。少任何一個鍵，漏掉的那一群不會
報錯，只會讓清單變短——而清單變短與「本來就沒有副本」在畫面上長得一樣。

用法：
    scripts/principle-mirror-check.py <slug>     # 查一張
    scripts/principle-mirror-check.py --all      # 全庫掃，列出 report 側較新的
"""
import sys, os, re, glob, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_GLOBS = ['.claude/skills/*/references/**/*.md', 'content/skills/**/*.md']


def read(p):
    with open(p, encoding='utf8') as f:
        return f.read()


def title_of(path):
    m = re.search(r'^title:\s*"(.+?)"', read(path), re.M)
    return m.group(1).strip() if m else None


def h1_of(path):
    with open(path, encoding='utf8') as f:
        return f.readline().lstrip('# ').strip()


def mapping_table():
    """反查 bin/skill-mirror 的 find_report_slug()：skill 側 slug -> 目標 route。"""
    out, key = {}, None
    for line in read(os.path.join(ROOT, 'bin/skill-mirror')).splitlines():
        m = re.match(r'^\s{4}([a-z0-9-]+)\)$', line)
        if m:
            key = m.group(1)
            continue
        if key:
            m = re.search(r'"(/(?:report|record)/([a-z0-9-]+)/)"', line)
            if m:
                out[key] = m.group(2)
            key = None
    return out


def last_commit(path):
    r = subprocess.run(['git', 'log', '-1', '--format=%at', '--', path],
                       capture_output=True, text=True, cwd=ROOT)
    return int(r.stdout.strip() or 0)


def source_for(slug):
    for d in ('content/report', 'content/record'):
        p = os.path.join(ROOT, d, slug + '.md')
        if os.path.exists(p):
            return os.path.join(d, slug + '.md')
    return None


def skill_files():
    seen = []
    for g in SKILL_GLOBS:
        seen += glob.glob(os.path.join(ROOT, g), recursive=True)
    return sorted(set(os.path.relpath(p, ROOT) for p in seen))


def copies_of(slug, mt, files):
    src = source_for(slug)
    if not src:
        return None, []
    title = title_of(os.path.join(ROOT, src))
    hits = []
    for f in files:
        base = os.path.basename(f)[:-3]
        why = []
        if base == slug:
            why.append('同名')
        if title and h1_of(os.path.join(ROOT, f)) == title:
            why.append('H1 相同')
        if mt.get(base) == slug:
            why.append('mapping table')
        if slug in read(os.path.join(ROOT, f)):
            why.append('內容提及')
        if why:
            hits.append((f, '+'.join(why)))
    return src, hits


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    mt, files = mapping_table(), skill_files()

    if sys.argv[1] == '--all':
        stale = 0
        srcs = sorted(glob.glob(os.path.join(ROOT, 'content/report/*.md')) +
                      glob.glob(os.path.join(ROOT, 'content/record/*.md')))
        for p in srcs:
            slug = os.path.basename(p)[:-3]
            if slug == '_index':
                continue
            src, hits = copies_of(slug, mt, files)
            st = last_commit(src)
            behind = [f for f, _ in hits
                      if f.startswith('.claude/') and last_commit(f) < st]
            if behind:
                stale += 1
                print(f"{slug}")
                for f in behind:
                    print(f"    落後: {f}")
        print(f"\n本體較新的副本出現在 {stale} 張卡上。")
        return 0

    slug = sys.argv[1]
    src, hits = copies_of(slug, mt, files)
    if src is None:
        print(f"找不到 content/report/{slug}.md 或 content/record/{slug}.md")
        return 1
    st = last_commit(src)
    print(f"{slug}  （本體：{src}）")
    if not hits:
        print("  副本 0 份")
        return 0
    for f, why in hits:
        flag = '  ← 落後，要同步' if last_commit(f) < st else ''
        print(f"  [{why}] {f}{flag}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
