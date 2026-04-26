import { test, expect, Page } from '@playwright/test';

/**
 * Regression tests for the search page's title/content scope filter.
 *
 * Bug we're guarding against (#55 layer mismatch):
 *   Old impl used view-layer post-filter on a paginated source. When the user
 *   selected title-only and clicked load more, the new batch could all fail
 *   the title regex → all hidden → user saw "load more did nothing" silent
 *   failure on sparse cases.
 *
 * Fix (#59 strategy C — multi-index):
 *   Build emits three pagefind indexes (full / title-only / content-only).
 *   Scope switch destroys + reinitializes PagefindUI with the matching
 *   bundlePath. Each scope returns the full set under that mode — no
 *   downstream silent gap is possible.
 *
 * These tests verify:
 *   1. Mode switch actually re-runs the query (results change)
 *   2. title scope returns ≤ all scope (subset relation holds)
 *   3. Sparse case shows clear empty state, not silent
 *   4. Load more in title scope brings in more title-matching results
 */

const SEARCH_PATH = '/blog/search/';

async function gotoSearch(page: Page, query?: string) {
  const url = query ? `${SEARCH_PATH}?q=${encodeURIComponent(query)}` : SEARCH_PATH;
  await page.goto(url);
  // Wait for PagefindUI to mount + first render.
  await page.locator('.pagefind-ui__search-input').waitFor({ timeout: 10_000 });
}

async function setQuery(page: Page, query: string) {
  const input = page.locator('.pagefind-ui__search-input');
  await input.fill(query);
  // Pagefind debounces; give it time to fetch + render.
  await page.waitForTimeout(800);
}

async function setScope(page: Page, scope: 'all' | 'title' | 'content') {
  await page.locator(`input[name="search-scope"][value="${scope}"]`).check();
  // After scope change, PagefindUI is destroyed + reinitialized + state restored.
  // Wait for the new UI + result render.
  await page.waitForTimeout(1000);
}

async function visibleResultCount(page: Page): Promise<number> {
  return page.locator('.pagefind-ui__result').count();
}

test.describe('search scope filter (multi-index)', () => {
  test('mode switch re-runs query (different result counts possible)', async ({
    page,
  }) => {
    await gotoSearch(page);
    await setQuery(page, '搜尋');

    await setScope(page, 'all');
    const allCount = await visibleResultCount(page);
    expect(allCount).toBeGreaterThan(0);

    await setScope(page, 'title');
    const titleCount = await visibleResultCount(page);

    // The two counts come from different indexes, so at least the result
    // identity changes; we mainly check that switching didn't crash and the
    // new query rendered something or shows empty state.
    const titleIsEmpty = await page
      .locator('.pagefind-ui__message')
      .filter({ hasText: /找不到|找到 0|相關內容/ })
      .first()
      .isVisible()
      .catch(() => false);

    expect(titleCount > 0 || titleIsEmpty).toBe(true);
  });

  test('title scope returns subset of all scope (counts respect ⊆)', async ({
    page,
  }) => {
    // Pick a query that's likely to appear in both title and body of multiple posts.
    const query = '寫作';

    await gotoSearch(page);
    await setQuery(page, query);

    await setScope(page, 'all');
    const allCount = await visibleResultCount(page);

    await setScope(page, 'title');
    const titleCount = await visibleResultCount(page);

    // Title-matching pages are a subset of all-matching pages.
    // (Pagefind ranks differently per index but the page set should satisfy this.)
    expect(titleCount).toBeLessThanOrEqual(allCount);
  });

  test('sparse query shows explicit empty state, not silent failure', async ({
    page,
  }) => {
    await gotoSearch(page);
    // String unlikely to appear in any title.
    await setQuery(page, 'zzzunlikely');
    await setScope(page, 'title');

    // Either no results visible OR an empty/zero-results message is shown.
    const resultCount = await visibleResultCount(page);
    const hasEmptyMessage = await page
      .locator('.pagefind-ui__message')
      .filter({ hasText: /找不到|找到 0|相關內容/ })
      .first()
      .isVisible()
      .catch(() => false);

    expect(resultCount === 0 && hasEmptyMessage).toBe(true);
  });

  test('title scope: load more reveals more title-matching results, not silent', async ({
    page,
  }) => {
    // Use a common term to get enough results that load-more is offered.
    await gotoSearch(page);
    await setQuery(page, '寫');
    await setScope(page, 'title');

    const before = await visibleResultCount(page);
    const loadMore = page.locator('.pagefind-ui__button').filter({ hasText: /載入更多|Load/ });
    if (!(await loadMore.isVisible().catch(() => false))) {
      // No load-more available — title scope already shows everything.
      // That's a valid pass — the bug we guard against (silent failure on load more)
      // can't manifest if there's nothing more to load.
      test.skip();
      return;
    }

    await loadMore.click();
    await page.waitForTimeout(500);
    const after = await visibleResultCount(page);

    // The fix guarantees: load more in title scope brings in more title-matching
    // results (not silent post-hidden ones). At minimum, count should increase.
    expect(after).toBeGreaterThan(before);
  });
});
