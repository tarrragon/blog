#!/usr/bin/env python3
"""實跑三套領域壓測資料庫（schema + seed + seed_scale），量測關鍵 SQL 寫法的
EXPLAIN QUERY PLAN 與耗時，輸出結構化快照到 benchmarks/sqlite-scale-snapshots.json。

用途：
- 讓靜態練習網站直接讀取經實跑驗證的執行計畫與耗時相對倍率（非手寫臆測值）
- 支援 CI 或本機隨時重跑更新，純 Python 3 標準函式庫無外部相依
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
import time

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from verify_domains import load_domain  # noqa: E402

OUT_PATH = SCRIPT_DIR / "benchmarks" / "sqlite-scale-snapshots.json"


# 每個計時樣本至少累積這麼久：單次執行只有幾微秒的查詢，直接計時會落在計時器解析度附近，
# 算出來的倍率（例如 0.562 / 0.001 = 562x）其實是在除以雜訊。改為在一個樣本內重複執行 N 次再除以 N。
MIN_SAMPLE_MS = 20.0


def measure_query(conn: sqlite3.Connection, sql: str, runs: int = 7) -> dict:
    plan = [str(r[-1]) for r in conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()]
    # 預熱一次消除首次編譯雜訊，同時估算單次耗時以決定每個樣本的重複次數
    t0 = time.perf_counter()
    rows = conn.execute(sql).fetchall()
    first_ms = (time.perf_counter() - t0) * 1000
    loops = max(1, min(10000, int(MIN_SAMPLE_MS / max(first_ms, 0.0005))))
    timings = []
    for _ in range(runs):
        t0 = time.perf_counter()
        for _ in range(loops):
            rows = conn.execute(sql).fetchall()
        timings.append((time.perf_counter() - t0) * 1000 / loops)
    return {
        "sql": " ".join(sql.split()),
        "rowCount": len(rows),
        "explainPlan": plan,
        "loopsPerSample": loops,
        "minMs": round(min(timings), 4),
        "medianMs": round(statistics.median(timings), 4),
    }


def ratio_text(slow: dict, fast: dict, label: str) -> str:
    """兩個變體的中位數倍率；附上絕對差，提醒讀者倍率大不代表使用者感覺得到。"""
    ratio = slow["medianMs"] / max(fast["medianMs"], 0.0001)
    diff = slow["medianMs"] - fast["medianMs"]
    return f"{ratio:.1f}x（{label}；單次差 {diff:.3f} ms）"


def run_all_benchmarks() -> dict:
    benchmarks = []

    # 1. bookstore：Sargable vs substr（50,009 筆 orders）
    conn = load_domain("bookstore", with_scale=True)
    try:
        b1_variants = {
            "non_sargable_substr": measure_query(
                conn,
                "SELECT COUNT(*) FROM orders WHERE substr(ordered_at, 1, 7) = '2025-06';",
            ),
            "sargable_half_open": measure_query(
                conn,
                "SELECT COUNT(*) FROM orders WHERE ordered_at >= '2025-06-01 00:00:00' AND ordered_at < '2025-07-01 00:00:00';",
            ),
        }
        benchmarks.append(
            {
                "benchmarkId": "bm-bookstore-sargable-range",
                "domain": "bookstore",
                "conceptIds": ["S5-01"],
                "measurementSource": "live-sqlite-measured",
                "datasetScale": "50,009 orders（含 idx_orders_ordered_id 索引）",
                "title": "單月訂單區間查詢：substr 包欄位 vs 半開區間",
                "variants": b1_variants,
                "speedupRatio": ratio_text(
                    b1_variants["non_sargable_substr"], b1_variants["sargable_half_open"], "半開區間相對 substr"
                ),
            }
        )

        # 2. bookstore：高重複熱點 email（7,007 顧客，2,000 列同信箱）
        b2_variants = {
            "group_by_having": measure_query(
                conn,
                "SELECT email FROM customers WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1;",
                runs=5,
            ),
            "self_join_distinct": measure_query(
                conn,
                "SELECT DISTINCT c1.email FROM customers c1 JOIN customers c2 ON c1.email = c2.email AND c1.customer_id <> c2.customer_id;",
                runs=3,
            ),
        }
        benchmarks.append(
            {
                "benchmarkId": "bm-bookstore-duplicate-email-skew",
                "domain": "bookstore",
                "conceptIds": ["S5-02"],
                "measurementSource": "live-sqlite-measured",
                "datasetScale": "7,007 customers（單一熱點重複 2,000 次、已抹除顧客 email 為 NULL，email 無索引）",
                "title": "熱點重複 Email 稽核：GROUP BY HAVING vs 自連接配對展開",
                "variants": b2_variants,
                "speedupRatio": ratio_text(
                    b2_variants["self_join_distinct"], b2_variants["group_by_having"], "GROUP BY 相對自連接"
                ),
            }
        )

        # 3. bookstore：深頁 OFFSET vs Keyset（回表取非索引欄位 total_amount, status）
        b3_variants = {
            "deep_offset_25000": measure_query(
                conn,
                "SELECT order_id, customer_id, status, total_amount, ordered_at FROM orders ORDER BY ordered_at DESC, order_id DESC LIMIT 20 OFFSET 25000;",
            ),
            "keyset_cursor": measure_query(
                conn,
                "SELECT order_id, customer_id, status, total_amount, ordered_at FROM orders WHERE (ordered_at, order_id) < ('2025-08-01 00:00:00', 150000) ORDER BY ordered_at DESC, order_id DESC LIMIT 20;",
            ),
        }
        benchmarks.append(
            {
                "benchmarkId": "bm-bookstore-offset-vs-keyset",
                "domain": "bookstore",
                "conceptIds": ["S3-05"],
                "measurementSource": "live-sqlite-measured",
                "datasetScale": "50,009 orders（含 idx_orders_ordered_id 索引，回表取 5 欄）",
                "title": "訂單深頁分頁：OFFSET 25000 vs Keyset 接續標記",
                "variants": b3_variants,
                "speedupRatio": ratio_text(
                    b3_variants["deep_offset_25000"], b3_variants["keyset_cursor"], "Keyset 相對 OFFSET 25000"
                ),
            }
        )
    finally:
        conn.close()

    # 4. swift-logistics：部分索引（約 4.5 萬筆 dispatch_tasks，僅 12 筆 queued）
    conn_l = load_domain("swift-logistics", with_scale=True)
    try:
        # 比較有部分索引與強制忽略索引（+status）的差異
        b4_variants = {
            "full_scan_bypass_index": measure_query(
                conn_l,
                "SELECT task_id FROM dispatch_tasks WHERE +status = 'queued' ORDER BY priority DESC, created_at ASC LIMIT 1;",
            ),
            "partial_index_queued": measure_query(
                conn_l,
                "SELECT task_id FROM dispatch_tasks WHERE status = 'queued' ORDER BY priority DESC, created_at ASC LIMIT 1;",
            ),
        }
        task_cnt = conn_l.execute("SELECT COUNT(*) FROM dispatch_tasks;").fetchone()[0]
        benchmarks.append(
            {
                "benchmarkId": "bm-logistics-partial-index-queue",
                "domain": "swift-logistics",
                "conceptIds": ["S7-04"],
                "measurementSource": "live-sqlite-measured",
                "datasetScale": f"{task_cnt:,} dispatch_tasks（僅 12 筆 queued，其餘 completed 或 claimed）",
                "title": "高比例已完成任務表輪詢：無索引全掃 vs 部分索引 WHERE status = 'queued'",
                "variants": b4_variants,
                "speedupRatio": ratio_text(
                    b4_variants["full_scan_bypass_index"], b4_variants["partial_index_queued"], "部分索引相對全表掃描"
                ),
            }
        )
    finally:
        conn_l.close()

    # 5. cloud-academy：重送風暴稽核（20,015 筆 webhook_events，1,500 筆熱點重送）
    conn_c = load_domain("cloud-academy", with_scale=True)
    try:
        b5_variants = {
            "group_by_having": measure_query(
                conn_c,
                "SELECT provider, external_id FROM webhook_events GROUP BY provider, external_id HAVING COUNT(*) > 1;",
                runs=5,
            ),
            "partial_index_pending": measure_query(
                conn_c,
                "SELECT event_id FROM webhook_events WHERE status = 'pending' ORDER BY received_at ASC LIMIT 5;",
            ),
        }
        benchmarks.append(
            {
                "benchmarkId": "bm-academy-webhook-storm",
                "domain": "cloud-academy",
                "conceptIds": ["S5-02", "S7-04"],
                "measurementSource": "live-sqlite-measured",
                "datasetScale": "20,015 webhook_events（含 1,500 筆 evt_storm_hot 重送與 12 筆 pending）",
                "title": "Webhook 重送稽核與待處理佇列部分索引定位",
                "variants": b5_variants,
                "speedupRatio": "見各變體執行計畫與中位數耗時",
            }
        )
    finally:
        conn_c.close()

    return {
        "schemaVersion": "1.0",
        "engine": f"SQLite {sqlite3.sqlite_version}",
        "runtime": f"Python {platform.python_version()} ({platform.system()} {platform.machine()})",
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": (
            "時間絕對值隨硬體與版本改變，教學判讀重點為同一組資料上的執行計畫結構與相對量級差。"
            "每個樣本重複執行 loopsPerSample 次再取單次平均，避免微秒級查詢的倍率落在計時器解析度上。"
            "多數變體的單次差距在幾毫秒以內，低於使用者感覺得到的約 100 ms，網站呈現時應以執行計畫與倍率為主、時間為輔。"
        ),
        "benchmarks": benchmarks,
    }


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = run_all_benchmarks()
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH} ({len(result['benchmarks'])} benchmarks)")
    for b in result["benchmarks"]:
        print(f"  - {b['benchmarkId']}: {b['speedupRatio']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
