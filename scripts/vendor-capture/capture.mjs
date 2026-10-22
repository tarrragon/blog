#!/usr/bin/env node
// 在本機用 Playwright 操作 monitoring/vendors 的實測頁，記錄各家追蹤碼實際送出的請求與寫下的 cookie。
//
// 結果會隨 vendor 改版而過期，所以每一份結果都記下擷取時間、瀏覽器版本與 vendor script 的版本資訊；
// 寫進文章時要連同這幾項一起寫。
//
// 用法：
//   node scripts/vendor-capture/capture.mjs --vendor meta-pixel --id <Pixel ID>
//   node scripts/vendor-capture/capture.mjs --vendor gtm --id <GTM-容器ID>
// 選項：
//   --url <實測頁網址>   預設是正式站的實測頁；改測本機 build 時傳 http://localhost:4173/blog/...
//   --out <目錄>         結果 JSON 的輸出目錄，預設 scripts/vendor-capture/results
// 環境變數：
//   PW_CHROMIUM_PATH     指定 Chromium 執行檔（瀏覽器版本與 @playwright/test 不符時用）
//
// 執行環境要能連到 connect.facebook.net、facebook.com、googletagmanager.com 等網域；
// 連不到時 script 會載入失敗，結果檔照樣產生，可從 steps 與 requests 看出是哪一個請求被擋。

import { chromium } from '@playwright/test';
import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const LAB_PAGES = {
  'meta-pixel': 'https://tarrragon.github.io/blog/monitoring/vendors/meta-pixel-lab/',
  gtm: 'https://tarrragon.github.io/blog/monitoring/vendors/google-tag-manager-lab/',
};
const COOKIE_PREFIXES = ['_fbp', '_fbc', '_ga', '_gid', '_gcl'];
const KEPT_RESPONSE_HEADERS = ['content-type', 'last-modified', 'etag', 'date', 'cache-control'];
// vendor script 本體：gtm.js 的回應不帶 last-modified 與 etag，改版要靠本體的長度與雜湊比對
const VENDOR_SCRIPT_PATHS = ['/en_US/fbevents.js', '/gtm.js', '/gtag/js'];

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 2) args[argv[i].replace(/^--/, '')] = argv[i + 1];
  return args;
}

const args = parseArgs(process.argv.slice(2));
if (!LAB_PAGES[args.vendor] || !args.id) {
  console.error('usage: capture.mjs --vendor meta-pixel|gtm --id <ID> [--url <lab page>] [--out <dir>]');
  process.exit(2);
}
const labUrl = args.url || LAB_PAGES[args.vendor];
const outDir = args.out || 'scripts/vendor-capture/results';

const browser = await chromium.launch(
  process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {},
);
const context = await browser.newContext();
const page = await context.newPage();
const labOrigin = new URL(labUrl).origin;
const startedAt = Date.now();
const steps = [];
const requests = [];

// 只記跨網域的請求：同網域的是實測頁自己的 HTML、CSS 與圖片
page.on('requestfinished', async (req) => {
  if (new URL(req.url()).origin === labOrigin) return;
  const res = await req.response();
  const headers = res ? await res.allHeaders() : {};
  const entry = describe(req, res ? res.status() : null, headers);
  if (res && VENDOR_SCRIPT_PATHS.includes(entry.path)) {
    const body = await res.body();
    entry.body = { bytes: body.length, sha256: createHash('sha256').update(body).digest('hex') };
  }
  requests.push(entry);
});
// GA4 的 g/collect 由 script 以 fetch 送出，伺服器回了 204 之後 Playwright 仍會把它記成 requestfailed（ERR_ABORTED）。
// 所以先從 response 事件記下已收到的回應，失敗事件只在真的沒有回應時才代表請求沒送達。
const responses = new Map();
page.on('response', (res) => responses.set(res.request(), res));
page.on('requestfailed', async (req) => {
  if (new URL(req.url()).origin === labOrigin) return;
  const res = responses.get(req);
  const headers = res ? await res.allHeaders() : {};
  requests.push({ ...describe(req, res ? res.status() : null, headers), failure: req.failure()?.errorText });
});

function describe(req, status, headers) {
  const url = new URL(req.url());
  const body = req.postData();
  return {
    atMs: Date.now() - startedAt,
    method: req.method(),
    resourceType: req.resourceType(),
    origin: url.origin,
    path: url.pathname,
    query: Object.fromEntries(url.searchParams),
    postData: body ? body.slice(0, 4000) : null,
    status,
    responseHeaders: Object.fromEntries(KEPT_RESPONSE_HEADERS.filter((h) => headers[h]).map((h) => [h, headers[h]])),
  };
}

async function step(label, fn) {
  await fn();
  await page.waitForTimeout(3000);   // 等第三方 script 送完請求、寫完 cookie
  steps.push({ atMs: Date.now() - startedAt, label, status: await page.locator('.vendor-lab-status').textContent() });
}

async function openAndLoad(url) {
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.locator('#vendor-lab-id').fill(args.id);
  await step('load', () => page.locator('[data-action="load"]').click());
}

if (args.vendor === 'meta-pixel') {
  await openAndLoad(labUrl);
  await step('view-content', () => page.locator('[data-action="view-content"]').click());
  await step('purchase', () => page.locator('[data-action="purchase"]').click());
  const withClick = new URL(labUrl);
  withClick.searchParams.set('fbclid', 'capture' + Date.now().toString(36));
  await openAndLoad(withClick.toString());
} else {
  await openAndLoad(labUrl);
  await step('push-purchase', () => page.locator('[data-action="push-purchase"]').click());
}

const vendorRuntime = await page.evaluate(() => ({
  fbqVersion: window.fbq ? window.fbq.version || null : null,
  gtmContainers: window.google_tag_manager ? Object.keys(window.google_tag_manager) : null,
  dataLayer: window.dataLayer ? JSON.parse(JSON.stringify(window.dataLayer)) : null,
}));
const cookies = (await context.cookies())
  .filter((c) => COOKIE_PREFIXES.some((p) => c.name.startsWith(p)))
  .map(({ name, value, domain, path, expires, httpOnly, secure, sameSite }) =>
    ({ name, value, domain, path, expires, httpOnly, secure, sameSite }));

const capturedAt = new Date(startedAt);
const result = {
  capturedAt: capturedAt.toISOString(),
  capturedAtTaipei: capturedAt.toLocaleString('sv-SE', { timeZone: 'Asia/Taipei' }),
  browser: browser.version(),
  userAgent: await page.evaluate(() => navigator.userAgent),
  vendor: args.vendor,
  id: args.id,
  labUrl,
  steps,
  vendorRuntime,
  cookies,
  requests,
};
await browser.close();

mkdirSync(outDir, { recursive: true });
const stamp = capturedAt.toISOString().slice(0, 16).replace(/[-:]/g, '');
const file = join(outDir, `${args.vendor}-${stamp}Z.json`);
writeFileSync(file, JSON.stringify(result, null, 2) + '\n');

console.log(`captured ${requests.length} cross-origin request(s), ${cookies.length} tracking cookie(s)`);
console.log(`time: ${result.capturedAt} (Asia/Taipei ${result.capturedAtTaipei}), browser ${result.browser}`);
for (const s of steps) console.log(`  step ${s.label}: ${s.status}`);
console.log(`written: ${file}`);
