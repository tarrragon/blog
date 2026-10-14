#!/usr/bin/env python3
"""把「撐、扛、垮、頂、掛在、站得住、咬、啃」這類物理動詞的命中，依它佔住的內容預先分類。

這支腳本只做候選分類，判定與改寫是人工的那一步（見 report #375）。
分類依據是動詞的詞形加上同一行有沒有負載相關的詞，所以它是啟發式：

1. 同一個詞形可能落在不同類，例如「扛」在「扛負載」是足夠性、在
   「硬扛協調」是負擔；腳本只看同一行有沒有負載詞，分錯的要人工改判。
2. 「掛在」多數是字面的技術用法（掛載 volume、程序掛在 session 上），
   腳本以同一行的技術詞先分到「字面或技術」，其餘才進「關係」。
3. 跳過程式碼區塊與 front matter 以外的行內程式碼不跳過——
   行內程式碼裡的命中多半是規則文件在討論這個詞本身，用 --exclude 排除。

用法：
    python3 scripts/physical-verb-scan.py                 # 掃 content/，排除 report 與 skills
    python3 scripts/physical-verb-scan.py content/backend # 只掃指定路徑
    python3 scripts/physical-verb-scan.py --list 失效結果  # 列出某一類的每一行
"""
import argparse
import collections
import pathlib
import re
import sys

LOAD = re.compile(
    r"流量|負載|QPS|TPS|請求|連線|尖峰|峰值|併發|並發|寫入|讀取|吞吐|容量|CPU|記憶體|"
    r"磁碟|資料庫|DB|叢集|節點|實例|伺服器|主機|佇列|額度|配額|上限|資料量|筆數|列數|規模|"
    r"connection|RPS|QPS|throughput|latency|pool|traffic|load|Aurora|PostgreSQL|MySQL|Redis"
)
TECH = re.compile(r"volume|session|subnet|掛載|mount|程序|process|pts|tty|`|容器|網卡|硬碟|節點上")

# (類別, 詞形 regex)；同一行依序比對，先命中的類別勝出
RULES = [
    ("突發緩衝", re.compile(r"(?<!支)(?:撐過|撐不過)")),
    ("耗盡時間", re.compile(r"(?<!支)(?:撐多久|撐不久|撐了多久)")),
    ("失效結果：故障擴散", re.compile(r"拖垮")),
    ("失效結果：過載", re.compile(r"壓垮|打垮|垮掉|扛不住|頂不住")),
    ("可信度", re.compile(r"站得住|站不住|站得起|站不起")),
    ("足夠性", re.compile(r"(?<!支)(?:撐得住|撐不住|撐住|撐起|撐得起|撐不起|能撐)|扛得住|扛住|扛下|頂得住|頂住")),
    ("負擔", re.compile(r"硬扛|扛起|扛著|扛|啃")),
    ("關係程度", re.compile(r"咬得|咬合")),
    ("關係", re.compile(r"掛在")),
    ("失效結果：其他", re.compile(r"垮")),
]

EXCLUDE_DEFAULT = ["content/report/", "content/skills/"]


def iter_lines(path):
    in_code = False
    in_fm = False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if n == 1 and line.strip() == "---":
            in_fm = True
            continue
        if in_fm:
            if line.strip() == "---":
                in_fm = False
            continue
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            yield n, line


def classify(line):
    for name, pat in RULES:
        m = pat.search(line)
        if not m:
            continue
        if name == "足夠性":
            return ("足夠性：負載" if LOAD.search(line) else "足夠性：其他"), m.group(0)
        if name == "負擔" and LOAD.search(line):
            return "足夠性：負載", m.group(0)
        if name == "關係" and TECH.search(line):
            return "字面或技術", m.group(0)
        return name, m.group(0)
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=["content"])
    ap.add_argument("--exclude", action="append", default=None,
                    help="排除的路徑前綴，可重複；預設排除 content/report/ 與 content/skills/")
    ap.add_argument("--list", metavar="類別", help="列出某一類（前綴比對）的每一行")
    args = ap.parse_args()
    excludes = args.exclude if args.exclude is not None else EXCLUDE_DEFAULT

    files = []
    for p in args.paths:
        pp = pathlib.Path(p)
        files += [pp] if pp.is_file() else sorted(pp.rglob("*.md"))
    files = [f for f in files if not any(str(f).startswith(e) for e in excludes)]

    counts = collections.Counter()
    rows = collections.defaultdict(list)
    for f in files:
        for n, line in iter_lines(f):
            cat, word = classify(line)
            if cat:
                counts[cat] += 1
                rows[cat].append((f, n, word, line.strip()))

    if args.list:
        for cat in sorted(rows):
            if cat.startswith(args.list):
                for f, n, word, text in rows[cat]:
                    print(f"{f}:{n}: [{cat}] {word} | {text[:120]}")
        return
    total = sum(counts.values())
    print(f"files scanned: {len(files)}, lines matched: {total}")
    for cat, c in counts.most_common():
        print(f"{c:5d}  {cat}")
    if total == 0:
        print("（零命中：先確認路徑與排除前綴，再當成乾淨）", file=sys.stderr)


if __name__ == "__main__":
    main()
