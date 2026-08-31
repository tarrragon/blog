# 找出每篇頻率最高的實詞（承重術語候選），供人工確認它有沒有被定義過
import re,io,sys,glob,collections
STOP=set('''這個 那個 一個 什麼 沒有 可以 因此 所以 而且 但是 如果 就是 不是 已經 還是 或者
一種 兩種 三種 那些 這些 其他 本篇 那一篇 這一篇 文章 內容 部分 情況 時候 例如 也就是
出現 使用 需要 進行 決定 產生 造成 變成 開始 結果 條件 方式 問題 之間 以及 而是 只有
台灣 中國 日本 法國 英國 美國 加密 市場 價格 成品 讀者 作法 名字 意思 東西
那一篇 那一篇寫 這一種 那一種 那一路 這一類 那一項 這一項 那一 這一 分鐘 這個字 那個字
單篇 未寫 見某 以上 以下 之後 之前 同一 同樣 各自 完整 具體 實際 直接 其中 底下 上面'''.split())
def terms(t):
    t=re.sub(r'```.*?```','',t,flags=re.S)
    t=re.sub(r'\[([^\]]*)\]\([^)]*\)',r'\1',t)
    t=re.sub(r'^---.*?^---','',t,flags=re.S|re.M)
    c=collections.Counter()
    for n in (4,3,2):
        for m in re.finditer(r'[一-鿿]{%d}'%n,t):
            w=m.group(0)
            if w in STOP: continue
            c[w]+=1
    return c
for f in sorted(sys.argv[1:]):
    t=io.open(f,encoding='utf-8').read()
    c=terms(t)
    # 只留下夠長且夠頻繁的
    top=[(w,n) for w,n in c.most_common(60) if len(w)>=3 and n>=4][:3]
    if not top:
        top=[(w,n) for w,n in c.most_common(60) if n>=6][:3]
    if top:
        print(f"{f.split('/')[-1]:44} " + "  ".join(f"{w}×{n}" for w,n in top))
