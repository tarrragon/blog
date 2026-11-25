/**
 * 開發版自動重新載入（只用於開發建置）
 *
 * 用法：在開發建置的最後一步、所有檔案都寫完之後呼叫
 *   const { applyDevAutoReload } = require('./dev-auto-reload')
 *   if (isDevBuild && process.env.DEV_AUTO_RELOAD !== '0') applyDevAutoReload(buildDir)
 *
 * 它對 buildDir 做三件事：
 * 1. manifest.json 加 `alarms` 權限（只在開發版）。
 * 2. 在 manifest.background.service_worker 指向的檔案尾端附加一段程式，
 *    這次的建置戳記寫死在程式裡。
 * 3. 最後才寫出 dev-build-stamp.json。
 *
 * service worker 每 3 秒讀一次 dev-build-stamp.json，與寫死的戳記不同就 chrome.runtime.reload()。
 * 戳記要寫死在程式裡：service worker 閒置被停掉再喚醒時跑的是載入時的舊程式，
 * 若改成啟動時讀檔記下，舊程式會記到新戳記而永遠不重新載入。
 * 建置過程若先清空輸出目錄，期間讀不到戳記檔就不重新載入；戳記檔最後才寫，
 * 不會重新載入到建到一半的版本。
 */

const fs = require('fs')
const path = require('path')

const STAMP_FILE = 'dev-build-stamp.json'
const ALARM_NAME = 'dev-auto-reload'
// 未封裝的擴充功能，chrome.alarms 的間隔可以低於 30 秒
const CHECK_PERIOD_MINUTES = 0.05

/**
 * @param {string} stamp - 這次建置的戳記
 * @returns {string} 附加到 service worker 檔案尾端的程式
 */
function buildSnippet (stamp) {
  return `
;/* dev-auto-reload：只存在於開發版建置 */
;(() => {
  const BUILT_STAMP = ${JSON.stringify(stamp)}
  const STAMP_URL = chrome.runtime.getURL(${JSON.stringify(STAMP_FILE)})
  const readStamp = () => fetch(STAMP_URL, { cache: 'no-store' })
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => (data && data.stamp) || null)
    .catch(() => null)
  const check = async () => {
    const onDisk = await readStamp()
    if (onDisk && onDisk !== BUILT_STAMP) {
      console.log('[dev-auto-reload] 偵測到新建置，重新載入擴充功能', { from: BUILT_STAMP, to: onDisk })
      chrome.runtime.reload()
    }
  }
  console.log('[dev-auto-reload] 目前建置', BUILT_STAMP)
  if (chrome.alarms) {
    chrome.alarms.create(${JSON.stringify(ALARM_NAME)}, { periodInMinutes: ${CHECK_PERIOD_MINUTES} })
    chrome.alarms.onAlarm.addListener((alarm) => { if (alarm.name === ${JSON.stringify(ALARM_NAME)}) check() })
  }
  check()
})()
`
}

/**
 * @param {object} manifest
 * @returns {object} 加上 alarms 權限的新物件（不改動輸入）
 */
function withAlarmsPermission (manifest) {
  const permissions = new Set(manifest.permissions || [])
  permissions.add('alarms')
  return { ...manifest, permissions: [...permissions] }
}

/**
 * @param {string} buildDir - 開發版輸出目錄（已含打包好的 service worker 檔）
 * @param {string} [stamp] - 建置戳記，預設為當下時間
 * @returns {{ stamp: string }}
 */
function applyDevAutoReload (buildDir, stamp = String(Date.now())) {
  const manifestPath = path.join(buildDir, 'manifest.json')
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
  fs.writeFileSync(manifestPath, JSON.stringify(withAlarmsPermission(manifest), null, 2))

  const workerPath = path.join(buildDir, manifest.background.service_worker)
  fs.appendFileSync(workerPath, buildSnippet(stamp))

  fs.writeFileSync(path.join(buildDir, STAMP_FILE), JSON.stringify({ stamp }))
  return { stamp }
}

module.exports = { applyDevAutoReload, buildSnippet, withAlarmsPermission, STAMP_FILE, ALARM_NAME }
