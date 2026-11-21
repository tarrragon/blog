import { expect, test } from '@playwright/test';

/**
 * 知識卡自動連結寫在建好的 HTML 裡的回歸測試。
 *
 * 部署的網站在 `hugo --minify` 之後由 `mdtools autolink-html public` 把卡片名稱的連結
 * 寫進 HTML 與 RSS（Makefile 的 postbuild target，`make site` 與 .github/workflows/deploy.yml 都跑它），<script>
 * 帶著 data-static 時頁面腳本就不再連結。建站流程漏了這一步的話，build 不會報錯：
 * 有跑 JavaScript 的瀏覽器照樣顯示腳本加的連結，沒有連結的是不跑 JavaScript 的讀者看到的頁面，
 * 以及 RSS 閱讀器與爬蟲讀到的 HTML。所以這裡關掉 JavaScript 讀頁面與 RSS。
 */

// backend 的文章，正文寫到好幾張 backend 的卡（consumer、queue、broker）
const ARTICLE = '/blog/backend/00-service-selection/async-delivery-selection/';

test.describe('自動連結在建站時寫進 HTML', () => {
  test.use({ javaScriptEnabled: false });

  test('不跑 JavaScript 也看得到正文裡的自動連結', async ({ page }) => {
    // 文章搬走時在這裡失敗，不會被讀成自動連結壞了
    const res = await page.goto(ARTICLE);
    expect(res?.ok()).toBeTruthy();
    const links = page.locator('.article-body a.kc-auto');
    expect(await links.count()).toBeGreaterThan(0);
    await expect(links.first()).toHaveAttribute('href', /\/blog\/backend\/knowledge-cards\//);
    await expect(page.locator('script[data-terms][data-static]')).toHaveCount(1);
  });

  test('標題與程式碼裡不加自動連結', async ({ page }) => {
    await page.goto(ARTICLE);
    // 正對照：這一頁的 h2「durable queue 承擔可重試工作」寫到 queue 這張卡的名字，正文裡的 queue 有連結
    await expect(page.locator('.article-body h2', { hasText: /\bqueue\b/i }).first()).toBeVisible();
    await expect(page.locator('.article-body a.kc-auto', { hasText: /^queue$/i }).first()).toBeAttached();
    await expect(page.locator('.article-body :is(h1, h2, h3, h4, code, pre) a.kc-auto')).toHaveCount(0);
  });

  test('RSS 的全文帶著自動連結', async ({ request }) => {
    const res = await request.get('/blog/backend/00-service-selection/index.xml');
    expect(res.ok()).toBeTruthy();
    expect(await res.text()).toContain('class="kc-auto"');
  });
});
