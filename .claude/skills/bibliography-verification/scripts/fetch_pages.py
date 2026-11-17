#!/usr/bin/env python3
"""依站點登記表分流書目連結：登記成 curl 的抓一次頁面，登記成瀏覽器的列出來交給瀏覽器查證。

用法：
    python3 -I scripts/fetch_pages.py <連結清單檔> <存頁面的目錄>

  <連結清單檔>   一行一條網址；空行與 # 開頭的行略過。
  <存頁面的目錄> 抓下來的頁面存成 <序號>.html；目錄不存在時建立。放在 repo 以外的暫存目錄。
                 同一個序號的舊檔在送出請求之前刪掉，所以連線失敗時不會讀到上一次留下的頁面。

站點登記表固定讀本檔所在 skill 的 references/site-registry.md（第一欄的網域、第二欄的查證方式）。
查證方式不是 curl 或「瀏覽器」的列略過，那個網域照沒有登記處理（走 curl）。
一條網址對得上好幾列時，取網域最長的那一列（www.example.com 的列優先於 example.com 的列）。

stdout 每條連結印一行，欄位以 | 分隔：
    序號|route|http|blocked|網址|title|isbn
  route    curl 或 browser（browser 的那幾條不送出請求，http 與 blocked 印 -）
  http     curl 回的狀態碼；連線失敗印 000，curl 的錯誤訊息第一行印到 stderr
  blocked  yes：狀態落在 BLOCK_STATUS，或頁面含 BLOCK_MARKERS 的字樣；no：其他
  title    頁面的 <title>；http 是 000 時空白。頁面依 <meta charset> 解碼，沒寫時用 UTF-8
  isbn     頁面裡通過檢查碼驗證的 ISBN-13，以及緊接在「ISBN」字樣之後的 ISBN-10，
           依出現順序、去重、以逗號分隔，最多 MAX_ISBNS 個

stderr 最後一行是計數：`fetch_pages: N url(s), C curl, B browser, K blocked, F failed`。
failed 是 http 為 000 的條數。沒有印出這一行代表腳本中途中止，不代表通過。

exit code：0 正常結束（有 blocked 或 failed 也是 0，逐行讀 http 與 blocked 兩欄決定處置）；
2 引數錯、連結清單檔不存在或是空的、讀不到站點登記表，或環境裡找不到 curl；
其他非零（例如 1）是中途中止，讀 stderr 的 traceback。

同一個主機名的兩次請求之間至少隔 MIN_INTERVAL_SECONDS 秒；每條連結最多花 25 秒（curl 的 -m）。
條數多時總時間會超過 agent shell 的單次執行上限，把清單分批或放到背景執行。

每條連結的請求只送一次，不重試、不換標頭：被擋的網站改用瀏覽器查證，不在這裡想辦法繞過。
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

REGISTRY = Path(__file__).resolve().parent.parent / "references" / "site-registry.md"

# Amazon 對 curl 的預設 User-Agent 回 503，所以每個網站都固定送這一個瀏覽器的 User-Agent，
# 只送一次、不輪換；被擋之後也不改標頭重試（理由見檔頭最後一段）。
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
BLOCK_STATUS = {"403", "429", "503"}
# 只收驗證頁本身才會出現的字樣：單獨的 captcha 會命中正常頁面嵌入的 reCAPTCHA 腳本與書名。
BLOCK_MARKERS = (
    "validatecaptcha",
    "enter the characters you see below",
    "robot check",
    "are you a robot",
    "verify you are human",
    "請輸入驗證碼",
)
MAX_ISBNS = 20
# 同一個主機名的兩次請求之間至少隔這麼多秒，避免連續幾十條打在同一個網站上、被自己的速率觸發 429。
MIN_INTERVAL_SECONDS = 3.0

ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
CHARSET_RE = re.compile(rb"<meta[^>]+charset=[\"']?([A-Za-z0-9_-]+)", re.I)
ISBN13_RE = re.compile(r"(?<!\d)(97[89](?:[-\s]?\d){10})(?!\d)")
# Amazon 在「ISBN-10」與冒號之間夾了方向控制字元（U+200E、U+200F），所以分隔符一併收。
ISBN10_RE = re.compile(
    r"ISBN(?:-10)?[\s‎‏:：]*((?:\d[-\s]?){9}[\dXx])(?![\dXx])", re.I
)


def load_registry(text: str) -> dict[str, str]:
    """回傳 {網域: 'curl' | 'browser'}；查證方式不是這兩個值的列略過。"""
    routes: dict[str, str] = {}
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        domain, method = m.group(1).strip().lower(), m.group(2).strip()
        if method == "curl":
            routes[domain] = "curl"
        elif method == "瀏覽器":
            routes[domain] = "browser"
    return routes


def route_for(url: str, routes: dict[str, str]) -> str:
    host = (urlparse(url).hostname or "").lower()
    for domain in sorted(routes, key=len, reverse=True):
        if host == domain or host.endswith("." + domain):
            return routes[domain]
    return "curl"


def decode_page(raw: bytes) -> str:
    m = CHARSET_RE.search(raw[:4096])
    encoding = m.group(1).decode("ascii", "ignore") if m else "utf-8"
    try:
        return raw.decode(encoding, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def extract_title(page: str) -> str:
    m = TITLE_RE.search(page)
    if not m:
        return ""
    title = html.unescape(m.group(1))
    return re.sub(r"\s+", " ", title).strip()[:140].replace("|", "/")


def _valid_isbn13(d: str) -> bool:
    return sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d)) % 10 == 0


def _valid_isbn10(d: str) -> bool:
    total = sum((10 - i) * (10 if c in "Xx" else int(c)) for i, c in enumerate(d))
    return total % 11 == 0


def extract_isbns(page: str) -> list[str]:
    # 先去掉標籤：Amazon 把「ISBN-10 :」與號碼放在兩個 <span> 裡。
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    found: list[tuple[int, str]] = []
    for m in ISBN13_RE.finditer(text):
        d = re.sub(r"\D", "", m.group(1))
        if len(d) == 13 and _valid_isbn13(d):
            found.append((m.start(), d))
    for m in ISBN10_RE.finditer(text):
        d = re.sub(r"[-\s]", "", m.group(1)).upper()
        if len(d) == 10 and _valid_isbn10(d):
            found.append((m.start(1), d))
    seen: list[str] = []
    for _, d in sorted(found):
        if d not in seen:
            seen.append(d)
        if len(seen) == MAX_ISBNS:
            break
    return seen


def is_blocked(status: str, page: str) -> bool:
    if status in BLOCK_STATUS:
        return True
    lowered = page.lower()
    return any(marker in lowered for marker in BLOCK_MARKERS)


def fetch(url: str, out: Path) -> str:
    if out.exists():
        out.unlink()
    result = subprocess.run(
        # --compressed：Amazon 有時不管請求有沒有宣告就回 gzip 壓縮的內容，不解壓的話頁面讀不出書名與 ISBN。
        ["curl", "-sS", "-L", "--compressed", "-m", "25", "-A", USER_AGENT,
         "-H", "Accept-Language: zh-TW,en;q=0.8",
         "-o", str(out), "-w", "%{http_code}", url],
        capture_output=True, text=True,
    )
    status = result.stdout.strip() or "000"
    if status == "000" and result.stderr.strip():
        print(f"fetch_pages: {url}: {result.stderr.strip().splitlines()[0]}", file=sys.stderr)
    return status


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    list_file, out_dir = Path(argv[1]), Path(argv[2])
    if not list_file.is_file():
        print(f"fetch_pages: 連結清單檔不存在 {list_file}", file=sys.stderr)
        return 2
    if not REGISTRY.is_file():
        print(f"fetch_pages: 讀不到站點登記表 {REGISTRY}", file=sys.stderr)
        return 2
    routes = load_registry(REGISTRY.read_text(encoding="utf-8"))
    if not routes:
        print(f"fetch_pages: 站點登記表沒有任何一列 {REGISTRY}", file=sys.stderr)
        return 2
    urls = [
        line.strip()
        for line in list_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not urls:
        print(f"fetch_pages: 連結清單是空的 {list_file}", file=sys.stderr)
        return 2
    if any(route_for(u, routes) == "curl" for u in urls) and shutil.which("curl") is None:
        print("fetch_pages: 環境裡找不到 curl", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    n_curl = n_browser = n_blocked = n_failed = 0
    last_request: dict[str, float] = {}
    for i, url in enumerate(urls, 1):
        route = route_for(url, routes)
        if route == "browser":
            n_browser += 1
            print(f"{i}|browser|-|-|{url}||")
            continue
        n_curl += 1
        host = (urlparse(url).hostname or "").lower()
        if host in last_request:
            wait = MIN_INTERVAL_SECONDS - (time.monotonic() - last_request[host])
            if wait > 0:
                time.sleep(wait)
        page_path = out_dir / f"{i}.html"
        status = fetch(url, page_path)
        last_request[host] = time.monotonic()
        page = decode_page(page_path.read_bytes()) if page_path.exists() else ""
        if status == "000":
            n_failed += 1
            page = ""
        blocked = is_blocked(status, page)
        n_blocked += blocked
        print(f"{i}|curl|{status}|{'yes' if blocked else 'no'}|{url}|"
              f"{extract_title(page)}|{','.join(extract_isbns(page))}")

    print(f"fetch_pages: {len(urls)} url(s), {n_curl} curl, {n_browser} browser, "
          f"{n_blocked} blocked, {n_failed} failed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
