---
title: "量終端機動畫程式的 CPU：用 pty 執行、認出 tsx 實際執行程式的程序、停掉之後檢查殘留、錄 profile 與數輸出量、用固定種子比較兩個版本，以及降頻之後 CPU 百分比的讀法"
date: 2026-11-17
description: "要量一個在終端機裡跑的 Node 動畫程式吃多少 CPU、改了之後省多少，而程式一放到背景或把輸出導到檔案就直接結束、量到的 CPU 接近 0、兩次結果對不上，或降了更新頻率、CPU 的降幅比頻率的降幅小時"
tags: ["work-log", "node", "tsx", "profiling", "效能", "量測", "terminal"]
slug: "terminal-animation-cpu-measurement"
---

2026-11-17 在一台 Apple M4 晶片的 Mac（型號識別碼 Mac16,10）、macOS 15.3、Node 24.4.1 上，為了決定先改哪裡，量開源專案 [terminal-sharks](https://github.com/tarrragon/terminal-sharks) 的終端機版：一支用 `tsx` 直接執行的 TypeScript 程式，每秒 60 次把鯊魚游動的畫面以 24-bit 色彩的 ANSI 跳脫碼寫到終端機。量的版本是[柵格化](/ux-design/knowledge-cards/rasterization/)（程式自己決定終端機每一格畫什麼）改寫之前的 commit `2f616b2` 與改寫之後的 `21e20a3`，兩個版本都預設帶著**魚群**：原作裡成群游動、會被鯊魚追逐的小魚，每一條魚每一幀都要模擬；之後的版本 `c74f1a9` 改成預設沒有魚群，要加 `SHARKS_FISH=on` 才有。`2f616b2` 起，終端機視窗失去焦點時降到每秒 15 次（為什麼降頻而不暫停，在〔[App 裡的裝飾性動畫](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕的〈重繪成本與動畫驅動器的排幀頻率〉）；量 60、30、15 次與錄 profile 時這一段還沒提交，工作樹是前一個版本加上量測用的暫時修改，終端機版的程式跟 `2f616b2` 只差焦點降頻那一段，而那一段在下文的 pty 裡收不到焦點的通知、不會觸發。量的人是在沒有終端機視窗的環境（一個自動化的 shell）裡操作。

這篇整理量這類程式時碰到的狀況與處理：程式在標準輸出不是終端機時直接結束，在沒有視窗的環境怎麼給它一個終端機；`tsx` 會起兩個 node 程序（作業系統裡各自有編號的 process；下文的「程式」指這支動畫程式本身），量到外層那一個時數字幾乎是 0；停掉程式之後有程序殘留，下一輪量到的是上一輪的程式；量的對象（程序的 CPU、CPU profile、送給終端機的輸出量）各自怎麼取、量到什麼；兩個版本各跑一次時場景是隨機的，數字的差異混著場景的差異；把更新頻率降到四分之一，CPU 只降了約三分之一，這個百分比要怎麼讀。終端機軟體自己解析輸出的 CPU 這次沒有量。下文的 CPU 百分比是 macOS `top` 的單核百分比（100% 等於一個核心全滿），依處理器型號與負載而變，換一台機器要自己重量。`script` 與 `top -l` 的寫法是 macOS 的，Linux 上 `script` 要寫成 `script -qc '<指令>' /dev/null`、取樣改用 `top -b -p <程序編號>`（這兩條沒有實跑）。

## 在沒有終端機視窗的環境用 pty 執行

這支程式啟動時檢查標準輸出是不是終端機（Node 的 `process.stdout.isTTY`），不是就印出錯誤並結束，所以不能直接在背景執行或把輸出導到檔案。macOS 的 `script` 指令會開一個 [PTY（pseudo-terminal，偽終端機）](/linux/dotfile/knowledge-cards/pty/)：作業系統提供的一對裝置，一端接著程式、讓程式以為自己接在終端機上，另一端由 `script` 讀寫。`script` 在裡面執行指定的指令，程式看到的標準輸出就是終端機。先照〔[瀏覽器 canvas 像素動畫的 CPU 量測與重畫上限](/ux-design/06-interaction-feedback/hands-on/canvas-ambient-frame-cap/)〕的第一節 clone 專案並 `npm install`，切到要量的版本，再執行：

```bash
cd terminal-sharks
git checkout 2f616b2        # 要量的版本
script -q /dev/null bash -c 'stty cols 240 rows 67; exec node_modules/.bin/tsx src/term.ts' > /dev/null < /dev/null &
```

`script` 的第一個引數是記錄檔，`/dev/null` 表示不記錄；`-q` 不印開始與結束的訊息。`stty cols 240 rows 67` 設定這個 pty 的大小，程式從 `process.stdout.columns` 與 `rows` 讀到這兩個值，用它們決定畫面有幾格；不設時 pty 的大小可能是 0，程式會退回自己的預設值 80 × 24。240 × 67 是這次挑的大小，換成自己要量的終端機大小。`exec` 讓 `bash` 把自己換成 `tsx`，少一層程序。`> /dev/null` 把 `script` 轉出來的畫面丟掉，`< /dev/null` 讓 `script` 不讀目前終端機的鍵盤輸入；這次就是用這兩個導向、在背景（最後的 `&`）跑的。在互動的終端機分頁裡沒有 `< /dev/null` 就放到背景時，`script` 會因為要調整終端機的設定而被暫停（從 shell 的工作控制推論，沒有實跑）。程式的錯誤訊息（例如 `npm install` 沒做、找不到 `tsx`）也一起被丟掉，所以啟動之後用〈認出 tsx 實際執行程式的那個程序〉的 `pgrep` 確認程式有在跑；要停的時候結束 `script` 這個程序（`kill <script 的程序編號>`），再照〈停掉程式之後檢查有沒有殘留的程序〉確認。

這個量法有兩個跟在終端機軟體的視窗裡執行不同的地方。輸出最後丟到 `/dev/null`，沒有任何終端機軟體在解析跳脫碼、畫字，所以量到的只有程式本身。程式在寫不進去時會跳過那一幀（Node 的 `writableNeedDrain` 是 `true` 時不寫），寫不寫得進去取決於 pty 的另一端讀得多快；這裡讀的是 `script`，它把讀到的直接丟掉，讀得比終端機軟體快，所以這一層的跳幀比在視窗裡少（推論，這次沒有計數）。另一次用 Python 的 `pty` 模組當讀取端時，讀取端慢了一點，每秒 60 次的程式實際每秒只送出 54 到 60 幀。

## 認出 tsx 實際執行程式的那個程序

`tsx` 執行一支 TypeScript 程式時有兩個 node 程序：外層的 `node …/tsx src/term.ts`，以及它起的、帶 `--import …/tsx/dist/loader.mjs` 參數的那一個，程式實際在帶 `loader.mjs` 的那個程序裡跑。照〈在沒有終端機視窗的環境用 pty 執行〉的方式啟動時，`pgrep -fl "src/term.ts"` 會列出三行，第一行是外層的 `script`（它的參數裡也有 `src/term.ts`），另外兩行是 `tsx` 的兩個 node：

```text
71196 script -q /dev/null bash -c stty cols 240 rows 67; exec node_modules/.bin/tsx src/term.ts
71197 node /…/node_modules/.bin/tsx src/term.ts
71200 /opt/homebrew/Cellar/node/24.4.1/bin/node --require /…/tsx/dist/preflight.cjs --import file:///…/tsx/dist/loader.mjs src/term.ts
```

同一次執行（240 × 67、每秒 15 次的設定）裡，量外層的 node 得到 1.9%，量帶 `loader.mjs` 的那一個得到 26.8%。所以取程序編號時用 `loader.mjs` 認：

```bash
pid=$(pgrep -f "loader.mjs .*term\.m?ts" | head -1)
```

`term\.m?ts` 同時對得上 `term.ts` 與〈用固定的種子比較兩個版本〉那一節的包裝程式 `seeded-term.mts`。

量 CPU 用 `top` 對這一個程序取樣，丟掉第一次（`top -l` 的第一次取樣是程序開始以來的平均），其餘取平均：

```bash
#!/bin/bash
# term-cpu.sh <取樣次數> <間隔秒>
n=${1:-8}; s=${2:-2}
pid=$(pgrep -f "loader.mjs .*term\.m?ts" | head -1)
[ -z "$pid" ] && { echo "no term.ts node process"; exit 1; }
top -l "$n" -s "$s" -stats pid,cpu -pid "$pid" 2>/dev/null |
awk -v pid="$pid" '/^Processes:/ {k++} k >= 2 && $1 == pid {sum += $2; m++}
  END { if (!m) { print "no samples"; exit 1 } printf "pid=%s samples=%d cpu=%.1f\n", pid, m, sum/m }'
```

```bash
bash term-cpu.sh 8 2      # 8 次取樣、每 2 秒一次，第 1 次丟掉，印出 7 次的平均
```

腳本印出量到的程序編號，〈停掉程式之後檢查有沒有殘留的程序〉用它認出量錯的程序。程式剛啟動時取樣可能比程序出現還早，腳本印 `no term.ts node process`；等一兩秒再跑一次，還是一樣時，程式多半沒有啟動成功，先回〈在沒有終端機視窗的環境用 pty 執行〉確認 `npm install` 與版本。

## 停掉程式之後檢查有沒有殘留的程序

連續量好幾個版本時，每一輪先停掉上一輪，再啟動下一輪。這次停掉的方式是結束外層的 `script`。比較有沒有魚群的那兩輪之間（在 `c74f1a9` 上，先量預設沒有魚群的一輪，再量 `SHARKS_FISH=on` 的一輪），停掉第一輪之後，`tsx` 的兩個 node 程序沒有跟著結束；第二輪啟動之後，`pgrep … | head -1` 取到的是編號較小的舊程序，量到的是第一輪的程式。發現的方式是兩輪印出的程序編號相同：

```text
pid=48643 samples=11 cpu=22.8      ← 沒有魚群的那一輪
pid=48643 samples=11 cpu=22.4      ← 以為是開了魚群的那一輪，編號卻一樣
```

用 `kill <程序編號>` 結束殘留的兩個 node 之後重量，開了魚群的那一輪是 38.3% 與 39.0%。這個殘留在大約十次停止裡出現一次，沒有找出它在什麼條件下發生。每一輪啟動之前先列一次：

```bash
pgrep -fl "term\.m?ts"
```

列出的只應該有這一輪要跑的那一組（`script` 一行加兩個 node）；量完之後比對腳本印的編號，跟上一輪相同就代表量錯了程序。

## 量的對象：程序的 CPU、CPU profile、送給終端機的輸出量

**程序的 CPU** 量的是這支程式整體用掉多少 CPU 時間。240 × 67、每秒 60 次時，`2f616b2`（柵格化改寫之前、有魚群）是 40% 到 43%。同一個設定、同一次執行連續量，最多差到 7 個百分點（`21e20a3` 的一次執行，六次量測從 32.6% 到 39.6%）：下文兩個條件的差距小於 7 個百分點時，寫成落在雜訊範圍內。

**CPU profile** 記錄時間落在哪些函式。Node 的 `--cpu-prof` 在程序結束時寫出一份 `.cpuprofile`，經由 `NODE_OPTIONS` 傳給 `tsx` 起的兩個 node：

```bash
NODE_OPTIONS="--cpu-prof --cpu-prof-dir=/tmp/prof" \
  script -q /dev/null bash -c 'stty cols 240 rows 67; exec node_modules/.bin/tsx src/term.ts' > /dev/null < /dev/null &
# 跑 20 秒之後，對帶 loader.mjs 的那個程序送 SIGTERM
kill -TERM <帶 loader.mjs 的程序編號>
```

`/tmp/prof` 換成自己要放檔案的目錄。profile 只在程序正常結束時寫出：這支程式收到 `SIGTERM` 時自己呼叫 `process.exit(0)`，所以用 `SIGTERM` 停；用 `SIGKILL` 停的話檔案不會產生。目錄裡會有三個檔案，檔名裡帶著程序編號：兩個是帶 `loader.mjs` 的程序寫的（檔名裡的 `.0.` 與 `.1.`，這次沒有查第二份屬於哪一個執行緒），一個是外層寫的；要讀的是帶 `loader.mjs` 那個程序編號、檔名裡是 `.0.` 的那一份。`.cpuprofile` 可以直接用 Chrome DevTools 的 Performance 面板或 speedscope 打開，看成[火焰圖](/backend/knowledge-cards/flame-graph/)；要一張依函式排好的表時，依函式加總 self time（花在函式本身、不含它呼叫的其他函式的時間）的 Python，存成 `self-time.py`，執行 `python3 self-time.py <.cpuprofile 檔的路徑>`；輸出裡的 `(idle)` 那一列就是主執行緒閒置的比例：

```python
import json, sys, collections
p = json.load(open(sys.argv[1]))
nodes = {n["id"]: n for n in p["nodes"]}
dt = collections.Counter()
for s, d in zip(p["samples"], p["timeDeltas"]):
    dt[s] += d
self_time = collections.Counter()
for i, t in dt.items():
    cf = nodes[i]["callFrame"]
    self_time[f"{cf['functionName'] or '(anon)'} {cf['url'].split('/')[-1]}"] += t
total = sum(dt.values())
for k, v in self_time.most_common(12):
    print(f"{v / total * 100:5.1f}% {k}")
```

這次的結果（`2f616b2` 的柵格化、每秒 60 次）：主執行緒的時間有 57% 是閒置，43% 在忙。忙碌的時間裡約七成在鯊魚的柵格化，也就是程式在 CPU 上把每條鯊魚的形狀逐格取樣、決定終端機每一格要畫什麼（`src/renderer.ts` 的 `rasterizeSharks` 連同它呼叫的函式佔全部時間的 29.2%，其中逐點取樣的 `sampleShark` 一個函式的 self time 就佔 24.8%；連同呼叫的函式一起算，要另外沿著 profile 的呼叫樹加總，上面的 Python 只算 self time）。模擬全部的魚與鯊魚約佔全部時間的 4%，也就是忙碌時間的約一成；組成輸出字串約 1.4%。這裡的柵格化是這支程式自己在 CPU 上的運算，格子是終端機的字元格；瀏覽器或 Flutter 交給 GPU 把圖層畫成像素的柵格化是同一類工作，跑在另一個處理器上，不出現在這支程式的 profile 裡。讀程式碼時判斷的「主要成本可能在模擬」是錯的，後來改的是柵格化（`21e20a3`）。

**送給終端機的輸出量**是終端機軟體每秒要解析的位元組數。這次暫時在程式寫出每一幀的地方（`src/term.ts` 的 `flush`）加計數，每 5 秒把幀數、空白的幀數與位元組數附加到一個檔案（這支程式用同步更新送出每一幀：一組開頭與結尾的跳脫碼包住整幀，終端機收齊之後才一次畫出，也就是 DEC 私有模式 2026；空白的幀指只有這組開頭、沒有任何格子變化的幀），量完拿掉，計數的程式沒有附。每秒 60 次時約 1.1 MB/s，30 次時約 0.67 MB/s，15 次時約 0.42 MB/s；三種頻率都沒有任何一幀是空的，代表每一幀都有格子在變。30 次與 15 次是量測時暫時把 `src/term.ts` 的 `const FPS = 60` 改成讀環境變數（`Number(process.env.TERM_FPS) || 60`）、啟動時給 `TERM_FPS=30` 或 `TERM_FPS=15` 得到的，量完改回；15 也是程式失去焦點時用的頻率，而在 pty 裡沒有視窗、收不到焦點的通知，量不到那個切換。終端機軟體解析這些跳脫碼、畫出字元的 CPU 隨輸出量增減，這次沒有量。

## 用固定的種子比較兩個版本

這支程式的魚群、鯊魚的路線都來自 `Math.random`，每次執行的場景不同：鯊魚靠得近、轉彎多的時候，柵格化的格子比較多。兩個版本各跑一次再比 CPU，差異裡混著場景的差異。這次比柵格化改寫前後的版本時，量的人先寫一支包裝程式，把 `Math.random` 換成固定種子的版本之後才載入程式：

```ts
// seeded-term.mts：固定 Math.random 的種子之後再載入 term.ts
let seed = 2024;
Math.random = () => {
  seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
await import("/path/to/terminal-sharks/src/term.ts");
```

`/path/to/terminal-sharks` 換成自己 clone 的位置。種子 `2024` 換成任何整數都可以，兩個版本要用同一個。這支包裝放在專案以外、沒有 `package.json` 的目錄；檔名用 `.mts`，是因為那裡沒有 `package.json`，`tsx` 會把 `.ts` 當成 CommonJS，而 CommonJS 不允許最上層的 `await`。執行時把 pty 指令裡的 `src/term.ts` 換成這個檔案的路徑。

固定種子固定的是起始狀態：魚群與鯊魚一開始的位置與方向兩次相同。之後每一幀推進多少時間取自實際經過的時間（`performance.now()`），兩次執行的計時器抖動不同，模擬抽亂數的時機跟著不同，場景跑一段時間之後就分開了。所以它把「一開始的場景就不一樣」這個差異拿掉，沒有讓兩次執行逐幀相同。要逐幀相同，還得把每一幀推進的時間固定（例如固定 1/60 秒），這要改程式，這次沒有做：比的是 CPU 用量，改用固定的推進時間之後，跳過的幀照樣推進，量到的就不是程式平常的行為。

兩個版本輪流跑，工作樹停在 `21e20a3`（改寫之後）：

```bash
git checkout 21e20a3
# 新版：照 pty 指令用 seeded-term.mts 跑，量完停掉
git show 2f616b2:src/renderer.ts > src/renderer.ts     # 換成改寫之前的柵格化
# 舊版：同樣跑一次，量完停掉
git checkout -- src/renderer.ts                         # 換回新版
```

每一次執行連續量兩次（`bash term-cpu.sh 16 2`，每次 15 個取樣）：舊版 42.1% 與 43.5%，新版 37.1% 與 36.7%。平均差約 6 個百分點，小於 7 個百分點的雜訊；柵格化本身變快了多少，另外由隔離出來的計時確認（〈降頻之後 CPU 百分比的讀法〉）。

## 降頻之後 CPU 百分比的讀法：60、30、15 次的量測與時脈的推論

把更新頻率從每秒 60 次降到 30 次、15 次（`2f616b2`、有魚群，用〈量的對象〉提到的 `TERM_FPS` 切換），CPU 是 40%–43%、33%–35%、25%–29%：更新次數降到四分之一，CPU 只降了約三分之一。15 次那一輪的 profile 顯示主執行緒 24.5% 的時間在忙，`sampleShark` 的 self time 是 13.6%；60 次時 `sampleShark` 的 self time 是 24.8%。次數少了四倍，這個函式的時間只少了不到一半，換算下來平均每一幀花在 `sampleShark` 的時間變長了。柵格化改寫那一次也有同樣的現象：把新舊兩份柵格化隔離出來，用一支 Node 腳本固定種子建一個模擬世界，每一幀依序交給兩份柵格化各算一次、各自計時（這支腳本沒有附；它同時逐格比對兩份的輸出，比對的做法在〔[效能最佳化的正確性要拿一份產生同樣畫面的參照實作逐格比](/report/optimization-equivalence-needs-a-reference-of-the-same-behavior/)〕），每一幀從約 4.9 ms 降到 1.9 ms；新版放回程式裡跑，profile 換算出每一幀約 3.4 ms，`top` 的 CPU 只從 42% 到 44% 降到約 37%。

一個符合這兩組數字的解釋是處理器的時脈：負載低的時候，作業系統讓處理器跑在較低的時脈或效率核心上，同樣的工作花比較多的時間，換算成百分比就偏高。這是推論，沒有驗證；macOS 上看得到時脈與能耗的 `powermetrics` 要用 `sudo` 執行，這次的環境沒有權限。同樣符合這些數字的還有幾個解釋：60、30、15 次那幾輪沒有固定種子，每一輪的場景不同，鯊魚靠得近時柵格化的格子多；兩幀相隔越久，CPU 的快取越冷；隔離計時是一個連續跑的迴圈，快取一直是熱的，跟程式裡隔 1/60 秒才跑一次的條件本來就不同。這次沒有把它們分開。另外，CPU 百分比也不等於耗電：低時脈下每單位工作的耗電比較少，百分比降的幅度可能低估了省下的電。所以這類百分比只能拿來比大小：降了頻率或改了算法之後百分比變小，代表確實省了；降的幅度不能當成工作量降的比例，要知道某一段程式快了多少，得把那一段隔離出來單獨計時，或在固定時脈、固定負載的條件下比。

## 量終端機動畫程式時的判斷標準

- **程式在標準輸出不是終端機時直接結束**：`script` 給它一個 pty，量到的是程式本身；終端機軟體不在量測裡，程式的跳幀也比在視窗裡少，因為讀取端換成了只丟資料的 `script`。量終端機軟體自己的成本，要在終端機軟體的視窗裡跑。
- **用 `tsx`、`ts-node` 這類包裝執行**：同一支程式有不只一個程序，包裝那一層幾乎不做事，量到它時數字接近 0，看起來像程式很省；實際執行程式的是帶 loader 參數的那一個。
- **連續量好幾輪**：停掉上一輪之後程序可能殘留，下一輪依名稱取程序編號時會取到舊的那一個，量到的是上一輪的程式；兩輪印出的編號相同就是這個情形。
- **場景有隨機成分**：兩個版本各跑一次的差異混著場景的差異；固定種子拿掉起始場景的差異，計時器的抖動仍然讓場景逐漸分開，所以差距小於同一個設定的雜訊時，這個量法分不出兩個版本，要靠把那一段隔離出來的計時。
- **降低頻率或改了算法**：CPU 百分比變小代表確實省了，降的幅度可能小於工作量降的幅度（這次的推論是時脈隨負載改變，也可能是場景與快取的差異），所以百分比只能比大小。讀取端慢（經過 SSH、終端機軟體來不及畫）時，程式設定的頻率不等於實際送出的幀數，比較兩種頻率要拿實際送出的幀數當分母，不拿設定值。
- **中間隔著多工器或內建在編輯器裡的終端機**（tmux、VS Code 的終端機）：程式到畫面之間多了幾個程序（tmux 的 server、編輯器的 renderer 與 GPU 程序），各自要量，量程式本身只看到其中一層。
- **決定先改哪裡**：讀程式碼估的熱點可能落在錯的地方；這次忙碌時間裡模擬約佔一成、柵格化約佔七成，profile 一錄就看得出來。先量再排順序的方法，寫在〔[效能最佳化的先後順序要等量完再排](/report/optimization-order-comes-from-removal-measurements/)〕。
