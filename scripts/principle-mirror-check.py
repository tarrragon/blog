#!/usr/bin/env python3
"""找出一張 report / record 卡在 skill 側的副本，並回報哪一邊比較新。

為什麼不用單一個鍵：副本與本體的對應在本庫有四種形態，每一種只有一個鍵抓得到。
檔名相同的用檔名；去專案化時改過標題的用 H1；兩者都改過的靠 bin/skill-mirror
的 mapping table；只在正文引用的靠內容掃描。少任何一個鍵，漏掉的那一群不會
報錯，只會讓清單變短——而清單變短與「本來就沒有副本」在畫面上長得一樣。

用法：
    scripts/principle-mirror-check.py <slug>                # 查一張
    scripts/principle-mirror-check.py <slug> --diff [rev]   # 查一張，並判斷改前的句子在不在副本裡
    scripts/principle-mirror-check.py --all                 # 全庫掃，列出 report 側較新的

--diff 取本體在工作樹相對 rev（預設 HEAD，也就是這次還沒提交的改動）刪掉或改掉的行，依句末標點
（。；！？）切成句子，逐句在每份副本裡找逐字的出現（兩邊都先拿掉粗體標記、把連結換成連結文字）：
找得到，代表副本逐字抄了那一句（措辭本身可能就是 skill 用來判讀的依據），印「→ 同步」；找不到，
代表副本已經改寫成 skill 自己的寫法，只改措辭或案例時不同步。改動是不是動了規則、判斷標準或處置，
要人判斷；改前的句子含數字、否定或情態字（跟 bin/changed-lines 同一組）、必修或可改時，工具印出
提醒：這類改動常常改了規則。同一段裡沒有改的句子不算改前的句子（扣掉改後版本裡還在的句子）。
少於 12 個字元的片段不拿去比對，有的話印出它們的數量與一個例子。沒有任何改動時印「沒有任何改動」
（給的 commit 不對）；diff 裡沒有任何刪掉或改掉的行時印「只有新增」。
找不到 slug 時 exit 1；引數錯或 git diff 失敗時 exit 2。

修改本腳本或 bin/skill-mirror 之後（新增 principle 卡會編輯 bin/skill-mirror 的
find_report_slug()，它是本腳本的 mapping 來源），逐個跑過這四個驗收案例再提交：

    multi-round-review-minimum-three-rounds  靠 H1 找到 minimum-three-rounds.md，並標為落後
    teaching-article-context-method          靠 mapping table 找到 teaching-article-context.md
    basics-anchor-the-advanced               靠同名找到
    description-frames-the-article           副本 0 份

前三個案例的正確輸出都至少有一行，所以「跑起來沒報錯」不算通過。
"""
import sys, os, re, glob, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_GLOBS = ['.claude/skills/*/references/**/*.md', 'content/skills/**/*.md']


def read(p):
    with open(p, encoding='utf8') as f:
        return f.read()


def title_of(path):
    m = re.search(r'^title:\s*"(.+?)"\s*$', read(path), re.M)
    if m:
        return m.group(1).strip()
    m = re.search(r'^title:\s*([^"\n].*?)\s*$', read(path), re.M)
    return m.group(1).strip() if m else None


def h1_of(path):
    for line in read(path).lstrip('\ufeff').splitlines():
        if line.strip():
            return line.lstrip('# ').strip()
    return ''


# mapping 條目數的下限。低於這個值多半是解析壞了而不是表真的變小——
# 這支腳本存在的理由就是「靜默零命中」，所以它自己的鍵失效時要出聲。
MAPPING_FLOOR = 10


def mapping_table(warn=True):
    """反查 bin/skill-mirror 的 find_report_slug()：skill 側 slug -> 目標 route。

    縮排刻意不綁死：原本要求正好四個空白，而 shell 檔重排縮排是常見編輯，
    綁死的版本在那種情況下回傳空 dict 而整支腳本照常跑完。
    """
    out, key = {}, None
    for line in read(os.path.join(ROOT, 'bin/skill-mirror')).splitlines():
        m = re.match(r'^\s*([a-z0-9-]+)\)$', line)
        if m:
            key = m.group(1)
            continue
        if key:
            m = re.search(r'"(/(?:report|record)/([a-z0-9-]+)/)"', line)
            if m:
                out[key] = m.group(2)
            key = None
    if warn and len(out) < MAPPING_FLOOR:
        print(f"警告：只從 bin/skill-mirror 解析到 {len(out)} 條 mapping"
              f"（預期至少 {MAPPING_FLOOR} 條）。這一個鍵可能已經失效，"
              f"下面的結果會少一整類副本。", file=sys.stderr)
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


def normalize(text):
    """比對前兩邊都做的正規化：粗體標記拿掉、連結 [文字](網址) 只留文字。

    副本去專案化時常改掉連結的網址、保留或拿掉粗體；只正規化一邊的話，逐字抄的句子會漏中。
    """
    return re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text).replace('**', '')


# 替換了就可能改掉規則意思的字：數字、否定與情態字、嚴重度的名字。跟 bin/changed-lines 的
# MEANING_CHARS 是同一組（bin/tests 比對兩份）；改一邊要改另一邊。
MEANING_CHARS = "不沒別勿無非未莫會要先必可須應該得能"
MEANING_WORDS = ("必修", "可改")


def sentences_of(lines):
    """diff 的行依句末標點（。；！？）切成句子，正規化之後回傳 (≥12 字元的句子, 更短的片段)。"""
    long_, short = [], []
    for line in lines:
        body = normalize(line.strip().lstrip('-*>').strip())
        for s in re.split(r'[。；！？]', body):
            s = s.strip()
            if len(s) >= 12:
                long_.append(s)
            elif s:
                short.append(s)
    return long_, short


def removed_sentences(src, rev):
    """本體在工作樹相對 rev 刪掉或改掉的句子：(句子, 短片段, diff 有沒有任何 - 行)。

    diff 的 - 行在 Markdown 裡多半是一整段，所以依句末標點切成句子：副本常常只抄了一段裡的一句。
    同一段裡沒有改的句子也在 - 行裡，所以扣掉改後（+ 行）裡還在的句子，剩下的才是改前的句子。
    少於 12 個字元的片段不拿去副本裡比對（單一個詞會到處誤中），另外回傳，讓輸出說出它們存在：
    「審查時列為必修」改成「可改」這類短句的改動就落在這裡。git diff 失敗時回傳 (False, False, False)。
    """
    r = subprocess.run(['git', 'diff', '-U0', rev, '--', src],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return False, False, False
    minus = [l[1:] for l in r.stdout.splitlines() if l.startswith('-') and not l.startswith('---')]
    plus = [l[1:] for l in r.stdout.splitlines() if l.startswith('+') and not l.startswith('+++')]
    old_long, old_short = sentences_of(minus)
    new_long, new_short = sentences_of(plus)
    keep = set(new_long) | set(new_short)
    return ([s for s in old_long if s not in keep], [s for s in old_short if s not in keep], bool(minus))


def meaning_bearing(sentences):
    """含數字、否定或情態字、嚴重度名字的句子：改了它們很可能改了規則，要照判定一。"""
    return [s for s in sentences
            if re.search(r'[0-9０-９一二三四五六七八九十兩]', s)
            or any(c in s for c in MEANING_CHARS) or any(w in s for w in MEANING_WORDS)]


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
                      if f.startswith('.claude/')
                      and 0 < last_commit(f) < st]
            if behind:
                stale += 1
                print(f"{slug}")
                for f in behind:
                    print(f"    落後: {f}")
        print(f"\n本體較新的副本出現在 {stale} 張卡上"
              f"（mapping 這個鍵解析到 {len(mt)} 條）。")
        print("這個判定用的是 git commit 時間，不看內容——副本晚於本體 commit"
              "而內容已經分岔的，這裡不會出現。")
        return 0

    slug = sys.argv[1]
    rev = None
    if len(sys.argv) > 2:
        if sys.argv[2] != '--diff' or len(sys.argv) > 4:
            print(__doc__)
            return 2
        rev = sys.argv[3] if len(sys.argv) == 4 else 'HEAD'
    src, hits = copies_of(slug, mt, files)
    if src is None:
        print(f"找不到 content/report/{slug}.md 或 content/record/{slug}.md")
        return 1
    removed, short, had_minus = removed_sentences(src, rev) if rev else (None, None, None)
    if removed is False:
        print(f"git diff {rev} 失敗（rev 打錯？）")
        return 2
    st = last_commit(src)
    print(f"{slug}  （本體：{src}）")
    if removed is not None:
        print(f"  本體相對 {rev} 刪掉或改掉的句子：{len(removed)} 句")
        changed_any = had_minus or subprocess.run(['git', 'diff', '--quiet', rev, '--', src], cwd=ROOT).returncode == 1
        if not changed_any:
            print(f"  本體相對 {rev} 沒有任何改動：給的 commit 不對（改動已經提交時給改動之前的 commit）")
        elif not had_minus:
            print("  這次只有新增，沒有改前的句子：副本不必因為措辭而同步")
        if short:
            print(f"  另有 {len(short)} 個少於 12 字元的改前片段沒有拿去比對（例：{short[0]}）：打開本體與副本對照這幾處")
        risky = meaning_bearing(removed + short)
        if risky:
            print(f"  改前的句子有 {len(risky)} 句含數字、否定或情態字、必修或可改（例：{risky[0][:40]}）："
                  "這類改動常常改了規則，照判定一確認；判不出時同步")
    if not hits:
        print("  副本 0 份")
        return 0
    for f, why in hits:
        lc = last_commit(f)
        flag = '  ← 尚未 commit' if lc == 0 else (
            '  ← 落後，要同步' if lc < st else '')
        print(f"  [{why}] {f}{flag}")
        if removed:
            raw = normalize(read(os.path.join(ROOT, f)))
            text = raw + '\n' + raw.replace('\n', '')  # 副本把一句拆成兩行時也比對得到
            found = [s for s in removed if s in text]
            if found:
                print(f"      改前的句子在副本裡逐字出現 {len(found)} 句（例：{found[0][:40]}）→ 同步")
            else:
                print("      改前的句子沒有逐字出現在副本裡 → 只改措辭或案例時不同步；改了規則、判斷標準或處置時同步")
    return 0


if __name__ == '__main__':
    sys.exit(main())
