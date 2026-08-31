import { expect, Page, test } from '@playwright/test';

/**
 * 左側垂直分類色帶的回歸測試。
 *
 * 整條是一欄：色塊由上往下堆疊、塊內文字 CJK 直排。四件事在改版面時會靜默
 * 壞掉，都不會有 build error：
 *
 * 1. 色塊被拉成統一高度。改一個 flex 值就會回去，而回去之後兩個字的分類會
 *    拿到跟十二個字一樣長的色塊，多出來的部分不對應任何內容。
 * 2. 主題的 `nav a` 給每個連結 12px 右外距，色塊會被推成分離的方塊而不是
 *    一條連續色帶。任何動到 nav 樣式的改動都可能把它加回來。
 * 3. 最深的路徑在矮視窗超出螢幕。壓縮靠兩個 flex 細節（min-height: 0、
 *    色塊不設 max-height），任一個被改掉都會讓色帶溢出或讓短標籤代長標籤
 *    讓步 —— 後者畫面上看起來仍然「有壓縮」，方向卻是反的。
 * 4. 色帶離開視窗左緣，變成浮在頁面中間的卡片。
 */

const PATHS = {
  // 首頁 + backend + 02-cache-redis
  depth3: '/blog/backend/02-cache-redis/',
  // 六層、標籤十來字，全站最長的色帶
  longest:
    '/blog/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/',
};

const RAIL_WIDTH = 48;

async function railState(page: Page) {
  return page.evaluate(() => {
    const rail = document.querySelector('.breadcrumb-rail') as HTMLElement | null;
    const main = document.querySelector('main') as HTMLElement | null;
    if (!rail || !main) return null;

    const railRect = rail.getBoundingClientRect();
    const mainRect = main.getBoundingClientRect();
    const blocks = [...rail.querySelectorAll('a')];
    const rects = blocks.map((b) => b.getBoundingClientRect());

    return {
      display: window.getComputedStyle(rail).display,
      blockCount: Number(rail.getAttribute('data-blocks')),
      left: railRect.left,
      right: railRect.right,
      top: railRect.top,
      bottom: railRect.bottom,
      width: railRect.width,
      height: railRect.height,
      viewportHeight: window.innerHeight,
      mainLeft: mainRect.left,
      // 一欄堆疊，接縫在上下方向；連續色帶應該全部是 0
      seams: rects.slice(1).map((r, i) => Math.round(r.top - rects[i].bottom)),
      widths: rects.map((r) => Math.round(r.width)),
      lefts: rects.map((r) => Math.round(r.left)),
      heights: rects.map((r) => Math.round(r.height)),
      labels: blocks.map((b) => b.textContent),
      writingMode: blocks[0] ? window.getComputedStyle(blocks[0]).writingMode : null,
    };
  });
}

test.describe('vertical breadcrumb rail', () => {
  test('單欄堆疊、文字直排、色塊上下相鄰無縫', async ({ page }) => {
    await page.setViewportSize({ width: 1500, height: 950 });
    await page.goto(PATHS.longest);

    const state = await railState(page);
    expect(state).not.toBeNull();
    expect(state!.display).toBe('flex');
    expect(state!.writingMode).toBe('vertical-rl');

    // 一欄：所有色塊同寬、左緣對齊，整條的寬度就是單塊的寬度
    expect(new Set(state!.widths)).toEqual(new Set([RAIL_WIDTH]));
    expect(new Set(state!.lefts).size).toBe(1);
    expect(Math.round(state!.width)).toBe(RAIL_WIDTH);

    expect(state!.seams.every((s) => s === 0)).toBe(true);

    // 色帶只走到分類，文章標題（SolarWinds 那一篇）不進來
    expect(state!.labels[0]).toBe('首頁');
    expect(state!.labels[1]).toBe('Backend');
    expect(state!.labels).toHaveLength(state!.blockCount);
  });

  test('色塊高度各自等於自己的標籤長度', async ({ page }) => {
    await page.setViewportSize({ width: 1500, height: 950 });
    await page.goto(PATHS.longest);

    const state = await railState(page);
    // 標籤從兩字（首頁）到十五字（攻擊者視角（紅隊）與攻擊面驗證），
    // 高度全部相同就代表色塊又被拉成統一高度了
    expect(new Set(state!.heights).size).toBeGreaterThan(1);
    // 「首頁」比「資安與資料保護」短，色塊也要比較短
    expect(state!.heights[0]).toBeLessThan(state!.heights[2]);
  });

  test('矮視窗時整條仍在畫面內、且由最長的色塊讓步', async ({ page }) => {
    await page.setViewportSize({ width: 1500, height: 950 });
    await page.goto(PATHS.longest);
    const tall = await railState(page);

    await page.setViewportSize({ width: 1500, height: 700 });
    await page.goto(PATHS.longest);
    const short = await railState(page);

    // 高視窗放得下就不壓縮，矮視窗壓縮到放得下 —— 兩者都要完整落在畫面內
    for (const s of [tall, short]) {
      expect(s!.top).toBeGreaterThanOrEqual(0);
      expect(s!.bottom).toBeLessThanOrEqual(s!.viewportHeight);
    }
    expect(short!.height).toBeLessThan(tall!.height);

    // 讓步方向：高視窗下最高的那一塊，也要是絕對值縮最多的那一塊。
    // 色塊若被設了 max-height，觸頂的長色塊會在 flex 演算法裡凍結，
    // 壓縮改由短色塊吸收，這條就會紅。
    const shrink = tall!.heights.map((h, i) => h - short!.heights[i]);
    const tallestIdx = tall!.heights.indexOf(Math.max(...tall!.heights));
    expect(shrink[tallestIdx]).toBe(Math.max(...shrink));
  });

  test('色帶貼齊視窗左緣、右緣不壓到正文', async ({ page }) => {
    for (const width of [1000, 1500, 1920]) {
      await page.setViewportSize({ width, height: 950 });
      await page.goto(PATHS.longest);

      const state = await railState(page);
      expect(state!.display, `@ ${width}`).toBe('flex');
      // 定位錨在視窗左緣而不是正文欄：視窗變寬時色帶不動、只有間距拉開
      expect(state!.left, `@ ${width}`).toBe(0);
      expect(state!.right, `@ ${width} 壓到正文`).toBeLessThan(state!.mainLeft);
    }
  });

  test('視窗放不下時整條收起、門檻不隨層數變動', async ({ page }) => {
    // 一欄堆疊之後色帶寬度固定 48px，斷點只有一個：
    // 48 + 24 留白 <= (視窗寬 - 正文欄 701) / 2，得 845px，見 custom.css
    for (const path of [PATHS.depth3, PATHS.longest]) {
      await page.setViewportSize({ width: 840, height: 950 });
      await page.goto(path);
      expect((await railState(page))!.display, `${path} @ 840`).toBe('none');

      await page.setViewportSize({ width: 900, height: 950 });
      await page.goto(path);
      expect((await railState(page))!.display, `${path} @ 900`).toBe('flex');
    }
  });

  test('首頁與搜尋頁不顯示色帶', async ({ page }) => {
    await page.setViewportSize({ width: 1500, height: 950 });
    for (const path of ['/blog/', '/blog/search/']) {
      await page.goto(path);
      await expect(page.locator('.breadcrumb-rail')).toHaveCount(0);
    }
  });
});
