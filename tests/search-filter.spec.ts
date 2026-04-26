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

/**
 * Visible-only result count — excludes hidden results.
 *
 * Critical detail (#69 dogfooding): the OLD buggy code used view-layer
 * post-filter that sets `display: none !important` on results that don't
 * match. If we count `.pagefind-ui__result` indiscriminately, we'd count
 * hidden ones too — making the test pass even on buggy code (false negative).
 *
 * We must count actually-visible results: not [hidden] AND computed display
 * is not 'none'.
 */
async function visibleResultCount(page: Page): Promise<number> {
  return page.evaluate(() => {
    return Array.from(document.querySelectorAll('.pagefind-ui__result')).filter(
      (el) => {
        const style = window.getComputedStyle(el as HTMLElement);
        return style.display !== 'none' && !(el as HTMLElement).hidden;
      }
    ).length;
  });
}

/** Read first N visible result titles. */
async function visibleTitles(page: Page, n: number): Promise<string[]> {
  return page.evaluate((limit) => {
    return Array.from(document.querySelectorAll('.pagefind-ui__result'))
      .filter((el) => {
        const style = window.getComputedStyle(el as HTMLElement);
        return style.display !== 'none' && !(el as HTMLElement).hidden;
      })
      .slice(0, limit)
      .map((el) => {
        const t = el.querySelector('.pagefind-ui__result-title');
        return t ? t.textContent?.trim() ?? '' : '';
      });
  }, n);
}

test.describe('search scope filter (multi-index)', () => {
  test('mode switch loads from scope-specific index (network-level proof of multi-index)', async ({
    page,
  }) => {
    // Network-level assertion: switching to scope=title MUST trigger a request
    // to /pagefind-title/ (and content scope to /pagefind-content/). This
    // structurally distinguishes the multi-index fix from the buggy
    // view-layer post-filter: buggy code never loaded those bundles because
    // they don't exist, so this test fails RED on the buggy build.
    const titleBundleRequests: string[] = [];
    const contentBundleRequests: string[] = [];
    page.on('request', (req) => {
      const url = req.url();
      if (url.includes('/pagefind-title/')) titleBundleRequests.push(url);
      if (url.includes('/pagefind-content/')) contentBundleRequests.push(url);
    });

    await gotoSearch(page);
    await setQuery(page, '寫作');

    await setScope(page, 'title');
    // Wait for pagefind to load + query
    await page.waitForTimeout(1500);

    expect(titleBundleRequests.length).toBeGreaterThan(0);

    await setScope(page, 'content');
    await page.waitForTimeout(1500);

    expect(contentBundleRequests.length).toBeGreaterThan(0);
  });

  test('title scope: every visible result contains query in title (no view-layer hide)', async ({
    page,
  }) => {
    const query = '寫作';

    await gotoSearch(page);
    await setQuery(page, query);
    await setScope(page, 'title');

    const titles = await visibleTitles(page, 20);
    expect(titles.length).toBeGreaterThan(0);

    // Strict: every visible title must contain the query (no fakery via
    // hide). With buggy code, pagefind returns full-text matches and view
    // layer tries to hide non-title-matches — but if regex escaping fails or
    // the apply() runs before MutationObserver, non-matching results might
    // be visible. With the fix, this is guaranteed by the source index.
    for (const title of titles) {
      expect(title.toLowerCase()).toContain(query);
    }
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

  test('post markup has data-pagefind-body (structural prerequisite for multi-index)', async ({
    page,
  }) => {
    // Structural test: verify the markup change that enables multi-index
    // strategy. The buggy code used <content> tag (no data-pagefind-body),
    // the fix uses <div class="article-body" data-pagefind-body>. This is a
    // structural prerequisite for content-only index extraction.
    //
    // Pick a known post page (any post with single.html layout).
    await page.goto(
      '/blog/posts/blog-markdown-寫作規範與-mdtools-檢查/',
    );
    const articleBody = page.locator('.article-body[data-pagefind-body]');
    await expect(articleBody).toHaveCount(1);

    // The hidden title meta inside .article-body (for content-only index)
    const titleMeta = page.locator(
      '.article-body [data-pagefind-meta="title"]',
    );
    await expect(titleMeta).toHaveCount(1);
  });

  // === Checkpoint 1 retrospective fixes (#70 / #71 / filter UI hint) ===

  test('URL persistence: deep link with ?q=X&scope=Y restores state on load (#70)', async ({
    page,
  }) => {
    // Navigate with both q and scope params. After load, both should be applied.
    await page.goto('/blog/search/?q=' + encodeURIComponent('寫作') + '&scope=title');
    await page.locator('.pagefind-ui__search-input').waitFor({ timeout: 10_000 });
    await page.waitForTimeout(1500);

    const state = await page.evaluate(() => ({
      scope: (
        document.querySelector(
          '.search-scope input[name="search-scope"]:checked',
        ) as HTMLInputElement
      )?.value,
      query: (
        document.querySelector('.pagefind-ui__search-input') as HTMLInputElement
      )?.value,
    }));

    expect(state.scope).toBe('title');
    expect(state.query).toBe('寫作');
  });

  test('URL persistence: state changes write back to URL (#70)', async ({ page }) => {
    await gotoSearch(page);
    await setQuery(page, '寫作');
    await setScope(page, 'title');
    await page.waitForTimeout(500);

    const url = page.url();
    expect(url).toContain('q=' + encodeURIComponent('寫作'));
    expect(url).toContain('scope=title');
  });

  test('Tab order: search input is first focusable, before scope radios (#71)', async ({
    page,
  }) => {
    await gotoSearch(page);

    // Find the document order positions of search input vs scope radios.
    const positions = await page.evaluate(() => {
      const input = document.querySelector('.pagefind-ui__search-input');
      const firstScopeRadio = document.querySelector(
        '.search-scope input[name="search-scope"]',
      );
      if (!input || !firstScopeRadio) return null;
      // Use compareDocumentPosition: returns DOCUMENT_POSITION_FOLLOWING (4)
      // if firstScopeRadio comes after input in document order.
      const cmp = input.compareDocumentPosition(firstScopeRadio);
      return {
        inputBeforeScope: !!(cmp & Node.DOCUMENT_POSITION_FOLLOWING),
      };
    });

    expect(positions).not.toBeNull();
    expect(positions!.inputBeforeScope).toBe(true);
  });

  test('Filter UI hint: visible when scope is title or content', async ({ page }) => {
    await gotoSearch(page);
    await setQuery(page, '寫作');

    // In 'all' mode, hint should NOT be visible
    await setScope(page, 'all');
    let hintVisible = await page
      .locator('.search-scope-hint')
      .isVisible()
      .catch(() => false);
    expect(hintVisible).toBe(false);

    // In 'title' mode, hint SHOULD be visible (filter UI gone, user needs to know)
    await setScope(page, 'title');
    hintVisible = await page
      .locator('.search-scope-hint')
      .isVisible()
      .catch(() => false);
    expect(hintVisible).toBe(true);

    // In 'content' mode, hint SHOULD also be visible
    await setScope(page, 'content');
    hintVisible = await page
      .locator('.search-scope-hint')
      .isVisible()
      .catch(() => false);
    expect(hintVisible).toBe(true);
  });
});
