import { expect, Page, Route, test } from '@playwright/test';

// vendor-lab 實測頁的承諾：讀者按下載入按鈕之前，這一頁不對 Meta / Google 發出任何請求。
// 測試把兩家的網域都攔下來回 stub，所以不依賴外部網路，也驗得到「按下之後才發出」。
const VENDOR_HOSTS = /(facebook\.net|facebook\.com|googletagmanager\.com|google-analytics\.com)/;

async function recordVendorRequests(page: Page) {
  const requests: string[] = [];
  await page.route(VENDOR_HOSTS, (route: Route) => {
    requests.push(route.request().url());
    return route.fulfill({ status: 200, contentType: 'application/javascript', body: '/* stub */' });
  });
  return requests;
}

test.describe('vendor lab pages', () => {
  test('Meta Pixel 實測頁：載入前零請求、填錯 ID 不載入、按下後注入 fbevents.js', async ({ page }) => {
    const requests = await recordVendorRequests(page);
    await page.goto('/blog/devops/monitoring/vendors/meta-pixel-lab/');
    await page.waitForLoadState('networkidle');
    expect(requests).toEqual([]);

    const lab = page.locator('.vendor-lab');
    await lab.locator('#vendor-lab-id').fill('not-a-pixel-id');
    await lab.locator('[data-action="load"]').click();
    await expect(lab.locator('.vendor-lab-status')).toContainText('ID 格式不符');
    expect(requests).toEqual([]);

    await lab.locator('#vendor-lab-id').fill('123456789012345');
    await lab.locator('[data-action="load"]').click();
    await expect(lab.locator('.vendor-lab-status')).toContainText('fbevents.js 已載入');
    expect(requests.some((u) => u.includes('connect.facebook.net/en_US/fbevents.js'))).toBe(true);

    await lab.locator('[data-action="purchase"]').click();
    await expect(lab.locator('.vendor-lab-calls')).toContainText("fbq('track', 'Purchase'");
  });

  test('GTM 實測頁：載入前零請求、按下後以填入的容器 ID 注入 gtm.js 並推資料層', async ({ page }) => {
    const requests = await recordVendorRequests(page);
    await page.goto('/blog/devops/monitoring/vendors/google-tag-manager-lab/');
    await page.waitForLoadState('networkidle');
    expect(requests).toEqual([]);

    const lab = page.locator('.vendor-lab');
    await lab.locator('#vendor-lab-id').fill('GTM-TEST123');
    await lab.locator('[data-action="load"]').click();
    await expect(lab.locator('.vendor-lab-status')).toContainText('gtm.js 已載入');
    expect(requests.some((u) => u.includes('googletagmanager.com/gtm.js?id=GTM-TEST123'))).toBe(true);

    await lab.locator('[data-action="push-purchase"]').click();
    await expect(lab.locator('.vendor-lab-datalayer')).toContainText('"event": "purchase"');
  });

  test('script 被擋下時狀態列回報載入失敗', async ({ page }) => {
    await page.route(VENDOR_HOSTS, (route: Route) => route.abort('blockedbyclient'));
    await page.goto('/blog/devops/monitoring/vendors/meta-pixel-lab/');
    const lab = page.locator('.vendor-lab');
    await lab.locator('#vendor-lab-id').fill('123456789012345');
    await lab.locator('[data-action="load"]').click();
    await expect(lab.locator('.vendor-lab-status')).toContainText('載入失敗');
  });
});
