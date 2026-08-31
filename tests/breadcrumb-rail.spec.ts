import { expect, Page, test } from '@playwright/test';

/**
 * 左側垂直分類色帶的回歸測試。
 *
 * 三件事在改版面時會靜默壞掉，都不會有 build error：
 *
 * 1. 色帶貼左緣往右長，深度越深越接近正文欄。斷點若沒有跟著層數走，深層頁面
 *    的色帶會在中等寬度壓到正文上 —— 兩者都還在、只是疊著，沒有任何報錯。
 * 2. 主題的 `nav a` 給每個連結 12px 右外距，色帶會被撐成分離的方塊而不是一條
 *    連續路徑。任何動到 nav 樣式的改動都可能把它加回來。
 * 3. 色帶離開視窗左緣，變成浮在頁面中間的卡片。
 */

const PATHS = {
  // 首頁 + backend + 02-cache-redis
  depth3: '/blog/backend/02-cache-redis/',
  // 首頁 + backend + 01-database + vendors + postgresql + hands-on（全站最深）
  depth6: '/blog/backend/01-database/vendors/postgresql/hands-on/',
};

const BLOCK_WIDTH = 48;

async function railState(page: Page) {
  return page.evaluate(() => {
    const rail = document.querySelector('.breadcrumb-rail') as HTMLElement | null;
    const main = document.querySelector('main') as HTMLElement | null;
    if (!rail || !main) return null;

    const railRect = rail.getBoundingClientRect();
    const mainRect = main.getBoundingClientRect();
    const blocks = [...rail.querySelectorAll('a')];

    return {
      display: window.getComputedStyle(rail).display,
      blockCount: Number(rail.getAttribute('data-blocks')),
      left: railRect.left,
      right: railRect.right,
      width: railRect.width,
      mainLeft: mainRect.left,
      // 相鄰色塊之間的縫隙，連續色帶應該全部是 0
      seams: blocks.slice(1).map((b, i) =>
        Math.round(b.getBoundingClientRect().left - blocks[i].getBoundingClientRect().right)
      ),
      labels: blocks.map((b) => b.textContent),
      writingMode: blocks[0] ? window.getComputedStyle(blocks[0]).writingMode : null,
    };
  });
}

test.describe('vertical breadcrumb rail', () => {
  test('文字直排、色塊相鄰無縫、末端不含文章標題', async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 900 });
    await page.goto(PATHS.depth6);

    const state = await railState(page);
    expect(state).not.toBeNull();
    expect(state!.display).toBe('flex');
    expect(state!.writingMode).toBe('vertical-rl');
    expect(state!.seams.every((s) => s === 0)).toBe(true);
    expect(state!.width).toBe(state!.blockCount * BLOCK_WIDTH);

    // 色帶只走到分類，文章標題（PostgreSQL Local Lab Quickstart 那一層）不進來
    expect(state!.labels[0]).toBe('首頁');
    expect(state!.labels[1]).toBe('Backend');
    expect(state!.labels).toHaveLength(state!.blockCount);
  });

  test('色帶貼齊視窗左緣、右緣不壓到正文', async ({ page }) => {
    for (const width of [1440, 1600, 1920]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(PATHS.depth6);

      const state = await railState(page);
      expect(state!.display).toBe('flex');
      // 定位錨在視窗左緣而不是正文欄：視窗變寬時色帶不動、只有間距拉開
      expect(state!.left, `@ ${width}`).toBe(0);
      expect(state!.right, `@ ${width} 壓到正文`).toBeLessThan(state!.mainLeft);
    }
  });

  test('視窗放不下時整條收起、不壓到正文', async ({ page }) => {
    // 門檻是 749 + 96n（n = 色塊數）取整到五十位，見 custom.css 的 media query 段
    const cases: Array<[string, number, boolean]> = [
      [PATHS.depth3, 1000, false],
      [PATHS.depth3, 1050, true],
      [PATHS.depth6, 1300, false],
      [PATHS.depth6, 1350, true],
    ];

    for (const [path, width, shouldShow] of cases) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(path);

      const state = await railState(page);
      if (!shouldShow) {
        expect(state!.display, `${path} @ ${width}`).toBe('none');
        continue;
      }
      expect(state!.display, `${path} @ ${width}`).toBe('flex');
      expect(state!.right, `${path} @ ${width} 壓到正文`).toBeLessThan(state!.mainLeft);
    }
  });

  test('首頁與搜尋頁不顯示色帶', async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 900 });
    for (const path of ['/blog/', '/blog/search/']) {
      await page.goto(path);
      await expect(page.locator('.breadcrumb-rail')).toHaveCount(0);
    }
  });
});
