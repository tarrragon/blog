import { expect, test, type Page } from '@playwright/test';

/**
 * 知識卡自動連結的兩份實作要給出同樣的連結：部署的頁面由 `mdtools autolink-html`
 * （scripts/mdtools/internal/autolinkhtml）在建站後寫進 HTML，本機 `hugo server` 預覽由
 * assets/js/autolink.js 在瀏覽器端加。比對規則只列在 JS 的檔頭，兩份程式各自實作；
 * 一份改了而另一份沒跟上時，本機預覽看到的連結就跟部署的不同，而建站與兩邊各自的
 * 測試都不會失敗。所以這裡對同一批頁面各跑一次兩份實作，比對連結清單與正文文字。
 *
 * - Go 那一份：`make site` 建好的頁面本身（script 帶著 data-static，JS 不再連結）。
 * - JS 那一份：攔截同一頁的回應，拿掉 data-static、把 kc-auto 連結還原成文字，
 *   讓 JS 照本機預覽的路徑連結，等它在 script 加上 data-done 之後讀取。
 *
 * 頁面從 sitemap 依固定間隔抽出載入自動連結腳本的頁面，每次跑抽到同一批，
 * 涵蓋 sitemap 的各個區段。
 */

const SAMPLE = 30; // 比對的頁數：sitemap 排序後均分成這麼多段，每段取一頁
const SCAN = 40; // 每段從起點往後最多看幾個網址，找載入自動連結腳本的頁面

type Link = { href: string; text: string; title: string; linkTitle: string; linkDesc: string };

async function collect(page: Page): Promise<{ links: Link[]; text: string }> {
  return page.evaluate(() => {
    const body = document.querySelector('.article-body');
    const links = Array.from(document.querySelectorAll('.article-body a.kc-auto')).map((a) => ({
      href: a.getAttribute('href') ?? '',
      text: a.textContent ?? '',
      title: a.getAttribute('title') ?? '',
      linkTitle: a.getAttribute('data-link-title') ?? '',
      linkDesc: a.getAttribute('data-link-desc') ?? '',
    }));
    return { links, text: body?.textContent ?? '' };
  });
}

// Go 寫進去的連結：文字經 HTML 跳脫、裡面沒有其他標籤，所以可以用正規表示式還原成文字
const GO_LINK = /<a class="kc-auto" [^>]*>([^<]*)<\/a>/g;

test('JS 與 autolinkhtml 在同一批頁面上給出同樣的自動連結', async ({ page, request, baseURL }) => {
  test.setTimeout(300_000);

  const sitemap = await (await request.get('/blog/sitemap.xml')).text();
  const urls = Array.from(sitemap.matchAll(/<loc>https?:\/\/[^/]+(\/blog\/[^<]*)<\/loc>/g), (m) => m[1]).sort();
  expect(urls.length).toBeGreaterThan(0);

  const seg = Math.max(1, Math.floor(urls.length / SAMPLE));
  const pages: string[] = [];
  for (let start = 0; start < urls.length && pages.length < SAMPLE; start += seg) {
    for (let i = start; i < Math.min(start + SCAN, urls.length); i++) {
      const html = await (await request.get(urls[i])).text();
      if (html.includes('data-terms=') && html.includes('data-static')) {
        pages.push(urls[i]);
        break;
      }
    }
  }
  // 抽不到頁面時這個測試什麼都沒比，當成失敗
  expect(pages.length).toBeGreaterThanOrEqual(10);

  let compared = 0;
  for (const url of pages) {
    const goRes = await page.goto(url);
    expect(goRes?.ok(), url).toBeTruthy();
    const go = await collect(page);

    const full = new URL(url, baseURL).href;
    await page.route(full, async (route) => {
      const res = await route.fetch();
      const html = (await res.text()).replace('<script data-static ', '<script ').replace(GO_LINK, '$1');
      await route.fulfill({ response: res, body: html });
    });
    await page.goto(url);
    await page.locator('script[data-terms][data-done]').waitFor({ state: 'attached' });
    const js = await collect(page);
    await page.unroute(full);

    expect.soft(js.links, `連結清單不同：${url}`).toEqual(go.links);
    expect.soft(js.text, `正文文字不同：${url}`).toBe(go.text);
    compared += go.links.length;
  }
  // 抽到的頁面一處連結都沒有時，比對等於沒做
  expect(compared).toBeGreaterThan(0);
});
