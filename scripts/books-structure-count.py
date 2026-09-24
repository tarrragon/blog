#!/usr/bin/env python3
"""書單分類的結構計數：書目小節總數、各線主題篇數。

書目小節＝各主題篇的 H2，扣掉三類非書目的節：
  - 每篇末尾的「為什麼只收這幾本／這兩本」與「這個主題接到哪裡」
  - 描述課而不是書的公開課段（段名含「課」或「影音」：「Yale 的兩門課……」「一門哲學課……」也算）
  - 比較多本書而不描述其中一本的綜合段（「這五本在哪裡分歧」）
  - 交付判定依據而不是書的判讀篇（JUDGMENT_PAGES）
主題篇＝各線目錄底下的文章，扣掉導讀、位置篇與書單層的說明文章（NON_TOPIC）。

用法：
  scripts/books-structure-count.py          印出計數，並比對 content/books/_index.md 維護區記錄的數字
  scripts/books-structure-count.py --list   另外列出每一個被計入的小節
記錄的數字寫在 _index.md 的一行：`<!-- books-structure: 小節=N 管理=a 技藝=b 財務=c -->`。
對不上時 exit 1：新增或移除書之後，同一次改動要把那一行與引用這些數字的地方一起改。
"""
import glob
import os
import re
import sys

ROOT = "content/books"
LINES = {"管理": "software-management/topics", "技藝": "craft", "財務": "finance"}
NON_TOPIC = {"craft-line-guide.md", "finance-line-guide.md", "positions.md",
             "starting-book-selection.md", "courses-not-found.md"}
JUDGMENT_PAGES = {"voice-and-silence.md"}
# 段名看不出是課程段的，逐條列在這裡（新增課程段時段名帶「課」字就不必登記）
NON_BOOK_HEADINGS = {"經濟學原理的後半整段接得住這個主題，而它接的是三本書共用的底"}
NON_BOOK = re.compile(r"為什麼只收|這個主題接到哪裡|課|影音|在哪裡分歧")


def topic_pages(sub):
    for f in sorted(glob.glob(os.path.join(ROOT, sub, "*.md"))):
        name = os.path.basename(f)
        if name == "_index.md" or name in NON_TOPIC:
            continue
        yield f


def book_sections(path):
    if os.path.basename(path) in JUDGMENT_PAGES:
        return []
    text = re.sub(r"```.*?```", "", open(path, encoding="utf-8").read(), flags=re.S)
    return [h for h in re.findall(r"^## (.+)$", text, re.M) if not NON_BOOK.search(h) and h.strip() not in NON_BOOK_HEADINGS]


def main():
    listing = "--list" in sys.argv
    counts, total = {}, 0
    for line, sub in LINES.items():
        pages = list(topic_pages(sub))
        counts[line] = len(pages)
        for p in pages:
            secs = book_sections(p)
            total += len(secs)
            if listing:
                for s in secs:
                    print(f"{line}\t{os.path.basename(p)}\t{s}")
    print(f"小節={total} " + " ".join(f"{k}={v}" for k, v in counts.items()))
    idx = open(os.path.join(ROOT, "_index.md"), encoding="utf-8").read()
    m = re.search(r"<!-- books-structure: (.*?) -->", idx)
    if not m:
        sys.exit("_index.md 沒有 books-structure 記錄行")
    recorded = dict(kv.split("=") for kv in m.group(1).split())
    actual = {"小節": str(total), **{k: str(v) for k, v in counts.items()}}
    diff = {k: (recorded.get(k), v) for k, v in actual.items() if recorded.get(k) != v}
    if diff:
        for k, (r, a) in diff.items():
            print(f"不符：{k} 記錄 {r}，實際 {a}", file=sys.stderr)
        sys.exit(1)
    print("與記錄一致")


if __name__ == "__main__":
    main()
