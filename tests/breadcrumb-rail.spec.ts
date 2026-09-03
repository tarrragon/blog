import { expect, Page, test } from '@playwright/test';

/**
 * 左側垂直分類色帶的回歸測試。
 *
 * 整條是一欄：色塊由上往下堆疊、塊內文字 CJK 直排。五件事在改版面時會靜默
 * 壞掉，都不會有 build error：
 *
 * 1. 色塊被拉成統一高度。改一個 flex 值就會回去，而回去之後兩個字的分類會
 *    拿到跟十二個字一樣長的色塊，多出來的部分不對應任何內容。
 * 2. 主題的 `nav a` 給每個連結 12px 右外距，色塊會被推成分離的方塊而不是
 *    一條連續色帶。任何動到 nav 樣式的改動都可能把它加回來。
 * 3. 最深的路徑在矮視窗超出螢幕。色塊要壓縮就得讓 flex 的自動最小高度歸零，
 *    min-height: 0 與 overflow: hidden 各自都做得到這件事（實測：只拿掉其中
 *    一個壓縮照常，兩個都沒有才會整條溢出）。色塊另外不能設會夾住的
 *    max-height —— 觸頂的長色塊會被凍結，讓步改由短色塊吸收，畫面上看起來
 *    仍然「有壓縮」，方向卻是反的。
 *    容器有 overflow: hidden，所以「整條變矮」不等於「壓縮成功」：色塊完全
 *    不收縮時放不下的那幾塊會被切在容器外，整條的高度一樣是封頂值。
 * 4. 色帶離開視窗左緣，變成浮在頁面中間的卡片。
 * 5. 窄視窗把整條收起。左側 gutter 放不下 48px 時的規格是換成 36px 的窄版、
 *    由 body 左內距接手讓出的空間，不是拿掉整條導航。
 */

const PATHS = {
  // 首頁 + backend + 02-cache-redis
  depth3: '/blog/backend/02-cache-redis/',
  // 六層、標籤十來字，全站最長的色帶
  longest:
    '/blog/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/',
};

const RAIL_WIDTH = 48;
// 850px 以下換成窄版，見 custom.css 的 @media (max-width: 849px)
const RAIL_WIDTH_NARROW = 36;
// 色帶容器的 max-height: 88vh
const RAIL_MAX_VH = 0.88;
// 量自然高度用的視窗高度。只要遠高於 88vh 封頂所需，實際值不影響量測。
const PROBE_HEIGHT = 3000;

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

/**
 * 色帶不受 88vh 封頂時的高度。視窗開到遠高於封頂所需再量，並確認量到的值
 * 確實沒觸頂 —— 校準值本身要有失敗態，否則它會在自己也被壓縮的那次給出一個
 * 看起來合理的數字，而後續所有以它為基準的推導都跟著錯。
 */
async function naturalRailHeight(page: Page) {
  await page.setViewportSize({ width: 1500, height: PROBE_HEIGHT });
  await page.goto(PATHS.longest);
  const state = await railState(page);
  expect(state!.height, '校準用的視窗仍然放不下色帶').toBeLessThan(
    PROBE_HEIGHT * RAIL_MAX_VH,
  );
  return state!.height;
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
    // 兩個視窗高度由當場量到的自然高度推出來，不寫死。色帶的自然高度是各色塊
    // 標籤長度相加，而字數換算成像素要經過執行環境的字型度量：同一份 HTML 在
    // macOS 量到 903px、在 CI 的 Linux 只有 337px。寫死高度等於假設「這個高度
    // 一定放不下」，假設不成立時測試不會報錯 —— 兩次都沒觸發壓縮，斷言只是在
    // 比較兩個相同的數字，而讓步方向那條也就跟著失去受測對象。
    const natural = await naturalRailHeight(page);
    const capHeight = natural / RAIL_MAX_VH; // 封頂剛好等於自然高度的視窗
    const tallVp = Math.ceil(capHeight) + 40; // 放得下、不壓縮
    const shortVp = Math.round(capHeight * 0.7); // 只給七成，一定壓縮

    await page.setViewportSize({ width: 1500, height: tallVp });
    await page.goto(PATHS.longest);
    const tall = await railState(page);

    await page.setViewportSize({ width: 1500, height: shortVp });
    await page.goto(PATHS.longest);
    const short = await railState(page);

    // 高視窗那次要真的是未壓縮的基準，「誰讓步」才有對照
    expect(tall!.height).toBeCloseTo(natural, 1);

    // 高視窗放得下就不壓縮，矮視窗壓縮到放得下 —— 兩者都要完整落在畫面內
    for (const s of [tall, short]) {
      expect(s!.top).toBeGreaterThanOrEqual(0);
      expect(s!.bottom).toBeLessThanOrEqual(s!.viewportHeight);
    }
    expect(short!.height).toBeLessThan(tall!.height);

    // 讓步的方式是壓縮，不是把放不下的部分裁掉。容器有 overflow: hidden，
    // 色塊完全不收縮時整條看起來仍然變矮了（rail 被封頂），而被切到容器外的
    // 色塊高度不變 —— 讓步量全是 0，「最大值等於 0」恆真。所以先確認各塊高度
    // 相加等於整條的高度，容器外沒有東西。
    const stacked = short!.heights.reduce((a, b) => a + b, 0);
    expect(stacked, '色塊被裁到容器外，而不是壓縮').toBeLessThanOrEqual(
      Math.ceil(short!.height) + 1,
    );

    // 讓步方向：高視窗下最高的那一塊，也要是絕對值縮最多的那一塊。
    // 色塊若被設了 max-height，觸頂的長色塊會在 flex 演算法裡凍結，
    // 壓縮改由短色塊吸收，這條就會紅。
    const shrink = tall!.heights.map((h, i) => h - short!.heights[i]);
    const tallestIdx = tall!.heights.indexOf(Math.max(...tall!.heights));
    const shortestIdx = tall!.heights.indexOf(Math.min(...tall!.heights));
    expect(shrink[tallestIdx]).toBe(Math.max(...shrink));
    expect(shrink[tallestIdx], '最長的色塊沒有讓步').toBeGreaterThan(
      shrink[shortestIdx],
    );
  });

  test('色帶貼齊視窗左緣、右緣不壓到正文', async ({ page }) => {
    // 375 與 840 落在窄版區間，色帶讓出的空間由 body 左內距接手，右緣同樣
    // 要停在正文左緣之外 —— 窄版的代價是色帶自己縮，不是壓到正文上
    for (const width of [375, 840, 1000, 1500, 1920]) {
      await page.setViewportSize({ width, height: 950 });
      await page.goto(PATHS.longest);

      const state = await railState(page);
      expect(state!.display, `@ ${width}`).toBe('flex');
      // 定位錨在視窗左緣而不是正文欄：視窗變寬時色帶不動、只有間距拉開
      expect(state!.left, `@ ${width}`).toBe(0);
      expect(state!.right, `@ ${width} 壓到正文`).toBeLessThan(state!.mainLeft);
    }
  });

  test('窄視窗換窄版色帶而不收起、門檻不隨層數變動', async ({ page }) => {
    // 一欄堆疊之後色帶寬度固定、不隨層數變動，所以斷點只有一個：850px 以下
    // 色塊換成 36px、body 左內距補到 44px 接手讓出的那 12px，見 custom.css。
    // 兩條深度差一倍的路徑要在同一個寬度換版，否則「寬度不隨層數變動」就不
    // 成立了。整條在任何寬度都不收起 —— 收起的唯一情形是列印。
    for (const path of [PATHS.depth3, PATHS.longest]) {
      await page.setViewportSize({ width: 840, height: 950 });
      await page.goto(path);
      const narrow = await railState(page);
      expect(narrow!.display, `${path} @ 840`).toBe('flex');
      expect(new Set(narrow!.widths), `${path} @ 840`).toEqual(
        new Set([RAIL_WIDTH_NARROW]),
      );

      await page.setViewportSize({ width: 900, height: 950 });
      await page.goto(path);
      const wide = await railState(page);
      expect(wide!.display, `${path} @ 900`).toBe('flex');
      expect(new Set(wide!.widths), `${path} @ 900`).toEqual(new Set([RAIL_WIDTH]));
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
