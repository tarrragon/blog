---
title: "瀏覽器 canvas 像素動畫的 CPU 量測與重畫上限：requestAnimationFrame 迴圈設成每秒 30 次、快速物體出現時全速，以及拿掉天空與合併繪製星星的量測"
date: 2026-11-17
description: "用 requestAnimationFrame 畫一個一直在動的 canvas 像素場景，CPU 用量偏高、想知道限制重畫次數能省多少、該先改哪一段時讀：為什麼每幀的 JS 時間看不到大部分的成本，以及用暫時拿掉某一段繪製的方式量出各段的上限。"
weight: 1
tags: ["ux-design", "hands-on", "animation", "performance", "canvas", "requestAnimationFrame"]
slug: "canvas-ambient-frame-cap"
---

2026-11-17 在一台 Apple M4 晶片的 Mac（型號識別碼 Mac16,10）、macOS 15.3 上，用 Chrome 157 量一個瀏覽器 canvas 上的像素夜空動畫；這台 Mac 接了兩台螢幕，量測的視窗開在 144 Hz 的那一台（另一台是 60 Hz，沒有量）。場景是開源專案 [terminal-sharks](https://github.com/tarrragon/terminal-sharks) 的「宇宙」場景（TypeScript、Vite），畫面上有漸層天空、捲動的星雲、會閃爍的星星（數量照畫面面積算，1920 × 1080 時約一千一百顆，含銀河帶與星團）、行星、偶爾劃過的流星與幾個像素角色，全部位置都對齊整數的像素單位。量測時用 Playwright 驅動 Chrome，CPU 用 macOS 的 `top` 取樣。

這篇記錄怎麼量這個場景的成本、怎麼決定先改哪裡，以及改完之後的數字。內容依序是：取得專案的三個版本與啟動開發伺服器；在頁面裡量每一幀的 JavaScript 時間與繪圖呼叫數，以及這個數字為什麼看不到大部分的成本；用 `top` 加總 Chrome 各程序的 CPU；在頁面裡模擬「每秒最多畫 30 次」量它能省多少；把上限寫進動畫迴圈，並在流星飛過時解除；用暫時拿掉的方式量天空與星星各自佔多少；把星星改成依顏色與亮度合併繪製。這個場景為什麼可以降到每秒 30 次、「一直在動的裝飾性動畫」的重繪成本怎麼想，寫在〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕；決定先改哪裡的方法，寫在〔[效能最佳化的先後順序要等量完再排](/report/optimization-order-comes-from-removal-measurements/)〕。60 Hz 的螢幕、Windows 與手機、GPU 本身的工作量、觀看測試與背景分頁這次沒有量，各自缺了什麼寫在最後一節。

## 取得 terminal-sharks 的三個版本並啟動 Vite 開發伺服器

這次量了三個版本。改之前是 commit `22fe92d`；改過的版本是 `1e16260`，同一個 commit 加了重畫上限與星星合併繪製。中間「只加了重畫上限、星星還沒合併」的版本沒有單獨的 commit，量的時候是工作樹的狀態；要重做，在 `1e16260` 上把 `src/space/sky.ts` 換回改之前的版本（`1e16260` 對這個檔案只改了星星的繪製）。

```bash
git clone https://github.com/tarrragon/terminal-sharks.git
cd terminal-sharks
git checkout 22fe92d                                  # 改之前
# git checkout 1e16260                                # 重畫上限加星星合併
# git checkout 1e16260 && git show 22fe92d:src/space/sky.ts > src/space/sky.ts   # 只有重畫上限
npm install
node_modules/.bin/vite --port 5179 --strictPort
```

三行 `git checkout` 一次只用一行，換版本之前先用 `git checkout -- src/space/sky.ts` 把換掉的檔案還原。`--port 5179` 是這次挑的埠號，換成任何沒被佔用的埠都可以，下文網址裡的 `5179` 跟著換；`--strictPort` 讓埠被佔用時直接報錯，而不是自己換一個埠、讓後面的網址連到別的地方。啟動指令寫成 `node_modules/.bin/vite`，不寫 `npx vite`：這次第一次跑 `npx vite` 時本地還沒裝套件，`npx` 開始下載另一個主版本的 vite（8.x），而專案用的是 6.x，所以先 `npm install` 再用本地的那一份。這台機器上的 npm（11.5.2）跑 `npm install` 會改寫 `package-lock.json` 裡各平台套件的 `libc` 欄位，只是 npm 版本間的格式差異，量測不受影響；不打算提交時，用 `git checkout -- package-lock.json` 還原。

`vite` 會一直在前景跑，這個終端機分頁保持開著，下文的指令在另一個分頁執行。宇宙場景的網址是 `http://localhost:5179/?scene=space`。

## 量每一幀的 JavaScript 時間與繪圖呼叫數

第一個量法是在頁面裡把 `requestAnimationFrame` 包一層：每一次回呼前後各記一次時間，得到這一幀的 JavaScript 花了多久；同時數 `CanvasRenderingContext2D` 的 `fillRect`、`drawImage`、`createLinearGradient` 被呼叫幾次。下面這段是在 Playwright 的 `page` 上執行的程式。這次經由 Playwright 的 MCP 伺服器的 `browser_run_code_unsafe` 執行，它開的是有視窗的 Google Chrome，視窗要拖到要量的那一台螢幕上；寫成獨立的 Playwright 腳本時，要自己用 `chromium.launch({ headless: false, channel: 'chrome' })` 開瀏覽器、用 `newPage()` 取得 `page`，那一種沒有實跑。沒有視窗的 headless 模式不跟著實體螢幕刷新，量不到這一節要的數字。

```js
async (page) => {
  const out = {};
  for (const [w, h] of [[1920, 1080], [3840, 2160]]) {
    await page.setViewportSize({ width: w, height: h });
    await page.goto('http://localhost:5179/?scene=space');
    await page.waitForTimeout(2000);
    out[`${w}x${h}`] = await page.evaluate(() => new Promise((res) => {
      const P = CanvasRenderingContext2D.prototype;
      const calls = { fillRect: 0, drawImage: 0, createLinearGradient: 0 };
      for (const k of Object.keys(calls)) {
        const o = P[k];
        P[k] = function (...a) { calls[k]++; return o.apply(this, a); };
      }
      const raf = window.requestAnimationFrame.bind(window);
      const js = [], gaps = [];
      let last = 0, n = 0;
      window.requestAnimationFrame = (cb) => raf((t) => {
        if (last) gaps.push(t - last);
        last = t;
        const s = performance.now();
        cb(t);
        js.push(performance.now() - s);
        if (++n === 300) {
          const sorted = (a) => a.slice().sort((x, y) => x - y);
          const med = (a) => sorted(a)[a.length >> 1];
          const p95 = (a) => sorted(a)[Math.floor(a.length * 0.95)];
          res({ dpr: devicePixelRatio, jsMed: med(js), jsP95: p95(js), gapMed: med(gaps),
                perFrame: Object.fromEntries(Object.entries(calls).map(([k, v]) => [k, v / 300])) });
        }
      });
    }));
  }
  return out;
}
```

`setViewportSize` 設的是頁面的 CSS 尺寸。回傳的 `dpr` 是 `devicePixelRatio`，這次的 Playwright 視窗是 1，所以 3840 × 2160 的頁面就是 3840 × 2160 個畫布像素，比這台 144 Hz 螢幕的 1440 × 2560 還大；Chrome 照樣畫完整個畫布。自己量到的 `dpr` 是 2 時，畫布像素是 4 倍，CPU 會比這次高。包裝在頁面載入 2 秒之後才裝上：場景自己的迴圈每一幀都重新呼叫 `requestAnimationFrame`，換掉之後的下一幀起就走進包裝。`gaps` 記的是相鄰兩次回呼的時間差，`gapMed` 約等於 1000 除以螢幕的更新率（144 Hz 是 6.9 ms，60 Hz 是 16.7 ms），可以用它確認視窗在哪一台螢幕上。包裝裝上之後一直留在頁面裡，下一節量 CPU 時要重新載入頁面，不沿用這個分頁。

量到的值（各 300 幀）：

| 頁面尺寸    | 每幀 JS 時間（中位數 / p95） | 回呼間隔中位數 | 每幀 `fillRect` | 每幀 `drawImage` |
| ----------- | ---------------------------- | -------------- | --------------- | ---------------- |
| 1920 × 1080 | 0.70 / 1.20 ms               | 6.90 ms        | 1,157           | 11               |
| 3840 × 2160 | 1.00 / 1.30 ms               | 6.90 ms        | 4,508           | 13               |

回呼間隔 6.9 ms 就是 144 Hz 的一個刷新週期：`requestAnimationFrame` 的預設行為是螢幕每刷新一次就呼叫一次，這個場景的回呼每一次都把整個場景畫一遍，所以每秒畫 144 次。這個預設服務的情境是要平滑的動畫，每一次刷新都算出新的位置（從機制推論；MDN 的〈Window: requestAnimationFrame() method〉寫回呼的次數通常跟螢幕的更新率相符，沒有寫這個預設的用意。[VSync](/ux-design/knowledge-cards/vsync/) 卡寫了各平台的同一套機制）。

每幀的 JavaScript 只花 0.7 到 1.0 ms，離 6.9 ms 的幀預算很遠。只看這個數字會判定這個場景沒有什麼好改；〈用 top 加總 Chrome 各程序的 CPU〉量的結果顯示成本落在別處。JS 時間量到的是回呼裡下達繪圖指令的時間，指令交給 GPU 程序之後的合成與柵格化不在這段時間裡。

## 用 top 加總 Chrome 各程序的 CPU

Chrome 把一個分頁的工作分給好幾個程序：renderer 程序跑頁面的 JavaScript 與繪圖指令，GPU 程序執行柵格化與合成。所以量一個分頁的成本要把這些程序加起來。這次用一支腳本跑 `top`，丟掉第一次取樣（`top -l` 的第一次是開機以來的平均），其餘取平均，依程序類型分開印：

```bash
#!/bin/bash
# chrome-cpu.sh <取樣次數> <間隔秒>：加總 Google Chrome 各程序的 %CPU，分 GPU、Renderer、其他三類
n=${1:-6}; s=${2:-2}
pids=$(pgrep -f "Google Chrome" | tr '\n' ' ')
top -l "$n" -s "$s" -stats pid,cpu $(for p in $pids; do printf -- '-pid %s ' "$p"; done) 2>/dev/null |
awk -v gpu="$(pgrep -f 'Chrome Helper \(Aperitif GPU\)' | tr '\n' ',')" \
    -v ren="$(pgrep -f 'Chrome Helper \(Aperitif Renderer\)' | tr '\n' ',')" '
  /^Processes:/ { sample++ }
  sample >= 2 && $1 ~ /^[0-9]+$/ {
    k = (index("," gpu, "," $1 ",") ? "gpu" : (index("," ren, "," $1 ",") ? "renderer" : "other"))
    sum[k] += $2; total += $2
  }
  END {
    m = sample - 1; if (m < 1) { print "no samples"; exit 1 }
    printf "samples=%d gpu=%.1f renderer=%.1f other=%.1f total=%.1f\n", m, sum["gpu"]/m, sum["renderer"]/m, sum["other"]/m, total/m
  }'
```

腳本裡的 `Google Chrome` 與 `Aperitif` 是這台機器上 Playwright 啟動的 Chrome 主程序與輔助程序的名稱片段；在自己的機器上先跑 `ps -axo pid,pcpu,comm | grep -i chrom` 看實際的名稱，三個 `pgrep` 的樣式都照著換（用 Playwright 內建的 Chromium 時，主程序叫 `Chromium`）。第一個 `pgrep` 一個程序都沒抓到時，`top` 沒有帶任何 `-pid`，量的是整台機器的全部程序，腳本不會報錯，印出的 `total` 會大得不合理。這支腳本加總的是名稱含 `Google Chrome` 的全部程序，自己平常開著的 Chrome 也會算進去；量之前關掉其他 Chrome 視窗，或先量一次空白頁當底數。

```bash
bash chrome-cpu.sh 8 2      # 8 次取樣、每 2 秒一次，第 1 次丟掉，印出 7 次的平均
```

量測的順序是：Playwright 的分頁開 `about:blank` 量一次底數；再用 `setViewportSize` 設好頁面尺寸、`goto` 場景網址重新載入（不帶量 JS 時間時裝上的包裝）、等 2 秒，連跑兩次腳本。下文的「一次量測」指跑一次腳本得到的 7 個取樣的平均，表裡斜線兩側是兩次量測。

| 條件（改之前，`22fe92d`） | GPU         | Renderer    | 合計        |
| ------------------------- | ----------- | ----------- | ----------- |
| 空白頁                    | 0.0         | 0.2         | 0.2         |
| 場景，1920 × 1080         | 29.2 / 33.5 | 16.0 / 19.2 | 45.3 / 52.9 |
| 場景，3840 × 2160         | 39.8 / 37.9 | 25.3 / 23.8 | 65.1 / 61.7 |

空白頁是 0.2%，代表量法本身的底數接近 0，場景的數字都是場景造成的。合計裡約六成在 GPU 程序，這一段 JS 計時完全看不到。同一個設定的兩次量測（1920 × 1080 的 45.3 與 52.9）差到約 8 個百分點，這是這個量法的雜訊：下文兩個條件的差距小於 8 個百分點時，寫成落在雜訊範圍內，不當成確定的節省。這些數字依機器、螢幕更新率、Chrome 版本與場景的隨機內容而變，換一台機器要自己重量。

## 模擬「每秒最多畫 30 次」能省多少

這個場景的位置都對齊整數的像素單位，大部分物體每秒移動 10 到 45 個 CSS 像素（小行星、塵埃、角色），彗星在 1920 寬的畫面上每秒約 70 到 110 像素（它用 20 到 30 秒走完畫面寬度加上尾巴長度，畫面越寬越快）：每秒畫 30 次時，這些物體兩次重畫之間只移動幾個像素以內；從移動距離推論，畫面跟每秒 144 次看不出差別。要知道把重畫頻率降下來能省多少，先不改程式，在頁面載入之前把 `requestAnimationFrame` 換成「間隔不到 1/30 秒就直接等下一次」的版本：

```js
async (page) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.addInitScript(() => {
    const raf = window.requestAnimationFrame.bind(window);
    let last = 0;
    window.requestAnimationFrame = (cb) => {
      const tick = (t) => {
        if (t - last >= 1000 / 30 - 2) { last = t; cb(t); } else raf(tick);
      };
      return raf(tick);
    };
  });
  await page.goto('http://localhost:5179/?scene=space');
}
```

`addInitScript` 讓這段在頁面自己的程式之前執行，場景一開始拿到的就是包裝過的版本。它對同一個 `page` 之後的每一次載入都有效，量完要關掉這個分頁再量別的條件。判斷式裡的 `- 2` 是 2 ms 的容許誤差，理由跟實作迴圈裡的 `0.002` 相同，寫在〈在動畫迴圈加上重畫上限，流星飛過時解除〉的程式碼之後。

1920 × 1080 下，CPU 合計從改之前的 45.3 / 52.9 降到 16.6 / 16.3，其中 GPU 程序從 29.2 / 33.5 降到 9.1 / 9.1：重畫頻率降到約五分之一，CPU 合計少了約三分之二。

## 在動畫迴圈加上重畫上限，流星飛過時解除

改法分兩處。場景提供「這一刻兩次重畫之間至少隔多久」，迴圈每次被叫醒時先比對經過的時間，不到就直接等下一次刷新。下面是改過的版本 `1e16260` 的 `src/web.ts` 迴圈：

```ts
let last = performance.now();
function frame(now: number) {
  requestAnimationFrame(frame);
  const elapsed = (now - last) / 1000;
  if (elapsed < (scene.frameInterval?.() ?? 0) - 0.002) return;
  const dt = Math.min(0.1, elapsed);
  last = now;
  scene.step(dt);
  scene.render(dt);
}
requestAnimationFrame(frame);
```

`requestAnimationFrame(frame)` 移到最前面，跳過的那幾次也會排好下一次回呼。判斷式裡的 `0.002`（2 ms）是容許的誤差：刷新的時間戳會在刷新週期附近跳動，60 Hz 的螢幕每兩次刷新剛好是 1/30 秒，沒有這個容許時，略短於 1/30 秒的那一次會被跳過，每秒 30 次變成 20 次（從刷新週期推算，這次沒有在 60 Hz 的螢幕上實跑）。`dt` 用實際經過的時間，模擬的速度不受重畫頻率影響；`Math.min(0.1, …)` 把一次推進的時間限制在 0.1 秒以內，分頁從背景回來、兩次回呼相隔好幾秒時，物體不會一次跳過一大段（這一行是改之前就有的）。

這一步也可以換成計時器：用 `setInterval` 每 1/30 秒畫一次，不經過 `requestAnimationFrame`。計時器的回呼不對齊螢幕的刷新，畫好的一幀要等到下一次刷新才顯示，每一幀的等待時間不一樣；分頁切到背景時，瀏覽器停掉 `requestAnimationFrame`，計時器只被降頻、照樣在畫（各平台的動畫驅動器在背景時怎麼表現，整理在〔[App 裡的裝飾性動畫](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕的〈重繪成本與動畫驅動器的排幀頻率〉）。所以這次留在 `requestAnimationFrame` 裡、用經過的時間決定畫不畫，計時器的寫法沒有實跑比較。

場景提供間隔的那一段在 `src/space/scene.ts`：

```ts
const AMBIENT_FPS = 30;

frameInterval() {
  return this.sky.meteor ? 0 : 1 / AMBIENT_FPS;
}
```

`AMBIENT_FPS` 的 30 是從物體的移動距離推定的值，沒有比較 24、36、48 這類其他值。144 不是 30 的整數倍：門檻是 1/30 秒減 2 ms，約 31.3 ms，144 Hz 上 4 次刷新是 27.8 ms、不到門檻，5 次是 34.7 ms，所以每 5 次刷新畫一次，約每秒 29 次（從刷新週期推算，跟下面量到的每秒 28 到 30 次相符），不會在每 4 次與每 5 次之間交替。流星每秒移動 700 到 1000 個像素，每秒畫 30 次時兩次重畫之間跳 23 到 33 個像素，看得出一格一格地跳（從移動距離推論），所以流星在畫面上時回傳 0，迴圈回到每次刷新都畫：平常照固定的低頻節奏重畫，快速物體出現的那一段時間照螢幕的更新率。

確認重畫頻率照設計切換：每一次重畫呼叫一次 `createLinearGradient`（天空的漸層），所以數這個呼叫每秒幾次，就是每秒重畫幾次。數的程式（1920 × 1080，連數 25 秒）：

```js
async (page) => {
  await page.goto('http://localhost:5179/?scene=space');
  await page.waitForTimeout(1500);
  return await page.evaluate(() => new Promise((res) => {
    const P = CanvasRenderingContext2D.prototype;
    const o = P.createLinearGradient;
    let n = 0;
    P.createLinearGradient = function (...a) { n++; return o.apply(this, a); };
    const per = [];
    const id = setInterval(() => {
      per.push(n); n = 0;
      if (per.length === 25) { clearInterval(id); res(per.join(' ')); }
    }, 1000);
  }));
}
```

```text
29 28 29 29 29 29 29 28 29 29 29 85 144 53 29 29 29 28 29 29 29 29 28 29 30
```

平常每秒 28 到 30 次，中間有一顆流星飛過，跨了三個一秒的計數區間（85、144、53），飛過之後回到 29。

| 頁面尺寸    | 改之前（合計 CPU） | 加上重畫上限（含流星） |
| ----------- | ------------------ | ---------------------- |
| 1920 × 1080 | 45.3 / 52.9        | 21.8 / 22.1            |
| 3840 × 2160 | 65.1 / 61.7        | 31.4 / 32.2            |

1920 × 1080 下，實作版本的 21.8 / 22.1 比模擬時的 16.6 / 16.3 高約 5.5 個百分點；流星飛過時全速重畫是其中一個成因，各成因各佔多少沒有拆開量。

## 用暫時拿掉的方式量天空與星星各自佔多少

加上重畫上限之後，剩下的成本落在哪一段，用「暫時拿掉」來量：把一段繪製關掉（畫面錯了也沒關係），量一次，差額就是改這一段最多能省的量。這一節量的是「只有重畫上限」的版本（`1e16260` 加上改之前的 `src/space/sky.ts`）。在 `src/space/sky.ts` 的 `renderBack` 裡，把畫天空與畫星星的兩行各包一個只供量測的開關（中間畫星雲的那一行不動），頁面載入之後在主控台把 `globalThis.__noSky` 或 `globalThis.__noStars` 設成 `true`；用 Playwright 時，用 `page.evaluate(() => { globalThis.__noSky = true; })` 代替主控台：

```ts
if (!(globalThis as any).__noSky) this.drawSky(ctx);
this.drawNebula(ctx);
if (!(globalThis as any).__noStars) this.drawStars(ctx);
```

量完把包了開關的兩行改回 `this.drawSky(ctx);` 與 `this.drawStars(ctx);`。`__noSky` 拿掉的是天空的漸層：它每一次重畫都建立一個漸層、填滿整個畫面，讀程式碼時判斷它是最貴的一段。

| 條件（3840 × 2160，只有重畫上限） | 合計 CPU    |
| --------------------------------- | ----------- |
| 不拿掉                            | 31.4 / 32.2 |
| 拿掉天空漸層                      | 30.6 / 32.5 |
| 拿掉星星                          | 23.9 / 24.6 |

天空漸層拿掉之後 CPU 沒有變化，快取它省不到 CPU，所以沒有做。拿掉星星少了約 7 到 8 個百分點，在約 8 個百分點的雜訊邊緣，所以下一步只把星星當成值得試的候選。

## 星星依顏色與亮度合併繪製

原本每顆星星各設一次 `globalAlpha` 與 `fillStyle`、各畫一個到九個 `fillRect`（十字星的光芒）。改法是把亮度量化成 16 級，同一種顏色、同一級亮度的星星收進同一個 `Path2D`，最後每一組只設一次樣式、呼叫一次 `fill()`。下面是 `1e16260` 的 `src/space/sky.ts` 裡 `drawStars` 的骨架（`STAR_COLORS` 是同一個檔案定義的四種星星顏色）：

```ts
const steps = STAR_ALPHA_STEPS + 1;          // STAR_ALPHA_STEPS = 16
const paths = new Map<number, Path2D>();
const pathFor = (color: number, alpha: number) => {
  const step = Math.round(Math.min(1, alpha) * STAR_ALPHA_STEPS);
  if (step <= 0) return null;
  const key = color * steps + step;
  let path = paths.get(key);
  if (!path) paths.set(key, (path = new Path2D()));
  return path;
};
// ……每顆星星：pathFor(顏色索引, 這一刻的亮度)?.rect(x, y, 寬, 高)
for (const [key, path] of paths) {
  ctx.fillStyle = STAR_COLORS[Math.floor(key / steps)];
  ctx.globalAlpha = (key % steps) / STAR_ALPHA_STEPS;
  ctx.fill(path);
}
```

亮度的級數是畫質與合併程度的取捨：級數越多，閃爍越細，組數越多；16 級時每級差 1/16 的透明度；改完的截圖裡星星與十字星的光芒都看得到、沒有缺塊，跟改之前沒有並排比對，也沒有做觀看測試。同一條路徑裡互相重疊的方塊只填一次，原本是各畫一次、疊兩層透明度；星星彼此重疊的情形很少，沒有比對過差異。量化與合併都刻意改變了輸出，這種有損的改法沒辦法拿改之前的版本逐格比；要驗證，得先做一份同樣量化成 16 級、但不合併路徑的參照，逐格比合併的邏輯，量化本身的差異另外判（拆成兩段的理由在〔[效能最佳化的正確性要拿一份產生同樣畫面的參照實作逐格比](/report/optimization-equivalence-needs-a-reference-of-the-same-behavior/)〕），這次兩段都沒有做。

3840 × 2160 下每次重畫的 `fillRect` 從 4,508 次降到 12 次（剩下的 12 次是星星以外的繪製），改成約 64 次 `fill()`（照〈量每一幀的 JavaScript 時間與繪圖呼叫數〉的寫法另外包住 `fill` 數出來），這一項是確定的。CPU 合計四次量測是 25.2、28.7、24.2、27.6，平均 26.4，只加上重畫上限時的兩次是 31.4 與 32.2，平均 31.8：四次都比較低，平均差約 5 個百分點，小於約 8 個百分點的雜訊，要確定省下多少得多量幾次。1920 × 1080 下是 22.3 / 22.9，跟只加上重畫上限時的 21.8 / 22.1 沒有差別：星星的數量隨畫面面積增加（1920 × 1080 約一千一百顆，3840 × 2160 約四千三百顆），小畫面上星星本來就只佔一小部分。

## 三個版本的 CPU 對照：改之前、加上重畫上限、再加上星星合併繪製

| 頁面尺寸    | 改之前（`22fe92d`） | 加上重畫上限（工作樹） | 再加上星星合併繪製（`1e16260`） |
| ----------- | ------------------- | ---------------------- | ------------------------------- |
| 1920 × 1080 | 45.3 / 52.9         | 21.8 / 22.1            | 22.3 / 22.9                     |
| 3840 × 2160 | 65.1 / 61.7         | 31.4 / 32.2            | 25.2 / 28.7 / 24.2 / 27.6       |

數字是 Chrome 全部程序的 CPU 合計（%），每個數字是一次量測（7 個取樣）的平均，「加上重畫上限」那一欄是實作的版本，不是模擬。讀程式碼時估的成本由高到低是天空、星星、重畫頻率，量出來的節省正好倒過來：重畫頻率省下一半，星星合併繪製在大畫面上的差距小於雜訊（平均約 5 個百分點），天空省不到 CPU。

## 未量測的範圍：60 Hz 螢幕、Windows 與 WebView2、GPU 時間、觀看測試、背景分頁

- **60 Hz 的螢幕**：重畫上限在 60 Hz 上是每兩次刷新畫一次，省下的比例從機制推論會比 144 Hz 小，迴圈判斷式裡 2 ms 的時間戳容許也只是推算。這台 Mac 接的另一台螢幕就是 60 Hz，把 Playwright 的視窗拖過去，照〈用 top 加總 Chrome 各程序的 CPU〉重量就能補上。
- **Windows 與 WebView2**：這個場景另外被包成 Windows 的螢幕保護程式，用 Tauri 的 WebView2 執行，這次沒有量。
- **GPU 的時間**：CPU 取樣裡的 GPU 程序是那個程序花的 CPU，GPU 本身的工作量沒有量（Chrome DevTools 的 Performance 面板與 macOS 的 Instruments 量得到）。
- **觀看測試**：每秒 30 次看起來跟 144 次一樣，是從物體的移動速度推論的，沒有找人看過。
- **背景分頁**：分頁切到背景時 Chrome 會停掉 `requestAnimationFrame`，這次沒有量；canvas 捲出可視範圍時回呼照樣在跑，要停得自己用 `IntersectionObserver` 判斷，這次也沒有做。
- **沒試的改法**：用邏輯像素的解析度畫一張小 canvas、再用 CSS 的 `image-rendering: pixelated` 放大，每次重畫要填的像素少很多，這個場景的像素單位大於 1 個 CSS 像素時可能省得更多；只在對齊整數像素之後的狀態有改變時才重畫，星星的閃爍與星雲的捲動讓幾乎每一次都有改變，可能省不到；把繪製移到 `OffscreenCanvas` 加 worker，減輕的是主執行緒，這次的成本約六成在 GPU 程序，總量可能不變。三種都沒有實作。
