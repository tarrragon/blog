// 量 sql.js（SQLite WASM）在三個領域、三種倍數下灌入 seed_scale.sql 的耗時與資料庫大小。
// README〈瀏覽器端載入（SQLite WASM）〉那張載入成本表的數字由本腳本產生。
//
// sql.js 不放進 repo 的 package.json：先裝到 repo 以外的目錄，再把那個目錄當第一個引數傳進來。
//   npm install --prefix <目錄> sql.js@1.13.0
//   node scripts/sql-practice/wasm_load_bench.mjs <目錄>
// 輸出每行一組：倍數、領域、seed_scale 耗時、匯出後的資料庫大小、外鍵違規數、SQLite 版本。
// 外鍵違規數不是 0 時 exit 1。
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const sqljsDir = process.argv[2];
if (!sqljsDir) {
  console.error('usage: node wasm_load_bench.mjs <sql.js 的安裝目錄（npm install --prefix 的目錄）>');
  process.exit(2);
}
const require = createRequire(path.resolve(sqljsDir) + '/');
const initSqlJs = require('sql.js');
const domainsDir = path.join(path.dirname(fileURLToPath(import.meta.url)), 'domains');

const SQL = await initSqlJs();
let failed = false;
for (const mult of [1, 3, 10]) {
  for (const domain of ['bookstore', 'cloud-academy', 'swift-logistics']) {
    const read = (f) => fs.readFileSync(path.join(domainsDir, domain, f), 'utf8');
    const db = new SQL.Database();
    // 外鍵要在交易外開啟；sql.js 新建的資料庫預設是 0。
    db.exec('PRAGMA foreign_keys = ON');
    db.exec(read('schema.sql'));
    db.exec(read('seed.sql'));
    db.exec(`CREATE TEMP TABLE scale_params (mult INTEGER NOT NULL); INSERT INTO scale_params VALUES (${mult});`);
    const t0 = performance.now();
    db.exec(read('seed_scale.sql'));
    const ms = performance.now() - t0;
    const fkErrors = db.exec('PRAGMA foreign_key_check').length;
    const version = db.exec('SELECT sqlite_version()')[0].values[0][0];
    console.log(`x${mult} ${domain} seed_scale ${ms.toFixed(0)}ms db ${(db.export().length / 1e6).toFixed(1)}MB fkErr ${fkErrors} sqlite ${version}`);
    if (fkErrors) failed = true;
    db.close();
  }
}
process.exit(failed ? 1 : 0);
