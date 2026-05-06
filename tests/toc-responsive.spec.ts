import { expect, Page, test } from '@playwright/test';

const ARTICLE_PATH = '/blog/go/00-philosophy/simplicity/';

async function tocState(page: Page) {
  return page.evaluate(() => {
    const toc = document.querySelector('.toc-sidebar') as HTMLElement | null;
    const toggle = document.querySelector('.toc-toggle-btn') as HTMLElement | null;
    if (!toc || !toggle) return null;

    const tocStyle = window.getComputedStyle(toc);
    const toggleStyle = window.getComputedStyle(toggle);

    return {
      tocDisplay: tocStyle.display,
      tocOpacity: tocStyle.opacity,
      tocPointerEvents: tocStyle.pointerEvents,
      tocTransform: tocStyle.transform,
      toggleDisplay: toggleStyle.display,
      expanded: toggle.getAttribute('aria-expanded'),
    };
  });
}

test.describe('responsive TOC layout', () => {
  test('desktop keeps fixed sidebar visible without toggle', async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 900 });
    await page.goto(ARTICLE_PATH);

    const state = await tocState(page);
    expect(state).not.toBeNull();
    expect(state!.tocDisplay).not.toBe('none');
    expect(state!.tocOpacity).toBe('1');
    expect(state!.toggleDisplay).toBe('none');

    const articleBox = await page.locator('.article-content').boundingBox();
    const tocBox = await page.locator('.toc-sidebar').boundingBox();
    expect(articleBox).not.toBeNull();
    expect(tocBox).not.toBeNull();
    expect(articleBox!.x + articleBox!.width).toBeLessThanOrEqual(tocBox!.x);
  });

  test('laptop width uses collapsed right-side drawer', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(ARTICLE_PATH);

    let state = await tocState(page);
    expect(state).not.toBeNull();
    expect(state!.toggleDisplay).toBe('flex');
    expect(state!.expanded).toBe('false');
    expect(state!.tocOpacity).toBe('0');
    expect(state!.tocPointerEvents).toBe('none');

    await page.locator('#toc-toggle').click();
    await expect.poll(async () => tocState(page)).toMatchObject({
      expanded: 'true',
      tocOpacity: '1',
      tocPointerEvents: 'auto',
    });

    await page.keyboard.press('Escape');
    await expect.poll(async () => tocState(page)).toMatchObject({
      expanded: 'false',
      tocOpacity: '0',
      tocPointerEvents: 'none',
    });
  });

  test('mobile hides TOC and toggle', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(ARTICLE_PATH);

    const state = await tocState(page);
    expect(state).not.toBeNull();
    expect(state!.tocDisplay).toBe('none');
    expect(state!.toggleDisplay).toBe('none');
  });
});
