#!/usr/bin/env python3
"""列出每篇的高頻實詞，供人工判斷它有沒有被定義過（承重術語候選）。

這支腳本只做候選清單，判定是人工的那一步。它的射程有三個限制，
用它之前要知道：

1. 只掃連續的中日韓漢字。英文術語（curdling point、CFD）看不到。
2. 一到四字都掃，而一字詞另設較高的頻率門檻（單字多半是功能詞）。
   這一項是為了讓「羹」這種單字承重術語現形——它在某一篇出現 40 次
   而複合詞形只有 4 次，用複合詞門檻會完全看不到它。
3. 比對用 lookahead 取重疊窗，所以「凝固溫度」出現三次就數到三次。
   非重疊比對會讓計數變成字元相位的函數（凝固溫 / 度很高 / 啊凝固），
   那個實作回報的排序不是頻率排序。

濾詞表要隨這一批的文體調整：新體例會製造自己的高頻詞（例如一批文章
統一採用某個路由句型之後，那個句型會佔據多數檔案的首位），而那些詞
對這個掃描是雜訊。判斷標準是問這個詞承不承擔內容。
"""
import re
import io
import sys
import glob
import collections

STOP = set('''這個 那個 一個 什麼 沒有 可以 因此 所以 而且 但是 如果 就是 不是 已經 還是 或者
一種 兩種 三種 那些 這些 其他 本篇 那一篇 這一篇 文章 內容 部分 情況 時候 例如 也就是
出現 使用 需要 進行 決定 產生 造成 變成 開始 結果 條件 方式 問題 之間 以及 而是 只有
台灣 中國 日本 法國 英國 美國 加密 市場 價格 成品 讀者 作法 名字 意思 東西
那一篇 那一篇寫 這一種 那一種 那一路 這一類 那一項 這一項 那一 這一 分鐘 這個字 那個字
單篇 未寫 見某 以上 以下 之後 之前 同一 同樣 各自 完整 具體 實際 直接 其中 底下 上面
的 是 在 有 和 與 就 也 都 而 一 不 了 這 那 它 們 個 之 於 為 以 或 對 到 從 被 把 讓 用'''.split())

# 一字詞的門檻另計：單字多半是功能詞，要更高的頻率才值得看
MIN_N_MULTI = 4
MIN_N_SINGLE = 8   # 單字算的是「在詞邊界上出現」的次數，門檻因此低於總出現次數
TOP_K = 3


def terms(text):
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'^---.*?^---', '', text, flags=re.S | re.M)
    counter = collections.Counter()
    for n in (4, 3, 2, 1):
        # lookahead 取重疊窗：頻率才不會變成字元相位的函數
        for m in re.finditer(r'(?=([一-鿿]{%d}))' % n, text):
            word = m.group(1)
            if word in STOP:
                continue
            counter[word] += 1
    return counter


def standalone_count(text, char):
    """單字在詞邊界上出現幾次。

    分開「羹」與「度」的不是包含關係（兩者都常在複合詞裡），是這個字
    會不會單獨成詞。中文沒有空格，所以用鄰接的虛詞與標點當邊界訊號：
    「就不叫羹」「台灣的羹」算，而「溫度」裡的度不算。
    """
    boundary = r'[的是叫成當把被跟與和，。、；：？！「」（）\s]'
    pat = r'(?:^|%s)%s(?:$|%s)' % (boundary, re.escape(char), boundary)
    return len(re.findall(pat, text))


def candidates(counter, text):
    out = []
    for word, n in counter.most_common():
        if len(word) == 1:
            # 單字要在詞邊界上站得住才算候選，否則它只是複合詞的碎片
            if standalone_count(text, word) < MIN_N_SINGLE:
                continue
        elif n < MIN_N_MULTI:
            continue
        # 已經被更長的候選涵蓋、且次數相近的，不重複佔位
        if any(word in longer and n <= cnt * 1.5 for longer, cnt in out):
            continue
        out.append((word, n))
        if len(out) == TOP_K:
            break
    return out


def main(paths):
    total = 0
    for path in sorted(paths):
        text = io.open(path, encoding='utf-8').read()
        top = candidates(terms(text), text)
        if top:
            total += len(top)
            print('%-44s %s' % (path.split('/')[-1],
                                '  '.join('%s×%d' % (w, n) for w, n in top)))
    print('\n候選總數 %d（這是清單，不是判定；逐個回原文看首次出現處有沒有定義）' % total)


if __name__ == '__main__':
    args = sys.argv[1:]
    files = [f for a in args for f in (glob.glob(a) if '*' in a else [a])]
    main(files)
